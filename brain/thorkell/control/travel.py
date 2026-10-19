"""Getting about the way a player does: through portals.

2026-10-18 rehearsal: the leader said "포탈 들어가면 집으로 갈 수 있어" and Thorkell neither saw the portal
nor knew how to use one. A player walks into a portal's middle; if it is connected (the swirl shows), the game
carries them to the other portal with the same tag. Production code never teleports: Thorkell walks in.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from thorkell.body.session import CommandRejected
from thorkell.control.skills import SkillContext, SkillOutcome, _do
from thorkell.lang import tr
from thorkell.world.where import distance_m

log = logging.getLogger(__name__)

# 포털을 지나면 이만큼 넘게 떨어진 곳에 나온다(걸어서는 몇 초 안에 못 가는 거리).
PORTAL_JUMP_M = 30.0
# 들어가서 저쪽에 나올 때까지(불러오기 포함).
THROUGH_TIMEOUT_S = 30.0


async def use_portal(ctx: SkillContext) -> SkillOutcome:
    """Go through a portal in sight; with `tag`, the one with that tag."""
    tag = str(ctx.goal.args.get("tag") or "")
    portals = [e for e in ctx.session.nearby("portal") if not tag or e.get("tag") == tag]
    if not portals:
        missing = (
            tr(f"'{tag}' 포털이 안 보여", f"I don't see a '{tag}' portal")
            if tag
            else tr("포털이 안 보여", "I don't see a portal")
        )
        return SkillOutcome(False, "no_portal", missing)
    return await go_through(ctx, min(portals, key=lambda e: float(e["distance"])))


async def go_through(ctx: SkillContext, portal: dict[str, Any]) -> SkillOutcome:
    if not portal.get("connected"):
        return SkillOutcome(
            False,
            "not_connected",
            tr(
                "이 포털은 이어진 곳이 없나 봐(소용돌이가 안 보여)",
                "This portal doesn't seem to lead anywhere (no swirl)",
            ),
        )
    assert ctx.session.state is not None
    start = list(ctx.session.state.data["pos"])
    center = portal.get("center") or portal["pos"]

    def crossed() -> bool:
        state = ctx.session.state
        return state is not None and distance_m(state.data["pos"], start) > PORTAL_JUMP_M

    # 건너가면 가던 곳(이쪽 포털)이 멀어진다. 건너간 것을 보면 바로 걸음을 멈춘다.
    walking = asyncio.create_task(
        _do(ctx, "move_to", {"target": {"pos": center}, "arrive_radius": 0.3, "timeout_s": 20}, timeout=25)
    )
    try:
        await ctx.session.wait_for(crossed, THROUGH_TIMEOUT_S)
    except TimeoutError:
        return SkillOutcome(
            False,
            "did_not_go",
            tr(
                "포털에 들어갔는데 아무 데도 안 갔어",
                "I walked into the portal, but it didn't take me anywhere",
            ),
        )
    finally:
        if not walking.done():
            walking.cancel()
        try:
            await walking
        except asyncio.CancelledError:
            pass
        except (CommandRejected, TimeoutError) as error:
            # 건너가는 동안(불러오기) 몸이 명령을 못 받을 수 있다. 건넜는지는 자리로 본다.
            log.info("walking into the portal ended with %s", error)
    return SkillOutcome(True, "went_through", tr("포털을 지나왔어", "Made it through the portal"))


SKILLS = {"use_portal": use_portal}
