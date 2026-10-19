"""Hunting and cooking against the simulator."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig

from thorkell.control.goals import Goal, Tier
from thorkell.sim.world import SimEntity, SimWorld, boar, deer


def field(*creatures: SimEntity) -> SimWorld:
    world = SimWorld(list(creatures))
    world.bot.foods = {"라즈베리": 1200.0}
    return world


async def test_hunts_a_boar_with_a_club_and_learns_what_it_drops(make_rig: Callable[..., Any]) -> None:
    world = field(boar(9.0, 2.0))
    world.bot.inventory = {"곤봉": 1}
    world.bot.known = {"곤봉"}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "멧돼지", "count": 1}, source="leader"))
    await rig.until(lambda: "멧돼지를 1마리 잡았어" in rig.said(), 60)
    assert rig.world.bot.inventory.get("날고기", 0) >= 1
    assert ("creature", "멧돼지") in rig.controller.world.sources("날고기")


async def test_shoots_a_deer_from_a_distance_with_a_bow(make_rig: Callable[..., Any]) -> None:
    world = field(deer(22.0, 0.0))
    world.bot.inventory = {"활": 1, "나무 화살": 20}
    world.bot.known = {"활", "나무 화살"}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "사슴", "count": 1}, source="leader"))
    await rig.until(lambda: "사슴을 1마리 잡았어" in rig.said(), 60)
    assert rig.world.bot.inventory["나무 화살"] < 20
    assert rig.world.bot.inventory.get("사슴 트로피", 0) == 1


async def test_cooks_meat_by_building_a_fire_and_a_rack(make_rig: Callable[..., Any]) -> None:
    world = field()
    world.bot.inventory = {"날고기": 2, "나무": 12, "돌": 6, "망치": 1}
    world.bot.known = set(world.bot.inventory)
    world.spawn(SimEntity("7:300", "station", "작업대", -6.0, 0.0, creator="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("cook", Tier.USER, {"item": "날고기", "count": 2}, source="leader"))
    await rig.until(lambda: any("구웠어" in text for text in rig.said()), 90)
    assert rig.world.bot.inventory.get("구운 고기", 0) == 2
    assert any(e.kind == "fire" for e in rig.world.entities.values())
    assert any(e.kind == "cooking" for e in rig.world.entities.values())


async def test_a_hunted_creature_fighting_back_does_not_start_a_separate_defence(
    make_rig: Callable[..., Any],
) -> None:
    world = field(boar(5.0, 0.0))
    world.bot.inventory = {"곤봉": 1}
    world.bot.known = {"곤봉"}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "멧돼지", "count": 1}, source="leader"))
    await rig.until(lambda: any(d.kind in ("done", "fail") for d in rig.controller.decisions), 60)
    assert [d.goal_kind for d in rig.controller.decisions if d.kind == "adopt"] == ["hunt"]


async def test_a_creature_that_runs_out_of_sight_is_not_counted_as_caught(
    make_rig: Callable[..., Any],
) -> None:
    # 보이지 않게 된 것과 쓰러진 것은 다르다. 쓰러지는 걸 봐야 잡은 것이다.
    world = field(boar(9.0, 2.0))
    world.bot.inventory = {"곤봉": 1}
    world.bot.known = {"곤봉"}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "멧돼지", "count": 1}, source="leader"))
    target = next(e for e in rig.world.entities.values() if e.name == "멧돼지")
    target.hp = target.max_hp = 1000.0
    await rig.until(lambda: target.hp < target.max_hp, 30)
    del rig.world.entities[target.id]  # 싸우다 멀리 달아나 안 보인다
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "hunt" for d in rig.controller.decisions),
        60,
    )
    assert not any(d.kind == "done" and d.goal_kind == "hunt" for d in rig.controller.decisions)


async def test_without_a_bow_it_sneaks_up_on_a_deer_once_it_knows_they_run(
    make_rig: Callable[..., Any],
) -> None:
    # 새 월드에서는 활이 없다(활에 사슴 가죽이 든다). 사람은 웅크리고 몰래 다가가 친다.
    # 쫓아가면 달아난다는 것을 겪어서 알게 되면(기억) 몰래 다가간다. 사슴은 달리기로는 못 따라잡는다.
    from thorkell.mind.mind import Mind
    from thorkell.mind.store import Store

    world = field(deer(22.0, 0.0))
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼"}
    mind = Mind(Store())
    rig: Rig = await make_rig(world=world, mind=mind)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "사슴", "count": 1}, source="leader"))
    await rig.until(lambda: "사슴을 1마리 잡았어" in rig.said(), 120)
    assert rig.world.bot.inventory.get("사슴 트로피", 0) == 1
    assert any(f.predicate == "flees" for f in mind.store.facts_about("사슴"))


async def test_searching_goes_farther_out_until_it_finds_a_deer(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-20): 제자리 둘레만 돌다 "사슴이 안 보여"로 리더에게 물었다. 들판 쪽으로 더 나가 본다.
    world = field(deer(-70.0, 95.0))
    world.bot.inventory = {"돌도끼": 1}
    world.bot.known = {"돌도끼"}
    rig: Rig = await make_rig(world=world, time_scale=16)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("search", Tier.USER, {"name": "사슴"}, source="leader"))
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "search" for d in rig.controller.decisions),
        120,
    )
    assert any(d.kind == "done" and d.goal_kind == "search" for d in rig.controller.decisions), rig.said()
