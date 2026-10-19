"""The planner's judgment wired into the simulator (model scripted): asking, proposing, trying."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig, ScriptedModel

from thorkell.plan.planner import Planner
from thorkell.sim.world import SimWorld, boar, forest


def talk(text: str, steps: list[dict[str, Any]] | None = None, clarify: str | None = None) -> dict[str, Any]:
    return {
        "interpretation_ko": "x",
        "clarify": clarify,
        "quantity": None,
        "assumptions": [],
        "steps": steps or [],
        "abort_if": [],
        "speech_gist_ko": text,
    }


async def test_an_unknown_creature_is_asked_about_not_guessed(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(talk("", clarify="멧돼지? 아직 못 봤어. 어떻게 생겼어?"))
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("멧돼지 잡아와")
    await rig.until(lambda: "멧돼지? 아직 못 봤어. 어떻게 생겼어?" in rig.said(), 10)
    await rig.until(lambda: rig.controller.current() is None, 5)
    # 리허설(2026-10-18): 되묻는 말을 한 번 하고, 일이 끝났다는 보고로 같은 말을 또 했다.
    assert rig.said().count("멧돼지? 아직 못 봤어. 어떻게 생겼어?") == 1
    prompt = model.prompts[0]
    assert "[이름을 아는 생물] 아직 없음" in prompt
    assert "멧돼지 잡아와" in prompt


async def test_a_named_creature_is_searched_for_then_hunted(make_rig: Callable[..., Any]) -> None:
    world = SimWorld([*forest(1), boar(26.0, 8.0)])
    world.bot.inventory = {"곤봉": 1}
    world.bot.known = {"곤봉"}
    world.bot.foods = {"라즈베리": 1200.0}
    plan = talk(
        "멧돼지는 처음인데, 한번 찾아볼게!",
        [
            {"id": "s1", "skill": "search", "args": {"name": "멧돼지"}},
            {"id": "s2", "skill": "hunt", "args": {"creature": "멧돼지", "count": 1}, "after": ["s1"]},
        ],
    )
    rig: Rig = await make_rig(world=world, planner=Planner(ScriptedModel(plan)))
    rig.world.leader_says("멧돼지 한 마리만 잡아와")
    await rig.until(lambda: rig.world.bot.inventory.get("날고기", 0) >= 1, 60)
    assert "멧돼지는 처음인데, 한번 찾아볼게!" in rig.said()


async def test_a_big_request_gets_a_concrete_proposal(make_rig: Callable[..., Any]) -> None:
    proposal = "작업대 둘레에 벽이랑 지붕이면 나무 30개쯤 들 것 같아. 그 정도로 지을까?"
    model = ScriptedModel(talk("", clarify=proposal))
    world = SimWorld(forest(2))
    world.bot.inventory = {"나무": 12, "돌": 4, "망치": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 1200.0}
    rig: Rig = await make_rig(world=world, planner=Planner(model))
    rig.world.leader_says("집을 지어야겠어")
    await rig.until(lambda: proposal in rig.said(), 10)
    prompt = model.prompts[0]
    assert "작업대(나무 10)" in prompt and "나무 12" in prompt
