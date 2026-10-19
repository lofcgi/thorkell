"""Gemini text models through the Interactions API (google-genai >= 2.26).

Used for planning, reflection and fact extraction: one JSON answer per call, constrained by a JSON
schema. Calls are stateless (`store=False`): the brain keeps its own memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from google import genai
from google.genai import types

# Interactions API는 오류를 이 비공개 모듈의 계층으로만 던진다(google-genai 2.26에서 공개 경로가 없다).
# 서버 과부하(503)·한도(429)·연결 실패가 모두 이 뿌리 아래에 있다.
from google.genai._gaos.lib.compat_errors import GeminiNextGenAPIClientError


class ModelError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status  # HTTP 상태(429 = 사용 한도), 응답이 없었으면 None


# 대화 중에 부르는 모델이라 오래 기다리지 않는다. SDK 기본값은 한도 초과(429)에도 서버가 말한 대기
# (약 30초)만큼씩 세 번 다시 해서, 실게임에서 인사 한마디에 90초 동안 아무 말이 없었다.
# 한도 초과는 다시 해도 소용없으니 바로 알리고, 과부하(5xx)만 한 번 다시 해 본다.
HTTP_OPTIONS = types.HttpOptions(
    timeout=60_000,
    retry_options=types.HttpRetryOptions(
        attempts=1, initial_delay=1.0, max_delay=4.0, http_status_codes=[500, 502, 503, 504]
    ),
)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    thought_tokens: int = 0
    cached_tokens: int = 0


class JsonModel(Protocol):
    async def generate_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]: ...


class GeminiJson:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ModelError("GEMINI_API_KEY is empty")
        self._client = genai.Client(api_key=api_key, http_options=HTTP_OPTIONS)

    async def generate_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        return await self._create(model, system, prompt, schema, thinking, max_output_tokens)

    async def see_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        images: tuple[str, ...],
        resolution: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        """Like generate_json, with base64 JPEG images (Thorkell's own screen) before the text."""
        content: list[Any] = [
            {"type": "image", "data": image, "mime_type": "image/jpeg", "resolution": resolution}
            for image in images
        ]
        content.append({"type": "text", "text": prompt})
        return await self._create(model, system, content, schema, thinking, max_output_tokens)

    async def _create(
        self,
        model: str,
        system: str,
        input: Any,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        try:
            interaction = await self._client.aio.interactions.create(
                model=model,
                input=input,
                system_instruction=system,
                response_format={"type": "text", "mime_type": "application/json", "schema": schema},
                generation_config={"thinking_level": thinking, "max_output_tokens": max_output_tokens},
                store=False,
            )
        except GeminiNextGenAPIClientError as error:
            status = getattr(error, "status_code", None)
            raise ModelError(f"{model} call failed ({status or 'no response'}): {error}", status) from error
        text = getattr(interaction, "output_text", None)
        if not text:
            raise ModelError(f"{model} returned no text (status={getattr(interaction, 'status', None)})")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ModelError(f"{model} returned invalid JSON: {error}: {text[:200]!r}") from error
        if not isinstance(data, dict):
            raise ModelError(f"{model} returned {type(data).__name__}, expected an object")
        usage = getattr(interaction, "usage", None)
        return data, Usage(
            input_tokens=int(getattr(usage, "total_input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "total_output_tokens", 0) or 0),
            thought_tokens=int(getattr(usage, "total_thought_tokens", 0) or 0),
            cached_tokens=int(getattr(usage, "total_cached_tokens", 0) or 0),
        )
