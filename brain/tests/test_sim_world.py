from __future__ import annotations

import itertools
from typing import Any

from thorkell.sim.world import SimEntity, SimWorld, eikthyr, greydwarf

_ids = itertools.count(1)


def _run(world: SimWorld, op: str, args: dict[str, Any], seconds: float = 30.0) -> dict[str, Any]:
    cmd_id = f"c{next(_ids)}"
    world.submit({"id": cmd_id, "op": op, "args": args})
    for _ in range(int(seconds / 0.05)):
        world.step(0.05)
        for message in world.outbox:
            if message["t"] == "result" and message["cmd_id"] == cmd_id:
                return message
    raise AssertionError(f"{op} did not finish in {seconds}s")


def test_walking_to_an_item_auto_picks_it_up_like_the_game() -> None:
    world = SimWorld([SimEntity("7:50", "item", "나무", 5.0, 0.0, stack=3)])
    result = _run(world, "move_to", {"target": {"id": "7:50"}, "arrive_radius": 1.2})
    assert (result["status"], result["code"]) == ("succeeded", "picked_up")
    assert result["evidence"]["added"] == 3
    assert result["evidence"]["auto"] is True
    assert world.bot.inventory["나무"] == 3
    assert "7:50" not in world.entities


def test_items_near_the_path_are_picked_up_on_the_way() -> None:
    world = SimWorld([SimEntity("7:50", "item", "나무", 4.0, 1.0, stack=2)])
    result = _run(world, "move_to", {"target": {"pos": [8.0, 0.0, 0.0]}, "arrive_radius": 0.5})
    assert result["code"] == "arrived"
    assert world.bot.inventory.get("나무") == 2


def test_items_out_of_auto_pickup_range_stay_put() -> None:
    world = SimWorld([SimEntity("7:50", "item", "나무", 4.0, 3.0, stack=2)])
    _run(world, "move_to", {"target": {"pos": [8.0, 0.0, 0.0]}, "arrive_radius": 0.5})
    assert "나무" not in world.bot.inventory
    assert "7:50" in world.entities


def test_items_the_leader_drops_are_not_auto_picked_up() -> None:
    # 게임은 플레이어가 버린 아이템의 자동 줍기를 끈다(ItemDrop.OnPlayerDrop). 건네준 것은 직접 주워야 한다.
    world = SimWorld([])
    dropped = world.leader_drops("돌도끼")
    result = _run(world, "move_to", {"target": {"pos": [dropped.x, 0.0, dropped.z]}, "arrive_radius": 0.3})
    assert result["code"] == "arrived"
    assert "돌도끼" not in world.bot.inventory
    assert _run(world, "pickup", {"id": dropped.id}, seconds=1)["code"] == "picked_up"
    assert world.bot.inventory["돌도끼"] == 1


def test_the_defence_reflex_leaves_bosses_and_bow_fights_to_the_brain() -> None:
    # 실게임(2026-10-17): 활을 든 채 에이크쉬르에게 맞자 반사가 보스에게 달려가 근접 반격했고,
    # 뿔에 세 번 맞았다.
    for creature, weapon in ((eikthyr(1.0, 0.0), "곤봉"), (greydwarf(1.0, 0.0), "활")):
        world = SimWorld([creature])
        world.bot.inventory = {weapon: 1, "나무 화살": 10}
        world.bot.equipped = weapon
        world.bot.hp = world.bot.hp_max = 200.0
        for _ in range(40):
            world.step(0.1)
        assert world.reflex_attacker is None, (creature.name, weapon)
        assert not any(e.get("kind") == "reflex_engaged" for e in world.outbox if e["t"] == "event")
