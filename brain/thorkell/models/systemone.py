"""Typed "System One" decisions: Jev (TypeSafe, cloud) and laya-serve (local) share one wire format.

POST {base}/v1/systemone
  {"model": ..., "state": {"body": <text>}, "questions": {name: {"type": choice|score|noul,
   "instructions": ..., "criteria": {option: description} | [levels]}}}
-> {"answers": {name: {"choice"|"score"|"noul": ..., "probabilities": {...}, "confidence": ...}},
    "usage": {...}}

Switching Jev -> laya is a base URL + model change; nothing falls back silently.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx


class SystemOneError(Exception):
    pass


@dataclass(frozen=True)
class Question:
    type: Literal["choice", "score", "noul"]
    instructions: str
    criteria: dict[str, str] | list[str] | None = None

    def wire(self) -> dict[str, Any]:
        body: dict[str, Any] = {"type": self.type, "instructions": self.instructions}
        if self.criteria is not None:
            body["criteria"] = self.criteria
        return body


@dataclass(frozen=True)
class Answer:
    choice: str | None = None
    score: float | None = None
    noul: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None


@dataclass(frozen=True)
class Backend:
    name: str  # "jev" | "laya"
    base_url: str
    model: str
    api_key: str | None = None


class SystemOne:
    def __init__(self, backend: Backend, client: httpx.AsyncClient | None = None) -> None:
        self.backend = backend
        self._client = client or httpx.AsyncClient()

    async def decide(
        self, state: str, questions: dict[str, Question], timeout: float
    ) -> tuple[dict[str, Answer], float, dict[str, Any]]:
        """Returns (answers, latency_ms, raw response). Raises SystemOneError / httpx.TimeoutException."""
        headers = {"Authorization": f"Bearer {self.backend.api_key}"} if self.backend.api_key else {}
        payload = {
            "model": self.backend.model,
            "state": {"body": state},
            "questions": {name: q.wire() for name, q in questions.items()},
        }
        began = time.perf_counter()
        response = await self._client.post(
            f"{self.backend.base_url}/v1/systemone", json=payload, headers=headers, timeout=timeout
        )
        latency_ms = (time.perf_counter() - began) * 1000
        if response.status_code != 200:
            raise SystemOneError(f"{self.backend.name} HTTP {response.status_code}: {response.text[:200]}")
        raw = response.json()
        answers_raw = raw.get("answers")
        if not isinstance(answers_raw, dict):
            raise SystemOneError(f"{self.backend.name} response has no answers object")
        answers: dict[str, Answer] = {}
        for name, question in questions.items():
            entry = answers_raw.get(name)
            if not isinstance(entry, dict):
                raise SystemOneError(f"{self.backend.name} did not answer '{name}'")
            answer = Answer(
                choice=entry.get("choice"),
                score=entry.get("score"),
                noul=entry.get("noul"),
                probabilities={str(k): float(v) for k, v in (entry.get("probabilities") or {}).items()},
                confidence=entry.get("confidence"),
            )
            if question.type == "choice" and (
                answer.choice is None
                or (isinstance(question.criteria, dict) and answer.choice not in question.criteria)
            ):
                raise SystemOneError(
                    f"{self.backend.name} chose {answer.choice!r} for '{name}', not an offered option"
                )
            if question.type == "noul" and answer.noul is None:
                raise SystemOneError(f"{self.backend.name} gave no noul for '{name}'")
            if question.type == "score" and answer.score is None:
                raise SystemOneError(f"{self.backend.name} gave no score for '{name}'")
            answers[name] = answer
        return answers, latency_ms, raw

    async def close(self) -> None:
        await self._client.aclose()
