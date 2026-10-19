"""Where something is, said the way a player reads the map: compass direction and a rough distance.

Valheim's map has north up: +z is north and +x is east. Positions are [x, y, z].
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from thorkell.lang import tr

COMPASS_KO = ("북", "북동", "동", "남동", "남", "남서", "서", "북서")
COMPASS_EN = ("north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest")
NEXT_TO_M = 3.0


def distance_m(origin: Sequence[float], target: Sequence[float]) -> float:
    return math.hypot(target[0] - origin[0], target[2] - origin[2])


def direction_ko(origin: Sequence[float], target: Sequence[float]) -> str:
    angle = math.degrees(math.atan2(target[0] - origin[0], target[2] - origin[2])) % 360
    index = round(angle / 45) % 8
    return tr(COMPASS_KO[index], COMPASS_EN[index])


def rough_m(distance: float) -> str:
    step = 5 if distance < 100 else 10 if distance < 1000 else 50
    return f"{round(distance / step) * step:.0f}m"


def where_ko(origin: Sequence[float], target: Sequence[float]) -> str:
    """'북동쪽 300m': where target is, seen from origin."""
    distance = distance_m(origin, target)
    if distance < NEXT_TO_M:
        return tr("바로 옆", "right here")
    direction = direction_ko(origin, target)
    return tr(f"{direction}쪽 {rough_m(distance)}", f"{rough_m(distance)} {direction}")
