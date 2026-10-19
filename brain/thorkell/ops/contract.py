"""`thorkell contract flash|jev|live`: check the real APIs behave the way the brain assumes.

Needs keys (inject with `op run --env-file brain/secrets.op -- ...`). Results go to
artifacts/contracts/<name>-<timestamp>.json; nothing here changes the brain's behaviour.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx
from google import genai
from google.genai import types

from thorkell.config import secret
from thorkell.decide.points import THREAT_RESPONSE
from thorkell.models.gemini import GeminiJson
from thorkell.models.systemone import Backend, SystemOne, SystemOneError
from thorkell.paths import REPO_ROOT
from thorkell.talk.tools import DECLARATIONS

SCHEMA = {
    "type": "object",
    "properties": {"answer_ko": {"type": "string"}, "count": {"type": "integer"}},
    "required": ["answer_ko", "count"],
}
STATE = (
    "SELF hp 18/25 (72%) stamina 30/50\nEQUIPPED 돌도끼\n"
    "CREATURE [1] 그레이드워프 dist 3.0 alerted\nTASK gather wood 4/10"
)


async def flash(model: str = "gemini-3.8-flash") -> dict[str, Any]:
    client = GeminiJson(secret("GEMINI_API_KEY"))
    results: dict[str, Any] = {}
    for level in ("minimal", "low", "medium"):
        began = time.perf_counter()
        try:
            data, usage = await client.generate_json(
                model=model,
                system="Return JSON only.",
                prompt="count에 3을 넣고, 나무 3개를 모으겠다는 말을 answer_ko에 한 문장으로 써.",
                schema=SCHEMA,
                thinking=level,
                max_output_tokens=512,
            )
            results[level] = {
                "ok": True,
                "seconds": round(time.perf_counter() - began, 2),
                "data": data,
                "usage": usage.__dict__,
            }
        except Exception as error:  # every outcome, including API rejections, is recorded
            results[level] = {"ok": False, "error": f"{type(error).__name__}: {error}"}
    return {"model": model, "thinking": results}


async def jev(rounds: int = 10) -> dict[str, Any]:
    one = SystemOne(
        Backend("jev", "https://api.typesafe.ai", "jev-1.13.0", secret("TYPESAFE_API_KEY")),
        httpx.AsyncClient(),
    )
    latencies, answers, errors = [], [], []
    for _ in range(rounds):
        try:
            result, latency, _ = await one.decide(STATE, THREAT_RESPONSE.questions, timeout=5.0)
            latencies.append(latency)
            answers.append(
                {
                    "choice": result["threat_response"].choice,
                    "probabilities": result["threat_response"].probabilities,
                }
            )
        except (SystemOneError, httpx.HTTPError) as error:
            errors.append(f"{type(error).__name__}: {error}")
    await one.close()
    summary: dict[str, Any] = {"rounds": rounds, "errors": errors, "answers": answers[:3]}
    if latencies:
        ordered = sorted(latencies)
        summary["latency_ms"] = {
            "p50": round(statistics.median(ordered), 1),
            "p95": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1),
        }
    return summary


async def live(model: str = "gemini-3.8-live") -> dict[str, Any]:
    client = genai.Client(api_key=secret("GEMINI_API_KEY"))
    config = types.LiveConnectConfig.model_validate(
        {
            "response_modalities": ["AUDIO"],
            "output_audio_transcription": {},
            "system_instruction": "너는 Thorkell이다. 상태를 물으면 반드시 ask_status 도구를 먼저 부른다.",
            "tools": [{"function_declarations": DECLARATIONS}],
            "session_resumption": {},
            "context_window_compression": {"sliding_window": {}},
        }
    )
    report: dict[str, Any] = {"model": model}
    async with client.aio.live.connect(model=model, config=config) as session:
        began = time.perf_counter()
        await session.send_client_content(
            turns=[{"role": "user", "parts": [{"text": "토르켈, 지금 뭐 하고 있어?"}]}], turn_complete=True
        )
        transcript, first_audio, tool_round = "", None, None
        deadline = time.perf_counter() + 30
        while time.perf_counter() < deadline and "turn_done" not in report:
            async for message in session.receive():
                if message.tool_call:
                    calls = message.tool_call.function_calls or []
                    report["tool_calls"] = [c.name for c in calls]
                    tool_round = time.perf_counter()
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(
                                id=c.id,
                                name=c.name,
                                response={"status_ko": "나무 모으기 (4/10) 하는 중이야."},
                                scheduling=types.FunctionResponseScheduling.WHEN_IDLE,
                            )
                            for c in calls
                        ]
                    )
                content = message.server_content
                parts = content.model_turn.parts or [] if content and content.model_turn else []
                if first_audio is None and any(p.inline_data for p in parts):
                    first_audio = time.perf_counter()
                if content and content.output_transcription and content.output_transcription.text:
                    transcript += content.output_transcription.text
                if message.session_resumption_update and message.session_resumption_update.new_handle:
                    report["resumable"] = bool(message.session_resumption_update.resumable)
                if content and content.turn_complete and (tool_round is None or first_audio is not None):
                    report["turn_done"] = True
        report["seconds_to_first_audio"] = round(first_audio - began, 2) if first_audio else None
        report["seconds_after_tool_to_audio"] = (
            round(first_audio - tool_round, 2) if first_audio and tool_round else None
        )
        report["transcript"] = transcript
    return report


CHECKS: dict[str, Callable[[], Awaitable[dict[str, Any]]]] = {"flash": flash, "jev": jev, "live": live}


async def run(name: str) -> dict[str, Any]:
    began = time.time()
    result = await CHECKS[name]()
    result["checked_at"] = datetime.now().isoformat(timespec="seconds")
    result["elapsed_s"] = round(time.time() - began, 1)
    out = REPO_ROOT / "artifacts/contracts" / f"{name}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n")
    result["saved_to"] = str(out)
    return result


def main(name: str) -> int:
    print(json.dumps(asyncio.run(run(name)), indent=2, ensure_ascii=False, default=str))
    return 0
