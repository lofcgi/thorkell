"""M5 in the simulator: learning a creature's weakness by fighting it and by being told.

The simulator's greydwarf secretly takes 0.5x slash and 1.5x blunt. The axe's tooltip numbers
(slash 14) beat the club's (blunt 12), so a first-timer reaches for the axe first.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from conftest import Rig

from thorkell.mind.mind import Mind
from thorkell.mind.speech import Limits, SpeechQueue
from thorkell.mind.store import Store
from thorkell.sim.world import greydwarf


def chatty_mind() -> Mind:
    return Mind(Store(), SpeechQueue(Limits(min_gap_s=0.2, self_talk_gap_s=0.2, topic_cooldown_s=120)))


def hit_types(rig: Rig, after: int = 0) -> list[str]:
    return [str(e.data["type"]) for e in rig.session.events_of("damage_dealt")[after:]]


async def test_first_fight_teaches_the_weakness_and_switches_weapon(make_rig: Callable[..., Any]) -> None:
    mind = chatty_mind()
    rig: Rig = await make_rig(mind=mind)
    rig.world.bot.equipped = "돌도끼"  # 벌목하던 사람처럼 도끼를 든 채 습격받는다
    rig.world.spawn(greydwarf(rig.world.bot.x + 5, rig.world.bot.z))
    await rig.until(lambda: "7:900" not in rig.world.entities, timeout=40)

    types = hit_types(rig)
    assert types[0] == "resistant", "a first-timer should try the axe (higher tooltip numbers) first"
    assert "weak" in types, "after slashes failed he should switch to the club"
    assert mind.store.fact("그레이드워프", "resists", "slash") is not None
    weak = mind.store.fact("그레이드워프", "weak_to", "blunt")
    assert weak is not None and weak.status in ("supported", "verified")
    await rig.until(lambda: any("둔기에 약한 것 같아" in text for text in rig.said()), timeout=10)
    await rig.until(lambda: any("곤봉으로 바꿔 볼게" in text for text in rig.said()), timeout=10)

    # After catching his breath, the next fight starts with the club right away.
    await rig.until(lambda: rig.world.bot.hp >= 0.9 * rig.world.bot.hp_max, timeout=20)
    before = len(rig.session.events_of("damage_dealt"))
    rig.world.spawn(greydwarf(rig.world.bot.x + 5, rig.world.bot.z, id="7:901"))
    await rig.until(lambda: "7:901" not in rig.world.entities, timeout=40)
    assert hit_types(rig, before)[0] == "weak"


async def test_told_weakness_is_tried_and_confirmed(make_rig: Callable[..., Any]) -> None:
    mind = chatty_mind()
    rig: Rig = await make_rig(mind=mind)
    rig.world.leader_says("그레이드워프 약점이 뭐야?")
    await rig.until(lambda: any("아직 잘 몰라" in text for text in rig.said()))
    rig.world.leader_says("그레이드워프는 둔기에 약해")
    await rig.until(lambda: any("싸울 때 확인해 볼게" in text for text in rig.said()))

    rig.world.spawn(greydwarf(rig.world.bot.x + 5, rig.world.bot.z))
    await rig.until(lambda: "7:900" not in rig.world.entities, timeout=40)
    assert hit_types(rig)[0] == "weak", "being told should make him reach for the club first"
    await rig.until(lambda: any("네 말이 맞았어" in text for text in rig.said()), timeout=10)
    fact = mind.store.fact("그레이드워프", "weak_to", "blunt")
    assert fact is not None and fact.status == "verified" and fact.told == 1

    rig.world.leader_says("그레이드워프 약점이 뭐야?")
    await rig.until(lambda: any("직접 싸워 보고 알았어" in text for text in rig.said()))


async def test_new_creature_gets_self_talk(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(mind=chatty_mind())
    rig.world.spawn(greydwarf(rig.world.bot.x + 30, rig.world.bot.z))
    await rig.until(lambda: any("처음 보는 놈인데" in text for text in rig.said()), timeout=10)
    whispers = [text for talker, text in rig.world.said if talker == "whisper"]
    assert any("그레이드워프" in text for text in whispers)
