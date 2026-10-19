from __future__ import annotations

import asyncio
import io
import json
import stat
from datetime import datetime
from pathlib import Path

import pytest
from test_backup import _sources
from test_runtime import _fake_bepinex, _fake_game, _plugins

from thorkell.ops import backup, play, runtime


def test_server_password_is_kept_private_and_follows_the_game_rule(tmp_path: Path) -> None:
    path = tmp_path / "secrets/server-password"
    assert play.stored_password(path) is None
    with pytest.raises(play.PlayError, match="5"):
        play.save_password("abc", path)
    assert not path.exists()
    play.save_password("skal-vikings", path)
    assert play.stored_password(path) == "skal-vikings"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


async def test_json_ui_writes_one_object_per_line_and_reads_commands() -> None:
    out = io.StringIO()
    commands = io.StringIO(
        "\n".join(
            [
                json.dumps({"type": "password", "value": "skal-vikings"}),
                json.dumps({"type": "say", "text": "따라와"}),
                "not json",
                json.dumps({"type": "status"}),
                json.dumps({"type": "quit"}),
            ]
        )
        + "\n"
    )
    ui = play.JsonUi(out=out, inp=commands)
    ui.attach(asyncio.get_running_loop())
    assert await asyncio.wait_for(ui.ask_password(None), 2) == "skal-vikings"
    lines = ui.lines()
    assert [await asyncio.wait_for(lines.get(), 2) for _ in range(3)] == ["따라와", "/status", None]
    ui.emit("thorkell", "나무 10개 해 올게.")
    messages = [json.loads(line) for line in out.getvalue().splitlines()]
    # 읽는 스레드의 경고와 비밀번호 요청은 순서가 정해져 있지 않다.
    assert sorted(m["type"] for m in messages[:-1]) == ["need_password", "warn"]
    assert messages[-1] == {"type": "thorkell", "text": "나무 10개 해 올게."}


def test_rehearsal_host_is_seeded_once_from_the_backup(tmp_path: Path) -> None:
    saves, cloud = _sources(tmp_path)
    made = backup.create(
        tmp_path / "backups",
        saves=saves,
        cloud_roots=[cloud],
        prefs=lambda dest: dest.write_bytes(b"<plist/>"),
        now=datetime(2026, 10, 2, 13, 0),
    )
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    root = tmp_path / "runtimes/rehearsal-host"

    host, created = play.prepare_rehearsal_host(root, game, pack, [plugins], made, "helloworld", "ko")
    assert created and host.role == "host-rehearsal"
    assert (host.saves / "worlds_local/helloworld/_main.51.fwl2").read_bytes() == b"meta"
    assert (host.saves / "characters_local/viking.fch").is_file()
    seeded = json.loads((host.root / "seeded-from.json").read_text())
    assert seeded == {"backup": str(made.root), "world": "helloworld"}
    assert "Worlds = helloworld" in (host.config_dir / "thorkell.host.cfg").read_text()
    assert "Language = Korean" in (host.config_dir / "thorkell.host.cfg").read_text()

    # 리허설에서 놀던 진행은 다음 실행에도 남는다: 이미 있는 런타임은 다시 복사하지 않는다.
    (host.saves / "worlds_local/helloworld/_main.51.fwl2").write_bytes(b"played")
    again, created = play.prepare_rehearsal_host(root, game, pack, [plugins], made, "helloworld", "ko")
    assert not created
    assert (again.saves / "worlds_local/helloworld/_main.51.fwl2").read_bytes() == b"played"


def test_host_status_drives_guidance_and_stops_on_dead_ends(tmp_path: Path) -> None:
    host = runtime.Runtime(root=tmp_path, role="host-rehearsal")
    assert play.read_status(host) is None
    assert "helloworld" in play.waiting_hint(None, "helloworld")

    (tmp_path / play.HOST_STATUS).write_text(json.dumps({"listener": "world_not_allowed", "world": "other"}))
    hint = play.waiting_hint(play.read_status(host), "helloworld")
    assert "other" in hint and "helloworld" in hint

    (tmp_path / play.HOST_STATUS).write_text(json.dumps({"listener": "open_playfab", "leader": None}))
    assert play.ready(play.read_status(host)) is False
    (tmp_path / play.HOST_STATUS).write_text(json.dumps({"listener": "open_playfab", "leader": "Viking"}))
    assert play.ready(play.read_status(host)) is True

    for dead_end in (
        "untested_build",
        "not_a_thorkell_runtime",
        "crossplay_shim_unavailable",
        "listen_failed",
    ):
        (tmp_path / play.HOST_STATUS).write_text(json.dumps({"listener": dead_end}))
        with pytest.raises(play.PlayError):
            play.waiting_hint(play.read_status(host), "helloworld")


async def test_json_ui_quit_while_asking_the_password_stops_instead_of_waiting() -> None:
    ui = play.JsonUi(out=io.StringIO(), inp=io.StringIO(json.dumps({"type": "quit"}) + "\n"))
    ui.attach(asyncio.get_running_loop())
    with pytest.raises(play.PlayError, match="비밀번호"):
        await asyncio.wait_for(ui.ask_password(None), 2)


def test_leader_chat_tail_reads_only_new_complete_lines(tmp_path: Path) -> None:
    path = tmp_path / play.LEADER_CHAT
    path.write_text(json.dumps({"from": "Viking", "text": "어제 한 말"}) + "\n")
    tail = play.LeaderChatTail(path)
    assert tail.read() == []
    with path.open("a") as handle:
        handle.write(json.dumps({"from": "Viking", "text": "뭐해?"}) + "\n")
        handle.write('{"from": "Viking", "te')
    assert [m["text"] for m in tail.read()] == ["뭐해?"]
    with path.open("a") as handle:
        handle.write('xt": "따라와"}\n')
    assert [m["text"] for m in tail.read()] == ["따라와"]
    assert tail.read() == []


def test_leader_chat_tail_waits_for_the_file(tmp_path: Path) -> None:
    path = tmp_path / play.LEADER_CHAT
    tail = play.LeaderChatTail(path)
    assert tail.read() == []
    path.write_text(json.dumps({"from": "Viking", "text": "안녕"}) + "\n")
    assert [m["text"] for m in tail.read()] == ["안녕"]


def test_where_thorkell_is_comes_from_the_hosts_view_of_both_players() -> None:
    # 사람에게 보여 주는 정보다(두뇌에는 넘기지 않는다). 호스트는 토르켈이 지도에 위치를 공개하지 않아도 안다.
    status = {"leader_pos": [0.0, 30.0, 0.0], "thorkell": {"name": "Thorkell", "pos": [250.0, 31.0, 160.0]}}
    assert play.thorkell_where(status) == "토르켈은 내 북동쪽 300m에 있어요"
    assert play.thorkell_where({**status, "thorkell": None}) is None
    assert play.thorkell_where({**status, "leader_pos": None}) is None
    assert play.thorkell_where(None) is None


def test_console_keeps_location_updates_out_of_the_conversation(capsys: pytest.CaptureFixture[str]) -> None:
    ui = play.ConsoleUi()
    ui.emit("where", "토르켈은 내 북동쪽 300m에 있어요")
    ui.emit("thorkell", "응, 따라갈게.")
    assert capsys.readouterr().out == "  토르켈: 응, 따라갈게.\n"


def test_the_brains_decisions_are_kept_in_a_file_while_playing(tmp_path: Path) -> None:
    # 리허설(2026-10-18)에서 토르켈이 갑자기 대답을 멈췄는데, 두뇌의 결정·경고가 앱 화면에만 있어서
    # 무엇에 막혔는지 밖에서 볼 수 없었다.
    import logging

    path = play.log_to_file(tmp_path)
    logging.getLogger("thorkell.control.controller").info("decision adopt g1: 부탁 처리하기 시작")
    logging.getLogger("thorkell.plan.planner").warning("plan attempt 1 rejected")
    for handler in logging.getLogger("thorkell").handlers:
        handler.flush()
    text = path.read_text()
    assert "부탁 처리하기 시작" in text and "plan attempt 1 rejected" in text


def test_a_new_world_starts_from_nothing_but_the_characters(tmp_path: Path) -> None:
    # 목표는 처음부터 같이 첫 보스까지다. 리허설 복사본(helloworld)은 후반 월드라 첫 보스를 이미 잡았다.
    saves, cloud = _sources(tmp_path)
    made = backup.create(
        tmp_path / "backups",
        saves=saves,
        cloud_roots=[cloud],
        prefs=lambda dest: dest.write_bytes(b"<plist/>"),
        now=datetime(2026, 10, 18, 17, 0),
    )
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    host, created = play.prepare_fresh_host(
        tmp_path / "runtimes/fresh-thorkell", game, pack, [plugins], made, "thorkell", "en"
    )
    assert created and host.role == "host-rehearsal"
    assert not (host.saves / "worlds_local").exists() or not any((host.saves / "worlds_local").iterdir())
    assert (host.saves / "characters_local/viking.fch").is_file()
    assert "Worlds = thorkell" in (host.config_dir / "thorkell.host.cfg").read_text()
    # 영어로 플레이하면 사람의 게임도 영어로 뜬다(같은 이름을 본다).
    assert "Language = English" in (host.config_dir / "thorkell.host.cfg").read_text()
    hint = play.waiting_hint(None, "thorkell", new=True)
    assert "새 월드" in hint and "thorkell" in hint
