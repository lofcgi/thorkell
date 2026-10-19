"""Playing in English: the leader's English chat is understood, and what the controller and its skills say,
report and show the models is English, with the English game's names."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from conftest import Rig, ScriptedModel

from thorkell.control import intents
from thorkell.control.goals import Goal, Tier
from thorkell.mind.store import Store
from thorkell.models.gemini import ModelError
from thorkell.plan.planner import Planner
from thorkell.sim.world import SimEntity, SimWorld
from thorkell.world.memory import WorldMemory
from thorkell.world.where import where_ko

pytestmark = pytest.mark.usefixtures("english")


# --- the leader's English chat --------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "kind", "count"),
    [
        ("Thorkell, stop!", "stop", None),
        ("stop", "stop", None),
        ("what are you doing?", "status", None),
        ("What're you up to?", "status", None),
        ("how's it going?", "status", None),
        ("How\N{RIGHT SINGLE QUOTATION MARK}s the wood going?", "status", None),
        ("status", "status", None),
        ("chop 10 wood", "gather_wood", 10),
        ("Thorkell, can you get me 20 wood?", "gather_wood", 20),
        ("gather some wood", "gather_wood", None),
        ("bring wood", "gather_wood", None),
        ("follow me", "follow", None),
        ("come with me", "follow", None),
        ("wait", "wait", None),
        ("wait here", "wait", None),
        ("stay here", "wait", None),
        ("take it", "pick_up", None),
        ("here, take this axe", "pick_up", None),
        ("pick it up", "pick_up", None),
        ("grab it", "pick_up", None),
        ("let's sleep", "sleep", None),
        ("go to bed", "sleep", None),
        ("time to sleep", "sleep", None),
    ],
)
def test_english_phrases(text: str, kind: str, count: int | None) -> None:
    assert intents.read(text) == intents.Intent(kind, count)


@pytest.mark.parametrize(
    "text",
    [
        "we need wood for a house",
        "this wooden wall looks nice",
        "how are you?",
        "how are you feeling today?",
        "nice weather",
        "take it easy",
        "stay safe",
        "did you sleep well?",
        "I followed the river here",
        "hold on, let me look at the map",
        "the bus stopped",
    ],
)
def test_english_near_misses_are_left_to_the_planner(text: str) -> None:
    assert intents.read(text) is None


# --- what Thorkell says and shows -------------------------------------------------------------------
def test_goals_are_described_in_english() -> None:
    wood = Goal("gather_wood", Tier.USER, {"count": 10})
    wood.progress["gathered"] = 4
    assert wood.describe_ko() == "gathering Wood (4/10)"
    assert Goal("fight", Tier.SURVIVAL, {"creature": "Eikthyr"}).describe_ko() == "fighting Eikthyr"
    assert Goal("use_portal", Tier.USER, {"tag": "home"}).describe_ko() == "going through the portal (home)"
    assert Goal("request", Tier.USER, {"text": "build a house"}).describe_ko() == (
        "working on your request: build a house"
    )


def test_where_reads_distance_then_direction_in_english() -> None:
    assert where_ko([0.0, 0.0, 0.0], [250.0, 5.0, 160.0]) == "300m northeast"
    assert where_ko([0.0, 0.0, 0.0], [-70.0, 0.0, -70.0]) == "100m southwest"
    assert where_ko([0.0, 0.0, 0.0], [1.0, 0.0, 1.0]) == "right here"


def test_creatures_are_labelled_in_english() -> None:
    memory = WorldMemory(Store())
    far = {"id": "1:2", "kind": "creature", "name": "", "key": "$enemy_boar", "size": "small"}
    assert memory.creature_label(far) == "unfamiliar small creature"
    assert memory.creature_label({**far, "size": None}) == "unfamiliar creature"
    memory.on_scene({"nearby": [{**far, "name": "Boar", "pos": [6, 0, 0]}]}, [0, 0, 0])
    assert memory.creature_label(far) == "Boar (far off)"


async def test_follow_and_wait_are_acknowledged_in_english(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.world.leader_says("Thorkell, follow me")
    await rig.until(lambda: "Okay, I'll follow you." in rig.said(), 5)
    assert rig.controller.stance == "follow"
    rig.world.leader_says("wait here")
    await rig.until(lambda: "Got it, I'll wait here." in rig.said(), 5)
    assert rig.controller.stance == "wait"


async def test_chopped_wood_on_request_and_said_so(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.world.bot.foods = {"라즈베리": 1200.0}
    rig.world.leader_says("Thorkell, chop 10 wood")
    await rig.until(lambda: "I'll get 10 Wood." in rig.said(), 5)
    await rig.until(
        lambda: any(d.kind == "done" and d.goal_kind == "gather_wood" for d in rig.controller.decisions)
    )
    assert rig.wood() >= 10
    adopted = next(d for d in rig.controller.decisions if d.kind == "adopt" and d.goal_kind == "gather_wood")
    assert adopted.reason_ko == "started gathering Wood (0/10)"


async def test_status_and_stop_in_english(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.world.bot.foods = {"라즈베리": 1200.0}
    rig.world.leader_says("chop 30 wood")
    await rig.until(lambda: rig.world.active is not None)
    rig.world.leader_says("what are you doing?")
    await rig.until(lambda: any(text.startswith("I'm gathering Wood (") for text in rig.said()), 5)
    rig.world.leader_says("Thorkell stop")
    await rig.until(lambda: rig.controller.current() is None and "Got it, I'll stop." in rig.said(), 3)
    drop = next(d for d in rig.controller.decisions if d.kind == "drop")
    assert drop.reason_ko == "the leader said to stop"


async def test_idle_status_and_unknown_words_through_the_host(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(leader_chat_via_host=True)
    rig.controller.stance = "wait"
    await rig.controller.hear_leader("how's it going?")
    await rig.controller.hear_leader("nice weather")
    assert rig.said() == [
        "Not doing anything right now. Got something for me?",
        "Sorry, I don't get that yet. Try 'follow me', 'wait' or 'chop 10 wood'.",
    ]


async def test_the_voice_model_hears_what_was_decided_in_english(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.world.bot.foods = {"라즈베리": 1200.0}
    assert rig.controller.request_text("chop 5 wood") == "Going to gather 5 Wood."
    await rig.until(lambda: (goal := rig.controller.current()) is not None and goal.kind == "gather_wood")
    # 새 부탁이 하던 일을 잠시 멈추게 한다. 상태를 물으면 끝나고 이어서 할 일도 말한다.
    assert rig.controller.request_text("stay here") == "Going to wait here."
    await rig.until(lambda: (goal := rig.controller.current()) is not None and goal.kind == "wait")
    assert rig.controller.status_ko().startswith(
        "I'm waiting here. After that I'll get back to gathering Wood ("
    )


async def test_takes_what_the_leader_hands_over(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.world.bot.inventory = {}
    rig.world.bot.equipped = None
    rig.world.leader_drops("돌도끼")
    rig.world.leader_says("Thorkell, take this axe")
    await rig.until(lambda: "Sure, I'll take it." in rig.said(), 5)
    await rig.until(lambda: rig.world.bot.inventory.get("돌도끼") == 1)


def house() -> SimWorld:
    """The leader's hut at night: walls and a roof, a fire, the leader's bed and a workbench."""
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
    world.day_fraction = 0.8
    world.bot.inventory = {"나무": 20, "망치": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 1200.0}
    return world


async def test_lets_sleep_builds_a_bed_by_its_english_name(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(world=house())
    rig.controller.stance = "wait"
    rig.world.leader_in_bed = True
    rig.world.leader_says("let's sleep")
    await rig.until(lambda: "Slept well! Good morning." in rig.said(), 90)
    beds = [e for e in rig.world.entities.values() if e.kind == "bed"]
    assert sorted(e.owner for e in beds) == ["Leader", "Thorkell"]


NO_PORTAL = {
    "interpretation_ko": "go home through the portal",
    "quantity": None,
    "assumptions": [],
    "steps": [{"id": "s1", "skill": "use_portal", "args": {}}],
    "abort_if": [],
    "speech_gist_ko": "I'll try the portal!",
}
DONE = {**NO_PORTAL, "steps": [], "speech_gist_ko": "No portal here. Let's walk."}


async def test_what_was_tried_is_shown_to_the_planner_in_english(make_rig: Callable[..., Any]) -> None:
    model = ScriptedModel(NO_PORTAL, DONE)
    rig: Rig = await make_rig(planner=Planner(model))
    rig.world.leader_says("let's go home")
    await rig.until(lambda: "No portal here. Let's walk." in rig.said())
    assert "use_portal(): didn't work — I don't see a portal" in model.prompts[1]


class QuotaSpent:
    async def generate_json(self, **_: Any) -> tuple[dict[str, Any], Any]:
        raise ModelError("gemini-3.8-flash call failed (429): limit: 20 requests per day", status=429)


async def test_spent_quota_names_the_english_phrases_that_still_work(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(planner=Planner(QuotaSpent()))
    rig.world.leader_says("hi Thorkell")
    await rig.until(lambda: any("usage limit" in text for text in rig.said()), 5)
    line = next(text for text in rig.said() if "usage limit" in text)
    assert "'follow me'" in line and "'chop 10 wood'" in line
    # 아는 영어 명령은 계획 모델 없이 바로 시작한다.
    rig.world.leader_says("follow me")
    await rig.until(lambda: "Okay, I'll follow you." in rig.said(), 5)
