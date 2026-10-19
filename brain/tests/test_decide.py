from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from thorkell.decide.points import INTENT_GUARD, THREAT_RESPONSE, Point
from thorkell.decide.runner import Breaker, DecisionRunner, RuleDecider
from thorkell.models.systemone import Answer, SystemOneError
from thorkell.world.serialize import MAX_CHARS, decision_state

STATE = {"hp": 18.0, "hp_max": 25.0, "stamina": 30.0, "stamina_max": 50.0, "swimming": False}
SCENE = {
    "biome": "초원",
    "env": {"night": False, "day_fraction": 0.41},
    "inventory": [
        {"name": "돌도끼", "stack": 1, "equipped": True},
        {"name": "곤봉", "stack": 1, "equipped": False},
        {"name": "라즈베리", "stack": 3, "equipped": False},
    ],
    "nearby": [
        {"kind": "creature", "name": "그레이드워프", "distance": 6.2, "health": 0.8, "alerted": True},
        {"kind": "tree", "name": "", "distance": 3.0},
    ],
    "leader": {"name": "Leader", "distance": 12.0},
}


def test_state_text_is_compact_and_precomputed() -> None:
    text = decision_state(STATE, SCENE, task="gather wood 4/10", recent=["took 4 damage from 그레이드워프"])
    assert text.splitlines() == [
        "SELF hp 18/25 (72%) stamina 30/50",
        "TIME day day_fraction 0.41 biome 초원",
        "EQUIPPED 돌도끼",
        "CARRY 곤봉 x1, 라즈베리 x3",
        "CREATURE [1] 그레이드워프 dist 6.2 health 80% alerted",
        "LEADER Leader dist 12",
        "TASK gather wood 4/10",
        "RECENT took 4 damage from 그레이드워프",
    ]


def test_state_text_is_capped() -> None:
    long_scene = {**SCENE, "inventory": [{"name": "x" * 300, "stack": 1, "equipped": False}] * 12}
    assert len(decision_state(STATE, long_scene, recent=["y" * 500] * 5)) <= MAX_CHARS


class FakeDecider:
    def __init__(self, name: str = "jev", delay: float = 0.0, fail: bool = False) -> None:
        self.name = name
        self.delay = delay
        self.fail = fail
        self.calls = 0

    async def decide(self, point: Point, state: str, context: dict[str, Any]) -> dict[str, Answer]:
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.fail:
            raise SystemOneError("boom")
        return {"threat_response": Answer(choice="fight", probabilities={"fight": 0.9}, confidence=0.9)}


async def test_answers_are_logged_for_distillation(tmp_path: Path) -> None:
    log = tmp_path / "decisions.jsonl"
    runner = DecisionRunner({"threat_response": FakeDecider()}, log)
    decided = await runner.ask(THREAT_RESPONSE, "SELF hp 18/25")
    assert decided.status == "ok"
    assert decided.choice("threat_response") == "fight"
    record = json.loads(log.read_text())
    assert record["state"] == "SELF hp 18/25"
    assert record["questions"]["threat_response"]["type"] == "choice"
    assert record["answers"]["threat_response"]["choice"] == "fight"
    assert record["backend"] == "jev"


async def test_deadline_is_a_timeout_not_a_default() -> None:
    runner = DecisionRunner({"threat_response": FakeDecider(delay=2.0)})
    decided = await runner.ask(THREAT_RESPONSE, "s")
    assert decided.status == "timeout"
    assert decided.answers == {}
    assert decided.choice("threat_response") is None


async def test_breaker_opens_after_three_failures_and_notifies() -> None:
    failing = FakeDecider(fail=True)
    runner = DecisionRunner({"threat_response": failing})
    opened: list[bool] = []
    runner.on_breaker_open = lambda: opened.append(True)
    for _ in range(3):
        assert (await runner.ask(THREAT_RESPONSE, "s")).status == "error"
    assert opened == [True]
    assert (await runner.ask(THREAT_RESPONSE, "s")).status == "breaker_open"
    assert failing.calls == 3


def test_breaker_window_and_cooldown() -> None:
    now = [0.0]
    breaker = Breaker(failures=3, window_s=30, cooldown_s=60, clock=lambda: now[0])
    assert not breaker.record_failure()  # t=0
    now[0] = 40
    assert not breaker.record_failure()  # t=0 fell out of the window
    assert not breaker.record_failure()
    assert breaker.record_failure()  # third within 30 s opens it
    now[0] = 99
    assert breaker.open
    now[0] = 100.5
    assert not breaker.open


async def test_rule_decider_is_explicit_and_deterministic() -> None:
    runner = DecisionRunner({"threat_response": RuleDecider(), "intent_guard": RuleDecider()})
    assert (await runner.ask(THREAT_RESPONSE, "s", {"hp_fraction": 0.2})).choice("threat_response") == (
        "retreat_to_leader"
    )
    assert (await runner.ask(THREAT_RESPONSE, "s", {"hp_fraction": 0.9})).choice("threat_response") == (
        "equip_best_then_fight"
    )
    guard = await runner.ask(INTENT_GUARD, "s", {"matched_intent": True})
    assert guard.answers["explicit_request"].noul == 1.0
