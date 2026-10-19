"""Tools the conversational (Live) model may call. It delegates to the controller and never moves
the body directly, so speech can only promise what the controller actually accepted.

Side-effecting tools pass `intent_guard` first: if the leader's last words do not look like an explicit
request, the call is refused as "unverified" and the model should ask to confirm.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from thorkell import lang
from thorkell.control.controller import Controller
from thorkell.decide.points import INTENT_GUARD
from thorkell.decide.runner import DecisionRunner
from thorkell.lang import tr
from thorkell.world.serialize import decision_state

log = logging.getLogger(__name__)

SIDE_EFFECTS = {"set_goal", "cancel"}

DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "set_goal",
        "description": (
            "리더가 시킨 일을 컨트롤러에 맡긴다. "
            "결과(accepted/queued/rejected)를 받은 뒤에만 '할게'라고 말한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "request_ko": {"type": "string", "description": "리더의 요청을 한 문장으로"},
                "urgent": {"type": "boolean", "description": "'지금', '먼저'처럼 당장 하라고 했으면 true"},
            },
            "required": ["request_ko"],
        },
        "behavior": "NON_BLOCKING",
    },
    {
        "name": "cancel",
        "description": "리더가 멈추라거나 그만하라고 했을 때 하던 일을 모두 멈춘다.",
        "parameters": {"type": "object", "properties": {"reason_ko": {"type": "string"}}},
        "behavior": "NON_BLOCKING",
    },
    {
        "name": "ask_status",
        "description": "지금 무엇을 하고 있는지, 다음에 무엇을 할지 확인한다(사실만 돌려준다).",
        "parameters": {"type": "object", "properties": {}},
        "behavior": "BLOCKING",
    },
    {
        "name": "recall_knowledge",
        "description": "게임에 대해 Thorkell이 직접 겪거나 들어서 아는 것을 찾는다. 모르면 모른다고 한다.",
        "parameters": {
            "type": "object",
            "properties": {"query_ko": {"type": "string", "description": "예: 그레이드워프 약점"}},
            "required": ["query_ko"],
        },
        "behavior": "BLOCKING",
    },
    {
        "name": "teach_fact",
        "description": "리더가 게임에 대해 알려 준 사실을 기억한다. 확인 전까지는 '들은 것'으로 남는다.",
        "parameters": {
            "type": "object",
            "properties": {"statement_ko": {"type": "string"}},
            "required": ["statement_ko"],
        },
        "behavior": "NON_BLOCKING",
    },
]

# 영어로 플레이할 때의 설명. 인자 이름(..._ko)은 그대로 두고 값은 영어로 받는다.
DECLARATIONS_EN: list[dict[str, Any]] = [
    {
        "name": "set_goal",
        "description": (
            "Hand what the leader asked for to the controller. "
            "Say 'I'll do it' only after you get the result (accepted/queued/rejected)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "request_ko": {"type": "string", "description": "The leader's request in one sentence"},
                "urgent": {
                    "type": "boolean",
                    "description": "true if they said to do it right away, like 'now' or 'first'",
                },
            },
            "required": ["request_ko"],
        },
        "behavior": "NON_BLOCKING",
    },
    {
        "name": "cancel",
        "description": "Stop everything you are doing when the leader says to stop or quit it.",
        "parameters": {"type": "object", "properties": {"reason_ko": {"type": "string"}}},
        "behavior": "NON_BLOCKING",
    },
    {
        "name": "ask_status",
        "description": "Check what you are doing now and what you will do next (returns facts only).",
        "parameters": {"type": "object", "properties": {}},
        "behavior": "BLOCKING",
    },
    {
        "name": "recall_knowledge",
        "description": (
            "Look up what Thorkell knows about the game from his own experience or from being told. "
            "If he doesn't know, say so."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query_ko": {"type": "string", "description": "e.g. greydwarf weakness"}},
            "required": ["query_ko"],
        },
        "behavior": "BLOCKING",
    },
    {
        "name": "teach_fact",
        "description": (
            "Remember a fact about the game the leader told you. Until it is confirmed it stays as 'heard'."
        ),
        "parameters": {
            "type": "object",
            "properties": {"statement_ko": {"type": "string"}},
            "required": ["statement_ko"],
        },
        "behavior": "NON_BLOCKING",
    },
]


def declarations() -> list[dict[str, Any]]:
    """The tools as the voice model reads them, in the language being played."""
    return DECLARATIONS_EN if lang.current() == "en" else DECLARATIONS


class ToolBridge:
    def __init__(
        self,
        controller: Controller,
        decider: DecisionRunner | None,
        last_leader_words: Callable[[], str],
    ) -> None:
        self.controller = controller
        self.decider = decider
        self.last_leader_words = last_leader_words

    async def call(self, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Returns (response, scheduling). Unknown tools are errors reported back to the model."""
        if name in SIDE_EFFECTS and not await self._explicit(name, args):
            say = tr(
                "정말 그렇게 할까? 한 번만 확인해 줘.", "You really want me to do that? Just confirm once."
            )
            return {"status": "unverified", "say_ko": say}, "WHEN_IDLE"
        match name:
            case "set_goal":
                summary = self.controller.request_text(
                    str(args["request_ko"]), urgent=bool(args.get("urgent"))
                )
                return {"status": "accepted", "summary_ko": summary}, "WHEN_IDLE"
            case "cancel":
                reason = args.get("reason_ko") or tr("리더가 멈추라고 했다", "the leader said to stop")
                await self.controller.cancel_all(str(reason))
                return {"status": "cancelled"}, "WHEN_IDLE"
            case "ask_status":
                return {"status_ko": self.controller.status_ko()}, "WHEN_IDLE"
            case "recall_knowledge":
                mind = self.controller.mind
                answer = (
                    mind.recall(str(args["query_ko"]))
                    if mind is not None
                    else tr("기억 장치가 꺼져 있어", "my memory is switched off")
                )
                return {"answer_ko": answer}, "WHEN_IDLE"
            case "teach_fact":
                mind = self.controller.mind
                reply = mind.hear(str(args["statement_ko"])) if mind is not None else None
                return {
                    "stored": reply is not None,
                    "reply_ko": reply or tr("어떤 사실인지 잘 모르겠어", "I'm not sure what the fact is"),
                }, "WHEN_IDLE"
        log.error("unknown tool %s", name)
        return {"error": f"unknown tool {name}"}, "WHEN_IDLE"

    async def _explicit(self, name: str, args: dict[str, Any]) -> bool:
        if self.decider is None:
            return True
        words = self.last_leader_words()
        session = self.controller.session
        state = decision_state(
            session.state.data if session.state else None,
            session.scene.data if session.scene else None,
            recent=[f"leader said: {words}", f"tool: {name} {args}"],
        )
        decided = await self.decider.ask(INTENT_GUARD, state, {"matched_intent": bool(words.strip())})
        answer = decided.answers.get("explicit_request")
        if decided.status != "ok" or answer is None or answer.noul is None:
            log.warning("intent_guard %s for %s: refusing until the leader confirms", decided.status, name)
            return False
        return answer.noul >= 0.5
