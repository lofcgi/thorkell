"""`thorkell judge`: the leader's open requests from the project goal, put to the real planner
(gemini-3.8-flash) in simulated situations. For each case it prints how Thorkell read the words, what it
asked or planned and what it said, checks the kind of answer a first-time player would give, and saves a
report under artifacts/judgment/. One or two model calls per case.

The fight cases ask the same model what Thorkell makes of a boss on first sight, whether a second try
follows the lessons of a lost fight, and what he takes from losing.

  cd brain && uv run --env-file ../.env thorkell judge [--case house]
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from thorkell import lang
from thorkell.body import auth
from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession
from thorkell.config import secret
from thorkell.control.controller import Controller
from thorkell.control.goals import Goal
from thorkell.lang import Language, tr
from thorkell.mind.store import Episode, Store
from thorkell.models.gemini import GeminiJson, ModelError
from thorkell.paths import REPO_ROOT
from thorkell.plan.planner import Planner, PlannerConfig
from thorkell.plan.schema import Plan
from thorkell.plan.tactics import AFTER_DEATH, FightView, JudgmentRejected, Reflection, Tactic, Tactician
from thorkell.sim.world import SimBody, SimEntity, SimWorld, boar, forest, pickable

PLAN_WAIT_S = 90.0


@dataclass(frozen=True)
class Case:
    name: str
    says_ko: str
    says_en: str
    world: Callable[[], SimWorld]
    # 처음 하는 사람이라면 할 만한 대답의 종류. 맞으면 이유를, 아니면 None을 돌려준다.
    judge: Callable[[Plan], str | None]
    expect_ko: str


def _camp() -> SimWorld:
    world = SimWorld(forest(4))
    world.bot.inventory = {"나무": 12, "돌": 4, "망치": 1, "돌도끼": 1, "곤봉": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 900.0}
    world.spawn(SimEntity("7:300", "station", "작업대", -4.0, 2.0, creator="Thorkell"))
    return world


def _with_boar() -> SimWorld:
    world = _camp()
    world.spawn(boar(12.0, 4.0))
    return world


def _hungry() -> SimWorld:
    world = SimWorld([*forest(3), pickable("라즈베리 덤불", ("라즈베리", 1), 7.0, -3.0, "7:410")])
    world.bot.inventory = {"곤봉": 1, "돌도끼": 1}
    world.bot.known = set(world.bot.inventory) | {"라즈베리"}
    world.bot.foods = {}
    return world


def _skills(plan: Plan) -> list[str]:
    return [step.skill for step in plan.steps]


def _asks_or_proposes(plan: Plan) -> str | None:
    if plan.clarify:
        return "규모를 되물었다"
    if plan.steps and set(_skills(plan)) <= {"build", "gather", "say"}:
        return "가진 재료로 지을 만한 것을 바로 시작했다"
    return None


def _asks_or_looks(plan: Plan) -> str | None:
    if plan.clarify:
        return "모르는 이름을 물었다"
    # hunt는 안 보이면 먼저 주변을 찾아본다(search). 장비를 드는 것은 준비라 건너뛴다.
    skills = [skill for skill in _skills(plan) if skill != "equip"]
    if skills and skills[0] in ("search", "hunt"):
        return f"찾아보면서 잡기로 했다({', '.join(_skills(plan))})"
    return None


def _hunts(plan: Plan) -> str | None:
    return "보이는 멧돼지를 사냥하기로 했다" if "hunt" in _skills(plan) else None


def _finds_food(plan: Plan) -> str | None:
    skills = set(_skills(plan))
    if skills & {"gather", "hunt", "search", "cook", "eat"}:
        return f"먹을 것을 구하기로 했다({', '.join(_skills(plan))})"
    return None


def _just_talks(plan: Plan) -> str | None:
    return "말로만 답했다" if not plan.steps and not plan.clarify else None


CASES = [
    Case(
        "house",
        "집을 지어야겠어",
        "We should build a house",
        _camp,
        _asks_or_proposes,
        "규모를 되묻거나 가진 재료로 지을 만한 걸 제안",
    ),
    Case(
        "unknown_boar",
        "멧돼지 잡아와",
        "Go get a boar",
        _camp,
        _asks_or_looks,
        "멧돼지가 뭔지 묻거나 먼저 찾아봄",
    ),
    Case("seen_boar", "멧돼지 잡아와", "Go get a boar", _with_boar, _hunts, "이름표로 본 멧돼지를 사냥"),
    Case(
        "food", "식량이 필요해", "We need food", _hungry, _finds_food, "보이는 덤불·사냥감으로 먹을 것을 구함"
    ),
    Case(
        "small_talk",
        "오늘 기분 어때?",
        "How are you feeling today?",
        _camp,
        _just_talks,
        "움직이지 않고 말로만 답함",
    ),
]


async def _run_case(case: Case, planner: Planner) -> dict[str, Any]:
    token = auth.new_hex(32)
    world = case.world()
    session = BodySession()
    server = BridgeServer(token, session.on_message)
    session.attach(server)
    await server.start(0)
    stop = asyncio.Event()
    body = asyncio.create_task(SimBody(world, time_scale=1).run(server.port, token, stop))
    controller = Controller(session, planner=planner)
    controller.stance = "wait"
    brain: asyncio.Task[None] | None = None
    try:
        await session.wait_for(lambda: session.armed and session.scene is not None, 10)
        brain = asyncio.create_task(controller.run(stop))
        # 한 번 둘러보게 둔다(이름표가 뜬 생물을 기억한다).
        await asyncio.sleep(1.0)
        world.leader_says(tr(case.says_ko, case.says_en))
        plan = await _plan_of(controller)
        await asyncio.sleep(2.0)
        said = [text for _, text in world.said]
    finally:
        stop.set()
        await asyncio.gather(body, *([brain] if brain is not None else []), return_exceptions=True)
        await server.close()
    verdict = case.judge(plan) if plan is not None else None
    return {
        "case": case.name,
        "says": tr(case.says_ko, case.says_en),
        "expect": case.expect_ko,
        "ok": verdict is not None,
        "verdict": verdict,
        "interpretation": plan.interpretation_ko if plan else None,
        "clarify": plan.clarify if plan else None,
        "steps": [step.model_dump(exclude_none=True) for step in plan.steps] if plan else None,
        "said": said,
        "decisions": [f"{d.kind}: {d.reason_ko}" for d in controller.decisions],
        "failed_requests": [g.progress.get("evidence") for g in controller.finished if g.status == "failed"],
    }


async def _plan_of(controller: Controller) -> Plan | None:
    """The plan the request goal got, or None if the request failed or no plan came in PLAN_WAIT_S."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + PLAN_WAIT_S
    while loop.time() < deadline:
        goals: list[Goal] = [
            *controller.finished,
            *([controller.active.goal] if controller.active else []),
        ]
        for goal in goals:
            plan = goal.progress.get("plan") if goal.kind == "request" else None
            if plan is not None:
                return plan  # type: ignore[no-any-return]
            if goal.kind == "request" and goal.status == "failed":
                return None
        await asyncio.sleep(0.2)
    return None


# --- fights: what Thorkell makes of a boss, and what he takes from losing to it ---------------------
def _eikthyr() -> str:
    return tr("에이크쉬르", "Eikthyr")


def _first_sight_view() -> FightView:
    eikthyr = _eikthyr()
    return FightView(
        eikthyr,
        tr(
            f"{eikthyr}: 키 약 3.5m, 화면 위쪽에 큰 체력바와 이름이 떴다, 체력 100%, 25m 앞, 나를 알아챘다",
            f"{eikthyr}: about 3.5 m tall, a big health bar and its name at the top of the screen, "
            "health 100%, 25 m ahead, has noticed me",
        ),
        tr(
            "체력 60/60, 스태미나 50/50\n음식 칸 1/3(라즈베리)\n"
            "가방의 음식: 구운 고기 6, 버섯 10, 라즈베리 9\n"
            "무기: 곤봉(둔기 12), 조잡한 활(찌르기 22), 화살 100개",
            "health 60/60, stamina 50/50\nfood slots 1/3 (Raspberries)\nfood in the bag: Cooked Meat 6, "
            "Mushroom 10, Raspberries 9\nweapons: Club (blunt 12), Crude Bow (pierce 22), 100 arrows",
        ),
        tr("40m 떨어져 있다", "40 m away"),
        True,
    )


def _looks(ahead_m: int, height_m: str) -> str:
    return tr(
        f"키 약 {height_m}m, 화면 위쪽에 큰 체력바와 이름이 떴다, 체력 100%, {ahead_m}m 앞, 나를 알아챘다",
        f"about {height_m} m tall, a big health bar and its name at the top of the screen, health 100%, "
        f"{ahead_m} m ahead, has noticed me",
    )


# 실게임(2026-10-17)에서 에이크쉬르에게 진 싸움과 비슷한 기록: 음식 한 칸, 16m 안에서 번개와 뿔.
def _lost_fight() -> dict[str, Any]:
    return {
        "looks": _looks(22, "3.5"),
        "tactic": {
            "impression_ko": tr(
                "엄청 크고 화면 위에 체력바가 떴어. 보스 같아",
                "It's huge and a health bar showed up at the top. Looks like a boss",
            ),
            "style": "ranged",
            "keep_m": 16.0,
            "close_m": 7.0,
            "retreat_hp": 0.3,
            "return_hp": 0.6,
            "hits_then_back": 2,
            "eat_first": False,
            "speech_ko": tr("보스야! 멀리서 쏠게", "A boss! I'll shoot from far away"),
            "cites": [],
        },
        "food_slots": 1,
        "hits": [
            [6.2, 9.5, 14, ["lightning", "pierce"]],
            [13.8, 9.1, 15, ["lightning", "pierce"]],
            [21.0, 18.0, 5, ["pierce"]],
            [24.4, 17.5, 4, ["pierce"]],
        ],
        "shots": {"fired": 11},
        "health": [[0.0, 1.0], [10.5, 0.96], [18.0, 0.91], [24.0, 0.88]],
        "my_hp_min": 0.0,
        "leader_m": 40,
        "seconds": 25.1,
    }


@dataclass(frozen=True)
class FightCase:
    name: str
    ask: Callable[[Tactician, Store], Awaitable[Tactic | Reflection]]
    judge: Callable[[Any, Store], str | None]
    expect_ko: str


async def _first_sight(tactician: Tactician, store: Store) -> Tactic:
    return await tactician.tactic(_first_sight_view(), [], [])


def _keeps_away(tactic: Tactic, _: Store) -> str | None:
    if tactic.style != "melee" and tactic.keep_m >= 10:
        return f"멀리서 싸우기로 했다({tactic.style}, {tactic.keep_m:g}m)"
    return None


async def _second_try(tactician: Tactician, store: Store) -> Tactic:
    eikthyr = _eikthyr()
    lost = store.add_episode(eikthyr, "died", _lost_fight())
    store.add_lesson(
        eikthyr,
        tr(
            "16m 안에서는 번개를 맞고, 5m 안에서는 뿔에 크게 맞았다. 25m 넘게 떨어져서 쏘자",
            "Inside 16 m I got hit by lightning, inside 5 m hard by the antlers. Shoot from more than 25 m",
        ),
        lost.id,
    )
    store.add_lesson(
        eikthyr,
        tr(
            "음식 한 칸으로는 몇 방에 죽는다. 싸우기 전에 세 칸을 채우자",
            "With one food slot a few hits kill me. Fill all three before the fight",
        ),
        lost.id,
    )
    return await tactician.tactic(_first_sight_view(), store.episodes(eikthyr), store.lessons((eikthyr,)))


def _follows_lessons(tactic: Tactic, _: Store) -> str | None:
    if {"L1", "L2"} <= set(tactic.cites) and tactic.keep_m >= 25 and tactic.eat_first:
        return f"교훈을 따랐다(멀리 {tactic.keep_m:g}m, 먼저 먹기)"
    return None


async def _reflect_on_loss(tactician: Tactician, store: Store) -> Reflection:
    lost = store.add_episode(_eikthyr(), "died", _lost_fight())
    return await tactician.reflect(lost, [], [], [])


def _learns_from_loss(reflection: Reflection, _: Store) -> str | None:
    numbered = [lesson for lesson in reflection.lessons if any(ch.isdigit() for ch in lesson.text_ko)]
    if numbered and reflection.after_death in ("alone", "with_leader"):
        return f"숫자를 근거로 교훈 {len(reflection.lessons)}개, 물건은 {reflection.after_death}"
    return None


# 실게임(2026-10-18) E4와 같은 기록: 98초까지 쏘아 78%로 깎았지만, 체력 50% 아래에서 물러나 있던 65초 동안
# 번개를 계속 맞아 내 체력은 안 찼고 상대는 80%로 회복했다. 회고는 "더 멀리"만 배웠다.
def _stalled_fight() -> dict[str, Any]:
    return {
        "looks": _looks(30, "3"),
        "tactic": {
            "impression_ko": tr(
                "번개를 쏘며 쫓아오는 거대한 사슴 보스",
                "A giant stag boss that chases me, shooting lightning",
            ),
            "style": "ranged",
            "keep_m": 32.0,
            "close_m": 12.0,
            "retreat_hp": 0.5,
            "return_hp": 0.8,
            "hits_then_back": 0,
            "eat_first": False,
            "retreat_to_leader": False,
            "speech_ko": tr("활로 아주 멀리서 쏴볼게!", "I'll try shooting from really far away!"),
            "cites": [],
        },
        "food_slots": 3,
        "hits": [
            [4.0, 13.2, 18, ["lightning"]],
            [31.9, 12.9, 23, ["lightning"]],
            [58.3, 14.0, 24, ["lightning"]],
            [68.5, 12.2, 14, ["lightning"]],
            [91.4, 18.8, 7, ["pierce"]],
            [98.5, 13.0, 22, ["lightning"]],
            [127.1, 12.9, 23, ["lightning"]],
            [154.5, 13.3, 9, ["lightning"]],
            [163.2, 13.3, 4, ["lightning"]],
            [165.6, 16.7, 4, ["pierce"]],
        ],
        "shots": {"fired": 9, "cannot_draw": 3, "no_line_of_sight": 6},
        "health": [[4.0, 1.0], [25.3, 0.9], [54.2, 0.82], [78.2, 0.78], [119.4, 0.79], [163.2, 0.8]],
        "my_health": [
            [4.0, 0.83],
            [18.7, 0.93],
            [58.3, 0.8],
            [68.5, 0.69],
            [91.4, 0.55],
            [98.5, 0.43],
            [111.8, 0.49],
            [127.1, 0.37],
            [140.3, 0.48],
            [154.5, 0.35],
            [163.2, 0.23],
            [165.6, 0.0],
        ],
        "retreats": 1,
        "recovering_s": 64.7,
        "my_hp_min": 0.0,
        "leader_m": 69,
        "seconds": 165.6,
    }


async def _reflect_on_stall(tactician: Tactician, store: Store) -> Reflection:
    stalled = store.add_episode(_eikthyr(), "died", _stalled_fight())
    return await tactician.reflect(stalled, [], [], [])


def _sees_the_stall(reflection: Reflection, _: Store) -> str | None:
    said = reflection.what_happened_ko + " ".join(lesson.text_ko for lesson in reflection.lessons)
    words = ("물러", "회복") if lang.current() == "ko" else ("back", "recover", "heal", "regen")
    if any(word in said.lower() for word in words) and reflection.after_death in AFTER_DEATH:
        return "물러나 있던 동안 안 통한 것을 짚음"
    return None


# 리허설(2026-10-18): 리더가 소환한 뿌리를 보고 싸움을 걸었고, 리더가 "내가 소환한거야"라고 해도 때렸다.
def _summoned_root() -> FightView:
    if lang.current() == "en":
        return FightView(
            "Summoned Root",
            "Summoned Root: about 3 m tall, name and health bar above its head, health 100%, 6 m ahead, "
            "has noticed me",
            "health 45/45, stamina 50/50\nfood slots 1/3 (Raspberries)\nfood in the bag: none\nweapons: none",
            '3 m away\nwhat the leader said lately: "can you see this too?" / "nah I summoned it"',
            False,
            sight_ko="A thick knot of tree roots has burst out of the ground right next to the leader and is "
            "writhing. It isn't attacking the leader",
        )
    return FightView(
        "소환된 뿌리",
        "소환된 뿌리: 키 약 3m, 머리 위에 이름과 체력바, 체력 100%, 6m 앞, 나를 알아챘다",
        "체력 45/45, 스태미나 50/50\n음식 칸 1/3(라즈베리)\n가방의 음식: 없음\n무기: 없음",
        '3m 떨어져 있다\n리더가 최근에 한 말: "이것도 보임?" / "ㄴㄴ 내가 소환한거야"',
        False,
        sight_ko="리더 바로 옆 땅에서 굵은 나무뿌리 덩어리가 솟아 꿈틀대고 있다. 리더를 공격하지는 않는다",
    )


async def _summon_seen(tactician: Tactician, _: Store) -> Tactic:
    return await tactician.tactic(_summoned_root(), [], [])


def _leaves_it(tactic: Tactic, _: Store) -> str | None:
    if tactic.style == "leave":
        return f"리더의 소환수로 보고 건드리지 않음: {tactic.speech_ko}"
    return None


def _hearing(words: str) -> FightView:
    view = _first_sight_view()
    heard = tr(f'리더가 최근에 한 말: "{words}"', f'what the leader said lately: "{words}"')
    return replace(view, leader_ko=f"{view.leader_ko}\n{heard}")


async def _told_alone(tactician: Tactician, _: Store) -> Tactic:
    return await tactician.tactic(
        _hearing(
            tr(
                "나는 싸움은 못 도와줘. 멀리서 지켜볼게. 이번엔 너 혼자 해 봐",
                "I can't help with the fighting. I'll watch from far away. You try it alone this time",
            )
        ),
        [],
        [],
    )


def _fights_alone(tactic: Tactic, _: Store) -> str | None:
    # 실게임(2026-10-18): 리더 쪽으로 물러나다 싸우지 않는 리더에게 보스를 끌고 가 리더가 죽었다.
    if tactic.style != "keep_away" and not tactic.retreat_to_leader:
        return f"혼자 싸우고({tactic.style}) 리더 쪽으로 끌고 가지 않음"
    return None


async def _told_together(tactician: Tactician, _: Store) -> Tactic:
    return await tactician.tactic(
        _hearing(
            tr(
                "같이 잡자! 내가 앞에서 막을게, 넌 뒤에서 쏴",
                "Let's take him down together! I'll hold him up front, you shoot from behind",
            )
        ),
        [],
        [],
    )


def _fights_with_leader(tactic: Tactic, _: Store) -> str | None:
    if tactic.style == "ranged" and tactic.retreat_to_leader:
        return f"리더 뒤에서 쏘고({tactic.keep_m:g}m) 물러날 때 리더 쪽으로"
    return None


# 실게임(2026-10-20, 죽을 수 있는 리더): 앞에서 막던 리더가 48초에 쓰러졌다. 토르켈은 모른 채 같은 방법으로
# 쏘다가 번개 다섯 번을 맞고 죽었다. 이제 쓰러지는 것을 보고 다시 판단한다.
def _leader_down() -> tuple[FightView, list[Episode]]:
    together = tr(
        "같이 잡자! 내가 앞에서 막을게, 넌 뒤에서 쏴",
        "Let's take him down together! I'll hold him up front, you shoot from behind",
    )
    view = _first_sight_view()
    view = replace(
        view,
        seen_ko=view.seen_ko.replace(
            tr("체력 100%, 25m 앞", "health 100%, 25 m ahead"),
            tr("체력 62%, 18m 앞", "health 62%, 18 m ahead"),
        ),
        me_ko=view.me_ko.replace(tr("체력 60/60", "health 60/60"), tr("체력 41/60", "health 41/60")),
        leader_ko=tr(
            "싸움 48초에 쓰러졌다(쓰러진 자리에 시체가 있다). 지금은 안 보인다\n"
            f'리더가 최근에 한 말: "{together}"',
            "Fell 48 s into the fight (the body lies where they fell). Now not in sight\n"
            f'what the leader said lately: "{together}"',
        ),
    )
    now = {
        "looks": _looks(18, "3.5"),
        "tactic": {
            "impression_ko": tr(
                "리더가 막는 동안 뒤에서 쏠 보스", "A boss to shoot from behind while the leader holds it"
            ),
            "style": "ranged",
            "keep_m": 20.0,
            "close_m": 12.0,
            "retreat_hp": 0.4,
            "return_hp": 0.8,
            "hits_then_back": 0,
            "eat_first": True,
            "retreat_to_leader": True,
            "speech_ko": tr("뒤에서 쏠게!", "I'll shoot from behind!"),
            "cites": [],
        },
        "food_slots": 3,
        "hits": [[51.0, 13.8, 17, ["lightning"]]],
        "shots": {"fired": 6, "hit": 4, "no_line_of_sight": 2},
        "health": [[3.0, 1.0], [40.0, 0.7], [52.0, 0.62]],
        "leader_fell_s": 48.0,
        "leader_m": 12,
        "seconds": 53.0,
    }
    return view, [Episode("now", _eikthyr(), tr("싸우는 중", "still fighting"), now)]


async def _sees_leader_down(tactician: Tactician, _: Store) -> Tactic:
    view, earlier = _leader_down()
    return await tactician.tactic(view, earlier, [])


def _stops_backing_to_leader(tactic: Tactic, _: Store) -> str | None:
    # 쓰러진 리더 쪽(시체)으로 물러나면 지켜 줄 사람이 없다. 무엇을 할지는 모델이 정한다.
    if not tactic.retreat_to_leader:
        return f"리더 없이 다시 정함({tactic.style}, {tactic.keep_m:g}m): {tactic.speech_ko}"
    return None


FIGHT_CASES = [
    FightCase("boss_seen", _first_sight, _keeps_away, "화면 위 체력바를 보고 보스로 여겨 거리를 둠"),
    FightCase("boss_again", _second_try, _follows_lessons, "지난 교훈(거리·음식)을 인용해 따름"),
    FightCase("boss_lost", _reflect_on_loss, _learns_from_loss, "진 싸움에서 숫자 근거 교훈과 묘비 결정"),
    FightCase(
        "boss_alone",
        _told_alone,
        _fights_alone,
        "리더가 혼자 하라고 하면 혼자 싸우고 리더에게 끌고 가지 않음",
    ),
    FightCase(
        "boss_together",
        _told_together,
        _fights_with_leader,
        "리더가 앞에서 막겠다면 뒤에서 쏘고 리더 쪽으로 물러남",
    ),
    FightCase("summon_said", _summon_seen, _leaves_it, "리더가 소환했다고 한 것은 적으로 보지 않고 둠"),
    FightCase(
        "leader_down",
        _sees_leader_down,
        _stops_backing_to_leader,
        "앞에서 막던 리더가 쓰러진 것을 보고 리더 쪽으로 물러나지 않게 다시 정함",
    ),
    FightCase(
        "boss_stalled",
        _reflect_on_stall,
        _sees_the_stall,
        "물러나 있는 동안 회복도 못 하고 상대만 회복한 것을 짚음",
    ),
]


async def _run_fight_case(case: FightCase, tactician: Tactician) -> dict[str, Any]:
    store = Store()
    try:
        answer = await case.ask(tactician, store)
    except (ModelError, JudgmentRejected) as error:
        return {
            "case": case.name,
            "expect": case.expect_ko,
            "ok": False,
            "verdict": None,
            "error": str(error),
        }
    verdict = case.judge(answer, store)
    return {
        "case": case.name,
        "expect": case.expect_ko,
        "ok": verdict is not None,
        "verdict": verdict,
        "answer": answer.model_dump(),
    }


async def run(case_names: list[str] | None, model: str, language: Language) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    lang.use(language)
    planner = Planner(GeminiJson(secret("GEMINI_API_KEY")), PlannerConfig(model=model))
    tactician = Tactician(planner.model, planner.config)
    chosen = [c for c in CASES if not case_names or c.name in case_names]
    results = []
    for case in chosen:
        result = await _run_case(case, planner)
        results.append(result)
        mark = "PASS" if result["ok"] else "FAIL"
        verdict = result["verdict"] or "기대: " + case.expect_ko
        print(f"[{mark}] {case.name}: 리더 '{result['says']}' → {verdict}")
        print(f"       해석: {result['interpretation']}")
        if result["clarify"]:
            print(f"       물음: {result['clarify']}")
        if result["steps"]:
            print(f"       단계: {[s['skill'] for s in result['steps']]}")
        for text in result["said"][-3:]:
            print(f"       말: {text}")
    for fight_case in [c for c in FIGHT_CASES if not case_names or c.name in case_names]:
        result = await _run_fight_case(fight_case, tactician)
        results.append(result)
        mark = "PASS" if result["ok"] else "FAIL"
        print(f"[{mark}] {fight_case.name}: {result['verdict'] or '기대: ' + fight_case.expect_ko}")
        print(f"       답: {json.dumps(result.get('answer') or result.get('error'), ensure_ascii=False)}")
    out = REPO_ROOT / "artifacts/judgment"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"judgment-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    usage = [{"input": u.input_tokens, "output": u.output_tokens} for u in planner.usage + tactician.usage]
    path.write_text(
        json.dumps(
            {"model": model, "language": language, "results": results, "usage": usage},
            ensure_ascii=False,
            indent=2,
        )
    )
    passed = sum(r["ok"] for r in results)
    print(f"{passed}/{len(results)} 통과, 모델 호출 {len(usage)}회. 보고서: {path}")
    return 0 if passed == len(results) else 1
