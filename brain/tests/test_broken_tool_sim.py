"""A tool that wears out in the middle of a job (real game 2026-10-19: the stone axe broke while chopping 20
wood, and Thorkell tried to pick it up again every 6 seconds). He notices it is broken, says so, and thinks
the leader's words over with what happened instead of giving up."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from conftest import Rig, ScriptedModel

from thorkell.control.goals import Goal, Tier
from thorkell.plan.planner import Planner
from thorkell.sim.world import SimEntity, SimWorld, forest


def camp() -> SimWorld:
    world = SimWorld(forest(3))
    # 한 번에 나무 한 그루(2번)와 통나무 둘(2번씩)을 넘어뜨릴 만큼만 버틴다.
    world.bot.inventory = {"돌도끼": 1, "돌": 4}
    world.bot.known = {"돌도끼", "돌", "나무"}
    world.bot.wear = {"돌도끼": 6}
    world.bot.foods = {"라즈베리": 1200.0}
    return world


async def test_a_broken_axe_is_noticed_and_the_request_thought_over(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(
        {
            "interpretation_ko": "도끼가 부러졌으니 새로 만들고 나머지를 한다",
            "steps": [
                {"id": "s1", "skill": "craft", "args": {"item": "돌도끼"}},
                {"id": "s2", "skill": "gather_wood", "args": {"count": 7}, "after": ["s1"]},
            ],
            "speech_gist_ko": "도끼가 부러졌네. 새로 만들어서 마저 할게",
        }
    )
    rig: Rig = await make_rig(world=camp(), planner=Planner(model))
    rig.controller.stance = "wait"
    rig.world.leader_says("나무 12개 캐줘")
    await rig.until(lambda: "돌도끼가 부러졌어" in rig.said(), 90)
    await rig.until(lambda: rig.wood() >= 12, 120)
    prompt = model.prompts[0]
    assert "[요청]\n나무 12개 캐줘" in prompt
    assert "돌도끼(부러짐) 1" in prompt
    assert "[이 부탁으로 해 본 것] 나무 모으기 (10/12): 안 됨 — 돌도끼가 부러졌어" in prompt
    assert rig.world.bot.broken.get("돌도끼", 0) >= 1


@pytest.mark.usefixtures("english")
async def test_a_broken_axe_in_english(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(
        {
            "interpretation_en": "the axe broke, so make a new one and finish",
            "steps": [
                {"id": "s1", "skill": "craft", "args": {"item": "Stone Axe"}},
                {"id": "s2", "skill": "gather_wood", "args": {"count": 7}, "after": ["s1"]},
            ],
            "speech_gist_en": "My axe broke. I'll make a new one and finish the job.",
        }
    )
    rig: Rig = await make_rig(world=camp(), planner=Planner(model))
    rig.controller.stance = "wait"
    rig.world.leader_says("Can you chop 12 wood for me?")
    await rig.until(lambda: "My Stone Axe broke" in rig.said(), 90)
    await rig.until(lambda: rig.wood() >= 12, 120)
    prompt = model.prompts[0]
    assert "Stone Axe (broken) 1" in prompt
    assert "[Tried for this request] gathering Wood (10/12): didn't work — My Stone Axe broke" in prompt
    assert "My axe broke. I'll make a new one and finish the job." in rig.said()


async def test_without_a_planner_it_only_says_the_axe_broke(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(world=camp())
    rig.controller.stance = "wait"
    rig.world.leader_says("나무 12개 캐줘")
    await rig.until(lambda: "돌도끼가 부러졌어" in rig.said(), 90)
    # 부러진 도끼를 다시 들려고 하지 않는다.
    equips = rig.world.commands.get("equip", 0)
    await rig.until(lambda: rig.controller.current() is None, 10)
    assert rig.world.commands.get("equip", 0) == equips


async def test_a_log_it_cannot_reach_is_left_for_another(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-19): 쉼터에 쓸 나무를 하다 닿지 않는 통나무 하나로 10분 동안 다가가기만 했다.
    world = SimWorld(forest(2))
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼", "나무"}
    world.bot.foods = {"라즈베리": 1200.0}
    stuck = SimEntity("7:66", "log", "", 3.0, -2.0, 40.0, 40.0, drops=[("나무", 5)], unreachable=True)
    world.spawn(stuck)
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather_wood", Tier.USER, {"count": 10}, source="leader"))
    await rig.until(lambda: "나무 10개 모았어" in rig.said() or rig.wood() >= 10, 120)
    assert stuck.id in rig.world.entities


async def test_a_tree_too_hard_for_the_axe_is_left_before_the_axe_wears_out(
    make_rig: Callable[..., Any],
) -> None:
    # 실게임(2026-10-19): 돌도끼로 안 베어지는 나무를 85번 쳐서 도끼 둘이 부러졌다.
    world = SimWorld(forest(2))
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼", "나무"}
    world.bot.wear = {"돌도끼": 14}
    world.bot.foods = {"라즈베리": 1200.0}
    oaks = [
        SimEntity(
            f"7:7{i}",
            "tree",
            "참나무",
            3.0 + i,
            -2.0,
            80.0,
            80.0,
            tier=2,
            becomes=[("log", "", 40.0, [("나무", 5)])],
        )
        for i in range(2)
    ]
    for oak in oaks:
        world.spawn(oak)
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather_wood", Tier.USER, {"count": 10}, source="leader"))
    await rig.until(lambda: "나무 10개 모았어" in rig.said(), 120)
    assert all(oak.hp == oak.max_hp for oak in oaks[1:])  # 한 그루에서 겪고 같은 종류는 건너뛴다
    assert not rig.world.bot.broken


async def test_trees_out_of_sight_are_looked_for_farther_out(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-20): 물가에서 제자리 20m만 둘러보고 "벨 나무가 안 보여"로 나무 부탁을 끝냈다.
    trees = [
        SimEntity(
            f"7:8{i}", "tree", "", -60.0 + 3 * i, 45.0, 40.0, 40.0, becomes=[("log", "", 40.0, [("나무", 5)])]
        )
        for i in range(2)
    ]
    world = SimWorld(trees)
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼", "나무"}
    world.bot.foods = {"라즈베리": 1200.0}
    rig: Rig = await make_rig(world=world, time_scale=16)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather_wood", Tier.USER, {"count": 5}, source="leader"))
    await rig.until(
        lambda: any(
            d.kind in ("done", "fail") and d.goal_kind == "gather_wood" for d in rig.controller.decisions
        ),
        120,
    )
    done = [d for d in rig.controller.decisions if d.kind == "done" and d.goal_kind == "gather_wood"]
    assert done, rig.said()


async def test_trees_it_cannot_reach_are_named_as_such(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-20): 강 건너 나무만 보이는데 "벨 나무가 안 보여"라고 해서, 계획이 이유를 모른 채
    # 같은 시도를 되풀이했다.
    world = SimWorld([SimEntity("7:91", "tree", "", 5.0, 0.0, 40.0, 40.0, unreachable=True)])
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼", "나무"}
    world.bot.foods = {"라즈베리": 1200.0}
    rig: Rig = await make_rig(world=world, time_scale=16)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather_wood", Tier.USER, {"count": 5}, source="leader"))
    await rig.until(
        lambda: any(d.kind == "fail" and d.goal_kind == "gather_wood" for d in rig.controller.decisions), 120
    )
    failed = next(d for d in rig.controller.decisions if d.kind == "fail" and d.goal_kind == "gather_wood")
    assert failed.reason_ko == "나무는 보이는데 다가갈 수가 없어(물 건너편이거나 막혀 있어)"
