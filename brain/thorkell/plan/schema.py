"""Plan representation and the per-request JSON schema handed to the planner model.

The schema is rebuilt for every request so its enums contain only skills that exist and item names
the game has actually shown Thorkell — the model cannot even express an undiscovered item.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from thorkell.lang import tr

# skill -> (argument names, short description for the prompt)
SKILL_CATALOG: dict[str, tuple[tuple[str, ...], str]] = {
    "equip": (("item",), "손에 든다. item은 인벤토리에 있는 이름"),
    "eat": (("item",), "먹는다. item은 인벤토리에 있는 음식"),
    "gather_wood": (("count",), "나무를 베고 떨어진 목재를 count개 줍는다"),
    "gather": (
        ("item",),
        "재료를 count개 모은다(땅에서 줍거나, 주워 보거나, 베어서). 모르는 출처는 해 보며 배운다. "
        "item에 덤불 같은 딸 것의 이름을 써도 된다. count를 빼면 지금 보이는 만큼 모은다",
    ),
    "craft": (
        ("item",),
        "제작 메뉴에 있는 것을 count개(생략하면 1) 만든다. 재료가 모자라면 먼저 모으고, 필요한 제작대로 간다",
    ),
    "build": (("piece",), "망치 메뉴에 있는 건축물 하나를 짓는다. near=leader면 리더 곁에"),
    "shelter": ((), "작업대에 벽과 지붕을 둘러 쓸 수 있게 한다(작업대가 없으면 먼저 짓는다). 작은 집의 시작"),
    "hunt": (("creature",), "생물을 count마리(생략하면 1) 잡고 떨어진 것을 줍는다"),
    "search": (("name",), "아직 못 봤거나 근처에 없는 것을 주변을 돌며 찾아본다(이름표를 보고 안다)"),
    "cook": (("item",), "날것을 count개(생략하면 1) 불 위 요리대에서 굽는다(불·요리대가 없으면 짓는다)"),
    "go_to": (("place",), "기억하는 장소로 간다"),
    "register_location": ((), "보이는 빛나는 돌(베그비시르)을 만져 지도에 장소를 표시한다"),
    "offer": (("item",), "제단에 아이템을 바친다(보스 소환). 리더가 분명히 원할 때만"),
    "fight": (("creature",), "보이는 생물과 싸운다. 어떻게 싸울지는 그때 보고 겪은 것을 떠올려 정한다"),
    "give": (("item",), "리더 쪽으로 count개(생략하면 1) 내려놓아 건넨다"),
    "sleep": ((), "자기 침대에 눕는다(없으면 리더 침대 옆에 짓는다). 오후·밤에만 되고 모두 누워야 밤이 간다"),
    "follow": ((), "리더를 따라다닌다(끝나지 않음, 마지막 단계로만)"),
    "wait": (("seconds",), "제자리에서 기다린다"),
    "go_to_leader": ((), "리더 곁으로 간다"),
    "pick_up": ((), "리더 발밑에 놓인 아이템(리더가 건네준 것)을 줍는다"),
    "say": (("text",), "짧게 말한다(한국어)"),
    "use_portal": (
        (),
        "보이는 포털로 걸어 들어가 이어진 곳으로 간다(소용돌이가 돌아야 이어진 것). tag로 이름표를 고른다",
    ),
}

SKILL_CATALOG_EN: dict[str, str] = {
    "equip": "Hold it in hand. item is a name in the inventory",
    "eat": "Eat it. item is a food in the inventory",
    "gather_wood": "Chop trees and pick up count pieces of the wood that falls",
    "gather": (
        "Collect count of a material (pick it up from the ground, try picking it, or chop it). Learns "
        "an unknown source by trying. item may also be the name of something to pick, like a bush. "
        "Without count, collect as many as are in sight"
    ),
    "craft": (
        "Make count (default 1) of something in the crafting menu. Gathers missing materials first and "
        "goes to the station it needs"
    ),
    "build": "Build one piece from the hammer menu. near=leader puts it next to the leader",
    "shelter": (
        "Put walls and a roof around a workbench so it can be used (builds the workbench first if there is "
        "none). The start of a small house"
    ),
    "hunt": "Catch count (default 1) of a creature and pick up what it drops",
    "search": "Walk around looking for something not seen yet or not nearby (knows it by its name tag)",
    "cook": "Roast count (default 1) raw things on a cooking station over a fire (builds them if missing)",
    "go_to": "Go to a remembered place",
    "register_location": "Touch a glowing stone in sight (Vegvisir) to mark a place on the map",
    "offer": "Offer an item at an altar (summons a boss). Only when the leader clearly wants it",
    "fight": "Fight a creature in sight. How to fight is decided then, from what you see and remember",
    "give": "Put count (default 1) down in front of the leader to hand it over",
    "sleep": (
        "Lie down in your own bed (builds one next to the leader's bed if there is none). Only in the "
        "afternoon or at night, and the night passes only when everyone lies down"
    ),
    "follow": "Follow the leader around (never ends; only as the last step)",
    "wait": "Wait where you are",
    "go_to_leader": "Go to the leader",
    "pick_up": "Pick up the items at the leader's feet (what the leader handed over)",
    "say": "Say something short (in English)",
    "use_portal": (
        "Walk into a portal in sight and come out where it leads (it is connected if it swirls). tag "
        "picks one by its name tag"
    ),
}


def skill_description(skill: str) -> str:
    return tr(SKILL_CATALOG[skill][1], SKILL_CATALOG_EN[skill])


# 생략할 수 있는 인자와 그때 쓰는 값. 설명(위 SKILL_CATALOG)에 적어 모델도 안다.
# 단계 인자의 범위. 스키마가 아니라 검증기가 본다(plan_schema 참고).
COUNT_RANGE = (1, 500)
SECONDS_RANGE = (1, 600)
MAX_STEPS = 12

OPTIONAL_ARGS: dict[str, dict[str, Any]] = {
    "craft": {"count": 1},
    "hunt": {"count": 1},
    "cook": {"count": 1},
    "give": {"count": 1},
}


@dataclass(frozen=True)
class Names:
    """Names the game has shown Thorkell, by what they name. The schema's enums come from these, so the model
    cannot even write a recipe, building or place it has not been shown. Creature and search names stay free
    text: the leader may ask about something Thorkell has never seen (the validator checks those)."""

    items: tuple[str, ...] = ()
    recipes: tuple[str, ...] = ()
    pieces: tuple[str, ...] = ()
    places: tuple[str, ...] = ()


class Quantity(BaseModel):
    value: int = Field(ge=0)
    basis: str  # carry | time | purpose | user | default
    cites: list[str] = Field(default_factory=list)


class Assumption(BaseModel):
    text: str
    cites: list[str] = Field(default_factory=list)
    hypothesis: bool = False


class Step(BaseModel):
    id: str
    skill: str
    args: dict[str, Any] = Field(default_factory=dict)
    after: list[str] = Field(default_factory=list)
    budget_s: int = Field(default=120, ge=1, le=3600)
    cites: list[str] = Field(default_factory=list)


class AbortIf(BaseModel):
    cond: str  # hp_below | dusk | night
    value: float | None = None  # hp_below: 남은 체력 비율(0~1). 체력 점수나 퍼센트가 아니다.


class Plan(BaseModel):
    interpretation_ko: str
    clarify: str | None = None
    quantity: Quantity | None = None
    assumptions: list[Assumption] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    abort_if: list[AbortIf] = Field(default_factory=list)
    speech_gist_ko: str = ""
    # 이 단계들로 부탁이 다 끝나지 않는다(예: 재료를 모아야 제작 메뉴에 뜬다). 마치면 다시 생각한다.
    think_again_after: bool = False


def plan_schema(names: Names) -> dict[str, Any]:
    """JSON schema with dynamic enums. Gemini structured output supports this subset.

    No numeric bounds here: with the menu enums, bounds and descriptions together the real model refused the
    schema as too complex (400 "invalid argument"). The validator checks the ranges (`COUNT_RANGE` etc.)."""
    skill_enum = sorted(SKILL_CATALOG)
    arg_properties: dict[str, Any] = {
        "count": {"type": "integer", "description": f"{COUNT_RANGE[0]}~{COUNT_RANGE[1]}"},
        "seconds": {"type": "integer", "description": f"{SECONDS_RANGE[0]}~{SECONDS_RANGE[1]}"},
        "text": {"type": "string"},
        "creature": {
            "type": "string",
            "description": tr(
                "생물 이름(이름표에 나온 그대로)", "creature name (exactly as on its name tag)"
            ),
        },
        "name": {"type": "string", "description": tr("찾을 것의 이름", "name of what to look for")},
        "near": {"type": "string", "enum": ["leader", "here"]},
        "tag": {"type": "string", "description": tr("포털 이름표", "the portal's name tag")},
    }
    for key, values in (
        ("item", sorted(set(names.items) | set(names.recipes))),
        ("piece", sorted(set(names.pieces))),
        ("place", sorted(set(names.places))),
    ):
        if values:
            arg_properties[key] = {"type": "string", "enum": values}
    return {
        "type": "object",
        "properties": {
            "interpretation_ko": {"type": "string"},
            "clarify": {"type": ["string", "null"]},
            "quantity": {
                "type": ["object", "null"],
                "properties": {
                    "value": {"type": "integer"},
                    "basis": {"type": "string", "enum": ["carry", "time", "purpose", "user", "default"]},
                    "cites": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["value", "basis"],
            },
            "assumptions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "cites": {"type": "array", "items": {"type": "string"}},
                        "hypothesis": {"type": "boolean"},
                    },
                    "required": ["text", "hypothesis"],
                },
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "skill": {"type": "string", "enum": skill_enum},
                        "args": {"type": "object", "properties": arg_properties},
                        "after": {"type": "array", "items": {"type": "string"}},
                        "budget_s": {"type": "integer"},
                        "cites": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "skill", "args"],
                },
            },
            "abort_if": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cond": {"type": "string", "enum": ["hp_below", "dusk", "night"]},
                        "value": {
                            "type": ["number", "null"],
                            "description": tr(
                                "hp_below: 남은 체력 비율(0~1). 0.3 = 체력 30% 아래에서 멈춤",
                                "hp_below: fraction of health left (0-1). 0.3 = stop below 30% health",
                            ),
                        },
                    },
                    "required": ["cond"],
                },
            },
            "speech_gist_ko": {"type": "string"},
            "think_again_after": {"type": "boolean"},
        },
        "required": ["interpretation_ko", "steps", "speech_gist_ko"],
    }
