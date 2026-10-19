"""Build the live voice (mic + speaker + Gemini Live) for a running brain."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, cast

from google import genai
from google.genai import types

from thorkell.config import VoiceSettings, secret
from thorkell.control.controller import Controller
from thorkell.decide.runner import DecisionRunner
from thorkell.talk.audio import Mic, SoundSpeaker
from thorkell.talk.live import LiveSession, LiveVoice, VoiceConfig
from thorkell.talk.router import SpeechRouter
from thorkell.talk.tools import ToolBridge


def build_voice(
    settings: VoiceSettings, controller: Controller, decider: DecisionRunner | None, handle_path: Path
) -> tuple[LiveVoice, Mic, SoundSpeaker]:
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
    speaker = SoundSpeaker()
    voice: LiveVoice

    def last_words() -> str:
        return voice.leader_words

    def connect(model: str, config: dict[str, Any]) -> AbstractAsyncContextManager[LiveSession]:
        # SDK의 AsyncSession은 LiveSession 프로토콜(send_* / receive)을 만족한다.
        live_config = types.LiveConnectConfig.model_validate(config)
        return cast(
            AbstractAsyncContextManager[LiveSession], client.aio.live.connect(model=model, config=live_config)
        )

    voice = LiveVoice(
        connect=connect,
        tools=ToolBridge(controller, decider, last_words),
        speaker=speaker,
        mic=frames,
        config=VoiceConfig(
            model=settings.model,
            voice=settings.voice,
            silence_ms=settings.silence_ms,
            handle_path=handle_path,
        ),
    )
    controller.say = SpeechRouter(controller.session, voice).say
    mic = Mic(frames, asyncio.get_running_loop())
    return voice, mic, speaker
