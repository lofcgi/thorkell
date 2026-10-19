"""The cognitive controller: the single writer of goals and intention.

It turns events into goals, keeps one goal active (one skill task), preempts by tier, resumes
suspended goals last-in-first-out, and speaks only about its own decisions.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from thorkell.body import protocol
from thorkell.body.session import BodySession, CommandRejected
from thorkell.control import intents
from thorkell.control.fight import close_record, describe_looks
from thorkell.control.goals import Decision, Goal, Tier
from thorkell.control.library import SKILLS
from thorkell.control.plan_skills import handle_request
from thorkell.control.skills import SkillContext, SkillOutcome, food_to_eat
from thorkell.decide.points import THREAT_RESPONSE
from thorkell.decide.runner import DecisionRunner
from thorkell.lang import tr
from thorkell.mind.korean import josa
from thorkell.mind.mind import Mind
from thorkell.mind.speech import Line
from thorkell.mind.store import Episode, Store, general
from thorkell.models.gemini import ModelError
from thorkell.plan.planner import Planner
from thorkell.plan.situation import DUSK
from thorkell.plan.tactics import JudgmentRejected, Tactician
from thorkell.world.memory import WorldMemory
from thorkell.world.serialize import decision_state
from thorkell.world.sight import Eyes

log = logging.getLogger(__name__)
# 게임의 일반 채팅은 15m 안에서만 보인다(Talker.m_normalDistance). 그보다 조금 안쪽까지만 일반으로 말한다.
NORMAL_EARSHOT_M = 14.0

SUSPENDED_EXPIRY_S = 600.0
# 다쳐서 미룬 부탁은 체력이 이만큼(비율) 돌아오면 이어 간다.
HEALED = 0.8
# 할 일이 없을 때 리더와 이만큼 넘게 떨어지면 곁으로 간다(동료로서의 기본 자세).
# "기다려"라고 하면 하지 않는다.
FOLLOW_GAP_M = 12.0
FINISHED_KEPT = 40
# 상대를 정해 놓고 스스로 싸우는 스킬. 그 상대에게 맞아도 따로 방어 목표를 세우지 않는다.
FIGHTING_SKILLS = ("hunt", "fight")
NIGHT_KO = "밤이 됐어. 어두우면 위험하니까 네 곁에 붙어 있을게."
NIGHT_EN = "It's night now. The dark's dangerous, so I'll stick close to you."
DIED_KO = "아… 죽었어. 다시 일어났어. 내 물건 찾으러 갈게."
DIED_EN = "Ah… I died. I'm back up. I'll go get my stuff."
DEFAULT_WOOD = 20
# 리더가 누운 걸 보고 자러 가려다 안 됐으면 이만큼 지나서 다시 본다(같은 실패를 되풀이하지 않게).
SLEEP_RETRY_S = 120.0
# 주의: 큰 생물이 나를 알아채고 이만큼 안에 있으면 어떻게 할지 생각할 차례다.
# 무엇인지, 어떻게 할지는 모델이 정한다.
# 생각해서 싸운 뒤(못 찾음 등)에는 이만큼 지나서 다시 본다.
NOTICE_BIG_M = 40.0
FACE_RETRY_S = 30.0
RECENT_HITS_S = 30.0
RISE_WAIT_S = 60.0
# 정해진 말로 알아듣는 명령. 검증된 스킬로 바로 시작한다(계획 모델을 기다리지 않는다).
COMMANDS = ("gather_wood", "follow", "wait", "pick_up", "sleep")
ACKNOWLEDGE_KO = {"follow": "응, 따라갈게.", "wait": "알겠어, 여기서 기다릴게.", "pick_up": "응, 받을게."}
ACKNOWLEDGE_EN = {
    "follow": "Okay, I'll follow you.",
    "wait": "Got it, I'll wait here.",
    "pick_up": "Sure, I'll take it.",
}


@dataclass
class _Active:
    goal: Goal
    task: asyncio.Task[SkillOutcome]


@dataclass
class Controller:
    session: BodySession
    leader_name: str = "Leader"
    # (text, talker) -> None. None이면 게임 채팅으로만 말한다.
    say: Callable[[str, str], Awaitable[None]] | None = None
    planner: Planner | None = None
    # 싸움 앞에서 무엇인지·어떻게 싸울지 생각하고, 끝나면 돌아본다. 없으면 큰 것과는 싸우지 못한다고 말한다.
    tactician: Tactician | None = None
    eyes: Eyes | None = None
    decider: DecisionRunner | None = None
    mind: Mind | None = None
    decisions: list[Decision] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    # True면 리더의 말은 hear_leader(사람 게임이 직접 넘겨준 채팅)로만 받는다.
    # 봇이 가까이서 같은 말을 들어도 두 번 처리하지 않는다.
    leader_chat_via_host: bool = False

    def __post_init__(self) -> None:
        # 기본 자세: follow면 할 일이 없을 때 리더 곁에 머문다. 리더가 "기다려"/"멈춰"라고 하면 wait.
        self.stance = "follow"
        self._fell_at: list[float] | None = None
        # 싸움을 돌아보는 중(배경 작업)과, 죽은 싸움을 돌아보고 정한 물건 찾기 방법(alone | with_leader).
        self._reflection: asyncio.Task[None] | None = None
        self._after_death: str | None = None
        self._death_state_seq = -1
        # 최근에 맞은 것(받은 시각, 공격자, 피해, 그때 거리, 피해 종류).
        # 싸움 밖에서 죽었을 때 돌아볼 기록이다.
        self._hits: list[tuple[float, str, float, int | None, list[str]]] = []
        # 세계 기억(장소·자원·생물 이름)은 지식과 같은 저장소에 둔다. 마음이 없으면 이번 실행 동안만 기억한다.
        self.world = WorldMemory(self.mind.store if self.mind is not None else Store())
        self.active: _Active | None = None
        # 끝난 목표(최근 것만). 상태 질문과 진단에 쓴다.
        self.finished: list[Goal] = []
        self.suspended: list[Goal] = []
        # 다치거나 날이 저물어 계획이 멈춘 부탁. 나으면(아침이 되면) 다시 생각해서 이어 간다.
        self.deferred: list[Goal] = []
        self.pending: list[Goal] = []
        self._events: asyncio.Queue[protocol.Event] = asyncio.Queue()
        self._threat_checks: dict[str, asyncio.Task[None]] = {}
        self._scene_seq = -1
        self._sleep_asked_at = -SLEEP_RETRY_S
        self._ate_at_seq = -1
        self._faced_at = -FACE_RETRY_S
        self.session.event_listeners.append(self._events.put_nowait)

    # --- public -------------------------------------------------------------------------------
    def request(self, goal: Goal) -> None:
        self.pending.append(goal)

    def current(self) -> Goal | None:
        return self.active.goal if self.active else None

    async def run(self, stop: asyncio.Event) -> None:
        try:
            while not stop.is_set():
                while not self._events.empty():
                    await self._on_event(self._events.get_nowait())
                scene = self.session.scene
                if scene is not None and scene.seq != self._scene_seq:
                    self._scene_seq = scene.seq
                    here = self.session.state.data["pos"] if self.session.state else [0.0, 0.0, 0.0]
                    self.world.on_scene(scene.data, here)
                    if self.mind is not None:
                        self.mind.on_scene(scene.data)
                if self._reflection is not None and self._reflection.done():
                    reflection, self._reflection = self._reflection, None
                    reflection.result()  # 모델 오류는 안에서 말로 알린다. 그 밖의 오류는 여기서 크게 터진다.
                await self._arbitrate()
                if self.mind is not None and (line := self.mind.speech.next()) is not None:
                    await self._speak(line.text, f"mind:{line.topic or 'line'}", line.talker)
                await asyncio.sleep(0.1)
        finally:
            if self.active is not None:
                self.active.task.cancel()

    # --- events -------------------------------------------------------------------------------
    async def _on_event(self, event: protocol.Event) -> None:
        if self.mind is not None:
            self.mind.on_event(event)
        if event.kind == "death":
            self._fell_at = list(event.data.get("pos") or []) or None
            # 몸은 이벤트와 상태를 차례대로 보낸다. 이 뒤에 온 상태부터 죽은 뒤의 몸이다.
            self._death_state_seq = self.session.state.seq if self.session.state else -1
            goals = ([self.active.goal] if self.active is not None else []) + self.suspended
            fights = [fight for goal in goals for fight in self._fights_in(goal)]
            for fight in fights:
                self._reflect_on(fight, "died" if fight.status == "active" else fight.outcome)
            await self._drop_all(tr("죽었다", "died"))
            if not fights:
                self._reflect_on_death()
            return
        if event.kind == "env_changed" and event.data.get("night") is True and self.mind is not None:
            self.mind.speech.offer(Line(tr(NIGHT_KO, NIGHT_EN), 1, "normal", "night", 300))
            return
        if event.kind == "damage_taken":
            self._note_hit(event.data)
        if event.kind == "damage_taken" and event.data.get("attacker_kind") == "creature":
            attacker = event.data.get("attacker_id")
            handled = [
                g for g in self.pending + ([self.active.goal] if self.active else []) if g.kind == "defend"
            ]
            # 사냥 중인 상대가 반격하는 것은 이미 싸우고 있는 것이다.
            # 따로 방어 목표를 세우면 사냥이 멈춰서 잡은 것도 못 줍는다.
            hunting = (
                self.active is not None
                and self.active.goal.kind in FIGHTING_SKILLS
                and self.active.goal.args.get("creature") == event.data.get("attacker_name")
            )
            if attacker and not hunting and not any(g.args["attacker_id"] == attacker for g in handled):
                if self.decider is None:
                    self._defend(attacker, event.data.get("attacker_name"), event.data.get("attacker_size"))
                elif attacker not in self._threat_checks or self._threat_checks[attacker].done():
                    self._threat_checks[attacker] = asyncio.create_task(self._threat(event))
        elif (
            event.kind == "chat"
            and event.data.get("from") == self.leader_name
            and not self.leader_chat_via_host
        ):
            await self._on_leader_chat(str(event.data.get("text", "")), bool(event.data.get("stop_phrase")))

    async def _on_leader_chat(self, text: str, body_stopped: bool) -> None:
        intent = intents.read(text)
        if intent is None or intent.kind not in ("stop", "status"):
            reply = self.mind.hear(text) if self.mind is not None else None
            if reply is not None:
                await self._speak(reply, "heard")
                return
        fighting = self._current_fight()
        if intent is None and fighting is not None and "tactic" in fighting.progress:
            # 싸우는 중의 말은 싸움이 끝날 때까지 미루지 않는다. 그 말을 듣고 싸움을 다시 판단한다
            # (리허설: "내가 소환한거야", "안보여?"가 2분 넘게 밀렸다).
            fighting.progress["heard"] = True
            return
        if intent is None:
            # 정해진 말이 아니다(인사, 잡담, 처음 보는 부탁). 계획 모델이 있으면 그쪽이 답하거나 일을 정한다.
            if self.planner is not None:
                self.request_text(text)
            else:
                await self._speak(
                    tr(
                        "미안, 그 말은 아직 못 알아들어. '따라와', '기다려', '나무 10개 캐줘'처럼 말해 줘.",
                        "Sorry, I don't get that yet. Try 'follow me', 'wait' or 'chop 10 wood'.",
                    ),
                    "unknown",
                )
            return
        match intent.kind:
            case "stop":
                self.stance = "wait"
                await self.cancel_all(
                    tr("사람이 멈추라고 했다", "the leader said to stop"), body_stopped=body_stopped
                )
            case "status":
                await self._speak(self.status_ko(), "status")
            case _:
                self.request_text(text)

    async def hear_leader(self, text: str) -> None:
        """The leader's words from outside game chat (the `thorkell play` console): handled like chat."""
        if self.mind is not None:
            # 게임 채팅으로 온 말은 Mind가 이벤트에서 남긴다. 호스트로 온 말은 여기서 남긴다.
            self.mind.store.log_utterance(self.leader_name, text)
        await self._on_leader_chat(text, body_stopped=False)

    # --- requests from chat rules or the voice model's tools -----------------------------------
    def request_text(self, text: str, urgent: bool = False) -> str:
        """Turn the leader's words into a goal. Returns a short factual summary for the voice model.

        Known commands start their tested skill at once. Only new kinds of requests, and wood requests
        without a count (the planner judges the quantity), wait for the planner."""
        intent = intents.read(text)
        planned = (
            intent is None
            or intent.kind not in COMMANDS
            or (intent.kind == "gather_wood" and intent.count is None)
        )
        if self.planner is not None and planned:
            goal = Goal("request", Tier.USER, {"text": text, "urgent": urgent}, source="leader")
            self.request(goal)
            return tr(f"부탁을 받았어: {text}. 계획을 세우는 중.", f"Got the request: {text}. Making a plan.")
        match intent.kind if intent else None:
            case "gather_wood":
                count = (intent.count if intent else None) or DEFAULT_WOOD
                self.request(
                    self._said(Goal("gather_wood", Tier.USER, {"count": count}, source="leader"), text)
                )
                return tr(f"나무 {count}개 모으기로 했어.", f"Going to gather {count} Wood.")
            case "follow":
                self.stance = "follow"
                self.request(Goal("follow", Tier.USER, source="leader"))
                return tr("따라가기로 했어.", "Going to follow you.")
            case "wait":
                self.stance = "wait"
                self.request(Goal("wait", Tier.USER, source="leader"))
                return tr("여기서 기다리기로 했어.", "Going to wait here.")
            case "pick_up":
                self.request(self._said(Goal("pick_up", Tier.USER, source="leader"), text))
                return tr("네가 놓아 준 걸 받으러 갈게.", "I'll go pick up what you put down.")
            case "sleep":
                self.request(self._said(Goal("sleep", Tier.USER, source="leader"), text))
                return tr("그래, 나도 누울게.", "Sure, I'll lie down too.")
        return tr("그 일은 아직 어떻게 하는지 몰라.", "I don't know how to do that yet.")

    @staticmethod
    def _said(goal: Goal, text: str) -> Goal:
        goal.progress["said"] = text
        return goal

    async def cancel_all(self, reason: str, body_stopped: bool = False) -> None:
        await self._drop_all(reason)
        if not body_stopped:
            await self.session.stop_all("leader_stop")
        await self._speak(tr("알겠어, 멈출게.", "Got it, I'll stop."), "stop")

    def status_ko(self) -> str:
        return self._status_ko()

    def _defend(self, attacker: str, name: str | None, size: str | None) -> None:
        # 그냥 두기로 했던 것도 나를 때리면 다시 판단한다.
        self.memory.get("left_alone", set()).discard(attacker)
        if size == "large":
            # 큰 것에게는 반사처럼 달려들지 않는다. 무엇인지, 어떻게 할지 먼저 생각한다.
            # 맞은 순간에는 장면(초당 두 번)에 아직 없을 수 있어서 맞은 이벤트의 덩치를 본다.
            self._face({"id": attacker, "name": name})
            return
        leader = self.session.scene.data.get("leader", {}) if self.session.scene else {}
        self.request(
            Goal(
                "defend",
                Tier.SURVIVAL,
                {"attacker_id": attacker, "name": name, "leader_id": leader.get("id")},
                source="damage_taken",
            )
        )

    async def _threat(self, event: protocol.Event) -> None:
        assert self.decider is not None
        attacker, name = str(event.data["attacker_id"]), event.data.get("attacker_name")
        state = self.session.state.data if self.session.state else None
        scene = self.session.scene.data if self.session.scene else None
        goal = self.current()
        text = decision_state(
            state,
            scene,
            task=goal.describe_ko() if goal else None,
            recent=[f"took {event.data.get('amount')} damage from {name}"],
        )
        hp = (state["hp"] / max(1.0, state["hp_max"])) if state else 1.0
        decided = await self.decider.ask(THREAT_RESPONSE, text, {"hp_fraction": hp})
        choice = decided.choice("threat_response")
        if decided.status != "ok" or choice is None:
            # 마감을 넘기면 숨은 기본 행동은 없다. 몸의 self_defense 반사가 막고, 다음 피격 때 다시 묻는다.
            self._decide(
                "threat",
                goal,
                tr(
                    f"{name} 대응 판단 없음({decided.status}); 반사에 맡김",
                    f"no response decided for {name} ({decided.status}); left to reflexes",
                ),
            )
            return
        self._decide("threat", goal, tr(f"{name} 대응: {choice}", f"response to {name}: {choice}"))
        match choice:
            case "fight" | "equip_best_then_fight":
                self._defend(attacker, name, event.data.get("attacker_size"))
            case "retreat_to_leader":
                self.request(Goal("retreat", Tier.SURVIVAL, {"name": name}, source="threat_response"))
            case "warn_leader_only":
                await self._speak(
                    tr(f"조심해! {josa(str(name), '이가')} 있어!", f"Watch out! {name} here!"), "warn"
                )
            case "avoid_and_continue":
                pass

    # --- arbitration --------------------------------------------------------------------------
    async def _arbitrate(self) -> None:
        if self.active is not None and self.active.task.done():
            await self._complete(self.active)

        fighting = self.active is not None and self.active.goal.kind in ("defend", "retreat")
        eating = any(g.kind == "eat" for g in self.pending) or (
            self.active is not None and self.active.goal.kind == "eat"
        )
        # 먹은 뒤에는 그 음식이 장면(음식 칸)에 보일 때까지 다음 음식을 고르지 않는다.
        # 실게임: 갱신 전에 같은 음식을 또 골라 "지금 못 먹겠어"라고 말했다.
        scene_seq = self.session.scene.seq if self.session.scene else -1
        if not eating and scene_seq > self._ate_at_seq:
            food = food_to_eat(
                SkillContext(self.session, Goal("eat", Tier.SURVIVAL), self.memory), in_danger=fighting
            )
            if food is not None:
                self.request(Goal("eat", Tier.SURVIVAL, {"item": food}, source="survival"))
        self._follow_leader_to_bed()
        self._notice_big()

        if self.pending:
            self.pending.sort(key=lambda g: (g.tier, g.created))
            best = self.pending[0]
            # 계획의 싸움 단계는 맨 위 싸움처럼 생존 목표다. 작은 놈에게 맞거나 배고프다고
            # 보스 싸움을 보류하지 않는다(실게임: 방어에 밀려 보류된 채 죽어 기억에 안 남았다).
            active_tier = Tier.SURVIVAL if self._planned_step() == "fight" else None
            if active_tier is None and self.active is not None:
                active_tier = self.active.goal.tier
            # 멈춰 둔 일이 기다리는 것보다 중요하면 그것부터 다시 한다. 실게임(2026-10-20): 싸운 뒤 기다리던
            # "따라가기"를 먼저 골라, 멈춰 둔 리더의 부탁(나무)을 잊었다.
            waiting_less = (
                self.active is None and bool(self.suspended) and self.suspended[-1].tier < best.tier
            )
            if not waiting_less and (
                self.active is None
                or (active_tier is not None and best.tier < active_tier)
                or (best.tier == Tier.USER and active_tier == Tier.USER)
            ):
                self.pending.pop(0)
                if self.active is not None:
                    await self._suspend_active(
                        tr(f"{best.describe_ko()} 때문에 잠시 멈춤", f"paused for {best.describe_ko()}")
                    )
                await self._adopt(best)

        # 미뤄 둔 리더의 부탁은 하는 일이 없을 때뿐 아니라 덜 중요한 자기 일(따라다니기)을 하는 중에도
        # 다시 본다. 실게임(2026-10-20): 다쳐서 미룬 뒤 쉬며 따라다니다가, 다 나아도 부탁으로 돌아가지 않았다.
        idle_enough = self.active is None or self.active.goal.tier > Tier.USER
        if idle_enough and not any(g.tier <= Tier.USER for g in self.pending):
            self._take_up_deferred()
        if self.active is None:
            self.suspended = [g for g in self.suspended if time.monotonic() - g.created < SUSPENDED_EXPIRY_S]
            if self.suspended:
                goal = self.suspended.pop()
                self._decide(
                    "resume", goal, tr(f"{goal.describe_ko()} 다시 시작", f"back to {goal.describe_ko()}")
                )
                await self._start(goal)
                return
        if self.active is None and not self.pending:
            await self._idle()

    async def _defer(self, goal: Goal, outcome: SkillOutcome) -> None:
        """A planned request stopped by its own abort condition (hurt, dusk, night): not the end of it.
        Real game 2026-10-20: hurt by greylings while chopping, Thorkell dropped two of the leader's
        requests for good. A person patches up and goes back to the job."""
        reason = outcome.code.split(":", 1)[1]
        goal.status = "deferred"
        goal.progress["deferred"] = reason
        for key in ("plan", "step"):
            goal.progress.pop(key, None)
        goal.progress.setdefault("attempts", []).append(outcome.detail_ko)
        self.deferred.append(goal)
        self._decide("suspend", goal, outcome.detail_ko)
        later = (
            tr("다 나으면 이어서 할게.", "I'll get back to it once I've healed.")
            if reason == "hp_below"
            else tr("날이 밝으면 이어서 할게.", "I'll pick it up again in the morning.")
        )
        await self._speak(f"{outcome.detail_ko}. {later}", "report")

    def _take_up_deferred(self) -> None:
        state = self.session.state.data if self.session.state else {}
        env = self.session.scene.data.get("env", {}) if self.session.scene else {}
        for goal in list(self.deferred):
            reason = goal.progress.get("deferred")
            if reason == "hp_below":
                ready = bool(state) and state["hp"] / max(1.0, state["hp_max"]) >= HEALED
            else:
                ready = bool(env) and not env.get("night") and float(env.get("day_fraction", 1.0)) < DUSK
            if ready:
                self.deferred.remove(goal)
                goal.status = "pending"
                goal.progress.pop("deferred", None)
                self._decide(
                    "resume", goal, tr(f"{goal.describe_ko()} 다시", f"back to {goal.describe_ko()}")
                )
                self.request(goal)
                return

    def _face(self, creature: dict[str, Any]) -> None:
        """Something big has noticed Thorkell or hit him: think what it is and how to face it (fight.py)."""
        facing = (
            any(g.kind == "fight" for g in self.pending)
            or (self.active is not None and self.active.goal.kind == "fight")
            or self._planned_step() == "fight"
        )
        name = creature.get("name")
        if not name or facing or time.monotonic() - self._faced_at < FACE_RETRY_S:
            return
        self._faced_at = time.monotonic()
        self.request(Goal("fight", Tier.SURVIVAL, {"creature": str(name)}, source="noticed"))

    def _current_fight(self) -> Goal | None:
        """The fight going on now: the active goal, or the fight step of the active plan."""
        if self.active is None:
            return None
        if self.active.goal.kind == "fight":
            return self.active.goal
        if self._planned_step() != "fight":
            return None
        plan = self.active.goal.progress["plan"]
        step = plan.steps[int(self.active.goal.progress.get("step", 0))]
        child: Goal | None = self.active.goal.progress.get("children", {}).get(step.id)
        return child

    def _planned_step(self) -> str | None:
        """The skill of the plan step the active request is on (a fight in a plan is a fight already)."""
        if self.active is None or self.active.goal.kind != "request":
            return None
        plan = self.active.goal.progress.get("plan")
        index = int(self.active.goal.progress.get("step", 0))
        return plan.steps[index].skill if plan is not None and index < len(plan.steps) else None

    def _notice_big(self) -> None:
        """A big creature close by that has noticed us (its health bar shows), e.g. a summoned boss."""
        state = self.session.state.data if self.session.state else {}
        if state.get("dead") or not self.session.armed:
            return
        left_alone = self.memory.get("left_alone", set())
        for creature in self.session.nearby("creature"):
            if (
                creature.get("size") == "large"
                and creature.get("alerted")
                and creature["distance"] <= NOTICE_BIG_M
                and creature["id"] not in left_alone  # 보고 싸울 상대가 아니라고 판단한 것
            ):
                self._face(creature)
                return

    def _follow_leader_to_bed(self) -> None:
        """The leader lying in bed (seen) means bedtime: the night passes only when every player lies down."""
        leader = self.session.scene.data.get("leader") if self.session.scene else None
        state = self.session.state.data if self.session.state else {}
        if leader is None or not leader.get("in_bed") or state.get("in_bed"):
            return
        sleeping = any(g.kind == "sleep" for g in self.pending) or (
            self.active is not None and self.active.goal.kind == "sleep"
        )
        if sleeping or time.monotonic() - self._sleep_asked_at < SLEEP_RETRY_S:
            return
        self._sleep_asked_at = time.monotonic()
        self.request(Goal("sleep", Tier.USER, source="leader_in_bed"))

    async def _idle(self) -> None:
        """Nothing to do: come back from death, or stay near the leader like a companion."""
        state = self.session.state.data if self.session.state else None
        if state is None or state.get("dead") or not self.session.armed:
            return
        if self._fell_at is not None:
            if self._reflection is not None:
                return  # 죽은 싸움을 돌아보는 중이다. 물건을 어떻게 찾을지 정한 다음에 움직인다.
            fell, self._fell_at = self._fell_at, None
            after, self._after_death = self._after_death, None
            if after == "with_leader":
                self.request(Goal("recover", Tier.USER, {"pos": fell, "with_leader": True}, source="self"))
                return
            await self._speak(tr(DIED_KO, DIED_EN), "death")
            self.request(Goal("recover", Tier.USER, {"pos": fell}, source="self"))
            return
        leader = self.session.scene.data.get("leader") if self.session.scene else None
        far_away = leader is not None and float(leader.get("distance", 0)) > FOLLOW_GAP_M
        on_map = self.session.scene is not None and "leader_on_map" in self.session.scene.data
        if self.stance == "follow" and (far_away or on_map):
            self.request(Goal("follow", Tier.AGENDA, source="self"))

    async def _adopt(self, goal: Goal) -> None:
        self._decide("adopt", goal, tr(f"{goal.describe_ko()} 시작", f"started {goal.describe_ko()}"))
        if goal.kind == "gather_wood" and goal.source == "leader":
            count = goal.args["count"]
            await self._speak(tr(f"나무 {count}개 해 올게.", f"I'll get {count} Wood."), "adopt")
        elif goal.kind in ACKNOWLEDGE_KO and goal.source == "leader":
            await self._speak(tr(ACKNOWLEDGE_KO[goal.kind], ACKNOWLEDGE_EN[goal.kind]), "adopt")
        elif goal.kind == "retreat":
            await self._speak(tr("위험해, 네 쪽으로 갈게!", "This is dangerous, I'm coming to you!"), "adopt")
        await self._start(goal)

    async def _start(self, goal: Goal) -> None:
        goal.status = "active"
        context = SkillContext(
            self.session,
            goal,
            self.memory,
            self.planner,
            self._speak_plain,
            self.mind,
            self.world,
            self.tactician,
            self.eyes,
        )
        run = handle_request if goal.kind == "request" else SKILLS[goal.kind]
        self.active = _Active(goal, asyncio.create_task(run(context)))

    async def _speak_plain(self, text: str) -> None:
        await self._speak(text, "skill")

    async def _suspend_active(self, reason: str) -> None:
        assert self.active is not None
        goal = self.active.goal
        await self._cancel(self.active)
        goal.status = "suspended"
        self.suspended.append(goal)
        self.active = None
        self._decide("suspend", goal, reason)

    async def _drop_all(self, reason: str) -> None:
        if self.active is not None:
            goal = self.active.goal
            await self._cancel(self.active)
            goal.status = "dropped"
            self._decide("drop", goal, reason)
            self.active = None
            for fight in self._fights_in(goal):
                self._reflect_on(fight, "stopped" if fight.status in ("active", "dropped") else fight.outcome)
        for goal in self.suspended + self.pending + self.deferred:
            goal.status = "dropped"
            self._decide("drop", goal, reason)
            for fight in self._fights_in(goal):
                self._reflect_on(fight, "stopped")
        self.suspended.clear()
        self.pending.clear()
        self.deferred.clear()

    async def _cancel(self, active: _Active) -> None:
        active.task.cancel()
        try:
            await active.task
        except asyncio.CancelledError:
            return
        except Exception as error:
            # 이미 실패로 끝난 스킬을 중단하려던 경우다. 목표는 어차피 접히지만 원인은 남긴다.
            log.error("skill %s ended with %s before it could be cancelled", active.goal.kind, error)

    async def _complete(self, active: _Active) -> None:
        goal = active.goal
        self.active = None
        error = active.task.exception()
        if error is not None:
            goal.status = "failed"
            goal.outcome = f"{type(error).__name__}: {error}"
            self._decide(
                "fail",
                goal,
                tr(
                    f"{goal.describe_ko()} 실패: {goal.outcome}",
                    f"{goal.describe_ko()} failed: {goal.outcome}",
                ),
            )
            log.error("skill %s crashed: %s", goal.kind, goal.outcome)
            for fight in self._fights_in(goal):
                # 몸 명령이 시간 안에 안 끝나는 등으로 끊긴 싸움도 겪은 것이다.
                self._reflect_on(fight, "stopped")
            return
        outcome = active.task.result()
        if goal.kind == "request" and outcome.code.startswith("aborted:"):
            await self._defer(goal, outcome)
            return
        if goal.kind == "eat":
            self._ate_at_seq = self.session.scene.seq if self.session.scene else -1
        goal.status = "done" if outcome.ok else "failed"
        goal.outcome = outcome.code
        if outcome.evidence:
            goal.progress["evidence"] = outcome.evidence
        self.finished.append(goal)
        del self.finished[:-FINISHED_KEPT]
        self._decide("done" if outcome.ok else "fail", goal, outcome.detail_ko or goal.describe_ko())
        for fight in self._fights_in(goal):
            self._reflect_on(fight, fight.outcome)
        if goal.tier <= Tier.USER and outcome.detail_ko:
            await self._speak(outcome.detail_ko, "report")
        said = goal.progress.get("said")
        if not outcome.ok and said and self.planner is not None:
            # 바로 시작한 명령이 막히면(나무를 하다 도끼가 부러짐) 거기서 끝내지 않는다. 계획으로 한 부탁처럼
            # 해 본 것과 결과를 들고 리더의 말을 다시 생각한다(실게임 2026-10-19).
            again = Goal("request", Tier.USER, {"text": said, "urgent": False}, source="leader")
            didnt = tr("안 됨", "didn't work")
            again.progress["attempts"] = [
                f"{goal.describe_ko()}: {didnt} — {outcome.detail_ko or outcome.code}"
            ]
            self.request(again)

    # --- learning from fights -----------------------------------------------------------------
    def _note_hit(self, data: dict[str, Any]) -> None:
        now = time.monotonic()
        attacker = str(data.get("attacker_name") or "")
        seen = next((e for e in self.session.nearby("creature") if e["id"] == data.get("attacker_id")), None)
        kinds = sorted(k for k, v in (data.get("types") or {}).items() if float(v) > 0)
        distance = round(float(seen["distance"])) if seen is not None else None
        self._hits.append((now, attacker, round(float(data.get("amount", 0)), 1), distance, kinds))
        self._hits = [hit for hit in self._hits if now - hit[0] <= RECENT_HITS_S]

    def _fights_in(self, goal: Goal) -> list[Goal]:
        """Fights in this goal not yet remembered: the goal itself, or fights that are steps of its plans."""
        fights = [goal, *goal.progress.get("past_children", []), *goal.progress.get("children", {}).values()]
        return [
            f
            for f in fights
            if f.kind == "fight" and "tactic" in f.progress and not f.progress.get("remembered")
        ]

    def _reflect_on(self, goal: Goal, outcome: str) -> None:
        """A fight ended: keep it as an episode in memory and think it over in the background."""
        if self.mind is None or self.tactician is None:
            return
        goal.progress["remembered"] = True
        record = close_record(self.session, goal)
        if outcome == "died":
            record["my_hp_min"] = 0.0
            record.setdefault("my_health", []).append([record.get("seconds", 0.0), 0.0])
        episode = self.mind.store.add_episode(str(goal.args["creature"]), outcome, record)
        followed = list(goal.progress["tactic"].cites)
        self._decide(
            "reflect",
            goal,
            tr(
                f"{episode.id} 기록: {goal.describe_ko()} → {outcome}",
                f"{episode.id} recorded: {goal.describe_ko()} → {outcome}",
            ),
        )
        self._reflection = asyncio.create_task(self._reflect(episode, followed))

    def _reflect_on_death(self) -> None:
        """Died outside a fight Thorkell chose (taken by surprise, or before he had decided how to fight):
        what hit him in the last moments is the episode."""
        if self.mind is None or self.tactician is None:
            return
        hits, self._hits = self._hits, []
        killer = next((hit[1] for hit in reversed(hits) if hit[1]), "")
        began = hits[0][0] if hits else time.monotonic()
        record: dict[str, Any] = {
            "hits": [
                [round(at - began, 1), amount, distance, kinds] for at, _, amount, distance, kinds in hits
            ],
            "attackers": sorted({hit[1] for hit in hits if hit[1]}),
            "seconds": round(time.monotonic() - began, 1),
            "my_hp_min": 0.0,
        }
        seen = next((e for e in self.session.nearby("creature") if e.get("name") == killer), None)
        if seen is not None:
            record["looks"] = describe_looks(seen)
        episode = self.mind.store.add_episode(killer or general(), "died", record)
        self._decide(
            "reflect",
            None,
            tr(
                f"{episode.id} 기록: {killer or '알 수 없는 것'}에게 죽음",
                f"{episode.id} recorded: killed by {killer or 'something unknown'}",
            ),
        )
        self._reflection = asyncio.create_task(self._reflect(episode, []))

    async def _reflect(self, episode: Episode, followed: list[str]) -> None:
        assert self.mind is not None and self.tactician is not None
        store = self.mind.store
        earlier = [e for e in store.episodes(episode.about, limit=4) if e.id != episode.id][-3:]
        try:
            reflection = await self.tactician.reflect(
                episode, earlier, self.mind.lessons_for(episode.about), followed
            )
        except (ModelError, JudgmentRejected) as error:
            log.error("reflection on %s failed: %s", episode.id, error)
            self._decide(
                "reflect",
                None,
                tr(f"{episode.id} 회고 실패: {error}", f"{episode.id} reflection failed: {error}"),
            )
            await self._speak(
                tr(
                    f"방금 싸움을 돌아보려는데 생각이 정리가 안 돼({error})",
                    f"I tried to think back on that fight, but I can't sort it out ({error})",
                ),
                "reflect",
            )
            return
        judged = [store.judge_lesson(v.lesson_id, v.held)[1] for v in reflection.verdicts]
        learned = [store.add_lesson(n.about, n.text_ko, episode.id) for n in reflection.lessons]
        none = tr("없음", "none")
        self._decide(
            "reflect",
            None,
            tr(f"{episode.id} 회고: ", f"{episode.id} reflection: ")
            + reflection.what_happened_ko
            + tr(" | 새 교훈: ", " | new lessons: ")
            + ("; ".join(f"{n.id} {n.text}" for n in learned) or none)
            + tr(" | 판정: ", " | verdicts: ")
            + ("; ".join(f"{j.id} {j.status}" for j in judged) or none),
        )
        if episode.outcome == "died":
            self._after_death = reflection.after_death
        await self._until_risen()
        await self._speak(reflection.speech_ko, "reflect")

    async def _until_risen(self) -> None:
        """A dead Thorkell cannot speak (the body is not armed until he rises at the spawn)."""

        def risen() -> bool:
            state = self.session.state
            return (
                state is not None
                and state.seq > self._death_state_seq
                and self.session.armed
                and not state.data.get("dead")
            )

        try:
            await self.session.wait_for(risen, RISE_WAIT_S)
        except TimeoutError:
            log.error("still not risen after %.0fs; speaking anyway", RISE_WAIT_S)

    # --- speech -------------------------------------------------------------------------------
    def _decide(self, kind: str, goal: Goal | None, reason: str, talker: str | None = None) -> Decision:
        decision = Decision(
            kind, goal.id if goal else None, reason, goal_kind=goal.kind if goal else None, talker=talker
        )
        self.decisions.append(decision)
        log.info("decision %s %s: %s", decision.kind, decision.goal_id, reason)
        return decision

    async def _speak(self, text: str, why: str, talker: str = "normal") -> None:
        if talker == "normal" and not self._leader_within(NORMAL_EARSHOT_M):
            talker = "shout"  # 리더가 멀면 외쳐야 답이 닿는다(외침은 모두에게 보인다)
        self._decide("speak", self.current(), f"[{why}] {text}", talker)
        if self.mind is not None:
            self.mind.store.log_utterance("Thorkell", text)
        if self.say is not None:
            await self.say(text, talker)
            return
        try:
            await self.session.command("say", {"talker": talker, "text": text}, timeout=5)
        except (CommandRejected, TimeoutError) as error:
            log.error("could not speak %r: %r", text, error)

    def _leader_within(self, metres: float) -> bool:
        leader = self.session.scene.data.get("leader") if self.session.scene else None
        return leader is not None and float(leader.get("distance", float("inf"))) <= metres

    def _status_ko(self) -> str:
        goal = self.current()
        upcoming = sorted(self.pending, key=lambda g: (g.tier, g.created))
        if goal is None:
            if upcoming:
                soon = upcoming[0].describe_ko()
                return tr(f"곧 {soon} 시작할 거야.", f"I'll start {soon} soon.")
            return tr(
                "지금은 하는 일 없어. 시킬 거 있어?", "Not doing anything right now. Got something for me?"
            )
        doing = goal.describe_ko()
        if upcoming:
            then = upcoming[0].describe_ko()
            return tr(f"{doing} 하는 중이야. 끝나면 {then} 할게.", f"I'm {doing}. After that, {then}.")
        if self.suspended:
            back = self.suspended[-1].describe_ko()
            return tr(
                f"{doing} 하는 중이야. 끝나면 {back} 이어서 할게.",
                f"I'm {doing}. After that I'll get back to {back}.",
            )
        return tr(f"{doing} 하는 중이야.", f"I'm {doing}.")
