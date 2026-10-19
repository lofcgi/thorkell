"""English play: what the slow brain reads and is asked (planner, fight judgment, eyes) is all English."""

from __future__ import annotations

import re
from typing import Any

import pytest
from conftest import ScriptedModel

from thorkell.mind.store import Store
from thorkell.plan.planner import Planner, context_from_scene
from thorkell.plan.situation import Known, describe
from thorkell.plan.tactics import FightView, Tactician, record_ko
from thorkell.world.memory import WorldMemory

HANGUL = re.compile(r"[가-힣]")

SCENE: dict[str, Any] = {
    "inventory": [
        {"name": "Stone Axe", "stack": 1, "weight": 2.0, "equipped": True},
        {"name": "Wood", "stack": 4, "weight": 8.0, "equipped": False},
        {"name": "Raspberries", "stack": 3, "weight": 0.3, "equipped": False, "food": {"health": 7}},
    ],
    "foods": [{"name": "Raspberries", "remaining_s": 600}],
    "weight": 10.3,
    "weight_max": 300,
    "env": {"night": False, "day_fraction": 0.4, "day": 2, "weather": "Clear"},
    "biome": "Meadows",
    "nearby": [
        {"kind": "tree", "name": "", "distance": 6.0, "pos": [6.0, 0.0, 0.0]},
        {"kind": "tree", "name": "", "distance": 9.0, "pos": [9.0, 0.0, 0.0]},
        {"kind": "portal", "name": "Portal", "tag": "home", "connected": True, "distance": 12.0},
        {"kind": "door", "name": "Wood Door", "open": False, "distance": 15.0},
    ],
    "leader": {"name": "Leader", "pos": [3.0, 0.0, 4.0], "distance": 5.0},
}

RECIPES = [
    {
        "name": "Club",
        "station": None,
        "have_materials": False,
        "resources": [{"name": "Wood", "have": 4, "amount": 6}],
    }
]


def test_the_situation_reads_in_english(english: None) -> None:
    text = describe(
        {"pos": [0.0, 0.0, 0.0], "hp": 25, "hp_max": 25, "stamina": 50, "stamina_max": 50},
        SCENE,
        WorldMemory(Store()),
        Known(recipes=RECIPES, talk=[("Leader", "can you make an axe?")], tried=["gather Wood 5: done"]),
    )
    assert "[Me] health 25/25" in text
    assert "[In sight] 2 x tree (standing) (nearest 6 m)" in text
    assert "Portal 'home' (connected)" in text and "Wood Door (closed)" in text
    assert "[Crafting menu] Club(Wood 4/6; by hand; missing materials)" in text
    assert "[Tried for this request] gather Wood 5: done" in text
    assert not HANGUL.search(text), text


async def test_the_planner_is_asked_in_english(english: None) -> None:
    # 영어로 플레이하면 모델은 `_en` 필드로 답한다(아래 경계 시험).
    model = ScriptedModel(
        {"interpretation_en": "say hi", "steps": [], "speech_gist_en": "Hey! Good to see you."}
    )
    planner = Planner(model)
    plan = await planner.plan("hi Thorkell", "[Me] health 25/25", context_from_scene(SCENE))
    assert plan.speech_gist_ko == "Hey! Good to see you."
    assert model.systems[0].startswith("You are the thoughts of Thorkell")
    assert "[Request]\nhi Thorkell" in model.prompts[0] and "[Skills]" in model.prompts[0]
    assert not HANGUL.search(model.systems[0] + model.prompts[0])


async def test_the_fight_judgment_is_asked_and_kept_in_english(english: None) -> None:
    model = ScriptedModel(
        {
            "impression_en": "A huge stag with glowing antlers",
            "style": "ranged",
            "keep_m": 18,
            "close_m": 8,
            "retreat_hp": 0.4,
            "return_hp": 0.8,
            "hits_then_back": 2,
            "eat_first": True,
            "retreat_to_leader": True,
            "dodge_within_m": 6,
            "speech_en": "That's a big one! I'll shoot from back here.",
        }
    )
    view = FightView(
        "Eikthyr", "Eikthyr 30 m ahead, health bar at the top", "health 25/25", "Leader 5 m", True
    )
    tactic = await Tactician(model).tactic(view, [], [])
    assert tactic.style == "ranged"
    assert "[Fights I remember with Eikthyr]\n(first time I see it)" in model.prompts[0]
    assert not HANGUL.search(model.systems[0] + model.prompts[0])

    store = Store()
    episode = store.add_episode(
        "Eikthyr",
        "died",
        {
            "seconds": 75,
            "tactic": tactic.model_dump(),
            "hits": [[10.0, 12.0, 4.5, ["lightning"]]],
            "health": [[0.0, 1.0], [70.0, 0.6]],
            "my_health": [[0.0, 1.0], [75.0, 0.0]],
            "time": {"shoot": [5, 20.0], "back_off": [3, 40.0]},
            "shots": {"hit": 4, "fired": 6},
            "food_slots": 3,
        },
    )
    record = record_ko(episode)
    assert "Got hit: 1 times" in record and "4.5m, lightning" in record
    assert "Time spent: backing off 3 times 40 s, shooting 5 times 20 s" in record
    assert not HANGUL.search(record), record


@pytest.mark.parametrize(
    "bearing, spot", [(0.0, "screen middle"), (-30.0, "screen left"), (170.0, "off screen")]
)
def test_where_things_fall_on_screen_in_english(english: None, bearing: float, spot: str) -> None:
    from thorkell.world.sight import on_screen

    assert on_screen(bearing, 60.0, 640, 360).startswith(spot)


def test_text_fields_go_to_the_model_as_english_fields(english: None) -> None:
    from thorkell.lang import answer_from_model, schema_for_model
    from thorkell.plan.schema import Names, plan_schema

    # 실게임(2026-10-19): `summary_ko`라는 필드 이름을 보면 영어 지시에도 한국어로 답했다.
    schema = schema_for_model(plan_schema(Names(items=("Wood",))))
    assert "speech_gist_en" in schema["properties"] and "speech_gist_en" in schema["required"]
    assert not any(key.endswith("_ko") for key in schema["properties"])
    assert answer_from_model({"speech_gist_en": "On it!", "steps": [{"args": {"item": "Wood"}}]}) == {
        "speech_gist_ko": "On it!",
        "steps": [{"args": {"item": "Wood"}}],
    }


def test_korean_play_keeps_the_fields_as_they_are() -> None:
    from thorkell.lang import answer_from_model, schema_for_model
    from thorkell.plan.schema import Names, plan_schema

    schema = plan_schema(Names())
    assert schema_for_model(schema) is schema
    assert answer_from_model({"speech_gist_ko": "응"}) == {"speech_gist_ko": "응"}
