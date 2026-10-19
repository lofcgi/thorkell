"""Bridge server: the brain listens on loopback; Thorkell.Body and Thorkell.Host connect to it.

One connection per role. Handshake: challenge -> hello (HMAC) -> welcome | reject.
Protocol violations close the connection loudly; nothing is silently dropped.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from thorkell.body import auth, protocol

log = logging.getLogger(__name__)

HELLO_TIMEOUT_S = 5.0

MessageHandler = Callable[[str, protocol.Message], Awaitable[None]]
ConnectionHandler = Callable[[str, bool], Awaitable[None]]


@dataclass
class _Peer:
    role: str
    session: str
    writer: asyncio.StreamWriter
    send_seq: int = 0
    recv_seq: int = -1
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class LinkError(Exception):
    pass


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


class BridgeServer:
    def __init__(
        self,
        token_hex: str,
        on_message: MessageHandler,
        on_connection: ConnectionHandler | None = None,
        accepted_caps: tuple[str, ...] = ("observe", "move", "act", "say"),
        state_hz: int = 10,
        scene_hz: int = 2,
    ) -> None:
        self._token = token_hex
        self._on_message = on_message
        self._on_connection = on_connection
        self._accepted_caps = accepted_caps
        self._state_hz = state_hz
        self._scene_hz = scene_hz
        self._peers: dict[str, _Peer] = {}
        self._server: asyncio.Server | None = None

    @property
    def listening(self) -> bool:
        return self._server is not None

    @property
    def port(self) -> int:
        if self._server is None:
            raise LinkError("server not started")
        port: int = self._server.sockets[0].getsockname()[1]
        return port

    def connected(self, role: str) -> bool:
        return role in self._peers

    async def start(self, port: int) -> None:
        self._server = await asyncio.start_server(
            self._handle, "127.0.0.1", port, limit=protocol.MAX_LINE_BYTES + 2
        )

    async def close(self) -> None:
        for peer in list(self._peers.values()):
            peer.writer.close()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def send(self, role: str, message: protocol.Message) -> None:
        peer = self._peers.get(role)
        if peer is None:
            raise LinkError(f"{role} is not connected")
        await self._write(peer, message)

    async def _write(self, peer: _Peer, message: protocol.Message) -> None:
        async with peer.lock:
            peer.send_seq += 1
            stamped = message.model_copy(update={"seq": peer.send_seq, "ts": _now_ms()})
            peer.writer.write((protocol.encode(stamped) + "\n").encode("utf-8"))
            await peer.writer.drain()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        address = writer.get_extra_info("peername")
        if address is None or not ipaddress.ip_address(address[0]).is_loopback:
            log.error("bridge: refusing non-loopback peer %s", address)
            writer.close()
            return

        role: str | None = None
        try:
            role = await self._handshake(reader, writer)
            await self._serve(self._peers[role], reader)
        except (LinkError, protocol.ProtocolError) as error:
            log.error("bridge: %s connection closed: %s", role or "unauthenticated", error)
        except (ConnectionError, asyncio.IncompleteReadError) as error:
            log.warning("bridge: %s disconnected: %s", role or "unauthenticated", error)
        finally:
            if role is not None and self._peers.get(role) is not None and self._peers[role].writer is writer:
                del self._peers[role]
                if self._on_connection is not None:
                    await self._on_connection(role, False)
            writer.close()

    async def _handshake(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> str:
        nonce = auth.new_hex(16)
        challenge = protocol.Challenge(seq=1, ts=_now_ms(), nonce=nonce)
        writer.write((protocol.encode(challenge) + "\n").encode("utf-8"))
        await writer.drain()

        line = await asyncio.wait_for(reader.readline(), HELLO_TIMEOUT_S)
        if not line:
            raise ConnectionError("closed before hello")
        hello = protocol.decode(line.decode("utf-8").rstrip("\r\n"))
        if not isinstance(hello, protocol.Hello):
            raise LinkError(f"expected hello, got {hello.t}")

        reason = None
        if hello.proto[0] != protocol.MAJOR:
            reason = "major_mismatch"
        elif not auth.verify(self._token, nonce, hello.role, hello.session, hello.mac):
            reason = "bad_mac"
        elif hello.role in self._peers:
            reason = "role_taken"
        if reason is not None:
            reject = protocol.Reject(seq=2, ts=_now_ms(), reason=reason)
            writer.write((protocol.encode(reject) + "\n").encode("utf-8"))
            await writer.drain()
            raise LinkError(f"rejected {hello.role}: {reason}")

        peer = _Peer(role=hello.role, session=hello.session, writer=writer, send_seq=1, recv_seq=hello.seq)
        self._peers[hello.role] = peer
        caps = tuple(c for c in hello.caps if c in self._accepted_caps)
        await self._write(
            peer,
            protocol.Welcome(
                seq=0, ts=0, accepted_caps=caps, state_hz=self._state_hz, scene_hz=self._scene_hz
            ),
        )
        log.info("bridge: %s connected (game %s, session %s)", hello.role, hello.game.version, hello.session)
        if self._on_connection is not None:
            await self._on_connection(hello.role, True)
        return hello.role

    async def _serve(self, peer: _Peer, reader: asyncio.StreamReader) -> None:
        while True:
            try:
                line = await reader.readline()
            except (ValueError, asyncio.LimitOverrunError) as error:
                raise protocol.ProtocolError("line_too_long", str(error)) from error
            if not line:
                return
            text = line.decode("utf-8").rstrip("\r\n")
            if not text:
                continue
            message = protocol.decode(text)
            if message.seq <= peer.recv_seq:
                raise LinkError(f"{peer.role} seq went backwards: {message.seq} after {peer.recv_seq}")
            peer.recv_seq = message.seq
            await self._on_message(peer.role, message)
