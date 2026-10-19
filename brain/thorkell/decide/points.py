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
