from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from thorkell.models.systemone import Backend, Question, SystemOne, SystemOneError

QUESTIONS = {
    "threat_response": Question(
        "choice",
        "What should Thorkell do now?",
        {"fight": "attack it", "retreat_to_leader": "run to the leader"},
    ),
    "danger": Question("noul", "Is Thorkell in danger?"),
}


def _client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_sends_wire_format_and_parses_answers() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "answers": {
                    "threat_response": {
                        "choice": "fight",
                        "probabilities": {"fight": 0.81, "retreat_to_leader": 0.19},
                        "confidence": 0.81,
                    },
                    "danger": {"noul": 0.64, "probabilities": {"true": 0.64, "false": 0.36}},
                },
                "usage": {"input_tokens": 120, "output_tokens": 0},
            },
        )

    backend = Backend("jev", "https://api.typesafe.ai", "jev-1.13.0", api_key="k")
    one = SystemOne(backend, _client(handler))
    answers, latency, _ = await one.decide("SELF hp 18/25", QUESTIONS, timeout=1.0)
    assert seen["url"] == "https://api.typesafe.ai/v1/systemone"
    assert seen["auth"] == "Bearer k"
    assert seen["body"]["state"] == {"body": "SELF hp 18/25"}
    assert seen["body"]["questions"]["threat_response"]["criteria"]["fight"] == "attack it"
    assert seen["body"]["model"] == "jev-1.13.0"
    assert answers["threat_response"].choice == "fight"
    assert answers["danger"].noul == pytest.approx(0.64)
    assert latency >= 0


async def test_laya_needs_no_auth_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"answers": {"danger": {"noul": 0.1}}})

    one = SystemOne(Backend("laya", "http://127.0.0.1:8000", "typed-decisions"), _client(handler))
    answers, _, _ = await one.decide("x", {"danger": QUESTIONS["danger"]}, timeout=1.0)
    assert answers["danger"].noul == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"answers": {"threat_response": {"choice": "teleport"}, "danger": {"noul": 0.5}}},
            "not an offered option",
        ),
        ({"answers": {"threat_response": {"choice": "fight"}}}, "did not answer 'danger'"),
        ({"answers": {"threat_response": {"choice": "fight"}, "danger": {}}}, "gave no noul"),
        ({}, "no answers object"),
    ],
)
async def test_malformed_answers_are_errors(payload: dict[str, Any], message: str) -> None:
    one = SystemOne(Backend("jev", "https://x", "m"), _client(lambda r: httpx.Response(200, json=payload)))
    with pytest.raises(SystemOneError, match=message):
        await one.decide("s", QUESTIONS, timeout=1.0)


async def test_http_errors_surface() -> None:
    one = SystemOne(
        Backend("jev", "https://x", "m"), _client(lambda r: httpx.Response(429, text="slow down"))
    )
    with pytest.raises(SystemOneError, match="HTTP 429"):
        await one.decide("s", QUESTIONS, timeout=1.0)
