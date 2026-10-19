"""Plan validator: a plan is rejected if it refers to things that don't exist or can't be justified."""

from __future__ import annotations

from dataclasses import dataclass, field

from thorkell.lang import tr
from thorkell.plan.quantity import Feasible
from thorkell.plan.schema import COUNT_RANGE, MAX_STEPS, SECONDS_RANGE, SKILL_CATALOG, Plan, Step

ENDLESS_SKILLS = {"follow"}


@dataclass(frozen=True)
class Context:
    inventory: frozenset[str]
    known_fact_ids: frozenset[str] = frozenset()
    feasible: Feasible | None = None
    edible: frozenset[str] = field(default_factory=frozenset)
    # 게임이 보여 준 이름들(제작 메뉴, 망치 메뉴, 기억하는 장소, 이름표로 본 생물, 본 적 있는 아이템)
    recipes: frozenset[str] = frozenset()
    pieces: frozenset[str] = frozenset()
    places: frozenset[str] = frozenset()
    creatures: frozenset[str] = frozenset()
    items: frozenset[str] = frozenset()
    # 리더가 한 말. 리더가 말한 이름은 토르켈이 아직 못 봤어도 찾아보거나 시도해 볼 수 있다.
    request: str = ""


def validate(plan: Plan, context: Context) -> list[str]:
    problems: list[str] = []
    if plan.clarify:
        if plan.steps:
            problems.append("a plan that asks a clarifying question must not contain steps yet")
        return problems
    if not plan.steps and not plan.speech_gist_ko.strip():
        problems.append("no steps and nothing to say")  # 말로만 답하는 계획(인사·잡담)은 괜찮다

    ids = [s.id for s in plan.steps]
    if len(ids) != len(set(ids)):
        problems.append("duplicate step ids")
    if len(ids) > MAX_STEPS:
        problems.append(f"too many steps ({len(ids)}); at most {MAX_STEPS}")
    seen: set[str] = set()
    searched: set[str] = set()
    # 앞 단계에서 손에 넣을 것(따거나 만든 것). 실게임(2026-10-19): "버섯을 따서 건네기"를 버섯이 아직 가방에
    # 없다고 두 번 거절해 먹을 것 부탁을 못 했다.
    coming: set[str] = set()
    for index, step in enumerate(plan.steps):
        if step.skill not in SKILL_CATALOG:
            problems.append(f"{step.id}: unknown skill {step.skill}")
            continue
        missing = [a for a in SKILL_CATALOG[step.skill][0] if a not in step.args]
        if missing:
            hints = ", ".join(f"{a}: {tr(ARG_HINTS[a], ARG_HINTS_EN[a])}" for a in missing if a in ARG_HINTS)
            problems.append(
                f"{step.id}: {step.skill} needs {', '.join(missing)}" + (f" ({hints})" if hints else "")
            )
        for dependency in step.after:
            if dependency not in seen:
                problems.append(f"{step.id}: depends on {dependency} which does not come before it")
        for key, (low, high) in (("count", COUNT_RANGE), ("seconds", SECONDS_RANGE)):
            value = step.args.get(key)
            if value is not None and not (isinstance(value, int) and low <= value <= high):
                problems.append(f"{step.id}: {key} must be {low}-{high}, got {value!r}")
        item = step.args.get("item")
        if step.skill in ("equip", "eat") and item is not None and item not in context.inventory | coming:
            problems.append(f"{step.id}: {item} is not in the inventory")
        if (
            step.skill == "eat"
            and item is not None
            and context.edible
            and item not in context.edible
            and item not in coming
        ):
            problems.append(f"{step.id}: {item} is not known to be food")
        problems.extend(_names(step, context, searched, frozenset(coming)))
        if step.skill in ("gather", "craft") and item is not None:
            coming.add(str(item))
        if step.skill == "gather_wood":
            # 실게임(2026-10-19): "도끼를 새로 만들고 나무를 해서 건네기"를 나무가 아직 없다고 거절했다.
            coming.add(tr("나무", "Wood"))
        if step.skill == "search":
            searched.add(str(step.args.get("name", "")))
        if step.skill in ENDLESS_SKILLS and index != len(plan.steps) - 1:
            problems.append(f"{step.id}: {step.skill} never ends, so it can only be the last step")
        for cite in step.cites:
            if cite not in context.known_fact_ids:
                problems.append(f"{step.id}: cites unknown fact {cite}")
        seen.add(step.id)

    for condition in plan.abort_if:
        if condition.cond == "hp_below" and (condition.value is None or not 0 < condition.value < 1):
            problems.append(f"hp_below needs a health fraction between 0 and 1, got {condition.value}")

    for assumption in plan.assumptions:
        # 근거(사실 id)를 달지 않은 가정은 가설로 본다. 실제 Flash는 "라즈베리는 먹을 수 있다"처럼
        # 화면에 보이는 것을 근거 없이 hypothesis=false로 적어서, 거절하면 멀쩡한 계획을 두 번 다 버렸다.
        # 사실 id가 아닌 근거("보이는 것: 라즈베리 덤불")도 같다: 근거 없는 가설로 둔다.
        assumption.cites = [cite for cite in assumption.cites if cite in context.known_fact_ids]
        if not assumption.hypothesis and not assumption.cites:
            assumption.hypothesis = True

    feasible = context.feasible
    if (
        plan.quantity is not None
        and feasible is not None
        and feasible.max is not None
        and plan.quantity.value > feasible.max
        and plan.quantity.basis != "user"
    ):
        problems.append(f"quantity {plan.quantity.value} exceeds what is feasible ({feasible.describe()})")
    gather = [s for s in plan.steps if s.skill == "gather_wood"]
    if (
        plan.quantity is not None
        and gather
        and sum(int(s.args.get("count", 0)) for s in gather) != plan.quantity.value
    ):
        problems.append("gather counts do not add up to the stated quantity")
    return problems


# 빠진 인자를 고칠 때 모델에게 주는 설명.
# 실제 Flash는 "gather needs count"만 보고는 두 번 다 count를 빼먹었다.
ARG_HINTS = {
    "count": "몇 개인지 정수. 부탁에 없으면 지금 상황(가방·시간·쓸 곳)에서 네가 정한다",
    "item": "가방·메뉴·보이는 것에 나온 이름 그대로",
    "creature": "이름표에 나온 이름이나 리더가 말한 이름",
    "piece": "망치 메뉴에 있는 이름",
}
ARG_HINTS_EN = {
    "count": (
        "how many, as an integer. If the request doesn't say, you decide from the situation "
        "(bag, time, what it's for)"
    ),
    "item": "the name exactly as it appears in the bag, a menu or what you see",
    "creature": "the name on its name tag or the name the leader said",
    "piece": "a name in the hammer menu",
}


def _names(step: Step, context: Context, searched: set[str], coming: frozenset[str]) -> list[str]:
    """A name in a step must be one the game showed Thorkell, one the leader said, or (for creatures and
    gathering) something an earlier step searches for. Items to hand over may come from an earlier step."""
    told = context.request

    def unknown(name: str, known: frozenset[str], what: str) -> list[str]:
        # 리더는 이름을 소문자나 복수형으로 말하기도 한다("chop some wood", "kill two boars").
        if name in known or (told and name.casefold() in told.casefold()) or name in searched:
            return []
        return [f"{step.id}: {what} '{name}' has not been shown by the game nor said by the leader"]

    args = step.args
    match step.skill:
        case "craft":
            item = str(args.get("item", ""))
            if item not in context.recipes:
                return [f"{step.id}: '{item}' is not in the crafting menu (recipe unknown)"]
        case "build":
            return unknown(str(args.get("piece", "")), context.pieces, "building")
        case "hunt" | "fight":
            return unknown(str(args.get("creature", "")), context.creatures, "creature")
        case "gather":
            return unknown(str(args.get("item", "")), context.items | context.inventory, "item")
        case "go_to":
            place = str(args.get("place", ""))
            if place not in context.places:
                return [f"{step.id}: place '{place}' is not remembered"]
        case "give" | "cook" | "offer":
            item = str(args.get("item", ""))
            if item not in context.inventory | coming:
                return [f"{step.id}: {item} is not in the inventory"]
    return []
