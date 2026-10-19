"""M4 integration in the simulator: planner-driven requests and threat decisions (models scripted)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from conftest import Rig, ScriptedModel

from thorkell.decide.points import Point
from thorkell.decide.runner import DecisionRunner, RuleDecider
from thorkell.models.gemini import ModelError
from thorkell.models.systemone import Answer
from thorkell.plan.planner import Planner
from thorkell.sim.world import greydwarf

PLAN = {
    "interpretation_ko": "해 지기 전에 쓸 나무를 모아 달라는 뜻",
    "quantity": {"value": 10, "basis": "purpose", "cites": []},
    "assumptions": [{"text": "숲 가장자리에 나무가 있다", "cites": [], "hypothesis": True}],
    "steps": [
        {"id": "s1", "skill": "equip", "args": {"item": "돌도끼"}},
        {"id": "s2", "skill": "gather_wood", "args": {"count": 10}, "after": ["s1"]},
    ],
    "abort_if": [{"cond": "hp_below", "value": 0.2}],
    "speech_gist_ko": "해 지기 전에 10개쯤 해 올게!",
}


async def test_planner_picks_quantity_says_it_and_delivers(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(PLAN)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("토르켈, 나무 좀 해줘")
    await rig.until(lambda: any("모았어" in text for text in rig.said()))
    assert "해 지기 전에 10개쯤 해 올게!" in rig.said()
    assert rig.wood() >= 10
    prompt = model.prompts[0]
    assert "나무 좀 해줘" in prompt and "[나] 체력" in prompt and "[가능한 최대 수량]" in prompt
    assert "[제작 메뉴]" in prompt and "[망치 메뉴]" in prompt
    assert rig.world.bot.equipped == "돌도끼"


async def test_rejected_plan_twice_is_reported_not_guessed(make_rig: Callable[..., Any]) -> None:
    bad = {**PLAN, "steps": [{"id": "s1", "skill": "equip", "args": {"item": "청동도끼"}}]}
    rig: Rig = await make_rig(planner=Planner(ScriptedModel(bad, bad)))
    rig.world.leader_says("나무 좀 해줘")
    await rig.until(lambda: any("계획을 못 세웠어" in text for text in rig.said()))
    assert rig.wood() == 0
    assert any(d.kind == "fail" for d in rig.controller.decisions)


async def test_known_commands_start_at_once_without_the_planner(make_rig: Callable[..., Any]) -> None:
    # 실게임에서 "따라와"가 플래너로 가서 20초 뒤 엉뚱한 중단 조건(체력 10.0)으로 바로 멈췄다.
    model = ScriptedModel()
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("따라와")
    await rig.until(lambda: (goal := rig.controller.current()) is not None and goal.kind == "follow", 5)
    await rig.until(lambda: "응, 따라갈게." in rig.said(), timeout=5)
    rig.world.leader_says("나무 3개 캐줘")
    await rig.until(lambda: any("모았어" in text for text in rig.said()))
    assert "나무 3개 해 올게." in rig.said()
    assert model.prompts == []


async def test_small_talk_is_answered_by_the_planner_without_moving(make_rig: Callable[..., Any]) -> None:
    hello = {
        "interpretation_ko": "인사",
        "quantity": None,
        "assumptions": [],
        "steps": [],
        "abort_if": [],
        "speech_gist_ko": "안녕! 나 여기 있어.",
    }
    model = ScriptedModel(hello)
    rig: Rig = await make_rig(planner=Planner(model))
    start = (rig.world.bot.x, rig.world.bot.z)
    rig.world.leader_says("ㅎㅇ")
    await rig.until(lambda: "안녕! 나 여기 있어." in rig.said(), timeout=5)
    await rig.until(lambda: rig.controller.current() is None, timeout=5)
    assert (rig.world.bot.x, rig.world.bot.z) == start
    assert len(model.prompts) == 1 and "ㅎㅇ" in model.prompts[0]


class QuotaSpent:
    async def generate_json(self, **_: Any) -> tuple[dict[str, Any], Any]:
        raise ModelError("gemini-3.8-flash call failed (429): limit: 20 requests per day", status=429)


async def test_spent_model_quota_is_explained_with_what_still_works(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(planner=Planner(QuotaSpent()))
    rig.world.leader_says("ㅎㅇ")
    await rig.until(lambda: any("사용 한도" in text for text in rig.said()), timeout=5)
    line = next(text for text in rig.said() if "사용 한도" in text)
    assert "따라와" in line and "나무 10개 캐줘" in line


async def test_threat_decision_chooses_to_fight(make_rig: Callable[..., Any]) -> None:
    runner = DecisionRunner({"threat_response": RuleDecider()})
    rig: Rig = await make_rig(decider=runner)
    rig.world.spawn(greydwarf(rig.world.bot.x + 6, rig.world.bot.z))
    await rig.until(lambda: "7:900" not in rig.world.entities, timeout=40)
    threat = [d for d in rig.controller.decisions if d.kind == "threat"]
    assert threat and "equip_best_then_fight" in threat[0].reason_ko
    assert not rig.world.bot.dead


class SlowDecider:
    name = "jev"

    async def decide(self, point: Point, state: str, context: dict[str, Any]) -> dict[str, Answer]:
        await asyncio.sleep(5)
        return {}


async def test_decision_timeout_has_no_hidden_default(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(decider=DecisionRunner({"threat_response": SlowDecider()}))
    rig.world.spawn(greydwarf(rig.world.bot.x + 2, rig.world.bot.z))
    await rig.until(lambda: any(d.kind == "threat" for d in rig.controller.decisions), timeout=10)
    threat = next(d for d in rig.controller.decisions if d.kind == "threat")
    assert "timeout" in threat.reason_ko and "반사에 맡김" in threat.reason_ko
    assert not any(g.kind == "defend" for g in rig.controller.pending)
    assert rig.controller.current() is None


async def test_stopping_a_plan_stops_the_step_it_is_on(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 계획 목표가 멈춘 뒤에도 그 계획의 단계(싸움)가 따로 계속 돌아,
    # 싸움 두 개가 한 몸을 같이 움직였다. 멈추면 지금 하던 단계도 멈춘다.
    rig: Rig = await make_rig(planner=Planner(ScriptedModel(PLAN)))
    rig.world.leader_says("토르켈, 나무 좀 해줘")
    await rig.until(lambda: rig.wood() >= 1, 30)
    rig.world.leader_says("멈춰")
    await rig.until(lambda: "알겠어, 멈출게." in rig.said(), 5)
    stopped_at = rig.wood()
    await asyncio.sleep(3.0)
    assert rig.wood() <= stopped_at + 1
    assert not any("모았어" in text for text in rig.said())


PORTAL_FIRST = {
    **PLAN,
    "steps": [{"id": "s1", "skill": "use_portal", "args": {}}],
    "abort_if": [],
    "speech_gist_ko": "포털로 가 볼게!",
}


async def test_when_a_step_fails_it_thinks_again_with_what_happened(make_rig: Callable[..., Any]) -> None:
    # 실게임(새 월드, 2026-10-18): 첫 방법(나뭇가지 줍기)이 한 번 안 되자 보고만 하고 9분을 서 있었다.
    # 사람은 안 된 것을 보고 다른 방법을 찾거나 묻는다. 무엇을 할지는 모델이 실패를 보고 정한다.
    model = ScriptedModel(PORTAL_FIRST, PLAN)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("나무 좀 해줘")
    await rig.until(lambda: any("모았어" in text for text in rig.said()))
    assert rig.wood() >= 10 and len(model.prompts) == 2
    assert "[이 부탁으로 해 본 것]" in model.prompts[1] and "포털이 안 보여" in model.prompts[1]


async def test_it_gives_up_after_a_few_tries_and_says_why(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(*[PORTAL_FIRST] * 6)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("집에 가자")
    await rig.until(lambda: "포털이 안 보여" in rig.said())
    assert len(model.prompts) == 3


async def test_a_plan_that_gets_partway_is_followed_by_thinking_again(make_rig: Callable[..., Any]) -> None:
    # 실게임(새 월드): 도끼 레시피는 재료를 주워야 메뉴에 뜬다. 모델은 재료 모으기까지만 계획할 수 있었고,
    # 그 계획이 끝나자 부탁(도끼)을 다 한 것으로 쳤다.
    first = {
        **PLAN,
        "steps": [{"id": "s1", "skill": "gather_wood", "args": {"count": 3}}],
        "abort_if": [],
        "speech_gist_ko": "나무부터 모을게",
        "think_again_after": True,
    }
    first["quantity"] = {"value": 3, "basis": "purpose", "cites": []}
    then = {**PLAN, "steps": [], "speech_gist_ko": "다 모았으니 이제 만들어 볼게", "abort_if": []}
    model = ScriptedModel(first, then)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("도끼 만들어 줘")
    await rig.until(lambda: "다 모았으니 이제 만들어 볼게" in rig.said())
    assert "gather_wood(count=3): 됨" in model.prompts[1]


async def test_a_job_stopped_by_getting_hurt_is_picked_up_after_healing(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-20): 나무를 하다 그레이링에게 맞아 "많이 다쳐서 멈췄어"로 리더의 부탁 둘을 끝내고 잊었다.
    # 사람은 몸을 추스른 뒤 하던 일로 돌아간다.
    hurt_stop = {**PLAN, "abort_if": [{"cond": "hp_below", "value": 0.5}]}
    model = ScriptedModel(hurt_stop, PLAN)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.controller.stance = "wait"
    rig.world.leader_says("토르켈, 나무 좀 해줘")
    await rig.until(
        lambda: rig.controller.current() is not None and rig.world.commands.get("attack", 0) > 0, 30
    )
    rig.world.bot.hp = 5.0
    await rig.until(lambda: any("다 나으면" in text for text in rig.said()), 20)
    # 쉬는 동안 리더를 따라다니기 시작해도(자기 일) 다 나으면 리더의 부탁으로 돌아간다(실게임 2026-10-20).
    from thorkell.control.goals import Goal, Tier

    rig.controller.request(Goal("follow", Tier.AGENDA, source="self"))
    await rig.until(lambda: (g := rig.controller.current()) is not None and g.kind == "follow", 10)
    rig.world.bot.hp = rig.world.bot.hp_max
    await rig.until(lambda: (g := rig.controller.current()) is not None and g.kind == "request", 5)
    await rig.until(lambda: rig.wood() >= 10, 90)
    assert len(model.prompts) == 2
    assert "많이 다쳐서 멈췄어" in model.prompts[1]
