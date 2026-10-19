"""Who has the conversational floor. Non-urgent speech waits for IDLE; urgent speech may cut in.

`turn_complete=True` injections interrupt the model's own generation, so they are only sent when the
floor is idle (or the line is urgent).
"""

from __future__ import annotations

import time
from collections.abc import Callable

USER, MODEL, IDLE = "user_speaking", "model_speaking", "idle"


class Floor:
    def __init__(self, idle_after_s: float = 1.5, clock: Callable[[], float] = time.monotonic) -> None:
        self.idle_after_s = idle_after_s
        self.clock = clock
        self._user_at = -1e9
        self._model_at = -1e9

    def user_activity(self) -> None:
        self._user_at = self.clock()

    def model_activity(self) -> None:
        self._model_at = self.clock()

    def state(self) -> str:
        now = self.clock()
        user = now - self._user_at < self.idle_after_s
        model = now - self._model_at < self.idle_after_s
        if user and (not model or self._user_at >= self._model_at):
            return USER
        if model:
            return MODEL
        return IDLE

    def idle(self) -> bool:
        return self.state() == IDLE
