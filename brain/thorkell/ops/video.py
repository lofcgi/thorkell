"""`thorkell video <run artifacts>`: the README video from a recorded scenario run.

Input: thorkell.mp4 (the bot's window) and timeline.jsonl (when the video started, each step's start and end,
who said what). Output in <run>/video: captioned.mp4 (every line as a caption, like game chat) and one GIF per
step, where the moments around each line play at normal speed and the long stretches between them run fast.
This ffmpeg has no text filters, so captions are PNGs drawn by tools/record/caption.swift and overlaid.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thorkell.ops.recording import VIDEO_W, _helper

GAMMA = 1.6
CAPTION_S = 4.5  # 한 줄을 보여 주는 시간(다음 줄이 오면 그때까지)
AROUND_S = (1.5, 5.0)  # GIF에서 말 앞뒤로 제 속도로 보여 줄 구간
GAP_OUT_S = 3.0  # 말 사이의 긴 구간은 이만큼으로 빨리 감는다
# README에 넣을 GIF: 이 크기를 넘으면 더 작게(폭, 초당 프레임) 다시 만든다.
GIF_SIZES = ((480, 8), (400, 6), (320, 6))
GIF_MAX_BYTES = 8_000_000
GIF_MAX_S = 25.0  # README에 넣을 수 있게 GIF 하나는 이만큼을 넘지 않게 빨리 감는다
ROW_H = 70  # 겹친 자막은 한 줄씩 위로 쌓는다


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    who: str
    text: str


class Clock:
    """Wall-clock time to time in the joined video. Recording can come in several files (the system stops the
    stream now and then); what happened between two files is not in the video and maps to the next file."""

    def __init__(self, segments: list[tuple[float, float]]) -> None:
        self.segments = segments  # (wall-clock start, duration), in order

    def covers(self, at: float) -> bool:
        start, _ = self.segments[0]
        last, duration = self.segments[-1]
        return start <= at < last + duration

    def __call__(self, at: float) -> float:
        offset = 0.0
        for start, duration in self.segments:
            if at < start:
                return offset
            if at < start + duration:
                return offset + at - start
            offset += duration
        return offset


def captions(timeline: list[dict[str, Any]], clock: Clock) -> list[Caption]:
    said = sorted((e for e in timeline if e["kind"] == "said"), key=lambda e: e["at"])
    out = []
    for index, entry in enumerate(said):
        if not clock.covers(entry["at"]):
            continue
        start = clock(entry["at"])
        end = start + CAPTION_S
        if index + 1 < len(said):
            end = min(end, max(start + 1.5, clock(said[index + 1]["at"])))
        out.append(Caption(round(start, 2), round(end, 2), entry["who"], entry["text"]))
    return out


def _duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return float(out.strip())


def burn(segments: Path, lines: list[Caption], work: Path, out: Path) -> None:
    """Overlay each caption PNG at the bottom of the picture while it is said. `segments` lists the
    recorded files in order (ffmpeg concat); they are read in place, without a joined copy."""
    work.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    # 게임 첫날 새벽 숲은 화면이 어둡다. 영상만 밝혀서 보이게 한다(자막은 그대로).
    chain: list[str] = [f"[0:v]eq=gamma={GAMMA}[lit]"]
    last = "lit"
    for index, line in enumerate(lines, start=1):
        png = work / f"caption-{index:03d}.png"
        subprocess.run([str(_helper("caption")), str(png), str(VIDEO_W), line.who, line.text], check=True)
        inputs += ["-i", str(png)]
        y = f"H-h-{24 + _row(lines, index - 1) * ROW_H}"
        shown = f"between(t,{line.start},{line.end})"
        chain.append(f"[{last}][{index}:v]overlay=0:{y}:enable='{shown}'[v{index}]")
        last = f"v{index}"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(segments),
    ]
    command += inputs
    command += ["-filter_complex", ";".join(chain), "-map", f"[{last}]"]
    command += ["-c:v", "h264_videotoolbox", "-b:v", "4M", "-pix_fmt", "yuv420p", "-y", str(out)]
    subprocess.run(command, check=True)


def _row(lines: list[Caption], index: int) -> int:
    """The lowest row free while this line shows (lines said at the same time stack up)."""
    taken = {_row(lines, i) for i in range(index) if lines[i].end > lines[index].start}
    return next(row for row in range(len(lines)) if row not in taken)


def pieces(start: float, end: float, lines: list[Caption]) -> list[tuple[float, float, float]]:
    """(from, to, speed) covering [start, end]: normal speed around each line, fast in between."""
    keep: list[list[float]] = []
    for line in lines:
        if line.end < start or line.start > end:
            continue
        a, b = max(start, line.start - AROUND_S[0]), min(end, line.start + AROUND_S[1])
        if keep and a <= keep[-1][1]:
            keep[-1][1] = max(keep[-1][1], b)
        else:
            keep.append([a, b])
    out: list[tuple[float, float, float]] = []
    cursor = start
    for a, b in keep:
        if a - cursor > 0.5:
            out.append((cursor, a, max(1.0, (a - cursor) / GAP_OUT_S)))
        out.append((a, b, 1.0))
        cursor = b
    if end - cursor > 0.5:
        out.append((cursor, end, max(1.0, (end - cursor) / GAP_OUT_S)))
    length = sum((b - a) / speed for a, b, speed in out)
    if length > GIF_MAX_S:
        out = [(a, b, speed * length / GIF_MAX_S) for a, b, speed in out]
    return out


def gif(video: Path, parts: list[tuple[float, float, float]], out: Path) -> None:
    for width, fps in GIF_SIZES:
        _gif(video, parts, out, width, fps)
        if out.stat().st_size <= GIF_MAX_BYTES:
            return


def _gif(video: Path, parts: list[tuple[float, float, float]], out: Path, width: int, fps: int) -> None:
    filters = []
    for index, (a, b, speed) in enumerate(parts):
        filters.append(f"[0:v]trim=start={a:.2f}:end={b:.2f},setpts=(PTS-STARTPTS)/{speed:.3f}[p{index}]")
    joined = "".join(f"[p{i}]" for i in range(len(parts)))
    filters.append(
        f"{joined}concat=n={len(parts)}:v=1:a=0,fps={fps},scale={width}:-1:flags=lanczos,split[a][b]"
    )
    filters.append("[a]palettegen=stats_mode=diff[pal];[b][pal]paletteuse=dither=bayer:bayer_scale=4")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    command += ["-filter_complex", ";".join(filters), "-loop", "0", "-y", str(out)]
    subprocess.run(command, check=True)


def build(run: Path) -> list[Path]:
    timeline = [
        json.loads(line) for line in (run / "timeline.jsonl").read_text().splitlines() if line.strip()
    ]
    files, durations = [], []
    for entry in sorted((e for e in timeline if e["kind"] == "video"), key=lambda e: e["start"]):
        path = run / entry.get("file", "thorkell.mp4")
        try:
            durations.append(_duration(path))
        except (subprocess.CalledProcessError, ValueError) as error:
            # 녹화 중 디스크가 차는 등으로 끝맺지 못한 조각. 빼고 무엇을 뺐는지 알린다.
            print(f"skipping unreadable recording {path.name}: {error}", file=sys.stderr)
            continue
        files.append(entry)
    clock = Clock([(e["start"], d) for e, d in zip(files, durations, strict=True)])
    out = run / "video"
    out.mkdir(parents=True, exist_ok=True)
    listing = out / "segments.txt"
    listing.write_text("".join(f"file '{(run / e.get('file', 'thorkell.mp4')).resolve()}'\n" for e in files))
    duration = sum(durations)
    lines = captions(timeline, clock)
    captioned = out / "captioned.mp4"
    burn(listing, lines, out / "captions", captioned)
    made = [captioned]
    steps = [e for e in timeline if e["kind"] == "step"]
    for number, step in enumerate(steps, start=1):
        start, end = clock(step["start"]), min(duration, clock(step["end"]))
        if end - start < 2:
            continue
        target = out / f"{number:02d}-{step['name']}.gif"
        gif(captioned, pieces(start, end, lines), target)
        made.append(target)
    return made
