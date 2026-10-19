"""Thorkell's mind in English: what the leader teaches in English, what he says, and how he writes what he
knows for the models."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import Rig
from test_live import FakeSession, voice

from thorkell.body import protocol
from thorkell.mind.korean import damage_from_words, damage_name
from thorkell.mind.mind import Mind
from thorkell.mind.speech import Limits, SpeechQueue
from thorkell.mind.store import GENERAL, Store
from thorkell.plan.schema import Plan, Step
from thorkell.plan.validate import Context, validate
from thorkell.sim.world import greydwarf
from thorkell.talk.tools import ToolBridge

CLUB = {"name": "Club", "damage": {"blunt": 12.0}}
AXE = {"name": "Stone Axe", "damage": {"chop": 20.0, "slash": 14.0}}


def event(kind: str, data: dict[str, Any]) -> protocol.Event:
    return protocol.Event(seq=1, ts=1, kind=kind, tick=1, data=data)


def chatty_mind() -> Mind:
    return Mind(Store(), SpeechQueue(Limits(min_gap_s=0, self_talk_gap_s=0)))


def spoken(mind: Mind) -> list[str]:
    texts = []
    while (line := mind.speech.next()) is not None:
        texts.append(line.text)
    return texts


# --- damage words ------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("words", "kind"),
    [
        ("blunt weapons", "blunt"),
        ("clubs", "blunt"),
        ("a mace", "blunt"),
        ("the Hammer", "blunt"),
        ("slashing", "slash"),
        ("swords", "slash"),
        ("an axe", "slash"),
        ("knives", "slash"),
        ("piercing", "pierce"),
        ("spears", "pierce"),
        ("arrows", "pierce"),
        ("my bow", "pierce"),
        ("fire", "fire"),
        ("flames", "fire"),
        ("frost", "frost"),
        ("ice", "frost"),
        ("poison", "poison"),
        ("lightning", "lightning"),
        ("spirit", "spirit"),
    ],
)
def test_english_damage_words(english: None, words: str, kind: str) -> None:
    assert damage_from_words(words) == kind


@pytest.mark.parametrize("words", ["a pickaxe", "nice", "my elbow", "a rainbow", "firewood", "nothing"])
def test_english_damage_words_need_whole_words(english: None, words: str) -> None:
    assert damage_from_words(words) is None


def test_korean_play_does_not_read_english_damage_words() -> None:
    assert damage_from_words("swords") is None


def test_damage_names_follow_the_language(english: None) -> None:
    assert damage_name("blunt") == "blunt"
    assert damage_name("frost") == "frost"
    assert damage_name("chop") == "chop"


def test_damage_names_stay_korean_by_default() -> None:
    assert damage_name("blunt") == "둔기"


# --- facts the leader tells in English -----------------------------------------------------------------
@pytest.mark.parametrize(
    ("said", "fact"),
    [
        ("Greydwarves are weak to blunt weapons", ("Greydwarf", "weak_to", "blunt")),
        ("trolls hate fire", ("Troll", "weak_to", "fire")),
        ("I heard the troll is really weak to fire!", ("Troll", "weak_to", "fire")),
        ("Hey Thorkell, greydwarf brutes are weak to clubs.", ("Greydwarf Brute", "weak_to", "blunt")),
        ("skeletons're weak to maces", ("Skeleton", "weak_to", "blunt")),
        ("wolves are vulnerable to spears", ("Wolf", "weak_to", "pierce")),
        ("trolls resist slash", ("Troll", "resists", "slash")),
        ("draugr are resistant to poison", ("Draugr", "resists", "poison")),
        ("slash doesn't work on trolls at all", ("Troll", "resists", "slash")),
        ("arrows don't do much against wolves", ("Wolf", "resists", "pierce")),
        ("Bonemass is weak to blunt", ("Bonemass", "weak_to", "blunt")),
    ],
)
def test_told_facts_in_english(english: None, said: str, fact: tuple[str, str, str]) -> None:
    mind = Mind(Store())
    assert mind.hear(said) is not None
    told = mind.store.fact(*fact)
    assert told is not None and told.status == "hypothesis" and told.provenance == "told"


@pytest.mark.parametrize(
    "said",
    [
        "I hate trolls",  # the leader, not a creature
        "it is weak to fire",  # which one?
        "you are weak to fire",
        "trolls are not weak to fire",
        "trolls are weak to nothing",
        "I'm weak to fire",
        "what's weak to fire?",
        "my weakness is mead",
        "is fire a weakness?",
        "chop some wood",
        "bring the pickaxe",
        "greydwarves hate me, they keep running into the fire",
    ],
)
def test_near_misses_teach_nothing(english: None, said: str) -> None:
    mind = Mind(Store())
    assert mind.hear(said) is None
    assert mind.store.all_facts() == []


def test_told_fact_is_a_hypothesis_until_seen(english: None) -> None:
    mind = Mind(Store())
    reply = mind.hear("Greydwarves are weak to blunt weapons")
    assert reply == "Got it. So Greydwarves are weak to blunt? I'll check next time I fight."
    assert (
        mind.hear("the troll is weak to fire")
        == "Got it. So the troll is weak to fire? I'll check next time I fight."
    )
    assert mind.hear("trolls resist slash") == (
        "Got it. So slash doesn't work well on trolls? I'll check next time I fight."
    )
    assert (
        mind.hear("What are greydwarves weak to?")
        == "You said it's weak to blunt. Haven't checked it myself yet."
    )
    assert mind.hear("wolf weakness?") == "I don't know much about Wolf yet. I'll find out once I fight one."


def test_a_known_name_is_used_as_the_game_writes_it(english: None) -> None:
    mind = Mind(Store())
    mind.on_scene({"nearby": [{"kind": "creature", "name": "Greydwarf Brute"}]})
    mind.hear("greydwarf brutes are weak to fire")
    assert mind.store.fact("Greydwarf Brute", "weak_to", "fire") is not None
    assert mind.recall("greydwarf brutes") == "weak_to fire (hypothesis, told)"
    assert mind.recall("trolls") == "I don't know much about Troll yet."


def test_seeing_it_verifies_and_he_says_so_in_english(english: None) -> None:
    mind = chatty_mind()
    mind.hear("greydwarves are weak to blunt weapons")
    mind.attacking("Greydwarf", "creature", CLUB)
    mind.on_event(event("damage_dealt", {"type": "weak", "amount": 18, "on_target": True}))
    fact = mind.store.fact("Greydwarf", "weak_to", "blunt")
    assert fact is not None and fact.status == "verified"
    assert spoken(mind) == ["You were right! Greydwarf really is weak to blunt."]
    assert mind.hear("greydwarf weakness?") == "Greydwarf is weak to blunt. I found out fighting one myself."
    assert mind.hear("greydwarves are weak to blunt") == (
        "Yeah, I found that out too. Greydwarves are weak to blunt."
    )


def test_resisted_hits_and_a_wrong_claim_in_english(english: None) -> None:
    mind = chatty_mind()
    mind.hear("greydwarves are weak to swords")
    mind.attacking("Greydwarf", "creature", AXE)
    for _ in range(2):
        mind.on_event(event("damage_dealt", {"type": "resistant", "amount": 7, "on_target": True}))
    claim = mind.store.fact("Greydwarf", "weak_to", "slash")
    assert claim is not None and claim.status == "refuted"
    texts = spoken(mind)
    assert "Slash attacks don't do much to Greydwarf." in texts
    assert "You said Greydwarf was weak to slash, but I tried it and I don't think so." in texts


def test_untold_weakness_found_by_fighting(english: None) -> None:
    mind = chatty_mind()
    mind.attacking("Greydwarf", "creature", CLUB)
    mind.on_event(event("damage_dealt", {"type": "weak", "on_target": True}))
    assert spoken(mind) == ["I think Greydwarf is weak to blunt!"]


def test_remarks_in_english(english: None) -> None:
    mind = chatty_mind()
    mind.on_scene({"nearby": [{"kind": "creature", "name": "Neck"}]})
    mind.on_event(event("damage_taken", {"attacker_kind": "creature", "attacker_name": "Greydwarf"}))
    mind.on_event(event("recipe_unlocked", {"name": "Club"}))
    mind.on_event(event("biome_entered", {"name": "Black Forest"}))
    mind.attacking("Rock", "object", None)
    mind.on_event(event("damage_dealt", {"type": "too_hard", "on_target": True}))
    assert set(spoken(mind)) == {
        "Never seen that one before... Neck?",
        "Greydwarf attacked me!",
        "I can make Club now.",
        "This must be the Black Forest. First time here.",
        "Can't break Rock with Unarmed.",
    }


# --- what he knows, written for the models -------------------------------------------------------------
def test_facts_and_lessons_render_in_english(english: None) -> None:
    mind = Mind(Store())
    mind.hear("trolls are weak to blunt")
    episode = mind.store.add_episode("Troll", "died", {})
    lesson = mind.store.add_lesson("Troll", "keep 10m away", episode.id)
    mind.store.judge_lesson(lesson.id, held=False)
    lines, ids = mind.facts_for_prompt()
    assert ids == frozenset({"F1", "L1"})
    assert lines == [
        "F1 Troll weak_to blunt (hypothesis; told; seen 0x)",
        "L1 [Troll] keep 10m away (hypothesis; learned from E1; held 0x, wrong 1x)",
    ]


def test_lessons_render_in_korean_by_default() -> None:
    store = Store()
    store.add_lesson(GENERAL, "먹고 싸우자", "E1")
    assert store.lessons()[0].line() == "L1 [일반] 먹고 싸우자 (hypothesis; E1에서 배움; 맞았음 0번)"


# --- the plan validator --------------------------------------------------------------------------------
def test_validator_hints_in_english(english: None) -> None:
    plan = Plan(interpretation_ko="wood", steps=[Step(id="s1", skill="gather_wood", args={})])
    problems = validate(plan, Context(inventory=frozenset()))
    assert any("count: how many, as an integer" in problem for problem in problems)


def test_a_name_the_leader_said_in_lowercase_counts_as_said(english: None) -> None:
    plan = Plan(interpretation_ko="hunt", steps=[Step(id="s1", skill="hunt", args={"creature": "Boar"})])
    assert validate(plan, Context(inventory=frozenset(), request="go hunt two boars")) == []
    assert validate(plan, Context(inventory=frozenset(), request="go hunt two deer")) == [
        "s1: creature 'Boar' has not been shown by the game nor said by the leader"
    ]


# --- the voice -----------------------------------------------------------------------------------------
async def test_the_voice_is_told_to_speak_english(english: None, tmp_path: Path) -> None:
    session = FakeSession([])
    configs: list[dict[str, Any]] = []
    live = voice([session], configs, tmp_path)
    task = asyncio.create_task(live.run(asyncio.Event()))
    await asyncio.wait_for(session.done.wait(), 2)
    assert "in English" in configs[0]["system_instruction"]
    tools = configs[0]["tools"][0]["function_declarations"]
    recall = next(d for d in tools if d["name"] == "recall_knowledge")
    assert recall["description"].startswith("Look up what Thorkell knows")
    assert await live.inject("Night fell", speak=False)
    assert await live.inject("Watch out!", speak=True, urgent=True)
    assert session.content == [("[Game event] Night fell", False), ("[Thorkell says] Watch out!", True)]
    task.cancel()


async def test_teach_and_recall_through_tools_in_english(english: None, make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(mind=Mind(Store()))
    tools = ToolBridge(rig.controller, None, lambda: "")
    unknown, _ = await tools.call("recall_knowledge", {"query_ko": "troll weakness"})
    assert unknown["answer_ko"] == "I don't know much about Troll yet. I'll find out once I fight one."
    taught, _ = await tools.call("teach_fact", {"statement_ko": "trolls are weak to blunt"})
    assert taught["stored"]
    known, _ = await tools.call("recall_knowledge", {"query_ko": "troll weakness"})
    assert known["answer_ko"] == "You said it's weak to blunt. Haven't checked it myself yet."
    not_a_fact, _ = await tools.call("teach_fact", {"statement_ko": "nice weather"})
    assert not_a_fact == {"stored": False, "reply_ko": "I'm not sure what the fact is"}


# --- in the (English) simulator ------------------------------------------------------------------------
async def test_told_weakness_is_tried_and_confirmed_in_english(
    english: None, make_rig: Callable[..., Any]
) -> None:
    mind = Mind(Store(), SpeechQueue(Limits(min_gap_s=0.2, self_talk_gap_s=0.2, topic_cooldown_s=120)))
    rig: Rig = await make_rig(mind=mind)
    rig.world.leader_says("What are greydwarves weak to?")
    await rig.until(lambda: any("I don't know much about Greydwarf yet" in text for text in rig.said()))
    rig.world.leader_says("Greydwarves are weak to blunt weapons")
    await rig.until(lambda: any("I'll check next time I fight" in text for text in rig.said()))

    rig.world.spawn(greydwarf(rig.world.bot.x + 5, rig.world.bot.z))
    await rig.until(lambda: "7:900" not in rig.world.entities, timeout=40)
    hits = [str(e.data["type"]) for e in rig.session.events_of("damage_dealt")]
    assert hits[0] == "weak", "being told should make him reach for the club first"
    await rig.until(lambda: "You were right! Greydwarf really is weak to blunt." in rig.said(), timeout=10)
    fact = mind.store.fact("Greydwarf", "weak_to", "blunt")
    assert fact is not None and fact.status == "verified" and fact.told == 1

    rig.world.leader_says("What are greydwarves weak to?")
    await rig.until(lambda: "Greydwarf is weak to blunt. I found out fighting one myself." in rig.said())
