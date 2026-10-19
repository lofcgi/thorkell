"""Compact text state for System One decisions (Jev / laya).

Fixed English section order, numbers precomputed (System One models can't count), only names the
game has shown the bot, and <= MAX_CHARS so the same request fits laya-typed-decisions (1,024 tokens).
"""

from __future__ import annotations

from typing import Any

MAX_CHARS = 1800


def _fmt(value: float) -> str:
    return f"{value:.0f}" if abs(value) >= 10 else f"{value:.1f}"


def decision_state(
    state: dict[str, Any] | None,
    scene: dict[str, Any] | None,
    task: str | None = None,
    recent: list[str] | None = None,
) -> str:
    lines: list[str] = []
    if state is not None:
        hp, hp_max = state.get("hp", 0.0), state.get("hp_max", 1.0)
        stamina, stamina_max = state.get("stamina", 0.0), state.get("stamina_max", 1.0)
        flags = [f for f in ("swimming", "encumbered", "in_attack") if state.get(f)]
        lines.append(
            f"SELF hp {_fmt(hp)}/{_fmt(hp_max)} ({hp / max(1.0, hp_max):.0%})"
            f" stamina {_fmt(stamina)}/{_fmt(stamina_max)}" + (" " + " ".join(flags) if flags else "")
        )
    if scene is not None:
        env = scene.get("env", {})
        lines.append(
            f"TIME {'night' if env.get('night') else 'day'}"
            + (f" day_fraction {env['day_fraction']:.2f}" if "day_fraction" in env else "")
            + (f" biome {scene['biome']}" if scene.get("biome") else "")
        )
        inventory = scene.get("inventory", [])
        equipped = [i["name"] for i in inventory if i.get("equipped")]
        lines.append(f"EQUIPPED {', '.join(equipped) if equipped else 'nothing'}")
        carried = [f"{i['name']} x{i['stack']}" for i in inventory if not i.get("equipped")][:12]
        if carried:
            lines.append(f"CARRY {', '.join(carried)}")
        creatures = [e for e in scene.get("nearby", []) if e.get("kind") == "creature"][:6]
        for index, creature in enumerate(creatures, 1):
            details = [f"dist {_fmt(creature['distance'])}"]
            if "health" in creature:
                details.append(f"health {creature['health']:.0%}")
            if creature.get("stars"):
                details.append(f"stars {creature['stars']}")
            if creature.get("alerted"):
                details.append("alerted")
            lines.append(f"CREATURE [{index}] {creature['name']} " + " ".join(details))
        leader = scene.get("leader")
        if leader:
            lines.append(f"LEADER {leader['name']} dist {_fmt(leader['distance'])}")
    if task:
        lines.append(f"TASK {task}")
    for line in recent or []:
        lines.append(f"RECENT {line}")
    text = "\n".join(lines)
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 3] + "..."
