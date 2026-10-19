"""Requests that go through the planner: plan once, then run the steps with abort conditions.

The plan and per-step progress live in the goal, so a request suspended by a fight resumes at the
step it was on (and a gather step counts what was actually picked up so far).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math

from thorkell.control.goals import Goal
from thorkell.control.library import SKILLS
from thorkell.control.making import menu
from thorkell.control.skills import SkillContext, SkillOutcome, _do
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.mind.store import Store
from thorkell.models.gemini import ModelError
from thorkell.plan.planner import PlanRejected, context_from_scene
from thorkell.plan.quantity import gather_feasible
from thorkell.plan.schema import OPTIONAL_ARGS, Plan, Step
from thorkell.plan.situation import Known, describe
from thorkell.world.memory import WorldMemory
from thorkell.world.sight import SightError

log = logging.getLogger(__name__)

DUSK = 0.70


async def handle_request(ctx: SkillContext) -> SkillOutcome:
    """Plan, run the plan, and think again with what happened when a step fails (a person tries another way
    or asks) or when the plan said it only gets partway (the recipe shows up once the materials are in hand).
    Whether and how to go on is the model's call; the code only caps how often it is asked."""
    goal = ctx.goal
    tried: list[str] = goal.progress.setdefault("attempts", [])
    plans = int(goal.progress.setdefault("plans", 0))
    failures = int(goal.progress.setdefault("failures_in_a_row", 0))
    while True:
        plan: Plan | None = goal.progress.get("plan")
        if plan is None:
            made = await _make_plan(ctx, tried)
            if isinstance(made, SkillOutcome):
                return made
            plan = made
            plans = goal.progress["plans"] = plans + 1
        outcome = await run_plan(ctx, plan)
        done = int(goal.progress.get("step", 0))
        tried.extend(f"{_step_ko(step)}: {tr('됨', 'done')}" for step in plan.steps[:done])
        if (outcome.ok and not plan.think_again_after) or outcome.code.startswith("aborted:"):
            return outcome
        failures = goal.progress["failures_in_a_row"] = 0 if outcome.ok else failures + 1
        if not outcome.ok:
            didnt = tr("안 됨", "didn't work")
            tried.append(f"{_step_ko(plan.steps[done])}: {didnt} — {outcome.detail_ko or outcome.code}")
            if failures >= FAILURES_IN_A_ROW:
                return outcome
        if plans >= PLANS_PER_REQUEST:
            return (
                outcome
                if not outcome.ok
                else SkillOutcome(
                    False,
                    "gave_up",
                    tr("여기까지 했는데 더는 잘 모르겠어", "Got this far, but I'm not sure what to do next"),
                )
            )
        log.info("thinking again about %r: %s", goal.args["text"], tried[-1] if tried else "")
        # 지난 계획의 하위 목표(싸움 기록이 남지 않은 것 포함)는 부탁이 끝날 때 컨트롤러가 본다.
        goal.progress.setdefault("past_children", []).extend(goal.progress.pop("children", {}).values())
        for key in ("plan", "step"):
            goal.progress.pop(key, None)


def _step_ko(step: Step) -> str:
    return f"{step.skill}({', '.join(f'{k}={v}' for k, v in step.args.items())})"


# 한 부탁에 계획을 세우는 횟수(모델 호출 비용의 상한). 넘으면 한 데까지와 안 된 이유를 말한다.
# 일이 나아가는 동안은 이어서 생각한다(재료 모으기 → 메뉴에 뜸 → 만들기). 잇달아 안 되면 그만두고 말한다.
PLANS_PER_REQUEST = 12
FAILURES_IN_A_ROW = 3


async def _make_plan(ctx: SkillContext, tried: list[str]) -> Plan | SkillOutcome:
    goal = ctx.goal
    if ctx.planner is None:
        raise RuntimeError("a request goal needs a configured planner")
    if ctx.session.scene is None or ctx.session.state is None:
        return SkillOutcome(False, "no_observation", tr("아직 주변이 안 보여", "I can't see around me yet"))
    scene, state = ctx.session.scene.data, ctx.session.state.data
    wood = next(iter(sorted(ctx.wood_names)), None)
    feasible = gather_feasible(scene, wood, ctx.memory.get("wood_rate_per_min"))
    facts, fact_ids = ctx.mind.facts_for_prompt() if ctx.mind is not None else ([], frozenset())
    # 사람은 친구가 말하면 친구가 보는 쪽을 쳐다보고 답한다. 메뉴를 읽는 동안 같이 본다.
    seeing = asyncio.create_task(look_for(ctx, str(goal.args["text"])))
    recipes, pieces = await menu(ctx, "recipes"), await menu(ctx, "pieces")
    world = ctx.world if ctx.world is not None else WorldMemory(Store())
    known = Known(
        recipes=recipes,
        pieces=pieces,
        texts=ctx.mind.store.recent_texts() if ctx.mind is not None else [],
        talk=ctx.mind.store.recent_utterances() if ctx.mind is not None else [],
        messages=[str(e.data.get("text")) for e in ctx.session.events_of("game_message")[-4:]],
        doing=str(ctx.memory.get("doing", "")),
        agenda=list(ctx.memory.get("agenda", [])),
        tried=list(tried),
    )
    context = context_from_scene(
        scene,
        feasible,
        fact_ids,
        recipes=recipes,
        pieces=pieces,
        places=[p.name for p in world.places()],
        creatures=world.creature_names(),
        items=world.seen_names() + [i for i, _, _ in _known_sources(world)],
        request=str(goal.args["text"]),
    )
    situation = describe(state, scene, world, known)
    sight = await seeing
    if sight is not None:
        situation += "\n\n" + tr("[지금 내 화면]", "[My screen now]") + "\n" + "\n".join(sight)
    try:
        plan = await ctx.planner.plan(goal.args["text"], situation, context, facts)
    except PlanRejected as error:
        log.error("plan rejected for %r: %s", goal.args["text"], error)
        return SkillOutcome(
            False,
            "plan_rejected",
            tr(
                "어떻게 할지 계획을 못 세웠어. 조금 다르게 말해 줄래?",
                "I couldn't work out a plan. Could you say it a bit differently?",
            ),
            {"problems": error.problems},
        )
    except ModelError as error:
        # 원인은 증거와 로그에 남긴다(목표의 outcome은 결과 코드로 덮인다).
        log.error("planner failed for %r: %s", goal.args["text"], error)
        evidence = {"error": str(error), "status": error.status}
        if error.status == 429:
            return SkillOutcome(False, "planner_quota", tr(QUOTA_KO, QUOTA_EN), evidence)
        return SkillOutcome(
            False,
            "planner_error",
            tr(
                "생각이 잘 안 정리돼. 다시 말해 줄래?",
                "I can't get my thoughts straight. Could you say that again?",
            ),
            evidence,
        )
    goal.progress["plan"] = plan
    if plan.clarify:
        if ctx.speak is not None:
            await ctx.speak(plan.clarify)
        return SkillOutcome(True, "asked", "")  # 이미 물었으니 보고로 되풀이하지 않는다
    if ctx.speak is not None and plan.speech_gist_ko:
        await ctx.speak(plan.speech_gist_ko)
    return plan


async def look_for(ctx: SkillContext, words: str) -> list[str] | None:
    """What Thorkell sees when the leader speaks: toward the leader's front if the leader is in sight,
    else all round. None without eyes. A failure to see goes in the lines, so the judgment knows."""
    if ctx.eyes is None:
        return None
    scene = ctx.session.scene.data if ctx.session.scene else {}
    leader = scene.get("leader")
    try:
        if leader is not None:
            facing = math.radians(float(leader.get("facing", 0.0)))
            x, y, z = (float(v) for v in leader["pos"])
            toward = [x + math.sin(facing) * LEADER_FRONT_M, y + 1.0, z + math.cos(facing) * LEADER_FRONT_M]
            view = await ctx.eyes.look(words, toward=toward)
        else:
            view = await ctx.eyes.look(words, around=True)
    except (ModelError, SightError, TimeoutError) as error:
        log.error("could not look before answering %r: %s", words, error)
        return [
            tr(
                f"(화면을 보려 했지만 못 봤다: {error})",
                f"(tried to look at the screen but couldn't: {error})",
            )
        ]
    return view.lines()


# 리더가 "이거"라고 할 때 볼 곳: 리더 앞 몇 m.
LEADER_FRONT_M = 3.0


def abort_reason(ctx: SkillContext, plan: Plan) -> str | None:
    state = ctx.session.state.data if ctx.session.state else {}
    env = ctx.session.scene.data.get("env", {}) if ctx.session.scene else {}
    for condition in plan.abort_if:
        hurt = bool(state) and state["hp"] / max(1.0, state["hp_max"]) < (condition.value or 0.0)
        if condition.cond == "hp_below" and hurt:
            return "hp_below"
        if condition.cond == "dusk" and env.get("day_fraction", 0) >= DUSK:
            return "dusk"
        if condition.cond == "night" and env.get("night"):
            return "night"
    return None


ABORT_KO = {"hp_below": "많이 다쳐서", "dusk": "해가 지려고 해서", "night": "밤이 돼서"}
ABORT_EN = {"hp_below": "I'm badly hurt", "dusk": "the sun's going down", "night": "it's night"}
QUOTA_KO = (
    "지금은 깊게 생각할 수가 없어(계획 모델 사용 한도에 걸렸어). "
    "'따라와', '기다려', '멈춰', '나무 10개 캐줘'처럼 정해진 말은 바로 알아들어."
)
QUOTA_EN = (
    "I can't think hard right now (the planning model hit its usage limit). "
    "I still get set phrases right away, like 'follow me', 'wait', 'stop' or 'chop 10 wood'."
)


async def run_plan(ctx: SkillContext, plan: Plan) -> SkillOutcome:
    # 단계가 없는 계획(인사·잡담에 답만 하는 것)은 speech_gist_ko로 이미 말했으니 마무리 보고를 하지 않는다.
    last = SkillOutcome(True, "done", "")
    while (index := int(ctx.goal.progress.setdefault("step", 0))) < len(plan.steps):
        step = plan.steps[index]
        task = asyncio.create_task(_run_step(ctx, step))
        try:
            while not task.done():
                reason = abort_reason(ctx, plan)
                if reason == "hp_below" and step.skill == "fight":
                    # 싸움에서 물러날 체력은 전술(retreat_hp)이 정한다. 일하다 다치면 멈추는 조건으로
                    # 끊지 않는다(실게임: 스스로 세운 계획의 싸움이 이 조건에 끊겼다).
                    reason = None
                if reason is not None:
                    stopped = tr(f"{ABORT_KO[reason]} 멈췄어", f"Stopped, {ABORT_EN[reason]}")
                    return SkillOutcome(False, f"aborted:{reason}", stopped)
                await asyncio.wait({task}, timeout=1.0)
        finally:
            # 계획이 멈추거나(중단 조건) 목표가 취소·보류되면 하던 단계도 멈춘다. 안 그러면 단계가 따로 남아
            # 몸을 계속 움직인다(실게임: 계획 안의 싸움과 새 싸움이 같이 돌았다).
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        last = task.result()
        if not last.ok:
            return last
        ctx.goal.progress["step"] = index + 1
    return last


# 계획 단계 중 스킬 목표를 따로 세우지 않고 바로 하는 것. 나머지는 모두 같은 이름의 스킬을 하위 목표로 돌린다.
DIRECT_STEPS = ("equip", "eat", "say", "wait", "go_to_leader")


async def _run_step(ctx: SkillContext, step: Step) -> SkillOutcome:
    match step.skill:
        case "equip" | "eat":
            result = await _do(ctx, step.skill, {"item": step.args["item"]})
            ok = result.status == "succeeded"
            if result.code == "swimming":
                return SkillOutcome(
                    False,
                    "swimming",
                    tr(
                        f"헤엄치는 중이라 {josa(str(step.args['item']), '을를')} 꺼낼 수 없어",
                        f"I can't take out the {step.args['item']} while I'm swimming",
                    ),
                )
            ready = tr("준비됨", "ready") if ok else tr("실패", "failed")
            return SkillOutcome(ok, result.code, f"{step.args['item']} {ready}")
        case "say":
            if ctx.speak is not None:
                await ctx.speak(str(step.args["text"]))
            return SkillOutcome(True, "said", "")  # 이미 말했으니 보고로 되풀이하지 않는다
        case "wait":
            await _do(
                ctx,
                "wait",
                {"seconds": float(step.args["seconds"])},
                timeout=float(step.args["seconds"]) + 10,
            )
            return SkillOutcome(True, "waited", tr("기다렸어", "Waited"))
        case "go_to_leader":
            leader = ctx.session.scene.data.get("leader") if ctx.session.scene else None
            if leader is None:
                return SkillOutcome(False, "leader_lost", tr("네가 안 보여", "I can't see you"))
            result = await _do(
                ctx,
                "move_to",
                {"target": {"id": leader["id"]}, "arrive_radius": 3.0, "run": True},
                timeout=120,
            )
            return SkillOutcome(
                result.status == "succeeded", result.code, tr("네 옆으로 왔어", "I'm right by you now")
            )
        case skill if skill in SKILLS:
            children: dict[str, Goal] = ctx.goal.progress.setdefault("children", {})
            args = {**OPTIONAL_ARGS.get(step.skill, {}), **step.args}
            child = children.setdefault(step.id, Goal(step.skill, ctx.goal.tier, args, source=ctx.goal.id))
            child.status = "active"
            outcome = await SKILLS[step.skill](ctx.child(child))
            child.status, child.outcome = ("done" if outcome.ok else "failed"), outcome.code
            return outcome
    raise ValueError(f"no runner for plan skill {step.skill}")


def _known_sources(world: WorldMemory) -> list[tuple[str, str, str]]:
    rows = world.db.execute("SELECT item, kind, source FROM sources").fetchall()
    return [(str(r["item"]), str(r["kind"]), str(r["source"])) for r in rows]
