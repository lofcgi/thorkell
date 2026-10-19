"""The first boss's altar the way players in the videos found it: register the location at the glowing stone
(the map gets a mark), read what the altar wants, and offer it when the leader agrees. What comes out is
fought like anything else Thorkell faces (control/fight.py): he decides what it is and how to fight it.

Summoning is never decided alone: it is a request goal the leader asked for (the planner only plans it
when the leader clearly wants it).
"""

from __future__ import annotations

from thorkell.control.making import Skill, _here
from thorkell.control.skills import SkillContext, SkillOutcome, _do, _nearest, _wait_scene
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.world.where import where_ko


async def register_location(ctx: SkillContext) -> SkillOutcome:
    """Use a glowing stone (vegvisir) in view: the game marks a place on the map."""
    stone = _nearest(ctx, "vegvisir")
    if stone is None:
        return SkillOutcome(False, "no_vegvisir", tr("빛나는 돌이 안 보여", "I don't see a glowing stone"))
    pins_before = {p["name"] for p in (ctx.session.scene.data.get("pins", []) if ctx.session.scene else [])}
    await _do(ctx, "move_to", {"target": {"id": stone["id"]}, "arrive_radius": 1.8}, timeout=40)
    await _do(ctx, "interact", {"id": stone["id"]})
    await _wait_scene(ctx)
    pins = ctx.session.scene.data.get("pins", []) if ctx.session.scene else []
    new = [p for p in pins if p["name"] not in pins_before]
    if not new:
        return SkillOutcome(
            False,
            "nothing_marked",
            tr(
                "돌을 만졌는데 지도에 아무것도 안 생겼어",
                "I touched the stone, but nothing showed up on the map",
            ),
        )
    pin = new[0]
    where = _where(ctx, pin["pos"])
    return SkillOutcome(
        True,
        "marked",
        tr(
            f"지도에 '{pin['name']}' 표시가 생겼어. {where}에 있대!",
            f"A '{pin['name']}' mark showed up on the map. It's {where}!",
        ),
    )


def _where(ctx: SkillContext, pos: list[float]) -> str:
    return where_ko(_here(ctx), pos)


async def offer(ctx: SkillContext) -> SkillOutcome:
    """Offer `item` at the altar (seen or remembered). What it wants is learned from the game's answer."""
    item = str(ctx.goal.args["item"])
    altar = _nearest(ctx, "altar")
    if altar is None and ctx.world is not None:
        known = next((p for p in ctx.world.places() if p.kind == "altar"), None)
        if known is not None:
            await _do(
                ctx, "move_to", {"target": {"pos": list(known.pos)}, "arrive_radius": 4.0, "run": True}, 120
            )
            await _wait_scene(ctx)
            altar = _nearest(ctx, "altar")
    if altar is None:
        return SkillOutcome(False, "no_altar", tr("제단이 어딨는지 몰라", "I don't know where the altar is"))
    await _do(ctx, "move_to", {"target": {"id": altar["id"]}, "arrive_radius": 1.8}, timeout=40)
    messages = len(ctx.session.events_of("game_message"))
    result = await _do(ctx, "use_item", {"item": item, "id": altar["id"]})
    said = [str(e.data.get("text")) for e in ctx.session.events_of("game_message")[messages:]]
    if result.code != "used":
        reason = tr(f" '{said[-1]}'래.", f" It says '{said[-1]}'.") if said else ""
        return SkillOutcome(
            False,
            "refused",
            tr(
                f"제단에 {josa(item, '을를')} 올렸는데 안 받아.{reason}",
                f"I put the {item} on the altar, but it won't take it.{reason}",
            ),
        )
    return SkillOutcome(
        True,
        "offered",
        tr("제단에 올렸어! 뭔가 온다, 준비해!", "Put it on the altar! Something's coming, get ready!"),
    )


SKILLS: dict[str, Skill] = {"register_location": register_location, "offer": offer}
