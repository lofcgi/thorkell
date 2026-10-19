"""Fight judgment and lessons: what the model is asked, what the validator refuses, how lessons move."""

from __future__ import annotations

import pytest
from conftest import ScriptedModel, reflection, tactic

from thorkell.mind.mind import Mind
from thorkell.mind.store import GENERAL, Store
from thorkell.plan.tactics import (
    FightView,
    JudgmentRejected,
    Tactic,
    Tactician,
    check_tactic,
    episode_line,
    record_ko,
)

VIEW = FightView(
    "에이크쉬르", "에이크쉬르: 키 약 3m, 화면 위쪽에 큰 체력바와 이름이 떴다", "체력 60/60", "40m", True
)


def test_a_lesson_is_a_hypothesis_until_later_fights_judge_it() -> None:
    store = Store()
    episode = store.add_episode("에이크쉬르", "died", {"hits": []})
    lesson = store.add_lesson("에이크쉬르", "멀리서 쏘자", episode.id)
    assert (lesson.id, lesson.status, lesson.learned_from) == ("L1", "hypothesis", "E1")
    assert store.judge_lesson("L1", held=True)[1].status == "supported"
    store.judge_lesson("L1", held=True)
    assert store.judge_lesson("L1", held=True)[1].status == "verified"
    wrong = store.add_lesson(GENERAL, "맨손으로 싸우자", episode.id)
    store.judge_lesson(wrong.id, held=False)
    assert store.judge_lesson(wrong.id, held=False)[1].status == "refuted"
    assert [lesson.id for lesson in store.lessons()] == ["L1"]
    assert store.lessons(("사슴",)) == []


def test_episodes_come_back_oldest_first_and_only_the_latest() -> None:
    store = Store()
    for outcome in ("died", "died", "lost", "killed"):
        store.add_episode("에이크쉬르", outcome, {})
    store.add_episode("멧돼지", "killed", {})
    assert [e.outcome for e in store.episodes("에이크쉬르")] == ["died", "lost", "killed"]


def test_the_validator_refuses_numbers_that_do_not_make_sense() -> None:
    def problems(**overrides: object) -> list[str]:
        return check_tactic(Tactic.model_validate(tactic(**overrides)), True, {"L1"})

    assert problems() == []
    assert problems(close_m=30.0)  # 지킬 거리보다 먼 곳에서 구른다
    assert problems(retreat_hp=0.8, return_hp=0.5)
    assert problems(retreat_hp=35.0, return_hp=70.0)  # 비율이 아니라 퍼센트
    assert problems(cites=["L9"])
    assert problems(style="sing")
    assert check_tactic(Tactic.model_validate(tactic()), False, set())  # 활 없이 ranged
    assert problems(style="melee", close_m=40.0) == []  # melee는 구르는 거리를 쓰지 않는다
    assert problems(hits_then_back=0) == []  # 활 싸움은 치고 빠지는 횟수를 쓰지 않는다(실제 모델이 0을 줬다)
    assert problems(style="melee", hits_then_back=0)
    assert problems(dodge_within_m=-1.0)
    assert problems(dodge_within_m=80.0)


async def test_a_rejected_tactic_gets_one_repair_with_the_problems() -> None:
    model = ScriptedModel(tactic(close_m=30.0), tactic())
    decided = await Tactician(model).tactic(VIEW, [], [])
    assert decided.close_m == 14.0
    assert "close_m" in model.prompts[1] and "고쳐서 다시" in model.prompts[1]


async def test_two_bad_answers_are_a_failure_not_a_default() -> None:
    model = ScriptedModel(tactic(close_m=30.0), tactic(close_m=40.0))
    with pytest.raises(JudgmentRejected):
        await Tactician(model).tactic(VIEW, [], [])


async def test_the_tactic_question_shows_earlier_fights_and_lessons() -> None:
    store = Store()
    episode = store.add_episode(
        "에이크쉬르",
        "died",
        {"hits": [[3.0, 6.0, 15, ["lightning"]]], "shots": {"fired": 9}, "seconds": 40.0, "tactic": tactic()},
    )
    lesson = store.add_lesson("에이크쉬르", "16m 안은 번개가 닿는다", episode.id)
    model = ScriptedModel(tactic(cites=["L1"]))
    decided = await Tactician(model).tactic(VIEW, [episode], [lesson])
    assert decided.cites == ["L1"]
    prompt = model.prompts[0]
    assert "에이크쉬르와 싸운 기억" in prompt
    assert "E1 (died, 40초), 맞은 것 1번(15~15m에서), 화살 9발, 쓴 방법: 활로 24m" in prompt
    assert "L1 [에이크쉬르] 16m 안은 번개가 닿는다 (hypothesis; E1에서 배움; 맞았음 0번)" in prompt


async def test_a_death_must_end_in_a_choice_about_the_tombstone() -> None:
    store = Store()
    episode = store.add_episode("에이크쉬르", "died", {"hits": [], "seconds": 5.0})
    model = ScriptedModel(reflection(), reflection(after_death="with_leader"))
    thought = await Tactician(model).reflect(episode, [], [], [])
    assert thought.after_death == "with_leader"
    assert "after_death" in model.prompts[1]


async def test_verdicts_on_any_lesson_the_fight_showed_true_or_false() -> None:
    # 실게임(2026-10-18): 전술이 아무 교훈도 인용하지 않았지만 실제로는 "30m 넘게 떨어져라"대로 싸웠고,
    # 쏠 틈 없이 졌다. 인용한 교훈만 판정하면 그 교훈은 계속 남아 다음에도 멀리 떨어지게 한다.
    store = Store()
    episode = store.add_episode("에이크쉬르", "died", {"hits": [], "seconds": 5.0})
    lessons = [
        store.add_lesson("에이크쉬르", "30m 넘게 떨어져서 쏘자", "E0"),
        store.add_lesson(GENERAL, "먹고 싸우자", "E0"),
    ]
    model = ScriptedModel(
        reflection(verdicts=[{"lesson_id": "L9", "held": False}], after_death="with_leader"),
        reflection(verdicts=[{"lesson_id": "L1", "held": False}], after_death="with_leader"),
    )
    thought = await Tactician(model).reflect(episode, [], lessons, [])
    assert [v.lesson_id for v in thought.verdicts] == ["L1"]
    assert "L9" in model.prompts[1]  # 보여 주지 않은 교훈은 판정할 수 없다


def test_the_record_reads_like_what_a_player_remembers() -> None:
    store = Store()
    episode = store.add_episode(
        "에이크쉬르",
        "died",
        {
            "looks": "키 약 3m, 화면 위쪽에 큰 체력바와 이름이 떴다",
            "tactic": tactic(),
            "hits": [[4.5, 6.0, 15, ["lightning"]], [9.0, 12.0, None, ["blunt"]]],
            "shots": {"fired": 7},
            "health": [[0.0, 1.0], [8.0, 0.9]],
            "my_hp_min": 0.0,
            "food_slots": 1,
            "retreats": 3,
            "recovering_s": 95.4,
            "my_health": [[0.0, 1.0], [4.5, 0.9], [9.0, 0.7]],
            "others": [[7.0, 8.1, "멧돼지", ["blunt"]], [8.0, 9.0, "멧돼지", ["blunt"]]],
            "saw_attacks": 3,
            "dodged": 2,
            "time": {"shoot": [7, 21.4], "back_off": [4, 30.2], "roll": [2, 1.9]},
            "tactic_changes": [[10.5, tactic(style="melee", keep_m=6.0, hits_then_back=3)]],
            "handled": ["멧돼지"],
            "seconds": 12.0,
        },
    )
    text = record_ko(episode)
    assert "체력이 낮아 물러난 것: 3번, 모두 95초(그동안은 싸우지 않았다)" in text
    assert "내 체력: 0초 100%, 4.5초 90%, 9초 70%" in text
    assert "다른 놈에게 맞은 것: 멧돼지 2번(모두 17.1) (처음 7초, 마지막 8초)" in text
    assert "싸우다 먼저 상대한 다른 놈: 멧돼지" in text
    assert "상대의 공격 동작을 본 것: 3번, 보고 구른 것: 2번" in text
    assert "한 일: 물러나기 4번 30초, 쏘기 7번 21초, 구르기 2번 2초" in text
    assert "10.5초에 바꾼 방법: 붙어서 3번 치고 6m 물러나기" in text
    assert "다른 놈에게 맞은 것 2번" in episode_line(episode)
    # 전술을 고를 때 지난 전술로 시간을 어디에 썼는지 본다(35m·20m로 했더니 물러나기만 했다).
    assert "한 일: 물러나기 30초, 쏘기 21초, 구르기 2초" in episode_line(episode)
    assert "물러나 있던 시간 95초" in episode_line(episode)
    assert "4.5초 6 (15m, 번개)" in text and "9초 12 (거리 모름, 둔기)" in text
    assert "활로 24m 거리 두기, 14m 안이면 물러나기, 체력 35% 아래면 물러나 회복, 70%에서 복귀" in text
    assert "음식 칸: 싸움에 들어갈 때 1칸" in text and "상대 체력바: 0초 100%, 8초 90%" in text


def test_the_planner_sees_lessons_and_may_cite_them() -> None:
    mind = Mind(Store())
    mind.store.add_lesson("에이크쉬르", "보스 부르기 전에 음식 세 칸을 채우자", "E1")
    lines, ids = mind.facts_for_prompt()
    assert any("음식 세 칸" in line for line in lines)
    assert "L1" in ids


async def test_the_fight_judge_cases_accept_the_answers_they_describe() -> None:
    from thorkell.ops.judgment import FIGHT_CASES, _run_fight_case

    answers = {
        "boss_seen": tactic(),
        "boss_again": tactic(keep_m=28.0, close_m=18.0, cites=["L1", "L2"]),
        "boss_lost": reflection(
            lessons=[{"about": "에이크쉬르", "text_ko": "16m 안에서 번개를 맞았다. 25m 밖에서 쏘자"}],
            after_death="with_leader",
        ),
        "boss_alone": tactic(retreat_to_leader=False),
        "boss_together": tactic(),
        "summon_said": tactic(style="leave", speech_ko="네가 부른 거구나, 그냥 둘게"),
        "boss_stalled": reflection(
            what_happened_ko="78%로 깎았지만 물러나 있던 65초 동안 회복도 못 하고 상대만 80%로 회복했다",
            after_death="with_leader",
        ),
    }
    for case in FIGHT_CASES:
        model = ScriptedModel(answers[case.name])
        result = await _run_fight_case(case, Tactician(model))
        assert result["ok"], result
        if case.name in ("boss_alone", "boss_together"):
            assert "리더가 최근에 한 말" in model.prompts[0]
