"""Hunting, searching for something by name, and cooking — field skills a first-time player learns by doing.

A creature is chosen by the name its name tag showed (or recognised later from afar by its kind). Whether
it runs away is learned by watching it; what it drops is learned by looking at the inventory after the kill.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

from thorkell import lang
from thorkell.control.making import WOOD, Skill, _game_says_since, _here, build, held, menu, run_child
from thorkell.control.skills import (
    SkillContext,
    SkillOutcome,
    _attack,
    _do,
    _held,
    _nearest,
    _wait_scene,
    equip_for_fight,
)
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.world.where import distance_m

# 활은 이 거리 안에서 쏜다(화살이 떨어지기 전에 맞힐 수 있는 거리). 그보다 멀면 다가간다.
BOW_RANGE_M = 25.0
BOW_STANDOFF_M = 18.0
# 근접으로 쫓다가 이만큼 연달아 거리가 벌어지면 "달아나는 동물"로 배운다.
CHASE_LOSSES = 3
# 몰래 다가가서 멈추는 거리(손이 닿는 거리 안).
SNEAK_REACH_M = 1.6
CLOSE_M = 5.0
SEARCH_LEGS = 8
SEARCH_LEG_M = 30.0
# 한 번 돌 때마다 처음 자리에서 이만큼(비율)씩 더 멀리 간다.
SEARCH_GROWTH = 0.5
COOK_S = 25.0
COOK_SLOTS = 2


def _matches(ctx: SkillContext, entity: dict[str, Any], name: str) -> bool:
    if entity.get("kind") != "creature":
        return False
    if entity.get("name") == name:
        return True
    key = entity.get("key")
    return bool(key) and ctx.world is not None and ctx.world.species_name(str(key)) == name


def _find(ctx: SkillContext, name: str) -> dict[str, Any] | None:
    found = [e for e in ctx.session.nearby() if _matches(ctx, e, name)]
    return min(found, key=lambda e: e["distance"]) if found else None


# 이름표는 쳐다본 생물에게만 뜬다(30m 안). 찾는 동안 이름 모를 생물이 보이면 멈춰서 쳐다본다.
LOOK_WITHIN_M = 30.0
LOOKS_PER_PAUSE = 3
# 탐색 한 번에 다가가서 볼 먼 생물 수.
FAR_LOOKS_PER_LEG = 2


async def look_around(ctx: SkillContext) -> None:
    """Stop and look at creatures in view whose name tag has not been seen, the way a player turns the
    camera to read what is out there."""
    unknown = [
        e
        for e in ctx.session.nearby("creature")
        if not e.get("name")
        and float(e["distance"]) <= LOOK_WITHIN_M
        and not (ctx.world is not None and e.get("key") and ctx.world.species_name(str(e["key"])))
    ]
    looks: list[dict[str, Any]] = ctx.goal.progress.setdefault("looks", [])
    for creature in sorted(unknown, key=lambda e: e["distance"])[:LOOKS_PER_PAUSE]:
        looked = await _do(ctx, "look_at", {"target": {"id": creature["id"]}}, timeout=5)
        looks.append({"id": creature["id"], "d": round(float(creature["distance"]), 1), **looked.evidence})
    if unknown:
        await _wait_scene(ctx)
    seen: list[list[Any]] = ctx.goal.progress.setdefault("seen", [])
    seen.append(
        [
            (e.get("name") or "?", e.get("key"), round(float(e["distance"]), 1))
            for e in ctx.session.nearby("creature")
        ]
    )


def _far_unknown(ctx: SkillContext) -> dict[str, Any] | None:
    """The nearest creature in view too far for its name tag, of a kind not known yet."""
    far = [
        e
        for e in ctx.session.nearby("creature")
        if not e.get("name")
        and float(e["distance"]) > LOOK_WITHIN_M
        and not (ctx.world is not None and e.get("key") and ctx.world.species_name(str(e["key"])))
    ]
    return min(far, key=lambda e: e["distance"]) if far else None


def _bow(ctx: SkillContext) -> tuple[dict[str, Any], dict[str, Any]] | None:
    inventory = ctx.session.inventory()
    # 내구도가 0인 활은 부서져서 못 쓴다(실게임: 부서진 활로 41번 쏘려 했다).
    bow = next((i for i in inventory if i.get("type") == "Bow" and float(i.get("durability", 1.0)) > 0), None)
    ammo = next((i for i in inventory if i.get("type") == "Ammo" and int(i.get("stack", 0)) > 0), None)
    return (bow, ammo) if bow is not None and ammo is not None else None


def _flees(ctx: SkillContext, name: str) -> bool:
    if ctx.mind is None:
        return False
    return any(f.predicate == "flees" and f.status != "refuted" for f in ctx.mind.store.facts_about(name))


async def search(ctx: SkillContext) -> SkillOutcome:
    """Look around for something called `name` the bot has not seen yet (or not nearby): walk out in legs,
    glancing at what comes into view. The body glances at creatures so their name tags show."""
    name = str(ctx.goal.args["name"])
    # 처음 자리에서 점점 멀어지며 돈다(나선). 실게임(2026-10-20): 제자리 둘레 30m만 오가다 사슴을 못 찾고
    # 리더에게 어디 있느냐고 물었다. 사람은 들판 쪽으로 더 나가 본다.
    start = _here(ctx)

    def found() -> bool:
        return _find(ctx, name) is not None or any(e.get("name") == name for e in ctx.session.nearby())

    for leg in range(SEARCH_LEGS + 1):
        await _wait_scene(ctx)
        await look_around(ctx)
        # 멀리(이름표가 뜨는 30m 밖) 이름 모를 생물이 보이면 다가가서 본다("저건 뭐지?").
        for _ in range(FAR_LOOKS_PER_LEG):
            if found():
                break
            far = _far_unknown(ctx)
            if far is None:
                break
            await _do(
                ctx,
                "move_to",
                {"target": {"id": far["id"]}, "arrive_radius": LOOK_WITHIN_M - 5, "timeout_s": 30},
                timeout=35,
            )
            await _wait_scene(ctx)
            await look_around(ctx)
        if found():
            return SkillOutcome(True, "found", tr(f"{josa(name, '을를')} 찾았어", f"Found the {name}"))
        if leg == SEARCH_LEGS:
            break
        angle = leg * 2.4 + 0.7
        reach = SEARCH_LEG_M * (1 + leg * SEARCH_GROWTH)
        point = [start[0] + reach * math.cos(angle), start[1], start[2] + reach * math.sin(angle)]
        await _do(ctx, "move_to", {"target": {"pos": point}, "arrive_radius": 3.0}, timeout=60)
    return SkillOutcome(
        False,
        "not_found",
        tr(f"근처를 돌아봤는데 {josa(name, '은는')} 안 보여", f"I looked around, but no {name} anywhere"),
        {"looks": ctx.goal.progress.get("looks"), "seen": ctx.goal.progress.get("seen")},
    )


async def hunt(ctx: SkillContext) -> SkillOutcome:
    """Kill `count` creatures called `creature` and pick up what they drop."""
    name, count = str(ctx.goal.args["creature"]), int(ctx.goal.args.get("count", 1))
    progress = ctx.goal.progress
    kills: int = progress.setdefault("kills", 0)
    while kills < count:
        await _wait_scene(ctx)
        target = _find(ctx, name)
        if target is None:
            await look_around(ctx)
            target = _find(ctx, name)
        if target is None:
            found = await run_child(ctx, f"search:{kills}", "search", {"name": name}, search)
            if not found.ok:
                return SkillOutcome(
                    kills > 0,
                    "not_found",
                    tr(
                        f"{josa(name, '을를')} {kills}마리 잡았어. 더는 안 보여",
                        f"Caught {kills} {name}. Can't see any more",
                    ),
                    {"search": found.evidence, "looks": progress.get("looks"), "seen": progress.get("seen")},
                )
            continue
        # 쓰러지자마자 곁의 것은 자동으로 주워진다. 무엇이 나왔는지는 싸우기 전과 비교한다.
        held_before = _held(ctx)
        killed = await _fight(ctx, target, name)
        if killed is None:
            return SkillOutcome(
                kills > 0,
                "lost",
                tr(f"{josa(name, '을를')} 놓쳤어 ({kills}/{count})", f"Lost the {name} ({kills}/{count})"),
            )
        kills += 1
        progress["kills"] = kills
        await _loot(ctx, killed, name, held_before)
    return SkillOutcome(
        True, "done", tr(f"{josa(name, '을를')} {kills}마리 잡았어", f"Caught {kills} {name}")
    )


async def _fight(ctx: SkillContext, target: dict[str, Any], name: str) -> list[float] | None:
    """Fight one creature until it falls (seen: `creature_died`). Returns where it fell, or None if it got
    away (out of sight without falling)."""
    target_id, last_pos = target["id"], list(target["pos"])
    deaths_before = len(ctx.session.events_of("creature_died"))
    losses, previous = 0, float(target["distance"])
    bow = _bow(ctx)
    ranged = bow is not None and (_flees(ctx, name) or previous > 8)
    # 쫓으면 달아나는 것을 아는 동물에게 활이 없으면 사람처럼 웅크리고 몰래 다가가 친다.
    sneaking = bow is None and _flees(ctx, name)

    def fell_at() -> list[float] | None:
        # 달리던 짐승은 마지막으로 본 자리(장면은 초당 두 번)보다 앞에서 쓰러진다. 쓰러진 자리에서 줍는다.
        for event in ctx.session.events_of("creature_died")[deaths_before:]:
            if event.data.get("id") == target_id:
                return list(event.data.get("pos") or last_pos)
        return None

    for _round in range(60):
        await _wait_scene(ctx)
        current = next((e for e in ctx.session.nearby() if e["id"] == target_id), None)
        if (fell := fell_at()) is not None:
            return fell
        if current is None:
            return None
        last_pos = list(current["pos"])
        distance = float(current["distance"])
        # 붙어서 덤비는 상대에게는 활을 당길 틈이 없다. 가까우면 근접 무기로 싸운다.
        if ranged and bow is not None and distance > CLOSE_M:
            await _do(ctx, "equip", {"item": bow[0]["name"]})
            if distance > BOW_RANGE_M:
                await _do(
                    ctx,
                    "move_to",
                    {
                        "target": {"id": target_id},
                        "arrive_radius": BOW_STANDOFF_M,
                        "run": True,
                        "timeout_s": 8,
                    },
                    timeout=12,
                )
                continue
            shot = await _do(ctx, "shoot", {"id": target_id}, timeout=15)
            if shot.code in ("no_ammo", "no_bow"):
                ranged, bow = False, None
            elif shot.code in ("no_line_of_sight", "out_of_range"):
                await _do(
                    ctx, "move_to", {"target": {"id": target_id}, "arrive_radius": 10.0, "timeout_s": 6}, 10
                )
            elif shot.evidence.get("killed"):
                await _wait_scene(ctx)
                return fell_at() or last_pos
            continue
        weapon = await equip_for_fight(ctx, name)
        if sneaking and distance > SNEAK_REACH_M:
            crept = await _do(
                ctx,
                "move_to",
                {"target": {"id": target_id}, "arrive_radius": SNEAK_REACH_M, "sneak": True, "timeout_s": 40},
                45,
            )
            if crept.code != "arrived":
                losses += 1
                if losses >= CHASE_LOSSES:
                    return None
                continue
        result = await _attack(ctx, current, 1, weapon, timeout=10, sneak=sneaking)
        if result.code == "out_of_reach":
            await _do(
                ctx,
                "move_to",
                {"target": {"id": target_id}, "arrive_radius": 1.6, "run": True, "timeout_s": 5},
                9,
            )
            await _wait_scene(ctx)
            now = next((e for e in ctx.session.nearby() if e["id"] == target_id), None)
            if now is not None and float(now["distance"]) > previous - 0.5:
                losses += 1
            previous = float(now["distance"]) if now is not None else previous
            if losses >= CHASE_LOSSES:
                # 쫓아갈수록 멀어진다: 달아나는 동물이다. 배워 두고, 활이 있으면 활로 바꾼다.
                if ctx.mind is not None:
                    _, after = ctx.mind.store.observe(name, "flees", "true")
                    if after.support == 1:
                        ctx.mind.learned(
                            tr(
                                f"{josa(name, '은는')} 쫓아가면 도망가네. 활 같은 게 있어야겠어.",
                                f"{name} runs off when I chase it. I need something like a bow.",
                            ),
                            f"flees:{name}",
                        )
                if bow is None:
                    # 이 녀석이 진정하면 몰래 다가가 본다.
                    if sneaking:
                        return None
                    sneaking, losses = True, 0
                    continue
                ranged, losses = True, 0
        elif result.evidence.get("destroyed"):
            await _wait_scene(ctx)
            return fell_at() or last_pos
    return None


async def _loot(ctx: SkillContext, at: list[float], name: str, before: dict[str, int]) -> None:
    """Walk over where it fell (the game picks up what lies within 2 m) and learn what it dropped."""
    await _do(ctx, "move_to", {"target": {"pos": at}, "arrive_radius": 0.8}, timeout=30)
    await asyncio.sleep(0.5)
    await _wait_scene(ctx)
    for lying in [e for e in ctx.session.nearby("item") if distance_m(e["pos"], at) < 4][:6]:
        moved = await _do(ctx, "move_to", {"target": {"id": lying["id"]}, "arrive_radius": 1.2}, timeout=20)
        if moved.code == "arrived":
            await _do(ctx, "pickup", {"id": lying["id"]})
    await _wait_scene(ctx)
    gained = [item for item, count in _held(ctx).items() if count > before.get(item, 0)]
    if ctx.world is not None:
        for item in gained:
            if ctx.world.learn_source(item, "creature", name) and ctx.mind is not None:
                ctx.mind.learned(
                    tr(
                        f"{josa(name, '을를')} 잡으니 {josa(item, '이가')} 나오네.",
                        f"So {name} drops {item}.",
                    ),
                    f"drop:{name}:{item}",
                )


# --- cooking ------------------------------------------------------------------------------------
async def cook(ctx: SkillContext) -> SkillOutcome:
    """Cook `count` of a raw `item` on a cooking station over a burning fire (built if there is none here)."""
    item, count = str(ctx.goal.args["item"]), int(ctx.goal.args.get("count", 1))
    if held(ctx, item) < 1:
        return SkillOutcome(
            False,
            "nothing_to_cook",
            tr(f"구울 {josa(item, '이가')} 없어", f"I don't have any {item} to cook"),
        )
    station = await _cooking_station(ctx)
    if isinstance(station, SkillOutcome):
        return station
    cooked: dict[str, int] = {}
    remaining = min(count, held(ctx, item))
    while remaining > 0:
        before = _held(ctx)
        since = len(ctx.session.events_of("game_message"))
        placed = 0
        for _slot in range(min(COOK_SLOTS, remaining)):
            await _do(ctx, "move_to", {"target": {"id": station}, "arrive_radius": 1.5}, timeout=30)
            used = await _do(ctx, "use_item", {"item": item, "id": station})
            if used.code != "used":
                break
            placed += 1
        if placed == 0:
            return SkillOutcome(
                False,
                "cannot_cook",
                tr(
                    f"요리대에 {josa(item, '을를')} 못 올렸어.",
                    f"I couldn't put the {item} on the Cooking Station.",
                )
                + _quote(_game_says_since(ctx, since)),
            )
        await _do(ctx, "wait", {"seconds": COOK_S + 1}, timeout=COOK_S + 10)
        for _take in range(placed):
            await _do(ctx, "interact", {"id": station})
            await asyncio.sleep(1.0)
        await _wait_scene(ctx)
        for name, value in _held(ctx).items():
            if value > before.get(name, 0) and name != item:
                cooked[name] = cooked.get(name, 0) + value - before.get(name, 0)
        remaining -= placed
    if not cooked:
        return SkillOutcome(
            False, "nothing_cooked", tr("굽긴 했는데 꺼낸 게 없어", "I cooked, but didn't get anything out")
        )
    made = ", ".join(tr(f"{name} {value}개", f"{value} {name}") for name, value in cooked.items())
    return SkillOutcome(True, "done", tr(f"{made} 구웠어", f"Cooked {made}"))


def _quote(said: str | None) -> str:
    if not said:
        return ""
    return tr(f" '{said}'래.", f" It says '{said}'.")


async def _cooking_station(ctx: SkillContext) -> str | SkillOutcome:
    station = _nearest(ctx, "cooking")
    if station is None:
        pieces = {p["name"]: p for p in await menu(ctx, "pieces")}
        fire_name = next((n for n, p in pieces.items() if _is_fire(p)), None)
        rack_name = next((n for n, p in pieces.items() if _is_rack(p)), None)
        if rack_name is None:
            return SkillOutcome(
                False,
                "no_cooking_station",
                tr("요리대를 아직 지을 줄 몰라", "I don't know how to build a Cooking Station yet"),
            )
        fire = _nearest(ctx, "fire")
        if fire is None and fire_name is not None:
            made = await run_child(ctx, "build:fire", "build", {"piece": fire_name}, build)
            if not made.ok:
                return made
            await _wait_scene(ctx)
            fire = _nearest(ctx, "fire")
        if fire is None:
            return SkillOutcome(False, "no_fire", tr("불이 있어야 구울 수 있어", "I need a fire to cook"))
        # 요리대는 불 바로 위에 있어야 익는다(게임: 불 영역 0.45m 안). 불 가운데를 겨눠서 짓는다.
        # pos는 다가갈 겉면이라 0.6m쯤 비켜나 "아래에 불을 피워야 한다"는 말을 들었다.
        made = await run_child(
            ctx,
            "build:rack",
            "build",
            {"piece": rack_name, "at": fire.get("center", fire["pos"]), "within_m": RACK_OVER_FIRE_M},
            build,
        )
        if not made.ok:
            return made
        await _wait_scene(ctx)
        station = _nearest(ctx, "cooking")
        if station is None:
            return SkillOutcome(
                False,
                "no_cooking_station",
                tr("요리대를 지었는데 안 보여", "I built the Cooking Station, but I can't see it"),
            )
    fire = _nearest(ctx, "fire")
    wood = next((i["name"] for i in ctx.session.inventory() if i["name"] == WOOD[lang.current()]), None)
    if fire is not None and wood is not None:
        await _do(ctx, "move_to", {"target": {"id": fire["id"]}, "arrive_radius": 1.5}, timeout=30)
        await _do(ctx, "use_item", {"item": wood, "id": fire["id"]})
    station_id: str = station["id"]
    return station_id


RACK_OVER_FIRE_M = 0.3


def _is_fire(piece: dict[str, Any]) -> bool:
    name = str(piece["name"])
    if lang.current() == "en":
        # 영어 이름: Campfire, Bonfire, Iron Fire Pit, Hearth. 횃불(Torch)은 불이 아니다.
        return "fire" in name.lower() or "Hearth" in name
    return "불" in name


def _is_rack(piece: dict[str, Any]) -> bool:
    return tr("요리", "Cooking Station") in str(piece["name"])


SKILLS: dict[str, Skill] = {"hunt": hunt, "search": search, "cook": cook}
