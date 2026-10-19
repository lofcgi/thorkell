"""Sleeping with the leader: the night passes only when every player lies in their own bed."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig

from thorkell.control.goals import Goal, Tier
from thorkell.sim.world import SimEntity, SimWorld


def house(night: bool = True) -> SimWorld:
    """The leader's hut: walls and a roof, a fire, the leader's bed and a workbench."""
    world = SimWorld(
        [
            SimEntity("7:301", "piece", "나무 벽", 0.0, 2.5),
            SimEntity("7:302", "piece", "나무 벽", 2.5, 0.0),
            SimEntity("7:303", "piece", "나무 벽", -2.5, 0.0),
            SimEntity("7:304", "piece", "나무 벽", 0.0, -2.5),
            SimEntity("7:305", "piece", "초가지붕 26°", 0.0, 0.0),
            SimEntity("7:306", "station", "작업대", -2.0, -2.0, creator="Leader"),
            SimEntity("7:307", "bed", "침대", -1.0, 0.0, owner="Leader"),
        ],
        leader_at=(-1.0, 0.0),
    )
    fire = world.spawn(SimEntity("7:308", "fire", "모닥불", 0.0, 1.5))
    fire.fuel = 5.0
    world.day_fraction = 0.8 if night else 0.4
    world.bot.inventory = {"나무": 20, "망치": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 1200.0}
    return world


async def test_when_the_leader_lies_down_at_night_it_builds_its_own_bed_and_sleeps(
    make_rig: Callable[..., Any],
) -> None:
    world = house()
    world.leader_in_bed = True
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    await rig.until(lambda: not rig.world.night, 90)
    beds = [e for e in rig.world.entities.values() if e.kind == "bed"]
    assert sorted(e.owner for e in beds) == ["Leader", "Thorkell"]
    assert rig.world.bot.inventory["나무"] == 12
    await rig.until(lambda: any("잘 잤" in text for text in rig.said()), 20)


async def test_asked_to_sleep_by_day_it_says_what_the_game_says(make_rig: Callable[..., Any]) -> None:
    world = house(night=False)
    world.spawn(SimEntity("7:309", "bed", "침대", 0.6, 0.0, owner="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("sleep", Tier.USER, source="leader"))
    await rig.until(lambda: any("지금은 잘 수 없" in text for text in rig.said()), 30)
    assert not rig.world.bot.in_bed
