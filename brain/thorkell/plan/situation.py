"""What Thorkell knows right now, written out in Korean for the planner — the same things a player in his
place would have on screen or remember: his own bars and bag, what is in view (creatures he has not looked
at stay unnamed), the crafting and hammer menus, places and sources he remembers, texts he has read, the last
game messages and the conversation. Nothing from game internals and no species keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thorkell.lang import tr
from thorkell.world.memory import WorldMemory
from thorkell.world.where import where_ko

MAX_NEARBY = 14
MAX_RECIPES = 24
MAX_PIECES = 18
MAX_TEXT = 220
DAY_LENGTH_S = 1800.0
DUSK = 0.70


@dataclass(frozen=True)
class Known:
    """The slow-changing part: menus, memory, facts, texts, talk, goals."""

    recipes: list[dict[str, Any]] = field(default_factory=list)
    pieces: list[dict[str, Any]] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    texts: list[tuple[str, str]] = field(default_factory=list)
    talk: list[tuple[str, str]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    doing: str = ""
    agenda: list[str] = field(default_factory=list)
    tried: list[str] = field(default_factory=list)


def _pct(value: float, top: float) -> str:
    return f"{value:.0f}/{top:.0f}"


def describe(state: dict[str, Any], scene: dict[str, Any], world: WorldMemory, known: Known) -> str:
    here = state.get("pos", [0.0, 0.0, 0.0])
    lines: list[str] = []
    foods = ", ".join(_food(f) for f in scene.get("foods", []))
    effects = ", ".join(scene.get("effects", []))
    hp = _pct(state.get("hp", 0), state.get("hp_max", 1))
    stamina = _pct(state.get("stamina", 0), state.get("stamina_max", 1))
    lines.append(
        tr(
            f"[나] 체력 {hp}, 스태미나 {stamina}, 먹은 음식 {foods or '없음'} (최대 3가지)"
            + (f", 상태 {effects}" if effects else ""),
            f"[Me] health {hp}, stamina {stamina}, food eaten {foods or 'none'} (up to 3 kinds)"
            + (f", status {effects}" if effects else ""),
        )
    )
    env = scene.get("env", {})
    fraction = float(env.get("day_fraction", 0.5))
    left = max(0, int((DUSK - fraction) * DAY_LENGTH_S / 60))
    if env.get("night"):
        time_ko = tr("밤", "night")
    elif fraction < DUSK:
        time_ko = tr(f"낮(해 지기까지 약 {left}분)", f"daytime (about {left} min until dusk)")
    else:
        time_ko = tr("해 질 녘", "dusk")
    day, weather, biome = env.get("day", "?"), env.get("weather", "?"), scene.get("biome", "")
    lines.append(
        tr(
            f"[때] {day}일째 {time_ko}, 날씨 {weather}, {biome}",
            f"[Time] day {day}, {time_ko}, weather {weather}, {biome}",
        )
    )
    inventory = scene.get("inventory", [])
    hands = ", ".join(i["name"] + _worn(i) for i in inventory if i.get("equipped"))
    bag = ", ".join(f"{i['name']}{_worn(i)} {i['stack']}" for i in inventory if not i.get("equipped"))
    weight = f"{scene.get('weight', 0):.0f}/{scene.get('weight_max', 300):.0f}"
    lines.append(
        tr(
            f"[손] {hands or '맨손'} / [가방] {bag or '비어 있음'} (무게 {weight})",
            f"[Hands] {hands or 'empty'} / [Bag] {bag or 'empty'} (weight {weight})",
        )
    )
    lines.append(tr("[보이는 것] ", "[In sight] ") + _nearby(scene, here, world))
    lines.append(tr("[리더] ", "[Leader] ") + _leader(scene, here))
    if scene.get("raven"):
        raven = scene["raven"]
        lines.append(
            tr(
                f"[까마귀] {raven['name']}이(가) {raven['distance']:.0f}m 앞에 내려앉아 있다",
                f"[Raven] {raven['name']} has landed {raven['distance']:.0f} m ahead",
            )
        )
    lines.append(
        tr("[제작 메뉴] ", "[Crafting menu] ")
        + (_recipes(known.recipes) or tr("아직 아는 레시피 없음", "no recipes known yet"))
    )
    lines.append(
        tr("[망치 메뉴] ", "[Hammer menu] ")
        + (
            _pieces(known.pieces)
            or tr(
                "망치가 없거나 아는 건축물 없음(망치를 가져야 메뉴가 보인다)",
                "no hammer, or no buildings known (the menu shows only with a hammer)",
            )
        )
    )
    places = [f"{p.name} {where_ko(here, p.pos)}" for p in world.places()]
    lines.append(tr("[기억하는 곳] ", "[Places I remember] ") + (", ".join(places) or tr("없음", "none")))
    lines.append(
        tr("[이름을 아는 생물] ", "[Creatures I know by name] ")
        + (", ".join(world.creature_names()) or tr("아직 없음", "none yet"))
    )
    sources = _sources(world)
    lines.append(
        tr("[어디서 나오는지 아는 것] ", "[Where things come from] ")
        + (sources or tr("아직 없음", "nothing yet"))
    )
    if known.facts:
        lines.append(tr("[알게 된 사실] ", "[Things I learned] ") + " / ".join(known.facts))
    for label, text in known.texts:
        lines.append(tr(f"[읽은 글: {label}] ", f"[Text I read: {label}] ") + text[:MAX_TEXT])
    if known.messages:
        lines.append(tr("[최근 게임 메시지] ", "[Recent game messages] ") + " / ".join(known.messages))
    lines.append(tr("[하는 일] ", "[Doing] ") + (known.doing or tr("없음", "nothing")))
    if known.agenda:
        lines.append(tr("[장기 목표] ", "[Long-term goals] ") + " / ".join(known.agenda))
    if known.talk:
        lines.append(
            tr("[최근 대화] ", "[Recent talk] ") + " / ".join(f"{who}: {text}" for who, text in known.talk)
        )
    if known.tried:
        lines.append(tr("[이 부탁으로 해 본 것] ", "[Tried for this request] ") + " / ".join(known.tried))
    return "\n".join(lines)


def _worn(item: dict[str, Any]) -> str:
    # 사람은 인벤토리에서 닳아 부러진 것(내구도 0)을 빨갛게 본다.
    return tr("(부러짐)", " (broken)") if "durability" in item and float(item["durability"]) <= 0 else ""


def _food(food: dict[str, Any]) -> str:
    left = int(food.get("remaining_s", 0)) // 60
    return tr(f"{food['name']}({left}분)", f"{food['name']} ({left} min)")


def _nearby(scene: dict[str, Any], here: list[float], world: WorldMemory) -> str:
    grouped: dict[str, list[float]] = {}
    labels: list[tuple[float, str]] = []
    for entity in scene.get("nearby", []):
        kind = entity.get("kind")
        if kind in ("player",):
            continue
        name = world.creature_label(entity) if kind == "creature" else str(entity.get("name") or "")
        if not name:
            name = {
                "tree": tr("나무(서 있는)", "tree (standing)"),
                "log": tr("통나무", "log"),
                "rock": tr("바위", "rock"),
            }.get(str(kind), str(kind))
        if kind == "portal":
            # 이름표는 조준하면 뜨고, 이어져 있으면 소용돌이가 돈다(사람이 보는 것).
            tag = f" '{entity['tag']}'" if entity.get("tag") else ""
            name += tag + (
                tr("(이어짐)", " (connected)")
                if entity.get("connected")
                else tr("(안 이어짐)", " (not connected)")
            )
        elif kind == "door" and "open" in entity:
            name += tr("(열림)", " (open)") if entity["open"] else tr("(닫힘)", " (closed)")
        grouped.setdefault(name, []).append(float(entity["distance"]))
    for name, distances in grouped.items():
        nearest = min(distances)
        if len(distances) > 1:
            label = tr(
                f"{name} {len(distances)}개(가장 가까운 것 {nearest:.0f}m)",
                f"{len(distances)} x {name} (nearest {nearest:.0f} m)",
            )
        else:
            label = tr(f"{name}(가장 가까운 것 {nearest:.0f}m)", f"{name} ({nearest:.0f} m)")
        labels.append((nearest, label))
    labels.sort()
    return ", ".join(text for _, text in labels[:MAX_NEARBY]) or tr("특별한 것 없음", "nothing special")


def _leader(scene: dict[str, Any], here: list[float]) -> str:
    leader = scene.get("leader")
    if leader is not None:
        return f"{leader['name']} {where_ko(here, leader['pos'])}"
    mark = scene.get("leader_on_map")
    if mark is not None:
        return tr(
            f"{mark['name']} 안 보임, 지도에서 {where_ko(here, mark['pos'])}",
            f"{mark['name']} out of sight, on the map {where_ko(here, mark['pos'])}",
        )
    return tr("안 보이고 지도에도 위치가 없다", "out of sight and not on the map")


def _recipes(recipes: list[dict[str, Any]]) -> str:
    parts = []
    for recipe in recipes[:MAX_RECIPES]:
        needs = ", ".join(f"{r['name']} {r['have']}/{r['amount']}" for r in recipe["resources"])
        where = recipe["station"] or tr("맨손", "by hand")
        ready = (
            tr("만들 수 있음", "can make")
            if recipe.get("have_materials")
            else tr("재료 부족", "missing materials")
        )
        parts.append(f"{recipe['name']}({needs}; {where}; {ready})")
    return "; ".join(parts)


def _pieces(pieces: list[dict[str, Any]]) -> str:
    parts = []
    for piece in pieces[:MAX_PIECES]:
        needs = ", ".join(f"{r['name']} {r['amount']}" for r in piece["resources"])
        where = (
            tr(f"; {piece['station']} 근처", f"; near a {piece['station']}") if piece.get("station") else ""
        )
        parts.append(f"{piece['name']}({needs}{where})")
    return "; ".join(parts)


def _sources(world: WorldMemory) -> str:
    rows = world.db.execute("SELECT item, kind, source FROM sources ORDER BY times DESC LIMIT 20").fetchall()
    by_item: dict[str, list[str]] = {}
    for row in rows:
        how = {
            "pickable": tr("줍기", "picking"),
            "creature": tr("사냥", "hunting"),
            "tree": tr("베기", "chopping"),
        }.get(str(row["kind"]), str(row["kind"]))
        by_item.setdefault(str(row["item"]), []).append(f"{row['source']} {how}")
    return "; ".join(f"{item}: {', '.join(ways)}" for item, ways in by_item.items())
