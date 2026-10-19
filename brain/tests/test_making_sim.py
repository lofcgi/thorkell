"""Gathering, crafting and building against the simulator: the bot starts with nothing, like a new player."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from conftest import Rig

from thorkell.control.goals import Goal, Tier
from thorkell.control.making import _game_says_since
from thorkell.sim.world import SimEntity, SimWorld, forest, pickable


def meadow() -> SimWorld:
    """Spawn-like ground: branches and stones lying about, a few trees further off, empty hands, fed."""
    entities: list[SimEntity] = forest(2)
    for index in range(6):
        entities.append(pickable("나뭇가지", ("나무", 1), 3.0 + 2.0 * index, -4.0, f"7:{100 + index}"))
    for index in range(4):
        entities.append(pickable("돌", ("돌", 1), -3.0 - 2.0 * index, 4.0, f"7:{200 + index}"))
    world = SimWorld(entities)
    world.bot.foods = {"라즈베리": 1200.0}
    return world


async def test_crafts_a_hammer_from_nothing_by_gathering_what_it_needs(
    make_rig: Callable[..., Any],
) -> None:
    rig: Rig = await make_rig(world=meadow())
    # 재료를 가져 본 적이 없으면 게임이 레시피를 열어 주지 않는다. 사람처럼 "아직 몰라"라고 한다.
    rig.controller.request(Goal("craft", Tier.USER, {"item": "망치"}, source="leader"))
    await rig.until(lambda: "망치는 아직 만드는 법을 몰라" in rig.said(), 20)
    # 나무를 주워 보면(나뭇가지가 나무를 주는지는 주워 보고 안다) 돌과 함께 레시피가 열린다.
    rig.controller.request(Goal("gather", Tier.USER, {"item": "나무", "count": 1}, source="leader"))
    rig.controller.request(Goal("gather", Tier.USER, {"item": "돌", "count": 1}, source="leader"))
    await rig.until(lambda: rig.world.bot.inventory.get("돌", 0) >= 1 and rig.wood() >= 1, 40)
    await rig.until(lambda: rig.controller.current() is None and not rig.controller.pending, 10)
    rig.controller.request(Goal("craft", Tier.USER, {"item": "망치"}, source="leader"))
    await rig.until(lambda: rig.world.bot.inventory.get("망치", 0) >= 1, 60)
    # 나뭇가지에서 나무가 나온다는 것은 주워 보고 배웠다.
    assert rig.controller.world.sources("나무")[0] == ("pickable", "나뭇가지")


async def test_builds_a_workbench_after_making_a_hammer(make_rig: Callable[..., Any]) -> None:
    world = meadow()
    world.bot.inventory = {"나무": 13, "돌": 2}
    world.bot.known = {"나무", "돌"}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("build", Tier.USER, {"piece": "작업대"}, source="leader"))
    await rig.until(lambda: any(e.name == "작업대" for e in rig.world.entities.values()), 60)
    bench = next(e for e in rig.world.entities.values() if e.name == "작업대")
    assert bench.creator == "Thorkell"
    assert rig.world.bot.inventory["망치"] == 1
    await rig.until(lambda: rig.controller.world.place("작업대") is not None, 5)


async def test_a_workbench_without_a_roof_is_reported_in_the_games_words(
    make_rig: Callable[..., Any],
) -> None:
    world = meadow()
    world.bot.inventory = {"나무": 30, "돌": 2, "망치": 1}
    world.bot.known = {"나무", "돌", "망치"}
    world.spawn(SimEntity("7:300", "station", "작업대", 2.0, 0.0, creator="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("craft", Tier.USER, {"item": "나무 화살"}, source="leader"))
    await rig.until(lambda: any(d.kind == "fail" for d in rig.controller.decisions), 30)
    failure = next(d for d in rig.controller.decisions if d.kind == "fail")
    assert "작업대를 쓸 수가 없어" in failure.reason_ko
    assert "지붕" in failure.reason_ko


async def test_puts_walls_and_a_roof_over_the_workbench_so_it_can_be_used(
    make_rig: Callable[..., Any],
) -> None:
    world = meadow()
    world.bot.inventory = {"나무": 30, "돌": 2, "망치": 1}
    world.bot.known = {"나무", "돌", "망치"}
    world.spawn(SimEntity("7:300", "station", "작업대", 2.0, 0.0, creator="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("shelter", Tier.USER, {}, source="leader"))
    await rig.until(lambda: "작업대에 벽이랑 지붕을 올렸어. 이제 쓸 수 있어!" in rig.said(), 60)
    assert rig.world.roofed(2.0, 0.0)
    rig.controller.request(Goal("craft", Tier.USER, {"item": "나무 화살"}, source="leader"))
    await rig.until(lambda: rig.world.bot.inventory.get("나무 화살", 0) >= 20, 30)


async def test_gathering_from_a_named_bush_collects_what_it_gives(make_rig: Callable[..., Any]) -> None:
    # 실제 플래너는 "식량이 필요해"에 gather(item="라즈베리 덤불")을 냈다.
    # 처음 보는 덤불이면 따 보고 나온 것을 모은다.
    world = meadow()
    for index in range(3):
        world.spawn(pickable("라즈베리 덤불", ("라즈베리", 1), 5.0, 2.0 + 2.0 * index, f"7:{400 + index}"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather", Tier.USER, {"item": "라즈베리 덤불", "count": 2}, source="leader"))
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "gather" for d in rig.controller.decisions),
        60,
    )
    assert rig.world.bot.inventory.get("라즈베리", 0) >= 2
    assert any(d.kind == "done" and d.goal_kind == "gather" for d in rig.controller.decisions)


async def test_gathering_without_a_count_takes_what_is_in_sight(make_rig: Callable[..., Any]) -> None:
    # "식량이 필요해"에 실제 플래너는 개수 없이 덤불을 따자고 했다. 개수가 없으면 보이는 만큼 딴다.
    world = meadow()
    for index in range(3):
        world.spawn(pickable("라즈베리 덤불", ("라즈베리", 1), 5.0, 2.0 + 2.0 * index, f"7:{400 + index}"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather", Tier.USER, {"item": "라즈베리 덤불"}, source="leader"))
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "gather" for d in rig.controller.decisions),
        60,
    )
    assert rig.world.bot.inventory.get("라즈베리", 0) == 3
    assert any(d.kind == "done" and d.goal_kind == "gather" for d in rig.controller.decisions)


def test_a_refusal_is_reported_only_from_messages_after_the_attempt() -> None:
    # 실게임: 작업대를 못 쓴 이유로 그 전에 뜬 "기술 강화됨 제작: 1"을 전했다.
    stale = SimpleNamespace(kind="game_message", data={"text": "기술 강화됨 제작: 1"})
    ctx = SimpleNamespace(session=SimpleNamespace(events_of=lambda kind: [stale]))
    assert _game_says_since(ctx, 1) is None  # type: ignore[arg-type]
    fresh = SimpleNamespace(kind="game_message", data={"text": "지붕이 필요합니다"})
    ctx = SimpleNamespace(session=SimpleNamespace(events_of=lambda kind: [stale, fresh]))
    assert _game_says_since(ctx, 1) == "지붕이 필요합니다"  # type: ignore[arg-type]


async def test_without_an_axe_it_gathers_wood_from_branches_not_trees(make_rig: Callable[..., Any]) -> None:
    # 실게임(새 월드): 돌 도끼에 나무가 모자라자 도끼도 없이 나무를 베러 가서 "벨 도구가 없어"로 실패했다.
    # 벨 도구가 없으면 나무는 땅에 떨어진 나뭇가지에서 얻는다. 근처 것은 이미 다 주웠다(나뭇가지에서 나무가
    # 나온다는 것은 안다). 나무는 가까이 있고 나뭇가지는 안 보이는 곳에 있다.
    entities: list[SimEntity] = forest(2)
    spots = [(48.0, 0.0), (-48.0, 0.0), (0.0, 48.0), (0.0, -48.0)]
    for index, (x, z) in enumerate(spots):
        for k in range(3):
            entities.append(pickable("나뭇가지", ("나무", 1), x + 1.5 * k, z, f"7:{100 + 3 * index + k}"))
    world = SimWorld(entities)
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.inventory = {"돌": 2}
    world.bot.known = {"돌"}
    rig: Rig = await make_rig(world=world)
    assert rig.controller.world is not None
    rig.controller.world.learn_source("나무", "pickable", "나뭇가지")
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather", Tier.USER, {"item": "나무", "count": 3}, source="leader"))
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "gather" for d in rig.controller.decisions),
        90,
    )
    assert rig.world.bot.inventory.get("나무", 0) >= 3


def test_a_building_site_is_looked_for_farther_out_before_asking() -> None:
    # 실게임(2026-10-20): 시작 신전 둘레(짓기 금지)와 비탈뿐이라 40m 안에 터가 없었다. 사람은 묻기 전에
    # 조금 더 걸어가 본다.
    import math

    from thorkell.control.making import SITE_FAR_M, _site_searches

    searches = _site_searches([0.0, 30.0, 0.0])
    assert searches[:2] == [([0.0, 30.0, 0.0], 24), ([0.0, 30.0, 0.0], 40)]
    far = searches[2:]
    assert len(far) == 8
    assert all(math.isclose(math.hypot(c[0], c[2]), SITE_FAR_M) for c, _ in far)
