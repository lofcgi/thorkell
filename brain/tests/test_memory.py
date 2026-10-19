from __future__ import annotations

from thorkell.mind.store import Store
from thorkell.world.memory import WorldMemory


def creature(
    name: str, key: str, distance: float, pos: list[float], size: str = "medium"
) -> dict[str, object]:
    return {
        "id": f"1:{key}",
        "kind": "creature",
        "name": name,
        "key": key,
        "distance": distance,
        "pos": pos,
        "size": size,
    }


def test_a_creature_seen_up_close_is_recognised_later_from_afar() -> None:
    memory = WorldMemory(Store())
    far = creature("", "$enemy_boar", 30, [30, 0, 0], "small")
    assert memory.creature_label(far) == "처음 보는 작은 생물"

    learned = memory.on_scene(
        {"nearby": [creature("멧돼지", "$enemy_boar", 6, [6, 0, 0], "small")]}, [0, 0, 0]
    )
    assert learned == ["멧돼지"]
    assert memory.creature_label(far) == "멧돼지(멀리)"
    assert memory.knows_creature("멧돼지")
    assert not memory.knows_creature("사슴")


def test_places_are_remembered_once_and_persist_in_the_store() -> None:
    store = Store()
    memory = WorldMemory(store)
    scene = {
        "nearby": [
            {"id": "1:2", "kind": "station", "name": "작업대", "distance": 5, "pos": [10, 30, 10]},
            {"id": "1:3", "kind": "altar", "name": "신비한 제단", "distance": 20, "pos": [100, 30, 0]},
        ]
    }
    memory.on_scene(scene, [0, 30, 0])
    memory.on_scene(scene, [0, 30, 0])
    again = WorldMemory(store)
    assert [(p.name, p.kind) for p in again.places()] == [("신비한 제단", "altar"), ("작업대", "station")]
    assert again.place("작업대") is not None and again.place("작업대").pos == (10.0, 30.0, 10.0)


def test_resource_sightings_answer_where_to_find_something() -> None:
    memory = WorldMemory(Store())
    memory.on_scene(
        {
            "nearby": [
                {"id": "1:5", "kind": "pickable", "name": "부싯돌", "distance": 30, "pos": [30, 0, 0]},
                {"id": "1:6", "kind": "pickable", "name": "부싯돌", "distance": 31, "pos": [31, 0, 1]},
                {"id": "1:7", "kind": "pickable", "name": "돌", "distance": 8, "pos": [8, 0, 0]},
            ]
        },
        [0, 0, 0],
    )
    assert memory.where_seen("부싯돌", [100, 0, 0]) == (31.0, 0.0, 1.0)
    assert memory.where_seen("버섯", [0, 0, 0]) is None
    assert set(memory.seen_names()) == {"부싯돌", "돌"}


def test_where_an_item_came_from_is_learned_from_experience() -> None:
    memory = WorldMemory(Store())
    assert memory.sources("나무") == []
    assert memory.learn_source("나무", "pickable", "나뭇가지") is True
    assert memory.learn_source("나무", "pickable", "나뭇가지") is False
    memory.learn_source("나무", "tree", "나무")
    assert memory.sources("나무") == [("pickable", "나뭇가지"), ("tree", "나무")]
    assert memory.yields("pickable", "나뭇가지") == ["나무"]
