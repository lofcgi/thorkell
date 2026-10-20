"""Decision points: where the brain asks a fast typed question instead of a slow planner.

Each point fixes its question(s), options (<= 20 so laya can match later) and deadline. What happens
when no answer arrives in time is decided by the caller per point — there is no hidden default.
"""

from __future__ import annotations

from dataclasses import dataclass

from thorkell.models.systemone import Question

THREAT_OPTIONS = {
    "fight": "attack the creature that is threatening Thorkell with what is equipped",
    "equip_best_then_fight": "switch to the most suitable weapon first, then attack",
    "retreat_to_leader": "run back to the leader for help",
    "avoid_and_continue": "ignore it and keep doing the current task",
    "warn_leader_only": "shout a warning to the leader but keep working",
}

SPEAK_LEVELS = ["not worth saying", "minor", "somewhat interesting", "interesting", "important to say now"]


@dataclass(frozen=True)
class Point:
    name: str
    deadline_s: float
    questions: dict[str, Question]


THREAT_RESPONSE = Point(
    "threat_response",
    0.6,
    {
        "threat_response": Question(
            "choice",
            "Thorkell is a companion who has never played this game before. A creature is threatening or "
            "attacking him. Pick what he should do right now given his health, weapon and the task.",
            THREAT_OPTIONS,
        )
    },
)

def threat_response(beside_leader: bool) -> Point:
    """The threat question with only the options that can be done now. Beside the leader, running back to
    the leader is not one: in the real game (2026-10-20) Jev picked it on every hit while Thorkell stood 3 m
    from the leader, so the retreat ended at once and he never fought back."""
    if not beside_leader:
        return THREAT_RESPONSE
    options = {k: v for k, v in THREAT_OPTIONS.items() if k != "retreat_to_leader"}
    question = THREAT_RESPONSE.questions["threat_response"]
    return Point(
        THREAT_RESPONSE.name,
        THREAT_RESPONSE.deadline_s,
        {"threat_response": Question(question.type, question.instructions, options)},
    )


SPEAK_WORTHY = Point(
    "speak_worthy",
    0.8,
    {
        "speak_worthy": Question(
            "score",
            "Thorkell noticed something. Would a friendly first-time player say this out loud "
            "to the leader now?",
            SPEAK_LEVELS,
        )
    },
)

INTENT_GUARD = Point(
    "intent_guard",
    0.6,
    {
        "explicit_request": Question(
            "noul",
            "Did the leader explicitly ask Thorkell to do this action in their last words (not a joke, "
            "not a question, not a hypothetical)?",
        )
    },
)

POINTS = {p.name: p for p in (THREAT_RESPONSE, SPEAK_WORTHY, INTENT_GUARD)}
