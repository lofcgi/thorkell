"""Going through portals in the simulator: on purpose (a plan step) and after the leader."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig, ScriptedModel

from thorkell.control.goals import Goal, Tier
from thorkell.plan.planner import Planner
from thorkell.sim.world import SimEntity, SimWorld


def portals(
    home: tuple[float, float] = (6.0, 4.0), far: tuple[float, float] = (900.0, 900.0)
) -> list[SimEntity]:
    here = SimEntity("7:60", "portal", "포털", home[0], home[1], tag="집", partner="7:61")
    there = SimEntity("7:61", "portal", "포털", far[0], far[1], tag="집", partner="7:60")
    return [here, there]


async def test_it_walks_into_a_portal_and_comes_out_at_the_other_one(make_rig: Callable[..., Any]) -> None:
    # 리허설(2026-10-18): 리더가 "포탈 들어가면 집으로 갈 수 있어"라고 했지만 포탈을 못 봤고 쓸 줄도 몰랐다.
    plan = {
        "interpretation_ko": "포털로 집에 가자는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [{"id": "s1", "skill": "use_portal", "args": {"tag": "집"}}],
        "abort_if": [],
        "speech_gist_ko": "포털로 가 볼게!",
    }
    rig: Rig = await make_rig(world=SimWorld(portals()), planner=Planner(ScriptedModel(plan)))
    rig.controller.stance = "wait"
    rig.world.leader_says("포탈 들어가면 집으로 갈 수 있어")
    await rig.until(lambda: rig.world.bot.x > 800, 20)
    await rig.until(lambda: any("포털을 지나왔어" in text for text in rig.said()), 10)


async def test_when_the_leader_steps_into_a_portal_it_follows(make_rig: Callable[..., Any]) -> None:
    world = SimWorld(portals(home=(8.0, 0.0)), leader_at=(7.0, 0.0))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "follow"
    rig.controller.request(Goal("follow", Tier.USER, source="leader"))
    await rig.until(lambda: rig.controller.current() is not None, 5)
    # 리더가 포털에 들어가 저쪽으로 갔다(봇에게는 리더가 포털 앞에서 사라진 것으로 보인다).
    rig.world.leader = (902.0, 900.0)
    await rig.until(lambda: rig.world.bot.x > 800, 30)
    await rig.until(lambda: rig.world.distance(*rig.world.leader) < 6, 20)


def test_the_planner_sees_a_portal_s_tag_and_a_door_s_state() -> None:
    from thorkell.mind.store import Store
    from thorkell.plan.situation import Known, describe
    from thorkell.world.memory import WorldMemory

    scene = {
        "nearby": [
            {
                "id": "7:60",
                "kind": "portal",
                "name": "Teleport",
                "tag": "집",
                "connected": True,
                "distance": 6.0,
                "pos": [6.0, 0.0, 4.0],
            },
            {
                "id": "7:62",
                "kind": "door",
                "name": "나무 문",
                "open": False,
                "distance": 3.0,
                "pos": [3.0, 0.0, 0.0],
            },
        ]
    }
    text = describe({"pos": [0.0, 0.0, 0.0], "hp": 25, "hp_max": 25}, scene, WorldMemory(Store()), Known())
    assert "Teleport '집'(이어짐)" in text and "나무 문(닫힘)" in text
