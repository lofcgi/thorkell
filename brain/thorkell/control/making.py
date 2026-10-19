"""Gathering any material, crafting and building — the way a first-time player does it.

What can be made is what the game's menus show (recipes and hammer pieces the game has unlocked, with
their materials and the station they need). Where a material comes from is learned: picking something,
chopping a tree or killing a creature and seeing the inventory grow. Something never tried is tried once
to see what it gives. Every step checks the world (inventory, the piece standing there), never a call.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from collections.abc import Callable, Coroutine
from typing import Any

from thorkell import lang
from thorkell.control.goals import Goal
from thorkell.control.skills import (
    BLOCKED_TRIES,
    SkillContext,
    SkillOutcome,
    _do,
    _held,
    _nearest,
    _wait_scene,
    can_chop,
    gather_wood,
)
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.world.where import distance_m

log = logging.getLogger(__name__)

Skill = Callable[[SkillContext], Coroutine[Any, Any, SkillOutcome]]
# 작업대는 루트에서 2m 안이어야 쓸 수 있다(CraftingStation.InUseDistance). 조금 안쪽까지 다가간다.
STATION_USE_M = 1.4
# 망치로 지을 때 눈에서 이 거리 안을 겨눈다(게임 한도 8m). 너무 붙으면 자기 몸과 겹친다.
PLACE_FROM_M = 3.0
SPOT_RADII = (3.0, 5.0)
# 집터(평평하고 트인 6x5m)를 찾아보는 반경. 가까운 데서부터.
SITE_RADII = (24, 40)
SITE_FAR_M = 50.0
SPOT_ANGLES = tuple(range(0, 360, 45))
# 주운 것이 인벤토리에 들어오기까지(덤불에서 튕겨 나와 자동 줍기) 기다리는 시간
PICK_SETTLE_S = 2.5
# 딴 것에서 떨어진 물건을 찾는 거리.
DROP_NEAR_M = 4.0
EXPLORE_LEGS = 4
EXPLORE_LEG_M = 25.0
# 게임이 보여 주는 이름은 게임의 언어를 따른다.
WOOD: dict[lang.Language, str] = {"ko": "나무", "en": "Wood"}
WORKBENCH: dict[lang.Language, str] = {"ko": "작업대", "en": "Workbench"}


# --- small helpers ------------------------------------------------------------------------------
async def menu(ctx: SkillContext, what: str) -> list[dict[str, Any]]:
    """What the crafting ('recipes') or hammer ('pieces') menu shows right now."""
    answer = await ctx.session.query(what, {})
    if not answer.ok:
        raise RuntimeError(f"body could not answer {what}: {answer.error}")
    entries: list[dict[str, Any]] = answer.data[what]
    return entries


def held(ctx: SkillContext, name: str) -> int:
    return _held(ctx).get(name, 0)


async def run_child(
    ctx: SkillContext, key: str, kind: str, args: dict[str, Any], skill: Skill
) -> SkillOutcome:
    """Run a sub-goal kept in this goal's progress, so a suspended goal resumes inside its sub-goal."""
    children: dict[str, Goal] = ctx.goal.progress.setdefault("children", {})
    child = children.get(key)
    if child is None or child.status in ("done", "failed"):
        child = Goal(kind, ctx.goal.tier, args, source=ctx.goal.id)
        children[key] = child
    child.status = "active"
    outcome = await skill(ctx.child(child))
    child.status = "done" if outcome.ok else "failed"
    return outcome


def _here(ctx: SkillContext) -> list[float]:
    assert ctx.session.state is not None
    pos: list[float] = ctx.session.state.data["pos"]
    return pos


async def _say(ctx: SkillContext, text: str) -> None:
    if ctx.speak is not None:
        await ctx.speak(text)


def _named_like(item: str, name: str) -> bool:
    """Is the thing called `name` named after `item`? English names the bush in the singular
    ("Raspberry Bush" gives "Raspberries")."""
    if lang.current() != "en":
        return item in name
    word = item.lower()
    singular = word[:-3] + "y" if word.endswith("ies") else word.removesuffix("s")
    return singular in name.lower()


# --- gathering ----------------------------------------------------------------------------------
async def gather(ctx: SkillContext) -> SkillOutcome:
    """Collect `count` of `item`, counting the inventory. Sources, in order: items lying around, things the
    bot has got it from before, things named like it, things never tried (try once and learn), places it
    was seen, then a short look around. Wood also comes from chopping trees."""
    asked = str(ctx.goal.args["item"])
    progress = ctx.goal.progress
    named = await _what_it_gives(ctx, asked)
    if isinstance(named, SkillOutcome):
        return named
    item = named
    start = progress.setdefault("held_at_start", held(ctx, item))
    if "count" in ctx.goal.args:
        target = int(ctx.goal.args["count"])
    else:
        # 개수를 안 정했으면 지금 보이는 만큼(딸 것 + 떨어진 것) 모은다. 이미 하나 따 봤으면 그것도 센다.
        target = progress.setdefault("in_sight", held(ctx, item) - start + _in_sight(ctx, asked, item))
        if target == 0:
            return SkillOutcome(
                False,
                "none_in_sight",
                tr(
                    f"근처에 {josa(item, '이가')} 안 보여. 몇 개나 필요해?",
                    f"I don't see any {item} nearby. How many do you need?",
                ),
            )
    tried: set[str] = set(progress.setdefault("tried", []))
    # 다가가지 못한 떨어진 것(틈에 빠진 나무 등)은 두고 다른 것을 찾는다(gather_wood와 같다).
    blocked: dict[str, int] = progress.setdefault("blocked", {})
    explored = 0
    while True:
        await _wait_scene(ctx)
        got = held(ctx, item) - start
        progress["gathered"] = got
        if got >= target:
            return SkillOutcome(True, "done", tr(f"{item} {got}개 모았어", f"Got {got} {item}"))
        lying = _nearest(ctx, "item", {item}, {i for i, tries in blocked.items() if tries >= BLOCKED_TRIES})
        if lying is not None:
            moved = await _do(
                ctx, "move_to", {"target": {"id": lying["id"]}, "arrive_radius": 1.2}, timeout=60
            )
            if moved.code == "arrived":
                await _do(ctx, "pickup", {"id": lying["id"]})
            elif moved.status == "failed":
                blocked[lying["id"]] = blocked.get(lying["id"], 0) + 1
            continue
        source = _pickable_source(ctx, item, tried)
        if source is not None:
            tried.add(source["id"])
            progress["tried"] = sorted(tried)
            await _pick(ctx, source)
            continue
        # 벨 도구가 없으면 나무는 베지 못한다. 떨어진 나뭇가지를 찾으러 둘러본다(실게임, 새 월드).
        trees = any(e for e in ctx.session.nearby() if e.get("kind") in ("tree", "log"))
        if item == WOOD[lang.current()] and trees and can_chop(ctx):
            wood = await run_child(
                ctx, f"chop:{explored}", "gather_wood", {"count": target - got}, gather_wood
            )
            if not wood.ok:
                return wood
            continue
        hunted = _creature_source(ctx, item)
        if hunted is not None:
            return SkillOutcome(
                False,
                "needs_hunting",
                tr(
                    f"{josa(item, '은는')} {hunted}에게서 나와. 사냥해야 해",
                    f"You get {item} from {hunted}. I need to hunt",
                ),
            )
        seen = ctx.world.where_seen(item, _here(ctx)) if ctx.world is not None else None
        if seen is not None and distance_m(_here(ctx), seen) > 8:
            await _do(ctx, "move_to", {"target": {"pos": list(seen)}, "arrive_radius": 4.0, "run": True}, 90)
            if ctx.world is not None and _nearest(ctx, "pickable") is None:
                ctx.world.forget_sighting(item, seen)
            continue
        if explored >= EXPLORE_LEGS:
            return SkillOutcome(
                False,
                "not_found",
                tr(f"주변에서 {josa(item, '을를')} 못 찾겠어", f"I can't find any {item} around here"),
            )
        explored += 1
        here = _here(ctx)
        angle = explored * 2.4
        point = [
            here[0] + EXPLORE_LEG_M * math.cos(angle),
            here[1],
            here[2] + EXPLORE_LEG_M * math.sin(angle),
        ]
        await _do(ctx, "move_to", {"target": {"pos": point}, "arrive_radius": 3.0, "run": True}, timeout=60)


async def _what_it_gives(ctx: SkillContext, name: str) -> str | SkillOutcome:
    """`name` may be a thing to pick rather than an item ("라즈베리 덤불에서 따 와"). Then gather what
    it gives: known from before, or learned by picking one now, like a player trying a bush the first time."""
    await _wait_scene(ctx)
    sources = [e for e in ctx.session.nearby("pickable") if e.get("name") == name]
    if not sources or held(ctx, name) > 0:
        return name
    if ctx.world is not None and (known := ctx.world.yields("pickable", name)):
        return known[0]
    before = _held(ctx)
    failed = await _pick(ctx, min(sources, key=lambda e: e["distance"]))
    if failed is not None:
        return SkillOutcome(
            False,
            "could_not_pick",
            tr(f"{josa(name, '을를')} 못 땄어: {failed}", f"Couldn't pick {name}: {failed}"),
        )
    gained = [item for item, count in _held(ctx).items() if count > before.get(item, 0)]
    if not gained:
        return SkillOutcome(
            False,
            "nothing_from_source",
            tr(
                f"{josa(name, '을를')} 따 봤는데 아무것도 안 나와",
                f"Tried picking {name}, but nothing came of it",
            ),
        )
    ctx.goal.progress["from"] = name
    return gained[0]


def _in_sight(ctx: SkillContext, asked: str, item: str) -> int:
    """How many of `item` the things in view would give: one per bush that gives it, plus what lies around."""
    world = ctx.world

    def gives(entity: dict[str, Any]) -> bool:
        name = str(entity.get("name") or "")
        known = world.yields("pickable", name) if world is not None else []
        return name == asked or item in known or _named_like(item, name)

    picks = sum(1 for e in ctx.session.nearby("pickable") if gives(e))
    lying = sum(int(e.get("stack", 1)) for e in ctx.session.nearby("item") if e.get("name") == item)
    return picks + lying


def _pickable_source(ctx: SkillContext, item: str, tried: set[str]) -> dict[str, Any] | None:
    """The nearest thing to pick that gives `item`: known to give it, named like it, or never tried yet."""
    pickables = [e for e in ctx.session.nearby("pickable") if e["id"] not in tried and e.get("name")]
    world = ctx.world

    def rank(entity: dict[str, Any]) -> int | None:
        name = str(entity["name"])
        known = world.yields("pickable", name) if world is not None else []
        if item in known:
            return 0
        if _named_like(item, name):
            return 1
        if not known:
            return 2  # 아직 안 주워 본 것: 주워 보고 뭐가 나오는지 배운다
        return None

    ranked = [(r, e["distance"], e) for e in pickables if (r := rank(e)) is not None]
    return min(ranked, key=lambda t: (t[0], t[1]))[2] if ranked else None


def _creature_source(ctx: SkillContext, item: str) -> str | None:
    if ctx.world is None:
        return None
    return next((source for kind, source in ctx.world.sources(item) if kind == "creature"), None)


async def _pick(ctx: SkillContext, entity: dict[str, Any]) -> str | None:
    """Walk to a pickable and pick it. None when something came into the inventory, else why not."""
    moved = await _do(ctx, "move_to", {"target": {"id": entity["id"]}, "arrive_radius": 1.5}, timeout=60)
    if moved.code != "arrived":
        return tr(f"가까이 못 갔어({moved.code})", f"couldn't get close ({moved.code})")
    before = _held(ctx)
    result = await _do(ctx, "interact", {"id": entity["id"]})
    if result.status != "succeeded":
        return tr(f"손이 안 닿았어({result.code})", f"couldn't reach it ({result.code})")
    # 덤불에서 튕겨 나온 아이템은 자동 줍기로 들어온다. 인벤토리가 늘 때까지 잠깐 본다.
    try:
        await ctx.session.wait_for(lambda: _held(ctx) != before, PICK_SETTLE_S)
    except TimeoutError:
        # 긴 것(나뭇가지)은 가운데에 떨어뜨려 자동 줍기 거리(2m) 밖일 수 있다(실게임, 새 월드).
        # 사람처럼 떨어진 것을 보고 걸어가서 줍는다.
        await _wait_scene(ctx)
        dropped = [e for e in ctx.session.nearby("item") if distance_m(e["pos"], entity["pos"]) < DROP_NEAR_M]
        for item in sorted(dropped, key=lambda e: float(e["distance"])):
            moved = await _do(
                ctx, "move_to", {"target": {"id": item["id"]}, "arrive_radius": 1.2}, timeout=30
            )
            if moved.code == "arrived":
                await _do(ctx, "pickup", {"id": item["id"]})
        # 몸은 인벤토리가 는 것을 보고 성공을 알린다. 두뇌의 인벤토리는 다음 상태 갱신에 따라온다.
        with contextlib.suppress(TimeoutError):
            await ctx.session.wait_for(lambda: _held(ctx) != before, PICK_SETTLE_S)
        if _held(ctx) == before:
            log.info("picked %s but nothing came in (dropped nearby: %d)", entity.get("name"), len(dropped))
            return tr("땄는데 아무것도 안 들어왔어", "picked it, but nothing came in")
    gained = [name for name, count in _held(ctx).items() if count > before.get(name, 0)]
    if ctx.world is not None:
        for name in gained:
            learned = ctx.world.learn_source(name, "pickable", str(entity["name"]))
            # 민들레를 따서 민들레가 나온 것은 깨달음이 아니다(실게임: "So Dandelion gives Dandelion.").
            if learned and ctx.mind is not None and name != entity["name"]:
                ctx.mind.learned(
                    tr(
                        f"{entity['name']}에서 {josa(name, '이가')} 나오네.",
                        f"So {entity['name']} gives {name}.",
                    ),
                    f"source:{name}",
                )
    return None


# --- crafting -----------------------------------------------------------------------------------
async def craft(ctx: SkillContext) -> SkillOutcome:
    """Make `count` of `item`. Missing materials are gathered first; a station the recipe needs is
    approached (and built if it can be). A station's own refusal (no roof) is reported as the game said."""
    item, count = str(ctx.goal.args["item"]), int(ctx.goal.args.get("count", 1))
    progress = ctx.goal.progress
    start = progress.setdefault("held_at_start", held(ctx, item))
    for _attempt in range(6):
        await _wait_scene(ctx)
        made = held(ctx, item) - start
        if made >= count:
            return SkillOutcome(True, "done", tr(f"{josa(item, '을를')} 만들었어", f"Made {item}"))
        recipe = next((r for r in await menu(ctx, "recipes") if r["name"] == item), None)
        if recipe is None:
            return SkillOutcome(
                False,
                "recipe_unknown",
                tr(f"{josa(item, '은는')} 아직 만드는 법을 몰라", f"I don't know how to make {item} yet"),
            )
        batches = math.ceil((count - made) / max(1, int(recipe["amount"])))
        for resource in recipe["resources"]:
            need = int(resource["amount"]) * batches - held(ctx, resource["name"])
            if need > 0:
                got = await run_child(
                    ctx,
                    f"gather:{resource['name']}",
                    "gather",
                    {"item": resource["name"], "count": need},
                    gather,
                )
                if not got.ok:
                    return SkillOutcome(
                        False,
                        "missing_materials",
                        tr(
                            f"{item} 만들 {josa(resource['name'], '이가')} 모자라. {got.detail_ko}",
                            f"Not enough {resource['name']} to make {item}. {got.detail_ko}",
                        ),
                    )
        station_id = None
        if recipe["station"]:
            station = await _reach_station(ctx, str(recipe["station"]))
            if isinstance(station, SkillOutcome):
                return station
            station_id = station
        args: dict[str, Any] = {"item": item, "count": batches}
        if station_id is not None:
            args["station_id"] = station_id
        since = len(ctx.session.events_of("game_message"))
        result = await _do(ctx, "craft", args, timeout=20 + 4 * batches)
        if result.code == "station_unusable":
            reason = _game_says_since(ctx, since)
            return SkillOutcome(
                False,
                "station_unusable",
                tr(
                    f"{josa(str(recipe['station']), '을를')} 쓸 수가 없어."
                    + (f" '{reason}'래." if reason else ""),
                    f"I can't use the {recipe['station']}." + (f" It says '{reason}'." if reason else ""),
                ),
            )
        if result.code == "out_of_reach" and station_id is not None:
            continue
        if result.status != "succeeded" and result.code != "missing_requirements":
            return SkillOutcome(
                False,
                result.code,
                tr(
                    f"{josa(item, '을를')} 못 만들었어 ({result.code})",
                    f"Couldn't make {item} ({result.code})",
                ),
            )
    return SkillOutcome(
        False,
        "gave_up",
        tr(f"{josa(item, '을를')} 몇 번 해 봐도 못 만들겠어", f"Tried a few times, but I can't make {item}"),
    )


def _game_says_since(ctx: SkillContext, since: int) -> str | None:
    """The game's last message after the `since`-th one: why the thing just tried was refused. Older messages
    (a skill-up, an earlier refusal) are not the reason."""
    messages = ctx.session.events_of("game_message")[since:]
    return str(messages[-1].data.get("text")) if messages else None


async def _reach_station(ctx: SkillContext, name: str) -> str | SkillOutcome:
    """Walk to a station called `name` (seen now or remembered); build one if none is known and it can be."""
    station = _nearest(ctx, "station", {name})
    if station is None and ctx.world is not None and (place := ctx.world.place(name)) is not None:
        await _do(
            ctx, "move_to", {"target": {"pos": list(place.pos)}, "arrive_radius": 3.0, "run": True}, 120
        )
        await _wait_scene(ctx)
        station = _nearest(ctx, "station", {name})
    if station is None:
        built = await run_child(ctx, f"build:{name}", "build", {"piece": name}, build)
        if not built.ok:
            return SkillOutcome(
                False,
                "no_station",
                tr(
                    f"{josa(name, '이가')} 있어야 만들 수 있어. {built.detail_ko}",
                    f"I can't make it without the {name}. {built.detail_ko}",
                ),
            )
        await _wait_scene(ctx)
        station = _nearest(ctx, "station", {name})
        if station is None:
            return SkillOutcome(
                False,
                "no_station",
                tr(f"{josa(name, '을를')} 지었는데 안 보여", f"I built the {name}, but I can't see it"),
            )
    # 제작대는 몸통 중심(루트)에서 2m 안이어야 쓸 수 있다. 표면 기준 도착이 아니라 가운데로 다가간다.
    middle = station.get("center", station["pos"])
    await _do(ctx, "move_to", {"target": {"pos": middle}, "arrive_radius": STATION_USE_M}, 60)
    station_id: str = station["id"]
    return station_id


# --- building -----------------------------------------------------------------------------------
async def build(ctx: SkillContext) -> SkillOutcome:
    """Put one hammer piece (`piece`) down near the leader (or here): get a hammer and the materials if
    needed, then try spots around until the game accepts one."""
    name = str(ctx.goal.args["piece"])
    pieces = await menu(ctx, "pieces")
    if not pieces:
        hammer = await _get_build_tool(ctx)
        if isinstance(hammer, SkillOutcome):
            return hammer
        pieces = await menu(ctx, "pieces")
    piece = next((p for p in pieces if p["name"] == name), None)
    if piece is None:
        return SkillOutcome(
            False,
            "piece_unknown",
            tr(f"{josa(name, '은는')} 아직 지을 줄 몰라", f"I don't know how to build {name} yet"),
        )
    for resource in piece["resources"]:
        need = int(resource["amount"]) - held(ctx, resource["name"])
        if need > 0:
            got = await run_child(
                ctx, f"gather:{resource['name']}", "gather", {"item": resource["name"], "count": need}, gather
            )
            if not got.ok:
                return SkillOutcome(
                    False,
                    "missing_materials",
                    tr(
                        f"{name} 지을 재료가 모자라. {got.detail_ko}",
                        f"Not enough materials for the {name}. {got.detail_ko}",
                    ),
                )
    if piece["station"] and _nearest(ctx, "station", {piece["station"]}) is None:
        station = await run_child(
            ctx, f"build:{piece['station']}", "build", {"piece": piece["station"]}, build
        )
        if not station.ok:
            return SkillOutcome(
                False,
                "no_station",
                tr(
                    f"{josa(name, '은는')} {piece['station']} 근처에서만 지을 수 있어",
                    f"I can only build the {name} near the {piece['station']}",
                ),
            )
    await _do(ctx, "equip", {"item": piece["tool"]})
    within = ctx.goal.args.get("within_m")
    tries: list[dict[str, Any]] = []
    for spot, angle in _spots(ctx):
        await _do(ctx, "move_to", {"target": {"pos": spot}, "arrive_radius": PLACE_FROM_M}, timeout=30)
        args: dict[str, Any] = {"piece": name, "pos": spot, "yaw": angle}
        if within is not None:
            args["within_m"] = float(within)
        result = await _do(ctx, "place", args, timeout=20)
        if result.code == "placed":
            # 작업대·모닥불·침대 같은 곳은 다음 장면에서 세계 기억이 자리째 기억한다.
            built = {
                "id": result.evidence.get("id"),
                "pos": result.evidence.get("pos"),
                "place": result.evidence,
            }
            return SkillOutcome(
                True, "placed", tr(f"{josa(name, '을를')} 지었어", f"Built the {name}"), built
            )
        if result.code == "missing_requirements":
            return SkillOutcome(
                False,
                "missing_requirements",
                tr(
                    f"{name} 짓기에 뭔가 모자라 ({result.evidence})",
                    f"Something's missing to build the {name} ({result.evidence})",
                ),
            )
        if result.code in ("no_build_tool", "piece_not_known", "piece_not_in_menu"):
            return SkillOutcome(
                False,
                result.code,
                tr(
                    f"{josa(name, '을를')} 지을 수가 없어 ({result.code})",
                    f"I can't build the {name} ({result.code})",
                ),
            )
        tries.append({"spot": spot, "code": result.code, **result.evidence})
        await asyncio.sleep(0)
    return SkillOutcome(
        False,
        "no_spot",
        tr(f"{josa(name, '을를')} 놓을 만한 자리를 못 찾았어", f"Couldn't find a good spot for the {name}"),
        {"tries": tries},
    )


def _spots(ctx: SkillContext) -> list[tuple[list[float], float]]:
    """Where to try putting a piece: exactly `at` first if given (a cooking rack goes right over its fire),
    then rings around the anchor (the leader when asked to build near them, else here). With `within_m`
    only `at` itself."""
    spots: list[tuple[list[float], float]] = []
    radii: tuple[float, ...]
    at = ctx.goal.args.get("at")
    if at is not None:
        spots.append((list(at), 0.0))
        # within_m가 있으면 그 자리여야만 한다(불 위 요리대). 둘레는 소용없다.
        anchor, radii = list(at), (() if ctx.goal.args.get("within_m") is not None else (0.5,))
    else:
        anchor, radii = _anchor(ctx), SPOT_RADII
    for radius in radii:
        for angle in SPOT_ANGLES:
            point = [
                anchor[0] + radius * math.sin(math.radians(angle)),
                anchor[1],
                anchor[2] + radius * math.cos(math.radians(angle)),
            ]
            spots.append((point, float(angle)))
    return spots


def _site_searches(anchor: list[float]) -> list[tuple[list[float], float]]:
    """Where to look for a building site, nearest first: around the anchor, then rings farther out."""
    searches: list[tuple[list[float], float]] = [(anchor, radius) for radius in SITE_RADII]
    for angle in range(0, 360, 45):
        far = [
            anchor[0] + SITE_FAR_M * math.sin(math.radians(angle)),
            anchor[1],
            anchor[2] + SITE_FAR_M * math.cos(math.radians(angle)),
        ]
        searches.append((far, SITE_RADII[0]))
    return searches


def _anchor(ctx: SkillContext) -> list[float]:
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    if ctx.goal.args.get("near") == "leader" and leader is not None:
        pos: list[float] = leader["pos"]
        return pos
    return _here(ctx)


async def _get_build_tool(ctx: SkillContext) -> SkillOutcome | None:
    """No build menu means no hammer. Make one if the crafting menu offers a hand-made tool."""
    tools = [r for r in await menu(ctx, "recipes") if r["type"] == "Tool" and r["station"] is None]
    for tool in tools:
        made = await run_child(ctx, f"craft:{tool['name']}", "craft", {"item": tool["name"]}, craft)
        if made.ok and await menu(ctx, "pieces"):
            return None
    return SkillOutcome(
        False,
        "no_build_tool",
        tr("지으려면 망치 같은 도구가 있어야 해", "I need a tool like a Hammer to build"),
    )


# --- a roof over the workbench ------------------------------------------------------------------
# 실게임에서 찾은 배치(2026-10-17, shelter 시나리오):
# - 작업대(폭 3m, 깊이 1.1m)를 방향 0으로 놓고, 뒤에 벽 둘(1m 뒤), 양옆에 벽 하나씩(2m 옆)을 세운다.
# - 앞에 서서 뒷벽 안쪽 면 윗부분을 겨눠 지붕 조각을 올리면 게임이 작업대를 쓰게 해 준다.
# - 바닥판은 "새는" 조각이라 지붕이 되지 않는다.
# - 벽은 그 바깥쪽에 서서 겨눠야 광선이 작업대에 먼저 맞지 않는다.
WALL_SPOTS = (
    (-1.0, 1.0, 0.0, -1.0, 4.0),
    (1.0, 1.0, 0.0, 1.0, 4.0),
    (-2.0, 0.0, 90.0, -5.0, 0.0),
    (2.0, 0.0, 90.0, 5.0, 0.0),
)
ROOF_SPOTS = (-1.0, 1.0)
PORCH_SPOTS = (-1.0, 1.0)
# 망치 메뉴의 이름으로 벽과 지붕을 알아본다(게임의 언어마다 이름이 다르다).
# 영어 "Wall"은 대소문자를 가린다: "Stakewall"(목책 담장)은 한국어에서도 "벽"이 아니다.
WALL_WORD: dict[lang.Language, str] = {"ko": "벽", "en": "Wall"}
ROOF_WORD: dict[lang.Language, str] = {"ko": "지붕", "en": "Roof"}
NOT_PLAIN_ROOF: dict[lang.Language, tuple[str, ...]] = {
    "ko": ("교차", "모서리", "용마루"),
    "en": ("Cross", "Corner", "Ridge"),
}


def _rotate(dx: float, dz: float, yaw: float) -> tuple[float, float]:
    r = math.radians(yaw)
    return dx * math.cos(r) + dz * math.sin(r), -dx * math.sin(r) + dz * math.cos(r)


def _wall_and_roof(pieces: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """The plain wall and a plain sloped roof in the hammer menu, by what the menu shows."""
    language = lang.current()
    plain = [p for p in pieces if [r["amount"] for r in p["resources"]] == [2]]
    wall = next((p["name"] for p in plain if WALL_WORD[language] in p["name"] and "°" not in p["name"]), None)
    roofs = [p["name"] for p in plain if ROOF_WORD[language] in p["name"] and "26°" in p["name"]]
    plain_roof = [n for n in roofs if not any(word in n for word in NOT_PLAIN_ROOF[language])]
    return wall, (plain_roof or roofs or [None])[0]


async def _station_opens(ctx: SkillContext, station_id: str, pos: list[float]) -> bool:
    """Open the station like a player does (it must be within 2 m of its middle); True if it opened."""
    await _do(ctx, "move_to", {"target": {"pos": pos}, "arrive_radius": STATION_USE_M}, timeout=30)
    opened = await _do(ctx, "interact", {"id": station_id})
    return bool(opened.evidence.get("opened"))


async def shelter(ctx: SkillContext) -> SkillOutcome:
    """Put walls and a roof over the workbench so it can be used (the game wants it covered)."""
    bench_name = str(ctx.goal.args.get("station", WORKBENCH[lang.current()]))
    bench = _nearest(ctx, "station", {bench_name})
    if bench is None:
        # 사람처럼 먼저 평평하고 트인 터(6x5m)를 고른다. 덤불·비탈에서는 벽이 밀리고 지붕이 작업대에 걸렸다.
        sites: list[dict[str, Any]] = []
        # 가까이에 없으면 사람처럼 조금 더 멀리까지 둘러본다(몸은 한 번에 40m까지 본다). 그래도 없으면
        # 둘레 40m 떨어진 곳들을 본다. 실게임(2026-10-19, 20): 시작 신전 둘레는 짓지 못하고 비탈과 숲이라
        # 40m 안에 터가 없어 리더에게 어디에 지을지 물었다.
        anchor = _anchor(ctx)
        for center, radius in _site_searches(anchor):
            answer = await ctx.session.query(
                "site", {"near": center, "width": 6, "depth": 5, "radius": radius}
            )
            sites = answer.data.get("sites", []) if answer.ok else []
            if sites:
                break
        if not sites:
            return SkillOutcome(
                False,
                "no_site",
                tr(
                    "근처에 집 지을 만한 평평한 땅이 안 보여",
                    "I don't see any flat ground nearby to build on",
                ),
            )
        site = list(sites[0]["pos"])
        ctx.goal.progress["site"] = sites[0]
        await _do(ctx, "move_to", {"target": {"pos": site}, "arrive_radius": 3.0}, timeout=60)
        made = await run_child(ctx, "build:bench", "build", {"piece": bench_name, "at": site}, build)
        if not made.ok:
            return made
        await _wait_scene(ctx)
        # 근처에 다른 작업대가 있을 수 있다. 방금 지은 것을 id로 찾는다.
        ctx.goal.progress["bench_build"] = made.evidence
        bench = next((e for e in ctx.session.nearby("station") if e["id"] == made.evidence.get("id")), None)
        if bench is None:
            return SkillOutcome(
                False,
                "no_station",
                tr(
                    f"{josa(bench_name, '을를')} 지었는데 안 보여",
                    f"I built the {bench_name}, but I can't see it",
                ),
            )
    if await _station_opens(ctx, bench["id"], bench.get("center", bench["pos"])):
        return SkillOutcome(
            True,
            "already_usable",
            tr(f"{josa(bench_name, '은는')} 이미 쓸 수 있어", f"I can already use the {bench_name}"),
        )
    wall, roof = _wall_and_roof(await menu(ctx, "pieces"))
    if wall is None or roof is None:
        return SkillOutcome(
            False,
            "pieces_unknown",
            tr("벽이나 지붕을 지을 줄 몰라", "I don't know how to build walls or a roof"),
        )
    need = 2 * (len(WALL_SPOTS) + len(ROOF_SPOTS) + len(PORCH_SPOTS))
    wood = WOOD[lang.current()]
    if held(ctx, wood) < need:
        got = await run_child(
            ctx, "gather:wood", "gather", {"item": wood, "count": need - held(ctx, wood)}, gather
        )
        if not got.ok:
            return SkillOutcome(
                False,
                "missing_materials",
                tr(
                    f"벽이랑 지붕에 나무가 모자라. {got.detail_ko}",
                    f"Not enough Wood for the walls and roof. {got.detail_ko}",
                ),
            )
    x, y, z = bench.get("center", bench["pos"])
    yaw = float(bench.get("yaw", 0.0))
    tool = next((p["tool"] for p in await menu(ctx, "pieces") if p["name"] == wall), None)
    if tool is not None:
        await _do(ctx, "equip", {"item": tool})

    def at(dx: float, dz: float, dy: float = 0.0) -> list[float]:
        rx, rz = _rotate(dx, dz, yaw)
        return [x + rx, y + dy, z + rz]

    log: list[dict[str, Any]] = []

    async def place(piece: str, aim: list[float], piece_yaw: float, exact: bool = False) -> dict[str, Any]:
        args = {"piece": piece, "pos": aim, "yaw": piece_yaw, "exact": exact}
        placed = await _do(ctx, "place", args, timeout=20)
        entry = {"piece": piece, "aim": [round(v, 2) for v in aim], "code": placed.code, **placed.evidence}
        log.append(entry)
        return entry

    walls: list[list[float]] = []
    for dx, dz, wall_yaw, sx, sz in WALL_SPOTS:
        await _do(ctx, "move_to", {"target": {"pos": at(sx, sz)}, "arrive_radius": 0.8}, timeout=30)
        placed = await place(wall, at(dx, dz), yaw + wall_yaw)
        if placed["code"] == "placed" and dz > 0.5:
            walls.append(list(placed["pos"]))
    if not walls:
        return SkillOutcome(
            False,
            "no_walls",
            tr("작업대 뒤에 벽을 못 세웠어", "I couldn't put up walls behind the Workbench"),
            {"bench": bench, "log": log},
        )
    top = min(w[1] for w in walls) + 1.0
    await _do(ctx, "move_to", {"target": {"pos": at(0.0, -3.0)}, "arrive_radius": 0.8}, timeout=30)
    for back in walls:
        # 실제로 선 뒷벽(두께 0.3m)의 안쪽 면 윗부분을 겨누면 게임이 지붕을 안쪽으로 붙인다.
        inward = [x - back[0], 0.0, z - back[2]]
        length = math.hypot(inward[0], inward[2]) or 1.0
        aim = [back[0] + inward[0] / length * 0.16, back[1] + 0.75, back[2] + inward[2] / length * 0.16]
        await place(roof, aim, yaw, exact=True)
    if not await _station_opens(ctx, bench["id"], [x, y, z]):
        await _do(ctx, "move_to", {"target": {"pos": at(0.0, -5.0)}, "arrive_radius": 0.8}, timeout=30)
        for dx in PORCH_SPOTS:
            aim = at(dx, -1.0)
            aim[1] = top + 0.3
            await place(roof, aim, yaw, exact=True)
        since = len(ctx.session.events_of("game_message"))
        if not await _station_opens(ctx, bench["id"], [x, y, z]):
            said = _game_says_since(ctx, since)
            return SkillOutcome(
                False,
                "still_exposed",
                tr(
                    "벽이랑 지붕을 올렸는데 아직 못 써." + (f" '{said}'래." if said else ""),
                    "I put up walls and a roof, but I still can't use it."
                    + (f" It says '{said}'." if said else ""),
                ),
                {
                    "bench": bench,
                    "site": ctx.goal.progress.get("site"),
                    "bench_build": ctx.goal.progress.get("bench_build"),
                    "log": log,
                },
            )
    return SkillOutcome(
        True,
        "sheltered",
        tr(
            f"{bench_name}에 벽이랑 지붕을 올렸어. 이제 쓸 수 있어!",
            f"Put walls and a roof over the {bench_name}. I can use it now!",
        ),
        {"log": log},
    )


SKILLS: dict[str, Skill] = {"gather": gather, "craft": craft, "build": build, "shelter": shelter}
