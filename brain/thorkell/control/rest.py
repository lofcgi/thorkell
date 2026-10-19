"""Sleeping. The night passes only when every player lies in their own bed, so when the leader goes to bed
Thorkell does too. A bed belongs to whoever claims it first (its owner's name shows when you look at it).
Without a bed of its own Thorkell builds one beside the leader's, where the roof and the fire already are,
and claims it. Whether it worked is what the game shows: lying in the bed, then morning.
"""

from __future__ import annotations

import math
import time
from typing import Any

from thorkell.control.making import Skill, _game_says_since, build, run_child
from thorkell.control.skills import SkillContext, SkillOutcome, _do, _wait_scene
from thorkell.lang import tr

BED = "침대"
BED_EN = "Bed"
# 리더 침대 옆으로 이만큼 떨어진 자리에 짓는다(침대 폭 약 1m).
BESIDE_M = 1.6
# 침대 주인 이름은 가까이 가서 봐야 보인다.
LOOK_AT_BED_M = 3.0
MORNING_WAIT_S = 600.0
# 리더가 일어난 채로 이만큼 지나면 같이 일어난다.
LEADER_UP_S = 20.0


async def sleep(ctx: SkillContext) -> SkillOutcome:
    """Lie down in its own bed (claimed or built beside the leader's) and stay until morning."""
    bed = await _own_bed(ctx)
    if isinstance(bed, SkillOutcome):
        return bed
    await _do(ctx, "move_to", {"target": {"id": bed["id"]}, "arrive_radius": 1.5}, timeout=40)
    since = len(ctx.session.events_of("game_message"))
    lay = await _do(ctx, "interact", {"id": bed["id"]})
    if not lay.evidence.get("in_bed"):
        return SkillOutcome(
            False,
            "cannot_sleep",
            tr("침대에 못 누웠어.", "Couldn't lie down in the bed.") + _quote(_game_says_since(ctx, since)),
        )
    return await _until_morning(ctx)


async def _own_bed(ctx: SkillContext) -> dict[str, Any] | SkillOutcome:
    await _wait_scene(ctx)
    beds = ctx.session.nearby("bed")
    # 주인이 안 보이는(멀리 있는) 침대는 다가가서 본다.
    for unread in [b for b in beds if "owner" not in b][:3]:
        await _do(
            ctx, "move_to", {"target": {"id": unread["id"]}, "arrive_radius": LOOK_AT_BED_M}, timeout=40
        )
        await _wait_scene(ctx)
    beds = ctx.session.nearby("bed")
    mine = next((b for b in beds if b.get("mine")), None)
    if mine is not None:
        return mine
    free = next((b for b in beds if b.get("owner") == ""), None)
    if free is None:
        built = await _build_beside(ctx, beds)
        if isinstance(built, SkillOutcome):
            return built
        free = built
    return await _claim(ctx, free)


async def _build_beside(ctx: SkillContext, beds: list[dict[str, Any]]) -> dict[str, Any] | SkillOutcome:
    leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
    leader_name = leader.get("name") if leader else None
    theirs = next((b for b in beds if b.get("owner") == leader_name), None) or (beds[0] if beds else None)
    if theirs is None:
        return SkillOutcome(
            False,
            "no_bed",
            tr("근처에 침대가 없어. 어디서 자면 돼?", "There's no bed nearby. Where should I sleep?"),
        )
    x, y, z = theirs.get("center", theirs["pos"])
    yaw = math.radians(float(theirs.get("yaw", 0.0)))
    tries: list[dict[str, Any]] = []
    piece = tr(BED, BED_EN)
    for side in (1.0, -1.0):
        at = [x + side * BESIDE_M * math.cos(yaw), y, z - side * BESIDE_M * math.sin(yaw)]
        made = await run_child(ctx, f"build:bed:{side:+.0f}", "build", {"piece": piece, "at": at}, build)
        if made.ok:
            await _wait_scene(ctx)
            built = next((b for b in ctx.session.nearby("bed") if b["id"] == made.evidence.get("id")), None)
            if built is not None:
                return built
        tries.append({"at": at, "code": made.code, "detail": made.detail_ko})
    return SkillOutcome(
        False,
        "no_bed_spot",
        tr("네 침대 옆에 내 침대를 못 놓겠어", "I can't place my bed next to yours"),
        {"tries": tries},
    )


async def _claim(ctx: SkillContext, bed: dict[str, Any]) -> dict[str, Any] | SkillOutcome:
    await _do(ctx, "move_to", {"target": {"id": bed["id"]}, "arrive_radius": 1.5}, timeout=40)
    since = len(ctx.session.events_of("game_message"))
    await _do(ctx, "interact", {"id": bed["id"]})
    await _wait_scene(ctx)
    claimed = next((b for b in ctx.session.nearby("bed") if b["id"] == bed["id"] and b.get("mine")), None)
    if claimed is None:
        return SkillOutcome(
            False,
            "cannot_claim",
            tr("침대를 내 것으로 못 했어.", "Couldn't claim the bed as mine.")
            + _quote(_game_says_since(ctx, since)),
        )
    return claimed


async def _until_morning(ctx: SkillContext) -> SkillOutcome:
    began = time.monotonic()
    leader_up: float | None = None
    while time.monotonic() - began < MORNING_WAIT_S:
        await _wait_scene(ctx)
        state = ctx.session.state.data if ctx.session.state else {}
        scene = ctx.session.scene.data if ctx.session.scene else {}
        if not state.get("in_bed"):
            if not scene.get("env", {}).get("night"):
                return SkillOutcome(True, "slept", tr("잘 잤다! 좋은 아침이야.", "Slept well! Good morning."))
            return SkillOutcome(
                False,
                "woke_at_night",
                tr("누웠다가 깼어. 아직 밤이야.", "Lay down but woke up. It's still night."),
            )
        leader = scene.get("leader")
        if leader is not None and not leader.get("in_bed"):
            leader_up = leader_up or time.monotonic()
            if time.monotonic() - leader_up > LEADER_UP_S:
                await _get_up(ctx)
                return SkillOutcome(
                    True,
                    "got_up",
                    tr("너 안 자는구나. 나도 일어날게.", "You're not sleeping, huh. I'll get up too."),
                )
        else:
            leader_up = None
    await _get_up(ctx)
    return SkillOutcome(
        False,
        "no_morning",
        tr("한참 누워 있었는데 아침이 안 와", "I've been lying here a long time, but morning isn't coming"),
    )


async def _get_up(ctx: SkillContext) -> None:
    state = ctx.session.state.data if ctx.session.state else {}
    x, y, z = state.get("pos", [0.0, 0.0, 0.0])
    await _do(ctx, "move_to", {"target": {"pos": [x + 1.0, y, z]}, "arrive_radius": 0.5}, timeout=10)


def _quote(said: str | None) -> str:
    return tr(f" '{said}'래.", f" It says '{said}'.") if said else ""


SKILLS: dict[str, Skill] = {"sleep": sleep}
