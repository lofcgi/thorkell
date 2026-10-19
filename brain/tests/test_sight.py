"""Thorkell's eyes: what his own screen shows, read by a (stand-in) multimodal model."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig

from thorkell.config import Config, VisionConfig
from thorkell.models.gemini import Usage
from thorkell.sim.world import SimEntity, SimWorld
from thorkell.world.sight import Eyes, on_screen


class SeeingModel:
    """Stands in for gemini-3.5-flash-lite looking at a frame: a prepared answer; keeps what it got."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    async def see_json(self, **call: Any) -> tuple[dict[str, Any], Usage]:
        self.calls.append(call)
        return self.answer, Usage(input_tokens=300, output_tokens=80)


async def test_it_looks_at_its_own_screen_and_ties_what_it_sees_to_named_things(
    make_rig: Callable[..., Any],
) -> None:
    rig: Rig = await make_rig(world=SimWorld([SimEntity("7:30", "item", "돌", 5.0, 0.0)]))
    model = SeeingModel(
        {
            "summary_ko": "풀밭. 앞에 돌 하나와 돌 테두리 안에 빛나는 소용돌이가 있다",
            "things": [
                {"what_ko": "돌", "where_ko": "화면 가운데 5m쯤", "id": "7:30"},
                {"what_ko": "빛나는 소용돌이", "where_ko": "화면 왼쪽 5m쯤", "note_ko": "처음 본다"},
            ],
            "ways": ["오른쪽으로 트인 길"],
            "leader_ko": None,
        }
    )
    eyes = Eyes(rig.session, model, VisionConfig(backend="gemini"))
    view = await eyes.look("리더가 가리키는 게 뭐야?")
    call = model.calls[0]
    assert call["images"] and call["model"] == "gemini-3.5-flash-lite" and call["resolution"] == "low"
    assert "7:30 돌 (item) 5m" in call["prompt"] and "리더가 가리키는 게 뭐야?" in call["prompt"]
    assert view.things[1]["what_ko"] == "빛나는 소용돌이" and view.ways == ["오른쪽으로 트인 길"]
    assert "- 빛나는 소용돌이: 화면 왼쪽 5m쯤 — 처음 본다" in view.lines()


def test_where_a_direction_falls_on_a_person_s_screen() -> None:
    assert on_screen(0.0, 65.0, 640, 360) == "화면 가운데"
    assert on_screen(-40.0, 65.0, 640, 360) == "화면 왼쪽"
    assert on_screen(90.0, 65.0, 640, 360) == "화면 밖 오른쪽"
    assert on_screen(170.0, 65.0, 640, 360) == "화면 밖 오른쪽 뒤"


def test_seeing_needs_the_gemini_key() -> None:
    assert Config(vision=VisionConfig(backend="gemini")).required_secrets() == ["GEMINI_API_KEY"]


async def test_asked_what_it_can_see_it_looks_all_round(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 포탈이 등 뒤에 있어 화면에 없었다. 사람은 카메라를 돌려 둘러본다.
    rig: Rig = await make_rig(world=SimWorld([SimEntity("7:30", "item", "돌", 0.0, -5.0)]))
    model = SeeingModel({"summary_ko": "풀밭", "things": [], "ways": []})
    eyes = Eyes(rig.session, model, VisionConfig(backend="gemini"))
    await eyes.look(around=True)
    call = model.calls[0]
    assert len(call["images"]) == 4
    assert "그림 1: 앞, 그림 2: 오른쪽, 그림 3: 뒤, 그림 4: 왼쪽" in call["prompt"]
    assert "7:30 돌 (item) 5m, 그림 3" in call["prompt"]


async def test_before_answering_the_leader_it_looks_where_the_leader_is_facing(
    make_rig: Callable[..., Any],
) -> None:
    # 리허설(2026-10-18): "이거 보여?" "포탈 같은거"에 물체 목록만 보고 "안 보여"라고 했다. 사람은 친구가
    # 보는 쪽을 쳐다보고 답한다. 판단하기 전에 리더 앞쪽을 보고, 본 것을 판단에 넣는다.
    from conftest import ScriptedModel

    from thorkell.plan.planner import Planner

    answer = {
        "interpretation_ko": "포탈이 보이냐는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [],
        "abort_if": [],
        "speech_gist_ko": "응, 네 앞에 돌 테두리 안에서 빛이 도는 게 보여!",
    }
    planner_model = ScriptedModel(answer)
    seeing = SeeingModel(
        {
            "summary_ko": "리더 바로 앞에 돌 테두리 안에서 빛이 도는 것이 서 있다",
            "things": [{"what_ko": "돌 테두리 안에 빛나는 소용돌이", "where_ko": "화면 가운데 5m쯤"}],
            "ways": [],
            "leader_ko": "그것을 바라보고 서 있다",
        }
    )
    rig: Rig = await make_rig(world=SimWorld([], leader_at=(6.0, 0.0)), planner=Planner(planner_model))
    rig.controller.eyes = Eyes(rig.session, seeing, VisionConfig(backend="gemini"))
    rig.world.leader_says("이거 보여?")
    await rig.until(lambda: "응, 네 앞에 돌 테두리 안에서 빛이 도는 게 보여!" in rig.said(), 10)
    assert len(seeing.calls[0]["images"]) == 1 and "이거 보여?" in seeing.calls[0]["prompt"]
    assert "[지금 내 화면]" in planner_model.prompts[0]
    assert "리더 바로 앞에 돌 테두리 안에서 빛이 도는 것이 서 있다" in planner_model.prompts[0]
