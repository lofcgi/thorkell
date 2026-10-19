from __future__ import annotations

from pathlib import Path

import pytest

from thorkell.ops import guard


def test_diff_reports_every_changed_added_and_removed_key() -> None:
    before = {
        "language": "Korean",
        "Screenmanager Resolution Width": 2560,
        "Screenmanager Fullscreen mode": 1,
    }
    after = {
        "language": "English",
        "Screenmanager Resolution Width": 640,
        "Screenmanager Window Position X": 10,
    }
    diff = guard.diff_prefs(before, after)
    assert diff.changed == ("Screenmanager Resolution Width", "language")
    assert diff.added == ("Screenmanager Window Position X",)
    assert diff.removed == ("Screenmanager Fullscreen mode",)
    assert diff.keys == (
        "Screenmanager Resolution Width",
        "language",
        "Screenmanager Window Position X",
        "Screenmanager Fullscreen mode",
    )


def test_restore_commands_undo_every_change() -> None:
    before = {
        "language": "Korean",
        "Screenmanager Resolution Width": 2560,
        "Screenmanager Fullscreen mode": 1,
    }
    after = {
        "language": "English",
        "Screenmanager Resolution Width": 640,
        "Screenmanager Window Position X": 10,
    }
    commands = guard.restore_commands(before, guard.diff_prefs(before, after), domain="d")
    assert commands == [
        ["defaults", "write", "d", "Screenmanager Resolution Width", "-int", "2560"],
        ["defaults", "write", "d", "language", "-string", "Korean"],
        ["defaults", "write", "d", "Screenmanager Fullscreen mode", "-int", "1"],
        ["defaults", "delete", "d", "Screenmanager Window Position X"],
    ]


def test_restore_rejects_unknown_value_types() -> None:
    before = {"weird": [1, 2]}
    diff = guard.PrefsDiff(changed=("weird",), added=(), removed=())
    with pytest.raises(TypeError):
        guard.restore_commands(before, diff)


def test_fingerprint_detects_any_save_change(tmp_path: Path) -> None:
    saves = tmp_path / "saves"
    (saves / "worlds_local").mkdir(parents=True)
    world = saves / "worlds_local/helloworld.fwl"
    world.write_bytes(b"a")
    cloud = tmp_path / "userdata/123/892970/remote"
    (cloud / "worlds/helloworld").mkdir(parents=True)
    chunk = cloud / "worlds/helloworld/_main.1.db2"
    chunk.write_bytes(b"w")
    log = tmp_path / "Player.log"
    log.write_text("x")
    roots = (saves, cloud)
    before = guard.fingerprint(roots, (log,))
    assert guard.fingerprint_changes(before, guard.fingerprint(roots, (log,))) == []

    world.write_bytes(b"ab")
    chunk.write_bytes(b"ww")
    (saves / "characters_local").mkdir()
    (saves / "characters_local/new.fch").write_bytes(b"c")
    changes = guard.fingerprint_changes(before, guard.fingerprint(roots, (log,)))
    assert changes == sorted(str(p) for p in (saves / "characters_local/new.fch", world, chunk))


def test_steam_cloud_roots_are_the_valheim_remote_folders(tmp_path: Path) -> None:
    (tmp_path / "111/892970/remote").mkdir(parents=True)
    (tmp_path / "222/892970/remote").mkdir(parents=True)
    (tmp_path / "333/440/remote").mkdir(parents=True)
    expected = [tmp_path / "111/892970/remote", tmp_path / "222/892970/remote"]
    assert guard.steam_cloud_roots(tmp_path) == expected
