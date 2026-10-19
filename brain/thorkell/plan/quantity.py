"""How much can Thorkell realistically gather right now? Computed by code, never by a model.

Every bound needs evidence: carrying weight is known (scene), per-unit weight only once an item of that
kind was carried, daylight left from the day fraction, gathering rate only from past measurements.
Unknown bounds are reported as unknown, not guessed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DAY_LENGTH_S = 1800.0  # Valheim's day/night cycle length
NIGHT_STARTS = 0.75


@dataclass(frozen=True)
class Bound:
    name: str  # carry | time
    limit: int
    detail: str


@dataclass(frozen=True)
class Feasible:
    max: int | None
    bounds: tuple[Bound, ...]
    unknown: tuple[str, ...]

    def describe(self) -> str:
        known = ", ".join(f"{b.name} <= {b.limit} ({b.detail})" for b in self.bounds) or "no known bound"
        unknown = f"; unknown: {', '.join(self.unknown)}" if self.unknown else ""
        return known + unknown


def unit_weight(scene: dict[str, Any], item_name: str) -> float | None:
    for item in scene.get("inventory", []):
        if item.get("name") == item_name and item.get("stack", 0) > 0:
            return float(item["weight"]) / float(item["stack"])
    return None


def gather_feasible(
    scene: dict[str, Any],
    item_name: str | None,
    rate_per_min: float | None,
    known_weight: float | None = None,
) -> Feasible:
    bounds: list[Bound] = []
    unknown: list[str] = []

    weight = known_weight or (unit_weight(scene, item_name) if item_name else None)
    headroom = float(scene.get("weight_max", 0)) - float(scene.get("weight", 0))
    if weight and weight > 0:
        limit = max(0, int(headroom // weight))
        bounds.append(Bound("carry", limit, f"{headroom:.0f} weight left / {weight:g} each"))
    else:
        unknown.append("unit weight")

    env = scene.get("env", {})
    fraction = env.get("day_fraction")
    if fraction is not None and not env.get("night"):
        seconds_left = max(0.0, (NIGHT_STARTS - float(fraction)) * DAY_LENGTH_S)
        if rate_per_min:
            limit = int(seconds_left / 60.0 * rate_per_min)
            bounds.append(
                Bound("time", limit, f"{seconds_left / 60:.0f} min to dusk x {rate_per_min:.1f}/min")
            )
        else:
            unknown.append("gathering rate")
    elif env.get("night"):
        bounds.append(Bound("time", 0, "already night"))

    best = min((b.limit for b in bounds), default=None)
    return Feasible(best, tuple(bounds), tuple(unknown))
