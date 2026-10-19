"""The fixed phrases the controller acts on without the planner."""

from __future__ import annotations

import pytest

from thorkell.control import intents


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("뭐해?", "status"),
        ("지금 뭐 하고 있어?", "status"),
        ("나무 잘 돼 가?", "status"),
        ("토르켈 멈춰", "stop"),
        ("따라와", "follow"),
        ("여기서 기다려", "wait"),
        ("나무 10개 캐줘", "gather_wood"),
        ("이제 자자", "sleep"),
        ("자러 가자", "sleep"),
    ],
)
def test_fixed_phrases(text: str, kind: str) -> None:
    read = intents.read(text)
    assert read is not None and read.kind == kind


@pytest.mark.parametrize("text", ["오늘 기분 어때?", "이 집 어때?", "안녕 토르켈"])
def test_small_talk_is_left_to_the_planner(text: str) -> None:
    # 실제 플래너 평가(thorkell judge)에서 "오늘 기분 어때?"가 상태 질문으로 잡혀
    # "지금은 하는 일 없어"라고 답했다.
    assert intents.read(text) is None
