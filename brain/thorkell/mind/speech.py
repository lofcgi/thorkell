"""Proactive speech: what Thorkell wants to say, and the limits that keep him from chattering.

Urgency: 3 danger, 2 failure needing help, 1 discovery/realization/milestone, 0 idle social.
Urgent lines (>= 2) skip the rate limits; the rest wait for a free slot and expire if they get stale.
Self-talk (whisper) has its own slower limit.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Line:
    text: str
    urgency: int
    talker: str = "normal"  # whisper = self-talk, normal = to the leader, shout = danger
    topic: str = ""
    ttl_s: float = 30.0
    created: float = field(default_factory=time.monotonic)


@dataclass
class Limits:
    min_gap_s: float = 20.0
    per_window: int = 6
    window_s: float = 600.0
    topic_cooldown_s: float = 300.0
    self_talk_gap_s: float = 60.0


class SpeechQueue:
    def __init__(self, limits: Limits | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.limits = limits or Limits()
        self.clock = clock
        self.queue: list[Line] = []
        self.spoken: list[tuple[float, Line]] = []
        self.dropped: list[Line] = []
        self._topics: dict[str, float] = {}

    def offer(self, line: Line) -> None:
        if line.topic and self.clock() - self._topics.get(line.topic, -1e9) < self.limits.topic_cooldown_s:
            self.dropped.append(line)
            return
        self.queue.append(line)

    def next(self) -> Line | None:
        now = self.clock()
        alive = [line for line in self.queue if now - line.created <= line.ttl_s]
        self.dropped.extend(line for line in self.queue if line not in alive)
        self.queue = sorted(alive, key=lambda line: (-line.urgency, line.created))
        for line in self.queue:
            if self._allowed(line, now):
                self.queue.remove(line)
                self.spoken.append((now, line))
                if line.topic:
                    self._topics[line.topic] = now
                return line
        return None

    def _allowed(self, line: Line, now: float) -> bool:
        if line.urgency >= 2:
            return True
        recent = [
            (t, spoken) for t, spoken in self.spoken if now - t <= self.limits.window_s and spoken.urgency < 2
        ]
        if line.talker == "whisper":
            whispers = [t for t, spoken in recent if spoken.talker == "whisper"]
            return not whispers or now - whispers[-1] >= self.limits.self_talk_gap_s
        normal = [t for t, spoken in recent if spoken.talker != "whisper"]
        if len(normal) >= self.limits.per_window:
            return False
        return not normal or now - normal[-1] >= self.limits.min_gap_s
