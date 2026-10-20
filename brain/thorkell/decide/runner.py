"""Asking decision points: deadline, circuit breaker, and a JSONL log for later laya distillation.

Backends are chosen per point by config (`jev`, `laya`, or `rules`) and never switch on their own.
The log keeps only what a distilled model may see (state text + questions) plus the answer and
latency; outcomes are joined later by a separate script and never become model inputs.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx

from thorkell.decide.points import Point
from thorkell.models.systemone import Answer, SystemOne, SystemOneError

Status = Literal["ok", "timeout", "error", "breaker_open"]


@dataclass(frozen=True)
class Decided:
    point: str
    status: Status
    answers: dict[str, Answer] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None

    def choice(self, question: str) -> str | None:
        answer = self.answers.get(question)
        return answer.choice if answer is not None else None


class Decider(Protocol):
    name: str

    async def decide(self, point: Point, state: str, context: dict[str, Any]) -> dict[str, Answer]: ...


class SystemOneDecider:
    def __init__(self, one: SystemOne) -> None:
        self.one = one
        self.name = one.backend.name

    async def decide(self, point: Point, state: str, context: dict[str, Any]) -> dict[str, Answer]:
        answers, _, _ = await self.one.decide(state, point.questions, timeout=point.deadline_s)
        return answers


class RuleDecider:
    """Deterministic baseline policy, selected explicitly in config (e.g. before API keys exist)."""

    name = "rules"

    async def decide(self, point: Point, state: str, context: dict[str, Any]) -> dict[str, Answer]:
        match point.name:
            case "threat_response":
                hp_fraction = float(context.get("hp_fraction", 1.0))
                offered = point.questions["threat_response"].criteria or []
                low = hp_fraction < 0.3 and "retreat_to_leader" in offered
                choice = "retreat_to_leader" if low else "equip_best_then_fight"
                return {"threat_response": Answer(choice=choice, confidence=1.0)}
            case "speak_worthy":
                return {"speak_worthy": Answer(score=float(context.get("urgency", 1)) + 1.0)}
            case "intent_guard":
                return {"explicit_request": Answer(noul=1.0 if context.get("matched_intent") else 0.0)}
        raise ValueError(f"no rule for decision point {point.name}")


@dataclass
class Breaker:
    failures: int = 3
    window_s: float = 30.0
    cooldown_s: float = 60.0
    clock: Callable[[], float] = time.monotonic
    _recent: list[float] = field(default_factory=list)
    _open_until: float = 0.0

    @property
    def open(self) -> bool:
        return self.clock() < self._open_until

    def record_failure(self) -> bool:
        """Returns True if this failure opened the breaker."""
        now = self.clock()
        self._recent = [t for t in self._recent if now - t <= self.window_s] + [now]
        if len(self._recent) >= self.failures and not self.open:
            self._open_until = now + self.cooldown_s
            self._recent.clear()
            return True
        return False


class DecisionRunner:
    def __init__(self, deciders: dict[str, Decider], log_path: Path | None = None) -> None:
        self.deciders = deciders
        self.log_path = log_path
        self.breaker = Breaker()
        self.on_breaker_open: Callable[[], None] | None = None

    async def ask(self, point: Point, state: str, context: dict[str, Any] | None = None) -> Decided:
        decider = self.deciders[point.name]
        if decider.name != "rules" and self.breaker.open:
            return self._log(point, decider, state, Decided(point.name, "breaker_open"))
        began = time.perf_counter()
        try:
            answers = await asyncio.wait_for(decider.decide(point, state, context or {}), point.deadline_s)
            decided = Decided(point.name, "ok", answers, (time.perf_counter() - began) * 1000)
        except (TimeoutError, httpx.TimeoutException):
            decided = Decided(point.name, "timeout", latency_ms=(time.perf_counter() - began) * 1000)
        except (SystemOneError, httpx.HTTPError) as error:
            decided = Decided(
                point.name, "error", latency_ms=(time.perf_counter() - began) * 1000, error=str(error)
            )
        if decided.status in ("timeout", "error") and self.breaker.record_failure() and self.on_breaker_open:
            self.on_breaker_open()
        return self._log(point, decider, state, decided)

    def _log(self, point: Point, decider: Decider, state: str, decided: Decided) -> Decided:
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": time.time(),
                "point": point.name,
                "backend": decider.name,
                "state": state,
                "questions": {name: q.wire() for name, q in point.questions.items()},
                "status": decided.status,
                "answers": {
                    name: {
                        "choice": a.choice,
                        "score": a.score,
                        "noul": a.noul,
                        "probabilities": a.probabilities,
                        "confidence": a.confidence,
                    }
                    for name, a in decided.answers.items()
                },
                "latency_ms": round(decided.latency_ms, 1),
                "error": decided.error,
            }
            with self.log_path.open("a") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return decided
