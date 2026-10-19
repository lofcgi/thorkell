"""Isolated game runtimes: APFS clones of Valheim.app + pinned BepInEx + Thorkell plugins.

The real Steam install is only ever read (cloned). Everything Thorkell launches lives in a
runtime directory that carries a marker file; nothing without that marker is ever deleted.

Bot and test runtimes (ISOLATED_ROLES) must not change the human's game state. The clones keep the real
bundle id, so they share the human's prefs domain, and Unity writes some keys there natively (session
counters at start, Screenmanager on quit) where Harmony cannot reach. Two OS-level layers cover what the
in-game patches cannot (checked on macOS 26.2, 2026-10-02):
- a sandbox-exec deny profile for the human's prefs, saves, log and the real install. cfprefsd refuses a
  prefs write only when the client lacks both user-preference-write and file-write-data on the plist, so
  the profile denies both.
- CFFIXED_USER_HOME=<runtime>/home, so Foundation's per-app folders (HTTPStorages, Application
  Support/<bundle id>) land in the runtime. cfprefsd ignores it; it does not isolate prefs by itself.
The human's own host clone runs with neither: that game is supposed to use the human's settings.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from thorkell.ops.backup import WorldSource
from thorkell.ops.guard import HUMAN_LOG, HUMAN_PREFS_PLIST, HUMAN_SAVES, PREFS_DOMAIN
from thorkell.paths import REPO_ROOT, THORKELL_HOME, game_managed

MARKER = "thorkell-runtime.json"
RUNTIMES_DIR = THORKELL_HOME / "runtimes"
# host-rehearsal: 사람이 직접 플레이하지만 세이브는 백업에서 복사한 것만 쓰는 리허설 호스트.
ISOLATED_ROLES = frozenset({"body", "host-test", "host-rehearsal"})
GAME_ASSEMBLIES = ("assembly_valheim.dll", "assembly_utils.dll")

PLUGIN_BUILDS = {
    "body": REPO_ROOT / "plugin/Thorkell.Body/bin/Release/netstandard2.1",
    "host": REPO_ROOT / "plugin/Thorkell.Host/bin/Release/netstandard2.1",
}


@dataclass(frozen=True)
class Runtime:
    root: Path
    role: str

    @property
    def saves(self) -> Path:
        return self.root / "saves"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def config_dir(self) -> Path:
        return self.root / "BepInEx/config"

    @property
    def bepinex_log(self) -> Path:
        return self.root / "BepInEx/LogOutput.log"

    @property
    def executable(self) -> Path:
        return self.root / "Valheim.app/Contents/MacOS/Valheim"

    @property
    def home(self) -> Path:
        return self.root / "home"

    @property
    def isolated(self) -> bool:
        return self.role in ISOLATED_ROLES


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_existing(root: Path) -> Runtime:
    marker = root / MARKER
    if not marker.is_file():
        raise FileNotFoundError(f"{root} is not a Thorkell runtime (no {MARKER})")
    return Runtime(root=root, role=json.loads(marker.read_text())["role"])


def _plugin_dlls(plugin_dirs: Sequence[Path]) -> list[Path]:
    dlls = [dll for directory in plugin_dirs for dll in sorted(directory.glob("*.dll"))]
    if not dlls:
        raise FileNotFoundError(f"no plugin DLLs in {[str(d) for d in plugin_dirs]}; build Release first")
    return dlls


def create(root: Path, role: str, game: Path, bepinex: Path, plugin_dirs: Sequence[Path]) -> Runtime:
    if root.exists():
        raise FileExistsError(f"runtime already exists: {root}")
    dlls = _plugin_dlls(plugin_dirs)

    root.mkdir(parents=True, mode=0o700)
    subprocess.run(["cp", "-cR", str(game / "Valheim.app"), str(root / "Valheim.app")], check=True)
    shutil.copytree(bepinex / "BepInEx/core", root / "BepInEx/core")
    (root / "BepInEx/config").mkdir(parents=True)
    shutil.copy2(bepinex / "BepInEx/config/BepInEx.cfg", root / "BepInEx/config/BepInEx.cfg")
    shutil.copytree(bepinex / "doorstop_libs", root / "doorstop_libs")
    shutil.copy2(game / "steam_appid.txt", root / "steam_appid.txt")
    plugins = root / "BepInEx/plugins/Thorkell"
    plugins.mkdir(parents=True)
    for dll in dlls:
        shutil.copy2(dll, plugins / dll.name)
    for name in ("saves", "logs"):
        (root / name).mkdir(mode=0o700)
    if role in ISOLATED_ROLES:
        (root / "home").mkdir(mode=0o700)

    managed = game_managed(root)
    manifest = {
        "role": role,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "game_sha256": {name: _sha256(managed / name) for name in GAME_ASSEMBLIES},
        "plugins": {dll.name: _sha256(dll) for dll in sorted(plugins.glob("*.dll"))},
    }
    (root / MARKER).write_text(json.dumps(manifest, indent=2) + "\n")
    return Runtime(root=root, role=role)


def ensure(root: Path, role: str, game: Path, bepinex: Path, plugin_dirs: Sequence[Path]) -> Runtime:
    """A long-lived runtime (the bot's character and the rehearsal world live in it): create it the first
    time, afterwards only refresh the Thorkell plugin DLLs. A runtime cloned from another game build is
    refused rather than patched, because the version gate would not arm it anyway."""
    if not root.exists():
        return create(root, role, game, bepinex, plugin_dirs)
    existing = open_existing(root)
    if existing.role != role:
        raise ValueError(f"{root} is a {existing.role} runtime, not {role}")
    manifest = json.loads((root / MARKER).read_text())
    current = {name: _sha256(game_managed(game) / name) for name in GAME_ASSEMBLIES}
    if manifest["game_sha256"] != current:
        raise RuntimeError(
            f"the game changed since {root} was cloned; run `thorkell upgrade-runtimes` to re-clone it"
        )
    plugins = root / "BepInEx/plugins/Thorkell"
    for dll in _plugin_dlls(plugin_dirs):
        shutil.copy2(dll, plugins / dll.name)
    manifest["plugins"] = {dll.name: _sha256(dll) for dll in sorted(plugins.glob("*.dll"))}
    (root / MARKER).write_text(json.dumps(manifest, indent=2) + "\n")
    return existing


def upgrade(
    root: Path, role: str, game: Path, bepinex: Path, plugin_dirs: Sequence[Path]
) -> tuple[Runtime, Path]:
    """Re-clone a long-lived runtime after a game update, carrying its saves (the bot's character, the
    rehearsal world) over. The old runtime stays beside it as <name>-<old assembly sha> so a build that
    fails its scenarios can be rolled back by renaming."""
    existing = open_existing(root)
    if existing.role != role:
        raise ValueError(f"{root} is a {existing.role} runtime, not {role}")
    old = json.loads((root / MARKER).read_text())["game_sha256"]
    current = {name: _sha256(game_managed(game) / name) for name in GAME_ASSEMBLIES}
    if old == current:
        raise ValueError(f"{root} is already cloned from this game build")
    kept = root.with_name(f"{root.name}-{old['assembly_valheim.dll'][:12]}")
    if kept.exists():
        raise FileExistsError(f"{kept} already exists; move it away first")
    root.rename(kept)
    fresh = create(root, role, game, bepinex, plugin_dirs)
    for entry in (kept / "saves").iterdir():
        subprocess.run(["cp", "-cR", str(entry), str(fresh.saves / entry.name)], check=True)
    return fresh, kept


def seed_saves(runtime: Runtime, world: WorldSource, characters: Sequence[Path]) -> None:
    """Copy a backed-up world and characters into an isolated runtime's own save folder."""
    if not runtime.isolated:
        raise ValueError(
            f"{runtime.role} runtime uses the human's real saves; only isolated runtimes are seeded"
        )
    worlds = runtime.saves / "worlds_local"
    worlds.mkdir(parents=True, exist_ok=True)
    if world.chunked_dir is not None:
        subprocess.run(["cp", "-cR", str(world.chunked_dir), str(worlds / world.name)], check=True)
    for path in world.legacy_files:
        shutil.copy2(path, worlds / path.name)
    folder = runtime.saves / "characters_local"
    folder.mkdir(parents=True, exist_ok=True)
    for character in characters:
        shutil.copy2(character, folder / character.name)


def remove(root: Path, base: Path) -> None:
    """Delete a runtime, but only one that carries our marker and lives under `base`."""
    resolved = root.resolve()
    if not resolved.is_relative_to(base.resolve()) or resolved == base.resolve():
        raise PermissionError(f"refusing to delete {root}: outside {base}")
    if not (resolved / MARKER).is_file():
        raise PermissionError(f"refusing to delete {root}: no {MARKER}")
    shutil.rmtree(resolved)


def write_config(runtime: Runtime, guid: str, sections: dict[str, dict[str, str | int | bool]]) -> Path:
    """Write a BepInEx cfg (mode 0600). Values may be secrets; never log them."""
    lines: list[str] = []
    for section, values in sections.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            text = str(value).lower() if isinstance(value, bool) else str(value)
            lines.append(f"{key} = {text}")
        lines.append("")
    path = runtime.config_dir / f"{guid}.cfg"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("\n".join(lines))
    os.chmod(path, 0o600)
    return path


def _sbpl_string(path: Path) -> str:
    # 샌드박스는 실제 경로(심볼릭 링크를 푼 경로)로 비교한다.
    text = str(path.resolve())
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sandbox_profile(game: Path) -> str:
    """Deny-list for isolated roles; everything else (Steam IPC, Metal, network, the runtime) is allowed."""
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            f'(deny user-preference-write (preference-domain "{PREFS_DOMAIN}"))',
            "(deny file-write*",
            f"    (literal {_sbpl_string(HUMAN_PREFS_PLIST)})",
            f"    (subpath {_sbpl_string(HUMAN_SAVES)})",
            f"    (subpath {_sbpl_string(HUMAN_LOG.parent)})",
            f"    (subpath {_sbpl_string(game)}))",
        ]
    )


def launch_command(runtime: Runtime, game_args: Sequence[str], game: Path) -> list[str]:
    """`game`: the real install this runtime was cloned from (isolated roles may not write to it)."""
    sandbox = ["sandbox-exec", "-p", sandbox_profile(game)] if runtime.isolated else []
    home = [f"CFFIXED_USER_HOME={runtime.home}"] if runtime.isolated else []
    # macOS strips DYLD_* when exec'ing /usr/bin/arch, so the variables go after it through env.
    return [
        *sandbox,
        "arch",
        "-x86_64",
        "env",
        *home,
        "DOORSTOP_ENABLED=1",
        f"DOORSTOP_TARGET_ASSEMBLY={runtime.root / 'BepInEx/core/BepInEx.Preloader.dll'}",
        f"DYLD_LIBRARY_PATH={runtime.root}",
        f"DYLD_INSERT_LIBRARIES={runtime.root / 'doorstop_libs/libdoorstop_x64.dylib'}",
        str(runtime.executable),
        *game_args,
    ]
