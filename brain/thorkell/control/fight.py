"""Facing a creature: think first, fight the way Thorkell decided, and keep a record for afterwards.

The thinking is the slow brain's (plan/tactics.py), with what Thorkell has lived through: earlier fights with
this creature and the lessons he took from them. This module only carries the decision out (keep the distance
it chose, roll when the creature gets inside the distance it chose, step back to eat below the health it
chose) and writes down what a player would remember: when and from how far the hits came, how many arrows
landed, how the health bar went. The controller turns that record into an episode and a reflection.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
import time
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import replace
from typing import Any

from thorkell import lang
from thorkell.body.protocol import Result
from thorkell.body.session import BodySession
from thorkell.control.field import _bow, _find, _loot
from thorkell.control.goals import Goal
from thorkell.control.making import _here, _say, run_child
from thorkell.control.skills import (
    SkillContext,
    SkillOutcome,
    _attack,
    _do,
    _held,
    _wait_scene,
    _weapons,
    defend,
    eat,
    equip_for_fight,
)
from thorkell.lang import tr
from thorkell.mind.korean import DAMAGE_KO, josa
from thorkell.mind.store import Episode, Lesson
from thorkell.models.gemini import ModelError
from thorkell.plan.tactics import FightView, JudgmentRejected, Tactic
from thorkell.world.sight import SightError
from thorkell.world.where import distance_m

log = logging.getLogger(__name__)

# 몸 기술(상대가 누구든 같다). 구르기는 스태미나를 쓴다(스태미나 바가 보인다). 활은 상대 둘레를 한 방향으로
# 돌며 쏘고 몇 발마다 방향을 바꾼다(좌우를 번갈아 움직이면 제자리라 날아오는 것을 못 피했다).
DODGE_STAMINA = 15.0
SHOTS_PER_SIDE = 5
# 지킬 거리보다 이만큼 더 멀면 다가가서 쏜다(화살이 닿는 거리).
SHOOT_SLACK_M = 10.0
# 생각하는 동안 가만히 서 있지 않는다. 이 안으로 다가오면 일단 물러선다.
THINKING_SPACE_M = 15.0
# 리더 쪽으로 물러나기로 했어도 리더가 이만큼 곁에 있으면 그냥 상대에게서 멀어진다.
LEADER_BESIDE_M = 4.0
# 싸움을 판단할 때 떠올리는 리더의 말(최근 몇 분).
LEADER_WORDS_S = 300.0
# 싸우는 중에 다른 놈이 이만큼 안에서 이 시간 안에 때렸으면 그놈부터 처리한다.
JOINED_NEAR_M = 6.0
JOINED_HIT_S = 5.0
# 명령을 하는 동안 상대의 공격 동작을 살피는 간격(초).
WATCH_S = 0.05
# 공격 동작을 보고 옆으로 구르는 거리(m).
ROLL_ASIDE_M = 6.0
# 화살 길이 막히면 옆으로 옮기는 걸음(m).
SIDESTEP_M = 5.0
# 상대 체력바가 이만큼(초) 줄지 않으면 그만둔다. 줄고 있는 동안은 계속한다.
STALL_S = 120.0
# 내 체력바가 이만큼 바뀔 때마다 기록한다.
HEALTH_STEP = 0.05
# 안 보이게 된 상대를 이만큼 못 보면 놓친 것이다.
GONE_S = 20.0
SAY_EVERY_S = 20.0
# 음식은 세 가지까지 한꺼번에 효과가 있다(화면에 칸이 셋 보인다).
FOOD_SLOTS = 3
LOOK_FOR_IT_SCENES = 40
# 화면 가운데의 처치 알림("에이크쉬르를 처치했습니다" / "Eikthyr is slain")에 든 말.
SLAIN_WORD: dict[lang.Language, str] = {"ko": "처치", "en": "slain"}


async def fight(ctx: SkillContext) -> SkillOutcome:
    name = str(ctx.goal.args["creature"])
    progress = ctx.goal.progress
    if ctx.tactician is None:
        return SkillOutcome(
            False,
            "no_judgment",
            tr(
                f"{josa(name, '이가')} 뭔지, 어떻게 싸울지 판단할 수가 없어(판단 모델이 꺼져 있어)",
                f"I can't tell what {name} is or how to fight it (my judgment model is off)",
            ),
        )
    record: dict[str, Any] = progress.setdefault("record", {"shots": {}, "hits": [], "health": []})
    # 생각하는 동안 맞은 것도 이 싸움의 기록이다.
    progress.setdefault("hits_from", len(ctx.session.events_of("damage_taken")))
    progress.setdefault("began", time.monotonic())
    tactic: Tactic | None = progress.get("tactic")
    if tactic is None:
        thought = await _think(ctx, name, record)
        if isinstance(thought, SkillOutcome):
            return thought
        tactic = progress["tactic"] = thought
        record["tactic"] = tactic.model_dump()
        await _say(ctx, tactic.speech_ko)
        if tactic.style == "leave":
            return _leave(ctx, record)
        if tactic.eat_first:
            record["ate"] = await fill_food(ctx)
            record["food_slots"] = len(_foods(ctx))
    return await _carry_out(ctx, name, tactic, record)


async def _think(
    ctx: SkillContext, name: str, record: dict[str, Any], midway: bool = False
) -> Tactic | SkillOutcome:
    assert ctx.tactician is not None
    creature = None
    for _scene in range(LOOK_FOR_IT_SCENES):
        await _wait_scene(ctx)
        creature = _find(ctx, name)
        if creature is not None:
            break
    if creature is None:
        return SkillOutcome(False, "not_found", tr(f"{josa(name, '이가')} 안 보여", f"I can't see {name}"))
    record["id"] = str(creature["id"])
    view = describe(ctx, name, creature)
    record["looks"] = view.seen_ko
    record["food_slots"] = len(_foods(ctx))
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    record["leader_m"] = round(float(leader["distance"])) if leader else None
    earlier = ctx.mind.store.episodes(name) if ctx.mind is not None else []
    if midway:
        # 싸우는 중에 다시 생각할 때는 지금 싸움이 어떻게 되고 있는지가 가장 중요한 기억이다.
        earlier = [*earlier, Episode("now", name, tr("싸우는 중", "still fighting"), dict(record))]
    lessons = ctx.mind.lessons_for(name) if ctx.mind is not None else []
    thinking = asyncio.create_task(_judge(ctx, name, creature, view, earlier, lessons))
    try:
        while not thinking.done():
            await _wait_scene(ctx)
            seen = _find(ctx, name)
            if seen is not None and seen["distance"] < THINKING_SPACE_M:
                await _back_off(ctx, seen, THINKING_SPACE_M, toward_leader=False)
        return thinking.result()
    except (ModelError, JudgmentRejected) as error:
        log.error("no tactic for %s: %s", name, error)
        return SkillOutcome(
            False,
            "no_judgment",
            tr(
                f"{josa(name, '과와')} 어떻게 싸울지 생각이 안 나({error})",
                f"I can't figure out how to fight {name} ({error})",
            ),
            {"error": str(error)},
        )
    finally:
        thinking.cancel()


async def _judge(
    ctx: SkillContext,
    name: str,
    creature: dict[str, Any],
    view: FightView,
    earlier: list[Episode],
    lessons: list[Lesson],
) -> Tactic:
    """Look at it (Thorkell's own screen, when he has eyes), then decide what it is and how to face it."""
    assert ctx.tactician is not None
    if ctx.eyes is not None:
        try:
            seen = await ctx.eyes.look(
                tr(
                    f"{name}: 저게 뭐야? 나를 노리는 적이야, 리더의 것이야?",
                    f"{name}: What is that? An enemy after me, or the leader's?",
                ),
                toward=list(creature["pos"]),
            )
            view = replace(view, sight_ko="\n".join(seen.lines()))
        except (ModelError, SightError, TimeoutError) as error:
            log.error("could not look at %s: %s", name, error)
            view = replace(
                view,
                sight_ko=tr(
                    f"(화면을 보려 했지만 못 봤다: {error})",
                    f"(I tried to look at my screen but couldn't: {error})",
                ),
            )
    return await ctx.tactician.tactic(view, earlier, lessons)


def _leader_fell(ctx: SkillContext, leader_ids: set[str], deaths_before: int) -> bool:
    """The leader's body dropped where they stood (`creature_died` with the id the leader had while seen)."""
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    if leader is not None and leader.get("id"):
        leader_ids.add(str(leader["id"]))
    return any(
        str(e.data.get("id")) in leader_ids for e in ctx.session.events_of("creature_died")[deaths_before:]
    )


def _leave(ctx: SkillContext, record: dict[str, Any]) -> SkillOutcome:
    """Decided it is not a foe: leave it be and do not take it up again (unless it attacks)."""
    ctx.goal.progress["remembered"] = True  # 싸우지 않았다. 싸움 기록·회고가 아니다
    ctx.memory.setdefault("left_alone", set()).add(str(record.get("id", "")))
    return SkillOutcome(True, "left", "", dict(record))


async def _rethink(
    ctx: SkillContext, name: str, record: dict[str, Any], why_ko: str | None
) -> Tactic | SkillOutcome:
    """Something changed mid-fight (the bow broke, the leader said something): decide again."""
    if why_ko:
        await _say(ctx, why_ko)
    thought = await _think(ctx, name, record, midway=True)
    if isinstance(thought, SkillOutcome):
        return SkillOutcome(thought.ok, thought.code, thought.detail_ko, dict(record))
    record.setdefault("tactic_changes", []).append([record["seconds"], thought.model_dump()])
    ctx.goal.progress["tactic"] = thought
    await _say(ctx, thought.speech_ko)
    if thought.style == "leave":
        return _leave(ctx, record)
    return thought


def describe_looks(creature: dict[str, Any]) -> str:
    """How a creature looks on Thorkell's screen, in words."""
    looks = []
    if creature.get("height_m"):
        looks.append(tr(f"키 약 {creature['height_m']:g}m", f"about {creature['height_m']:g}m tall"))
    if creature.get("top_bar"):
        looks.append(
            tr(
                "화면 위쪽에 큰 체력바와 이름이 떴다",
                "a big health bar and name came up at the top of the screen",
            )
        )
    elif creature.get("health") is not None:
        looks.append(tr("머리 위에 이름과 체력바", "name and health bar over its head"))
    if creature.get("health") is not None:
        health = round(float(creature["health"]) * 100)
        looks.append(tr(f"체력 {health}%", f"health {health}%"))
    if creature.get("stars"):
        looks.append(tr(f"별 {creature['stars']}개", f"{creature['stars']} stars"))
    distance = round(float(creature["distance"]))
    looks.append(tr(f"{distance}m 앞", f"{distance}m ahead"))
    if creature.get("alerted"):
        looks.append(tr("나를 알아챘다", "noticed me"))
    return ", ".join(looks)


def describe(ctx: SkillContext, name: str, creature: dict[str, Any]) -> FightView:
    """What Thorkell's own screen shows of the creature, himself and the leader, in words."""
    state = ctx.session.state.data if ctx.session.state else {}
    foods = _foods(ctx)
    bag_food = [f"{i['name']} {i.get('stack', 1)}" for i in ctx.session.inventory() if i.get("food")]
    held = _weapons(ctx) + [i for i in ctx.session.inventory() if i.get("type") == "Bow"]
    weapons = [
        tr(f"{w['name']}(부서짐)", f"{w['name']} (broken)")
        if float(w.get("durability", 1.0)) <= 0
        else tr(f"{w['name']}({_damage_ko(w)})", f"{w['name']} ({_damage_ko(w)})")
        for w in held
    ]
    arrows = sum(int(i.get("stack", 0)) for i in ctx.session.inventory() if i.get("type") == "Ammo")
    hp = f"{round(float(state.get('hp', 0)))}/{round(float(state.get('hp_max', 0)))}"
    stamina = f"{round(float(state.get('stamina', 0)))}/{round(float(state.get('stamina_max', 0)))}"
    none = tr("없음", "none")
    me = [
        tr(f"체력 {hp}, 스태미나 {stamina}", f"Health {hp}, stamina {stamina}"),
        tr(f"음식 칸 {len(foods)}/{FOOD_SLOTS}", f"Food slots {len(foods)}/{FOOD_SLOTS}")
        + (tr(f"({', '.join(foods)})", f" ({', '.join(foods)})") if foods else ""),
        tr("가방의 음식: ", "Food in my bag: ") + (", ".join(bag_food) or none),
        tr("무기: ", "Weapons: ")
        + (", ".join(weapons) or none)
        + (tr(f", 화살 {arrows}개", f", {arrows} arrows") if arrows else ""),
    ]
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    if leader:
        leader_m = round(float(leader["distance"]))
        leader_ko = tr(f"{leader_m}m 떨어져 있다", f"{leader_m}m away")
    else:
        leader_ko = tr("안 보인다", "not in sight")
    fell = ctx.goal.progress.get("leader_fell_s")
    if fell is not None:
        leader_ko = (
            tr(
                f"싸움 {fell:g}초에 쓰러졌다(쓰러진 자리에 시체가 있다). 지금은 ",
                f"Fell {fell:g} s into the fight (the body lies where they fell). Now ",
            )
            + leader_ko
        )
    if ctx.mind is not None:
        since = time.time() - LEADER_WORDS_S
        words = [t for who, t in ctx.mind.store.recent_utterances(since=since) if who == ctx.mind.leader_name]
        if words:
            leader_ko += tr("\n리더가 최근에 한 말: ", "\nWhat the leader said lately: ") + " / ".join(
                f'"{w}"' for w in words
            )
    return FightView(
        name, f"{name}: {describe_looks(creature)}", "\n".join(me), leader_ko, _bow(ctx) is not None
    )


def _damage_ko(weapon: dict[str, Any]) -> str:
    """The weapon's damage the way its tooltip reads ("Blunt 6" in English: the game's word is the type
    capitalised)."""
    english = lang.current() == "en"
    return ", ".join(
        f"{k.capitalize() if english else DAMAGE_KO.get(k, k)} {float(v):g}"
        for k, v in weapon.get("damage", {}).items()
        if v
    )


def _foods(ctx: SkillContext) -> list[str]:
    return [str(f["name"]) for f in (ctx.session.scene.data.get("foods", []) if ctx.session.scene else [])]


async def fill_food(ctx: SkillContext) -> list[str]:
    """Fill the empty food slots with the best foods in the bag (each kind once)."""
    eaten: list[str] = []
    for _slot in range(FOOD_SLOTS):
        await _wait_scene(ctx)
        active = set(_foods(ctx))
        if len(active) >= FOOD_SLOTS:
            break
        foods = [i for i in ctx.session.inventory() if i.get("food") and i["name"] not in active]
        if not foods:
            break
        best = max(
            foods, key=lambda i: float(i["food"].get("health", 0)) + float(i["food"].get("stamina", 0))
        )
        done = await run_child(ctx, f"eat:{best['name']}", "eat", {"item": best["name"]}, eat)
        if not done.ok:
            break
        eaten.append(str(best["name"]))
    return eaten


async def _carry_out(ctx: SkillContext, name: str, tactic: Tactic, record: dict[str, Any]) -> SkillOutcome:
    """Fight as decided until Thorkell sees it fall (its body drops: `creature_died`), loses it, or gives up.
    Out of sight is not a win: then he goes back to look for it."""
    seen_at: float | None = None
    last_pos: list[float] | None = None
    distance = float("inf")
    swings = 0
    side = 1.0
    said_at = -SAY_EVERY_S
    shots: dict[str, int] = record["shots"]
    progress = ctx.goal.progress
    began = float(progress["began"])
    killed = False
    recovering = False
    # 물러나 있던 시간도 이 싸움의 기록이다(그동안은 싸우지 않는다).
    recovering_s = float(record.get("recovering_s", 0.0))
    tick = time.monotonic()
    looked_back = False
    creature_id: str | None = record.get("id")
    deaths_before = len(ctx.session.events_of("creature_died"))
    progress.setdefault("attacks_from", len(ctx.session.events_of("creature_attacking")))
    gained_at = time.monotonic()
    _round = 0
    used_seq = -1
    messages_from = len(ctx.session.events_of("game_message"))
    held_at_start = _held(ctx)  # 전리품이 무엇인지는 싸우기 전과 비교한다(쓰러지면 곁의 것은 바로 주워진다)
    leader_ids: set[str] = set()
    while True:
        _round += 1
        # 지난 차례 뒤에 새 장면이 이미 왔으면 기다리지 않는다(쏘는 동안 온 장면으로 바로 다음 화살을 당긴다).
        await _scene_after(ctx, used_seq)
        used_seq = ctx.session.scene.seq if ctx.session.scene else used_seq
        now = time.monotonic()
        record["seconds"] = round(now - began, 1)
        if progress.pop("heard", False):
            # 리더가 싸우는 중에 말했다(그 말은 기억에 있다). 사람은 듣고 다시 판단한다.
            changed = await _rethink(ctx, name, record, None)
            if isinstance(changed, SkillOutcome):
                return changed
            tactic = changed
            gained_at = now
        if _leader_fell(ctx, leader_ids, deaths_before) and "leader_fell_s" not in progress:
            # 앞에서 막던 리더가 쓰러졌다(실게임 2026-10-20: 모른 채 같은 방법으로 쏘다가 번개를 맞고 죽었다).
            # 사람은 친구가 쓰러지는 것을 보고 다시 판단한다.
            progress["leader_fell_s"] = record["leader_fell_s"] = record["seconds"]
            changed = await _rethink(ctx, name, record, tr("리더가 쓰러졌어!", "The leader is down!"))
            if isinstance(changed, SkillOutcome):
                return changed
            tactic = changed
            gained_at = now
        if now - gained_at > STALL_S and not progress.get("rethought_stall"):
            # 진척이 멈추면 그만두기 전에 한 번 다시 생각한다(실게임 2026-10-20: 화살 절반이 나무에 막혀
            # 68%에서 멈췄는데 그대로 끝냈다). 지금 싸움의 기록을 보고 자리나 방법을 바꾼다.
            progress["rethought_stall"] = True
            # 지금 안 보이면(나무 뒤, 리더가 끌고 감) 생각하려다 못 찾아 싸움을 끝내지 않는다.
            # 실게임(2026-10-20): 42%까지 깎은 보스가 잠깐 안 보일 때 다시 생각하려다 "안 보여"로 끝냈다.
            if _find(ctx, name) is not None:
                changed = await _rethink(
                    ctx,
                    name,
                    record,
                    tr("잘 안 먹히네. 다시 생각해 볼게", "This isn't working. Let me think again."),
                )
                if isinstance(changed, SkillOutcome):
                    return changed
                tactic = changed
            gained_at = now
        if now - gained_at > STALL_S:
            # 상대 체력이 줄고 있는 동안은 계속한다(실게임: 2% 남은 보스를 차례 수로 끊었다).
            return SkillOutcome(
                False,
                "too_long",
                tr("너무 오래 싸웠어. 잠깐 정리하자", "This fight's dragging on. Let's regroup for a bit"),
                dict(record),
            )
        if recovering:
            recovering_s += now - tick
            record["recovering_s"] = round(recovering_s, 1)
        tick = now
        state = ctx.session.state.data if ctx.session.state else {}
        hp = float(state.get("hp", 1)) / max(1.0, float(state.get("hp_max", 1)))
        record["my_hp_min"] = round(min(hp, float(record.get("my_hp_min", 1.0))), 2)
        # 사람은 체력바가 줄고 차는 것을 본다(물러나도 거의 안 차는 것까지). 상대가 안 보일 때도 보인다.
        mine: list[list[float]] = record.setdefault("my_health", [])
        if not mine or abs(mine[-1][1] - hp) >= HEALTH_STEP:
            mine.append([record["seconds"], round(hp, 2)])
        creature = _find(ctx, name)
        if creature is not None:
            distance = record["last_m"] = round(float(creature["distance"]))
        progress["hits_from"] = _note_hits(
            ctx.session, name, creature_id, began, progress["hits_from"], record
        )
        joined = record.get("joined")
        near = next(
            (
                e
                for e in ctx.session.nearby("creature")
                if joined is not None and e["id"] == joined["id"] and float(e["distance"]) <= JOINED_NEAR_M
            ),
            None,
        )
        if (
            joined is not None
            and near is not None
            and record["seconds"] - float(joined["at"]) <= JOINED_HIT_S
        ):
            # 끼어들어 때리는 놈을 두고 상대만 보면 그놈에게 맞아 죽는다(실게임: 보스 싸움 중 멧돼지에게 8번).
            record["joined"] = None
            record.setdefault("handled", []).append(str(joined["name"]))
            await _say(ctx, tr(f"{joined['name']}부터 처리할게!", f"Dealing with {joined['name']} first!"))
            with _timed(record, "other"):
                await run_child(
                    ctx,
                    f"joined:{joined['id']}",
                    "defend",
                    {"attacker_id": joined["id"], "name": joined["name"]},
                    defend,
                )
            continue
        fell = [
            e
            for e in ctx.session.events_of("creature_died")[deaths_before:]
            if e.data.get("id") == creature_id
        ]
        # 쓰러지는 걸 못 봐도 게임이 화면 가운데에 알린다(실게임: "에이크쉬르를 처치했습니다").
        told = [
            e
            for e in ctx.session.events_of("game_message")[messages_from:]
            if e.data.get("where") == "center"
            and name in str(e.data.get("text", ""))
            and SLAIN_WORD[lang.current()] in str(e.data.get("text", ""))
        ]
        if told:
            if last_pos is not None:
                await _loot(ctx, last_pos, name, held_at_start)
            return SkillOutcome(
                True, "killed", tr(f"{josa(name, '을를')} 해치웠어!", f"Took down {name}!"), dict(record)
            )
        if creature is None or fell:
            # 빗나간 화살이 떨어진 것은 전리품이 아니다(실게임에서 그걸로 이겼다고 착각했다).
            if killed or fell:
                at = list(fell[0].data.get("pos") or last_pos or []) if fell else last_pos
                if at:
                    await _loot(ctx, at, name, held_at_start)
                return SkillOutcome(
                    True, "killed", tr(f"{josa(name, '을를')} 해치웠어!", f"Took down {name}!"), dict(record)
                )
            if seen_at is None:
                if _round > LOOK_FOR_IT_SCENES:
                    return SkillOutcome(
                        False,
                        "not_found",
                        tr(f"{josa(name, '이가')} 안 보여", f"I can't see {name}"),
                        dict(record),
                    )
                continue
            scene = ctx.session.scene.data if ctx.session.scene else {}
            top_bar = next(
                (
                    b
                    for b in scene.get("boss_bars", [])
                    if b.get("id") == creature_id or b.get("name") == name
                ),
                None,
            )
            if top_bar is not None:
                # 가려졌을 뿐 화면 위쪽 체력바가 그대로다: 살아 있고 가까이 있다. 놓쳤다고 하지 않고 찾아간다
                # (실게임: 리더와 싸우는 보스가 시야를 들락날락하자 20초 뒤 "놓쳤어"로 끝냈다).
                seen_at = now
                if last_pos is not None and distance_m(_here(ctx), last_pos) > tactic.keep_m:
                    await _do(
                        ctx,
                        "move_to",
                        {
                            "target": {"pos": last_pos},
                            "arrive_radius": tactic.keep_m,
                            "run": True,
                            "timeout_s": 6,
                        },
                        timeout=8,
                    )
                continue
            if not looked_back and last_pos is not None:
                # 안 보이게 됐을 뿐이다(언덕 너머 등). 마지막으로 본 쪽으로 가 본다.
                looked_back = True
                await _do(
                    ctx,
                    "move_to",
                    {
                        "target": {"pos": last_pos},
                        "arrive_radius": tactic.keep_m,
                        "run": True,
                        "timeout_s": 20,
                    },
                    timeout=25,
                )
                continue
            if now - seen_at > GONE_S:
                code = "avoided" if tactic.style == "keep_away" else "lost"
                return SkillOutcome(
                    tactic.style == "keep_away",
                    code,
                    tr(
                        f"{josa(name, '을를')} 놓쳤어. 어디 갔는지 안 보여",
                        f"Lost {name}. I can't see where it went",
                    ),
                    dict(record),
                )
            continue
        looked_back = False
        creature_id = record["id"] = str(creature["id"])
        if _winding_up(ctx, tactic, record, creature_id):
            await _roll_aside(ctx, creature, record)
            continue

        async def act(
            op: str,
            args: dict[str, Any],
            timeout: float,
            foe: dict[str, Any] = creature,
            decided: Tactic = tactic,
        ) -> Result | None:
            return await _watching(ctx, decided, record, foe, op, args, timeout)

        seen_at = now
        last_pos = list(creature["pos"])
        bar: list[list[float]] = record["health"]
        if creature.get("health") is not None and (not bar or bar[-1][1] != creature["health"]):
            if bar and float(creature["health"]) < bar[-1][1]:
                gained_at = now
            bar.append([record["seconds"], float(creature["health"])])
        was_recovering = recovering
        recovering = hp < (tactic.return_hp if recovering else tactic.retreat_hp)
        if recovering and not was_recovering:
            record["retreats"] = int(record.get("retreats", 0)) + 1
        # 가까우면 물러난다. 구르기는 공격 동작이 보일 때만 한다(_winding_up). 가깝다고 매번 구르면 스태미나만
        # 바닥나고 쏠 틈이 없다(실게임: 183초 중 구르기 36번, 쏘기 3번).
        close = tactic.style != "melee" and distance < tactic.close_m
        if recovering:
            await _back_off(
                ctx, creature, tactic.keep_m + SHOOT_SLACK_M, tactic.retreat_to_leader, act, record
            )
            # 물러나기 시작할 때 한 번 말한다. 물러나 있는 동안 되풀이하지 않는다(실게임: 5분 동안 15번).
            if not was_recovering and now - said_at > SAY_EVERY_S:
                said_at = now
                await _say(
                    ctx, tr("피가 얼마 없어, 잠깐 빠질게!", "I'm low on health, backing off for a bit!")
                )
            began_eating = time.monotonic()
            ate = await fill_food(ctx)
            if ate:
                record.setdefault("ate", []).extend(ate)
                _count(record, "eat", began_eating)
            continue
        if close:
            await _back_off(ctx, creature, tactic.keep_m, tactic.retreat_to_leader, act, record)
            swings = 0
            continue
        if tactic.style == "keep_away":
            if distance < tactic.keep_m:
                await _back_off(ctx, creature, tactic.keep_m, tactic.retreat_to_leader, act, record)
            else:
                with _timed(record, "wait"):
                    await act("wait", {"seconds": 1.0}, 4)
            continue
        bow = _bow(ctx) if tactic.style == "ranged" else None
        if tactic.style == "ranged" and bow is None:
            # 싸우다 활이 부서지거나 화살이 떨어졌다. 사람은 남은 것으로 어떻게 할지 다시 정한다.
            broken = any(
                i.get("type") == "Bow" and float(i.get("durability", 1.0)) <= 0
                for i in ctx.session.inventory()
            )
            changed = await _rethink(
                ctx,
                name,
                record,
                tr(
                    "활이 부서졌어! 어떻게 할지 다시 생각해 볼게",
                    "My bow broke! Let me think this over again",
                )
                if broken
                else tr("화살이 다 떨어졌어!", "I'm out of arrows!"),
            )
            if isinstance(changed, SkillOutcome):
                return changed
            tactic = changed
            continue
        if bow is not None:
            if not bow[0].get("equipped"):
                await _do(ctx, "equip", {"item": bow[0]["name"]})
            if distance > tactic.keep_m + SHOOT_SLACK_M:
                with _timed(record, "approach"):
                    await act(
                        "move_to",
                        {
                            "target": {"id": creature["id"]},
                            "arrive_radius": tactic.keep_m,
                            "run": True,
                            "timeout_s": 6,
                        },
                        8,
                    )
                continue
            fired = sum(shots.values())
            if fired and fired % SHOTS_PER_SIDE == 0:
                side = -side
            with _timed(record, "shoot"):
                shot = await act(
                    "shoot",
                    {
                        "id": creature["id"],
                        "strafe": _strafe(ctx, creature, side, distance, tactic),
                        "wait_hit": False,
                    },
                    12,
                )
            if shot is not None:
                shots[shot.code] = shots.get(shot.code, 0) + 1
                killed = killed or bool(shot.evidence.get("killed"))
                if shot.code == "no_line_of_sight":
                    # 나무·바위에 막혔다. 같은 자리에서 다시 쏘지 않는다(실게임: 55번 다시 쏘려 했다).
                    # 몸이 가까이에서 보이는 자리를 찾았으면 그리로, 못 찾았으면 옆으로 몇 걸음 옮긴다
                    # (실게임 2026-10-20: 몇 걸음으로는 넓은 덤불을 못 벗어나 44번 중 19번이 막혔다).
                    side = -side
                    clear = shot.evidence.get("clear_from")
                    # 진단: 몸이 보이는 자리를 찾아 준 횟수(못 찾으면 옆걸음).
                    moved = "to_clear_spot" if clear else "sidestep"
                    record.setdefault("blocked_moves", {}).setdefault(moved, 0)
                    record["blocked_moves"][moved] += 1
                    with _timed(record, "reposition"):
                        await act(
                            "move_to",
                            {
                                "target": {"pos": list(clear) if clear else _aside(ctx, creature, side)},
                                "arrive_radius": 1.0,
                                "timeout_s": 6 if clear else 4,
                            },
                            8 if clear else 6,
                        )
            continue
        weapon = await equip_for_fight(ctx, name)
        if swings >= tactic.hits_then_back:
            await _back_off(ctx, creature, tactic.keep_m, tactic.retreat_to_leader, act, record)
            swings = 0
            continue
        with _timed(record, "swing"):
            result = await _attack(ctx, creature, 1, weapon, timeout=8)
        killed = killed or bool(result.evidence.get("destroyed"))
        if result.code == "out_of_reach":
            await _do(
                ctx,
                "move_to",
                {"target": {"id": creature["id"]}, "arrive_radius": 1.8, "timeout_s": 4},
                timeout=6,
            )
        else:
            swings += 1
            record["swings"] = int(record.get("swings", 0)) + 1


def _note_hits(
    session: BodySession, name: str, creature_id: str | None, began: float, since: int, record: dict[str, Any]
) -> int:
    """Hits since the last look: from this creature, with how far it was then (the last distance seen), and
    from anything else that joined in (a person sees who hit them, not only the one they fight)."""
    events = session.events_of("damage_taken")
    for event in events[since:]:
        data = event.data
        kinds = sorted(k for k, v in (data.get("types") or {}).items() if float(v) > 0)
        at = round(time.monotonic() - began, 1)
        amount = round(float(data.get("amount", 0)), 1)
        if data.get("attacker_name") == name or data.get("attacker_id") == creature_id:
            record["hits"].append([at, amount, record.get("last_m", -1), kinds])
        elif data.get("attacker_name"):
            record.setdefault("others", []).append([at, amount, str(data["attacker_name"]), kinds])
            record["joined"] = {"id": data.get("attacker_id"), "name": data["attacker_name"], "at": at}
    return len(events)


def close_record(session: BodySession, goal: Goal) -> dict[str, Any]:
    """The fight's record when it ends, including hits that came after the skill's last look (the killing
    blow arrives as the skill is being stopped)."""
    progress = goal.progress
    record: dict[str, Any] = progress["record"]
    name = str(goal.args["creature"])
    progress["hits_from"] = _note_hits(
        session, name, record.get("id"), float(progress["began"]), int(progress["hits_from"]), record
    )
    record["seconds"] = round(time.monotonic() - float(progress["began"]), 1)
    return record


def _strafe(
    ctx: SkillContext, creature: dict[str, Any], side: float, distance: float, tactic: Tactic
) -> list[float]:
    """Sideways to the creature (dodges what it throws), drifting back when it is inside the kept distance."""
    here = _here(ctx)
    dx, dz = here[0] - creature["pos"][0], here[2] - creature["pos"][2]
    length = math.hypot(dx, dz) or 1.0
    away = (dx / length, dz / length)
    back = 0.6 if distance < tactic.keep_m else 0.0
    return [-away[1] * side + away[0] * back, 0.0, away[0] * side + away[1] * back]


def _away(ctx: SkillContext, creature: dict[str, Any], metres: float, toward_leader: bool) -> list[float]:
    """A point `metres` away from the creature; leaning toward the leader if the tactic says so. When the
    leader is beyond the creature, only sideways toward the leader: running at the leader runs past it."""
    here = _here(ctx)
    dx, dz = here[0] - creature["pos"][0], here[2] - creature["pos"][2]
    length = math.hypot(dx, dz) or 1.0
    away = (dx / length, dz / length)
    scene = ctx.session.scene.data if ctx.session.scene else {}
    leader = scene.get("leader") or scene.get("leader_on_map")
    if toward_leader and leader is not None:
        lx, lz = leader["pos"][0] - here[0], leader["pos"][2] - here[2]
        to_leader = math.hypot(lx, lz)
        if to_leader > LEADER_BESIDE_M:
            lx, lz = lx / to_leader, lz / to_leader
            behind = min(0.0, lx * away[0] + lz * away[1])
            ax, az = away[0] + lx - behind * away[0], away[1] + lz - behind * away[1]
            norm = math.hypot(ax, az) or 1.0
            away = (ax / norm, az / norm)
    return [here[0] + away[0] * metres, here[1], here[2] + away[1] * metres]


async def _back_off(
    ctx: SkillContext,
    creature: dict[str, Any],
    to: float,
    toward_leader: bool,
    act: Callable[[str, dict[str, Any], float], Awaitable[Result | None]] | None = None,
    record: dict[str, Any] | None = None,
) -> None:
    gap = distance_m(_here(ctx), creature["pos"])
    if gap >= to:
        return
    began = time.monotonic()
    args = {
        "target": {"pos": _away(ctx, creature, to - gap, toward_leader)},
        "arrive_radius": 2.0,
        "run": True,
        "timeout_s": 6,
    }
    if act is not None:
        await act("move_to", args, 8)
    else:
        await _do(ctx, "move_to", args, timeout=8)
    if record is not None:
        _count(record, "back_off", began)


async def _scene_after(ctx: SkillContext, seq: int) -> None:
    await ctx.session.wait_for(
        lambda: ctx.session.scene is not None and ctx.session.scene.seq > seq, timeout=5
    )


def _winding_up(ctx: SkillContext, tactic: Tactic, record: dict[str, Any], creature_id: str) -> bool:
    """Was the foe seen starting an attack since the last look, close enough to roll aside as decided?"""
    events = ctx.session.events_of("creature_attacking")
    progress = ctx.goal.progress
    new, progress["attacks_from"] = events[int(progress["attacks_from"]) :], len(events)
    seen = [e for e in new if e.data.get("id") == creature_id]
    record["saw_attacks"] = int(record.get("saw_attacks", 0)) + len(seen)
    state = ctx.session.state.data if ctx.session.state else {}
    return (
        tactic.dodge_within_m > 0
        and any(float(e.data.get("distance", 999.0)) <= tactic.dodge_within_m for e in seen)
        and float(state.get("stamina", 0)) >= DODGE_STAMINA
    )


async def _watching(
    ctx: SkillContext,
    tactic: Tactic,
    record: dict[str, Any],
    creature: dict[str, Any],
    op: str,
    args: dict[str, Any],
    timeout: float,
) -> Result | None:
    """A command, unless the foe is seen starting an attack within the decided distance meanwhile: then it
    stops and Thorkell rolls aside (a person sees the wind-up and rolls). None when it rolled instead."""
    task = asyncio.create_task(_do(ctx, op, args, timeout=timeout))
    try:
        while not task.done():
            if _winding_up(ctx, tactic, record, str(creature["id"])):
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                await _roll_aside(ctx, creature, record)
                return None
            await asyncio.wait({task}, timeout=WATCH_S)
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def _aside(ctx: SkillContext, creature: dict[str, Any], side: float) -> list[float]:
    """A spot a few steps sideways to the creature, to see past what is in the way."""
    here = _here(ctx)
    dx, dz = here[0] - creature["pos"][0], here[2] - creature["pos"][2]
    length = math.hypot(dx, dz) or 1.0
    return [here[0] - dz / length * side * SIDESTEP_M, here[1], here[2] + dx / length * side * SIDESTEP_M]


async def _roll_aside(ctx: SkillContext, creature: dict[str, Any], record: dict[str, Any]) -> None:
    """Roll sideways to the foe, to alternating sides (out of the line of what it throws or swings)."""
    here = _here(ctx)
    dx, dz = here[0] - creature["pos"][0], here[2] - creature["pos"][2]
    length = math.hypot(dx, dz) or 1.0
    side = 1.0 if int(record.get("dodged", 0)) % 2 == 0 else -1.0
    toward = [
        here[0] - dz / length * side * ROLL_ASIDE_M,
        here[1],
        here[2] + dx / length * side * ROLL_ASIDE_M,
    ]
    record["dodged"] = int(record.get("dodged", 0)) + 1
    with _timed(record, "roll"):
        await _do(ctx, "dodge", {"toward": toward}, timeout=3)


@contextlib.contextmanager
def _timed(record: dict[str, Any], what: str) -> Iterator[None]:
    """Count what Thorkell did in the fight and how long it took (a person remembers "I mostly ran")."""
    began = time.monotonic()
    try:
        yield
    finally:
        _count(record, what, began)


def _count(record: dict[str, Any], what: str, began: float) -> None:
    done = record.setdefault("time", {}).setdefault(what, [0, 0.0])
    done[0], done[1] = done[0] + 1, round(done[1] + time.monotonic() - began, 1)


SKILLS = {"fight": fight}
