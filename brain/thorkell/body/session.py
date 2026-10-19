"""Brain-side view of one connected body: latest observations, events, and command round-trips.

Every command gets exactly one ack and, if accepted, exactly one result (Body guarantees it);
`command()` turns that into an awaitable. Timeouts are errors, not silent defaults.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from thorkell.body import protocol
from thorkell.body.link import BridgeServer

log = logging.getLogger(__name__)


class CommandRejected(Exception):
    def __init__(self, op: str, code: str) -> None:
        super().__init__(f"{op} rejected: {code}")
        self.op = op
        self.code = code


@dataclass
class _Pending:
    op: str
    ack: asyncio.Future[protocol.Ack]
    result: asyncio.Future[protocol.Result]
    progress: list[dict[str, Any]] = field(default_factory=list)


class BodySession:
    ROLE = "body"

    def __init__(self) -> None:
        self.state: protocol.State | None = None
        self.scene: protocol.Scene | None = None
        self.status: protocol.Status | None = None
        self.events: list[protocol.Event] = []
        self.event_listeners: list[Callable[[protocol.Event], None]] = []
        self._pending: dict[str, _Pending] = {}
        self._ids = itertools.count(1)
        self._server: BridgeServer | None = None
        self._changed = asyncio.Event()
        self._abandoned: set[str] = set()

    def attach(self, server: BridgeServer) -> None:
        self._server = server

    async def on_message(self, role: str, message: protocol.Message) -> None:
        if role != self.ROLE:
            return
        match message:
            case protocol.State():
                self.state = message
            case protocol.Scene():
                self.scene = message
            case protocol.Status():
                self.status = message
            case protocol.Event():
                self.events.append(message)
                for listener in self.event_listeners:
                    listener(message)
            case protocol.Ack():
                pending = self._pending.get(message.cmd_id)
                if pending is None:
                    raise LookupError(f"ack for unknown command {message.cmd_id}")
                if pending.ack.done():
                    return
                pending.ack.set_result(message)
                if not message.accepted:
                    del self._pending[message.cmd_id]
            case protocol.Progress():
                pending = self._pending.get(message.cmd_id)
                if pending is not None:
                    pending.progress.append(message.metrics)
            case protocol.Result():
                pending = self._pending.pop(message.cmd_id, None)
                if pending is None:
                    raise LookupError(f"result for unknown command {message.cmd_id}")
                if message.cmd_id in self._abandoned:
                    self._abandoned.discard(message.cmd_id)
                elif not pending.result.done():
                    pending.result.set_result(message)
            case protocol.QueryResult():
                if message.id in self._abandoned:
                    self._abandoned.discard(message.id)  # 기다리다 만 질의의 늦은 답
                    return
                pending = self._pending.pop(message.id, None)
                if pending is None:
                    raise LookupError(f"query_result for unknown query {message.id}")
                pending.result.set_result(message)  # type: ignore[arg-type]
            case _:
                raise LookupError(f"unexpected {message.t} from body")
        self._changed.set()

    async def wait_for(self, predicate: Callable[[], bool], timeout: float) -> None:
        async with asyncio.timeout(timeout):
            while not predicate():
                self._changed.clear()
                await self._changed.wait()

    @property
    def armed(self) -> bool:
        return self.status is not None and self.status.armed

    async def command(
        self,
        op: str,
        args: dict[str, Any],
        *,
        timeout: float = 30.0,
        mode: str = "replace",
        ttl_ms: int = 2000,
    ) -> protocol.Result:
        if self._server is None:
            raise RuntimeError("session not attached to a bridge server")
        cmd_id = f"c{next(self._ids)}"
        loop = asyncio.get_running_loop()
        pending = _Pending(op=op, ack=loop.create_future(), result=loop.create_future())
        self._pending[cmd_id] = pending
        based_on = self.scene.seq if self.scene is not None else 0
        await self._server.send(
            self.ROLE,
            protocol.Command(
                seq=0,
                ts=0,
                id=cmd_id,
                op=op,
                args=args,
                mode=mode,  # type: ignore[arg-type]
                based_on_seq=based_on,
                ttl_ms=ttl_ms,
            ),
        )
        try:
            async with asyncio.timeout(timeout):
                ack = await pending.ack
                if not ack.accepted:
                    raise CommandRejected(op, ack.code)
                result = await pending.result
                if result.status == "failed":
                    # 몸이 못 한 일은 두뇌 기록에 남긴다(왜 멈췄는지 밖에서 읽을 수 있게).
                    log.info("%s %s failed: %s %s", op, args, result.code, result.evidence)
                return result
        except asyncio.CancelledError:
            await self._abandon(cmd_id)
            raise
        except TimeoutError as error:
            await self._abandon(cmd_id)
            # 시간 초과는 기다리던 퓨처를 취소한다. 취소된 ack는 받지 못한 것이다.
            acked = pending.ack.done() and not pending.ack.cancelled()
            waited = "result" if acked else "ack"
            raise TimeoutError(f"{op} {cmd_id}: no {waited} in {timeout:g}s (args {args})") from error

    async def _abandon(self, cmd_id: str) -> None:
        """A command the brain gave up on stops in the body too. Its result (cancelled) is ignored if it
        arrives later."""
        assert self._server is not None
        if cmd_id in self._pending and self._server.connected(self.ROLE):
            self._abandoned.add(cmd_id)
            await self._server.send(
                self.ROLE, protocol.Cancel(seq=0, ts=0, cmd_id=cmd_id, reason="abandoned")
            )

    async def stop_all(self, reason: str) -> None:
        if self._server is None:
            raise RuntimeError("session not attached to a bridge server")
        # 진행 중·대기 명령은 몸이 cancelled 결과로 닫아 주므로 기다리던 쪽도 정상적으로 깨어난다.
        await self._server.send(self.ROLE, protocol.StopAll(seq=0, ts=0, reason=reason))

    async def query(self, what: str, args: dict[str, Any], timeout: float = 5.0) -> protocol.QueryResult:
        if self._server is None:
            raise RuntimeError("session not attached to a bridge server")
        query_id = f"q{next(self._ids)}"
        loop = asyncio.get_running_loop()
        pending = _Pending(op=what, ack=loop.create_future(), result=loop.create_future())
        self._pending[query_id] = pending
        await self._server.send(self.ROLE, protocol.Query(seq=0, ts=0, id=query_id, what=what, args=args))
        try:
            async with asyncio.timeout(timeout):
                result = await pending.result
        except (TimeoutError, asyncio.CancelledError):
            # 답이 나중에 오면 버린다(몸은 질의를 끝까지 처리해서 답한다).
            self._pending.pop(query_id, None)
            self._abandoned.add(query_id)
            raise
        assert isinstance(result, protocol.QueryResult)
        return result

    def nearby(self, kind: str | None = None) -> list[dict[str, Any]]:
        if self.scene is None:
            return []
        entries: list[dict[str, Any]] = self.scene.data.get("nearby", [])
        return [e for e in entries if kind is None or e.get("kind") == kind]

    def inventory(self) -> list[dict[str, Any]]:
        if self.scene is None:
            return []
        items: list[dict[str, Any]] = self.scene.data.get("inventory", [])
        return items

    def events_of(self, kind: str) -> list[protocol.Event]:
        return [e for e in self.events if e.kind == kind]
