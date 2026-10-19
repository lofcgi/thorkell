"""README video: record one game window (the bot's, a normal 1280x720 window while recording).

The recorder (tools/record/window-recorder.swift, ScreenCaptureKit) captures that window's own content, never
the rest of the screen. The screen-recording permission belongs to the app that runs this (System Settings >
Privacy & Security).
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from thorkell.paths import REPO_ROOT

VIDEO_W, VIDEO_H = 1280, 720
FPS = 30


class RecordingError(Exception):
    pass


def _helper(name: str, library: bool = False) -> Path:
    """Compile tools/record/<name>.swift once (into artifacts/) and return the binary."""
    source = REPO_ROOT / "tools/record" / f"{name}.swift"
    binary = REPO_ROOT / "artifacts" / f"record-{name}"
    if not binary.is_file() or binary.stat().st_mtime < source.stat().st_mtime:
        binary.parent.mkdir(parents=True, exist_ok=True)
        flags = ["-parse-as-library"] if library else []
        subprocess.run(["xcrun", "swiftc", "-O", *flags, "-o", str(binary), str(source)], check=True)
    return binary


class WindowRecording:
    """Records only the game window's own content (ScreenCaptureKit), so nothing else on the screen is kept
    even if another window covers it. An earlier version recorded the window's area of the screen and caught
    the user's own windows lying on top (2026-10-20).

    The system sometimes stops the stream on its own (after 110 s in a real run); recording then goes on in
    a new file. `segments` holds (file, wall-clock start) for each; `on_segment` hears about each one."""

    def __init__(self, pid: int, out: Path, on_segment: Callable[[Path, float], None] | None = None) -> None:
        self.pid = pid
        self.out = out
        self.on_segment = on_segment
        self.segments: list[tuple[Path, float]] = []
        self.process: subprocess.Popen[str] | None = None
        self.keeper: asyncio.Task[None] | None = None
        self.stopping = False

    @property
    def started_at(self) -> float | None:
        return self.segments[0][1] if self.segments else None

    async def start(self, timeout: float = 90) -> None:
        self.out.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while not await self._segment():
            if time.monotonic() > deadline:
                raise RecordingError(f"could not record the window of pid {self.pid}; see recorder.log")
            await asyncio.sleep(2)
        self.keeper = asyncio.create_task(self._keep())

    async def _segment(self) -> bool:
        path = (
            self.out if not self.segments else self.out.with_name(f"{self.out.stem}-{len(self.segments)}.mp4")
        )
        self.process = subprocess.Popen(
            [str(_helper("window-recorder", library=True)), str(self.pid), str(path), str(FPS)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(self.out.parent / "recorder.log").open("a"),
            text=True,
        )
        assert self.process.stdout is not None
        line = await asyncio.to_thread(self.process.stdout.readline)
        if not line.startswith("started "):
            self.process.wait()
            return False
        self.segments.append((path, float(line.split()[1])))
        if self.on_segment is not None:
            self.on_segment(path, self.segments[-1][1])
        return True

    async def _keep(self) -> None:
        while not self.stopping:
            assert self.process is not None
            await asyncio.to_thread(self.process.wait)
            if self.stopping:
                return
            assert self.process.stdout is not None
            why = self.process.stdout.read().strip()
            with (self.out.parent / "recorder.log").open("a") as log:
                log.write(f"{time.strftime('%H:%M:%S')} segment ended ({self.process.returncode}): {why}\n")
            # 시스템이 스트림을 끊었다. 창이 아직 있으면 새 파일로 이어 간다.
            await asyncio.sleep(1)
            while not self.stopping and not await self._segment():
                await asyncio.sleep(2)

    async def stop(self) -> None:
        self.stopping = True
        if self.process is not None and self.process.poll() is None:
            assert self.process.stdin is not None
            self.process.stdin.write("q\n")
            self.process.stdin.flush()
            for _ in range(40):
                if self.process.poll() is not None:
                    break
                await asyncio.sleep(0.5)
            else:
                self.process.terminate()
        if self.keeper is not None:
            await asyncio.gather(self.keeper, return_exceptions=True)
