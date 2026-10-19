from __future__ import annotations

import asyncio
import stat
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from conftest import Rig
from google.genai import types

from thorkell.decide.runner import DecisionRunner, RuleDecider
from thorkell.talk.floor import IDLE, MODEL, USER, Floor
from thorkell.talk.live import LiveVoice, VoiceConfig
from thorkell.talk.tools import ToolBridge


def msg(**fields: Any) -> types.LiveServerMessage:
    return types.LiveServerMessage.model_validate(fields)


class FakeSession:
    def __init__(self, turns: list[list[types.LiveServerMessage]]) -> None:
        self.turns = turns
        self.audio: list[bytes] = []
        self.content: list[tuple[str, bool]] = []
        self.tool_responses: list[types.FunctionResponse] = []
        self.done = asyncio.Event()

    async def send_realtime_input(self, *, audio: types.Blob) -> None:
        assert audio.mime_type == "audio/pcm;rate=16000"
        self.audio.append(audio.data or b"")

    async def send_client_content(self, *, turns: list[dict[str, Any]], turn_complete: bool) -> None:
        self.content.append((turns[0]["parts"][0]["text"], turn_complete))

    async def send_tool_response(self, *, function_responses: list[types.FunctionResponse]) -> None:
        self.tool_responses.extend(function_responses)

    async def receive(self) -> AsyncIterator[types.LiveServerMessage]:
        if not self.turns:
            self.done.set()
            await asyncio.sleep(3600)
        for message in self.turns.pop(0):
            yield message


class Recorder:
    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.flushes = 0

    def play(self, pcm: bytes) -> None:
        self.played.append(pcm)

    def flush(self) -> None:
        self.flushes += 1


class StubTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        self.calls.append((name, args))
        return {"status": "accepted"}, "WHEN_IDLE"


def connector(sessions: list[FakeSession], configs: list[dict[str, Any]]) -> Callable[..., Any]:
    @asynccontextmanager
    async def connect(model: str, config: dict[str, Any]) -> AsyncIterator[FakeSession]:
        configs.append(config)
        if not sessions:
            raise ConnectionError("resumption rejected")
        yield sessions.pop(0)

    return connect


def voice(sessions: list[FakeSession], configs: list[dict[str, Any]], tmp_path: Path, **kw: Any) -> LiveVoice:
    return LiveVoice(
        connect=connector(sessions, configs),
        tools=StubTools(),  # type: ignore[arg-type]
        speaker=Recorder(),
        mic=asyncio.Queue(),
        config=VoiceConfig(handle_path=tmp_path / "live.handle"),
        **kw,
    )


async def test_audio_transcripts_tools_and_resumption(tmp_path: Path) -> None:
    session = FakeSession(
        [
            [
                msg(server_content={"input_transcription": {"text": "토르켈 나무 좀 해줘"}}),
                msg(
                    tool_call={
                        "function_calls": [{"id": "t1", "name": "set_goal", "args": {"request_ko": "나무"}}]
                    }
                ),
                msg(
                    server_content={
                        "model_turn": {
                            "parts": [{"inline_data": {"data": b"\x01\x02", "mime_type": "audio/pcm"}}]
                        }
                    }
                ),
                msg(server_content={"output_transcription": {"text": "응, 해 올게!"}}),
                msg(session_resumption_update={"new_handle": "h-123", "resumable": True}),
                msg(server_content={"interrupted": True, "turn_complete": True}),
            ]
        ]
    )
    transcripts: list[tuple[str, str]] = []
    live = voice([session], [], tmp_path, on_transcript=lambda who, text: transcripts.append((who, text)))
    stop = asyncio.Event()
    task = asyncio.create_task(live.run(stop))
    await asyncio.wait_for(session.done.wait(), 2)

    assert transcripts == [("leader", "토르켈 나무 좀 해줘"), ("thorkell", "응, 해 올게!")]
    assert live.leader_words == "토르켈 나무 좀 해줘"
    assert live.speaker.played == [b"\x01\x02"]  # type: ignore[attr-defined]
    assert live.speaker.flushes == 1  # type: ignore[attr-defined]
    response = session.tool_responses[0]
    assert (response.id, response.name, response.response) == ("t1", "set_goal", {"status": "accepted"})
    assert response.scheduling == types.FunctionResponseScheduling.WHEN_IDLE
    handle = tmp_path / "live.handle"
    assert handle.read_text() == "h-123" and stat.S_IMODE(handle.stat().st_mode) == 0o600

    await live.mic.put(b"\x00" * 640)
    await asyncio.sleep(0.05)
    assert session.audio == [b"\x00" * 640]
    stop.set()
    task.cancel()


async def test_go_away_reconnects_with_the_handle(tmp_path: Path) -> None:
    first = FakeSession(
        [
            [
                msg(session_resumption_update={"new_handle": "h-1", "resumable": True}),
                msg(go_away={"time_left": "5s"}),
            ]
        ]
    )
    second = FakeSession([])
    configs: list[dict[str, Any]] = []
    live = voice([first, second], configs, tmp_path)
    task = asyncio.create_task(live.run(asyncio.Event()))
    await asyncio.wait_for(second.done.wait(), 2)
    assert configs[0]["session_resumption"] == {}
    assert configs[1]["session_resumption"] == {"handle": "h-1"}
    assert live.status == "up"
    task.cancel()


async def test_failed_resume_takes_voice_down_loudly(tmp_path: Path) -> None:
    (tmp_path / "live.handle").write_text("stale")
    downs: list[str] = []
    live = voice([], [], tmp_path, on_down=downs.append)
    await asyncio.wait_for(live.run(asyncio.Event()), 2)
    assert live.status == "down"
    assert downs and "세션 재개 실패" in downs[0]


async def test_injections_respect_the_floor(tmp_path: Path) -> None:
    now = [0.0]
    session = FakeSession([])
    live = voice([session], [], tmp_path, floor=Floor(idle_after_s=1.5, clock=lambda: now[0]))
    task = asyncio.create_task(live.run(asyncio.Event()))
    await asyncio.wait_for(session.done.wait(), 2)

    live.floor.model_activity()
    assert not await live.inject("나무 다 모았어", speak=True)
    assert await live.inject("밤이 됐다", speak=False)
    assert await live.inject("위험해!", speak=True, urgent=True)
    now[0] = 2.0
    assert await live.inject("나무 다 모았어", speak=True)
    assert session.content == [
        ("[게임 이벤트] 밤이 됐다", False),
        ("[Thorkell이 할 말] 위험해!", True),
        ("[Thorkell이 할 말] 나무 다 모았어", True),
    ]
    task.cancel()


def test_floor_states() -> None:
    now = [0.0]
    floor = Floor(idle_after_s=1.5, clock=lambda: now[0])
    assert floor.state() == IDLE
    floor.user_activity()
    assert floor.state() == USER
    now[0] = 1.0
    floor.model_activity()
    assert floor.state() == MODEL
    now[0] = 3.0
    assert floor.idle()


async def test_tool_bridge_against_the_simulator(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(
        decider=DecisionRunner({"intent_guard": RuleDecider(), "threat_response": RuleDecider()})
    )
    words = [""]
    tools = ToolBridge(rig.controller, rig.controller.decider, lambda: words[0])

    refused, _ = await tools.call("set_goal", {"request_ko": "나무 10개 캐줘"})
    assert refused["status"] == "unverified"

    words[0] = "토르켈 나무 10개 캐줘"
    accepted, scheduling = await tools.call("set_goal", {"request_ko": "나무 10개 캐줘"})
    assert accepted["status"] == "accepted" and "나무 10개" in accepted["summary_ko"]
    assert scheduling == "WHEN_IDLE"
    await rig.until(lambda: rig.controller.current() is not None)

    status, _ = await tools.call("ask_status", {})
    assert "나무 모으기" in status["status_ko"]

    words[0] = "그만해"
    cancelled, _ = await tools.call("cancel", {"reason_ko": "리더가 그만하래"})
    assert cancelled["status"] == "cancelled"
    await rig.until(lambda: rig.controller.current() is None and "알겠어, 멈출게." in rig.said())


async def test_teach_and_recall_through_tools(make_rig: Callable[..., Any]) -> None:
    from thorkell.mind.mind import Mind
    from thorkell.mind.store import Store

    rig: Rig = await make_rig(mind=Mind(Store()))
    tools = ToolBridge(rig.controller, None, lambda: "")
    unknown, _ = await tools.call("recall_knowledge", {"query_ko": "트롤 약점"})
    assert "아직 잘 몰라" in unknown["answer_ko"]
    taught, _ = await tools.call("teach_fact", {"statement_ko": "트롤은 둔기에 약해"})
    assert taught["stored"]
    known, _ = await tools.call("recall_knowledge", {"query_ko": "트롤 약점"})
    assert "둔기에 약하다고 했었지" in known["answer_ko"]


@pytest.mark.parametrize("name", ["set_goal", "cancel", "ask_status", "recall_knowledge", "teach_fact"])
def test_declarations_are_complete(name: str) -> None:
    from thorkell.talk.tools import DECLARATIONS

    declaration = next(d for d in DECLARATIONS if d["name"] == name)
    assert declaration["behavior"] in ("BLOCKING", "NON_BLOCKING")
    assert declaration["parameters"]["type"] == "object"
