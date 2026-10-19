from __future__ import annotations

import json
from typing import Any

import pytest

from thorkell.models.gemini import Usage
from thorkell.plan.planner import Planner, PlanRejected, context_from_scene
from thorkell.plan.quantity import gather_feasible
from thorkell.plan.schema import Names, Plan, plan_schema
from thorkell.plan.validate import Context, validate

SCENE = {
    "inventory": [
        {"name": "돌도끼", "stack": 1, "weight": 2.0, "equipped": False},
        {"name": "나무", "stack": 4, "weight": 8.0, "equipped": False},
        {"name": "라즈베리", "stack": 3, "weight": 0.3, "equipped": False, "food": {"health": 7}},
    ],
    "weight": 10.3,
    "weight_max": 300,
    "env": {"night": False, "day_fraction": 0.5},
}


def test_feasible_uses_only_known_bounds() -> None:
    feasible = gather_feasible(SCENE, "나무", rate_per_min=None)
    assert feasible.max == 144  # (300-10.3)//2
    assert feasible.unknown == ("gathering rate",)
    timed = gather_feasible(SCENE, "나무", rate_per_min=6.0)
    assert timed.max == 45  # 7.5 min to dusk * 6/min
    assert "time <= 45" in timed.describe()


def test_feasible_unknown_weight_and_night() -> None:
    scene = {**SCENE, "env": {"night": True}}
    feasible = gather_feasible(scene, "구리", rate_per_min=None)
    assert feasible.max == 0
    assert "unit weight" in feasible.unknown


def plan(**overrides: Any) -> Plan:
    base: dict[str, Any] = {
        "interpretation_ko": "나무를 모아 달라는 뜻",
        "quantity": {"value": 20, "basis": "purpose", "cites": []},
        "steps": [
            {"id": "s1", "skill": "equip", "args": {"item": "돌도끼"}},
            {"id": "s2", "skill": "gather_wood", "args": {"count": 20}, "after": ["s1"]},
        ],
        "speech_gist_ko": "20개쯤 해 올게",
    }
    base.update(overrides)
    return Plan.model_validate(base)


CONTEXT = context_from_scene(SCENE, feasible=gather_feasible(SCENE, "나무", rate_per_min=6.0))


def test_good_plan_passes() -> None:
    assert validate(plan(), CONTEXT) == []


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"steps": [{"id": "s1", "skill": "equip", "args": {"item": "청동도끼"}}]}, "not in the inventory"),
        ({"steps": [{"id": "s1", "skill": "fly", "args": {}}]}, "unknown skill"),
        ({"steps": [{"id": "s1", "skill": "gather_wood", "args": {}}]}, "needs count"),
        (
            {"steps": [{"id": "s1", "skill": "gather_wood", "args": {"count": 20}, "after": ["s9"]}]},
            "does not come before",
        ),
        (
            {
                "steps": [
                    {"id": "s1", "skill": "follow", "args": {}},
                    {"id": "s2", "skill": "gather_wood", "args": {"count": 20}},
                ]
            },
            "never ends",
        ),
        (
            {
                "quantity": {"value": 80, "basis": "purpose"},
                "steps": [{"id": "s1", "skill": "gather_wood", "args": {"count": 80}}],
            },
            "exceeds what is feasible",
        ),
        (
            {
                "quantity": {"value": 20, "basis": "purpose"},
                "steps": [{"id": "s1", "skill": "gather_wood", "args": {"count": 5}}],
            },
            "do not add up",
        ),
        ({"steps": [{"id": "s1", "skill": "eat", "args": {"item": "돌도끼"}}]}, "not known to be food"),
        # 실제 Flash가 체력 10(점수)을 넣어서, 비율(1.0) < 10이 늘 참이 되어 계획이 바로 취소됐다.
        ({"abort_if": [{"cond": "hp_below", "value": 10.0}]}, "hp_below needs a health fraction"),
        ({"abort_if": [{"cond": "hp_below"}]}, "hp_below needs a health fraction"),
        # 범위는 스키마가 아니라 여기서 본다(스키마에 넣으면 Gemini가 400을 냈다).
        ({"steps": [{"id": "s1", "skill": "gather_wood", "args": {"count": 0}}]}, "count must be 1-500"),
        ({"steps": [{"id": "s1", "skill": "wait", "args": {"seconds": 900}}]}, "seconds must be 1-600"),
    ],
)
def test_bad_plans_are_rejected(overrides: dict[str, Any], fragment: str) -> None:
    problems = validate(plan(**overrides), CONTEXT)
    assert any(fragment in p for p in problems), problems


def test_user_quantity_may_exceed_feasible() -> None:
    p = plan(
        quantity={"value": 80, "basis": "user"},
        steps=[{"id": "s1", "skill": "gather_wood", "args": {"count": 80}}],
    )
    assert validate(p, CONTEXT) == []


def test_clarifying_plan_has_no_steps() -> None:
    assert validate(plan(clarify="보스 잡으러 지금 갈까?", steps=[]), CONTEXT) == []
    assert any("must not contain steps" in p for p in validate(plan(clarify="?"), CONTEXT))


def test_schema_stays_within_what_gemini_accepts() -> None:
    # 실제 gemini-3.8-flash가 메뉴 이름 enum + 숫자 범위 + 설명이 다 있는 스키마를 400("invalid argument")으로
    # 거절했다(2026-10-17). 범위는 검증기가 본다. 스키마에는 범위를 넣지 않는다.
    text = json.dumps(plan_schema(Names(items=tuple(f"i{n}" for n in range(30)))))
    assert '"minimum"' not in text and '"maximum"' not in text and '"maxItems"' not in text


def test_schema_enums_only_discovered_items() -> None:
    schema = plan_schema(Names(items=("돌도끼", "라즈베리")))
    args = schema["properties"]["steps"]["items"]["properties"]["args"]["properties"]
    assert args["item"]["enum"] == ["돌도끼", "라즈베리"]
    empty = plan_schema(Names())["properties"]["steps"]["items"]["properties"]["args"]["properties"]
    assert "item" not in empty and "piece" not in empty and "place" not in empty


class ScriptedModel:
    def __init__(self, *responses: dict[str, Any]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.schemas: list[dict[str, Any]] = []

    async def generate_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        self.prompts.append(prompt)
        self.schemas.append(schema)
        return self.responses.pop(0), Usage(input_tokens=100, output_tokens=50)


GOOD = plan().model_dump()


async def test_planner_returns_valid_plan() -> None:
    model = ScriptedModel(GOOD)
    result = await Planner(model).plan("나무 좀 해줘", "SELF hp 25/25", CONTEXT)
    assert result.quantity is not None and result.quantity.value == 20
    assert "[가능한 최대 수량]" in model.prompts[0]
    assert model.schemas[0]["properties"]["steps"]["items"]["properties"]["args"]["properties"]["item"][
        "enum"
    ] == [
        "나무",
        "돌도끼",
        "라즈베리",
    ]


async def test_planner_repairs_once_with_problems() -> None:
    bad = {**GOOD, "steps": [{"id": "s1", "skill": "equip", "args": {"item": "청동도끼"}}]}
    model = ScriptedModel(bad, GOOD)
    result = await Planner(model).plan("나무 좀 해줘", "s", CONTEXT)
    assert result.steps[0].args["item"] == "돌도끼"
    assert "청동도끼 is not in the inventory" in model.prompts[1]


async def test_planner_gives_up_after_second_rejection() -> None:
    bad = {**GOOD, "steps": [{"id": "s1", "skill": "equip", "args": {"item": "청동도끼"}}]}
    model = ScriptedModel(bad, bad)
    with pytest.raises(PlanRejected) as error:
        await Planner(model).plan("나무 좀 해줘", "s", CONTEXT)
    assert "청동도끼" in str(error.value)


def test_context_marks_food_and_inventory() -> None:
    assert CONTEXT.edible == frozenset({"라즈베리"})
    assert "돌도끼" in CONTEXT.inventory
    assert isinstance(CONTEXT, Context)


def test_schema_says_hp_below_is_a_fraction() -> None:
    # 범위(0~1) 자체는 검증기가 본다(test_bad_plans_are_rejected). 스키마는 설명으로 알려 준다.
    value = plan_schema(Names())["properties"]["abort_if"]["items"]["properties"]["value"]
    assert "0~1" in value["description"]


def test_talk_only_plan_is_fine_but_an_empty_one_is_not() -> None:
    # 인사·잡담에는 단계 없이 말로만 답한다. 말도 없고 질문도 없는 빈 계획은 거절한다.
    assert validate(plan(steps=[], speech_gist_ko="안녕! 나 여기 있어."), CONTEXT) == []
    assert any("no steps" in p for p in validate(plan(steps=[], speech_gist_ko=""), CONTEXT))


NAMED = context_from_scene(
    SCENE,
    recipes=[{"name": "망치", "resources": [{"name": "나무", "amount": 3}, {"name": "돌", "amount": 2}]}],
    pieces=[{"name": "작업대", "resources": [{"name": "나무", "amount": 10}]}],
    places=["작업대"],
    creatures=["사슴"],
    request="멧돼지 좀 잡아와",
)


def step(skill: str, **args: Any) -> dict[str, Any]:
    return {"id": f"s-{skill}", "skill": skill, "args": args}


@pytest.mark.parametrize(
    ("steps", "fragment"),
    [
        ([step("craft", item="활", count=1)], "not in the crafting menu"),
        ([step("hunt", creature="트롤", count=1)], "creature '트롤' has not been shown"),
        ([step("go_to", place="제단")], "place '제단' is not remembered"),
        ([step("give", item="활", count=1)], "not in the inventory"),
        ([step("build", piece="성벽")], "building '성벽' has not been shown"),
    ],
)
def test_names_must_come_from_the_game_or_the_leader(steps: list[dict[str, Any]], fragment: str) -> None:
    problems = validate(plan(quantity=None, steps=steps), NAMED)
    assert any(fragment in p for p in problems), problems


def test_a_creature_the_leader_named_may_be_searched_for_and_hunted() -> None:
    steps = [step("search", name="멧돼지"), {**step("hunt", creature="멧돼지", count=1), "id": "s2"}]
    assert validate(plan(quantity=None, steps=steps), NAMED) == []
    known = [step("craft", item="망치", count=1), {**step("build", piece="작업대"), "id": "s2"}]
    assert validate(plan(quantity=None, steps=known), NAMED) == []


def test_an_uncited_assumption_is_kept_as_a_hypothesis_not_rejected() -> None:
    # 실제 Flash: "가방의 라즈베리는 먹을 수 있다"를 근거 없이 사실로 적었다. 계획은 멀쩡하다.
    p = plan(assumptions=[{"text": "라즈베리는 먹을 수 있다", "hypothesis": False}])
    assert validate(p, CONTEXT) == []
    assert p.assumptions[0].hypothesis is True


def test_count_may_be_left_out_where_one_is_the_natural_amount() -> None:
    steps = [step("craft", item="망치"), {**step("hunt", creature="사슴"), "id": "s2"}]
    assert validate(plan(quantity=None, steps=steps), NAMED) == []


def test_an_assumption_citing_what_it_saw_instead_of_a_fact_id_is_a_hypothesis() -> None:
    # 실제 Flash는 사실 id 대신 "보이는 것: 라즈베리 덤불"을 근거로 적었다. 거절하지 않고 가설로 둔다.
    p = plan(
        assumptions=[
            {"text": "덤불에서 먹을 게 나온다", "cites": ["보이는 것: 라즈베리 덤불"], "hypothesis": False}
        ]
    )
    assert validate(p, CONTEXT) == []
    assert p.assumptions[0].hypothesis and p.assumptions[0].cites == []


def test_a_step_may_use_what_an_earlier_step_gets() -> None:
    # 실게임(2026-10-19): 먹을 것 부탁에 버섯을 따서 건네는 계획을, 버섯이 아직 가방에 없다고 거절했다.
    context = context_from_scene(SCENE, items=["버섯"], request="배고파. 먹을 것 좀 구해 와")
    shared = plan(
        steps=[
            {"id": "s1", "skill": "gather", "args": {"item": "버섯", "count": 3}},
            {"id": "s2", "skill": "go_to_leader", "args": {}, "after": ["s1"]},
            {"id": "s3", "skill": "give", "args": {"item": "버섯", "count": 2}, "after": ["s2"]},
            {"id": "s4", "skill": "eat", "args": {"item": "버섯"}, "after": ["s3"]},
        ],
        quantity=None,
    )
    assert validate(shared, context) == []
    # 아무 단계도 가져오지 않는 것은 여전히 안 된다.
    handed = plan(steps=[{"id": "s1", "skill": "give", "args": {"item": "버섯", "count": 1}}], quantity=None)
    assert validate(handed, context) == ["s1: 버섯 is not in the inventory"]


def test_wood_from_a_chopping_step_can_be_handed_over() -> None:
    context = context_from_scene(SCENE, request="나무 20개 해 줘")
    chopped = plan(
        steps=[
            {"id": "s1", "skill": "gather_wood", "args": {"count": 20}},
            {"id": "s2", "skill": "give", "args": {"item": "나무", "count": 20}, "after": ["s1"]},
        ],
        quantity=None,
    )
    assert validate(chopped, context) == []
