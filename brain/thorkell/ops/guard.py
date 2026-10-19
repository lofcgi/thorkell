"""Evidence that native runs never touched the human's game state.

- prefs: the bot/test clones share the human's prefs domain (same bundle id). Harmony blocks managed
  writes and the launch sandbox (ops/runtime.py) denies the rest. We snapshot before and diff after: any
  change is a violation. A violation is also undone (changed keys written back, added keys deleted) so a
  failed run never leaves the human's settings altered, but the run still fails.
- saves: fingerprint of the human's local save tree, the Steam Cloud copies of Valheim's saves (the human's
  characters and worlds live there) and the log; every file must keep its size and mtime.
"""

from __future__ import annotations

import plistlib
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PREFS_DOMAIN = "com.coffeestain.valheim-steam"
HUMAN_PREFS_PLIST = Path.home() / "Library/Preferences" / f"{PREFS_DOMAIN}.plist"
HUMAN_SAVES = Path.home() / "Library/Application Support/IronGate/Valheim"
HUMAN_LOG = Path.home() / "Library/Logs/IronGate/Valheim/Player.log"
STEAM_USERDATA = Path.home() / "Library/Application Support/Steam/userdata"
VALHEIM_APPID = "892970"


def steam_cloud_roots(userdata: Path = STEAM_USERDATA) -> list[Path]:
    """Steam's local copies of Valheim's cloud saves, one per Steam account on this Mac."""
    return sorted(path for path in userdata.glob(f"*/{VALHEIM_APPID}/remote") if path.is_dir())


def snapshot_prefs(domain: str = PREFS_DOMAIN) -> dict[str, Any]:
    exported = subprocess.run(["defaults", "export", domain, "-"], capture_output=True, check=True).stdout
    data: dict[str, Any] = plistlib.loads(exported)
    return data


@dataclass(frozen=True)
class PrefsDiff:
    changed: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def keys(self) -> tuple[str, ...]:
        return self.changed + self.added + self.removed


def diff_prefs(before: dict[str, Any], after: dict[str, Any]) -> PrefsDiff:
    return PrefsDiff(
        changed=tuple(sorted(k for k in before.keys() & after.keys() if before[k] != after[k])),
        added=tuple(sorted(after.keys() - before.keys())),
        removed=tuple(sorted(before.keys() - after.keys())),
    )


def _write_args(value: Any) -> list[str]:
    if isinstance(value, bool):
        return ["-bool", "true" if value else "false"]
    if isinstance(value, int):
        return ["-int", str(value)]
    if isinstance(value, float):
        return ["-float", repr(value)]
    if isinstance(value, str):
        return ["-string", value]
    if isinstance(value, bytes):
        return ["-data", value.hex()]
    raise TypeError(f"cannot restore prefs value of type {type(value).__name__}")


def restore_commands(before: dict[str, Any], diff: PrefsDiff, domain: str = PREFS_DOMAIN) -> list[list[str]]:
    commands: list[list[str]] = []
    for key in diff.changed + diff.removed:
        commands.append(["defaults", "write", domain, key, *_write_args(before[key])])
    for key in diff.added:
        commands.append(["defaults", "delete", domain, key])
    return commands


def restore_prefs(before: dict[str, Any], diff: PrefsDiff) -> list[str]:
    restored = []
    for command in restore_commands(before, diff):
        subprocess.run(command, check=True)
        restored.append(command[3])
    return restored


def fingerprint(
    roots: Sequence[Path] | None = None, extra: Sequence[Path] = (HUMAN_LOG,)
) -> dict[str, tuple[int, int]]:
    """path -> (size, mtime_ns) for every file under the roots and the extra files.
    Default roots: the local saves and every Steam Cloud copy of Valheim's saves."""
    result: dict[str, tuple[int, int]] = {}
    for root in [HUMAN_SAVES, *steam_cloud_roots()] if roots is None else roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                stat = path.stat()
                result[str(path)] = (stat.st_size, stat.st_mtime_ns)
    for path in extra:
        if path.is_file():
            stat = path.stat()
            result[str(path)] = (stat.st_size, stat.st_mtime_ns)
    return result


def fingerprint_changes(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> list[str]:
    keys = before.keys() | after.keys()
    return sorted(k for k in keys if before.get(k) != after.get(k))
