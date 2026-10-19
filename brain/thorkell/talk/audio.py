"""Microphone (16 kHz PCM16 mono, 20 ms frames) and speaker (24 kHz PCM16 mono) via sounddevice.

Errors opening devices (e.g. macOS microphone permission denied for the terminal) are raised with a
Korean hint; nothing falls back to "no audio" silently.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import numpy as np
import sounddevice as sd

from thorkell.lang import tr

MIC_RATE = 16000
SPEAKER_RATE = 24000
FRAME_MS = 20


class AudioError(Exception):
    pass


class Mic:
    def __init__(self, queue: asyncio.Queue[bytes], loop: asyncio.AbstractEventLoop) -> None:
        self.queue = queue
        self.loop = loop
        self.overruns = 0
        self._stream: Any = None

    def start(self) -> None:
        def callback(indata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags) -> None:
            if status.input_overflow:
                self.overruns += 1
            self.loop.call_soon_threadsafe(self.queue.put_nowait, bytes(indata))

        try:
            self._stream = sd.InputStream(
                samplerate=MIC_RATE,
                channels=1,
                dtype="int16",
                blocksize=MIC_RATE * FRAME_MS // 1000,
                callback=callback,
            )
            self._stream.start()
        except sd.PortAudioError as error:
            raise AudioError(
                tr(
                    f"마이크를 열 수 없어요({error}). "
                    "시스템 설정 → 개인정보 보호 및 보안 → 마이크에서 터미널 앱을 허용하세요.",
                    f"Can't open the microphone ({error}). "
                    "Allow your terminal app in System Settings → Privacy & Security → Microphone.",
                )
            ) from error

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.close()


class SoundSpeaker:
    """Plays model audio as it streams; flush() drops what's buffered (barge-in)."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stream: Any = None

    def start(self) -> None:
        def callback(outdata: np.ndarray, frames: int, time: Any, status: sd.CallbackFlags) -> None:
            wanted = frames * 2
            with self._lock:
                chunk = bytes(self._buffer[:wanted])
                del self._buffer[:wanted]
            outdata[:] = np.frombuffer(chunk.ljust(wanted, b"\0"), dtype=np.int16).reshape(-1, 1)

        try:
            self._stream = sd.OutputStream(
                samplerate=SPEAKER_RATE, channels=1, dtype="int16", callback=callback
            )
            self._stream.start()
        except sd.PortAudioError as error:
            raise AudioError(
                tr(f"스피커를 열 수 없어요({error}).", f"Can't open the speaker ({error}).")
            ) from error

    def play(self, pcm: bytes) -> None:
        with self._lock:
            self._buffer.extend(pcm)

    def flush(self) -> None:
        with self._lock:
            self._buffer.clear()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.close()
