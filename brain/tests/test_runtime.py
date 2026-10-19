from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from thorkell.ops import backup, guard, runtime


def _fake_game(tmp_path: Path) -> Path:
    game = tmp_path / "game"
    managed = game / "Valheim.app/Contents/Resources/Data/Managed"
    managed.mkdir(parents=True)
    (managed / "assembly_valheim.dll").write_bytes(b"valheim")
    (managed / "assembly_utils.dll").write_bytes(b"utils")
    (game / "Valheim.app/Contents/MacOS").mkdir(parents=True)
    (game / "Valheim.app/Contents/MacOS/Valheim").write_bytes(b"exe")
    (game / "steam_appid.txt").write_text("892970")
    return game


def _fake_bepinex(tmp_path: Path) -> Path:
    pack = tmp_path / "pack"
    (pack / "BepInEx/core").mkdir(parents=True)
    (pack / "BepInEx/core/BepInEx.Preloader.dll").write_bytes(b"preloader")
    (pack / "BepInEx/config").mkdir(parents=True)
    (pack / "BepInEx/config/BepInEx.cfg").write_text("[Logging]\n")
    (pack / "doorstop_libs").mkdir()
    (pack / "doorstop_libs/libdoorstop_x64.dylib").write_bytes(b"dylib")
    return pack


def _plugins(tmp_path: Path) -> Path:
    out = tmp_path / "bin"
    out.mkdir()
    for name in ("Thorkell.Body.dll", "Thorkell.Wire.dll", "Thorkell.Core.dll"):
        (out / name).write_bytes(name.encode())
    (out / "Thorkell.Body.pdb").write_bytes(b"pdb")
    return out


def test_create_clones_game_and_installs_plugins(tmp_path: Path) -> None:
    rt = runtime.create(
        tmp_path / "rt/body", "body", _fake_game(tmp_path), _fake_bepinex(tmp_path), [_plugins(tmp_path)]
    )
    assert rt.executable.read_bytes() == b"exe"
    assert sorted(p.name for p in (rt.root / "BepInEx/plugins/Thorkell").iterdir()) == [
        "Thorkell.Body.dll",
        "Thorkell.Core.dll",
        "Thorkell.Wire.dll",
    ]
    manifest = json.loads((rt.root / runtime.MARKER).read_text())
    assert manifest["role"] == "body"
    assert set(manifest["game_sha256"]) == {"assembly_valheim.dll", "assembly_utils.dll"}
    assert stat.S_IMODE(rt.saves.stat().st_mode) == 0o700
    assert runtime.open_existing(rt.root).role == "body"


def test_create_refuses_existing_root_and_missing_builds(tmp_path: Path) -> None:
    game, pack = _fake_game(tmp_path), _fake_bepinex(tmp_path)
    (tmp_path / "taken").mkdir()
    with pytest.raises(FileExistsError):
        runtime.create(tmp_path / "taken", "body", game, pack, [_plugins(tmp_path)])
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="build Release"):
        runtime.create(tmp_path / "rt2", "body", game, pack, [tmp_path / "empty"])


def test_remove_requires_marker_and_base(tmp_path: Path) -> None:
    base = tmp_path / "runtimes"
    rt = runtime.create(
        base / "body", "body", _fake_game(tmp_path), _fake_bepinex(tmp_path), [_plugins(tmp_path)]
    )
    stranger = base / "not-ours"
    stranger.mkdir()
    with pytest.raises(PermissionError, match=r"no thorkell-runtime\.json"):
        runtime.remove(stranger, base)
    with pytest.raises(PermissionError, match="outside"):
        runtime.remove(rt.root, tmp_path / "elsewhere")
    with pytest.raises(PermissionError, match="outside"):
        runtime.remove(base, base)
    runtime.remove(rt.root, base)
    assert not rt.root.exists()
    assert stranger.exists()


def test_config_is_private_and_bepinex_formatted(tmp_path: Path) -> None:
    rt = runtime.create(
        tmp_path / "rt", "body", _fake_game(tmp_path), _fake_bepinex(tmp_path), [_plugins(tmp_path)]
    )
    path = runtime.write_config(
        rt, "thorkell.body", {"Bridge": {"Port": 47821, "Token": "ab" * 32, "Strict": True}}
    )
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.read_text() == f"[Bridge]\nPort = 47821\nToken = {'ab' * 32}\nStrict = true\n"


def test_launch_command_sets_dyld_after_arch(tmp_path: Path) -> None:
    rt = runtime.Runtime(root=tmp_path, role="host")
    command = runtime.launch_command(rt, ["-batchmode", "-thorkell-host"], tmp_path / "game")
    assert command[:3] == ["arch", "-x86_64", "env"]
    env = command[3 : command.index(str(rt.executable))]
    assert any(part.startswith("DYLD_INSERT_LIBRARIES=") for part in env)
    assert not any(part.startswith("CFFIXED_USER_HOME=") for part in env)
    assert command[-2:] == ["-batchmode", "-thorkell-host"]


def test_isolated_roles_get_a_private_home(tmp_path: Path) -> None:
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    body = runtime.create(tmp_path / "body", "body", game, pack, [plugins])
    assert stat.S_IMODE(body.home.stat().st_mode) == 0o700
    host = runtime.create(tmp_path / "host", "host", game, pack, [plugins])
    assert not host.home.exists()


def test_isolated_roles_launch_inside_the_deny_sandbox(tmp_path: Path) -> None:
    game = tmp_path / "game"
    for role in ("body", "host-test"):
        rt = runtime.Runtime(root=tmp_path / role, role=role)
        command = runtime.launch_command(rt, ["-batchmode"], game)
        assert command[:2] == ["sandbox-exec", "-p"]
        profile = command[2]
        assert f'(preference-domain "{guard.PREFS_DOMAIN}")' in profile
        assert f'(literal "{guard.HUMAN_PREFS_PLIST.resolve()}")' in profile
        assert f'(subpath "{guard.HUMAN_SAVES.resolve()}")' in profile
        assert f'(subpath "{game.resolve()}")' in profile
        assert command[3:6] == ["arch", "-x86_64", "env"]
        assert f"CFFIXED_USER_HOME={rt.home}" in command[6 : command.index(str(rt.executable))]


def test_sandbox_profile_quotes_paths() -> None:
    profile = runtime.sandbox_profile(Path('/tmp/odd "game" \\ dir'))
    assert '(subpath "/tmp/odd \\"game\\" \\\\ dir"))' in profile.replace("/private/tmp", "/tmp")


@pytest.mark.skipif(sys.platform != "darwin", reason="sandbox-exec is macOS only")
def test_sandbox_profile_really_denies_writes_into_the_game(tmp_path: Path) -> None:
    game = tmp_path / "game"
    game.mkdir()
    touch = ["sandbox-exec", "-p", runtime.sandbox_profile(game), "/usr/bin/touch"]
    denied = subprocess.run([*touch, str(game / "x")], check=False)
    allowed = subprocess.run([*touch, str(tmp_path / "y")], check=False)
    assert denied.returncode != 0 and not (game / "x").exists()
    assert allowed.returncode == 0 and (tmp_path / "y").exists()


def test_ensure_creates_once_then_only_refreshes_plugins(tmp_path: Path) -> None:
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    first = runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins])
    (first.saves / "characters_local").mkdir()
    (first.saves / "characters_local/thorkell.fch").write_bytes(b"progress")
    (plugins / "Thorkell.Body.dll").write_bytes(b"new build")

    again = runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins])
    assert (again.root / "BepInEx/plugins/Thorkell/Thorkell.Body.dll").read_bytes() == b"new build"
    assert (again.saves / "characters_local/thorkell.fch").read_bytes() == b"progress"
    with pytest.raises(ValueError, match="body runtime, not host-rehearsal"):
        runtime.ensure(tmp_path / "rt/body", "host-rehearsal", game, pack, [plugins])


def test_ensure_refuses_a_runtime_cloned_from_another_game_build(tmp_path: Path) -> None:
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins])
    (game / "Valheim.app/Contents/Resources/Data/Managed/assembly_valheim.dll").write_bytes(b"patched game")
    with pytest.raises(RuntimeError, match="game changed"):
        runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins])


def test_upgrade_reclones_a_changed_game_and_keeps_saves_and_the_old_runtime(tmp_path: Path) -> None:
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    old = runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins])
    (old.saves / "characters_local").mkdir()
    (old.saves / "characters_local/thorkell.fch").write_bytes(b"progress")
    old_sha = json.loads((old.root / runtime.MARKER).read_text())["game_sha256"]["assembly_valheim.dll"]
    managed = game / "Valheim.app/Contents/Resources/Data/Managed"
    (managed / "assembly_valheim.dll").write_bytes(b"patched game")

    new, kept = runtime.upgrade(tmp_path / "rt/body", "body", game, pack, [plugins])

    assert kept == tmp_path / f"rt/body-{old_sha[:12]}"
    assert (kept / runtime.MARKER).is_file()
    assert (new.saves / "characters_local/thorkell.fch").read_bytes() == b"progress"
    assert (new.root / "Valheim.app/Contents/Resources/Data/Managed/assembly_valheim.dll").read_bytes() == (
        b"patched game"
    )
    assert runtime.ensure(tmp_path / "rt/body", "body", game, pack, [plugins]).root == new.root
    with pytest.raises(ValueError, match="already cloned from this game build"):
        runtime.upgrade(tmp_path / "rt/body", "body", game, pack, [plugins])


def test_seed_saves_copies_a_world_and_characters_into_an_isolated_runtime(tmp_path: Path) -> None:
    game, pack, plugins = _fake_game(tmp_path), _fake_bepinex(tmp_path), _plugins(tmp_path)
    world_dir = tmp_path / "backup/worlds/helloworld"
    world_dir.mkdir(parents=True)
    (world_dir / "_main.51.fwl2").write_bytes(b"meta")
    (world_dir / "00_01__0_18.chunk").write_bytes(b"chunk")
    character = tmp_path / "backup/characters/viking.fch"
    character.parent.mkdir(parents=True)
    character.write_bytes(b"viking")
    source = backup.WorldSource("helloworld", world_dir, ())

    rehearsal = runtime.create(tmp_path / "rt/rehearsal", "host-rehearsal", game, pack, [plugins])
    runtime.seed_saves(rehearsal, source, [character])
    assert (rehearsal.saves / "worlds_local/helloworld/_main.51.fwl2").read_bytes() == b"meta"
    assert (rehearsal.saves / "characters_local/viking.fch").read_bytes() == b"viking"

    human = runtime.create(tmp_path / "rt/host", "host", game, pack, [plugins])
    with pytest.raises(ValueError, match="real saves"):
        runtime.seed_saves(human, source, [character])
