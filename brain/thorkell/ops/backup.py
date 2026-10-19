"""`thorkell backup`: copy the human's Valheim saves and prefs, with checksums. Sources are only read.

A backup is THORKELL_HOME/backups/<timestamp>/ (mode 0700):
  steam/<account>/remote/...   Steam's copy of Valheim's cloud saves (characters, worlds, serverlist)
  local/...                    ~/Library/Application Support/IronGate/Valheim
  prefs/<domain>.plist         `defaults export` of the shared prefs domain
  manifest.json                {"created", "sources", "files": {relative path: [size, sha256]}}
Files are APFS clones (`cp -c`), so a backup costs almost no disk until the originals change. Every copy
is hashed against its original; a file that changed during the copy fails the backup.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from thorkell.ops import guard
from thorkell.paths import THORKELL_HOME

BACKUPS_DIR = THORKELL_HOME / "backups"
MANIFEST = "manifest.json"


class BackupError(Exception):
    pass


@dataclass(frozen=True)
class WorldSource:
    name: str
    chunked_dir: Path | None  # 1.0 형식: <worlds>/<name>/_main.<n>.fwl2 + .chunk 파일들
    legacy_files: tuple[Path, ...]  # 구형: <name>.fwl, <name>.db


@dataclass(frozen=True)
class Backup:
    root: Path
    manifest: dict[str, Any]

    def _world_dirs(self) -> list[Path]:
        return [*sorted((self.root / "steam").glob("*/remote/worlds")), self.root / "local/worlds_local"]

    def world(self, name: str) -> WorldSource:
        found = []
        for worlds in self._world_dirs():
            chunked = worlds / name
            if any(chunked.glob("_main.*.fwl2")):
                found.append(WorldSource(name, chunked, ()))
            fwl = worlds / f"{name}.fwl"
            if fwl.is_file():
                found.append(
                    WorldSource(name, None, tuple(p for p in (fwl, worlds / f"{name}.db") if p.is_file()))
                )
        if not found:
            raise BackupError(f"world {name!r} is not in backup {self.root}")
        if len(found) > 1:
            places = ", ".join(str(w.chunked_dir or w.legacy_files[0]) for w in found)
            raise BackupError(f"world {name!r} is in several places in the backup: {places}")
        return found[0]

    def characters(self) -> list[Path]:
        """Current character files (not the game's own .old copies or *_backup* snapshots). If the same
        character is both in the cloud and local, the newer file wins."""
        newest: dict[str, Path] = {}
        folders = [
            *sorted((self.root / "steam").glob("*/remote/characters")),
            self.root / "local/characters_local",
        ]
        for folder in folders:
            for path in sorted(folder.glob("*.fch")):
                if "_backup" in path.stem:
                    continue
                current = newest.get(path.name)
                if current is None or path.stat().st_mtime > current.stat().st_mtime:
                    newest[path.name] = path
        return [newest[name] for name in sorted(newest)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _clone(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", "-cR", str(source), str(target)], check=True)


def _export_prefs(dest: Path) -> None:
    subprocess.run(["defaults", "export", guard.PREFS_DOMAIN, str(dest)], check=True)


def create(
    dest_root: Path = BACKUPS_DIR,
    *,
    saves: Path = guard.HUMAN_SAVES,
    cloud_roots: Sequence[Path] | None = None,
    prefs: Callable[[Path], None] = _export_prefs,
    now: datetime | None = None,
) -> Backup:
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    root = dest_root / stamp
    if root.exists():
        raise BackupError(f"backup already exists: {root}")
    dest_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    partial = dest_root / f"{stamp}.partial"
    partial.mkdir(mode=0o700)

    sources: dict[str, str] = {}
    for cloud in guard.steam_cloud_roots() if cloud_roots is None else cloud_roots:
        prefix = f"steam/{cloud.parent.parent.name}/remote"
        _clone(cloud, partial / prefix)
        sources[prefix] = str(cloud)
    if saves.is_dir():
        _clone(saves, partial / "local")
        sources["local"] = str(saves)
    (partial / "prefs").mkdir()
    prefs(partial / "prefs" / f"{guard.PREFS_DOMAIN}.plist")

    files: dict[str, list[Any]] = {}
    for path in sorted(partial.rglob("*")):
        if path.is_file() and not path.is_symlink():
            files[str(path.relative_to(partial))] = [path.stat().st_size, _sha256(path)]
    for prefix, source in sources.items():
        for name, (_, digest) in files.items():
            if name.startswith(prefix + "/"):
                original = Path(source) / name[len(prefix) + 1 :]
                if _sha256(original) != digest:
                    raise BackupError(
                        f"{original} changed while it was being copied; close Valheim and retry"
                    )

    manifest = {
        "created": (now or datetime.now()).isoformat(timespec="seconds"),
        "sources": sources,
        "files": files,
    }
    (partial / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    partial.rename(root)
    return Backup(root, manifest)


def verify(made: Backup) -> list[str]:
    """Relative paths whose copy is missing or no longer matches the manifest."""
    broken = []
    for name, (_, digest) in made.manifest["files"].items():
        path = made.root / name
        if not path.is_file() or _sha256(path) != digest:
            broken.append(name)
    return sorted(broken)


def latest(dest_root: Path = BACKUPS_DIR) -> Backup | None:
    if not dest_root.is_dir():
        return None
    finished = sorted(p for p in dest_root.iterdir() if (p / MANIFEST).is_file())
    if not finished:
        return None
    root = finished[-1]
    return Backup(root, json.loads((root / MANIFEST).read_text()))
