from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path

import pytest

from thorkell.ops import backup


def _sources(tmp_path: Path) -> tuple[Path, Path]:
    saves = tmp_path / "IronGate/Valheim"
    (saves / "worlds_local/helloworld").mkdir(parents=True)
    (saves / "worlds_local/helloworld/cacheMinimapMeta").write_bytes(b"minimap only, not a world")
    (saves / "characters_local").mkdir()
    (saves / "characters_local/viking_backup_20260909.fch").write_bytes(b"old backup")
    (saves / "Player.log").symlink_to(tmp_path / "elsewhere.log")
    cloud = tmp_path / "userdata/111/892970/remote"
    (cloud / "worlds/helloworld").mkdir(parents=True)
    (cloud / "worlds/helloworld/_main.51.fwl2").write_bytes(b"meta")
    (cloud / "worlds/helloworld/_main.51.db2").write_bytes(b"db")
    (cloud / "worlds/helloworld/00_01__0_18.chunk").write_bytes(b"chunk")
    (cloud / "worlds/legacy.fwl").write_bytes(b"fwl")
    (cloud / "worlds/legacy.db").write_bytes(b"db")
    (cloud / "characters").mkdir()
    (cloud / "characters/viking.fch").write_bytes(b"viking")
    (cloud / "characters/viking.fch.old").write_bytes(b"previous")
    (cloud / "characters/viking_backup_auto-20260926.fch").write_bytes(b"auto backup")
    return saves, cloud


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(p): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }


def _create(tmp_path: Path, saves: Path, cloud: Path, when: datetime) -> backup.Backup:
    return backup.create(
        tmp_path / "backups",
        saves=saves,
        cloud_roots=[cloud],
        prefs=lambda dest: dest.write_bytes(b"<plist/>"),
        now=when,
    )


def test_backup_copies_saves_cloud_and_prefs_with_checksums(tmp_path: Path) -> None:
    saves, cloud = _sources(tmp_path)
    before = {**_snapshot(saves), **_snapshot(cloud)}
    made = _create(tmp_path, saves, cloud, datetime(2026, 10, 2, 12, 30))

    assert made.root == tmp_path / "backups/20261002-123000"
    assert stat.S_IMODE(made.root.stat().st_mode) == 0o700
    files = made.manifest["files"]
    assert "steam/111/remote/worlds/helloworld/_main.51.db2" in files
    assert "steam/111/remote/characters/viking.fch" in files
    assert "local/worlds_local/helloworld/cacheMinimapMeta" in files
    assert "prefs/com.coffeestain.valheim-steam.plist" in files
    assert not any(name.endswith("Player.log") for name in files)
    assert backup.verify(made) == []
    assert {**_snapshot(saves), **_snapshot(cloud)} == before


def test_verify_names_changed_and_missing_copies(tmp_path: Path) -> None:
    saves, cloud = _sources(tmp_path)
    made = _create(tmp_path, saves, cloud, datetime(2026, 10, 2, 12, 30))
    (made.root / "steam/111/remote/characters/viking.fch").write_bytes(b"tampered")
    (made.root / "steam/111/remote/worlds/legacy.db").unlink()
    assert backup.verify(made) == [
        "steam/111/remote/characters/viking.fch",
        "steam/111/remote/worlds/legacy.db",
    ]


def test_latest_skips_unfinished_backups(tmp_path: Path) -> None:
    saves, cloud = _sources(tmp_path)
    _create(tmp_path, saves, cloud, datetime(2026, 10, 1, 9, 0))
    newest = _create(tmp_path, saves, cloud, datetime(2026, 10, 2, 9, 0))
    (tmp_path / "backups/20261003-090000.partial").mkdir()
    found = backup.latest(tmp_path / "backups")
    assert found is not None and found.root == newest.root
    assert backup.latest(tmp_path / "nothing") is None


def test_backup_knows_where_a_world_and_the_characters_are(tmp_path: Path) -> None:
    saves, cloud = _sources(tmp_path)
    made = _create(tmp_path, saves, cloud, datetime(2026, 10, 2, 12, 30))

    chunked = made.world("helloworld")
    assert chunked.chunked_dir == made.root / "steam/111/remote/worlds/helloworld"
    legacy = made.world("legacy")
    assert legacy.chunked_dir is None
    assert [p.name for p in legacy.legacy_files] == ["legacy.fwl", "legacy.db"]
    with pytest.raises(backup.BackupError, match="nope"):
        made.world("nope")
    assert [p.name for p in made.characters()] == ["viking.fch"]
