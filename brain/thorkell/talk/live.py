"""Korean voice conversation through gemini-3.8-live.

One session at a time. Mic frames (16 kHz PCM16) stream in, the model's audio (24 kHz PCM16) streams
out, tool calls go to the ToolBridge, and the resumption handle is kept so a GoAway (connection ends
after ~10 min) reconnects into the same conversation. If resuming fails the voice goes "down" loudly;
body control keeps running and reconnecting is an explicit action — no silent fresh session.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from google.genai import types

from thorkell import lang
from thorkell.lang import tr
from thorkell.talk.floor import Floor
from thorkell.talk.tools import ToolBridge, declarations

log = logging.getLogger(__name__)

PERSONA = """너는 Thorkell, Valheim을 처음 해 보는 바이킹 동료다. 리더(사용자)와 친구처럼 반말로 짧게 말한다.
- 게임을 미리 아는 척하지 않는다. 게임에 대해서는 recall_knowledge로 찾은 것과
  직접 본 것만 말한다. 모르면 모른다고 한다.
- 일을 시키면 set_goal을 부르고, 결과가 accepted일 때만 "할게"라고 말한다. 멈추라면 cancel.
- 지금 뭐 하냐고 물으면 ask_status. 리더가 게임 사실을 알려 주면 teach_fact.
- "[게임 이벤트]"로 시작하는 입력은 게임에서 일어난 일이다. 필요할 때만 짧게 반응한다.
- "[Thorkell이 할 말]"로 시작하면 그 뜻을 네 말투로 리더에게 한두 문장으로 전한다."""

PERSONA_EN = """You are Thorkell, a Viking companion playing Valheim for the first time. Talk with the leader
(the user) like a friend: casual, short, in English.
- Don't act like you already know the game. About the game, say only what recall_knowledge finds and
  what you saw yourself. If you don't know, say you don't know.
- When asked to do something, call set_goal, and say "I'll do it" only when the result is accepted.
  To stop, cancel.
- When asked what you're doing, ask_status. When the leader tells you a fact about the game, teach_fact.
- Input starting with "[Game event]" is something that happened in the game. React briefly, only when needed.
- Input starting with "[Thorkell says]": tell the leader what it means in your own words, in one or two
  sentences."""


def persona() -> str:
    """The voice model's instructions in the language being played."""
    return PERSONA_EN if lang.current() == "en" else PERSONA


class Speaker(Protocol):
    def play(self, pcm: bytes) -> None: ...
    def flush(self) -> None: ...


class LiveSession(Protocol):
    async def send_realtime_input(self, *, audio: types.Blob) -> None: ...
    async def send_client_content(self, *, turns: list[dict[str, Any]], turn_complete: bool) -> None: ...
    async def send_tool_response(self, *, function_responses: list[types.FunctionResponse]) -> None: ...
    def receive(self) -> AsyncIterator[types.LiveServerMessage]: ...


Connect = Callable[[str, dict[str, Any]], AbstractAsyncContextManager[LiveSession]]


@dataclass
class VoiceConfig:
    model: str = "gemini-3.8-live"
    voice: str = "Kore"
    silence_ms: int = 600
    handle_path: Path | None = None


@dataclass
class LiveVoice:
    connect: Connect
    tools: ToolBridge
    speaker: Speaker
    mic: asyncio.Queue[bytes]
    config: VoiceConfig = field(default_factory=VoiceConfig)
    floor: Floor = field(default_factory=Floor)
    on_transcript: Callable[[str, str], None] | None = None
    on_down: Callable[[str], None] | None = None

    def __post_init__(self) -> None:
        self.status = "down"
        self.handle: str | None = self._load_handle()
        self.session: LiveSession | None = None
        self.leader_words = ""

    # --- lifecycle -------------------------------------------------------------------------------
    def connect_config(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "response_modalities": ["AUDIO"],
            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": self.config.voice}}},
            "system_instruction": persona(),
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "realtime_input_config": {
                "automatic_activity_detection": {"silence_duration_ms": self.config.silence_ms}
            },
            "context_window_compression": {"sliding_window": {}},
            "session_resumption": {"handle": self.handle} if self.handle else {},
            "tools": [{"function_declarations": declarations()}],
        }
        return config

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            resuming = self.handle is not None
            self.status = "connecting"
            try:
                async with self.connect(self.config.model, self.connect_config()) as session:
                    self.session = session
                    self.status = "up"
                    reason = await self._serve(session, stop)
            except Exception as error:
                what = tr(
                    f"{'세션 재개' if resuming else '연결'} 실패",
                    "session resume failed" if resuming else "connection failed",
                )
                self._down(f"{what}: {type(error).__name__}: {error}")
                return
            finally:
                self.session = None
            if reason != "go_away":
                self.status = "down"
                return
            log.info("live: GoAway, reconnecting with resumption handle")

    def _down(self, why: str) -> None:
        self.status = "down"
        log.error("live voice down: %s", why)
        if self.on_down is not None:
            self.on_down(why)

    async def _serve(self, session: LiveSession, stop: asyncio.Event) -> str:
        pump = asyncio.create_task(self._pump_mic(session))
        try:
            while not stop.is_set():
                async for message in session.receive():
                    outcome = await self._handle(session, message)
                    if outcome == "go_away":
                        return "go_away"
            return "stopped"
        finally:
            pump.cancel()

    async def _pump_mic(self, session: LiveSession) -> None:
        while True:
            frame = await self.mic.get()
            await session.send_realtime_input(audio=types.Blob(data=frame, mime_type="audio/pcm;rate=16000"))

    # --- messages from the model -----------------------------------------------------------------
    async def _handle(self, session: LiveSession, message: types.LiveServerMessage) -> str | None:
        content = message.server_content
        if content is not None:
            if content.model_turn is not None:
                for part in content.model_turn.parts or []:
                    if part.inline_data is not None and part.inline_data.data:
                        self.floor.model_activity()
                        self.speaker.play(part.inline_data.data)
            if content.output_transcription is not None and content.output_transcription.text:
                self.floor.model_activity()
                self._transcript("thorkell", content.output_transcription.text)
            if content.input_transcription is not None and content.input_transcription.text:
                self.floor.user_activity()
                self.leader_words = content.input_transcription.text
                self._transcript("leader", content.input_transcription.text)
            if content.interrupted:
                self.speaker.flush()
        if message.tool_call is not None:
            responses = []
            for call in message.tool_call.function_calls or []:
                response, scheduling = await self.tools.call(call.name or "", dict(call.args or {}))
                responses.append(
                    types.FunctionResponse(
                        id=call.id,
                        name=call.name,
                        response=response,
                        scheduling=types.FunctionResponseScheduling(scheduling),
                    )
                )
            await session.send_tool_response(function_responses=responses)
        update = message.session_resumption_update
        if update is not None and update.resumable and update.new_handle:
            self.handle = update.new_handle
            self._save_handle()
        if message.go_away is not None:
            return "go_away"
        return None

    def _transcript(self, who: str, text: str) -> None:
        if self.on_transcript is not None:
            self.on_transcript(who, text)

    # --- things Thorkell wants to say ------------------------------------------------------------
    async def inject(self, text: str, *, speak: bool, urgent: bool = False) -> bool:
        """Context-only (speak=False) never interrupts. speak=True needs an idle floor unless urgent,
        because turn_complete=True cuts the model's own generation. Returns False if not sent now."""
        if self.session is None or self.status != "up":
            return False
        if speak and not urgent and not self.floor.idle():
            return False
        label = tr("[Thorkell이 할 말]", "[Thorkell says]") if speak else tr("[게임 이벤트]", "[Game event]")
        await self.session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": f"{label} {text}"}]}], turn_complete=speak
        )
        return True

    # --- resumption handle (0600 file) -----------------------------------------------------------
    def _load_handle(self) -> str | None:
        path = self.config.handle_path
        if path is None or not path.is_file():
            return None
        handle = path.read_text().strip()
        return handle or None

    def _save_handle(self) -> None:
        path = self.config.handle_path
        if path is None or self.handle is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(self.handle)
