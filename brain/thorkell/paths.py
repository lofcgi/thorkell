from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not (REPO_ROOT / "Thorkell.sln").is_file():
    raise RuntimeError(f"thorkell package is not inside the repo checkout: {REPO_ROOT}")

DEFAULT_GAME_ROOT = Path.home() / "Library/Application Support/Steam/steamapps/common/Valheim"
THORKELL_HOME = Path.home() / "Library/Application Support/Thorkell"


def game_root() -> Path:
    return Path(os.environ.get("THORKELL_GAME_ROOT", str(DEFAULT_GAME_ROOT)))


def game_managed(root: Path) -> Path:
    return root / "Valheim.app/Contents/Resources/Data/Managed"
