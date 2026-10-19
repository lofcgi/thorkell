from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from thorkell.body import auth, protocol
from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession, CommandRejected

TOKEN = "3c" * 32


class FakeBody:
    """Minimal Thorkell.Body: handshake, then answer commands like ActionRunner does."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self.seq = 0
        self.task: asyncio.Task[None] | None = None
        self.reject_ops: set[str] = set()

    @classmethod
    async def connect(cls, port: int) -> FakeBody:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        body = cls(reader, writer)
        challenge = json.loads(await reader.readline())
        await body.send(
            "hello",
            role="body",
            proto=[1, 0],
            plugin="test",
            game={"version": "1.0.16", "network": 40, "assembly_sha256": "00"},
            session="ab" * 16,
            caps=["observe", "act"],
            mac=auth.mac(TOKEN, challenge["nonce"], "body", "ab" * 16),
        )
        welcome = json.loads(await reader.readline())
        assert welcome["t"] == "welcome"
        body.task = asyncio.create_task(body.serve())
        return body

    async def send(self, t: str, **body: Any) -> None:
        self.seq += 1
        self.writer.write((json.dumps({"v": 1, "t": t, "seq": self.seq, "ts": 1, **body}) + "\n").encode())
        await self.writer.drain()

    async def serve(self) -> None:
        while line := await self.reader.readline():
            message = json.loads(line)
            if message["t"] == "cmd":
                if message["op"] in self.reject_ops:
                    await self.send("ack", cmd_id=message["id"], accepted=False, code="not_armed")
                    continue
                await self.send("ack", cmd_id=message["id"], accepted=True, code="ok")
                await self.send("progress", cmd_id=message["id"], metrics={"remaining_m": 3.0})
                await self.send(
                    "result",
                    cmd_id=message["id"],
                    status="succeeded",
                    code="arrived",
                    evidence={"remaining_m": 1.0},
                )
            elif message["t"] == "query":
                await self.send("query_result", id=message["id"], ok=True, data={"recipes": ["곤봉"]})


@pytest.fixture
async def wired() -> AsyncIterator[tuple[BodySession, FakeBody]]:
    session = BodySession()
    server = BridgeServer(TOKEN, session.on_message)
    session.attach(server)
    await server.start(0)
    body = await FakeBody.connect(server.port)
    yield session, body
    await server.close()


async def test_command_round_trip_collects_progress(wired: tuple[BodySession, FakeBody]) -> None:
    session, _ = wired
    result = await session.command("move_to", {"target": {"pos": [1, 2, 3]}}, timeout=2)
    assert result.status == "succeeded"
    assert result.code == "arrived"


async def test_rejected_command_raises_with_code(wired: tuple[BodySession, FakeBody]) -> None:
    session, body = wired
    body.reject_ops.add("attack")
    with pytest.raises(CommandRejected) as error:
        await session.command("attack", {"id": "1:2"}, timeout=2)
    assert error.value.code == "not_armed"


async def test_observations_and_events_are_tracked(wired: tuple[BodySession, FakeBody]) -> None:
    session, body = wired
    await body.send(
        "status", armed=True, ready=True, reasons=[], version_gate={"ok": True, "found": "1", "tested": "1"}
    )
    await body.send(
        "scene", tick=1, data={"nearby": [{"id": "1:2", "kind": "tree"}], "inventory": [{"name": "돌도끼"}]}
    )
    await body.send("event", kind="chat", tick=2, data={"from": "Leader", "text": "안녕"})
    await session.wait_for(
        lambda: session.armed and session.scene is not None and bool(session.events), timeout=2
    )
    assert session.nearby("tree")[0]["id"] == "1:2"
    assert session.inventory()[0]["name"] == "돌도끼"
    assert session.events_of("chat")[0].data["text"] == "안녕"


async def test_query_round_trip(wired: tuple[BodySession, FakeBody]) -> None:
    session, _ = wired
    result = await session.query("known", {})
    assert result.ok
    assert result.data == {"recipes": ["곤봉"]}


async def test_timeout_is_an_error(wired: tuple[BodySession, FakeBody]) -> None:
    session, body = wired
    assert body.task is not None
    body.task.cancel()
    with pytest.raises(TimeoutError) as error:
        await session.command("wait", {"seconds": 1}, timeout=0.2)
    # 실게임(2026-10-17): 보스전이 빈 TimeoutError로 끝나서 어느 명령이 멈췄는지 알 수 없었다.
    assert "wait" in str(error.value) and "no ack" in str(error.value)


def test_session_requires_server() -> None:
    session = BodySession()
    with pytest.raises(RuntimeError):
        asyncio.run(session.command("wait", {}))


def test_message_types_handled() -> None:
    handled = {"state", "scene", "status", "event", "ack", "progress", "result", "query_result"}
    plugin_to_brain = {"hello", *handled}
    assert handled <= set(protocol.TYPES)
    assert plugin_to_brain - handled == {"hello"}


async def test_cancelling_a_command_tells_the_body(wired: tuple[BodySession, FakeBody]) -> None:
    session, body = wired
    assert body.task is not None
    body.task.cancel()
    seen: list[dict[str, Any]] = []

    async def record() -> None:
        while line := await body.reader.readline():
            seen.append(json.loads(line))

    recorder = asyncio.create_task(record())
    task = asyncio.create_task(session.command("move_to", {"target": {"pos": [0, 0, 0]}}, timeout=5))
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.sleep(0.1)
    recorder.cancel()
    kinds = [m["t"] for m in seen]
    assert kinds == ["cmd", "cancel"]
    assert seen[1]["cmd_id"] == seen[0]["id"]
    # a late ack/result for the abandoned command is consumed without error
    await body.send("ack", cmd_id=seen[0]["id"], accepted=True, code="ok")
    await body.send("result", cmd_id=seen[0]["id"], status="cancelled", code="abandoned", evidence={})
    await asyncio.sleep(0.1)


async def test_a_late_answer_to_a_timed_out_query_is_dropped(wired: tuple[BodySession, FakeBody]) -> None:
    # 실게임(새 월드, 2026-10-18): 시간이 지난 질의의 답이 늦게 오자 링크 처리기가 InvalidStateError로 죽었다.
    session, body = wired
    assert body.task is not None
    body.task.cancel()
    seen: list[dict[str, Any]] = []

    async def record() -> None:
        while line := await body.reader.readline():
            seen.append(json.loads(line))

    recorder = asyncio.create_task(record())
    with pytest.raises(TimeoutError):
        await session.query("look", {}, timeout=0.1)
    await body.send("query_result", id=seen[0]["id"], ok=True, data={"frames": []})
    await asyncio.sleep(0.1)
    recorder.cancel()
    assert session._server is not None and session._server.connected("body")
    assert seen[0]["id"] not in session._pending
