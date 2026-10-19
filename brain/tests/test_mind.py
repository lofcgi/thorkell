from __future__ import annotations

from typing import Any

import pytest

from thorkell.body import protocol
from thorkell.mind.korean import damage_from_words, josa
from thorkell.mind.mind import Mind
from thorkell.mind.speech import Limits, Line, SpeechQueue
from thorkell.mind.store import Store, status_of

CLUB = {"name": "곤봉", "damage": {"blunt": 12.0}}
AXE = {"name": "돌도끼", "damage": {"chop": 20.0, "slash": 14.0}}


def event(kind: str, data: dict[str, Any]) -> protocol.Event:
    return protocol.Event(seq=1, ts=1, kind=kind, tick=1, data=data)


@pytest.mark.parametrize(
    ("word", "particle", "expected"),
    [
        ("트롤", "은는", "트롤은"),
        ("그레이드워프", "은는", "그레이드워프는"),
        ("곤봉", "을를", "곤봉을"),
        ("도끼", "을를", "도끼를"),
        ("곤봉", "으로", "곤봉으로"),
        ("돌도끼", "으로", "돌도끼로"),
        ("활", "으로", "활로"),
        ("Greydwarf", "이가", "Greydwarf가"),
    ],
)
def test_josa(word: str, particle: str, expected: str) -> None:
    assert josa(word, particle) == expected


def test_damage_words() -> None:
    assert damage_from_words("둔기") == "blunt"
    assert damage_from_words("때리는 무기") == "blunt"
    assert damage_from_words("불화살") == "pierce" or damage_from_words("불화살") == "fire"
    assert damage_from_words("그냥") is None


def test_status_rules() -> None:
    assert status_of(told=1, support=0, contradict=0) == "hypothesis"
    assert status_of(told=0, support=1, contradict=0) == "supported"
    assert status_of(told=0, support=3, contradict=0) == "verified"
    assert status_of(told=1, support=1, contradict=0) == "verified"
    assert status_of(told=1, support=0, contradict=2) == "refuted"
    assert status_of(told=0, support=2, contradict=2) == "supported"


def test_told_fact_is_a_hypothesis_until_seen() -> None:
    mind = Mind(Store())
    reply = mind.hear("그레이드워프는 둔기에 약해")
    assert reply == "알았어. 그레이드워프는 둔기에 약하다는 거지? 싸울 때 확인해 볼게."
    fact = mind.store.fact("그레이드워프", "weak_to", "blunt")
    assert fact is not None and fact.status == "hypothesis" and fact.provenance == "told"
    assert mind.hear("그레이드워프 약점이 뭐야?") == "네가 둔기에 약하다고 했었지. 아직 직접 확인은 못 했어."


def test_seeing_it_verifies_and_is_worth_saying() -> None:
    mind = Mind(Store(), SpeechQueue(Limits(min_gap_s=0, self_talk_gap_s=0)))
    mind.hear("그레이드워프는 둔기에 약해")
    mind.attacking("그레이드워프", "creature", CLUB)
    mind.on_event(event("damage_dealt", {"type": "weak", "amount": 18, "on_target": True}))
    fact = mind.store.fact("그레이드워프", "weak_to", "blunt")
    assert fact is not None and fact.status == "verified"
    line = mind.speech.next()
    assert line is not None and line.text == "네 말이 맞았어! 그레이드워프는 정말 둔기에 약하네."
    assert mind.hear("그레이드워프 약점이 뭐야?") == "그레이드워프는 둔기에 약해. 직접 싸워 보고 알았어."


def test_resisted_hits_are_learned_and_contradict_claims() -> None:
    mind = Mind(Store(), SpeechQueue(Limits(min_gap_s=0, self_talk_gap_s=0)))
    mind.hear("그레이드워프는 칼에 약해")
    mind.attacking("그레이드워프", "creature", AXE)
    for _ in range(2):
        mind.on_event(event("damage_dealt", {"type": "resistant", "amount": 7, "on_target": True}))
    assert mind.store.fact("그레이드워프", "resists", "slash").status in ("supported", "verified")  # type: ignore[union-attr]
    claim = mind.store.fact("그레이드워프", "weak_to", "slash")
    assert claim is not None and claim.status == "refuted"
    texts = []
    while (line := mind.speech.next()) is not None:
        texts.append(line.text)
    assert "베기 공격이 그레이드워프한테는 잘 안 먹히네." in texts
    assert "그레이드워프가 베기에 약하다고 했는데, 해 보니까 아닌 것 같아." in texts


def test_hits_without_a_target_or_on_ambiguous_weapons_teach_nothing() -> None:
    mind = Mind(Store())
    mind.on_event(event("damage_dealt", {"type": "weak", "on_target": True}))
    mind.attacking("그레이드워프", "creature", {"name": "이상한검", "damage": {"slash": 10, "fire": 10}})
    mind.on_event(event("damage_dealt", {"type": "weak", "on_target": True}))
    assert mind.store.facts_about("그레이드워프") == []


def test_hits_on_something_else_in_the_swing_teach_nothing() -> None:
    # 한 번 휘두르면 범위 안의 덤불·바위도 맞는다.
    # 몸이 겨냥한 대상에 맞았다고 확인한 타격으로만 배운다.
    mind = Mind(Store())
    mind.hear("그레이드워프는 둔기에 약해")
    mind.attacking("그레이드워프", "creature", CLUB)
    mind.on_event(event("damage_dealt", {"type": "normal", "on_target": False}))
    mind.on_event(event("damage_dealt", {"type": "too_hard", "on_target": False}))
    fact = mind.store.fact("그레이드워프", "weak_to", "blunt")
    assert fact is not None and fact.status == "hypothesis"
    assert mind.store.fact("그레이드워프", "too_hard_for", "곤봉") is None


def test_first_sighting_is_self_talk_once() -> None:
    mind = Mind(Store(), SpeechQueue(Limits(self_talk_gap_s=0)))
    scene = {"nearby": [{"kind": "creature", "name": "목"}]}
    mind.on_scene(scene)
    mind.on_scene(scene)
    line = mind.speech.next()
    assert line is not None and line.talker == "whisper" and "처음 보는 놈" in line.text
    assert mind.speech.next() is None


def test_attacked_by_creature_is_urgent() -> None:
    mind = Mind(Store())
    mind.on_event(
        event("damage_taken", {"attacker_kind": "creature", "attacker_name": "그레이드워프", "amount": 4})
    )
    line = mind.speech.next()
    assert line is not None and line.urgency == 2 and line.text == "그레이드워프가 날 공격했어!"


def test_speech_rate_limits() -> None:
    now = [0.0]
    queue = SpeechQueue(
        Limits(min_gap_s=20, per_window=2, window_s=600, topic_cooldown_s=300), clock=lambda: now[0]
    )
    queue.offer(Line("a", 1, topic="t1"))
    queue.offer(Line("b", 1, topic="t2", ttl_s=100))
    assert queue.next() is not None and queue.next() is None  # min gap
    now[0] = 21
    assert queue.next() is not None  # second one after the gap
    queue.offer(Line("c", 1, topic="t3", ttl_s=1000))
    now[0] = 50
    assert queue.next() is None  # per-window cap
    queue.offer(Line("danger", 3))
    assert queue.next() is not None  # urgent skips limits
    queue.offer(Line("again", 1, topic="t1"))
    assert queue.dropped[-1].text == "again"  # topic cooldown


def test_facts_for_prompt_lists_ids() -> None:
    mind = Mind(Store())
    mind.hear("트롤은 둔기에 약해")
    lines, ids = mind.facts_for_prompt()
    assert ids == frozenset({"F1"})
    assert lines == ["F1 트롤 weak_to blunt (hypothesis; told; seen 0x)"]
