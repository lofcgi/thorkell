"""The first boss in the simulator: offering at the altar, deciding how to fight what comes out, and
learning from how it went. The judgment here is a stand-in model (JudgmentModel); `thorkell judge` asks
the real one."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from typing import Any

from conftest import JudgmentModel, Rig, reflection, tactic

from thorkell.control.goals import Goal, Tier
from thorkell.mind.mind import Mind
from thorkell.mind.store import Store
from thorkell.plan.tactics import Tactician
from thorkell.sim.world import SimEntity, SimWorld, eikthyr


def arena() -> SimWorld:
    world = SimWorld([SimEntity("7:500", "altar", "신비한 제단", 4.0, 0.0)])
    world.bot.inventory = {"사슴 트로피": 2, "활": 1, "나무 화살": 80, "곤봉": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.hp_max = world.bot.hp = 60.0
    return world


def thinking(model: JudgmentModel) -> dict[str, Any]:
    return {"tactician": Tactician(model), "mind": Mind(Store())}


def fight_ended(rig: Rig, count: int = 1) -> bool:
    return (
        sum(d.kind in ("done", "fail") and d.goal_kind == "fight" for d in rig.controller.decisions) >= count
    )


async def test_offers_trophies_then_decides_how_to_fight_what_comes_out(make_rig: Callable[..., Any]) -> None:
    model = JudgmentModel([tactic()], [reflection()])
    world = arena()
    world.bot.inventory.update({"구운 고기": 2, "버섯": 2})
    rig: Rig = await make_rig(world=world, time_scale=2, **thinking(model))
    rig.controller.stance = "wait"
    rig.controller.request(Goal("offer", Tier.USER, {"item": "사슴 트로피"}, source="leader"))
    await rig.until(lambda: any(e.name == "에이크쉬르" for e in rig.world.entities.values()), 30)
    assert "제단에 올렸어! 뭔가 온다, 준비해!" in rig.said()
    # 이 시험은 싸움의 흐름만 본다. 보스 체력(500)을 다 깎는 동안 번개에 지지 않게 줄이고 느리게 한다.
    boss = next(e for e in rig.world.entities.values() if e.name == "에이크쉬르")
    boss.hp = boss.max_hp = 150.0
    boss.speed = 2.5
    # 시키지 않아도 알아챈 큰 것 앞에서 생각한다. 무엇으로 보이는지는 사람이 화면에서 보는 것으로 판단한다.
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    seen = model.prompts["tactic"][0]
    assert "키 약 3m" in seen and "화면 위쪽에 큰 체력바와 이름이 떴다" in seen
    assert "large" not in seen and "$enemy" not in seen
    await rig.until(lambda: "보스 같아! 멀리서 활로 쏠게" in rig.said(), 10)
    # 먹고 싸우기로 했으니(eat_first) 빈 음식 칸을 채운다.
    await rig.until(lambda: set(rig.world.bot.foods) == {"라즈베리", "구운 고기", "버섯"}, 20)
    await rig.until(lambda: not any(e.name == "에이크쉬르" for e in rig.world.entities.values()), 120)
    assert not rig.world.bot.dead
    assert rig.world.bot.inventory["나무 화살"] < 80
    await rig.until(lambda: rig.world.bot.inventory.get("에이크쉬르 트로피", 0) == 1, 60)
    # 기록의 음식 칸은 먹고 나서 싸움에 들어갈 때의 것이다. 실게임에서 먹기 전 1칸만 적혀 있어
    # "1칸만 채우지 말자"는 틀린 교훈이 나왔다(2026-10-18).
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 10)
    assert store.episodes("에이크쉬르")[0].record["food_slots"] == 3


async def test_a_wrong_offering_is_explained_in_the_games_words(make_rig: Callable[..., Any]) -> None:
    world = arena()
    world.bot.inventory = {"사슴 트로피": 1}
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("offer", Tier.USER, {"item": "사슴 트로피"}, source="leader"))
    await rig.until(lambda: any("안 받아" in text for text in rig.said()), 20)


async def test_without_a_judgment_model_it_says_so_instead_of_fighting(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig(world=arena(), time_scale=4)
    rig.controller.stance = "wait"
    rig.world.spawn(eikthyr(30.0, 0.0))
    await rig.until(lambda: any("판단 모델이 꺼져 있어" in text for text in rig.said()), 20)
    assert rig.world.bot.inventory["나무 화살"] == 80


async def test_a_lesson_from_one_fight_changes_the_next(make_rig: Callable[..., Any]) -> None:
    # 첫 싸움은 가까이(12m)에서 쏘다가 번개(18m까지 닿음)를 맞는다. 돌아보고 교훈을 남긴다.
    # 다음 싸움은 그 교훈을 떠올려 멀리서 쏘고, 덜 맞았으니 교훈이 맞았다고 기록한다.
    lesson = "에이크쉬르는 18m 안에서 번개를 쏜다. 25m 밖에서 쏘자"
    model = JudgmentModel(
        [tactic(keep_m=12.0, close_m=6.0, eat_first=False), tactic(keep_m=26.0, close_m=19.0, cites=["L1"])],
        [
            reflection(lessons=[{"about": "에이크쉬르", "text_ko": lesson}], speech_ko="번개를 너무 맞았어"),
            reflection(verdicts=[{"lesson_id": "L1", "held": True, "why_ko": "멀리서는 안 맞았다"}]),
        ],
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    store = rig.controller.mind.store  # type: ignore[union-attr]
    for attempt in (1, 2):
        boss = eikthyr(36.0, 0.0, id=f"7:99{attempt}")
        boss.hp, boss.max_hp, boss.speed = 120.0, 120.0, 2.5
        rig.world.spawn(boss)
        rig.controller.request(Goal("fight", Tier.USER, {"creature": "에이크쉬르"}, source="leader"))
        await rig.until(lambda attempt=attempt: fight_ended(rig, attempt), 120)
        await rig.until(lambda attempt=attempt: len(model.prompts["reflection"]) == attempt, 10)
        await rig.until(lambda: rig.controller._reflection is None, 10)
    first, second = store.episodes("에이크쉬르")
    lightning = [[hit for hit in e.record["hits"] if "lightning" in hit[3]] for e in (first, second)]
    assert len(lightning[0]) >= 2 and len(lightning[1]) < len(lightning[0])
    # 두 번째 판단에는 첫 싸움의 기록과 교훈이 들어간다.
    assert "E1 (killed" in model.prompts["tactic"][1] and lesson in model.prompts["tactic"][1]
    assert "번개" in model.prompts["reflection"][0] and "12m" in model.prompts["reflection"][0]
    learned = store.lesson("L1")
    assert learned is not None and learned.status == "supported" and learned.learned_from == "E1"
    assert "번개를 너무 맞았어" in rig.said()


async def test_after_dying_to_a_boss_it_decides_how_to_get_its_things_back(
    make_rig: Callable[..., Any],
) -> None:
    # 실게임(2026-10-17): 에이크쉬르에게 죽고 혼자 묘비를 찾으러 갔다가 세 번 더 죽었다.
    # 이제 죽으면 돌아보고, 같이 가기로 했으면 리더가 묘비 곁에 갈 때까지 기다린다.
    model = JudgmentModel(
        [tactic()],
        [reflection(after_death="with_leader", speech_ko="한 방에 죽었어. 혼자 가면 또 당하니 같이 가자")],
    )
    world = SimWorld([], leader_at=(2.0, 0.0))
    world.bot.inventory = {"돌도끼": 1}
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.x, world.bot.z = 80.0, 5.0
    world.bot.hp = 1.0
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    rig.world.spawn(eikthyr(81.0, 5.0))
    await rig.until(lambda: any("같이 가자" in text for text in rig.said()), 30)
    tomb = next(e for e in rig.world.entities.values() if e.kind == "tombstone")
    record = model.prompts["reflection"][0]
    assert "에이크쉬르" in record and "died" in record
    # 보스가 묘비 곁에 있는 동안 혼자 가지 않는다.
    await asyncio.sleep(3.0)
    assert math.hypot(rig.world.bot.x - tomb.x, rig.world.bot.z - tomb.z) > 20
    # 보스가 떠나고 리더가 묘비 곁으로 가면 같이 가서 되찾는다.
    del rig.world.entities["7:990"]
    rig.world.leader = (tomb.x - 3.0, tomb.z)
    await rig.until(lambda: rig.world.bot.inventory.get("돌도끼", 0) == 1, 60)


async def test_when_the_leader_summons_the_boss_it_joins_the_fight_from_range(
    make_rig: Callable[..., Any],
) -> None:
    # 사람이 직접 제단에 바치면 토르켈은 시키지 않아도 생각한 뒤 싸움에 합류한다. 반사처럼 달려들지 않는다.
    model = JudgmentModel([tactic()], [reflection()])
    world = arena()
    world.bot.inventory.update({"구운 고기": 2, "버섯": 2})
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: any(d.kind == "adopt" for d in rig.controller.decisions), 20)
    adopted = [d.goal_kind for d in rig.controller.decisions if d.kind == "adopt"]
    assert "fight" in adopted and "defend" not in adopted
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 30)


async def test_falling_back_leans_toward_the_leader(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 거리를 두기로 하고 "이쪽으로 빨리 와!"라고 외친 뒤 리더 반대쪽으로 230m를 달려
    # 검은 숲에서 죽었다. 사람은 도와줄 사람 쪽으로 물러난다.
    model = JudgmentModel(
        [tactic(style="keep_away", keep_m=25.0, close_m=12.0, eat_first=False)],
        [reflection(after_death="with_leader")],
    )
    world = SimWorld([], leader_at=(0.0, 60.0))
    world.bot.inventory = {"곤봉": 1}
    world.bot.foods = {"라즈베리": 1200.0}
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: math.hypot(rig.world.bot.x, rig.world.bot.z) >= 15, 30)
    # 곧장 물러나면 서쪽(z≈0)으로 가서 리더(북쪽 60m)와 멀어진다.
    assert rig.world.bot.z > 5
    assert math.hypot(rig.world.bot.x - 0.0, rig.world.bot.z - 60.0) < 60


async def test_it_keeps_the_fight_away_from_a_leader_who_will_not_fight(
    make_rig: Callable[..., Any],
) -> None:
    # 실게임(2026-10-18): 리더 쪽으로 물러나다 싸우지 않는 리더에게 보스를 끌고 가 리더가 죽었다.
    # 리더 쪽으로 갈지는 판단이다. 리더가 한 말을 듣고 모델이 정한다.
    model = JudgmentModel(
        [tactic(style="keep_away", keep_m=25.0, close_m=12.0, eat_first=False, retreat_to_leader=False)],
        [reflection(after_death="with_leader")],
    )
    world = SimWorld([], leader_at=(0.0, 60.0))
    world.bot.inventory = {"곤봉": 1}
    world.bot.foods = {"라즈베리": 1200.0}
    rig: Rig = await make_rig(world=world, time_scale=4, leader_chat_via_host=True, **thinking(model))
    rig.controller.stance = "wait"
    await rig.controller.hear_leader("나는 싸움 못 해. 멀리서 볼게")
    rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: math.hypot(rig.world.bot.x, rig.world.bot.z) >= 15, 30)
    assert abs(rig.world.bot.z) < 3
    asked = model.prompts["tactic"][0]
    assert "리더가 최근에 한 말" in asked and "나는 싸움 못 해. 멀리서 볼게" in asked


async def test_losing_sight_of_the_boss_is_not_a_win(make_rig: Callable[..., Any]) -> None:
    # 실게임: 보스가 언덕 너머로 안 보이자 20초 뒤 "해치운 것 같아!"라고 했다. 서버는 살아 있다고 했다.
    model = JudgmentModel([tactic()], [reflection()])
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: boss.hp < boss.max_hp, 30)
    # 보스가 멀리 가 버린다(시야 밖). 쓰러지는 걸 못 봤으니 이긴 게 아니다.
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    await rig.until(lambda: fight_ended(rig), 120)
    assert not any("해치운" in text for text in rig.said())
    assert any(d.kind == "fail" and d.goal_kind == "fight" for d in rig.controller.decisions)
    await rig.until(lambda: rig.controller.mind.store.episodes("에이크쉬르") != [], 10)  # type: ignore[union-attr]
    assert rig.controller.mind.store.episodes("에이크쉬르")[0].outcome == "lost"  # type: ignore[union-attr]
    # 끝났다고 정하면 기록부터 남기고 보고한다. 보고하는 말을 마친 뒤에 남기면 그사이 기억이 비어 있다
    # (실게임 시나리오가 그 틈에 "기록 없음"으로 실패했다).
    order = [
        d.kind
        for d in rig.controller.decisions
        if d.kind == "reflect" or (d.kind == "speak" and d.reason_ko.startswith("[report]"))
    ]
    assert order.index("reflect") < order.index("speak")


async def test_a_plan_can_eat_then_offer(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 리더의 말을 듣고 "더 먹고 제단에 바친다"는 계획을 세웠는데, 계획 실행기에 offer가
    # 없어서 계획 전체가 실패했고 음식 한 칸으로 싸웠다. 플래너가 쓸 수 있는 스킬은 모두 실행된다.
    from conftest import ScriptedModel

    from thorkell.plan.planner import Planner

    plan = {
        "interpretation_ko": "더 먹고 제단에 바치라는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [
            {"id": "s1", "skill": "eat", "args": {"item": "구운 고기"}},
            {"id": "s2", "skill": "offer", "args": {"item": "사슴 트로피"}, "after": ["s1"]},
        ],
        "abort_if": [],
        "speech_gist_ko": "든든히 먹고 올릴게!",
    }
    world = arena()
    world.bot.inventory["구운 고기"] = 2
    world.bot.known = set(world.bot.inventory)
    rig: Rig = await make_rig(world=world, planner=Planner(ScriptedModel(plan)))
    rig.controller.stance = "wait"
    rig.world.leader_says("먹고 제단에 트로피 올려 줘")
    await rig.until(lambda: "제단에 올렸어! 뭔가 온다, 준비해!" in rig.said(), 30)
    assert "구운 고기" in rig.world.bot.foods
    assert not any("no runner" in d.reason_ko for d in rig.controller.decisions)


def test_every_skill_the_planner_may_use_has_a_runner() -> None:
    from thorkell.control.plan_skills import DIRECT_STEPS, SKILLS
    from thorkell.plan.schema import SKILL_CATALOG

    assert set(SKILL_CATALOG) <= set(DIRECT_STEPS) | set(SKILLS)


async def test_time_spent_backing_off_to_heal_is_remembered(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 141초 중 대부분을 체력 50% 아래라 물러나 있느라 화살을 3발밖에 못 쐈다.
    # 그 시간이 기록에 없어서 회고에서 돌아볼 수 없었다.
    model = JudgmentModel(
        [tactic(eat_first=False, retreat_hp=0.5, return_hp=0.9)], [reflection(after_death="with_leader")]
    )
    world = arena()
    world.bot.hp = 28.0
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = rig.world.spawn(eikthyr(30.0, 0.0))
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    await asyncio.sleep(2.0)
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    await rig.until(lambda: fight_ended(rig), 60)
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 10)
    record = store.episodes("에이크쉬르")[0].record
    assert record["retreats"] >= 1 and record["recovering_s"] > 0


async def test_a_fight_in_the_plan_is_not_started_twice(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 계획 단계로 싸우는 중에 큰 것을 알아채 같은 상대와의 싸움을 또 세웠다.
    # 생각(모델 호출)을 두 번 했고, 계획이 끊겼다. 이미 그 상대와 싸우고 있으면 새로 세우지 않는다.
    from conftest import ScriptedModel

    from thorkell.plan.planner import Planner

    plan = {
        "interpretation_ko": "에이크쉬르를 잡자는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [{"id": "s1", "skill": "fight", "args": {"creature": "에이크쉬르"}}],
        "abort_if": [],
        "speech_gist_ko": "좋아, 해 볼게!",
    }
    model = JudgmentModel([tactic(), tactic()], [reflection(after_death="with_leader")])
    rig: Rig = await make_rig(
        world=arena(), time_scale=4, planner=Planner(ScriptedModel(plan)), **thinking(model)
    )
    rig.controller.stance = "wait"
    boss = eikthyr(50.0, 0.0)
    boss.hostile = False
    rig.world.spawn(boss)
    rig.world.leader_says("에이크쉬르 잡아 봐")

    def planned_fight() -> bool:
        active = rig.controller.active
        return active is not None and active.goal.kind == "request" and "plan" in active.goal.progress

    await rig.until(planned_fight, 20)
    # 계획 속 싸움이 상대를 찾는 사이 상대가 다가와 나를 알아챈다(큰 것이 알아챔 → 생각할 때).
    boss.x, boss.hostile, boss.provoked = 30.0, True, True
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 78, 30)
    assert len(model.prompts["tactic"]) == 1
    assert not any(d.kind == "suspend" for d in rig.controller.decisions)


async def test_a_fight_in_a_plan_follows_its_tactic_and_is_remembered(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 토르켈이 스스로 세운 계획(먹기→바치기→싸우기)의 싸움이 계획의 중단 조건
    # (체력 50% 아래)에 끊겼다. 그 싸움은 기록도 남지 않았다(회고는 맨 위 싸움 목표만 했다).
    # 싸움의 체력 판단은 전술(물러날 체력)이 하고, 계획으로 한 싸움도 기억에 남는다.
    from conftest import ScriptedModel

    from thorkell.plan.planner import Planner

    plan = {
        "interpretation_ko": "에이크쉬르를 잡자는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [{"id": "s1", "skill": "fight", "args": {"creature": "에이크쉬르"}}],
        "abort_if": [{"cond": "hp_below", "value": 0.6}],
        "speech_gist_ko": "좋아, 해 볼게!",
    }
    model = JudgmentModel([tactic(retreat_hp=0.2, return_hp=0.5)], [reflection(after_death="with_leader")])
    world = arena()
    world.bot.hp = 30.0
    # 싸움이 안 끝나고 상대를 놓치면(안 된 단계) 다시 생각한다. 그때는 리더에게 말만 한다.
    after = {**plan, "steps": [], "abort_if": [], "speech_gist_ko": "놓쳤어. 준비하고 다시 하자"}
    rig: Rig = await make_rig(
        world=world, time_scale=4, planner=Planner(ScriptedModel(plan, after)), **thinking(model)
    )
    rig.controller.stance = "wait"
    boss = eikthyr(50.0, 0.0)
    boss.hostile = False
    rig.world.spawn(boss)
    rig.world.leader_says("에이크쉬르 잡아 봐")

    def planned_fight() -> bool:
        active = rig.controller.active
        return active is not None and active.goal.kind == "request" and "plan" in active.goal.progress

    await rig.until(planned_fight, 20)
    boss.x, boss.hostile, boss.provoked = 30.0, True, True
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 78, 30)
    assert not any("많이 다쳐서" in text for text in rig.said())
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 60)
    await rig.until(lambda: bool(model.prompts["reflection"]), 10)
    assert store.episodes("에이크쉬르")[0].outcome == "lost"


async def test_it_rolls_away_even_while_backing_off_to_heal(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 체력이 낮아 물러나는 중에는 3m까지 다가와도 구르지 않고 달리기만 하다 뿔에 맞았다.
    # 물러나는 중에도 공격 동작이 보이면(정한 거리 안) 구른다.
    model = JudgmentModel(
        [tactic(eat_first=False, retreat_hp=0.6, return_hp=1.0, dodge_within_m=10.0)],
        [reflection(after_death="with_leader")],
    )
    world = arena()
    world.bot.hp = 25.0
    world.bot.foods = {}  # 이 시험 동안 체력이 다시 차서 물러나기가 끝나지 않게
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    await asyncio.sleep(0.5)
    boss.x, boss.z = rig.world.bot.x + 6.0, rig.world.bot.z  # 바짝 붙었다(구를 거리 14m 안)
    await rig.until(lambda: rig.world.dodges >= 1, 5)
    assert rig.world.bot.hp < rig.world.bot.hp_max


async def test_my_health_over_the_fight_is_remembered(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 물러나 있던 33초 동안 체력이 7.5에서 8.5로 1 올랐다. 기록에 최저 체력만 있어서
    # 회복이 거의 안 된다는 것을 못 보고 "더 멀리 도망치자"고 배웠다. 사람은 체력바가 안 차는 것을 본다.
    model = JudgmentModel([tactic(eat_first=False)], [reflection(after_death="with_leader")])
    world = arena()
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = rig.world.spawn(eikthyr(20.0, 0.0))
    await rig.until(lambda: rig.world.bot.hp < 50, 30)
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 60)
    trace = store.episodes("에이크쉬르")[0].record["my_health"]
    lowest = min(range(len(trace)), key=lambda i: trace[i][1])
    assert trace[lowest][1] < 0.9 and trace[-1][1] > trace[lowest][1]  # 줄었다가 다시 차는 것까지 보인다


async def test_a_small_attacker_does_not_pause_a_boss_fight_from_a_plan(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 계획으로 하던 보스 싸움이 회색 난쟁이에게 맞자 방어(생존) 목표에 밀려 보류됐고,
    # 그대로 죽어 보스 싸움이 기억에 안 남았다. 맨 위 싸움처럼 계획의 싸움도 생존 목표에 밀리지 않는다.
    from conftest import ScriptedModel

    from thorkell.plan.planner import Planner
    from thorkell.sim.world import greydwarf

    plan = {
        "interpretation_ko": "에이크쉬르를 잡자는 뜻",
        "quantity": None,
        "assumptions": [],
        "steps": [{"id": "s1", "skill": "fight", "args": {"creature": "에이크쉬르"}}],
        "abort_if": [],
        "speech_gist_ko": "좋아, 해 볼게!",
    }
    model = JudgmentModel([tactic(), tactic()], [reflection(after_death="with_leader")])
    rig: Rig = await make_rig(
        world=arena(), time_scale=4, planner=Planner(ScriptedModel(plan)), **thinking(model)
    )
    rig.controller.stance = "wait"
    boss = eikthyr(50.0, 0.0)
    boss.hostile = False
    rig.world.spawn(boss)
    rig.world.leader_says("에이크쉬르 잡아 봐")

    def planned_fight() -> bool:
        active = rig.controller.active
        return active is not None and active.goal.kind == "request" and "plan" in active.goal.progress

    await rig.until(planned_fight, 20)
    boss.x, boss.hostile, boss.provoked = 30.0, True, True
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 78, 30)
    rig.world.spawn(greydwarf(rig.world.bot.x + 1.5, rig.world.bot.z, id="7:901"))
    await rig.until(lambda: rig.world.bot.hp < rig.world.bot.hp_max - 1, 20)
    await asyncio.sleep(2.0)
    assert not any(d.kind == "suspend" for d in rig.controller.decisions)


async def test_a_creature_that_joins_the_fight_is_dealt_with_and_remembered(
    make_rig: Callable[..., Any],
) -> None:
    # 실게임(2026-10-18): 보스와 싸우는 동안 멧돼지에게 8번 맞아 52%에서 0%가 됐다. 싸움 기록에는 보스에게
    # 맞은 것만 남아 "보스의 맹공"으로 회고했다. 사람은 끼어든 놈을 먼저 처리하고, 그 일을 기억한다.
    from thorkell.sim.world import greydwarf

    model = JudgmentModel([tactic(eat_first=False)], [reflection(after_death="with_leader")])
    world = arena()
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(30.0, 0.0)
    boss.speed = 1.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 20)
    add = greydwarf(rig.world.bot.x - 1.5, rig.world.bot.z, id="7:901")
    rig.world.spawn(add)
    await rig.until(lambda: "7:901" not in rig.world.entities or add.hp < add.max_hp, 30)
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 60)
    record = store.episodes("에이크쉬르")[0].record
    assert any(hit[2] == "그레이드워프" for hit in record["others"])
    assert "그레이드워프" in record["handled"]


async def test_seeing_the_boss_wind_up_it_rolls_aside(make_rig: Callable[..., Any]) -> None:
    # 사람은 보스가 몸을 젖히는 것(공격 동작)을 보고 구른다. 몇 m 안에서 구를지는 겪은 것으로 정한다
    # (교훈: 번개는 26m까지 닿는다). 활을 당기는 중이어도 구른다.
    model = JudgmentModel(
        [tactic(eat_first=False, keep_m=16.0, close_m=6.0, dodge_within_m=25.0)],
        [reflection(after_death="with_leader")],
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(17.0, 0.0)
    boss.speed = 0.5
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.dodges >= 2, 30)
    boss.x, boss.z, boss.hostile, boss.provoked = 300.0, 300.0, False, False
    store = rig.controller.mind.store  # type: ignore[union-attr]
    await rig.until(lambda: store.episodes("에이크쉬르") != [], 60)
    record = store.episodes("에이크쉬르")[0].record
    assert record["dodged"] >= 2 and record["saw_attacks"] >= record["dodged"]
    # 무엇을 하며 시간을 썼는지도 남는다(실게임: 160초 동안 화살을 몇 발 못 쐈는데 어디에 썼는지 몰랐다).
    assert record["time"]["roll"][0] == record["dodged"] and record["time"]["shoot"][0] >= 1


async def test_close_by_it_backs_off_without_rolling_every_time(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18): 구를 거리(20m) 안이면 매번 구르고 물러나느라 183초 중 구르기 36번 35초, 물러나기
    # 98초, 쏘기 8초였다. 가까우면 물러나고, 구르기는 공격 동작이 보일 때만 한다.
    model = JudgmentModel(
        [tactic(eat_first=False, keep_m=24.0, close_m=14.0, dodge_within_m=0.0)],
        [reflection(after_death="with_leader")],
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(20.0, 0.0)
    rig.world.spawn(boss)
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    for _ in range(6):
        boss.x, boss.z = rig.world.bot.x + 8.0, rig.world.bot.z
        await asyncio.sleep(0.5)
    assert rig.world.dodges == 0


async def test_a_big_creature_is_seen_from_far_away(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18, 같이 싸우기): 보스가 리더와 싸우는 37~41m에서 지각 범위(40m)를 들락날락해 못 쐈다.
    # 사람은 키 3m짜리를 40m 밖에서도 본다. 큰 것은 100m까지 보인다.
    world = arena()
    boss = eikthyr(70.0, 0.0)
    boss.aggro, boss.speed = 80.0, 0.0
    world.spawn(boss)
    rig: Rig = await make_rig(world=world, time_scale=4)
    rig.controller.stance = "wait"
    await rig.until(lambda: any(e["name"] == "에이크쉬르" for e in rig.session.nearby("creature")), 10)


async def test_a_hidden_boss_whose_bar_still_shows_is_not_lost(make_rig: Callable[..., Any]) -> None:
    # 보스가 나무 뒤로 가려져도 알아챈 보스의 체력바는 화면 위쪽에 남는다(EnemyHud). 사람은 그걸 보고
    # 놓쳤다고 하지 않고 찾으러 간다. 실게임에서는 20초 안 보이자 "놓쳤어"로 끝냈다.
    model = JudgmentModel([tactic(eat_first=False)], [reflection(after_death="with_leader")])
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(30.0, 0.0)
    boss.speed = 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 20)
    boss.hidden = True
    await rig.until(lambda: bool(rig.session.scene and rig.session.scene.data.get("boss_bars")), 5)
    await asyncio.sleep(8.0)  # 게임 시간 32초: 놓쳤다고 하는 20초를 넘긴다
    assert not fight_ended(rig)
    boss.hidden = False
    arrows = rig.world.bot.inventory["나무 화살"]
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < arrows, 20)


async def test_when_the_bow_breaks_it_thinks_again(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18, 같이 싸우기): 에이크쉬르를 2%까지 깎았는데 활이 부서졌다. 부서진 활로 41번 더
    # 쏘려다 끝났다. 사람은 "활이 부서졌어!" 하고 남은 무기로 어떻게 할지 다시 정한다.
    model = JudgmentModel(
        [
            tactic(eat_first=False),
            tactic(style="melee", keep_m=6.0, close_m=2.0, hits_then_back=3, speech_ko="몽둥이로 간다!"),
        ],
        [reflection(after_death="with_leader")],
    )
    world = arena()
    world.bot.bow_uses = 3
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.speed = 0.5
    rig.world.spawn(boss)
    await rig.until(lambda: len(model.prompts["tactic"]) == 2, 40)
    assert any("활이 부서졌어" in text for text in rig.said())
    assert "활(부서짐)" in model.prompts["tactic"][1]
    await rig.until(lambda: "몽둥이로 간다!" in rig.said(), 10)


async def test_a_fight_that_is_getting_somewhere_is_not_cut_off(
    make_rig: Callable[..., Any], monkeypatch: Any
) -> None:
    # 실게임(2026-10-18): 보스가 2%였는데 400번째 차례에 "너무 오래 싸웠어"로 끝냈다. 상대 체력이 줄고
    # 있는 동안은 계속 싸운다. 오래 아무 진척이 없을 때만 그만둔다.
    from thorkell.control import fight

    monkeypatch.setattr(fight, "STALL_S", 6.0)
    model = JudgmentModel([tactic(eat_first=False)], [reflection(after_death="with_leader")])
    world = arena()
    world.bot.inventory["나무 화살"] = 2000
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.hp = boss.max_hp = 2000.0
    boss.speed, boss.ranged_m = 0.0, 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 2000, 20)
    await asyncio.sleep(15.0)
    assert not fight_ended(rig)


async def test_a_fight_going_nowhere_is_rethought_once_then_ends(
    make_rig: Callable[..., Any], monkeypatch: Any
) -> None:
    from thorkell.control import fight

    monkeypatch.setattr(fight, "STALL_S", 6.0)
    model = JudgmentModel(
        [tactic(eat_first=False), tactic(eat_first=False, keep_m=12.0, close_m=6.0)],
        [reflection(after_death="with_leader")],
    )
    world = arena()
    world.bot.inventory["나무 화살"] = 2000
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.multipliers = {"pierce": 0.0}  # 화살이 안 통한다
    boss.speed, boss.ranged_m = 0.0, 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: fight_ended(rig), 40)
    assert any(d.kind == "fail" and "너무 오래" in d.reason_ko for d in rig.controller.decisions)
    # 그만두기 전에 한 번 다시 생각한다. 그때는 지금 싸움이 어떻게 되고 있는지를 본다(실게임 2026-10-20).
    assert "잘 안 먹히네. 다시 생각해 볼게" in rig.said()
    assert len(model.prompts["tactic"]) == 2
    assert "now (싸우는 중" in model.prompts["tactic"][1]


async def test_it_keeps_shooting_without_needless_pauses(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18, 같이 싸우기 2): 406초 중 쏘기 146초, 다가가기·물러나기 40초였고 나머지 220초는
    # 아무것도 하지 않았다. 매 차례 새 장면을 기다리고(최대 0.5초), 들고 있는 활을 매번 다시 들었다.
    model = JudgmentModel([tactic(eat_first=False)], [reflection(after_death="with_leader")])
    world = arena()
    world.bot.inventory["나무 화살"] = 500
    rig: Rig = await make_rig(world=world, time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.hp = boss.max_hp = 5000.0
    boss.speed, boss.ranged_m = 0.0, 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.commands.get("shoot", 0) >= 10, 30)
    assert rig.world.commands.get("equip", 0) <= 2


async def test_the_games_kill_message_is_a_win_even_unseen(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18, 같이 싸우기 4): 보스가 1%에서 쓰러졌는데 시체를 못 봐 "놓쳤어"라고 했다.
    # 화면 가운데 "에이크쉬르를 처치했습니다"가 떴다. 사람은 그걸 읽고 이긴 걸 안다(전리품도 줍는다).
    model = JudgmentModel([tactic(eat_first=False)], [reflection()])
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.speed, boss.ranged_m = 0.0, 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 20)
    boss.hidden, boss.hp = True, 0.1
    rig.world.hit(boss)  # 안 보이는 곳에서 마지막 한 대를 맞고 쓰러진다(시체는 못 본다)
    await rig.until(lambda: fight_ended(rig), 30)
    assert any(
        d.kind == "done" and d.goal_kind == "fight" and "해치웠어" in d.reason_ko
        for d in rig.controller.decisions
    )


async def test_no_line_of_sight_means_move_not_shoot_again(make_rig: Callable[..., Any]) -> None:
    # 실게임(2026-10-18, 같이 싸우기 4): 나무에 막혀 같은 자리에서 55번 다시 쏘려 했다. 사람은 몇 걸음 옮긴다.
    model = JudgmentModel([tactic(eat_first=False)], [reflection()])
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.speed, boss.ranged_m = 0.0, 0.0
    boss.hp = boss.max_hp = 5000.0
    rig.world.spawn(boss)
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    boss.cover_from = (rig.world.bot.x, rig.world.bot.z)
    arrows = rig.world.bot.inventory["나무 화살"]
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < arrows - 2, 20)
    assert rig.world.commands.get("shoot", 0) < 12


async def test_a_big_thing_that_is_not_a_foe_is_left_alone(
    make_rig: Callable[..., Any], monkeypatch: Any
) -> None:
    # 리허설(2026-10-18): 리더가 소환한 뿌리(크고 나를 알아챔)를 보고 코드가 싸움을 시작했고, 30초마다 다시
    # 싸움을 걸어 끝내 맨손으로 때렸다. 싸울 상대인지도 판단이다. 두기로 한 것은 다시 싸움을 걸지 않는다.
    from thorkell.control import controller as controller_module

    monkeypatch.setattr(controller_module, "FACE_RETRY_S", 1.0)
    model = JudgmentModel(
        [tactic(style="leave", speech_ko="네가 부른 거구나, 건드리지 않을게")], [reflection()]
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.stance = "wait"
    root = eikthyr(12.0, 0.0)
    root.name, root.hostile, root.speed, root.ranged_m = "소환된 뿌리", False, 0.0, 0.0
    rig.world.spawn(root)
    await rig.until(lambda: "네가 부른 거구나, 건드리지 않을게" in rig.said(), 20)
    await asyncio.sleep(3.0)
    assert len(model.prompts["tactic"]) == 1
    assert rig.world.bot.inventory["나무 화살"] == 80 and root.hp == root.max_hp


async def test_words_from_the_leader_mid_fight_change_the_plan(make_rig: Callable[..., Any]) -> None:
    # 리허설(2026-10-18): 싸우는 동안 리더의 말("내가 소환한거야", "안보여?")이 싸움이 끝날 때까지 밀렸다.
    # 사람은 싸우다가도 듣고 다시 판단한다.
    model = JudgmentModel(
        [tactic(eat_first=False), tactic(style="leave", speech_ko="아 네 거였어? 그만할게!")], [reflection()]
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, leader_chat_via_host=True, **thinking(model))
    rig.controller.stance = "wait"
    root = eikthyr(20.0, 0.0)
    root.name, root.speed, root.ranged_m = "소환된 뿌리", 0.0, 0.0
    rig.world.spawn(root)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 20)
    await rig.controller.hear_leader("그거 내가 소환한거야")
    await rig.until(lambda: "아 네 거였어? 그만할게!" in rig.said(), 20)
    assert "그거 내가 소환한거야" in model.prompts["tactic"][1]
    await rig.until(lambda: rig.controller.current() is None, 10)
    arrows = rig.world.bot.inventory["나무 화살"]
    await asyncio.sleep(2.0)
    assert rig.world.bot.inventory["나무 화살"] == arrows


async def test_before_judging_a_fight_it_looks_at_the_foe(make_rig: Callable[..., Any]) -> None:
    from test_sight import SeeingModel

    from thorkell.config import VisionConfig
    from thorkell.world.sight import Eyes

    model = JudgmentModel([tactic(eat_first=False)], [reflection()])
    seeing = SeeingModel(
        {"summary_ko": "리더 곁에 땅에서 솟은 거대한 뿌리가 꿈틀댄다", "things": [], "ways": []}
    )
    rig: Rig = await make_rig(world=arena(), time_scale=4, **thinking(model))
    rig.controller.eyes = Eyes(rig.session, seeing, VisionConfig(backend="gemini"))
    rig.controller.stance = "wait"
    rig.world.spawn(eikthyr(25.0, 0.0))
    await rig.until(lambda: bool(model.prompts["tactic"]), 20)
    assert "[화면]" in model.prompts["tactic"][0]
    assert "리더 곁에 땅에서 솟은 거대한 뿌리가 꿈틀댄다" in model.prompts["tactic"][0]
    assert len(seeing.calls[0]["images"]) == 1
