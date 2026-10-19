from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from thorkell.ops import scenario


def test_host_chat_lines_are_read_with_the_name_the_human_sees(tmp_path: Path) -> None:
    # Terminal.AddString(title, text, type)가 만드는 모양 그대로다(외침은 노란색, 일반은 흰색).
    lines = [
        "/w [text] - 귓속말",
        "<color=orange>Thorkell</color>: <color=#FFEB04FF>내가 왔다!</color>",
        "<color=orange>Leader</color>: <color=#FFFFFFFF>토르켈, 따라와</color>",
    ]
    (tmp_path / "host-chat.jsonl").write_text(
        "".join(json.dumps({"line": line}, ensure_ascii=False) + "\n" for line in lines)
    )
    host = SimpleNamespace(root=tmp_path)
    assert scenario.host_chat(host) == [("Thorkell", "내가 왔다!"), ("Leader", "토르켈, 따라와")]  # type: ignore[arg-type]


def test_the_leaders_own_arrival_shout_is_not_counted_as_a_misnamed_thorkell_line() -> None:
    # 실게임(2026-10-17): 리더가 먼저 접속하면 게임이 리더 이름으로 "내가 왔다!"를 외친다.
    # 토르켈의 말이 아니다.
    lines = [("Leader", "내가 왔다!"), ("Thorkell", "내가 왔다!")]
    assert scenario.misnamed_after_arrival(lines, leader="Leader", bot="Thorkell") == []
    wrong = [("Leader", "내가 왔다!"), ("Leader", "내가 왔다!"), ("Thorkell", "안녕")]
    assert scenario.misnamed_after_arrival(wrong, leader="Leader", bot="Thorkell") == ["내가 왔다!"]
