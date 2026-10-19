"""Skills: coroutines that compose body commands into a goal (no model calls here).

Progress is always read from the world (inventory, target health, scene), never from swing counts, so a
skill cancelled mid-way (preempted by a fight) resumes correctly when restarted with the same Goal.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from thorkell.body.protocol import Result
from thorkell.body.session import BodySession, CommandRejected
from thorkell.control.goals import Goal
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.mind.speech import Line
from thorkell.world.where import distance_m, where_ko

if TYPE_CHECKING:
    from thorkell.mind.mind import Mind
    from thorkell.plan.planner import Planner
    from thorkell.plan.tactics import Tactician
    from thorkell.world.memory import WorldMemory
    from thorkell.world.sight import Eyes

WEAPON_TYPES = ("OneHandedWeapon", "TwoHandedWeapon", "Tool", "TwoHandedWeaponLeft")
# 건네받기: 리더 발밑(이 거리 안)에 놓인 아이템을, 한 번에 이 개수까지만 줍는다.
HANDOVER_RADIUS = 4.0
HANDOVER_LIMIT = 5
# 멀리 있는 리더(지도 위치)를 따라갈 때: 한 번에 이만큼 가서 다시 본다(그동안 리더도 움직인다).
# 한 구간에 이만큼도 못 다가가는 일이 연달아 이 횟수면 길이 막힌 것으로 보고 알린다.
FAR_LEG_M = 60.0
FAR_MIN_GAIN_M = 5.0
FAR_STALLS = 3
# 리더가 이만큼(초) 전까지 보였고 포털 이만큼(m) 앞에서 사라졌으면 포털로 간 것이다.
LEADER_VANISHED_S = 15.0
PORTAL_NEAR_M = 6.0
LEADER_HIDDEN_KO = "네가 안 보여. 지도에서 위치 공개를 켜 주면 찾아갈게."
LEADER_HIDDEN_EN = "I can't see you. Turn on position sharing on the map and I'll come find you."
# 방어하던 상대가 이만큼 연달아 장면에 없으면 안 보이게 된 것이다(장면은 초당 두 번).
UNSEEN_SCENES = 4
TOOL_DAMAGE = ("chop", "pickaxe")
# 나무를 하다 다가가지 못한 것은 이만큼 막히면 두고 다른 것을 찾는다.
BLOCKED_TRIES = 2
# 배운 것이 피해 기대치에 주는 배율. 들은 것(가설)은 직접 본 것보다 약하게 반영한다.
KNOWLEDGE_MULTIPLIER = {
    ("weak_to", "verified"): 1.5,
    ("weak_to", "supported"): 1.5,
    ("weak_to", "hypothesis"): 1.25,
    ("resists", "verified"): 0.5,
    ("resists", "supported"): 0.5,
    ("resists", "hypothesis"): 0.75,
    ("immune_to", "verified"): 0.0,
    ("immune_to", "supported"): 0.0,
    ("immune_to", "hypothesis"): 0.5,
}


@dataclass(frozen=True)
class SkillOutcome:
    ok: bool
    code: str
    detail_ko: str
    # 진단용 기록(어느 단계가 어떻게 끝났는지). 말로 하지 않고 끝난 목표에 남긴다.
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillContext:
    session: BodySession
    goal: Goal
    memory: dict[str, Any] = field(default_factory=dict)
    planner: Planner | None = None
    speak: Callable[[str], Awaitable[None]] | None = None
    mind: Mind | None = None
    world: WorldMemory | None = None
    tactician: Tactician | None = None
    eyes: Eyes | None = None

    def child(self, goal: Goal) -> SkillContext:
        return SkillContext(
            self.session,
            goal,
            self.memory,
            self.planner,
            self.speak,
            self.mind,
            self.world,
            self.tactician,
            self.eyes,
        )

    @property
    def wood_names(self) -> set[str]:
        names: set[str] = self.memory.setdefault("wood_names", set())
        return names


def _distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def _toward(here: list[float], there: list[float], at_most: float) -> list[float]:
    distance = _distance(here, there)
    if distance <= at_most:
        return list(there)
    share = at_most / distance
    return [here[0] + (there[0] - here[0]) * share, here[1], here[2] + (there[2] - here[2]) * share]


# 두뇌는 몸이 자기 시간 제한(예: move_to timeout_s)으로 결과를 보낼 때까지 조금 더 기다린다.
# 같은 시간에 끊으면 결과 대신 TimeoutError가 나서 스킬이 통째로 멈췄다(실게임 far_follow).
RESULT_GRACE_S = 10.0


async def _do(ctx: SkillContext, op: str, args: dict[str, Any], timeout: float = 30) -> Result:
    return await ctx.session.command(op, args, timeout=timeout + RESULT_GRACE_S)


def _weapons(ctx: SkillContext) -> list[dict[str, Any]]:
    return [i for i in ctx.session.inventory() if i.get("type") in WEAPON_TYPES and not broken(i)]


def broken(item: dict[str, Any]) -> bool:
    """Worn down to nothing: the game shows it red and will not let you hold it (durability 0)."""
    return "durability" in item and float(item["durability"]) <= 0


def _broken_chopper(ctx: SkillContext) -> dict[str, Any] | None:
    return next(
        (
            i
            for i in ctx.session.inventory()
            if i.get("type") in WEAPON_TYPES and broken(i) and float(i.get("damage", {}).get("chop", 0)) > 0
        ),
        None,
    )


def combat_score(ctx: SkillContext, weapon: dict[str, Any], target: str | None) -> float:
    """Expected damage per swing as a first-time player would judge it: the tooltip numbers,
    adjusted by what he has learned (or been told) about this creature."""
    multipliers: dict[str, float] = {}
    if ctx.mind is not None and target:
        for fact in ctx.mind.store.facts_about(target):
            factor = KNOWLEDGE_MULTIPLIER.get((fact.predicate, fact.status))
            if factor is not None:
                multipliers[fact.object] = factor
    damage = weapon.get("damage", {})
    return sum(float(v) * multipliers.get(k, 1.0) for k, v in damage.items() if k not in TOOL_DAMAGE)


async def _equip(ctx: SkillContext, item: dict[str, Any] | None) -> dict[str, Any] | None:
    if item is not None and not item.get("equipped"):
        await _do(ctx, "equip", {"item": item["name"]})
    return item


def can_chop(ctx: SkillContext) -> bool:
    return any(float(w.get("damage", {}).get("chop", 0)) > 0 for w in _weapons(ctx))


async def equip_for_chopping(ctx: SkillContext) -> dict[str, Any] | None:
    tools = [w for w in _weapons(ctx) if float(w.get("damage", {}).get("chop", 0)) > 0]
    return await _equip(ctx, max(tools, key=lambda w: float(w["damage"]["chop"])) if tools else None)


async def equip_for_fight(ctx: SkillContext, target: str | None) -> dict[str, Any] | None:
    weapons = _weapons(ctx)
    if not weapons:
        return None
    best = max(weapons, key=lambda w: combat_score(ctx, w, target))
    if not best.get("equipped") and any(w.get("equipped") for w in weapons) and ctx.mind is not None:
        ctx.mind.speech.offer(
            Line(
                tr(f"{josa(best['name'], '으로')} 바꿔 볼게!", f"Switching to the {best['name']}!"),
                1,
                "whisper",
                f"switch:{best['name']}",
                10,
            )
        )
    return await _equip(ctx, best)


async def _attack(
    ctx: SkillContext,
    entity: dict[str, Any],
    swings: int,
    weapon: dict[str, Any] | None,
    timeout: float = 30,
    sneak: bool = False,
) -> Result:
    """Swing at an entity. `weapon` is what the skill just equipped: the scene (2 Hz) can still show the
    previous item, and attributing hits to the wrong weapon would teach the wrong weakness."""
    if ctx.mind is not None:
        ctx.mind.attacking(str(entity.get("name") or ""), str(entity.get("kind")), weapon)
    try:
        args = {"id": entity["id"], "swings": swings, **({"sneak": True} if sneak else {})}
        return await _do(ctx, "attack", args, timeout=timeout)
    finally:
        if ctx.mind is not None:
            # 마지막 타격의 피해 텍스트가 조금 늦게 도착할 수 있다.
            await asyncio.sleep(0.2)
            ctx.mind.attack_done()


def _nearest(
    ctx: SkillContext, kind: str, names: set[str] | None = None, skip: Collection[str] = ()
) -> dict[str, Any] | None:
    candidates = [
        e
        for e in ctx.session.nearby(kind)
        if (names is None or e.get("name") in names) and e["id"] not in skip
    ]
    return min(candidates, key=lambda e: e["distance"]) if candidates else None


async def _approach(ctx: SkillContext, entity: dict[str, Any], radius: float) -> bool:
    result = await _do(ctx, "move_to", {"target": {"id": entity["id"]}, "arrive_radius": radius}, timeout=60)
    return result.status == "succeeded"


async def _wait_scene(ctx: SkillContext) -> None:
    seq = ctx.session.scene.seq if ctx.session.scene else -1
    await ctx.session.wait_for(
        lambda: ctx.session.scene is not None and ctx.session.scene.seq > seq, timeout=5
    )


def _held(ctx: SkillContext) -> dict[str, int]:
    totals: dict[str, int] = {}
    for item in ctx.session.inventory():
        totals[item["name"]] = totals.get(item["name"], 0) + int(item.get("stack", 0))
    return totals


async def gather_wood(ctx: SkillContext) -> SkillOutcome:
    """Progress = wood in the inventory minus what was held when the goal began. Pickup results alone miss
    the game's auto-pickup (anything within ~2 m is picked up while walking or chopping)."""
    target = int(ctx.goal.args["count"])
    progress = ctx.goal.progress
    progress.setdefault("gathered", 0)
    held_at_start: dict[str, int] = progress.setdefault("held_at_start", _held(ctx))
    explored = 0
    started, start_count = time.monotonic(), progress["gathered"]
    # 다가가다 막힌 횟수(바위 틈의 통나무 등). 사람은 두어 번 막히면 다른 나무로 간다.
    # 실게임(2026-10-19): 닿지 않는 통나무 하나로 10분 동안 다가가기만 했다.
    blocked: dict[str, int] = progress.setdefault("blocked", {})

    def given_up() -> set[str]:
        return {target_id for target_id, tries in blocked.items() if tries >= BLOCKED_TRIES}

    def measure() -> None:
        held = _held(ctx)
        gathered = sum(max(0, held.get(name, 0) - held_at_start.get(name, 0)) for name in ctx.wood_names)
        progress["gathered"] = max(progress["gathered"], gathered)
        minutes = (time.monotonic() - started) / 60.0
        if progress["gathered"] > start_count and minutes > 0.05:
            rate = (progress["gathered"] - start_count) / minutes
            previous = ctx.memory.get("wood_rate_per_min")
            ctx.memory["wood_rate_per_min"] = rate if previous is None else 0.7 * previous + 0.3 * rate

    while True:
        await _wait_scene(ctx)
        measure()
        if progress["gathered"] >= target:
            break
        drop = _nearest(ctx, "item", ctx.wood_names, given_up()) if ctx.wood_names else None
        if drop is not None:
            approach = await _do(
                ctx, "move_to", {"target": {"id": drop["id"]}, "arrive_radius": 1.2}, timeout=60
            )
            if approach.code == "arrived":
                await _do(ctx, "pickup", {"id": drop["id"]})
            elif approach.status == "failed":
                blocked[drop["id"]] = blocked.get(drop["id"], 0) + 1
            continue

        tool = await equip_for_chopping(ctx)
        if tool is None:
            worn = _broken_chopper(ctx)
            if worn is not None:
                # 실게임(2026-10-19): 나무를 하다 돌도끼가 닳아 부러졌는데, 모르고 6초마다 다시 들려고 했다.
                return SkillOutcome(
                    False,
                    "tool_broken",
                    tr(f"{josa(worn['name'], '이가')} 부러졌어", f"My {worn['name']} broke"),
                    {"gathered": progress["gathered"]},
                )
            return SkillOutcome(
                False, "no_tool", tr("나무를 벨 도구가 없어", "I've got nothing to chop trees with")
            )
        # 이 도끼로 안 베어지는 종류(이름표)는 사람처럼 한 번 겪으면 건너뛴다.
        hard: set[str] = ctx.memory.setdefault("too_hard", set())
        skip = given_up() | {
            e["id"] for e in ctx.session.nearby() if f"{tool['name']}|{e.get('name') or ''}" in hard
        }
        log = _nearest(ctx, "log", skip=skip)
        tree = _nearest(ctx, "tree", skip=skip)
        target_entity = log or tree
        if target_entity is None:
            if explored >= 3:
                return SkillOutcome(
                    False,
                    "no_trees",
                    tr("주변에 벨 나무가 안 보여", "I don't see any trees to chop around here"),
                )
            explored += 1
            assert ctx.session.state is not None
            here = ctx.session.state.data["pos"]
            angle = explored * 2.1
            point = [here[0] + 20 * math.cos(angle), here[1], here[2] + 20 * math.sin(angle)]
            await _do(ctx, "move_to", {"target": {"pos": point}, "arrive_radius": 2.0}, timeout=60)
            continue

        if not await _approach(ctx, target_entity, 1.6):
            blocked[target_entity["id"]] = blocked.get(target_entity["id"], 0) + 1
            continue
        before_items = {e["id"] for e in ctx.session.nearby("item")}
        held_before = _held(ctx)
        try:
            dealt = len(ctx.session.events_of("damage_dealt"))
            result = await _attack(ctx, target_entity, 5, tool)
        except CommandRejected as error:
            return SkillOutcome(
                False, error.code, tr("몸이 공격 명령을 거절했어", "My body refused to attack")
            )
        landed = [
            e.data.get("type")
            for e in ctx.session.events_of("damage_dealt")[dealt:]
            if e.data.get("on_target")
        ]
        if landed and all(kind == "too_hard" for kind in landed):
            # 실게임(2026-10-19): 돌도끼로 안 베어지는 나무를 85번 쳐서 도끼 둘이 닳아 부러졌다.
            # 사람은 "너무 단단함"이 뜨면 다른 나무로 간다.
            blocked[target_entity["id"]] = BLOCKED_TRIES
            if target_entity.get("name"):
                hard.add(f"{tool['name']}|{target_entity['name']}")
            continue
        if result.code == "out_of_reach":
            continue
        if result.status == "failed" and result.code == "cannot_attack":
            await _do(ctx, "wait", {"seconds": 3.0})
            continue
        if result.evidence.get("destroyed"):
            if target_entity["kind"] == "tree":
                # 쓰러지는 나무에 깔리지 않게 물러섰다가 다가간다.
                await _do(ctx, "wait", {"seconds": 2.0})
                continue
            await asyncio.sleep(0.3)
            await _wait_scene(ctx)
            # 통나무가 남긴 것: 근처에 새로 떨어진 아이템, 그리고 자동 줍기로 이미 인벤토리에 들어온 아이템.
            new = [
                e
                for e in ctx.session.nearby("item")
                if e["id"] not in before_items and _distance(e["pos"], target_entity["pos"]) < 4
            ]
            ctx.wood_names.update(e["name"] for e in new)
            held = _held(ctx)
            ctx.wood_names.update(name for name, count in held.items() if count > held_before.get(name, 0))
    gathered = progress["gathered"]
    return SkillOutcome(True, "done", tr(f"나무 {gathered}개 모았어", f"Got {gathered} Wood"))


async def defend(ctx: SkillContext) -> SkillOutcome:
    """Brain-level fight loop. Frame-rate blocking/dodging belongs to the body's reflexes; this keeps the
    target in reach, swings, and re-picks the weapon as it learns what works on this creature."""
    attacker_id = ctx.goal.args["attacker_id"]
    name = str(ctx.goal.args.get("name") or tr("적", "the enemy"))
    deaths_before = len(ctx.session.events_of("creature_died"))
    unseen = 0
    while True:
        if any(
            e.data.get("id") == attacker_id for e in ctx.session.events_of("creature_died")[deaths_before:]
        ):
            return SkillOutcome(True, "killed", tr(f"{josa(name, '을를')} 해치웠어", f"Took down {name}"))
        enemy = next((e for e in ctx.session.nearby() if e["id"] == attacker_id), None)
        if enemy is None:
            # 안 보이는 것은 쓰러진 것이 아니다(달아났거나, 맞은 순간 장면에 아직 안 떴다).
            unseen += 1
            if unseen < UNSEEN_SCENES:
                await _wait_scene(ctx)
                continue
            return SkillOutcome(
                True,
                "threat_gone",
                tr(
                    f"{josa(name, '이가')} 안 보여. 일단 괜찮은 것 같아",
                    f"Can't see {name} anymore. I think we're okay for now",
                ),
            )
        unseen = 0
        state = ctx.session.state
        hurt = state is not None and state.data["hp"] / max(1.0, state.data["hp_max"]) < 0.3
        # 상대가 이미 많이 약해졌으면 끝까지 싸운다. 쫓아오는 적에게서 도망치다 맞는 게 더 위험하다.
        if hurt and float(enemy.get("health", 1.0)) >= 0.5:
            await _do(
                ctx,
                "move_to",
                {"target": {"id": ctx.goal.args.get("leader_id", "")}, "run": True},
                timeout=20,
            )
            return SkillOutcome(
                False, "retreated", tr("너무 다쳐서 물러났어", "I got hurt too badly, so I backed off")
            )
        weapon = await equip_for_fight(ctx, enemy.get("name"))
        result = await _attack(ctx, enemy, 1, weapon, timeout=10)
        if result.evidence.get("destroyed"):
            return SkillOutcome(True, "killed", tr(f"{josa(name, '을를')} 해치웠어", f"Took down {name}"))
        if result.code == "out_of_reach":
            await _do(
                ctx,
                "move_to",
                {"target": {"id": attacker_id}, "arrive_radius": 1.6, "timeout_s": 4},
                timeout=8,
            )
        elif result.code == "not_found":
            await _wait_scene(ctx)


async def follow(ctx: SkillContext) -> SkillOutcome:
    from thorkell.control.travel import go_through  # travel uses this module

    stalls = 0
    announced = False
    last_seen: tuple[float, list[float]] | None = None
    while True:
        await _wait_scene(ctx)
        assert ctx.session.scene is not None and ctx.session.state is not None
        leader = ctx.session.scene.data.get("leader")
        if leader is not None:
            last_seen = (time.monotonic(), list(leader["pos"]))
        elif last_seen is not None and time.monotonic() - last_seen[0] < LEADER_VANISHED_S:
            # 포털 앞에서 사라졌으면 포털로 간 것이다. 지도에 찍힌 먼 자리로 걸어가지 않고 따라 들어간다.
            portal = next(
                (
                    p
                    for p in ctx.session.nearby("portal")
                    if p.get("connected")
                    and distance_m(p.get("center") or p["pos"], last_seen[1]) <= PORTAL_NEAR_M
                ),
                None,
            )
            if portal is not None:
                if ctx.speak is not None:
                    await ctx.speak(
                        tr("포털로 갔구나, 따라갈게!", "You went through the portal, I'll follow!")
                    )
                last_seen = None
                went = await go_through(ctx, portal)
                if not went.ok:
                    return went
                continue
        if leader is None:
            # 멀면 리더 캐릭터가 로드되지 않아 보이지 않는다. 지도에 공개된 위치로 한 구간씩 간다.
            mark = ctx.session.scene.data.get("leader_on_map")
            if mark is None:
                return SkillOutcome(False, "leader_lost", tr(LEADER_HIDDEN_KO, LEADER_HIDDEN_EN))
            here = ctx.session.state.data["pos"]
            if not announced and ctx.speak is not None:
                where = where_ko(here, mark["pos"])
                await ctx.speak(
                    tr(
                        f"지도에서 너를 찾았어. {where}에 있네. 갈게!",
                        f"Found you on the map, {where}. On my way!",
                    )
                )
            announced = True
            await _do(
                ctx,
                "move_to",
                {"target": {"pos": _toward(here, mark["pos"], FAR_LEG_M)}, "arrive_radius": 3.0, "run": True},
                timeout=60,
            )
            here = ctx.session.state.data["pos"]
            gained = float(mark["distance"]) - distance_m(here, mark["pos"])
            stalls = stalls + 1 if gained < FAR_MIN_GAIN_M else 0
            if stalls >= FAR_STALLS:
                where = where_ko(mark["pos"], here)
                return SkillOutcome(
                    False,
                    "blocked",
                    tr(
                        f"길이 막혀서 더 못 가겠어. 나는 네 {where}에 있어.",
                        f"The way's blocked, I can't get any further. From you, I'm {where}.",
                    ),
                )
            continue
        stalls = 0
        if leader["distance"] > 4:
            await _do(
                ctx,
                "move_to",
                {"target": {"id": leader["id"]}, "arrive_radius": 3.0, "run": True},
                timeout=60,
            )
        else:
            await _do(ctx, "wait", {"seconds": 1.0})


async def pick_up(ctx: SkillContext) -> SkillOutcome:
    """Pick up what the leader put down at their feet. The game does not auto-pick items a player drops
    (ItemDrop.OnPlayerDrop), so each one is taken with the pickup action."""
    picked: list[str] = []
    tried: set[str] = set()
    while len(picked) < HANDOVER_LIMIT:
        await _wait_scene(ctx)
        assert ctx.session.scene is not None
        leader = ctx.session.scene.data.get("leader")
        if leader is None:
            return SkillOutcome(False, "leader_lost", tr("네가 안 보여", "I can't see you"))
        lying = [
            e
            for e in ctx.session.nearby("item")
            if e["id"] not in tried and _distance(e["pos"], leader["pos"]) <= HANDOVER_RADIUS
        ]
        if not lying:
            break
        item = min(lying, key=lambda e: e["distance"])
        tried.add(item["id"])
        result = await _do(ctx, "move_to", {"target": {"id": item["id"]}, "arrive_radius": 1.5}, timeout=60)
        if result.status == "succeeded" and result.code == "arrived":
            result = await _do(ctx, "pickup", {"id": item["id"]})
        if result.code == "picked_up":
            picked.append(str(result.evidence.get("item") or item.get("name")))
    if not picked:
        return SkillOutcome(
            False,
            "nothing_handed_over",
            tr("네 발밑에 주울 게 안 보여", "I don't see anything at your feet to pick up"),
        )
    got = ", ".join(picked)
    return SkillOutcome(True, "done", tr(f"{got} 받았어. 고마워!", f"Got {got}. Thanks!"))


async def wait_here(ctx: SkillContext) -> SkillOutcome:
    while True:
        await _do(ctx, "wait", {"seconds": 5.0})


async def retreat(ctx: SkillContext) -> SkillOutcome:
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    if leader is None:
        return SkillOutcome(False, "leader_lost", tr("도망칠 곳이 안 보여", "I don't see anywhere to run to"))
    result = await _do(
        ctx, "move_to", {"target": {"id": leader["id"]}, "arrive_radius": 2.5, "run": True}, timeout=60
    )
    return SkillOutcome(
        result.status == "succeeded", result.code, tr("네 옆으로 피했어", "Fell back to your side")
    )


# 먹으려다 몸이 거절한 음식은 이만큼 다시 고르지 않는다(날고기처럼 먹을 수 없는 것, 이미 먹은 것).
REFUSED_FOOD_S = 300.0
# 큰 적에게 죽었을 때: 리더가 묘비에서 이만큼 안에 오면 같이 간다. 그때까지 리더 곁(이만큼 안)에 있는다.
WITH_LEADER_M = 25.0
STAY_BY_LEADER_M = 8.0


async def eat(ctx: SkillContext) -> SkillOutcome:
    item = str(ctx.goal.args["item"])
    result = await _do(ctx, "eat", {"item": item})
    if result.status != "succeeded":
        refused: dict[str, float] = ctx.memory.setdefault("refused_food", {})
        refused[item] = time.monotonic() + REFUSED_FOOD_S
        return SkillOutcome(
            False, result.code, tr(f"{josa(item, '은는')} 지금 못 먹겠어", f"I can't eat {item} right now")
        )
    return SkillOutcome(True, result.code, tr(f"{josa(item, '을를')} 먹었어", f"Ate some {item}"))


def food_to_eat(ctx: SkillContext, in_danger: bool) -> str | None:
    """P0 survival: keep food effects up (max health, regeneration). In a fight, eat only when badly hurt."""
    scene, state = ctx.session.scene, ctx.session.state
    if scene is None or state is None:
        return None
    active = {f["name"] for f in scene.data.get("foods", [])}
    hp = state.data["hp"] / max(1.0, state.data["hp_max"])
    if len(active) >= 3 or (active and hp >= 0.4) or (in_danger and hp >= 0.25):
        return None
    refused: dict[str, float] = ctx.memory.get("refused_food", {})
    now = time.monotonic()
    candidates = [
        i
        for i in ctx.session.inventory()
        if i.get("food") and i["name"] not in active and refused.get(i["name"], 0.0) <= now
    ]
    if not candidates:
        return None
    best = max(
        candidates, key=lambda i: float(i["food"].get("health", 0)) + float(i["food"].get("stamina", 0))
    )
    name: str = best["name"]
    return name


async def give(ctx: SkillContext) -> SkillOutcome:
    """Hand `count` of `item` to the leader: walk up, turn to them, put it down at their feet."""
    item, count = str(ctx.goal.args["item"]), int(ctx.goal.args.get("count", 1))
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    if leader is None:
        return SkillOutcome(
            False, "leader_lost", tr("네가 안 보여서 못 건네겠어", "I can't see you, so I can't hand it over")
        )
    await _do(ctx, "move_to", {"target": {"id": leader["id"]}, "arrive_radius": 2.0, "run": True}, timeout=60)
    result = await _do(ctx, "drop", {"item": item, "count": count, "toward": {"id": leader["id"]}})
    if result.code != "dropped":
        return SkillOutcome(
            False,
            result.code,
            tr(
                f"{josa(item, '을를')} 못 건넸어 ({result.code})",
                f"Couldn't hand over the {item} ({result.code})",
            ),
        )
    dropped = result.evidence.get("dropped")
    return SkillOutcome(
        True,
        "given",
        tr(
            f"{item} {dropped}개 네 앞에 놓았어. 주워 가!",
            f"Put {dropped} {item} down in front of you. Grab it!",
        ),
    )


async def go_to(ctx: SkillContext) -> SkillOutcome:
    """Walk to a remembered place (the workbench, the altar)."""
    name = str(ctx.goal.args["place"])
    place = ctx.world.place(name) if ctx.world is not None else None
    if place is None:
        return SkillOutcome(
            False,
            "place_unknown",
            tr(f"{josa(name, '이가')} 어딘지 기억이 안 나", f"I can't remember where the {name} is"),
        )
    result = await _do(
        ctx,
        "move_to",
        {"target": {"pos": list(place.pos)}, "arrive_radius": 3.0, "run": True, "timeout_s": 120},
        125,
    )
    return SkillOutcome(result.code == "arrived", result.code, tr(f"{name}에 왔어", f"Made it to the {name}"))


async def _with_leader_to(ctx: SkillContext, place: list[float]) -> None:
    """Stay by the leader until the leader is near `place`; then go there together."""
    while True:
        await _wait_scene(ctx)
        scene = ctx.session.scene.data if ctx.session.scene else {}
        leader = scene.get("leader") or scene.get("leader_on_map")
        if leader is not None and _distance(leader["pos"], place) < WITH_LEADER_M:
            return
        if leader is not None and float(leader.get("distance", 0.0)) > STAY_BY_LEADER_M:
            target = {"id": leader["id"]} if "id" in leader else {"pos": leader["pos"]}
            await _do(
                ctx,
                "move_to",
                {"target": target, "arrive_radius": STAY_BY_LEADER_M / 2, "run": True, "timeout_s": 10},
                timeout=15,
            )
        else:
            await _do(ctx, "wait", {"seconds": 2.0}, timeout=5)


async def recover(ctx: SkillContext) -> SkillOutcome:
    """After dying: walk back to where he fell and take everything back from the tombstone."""
    fell = list(ctx.goal.args["pos"])
    # 다시 이어 할 때 이미 되찾았는지 알 수 있게 시작할 때 가진 수를 남긴다(먹기 등이 중간에 끼어든다).
    start = ctx.goal.progress.setdefault("held_at_start", sum(_held(ctx).values()))
    if ctx.goal.args.get("with_leader"):
        await _with_leader_to(ctx, fell)
    for _leg in range(20):
        await _wait_scene(ctx)
        assert ctx.session.state is not None
        here = ctx.session.state.data["pos"]
        if _distance(here, fell) < 8 and _nearest(ctx, "tombstone") is not None:
            break
        await _do(
            ctx,
            "move_to",
            {"target": {"pos": _toward(here, fell, FAR_LEG_M)}, "arrive_radius": 3.0, "run": True},
            timeout=60,
        )
    tomb = _nearest(ctx, "tombstone")
    if tomb is None:
        if sum(_held(ctx).values()) > start:
            await equip_for_fight(ctx, None)
            return SkillOutcome(
                True,
                "recovered",
                tr("내 물건 다 찾았어. 다시 갈 수 있어!", "Got all my stuff back. Ready to go again!"),
            )
        return SkillOutcome(
            False,
            "no_tombstone",
            tr(
                "내가 죽은 자리에 왔는데 묘비가 안 보여",
                "I'm back where I died, but I don't see my tombstone",
            ),
        )
    before = sum(_held(ctx).values())
    await _do(ctx, "move_to", {"target": {"id": tomb["id"]}, "arrive_radius": 1.5}, timeout=30)
    await _do(ctx, "interact", {"id": tomb["id"]})
    try:
        await ctx.session.wait_for(lambda: sum(_held(ctx).values()) > before, 5)
    except TimeoutError:
        return SkillOutcome(
            False,
            "not_recovered",
            tr("묘비를 열었는데 물건이 안 들어와", "I opened the tombstone, but my stuff isn't coming back"),
        )
    await equip_for_fight(ctx, None)
    return SkillOutcome(
        True,
        "recovered",
        tr("내 물건 다 찾았어. 다시 갈 수 있어!", "Got all my stuff back. Ready to go again!"),
    )


SKILLS = {
    "recover": recover,
    "give": give,
    "go_to": go_to,
    "eat": eat,
    "pick_up": pick_up,
    "gather_wood": gather_wood,
    "defend": defend,
    "follow": follow,
    "wait": wait_here,
    "retreat": retreat,
}
