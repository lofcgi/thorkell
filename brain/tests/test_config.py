from __future__ import annotations

from pathlib import Path

import pytest

from thorkell.config import ConfigError, load


def test_minimal_thinking_is_rejected_up_front(tmp_path: Path) -> None:
    # gemini-3.8-flash는 thinking_level minimal을 400으로 거절한다(2026-10-02 계약 확인).
    # 실행 중이 아니라 설정을 읽을 때 막는다.
    path = tmp_path / "thorkell.toml"
    path.write_text('[planner]\nbackend = "gemini"\nthinking = "minimal"\n')
    with pytest.raises(ConfigError):
        load(path)


def test_low_thinking_is_the_default() -> None:
    assert load(None).planner.thinking == "low"
