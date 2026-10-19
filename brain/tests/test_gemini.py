from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from google.genai._gaos.lib.compat_errors import APIConnectionError, InternalServerError, RateLimitError

from thorkell.models.gemini import GeminiJson, ModelError


def gemini_raising(error: Exception) -> GeminiJson:
    async def create(**_: Any) -> Any:
        raise error

    client = GeminiJson("test-key")
    client._client = SimpleNamespace(aio=SimpleNamespace(interactions=SimpleNamespace(create=create)))  # type: ignore[assignment]
    return client


async def ask(client: GeminiJson) -> None:
    await client.generate_json(
        model="gemini-3.8-flash", system="s", prompt="p", schema={}, thinking="low", max_output_tokens=64
    )


REQUEST = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/interactions")


async def test_server_overload_becomes_model_error() -> None:
    # 실제로 겪은 것: 503 "high demand"가 ModelError가 아니어서 플래너 실패를 말로 알리지 못했다.
    busy = InternalServerError(
        "This model is currently experiencing high demand.",
        response=httpx.Response(503, request=REQUEST),
        body=None,
    )
    with pytest.raises(ModelError, match="503") as caught:
        await ask(gemini_raising(busy))
    assert caught.value.__cause__ is busy


async def test_connection_failure_becomes_model_error() -> None:
    offline = APIConnectionError(message="Connection error.", request=REQUEST)
    with pytest.raises(ModelError, match="Connection error"):
        await ask(gemini_raising(offline))


async def test_programming_errors_are_not_wrapped() -> None:
    with pytest.raises(TypeError):
        await ask(gemini_raising(TypeError("bad argument")))


async def test_quota_exhaustion_fails_at_once_with_its_status() -> None:
    # 실제로 겪은 것: 무료 등급 하루 20회를 다 쓰자 SDK가 30초씩 세 번 기다려 90초 뒤에야 실패했다.
    quota = RateLimitError(
        "Rate limit exceeded for model gemini-3.8-flash (limit: 20 requests per day on Free Tier).",
        response=httpx.Response(429, request=REQUEST),
        body=None,
    )
    with pytest.raises(ModelError) as caught:
        await ask(gemini_raising(quota))
    assert caught.value.status == 429
    retry = GeminiJson("test-key")._client._api_client._http_options.retry_options
    assert retry is not None and 429 not in (retry.http_status_codes or [])
    assert retry.attempts == 1 and 503 in (retry.http_status_codes or [])
