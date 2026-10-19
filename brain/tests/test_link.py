from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest

from thorkell.body import auth, protocol
from thorkell.body.link import BridgeServer

TOKEN = "5a" * 32


class FakePlugin:
    """Speaks the plugin side of the handshake, like Thorkell.Body would."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self.seq = 0

    @classmethod
    async def connect(cls, port: int) -> FakePlugin:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        return cls(reader, writer)

    async def read(self) -> dict[str, object]:
        line = await asyncio.wait_for(self.reader.readline(), 2)
        assert line, "connection closed"
        result: dict[str, object] = json.loads(line)
        return result

    async def send_raw(self, payload: dict[str, object]) -> None:
        self.writer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode())
        await self.writer.drain()

    async def hello(
        self, role: str = "body", token: str = TOKEN, session: str = "ab" * 16
    ) -> dict[str, object]:
        challenge = await self.read()
        assert challenge["t"] == "challenge"
        self.seq += 1
        await self.send_raw(
            {
                "v": 1,
                "t": "hello",
                "seq": self.seq,
                "ts": 1,
                "role": role,
                "proto": [1, 0],
                "plugin": "0.1.0",
                "game": {"version": "1.0.16", "network": 40, "assembly_sha256": "00"},
                "session": session,
                "caps": ["observe", "move", "teleport"],
                "mac": auth.mac(token, str(challenge["nonce"]), role, session),
            }
        )
        return await self.read()

    async def send(self, kind: str, data: dict[str, object]) -> None:
        self.seq += 1
        await self.send_raw(
            {"v": 1, "t": "event", "seq": self.seq, "ts": 2, "kind": kind, "tick": 1, "data": data}
        )

    async def closed(self) -> bool:
        return await asyncio.wait_for(self.reader.read(), 2) == b""


@pytest.fixture
async def server() -> AsyncIterator[tuple[BridgeServer, list[tuple[str, protocol.Message]]]]:
    received: list[tuple[str, protocol.Message]] = []

    async def on_message(role: str, message: protocol.Message) -> None:
        received.append((role, message))

    bridge = BridgeServer(TOKEN, on_message)
    await bridge.start(0)
    yield bridge, received
    await bridge.close()


async def test_handshake_then_events_flow_both_ways(
    server: tuple[BridgeServer, list[tuple[str, protocol.Message]]],
) -> None:
    bridge, received = server
    plugin = await FakePlugin.connect(bridge.port)
    welcome = await plugin.hello()
    assert welcome["t"] == "welcome"
    assert welcome["accepted_caps"] == ["observe", "move"]
    assert bridge.connected("body")

    await plugin.send("chat", {"from": "leader", "talker": "normal", "text": "나무 좀 해줘"})
    for _ in range(50):
        if received:
            break
        await asyncio.sleep(0.01)
    role, message = received[0]
    assert role == "body"
    assert isinstance(message, protocol.Event)
    assert message.data["text"] == "나무 좀 해줘"

    await bridge.send("body", protocol.StopAll(seq=0, ts=0, reason="test"))
    stop = await plugin.read()
    assert stop["t"] == "stop_all"
    assert isinstance(stop["seq"], int) and stop["seq"] > int(str(welcome["seq"]))


async def test_bad_mac_is_rejected(server: tuple[BridgeServer, list[tuple[str, protocol.Message]]]) -> None:
    bridge, _ = server
    plugin = await FakePlugin.connect(bridge.port)
    reply = await plugin.hello(token="00" * 32)
    assert reply == {**reply, "t": "reject", "reason": "bad_mac"}
    assert await plugin.closed()
    assert not bridge.connected("body")


async def test_second_connection_for_same_role_is_rejected(
    server: tuple[BridgeServer, list[tuple[str, protocol.Message]]],
) -> None:
    bridge, _ = server
    first = await FakePlugin.connect(bridge.port)
    assert (await first.hello())["t"] == "welcome"
    second = await FakePlugin.connect(bridge.port)
    assert (await second.hello())["reason"] == "role_taken"
    assert bridge.connected("body")


async def test_backwards_seq_closes_connection(
    server: tuple[BridgeServer, list[tuple[str, protocol.Message]]],
) -> None:
    bridge, _ = server
    plugin = await FakePlugin.connect(bridge.port)
    await plugin.hello()
    await plugin.send("chat", {"text": "a"})
    plugin.seq = 0
    await plugin.send("chat", {"text": "b"})
    assert await plugin.closed()
    await asyncio.sleep(0.05)
    assert not bridge.connected("body")


async def test_unknown_message_type_closes_connection(
    server: tuple[BridgeServer, list[tuple[str, protocol.Message]]],
) -> None:
    bridge, _ = server
    plugin = await FakePlugin.connect(bridge.port)
    await plugin.hello()
    await plugin.send_raw({"v": 1, "t": "teleport", "seq": 99, "ts": 1})
    assert await plugin.closed()


async def test_send_to_missing_role_raises(
    server: tuple[BridgeServer, list[tuple[str, protocol.Message]]],
) -> None:
    bridge, _ = server
    with pytest.raises(Exception, match="not connected"):
        await bridge.send("host", protocol.StopAll(seq=0, ts=0, reason="x"))
