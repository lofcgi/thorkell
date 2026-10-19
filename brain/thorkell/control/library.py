"""Every skill the controller can start, by goal kind."""

from __future__ import annotations

from thorkell.control import boss, field, fight, making, rest, skills, travel

SKILLS: dict[str, making.Skill] = {
    **skills.SKILLS,
    **making.SKILLS,
    **field.SKILLS,
    **boss.SKILLS,
    **fight.SKILLS,
    **rest.SKILLS,
    **travel.SKILLS,
}
