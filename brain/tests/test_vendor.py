from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from thorkell.ops import vendor


def _pinned(tmp_path: Path, payload: bytes, sha: str | None = None) -> vendor.Pinned:
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("BepInEx/core/BepInEx.dll", payload)
    digest = sha or hashlib.sha256(archive.read_bytes()).hexdigest()
    return vendor.Pinned("pack", "1", "file:///unused", digest, archive, tmp_path / "pack")


def test_ensure_extracts_verified_archive(tmp_path: Path) -> None:
    pinned = _pinned(tmp_path, b"dll")
    out = vendor.ensure(pinned)
    assert (out / "BepInEx/core/BepInEx.dll").read_bytes() == b"dll"


def test_hash_mismatch_is_an_error(tmp_path: Path) -> None:
    pinned = _pinned(tmp_path, b"dll", sha="0" * 64)
    with pytest.raises(RuntimeError, match="sha256"):
        vendor.ensure(pinned)
    assert not pinned.dir.exists()


def test_repo_manifest_pins_bepinexpack() -> None:
    pinned = vendor.load()
    assert pinned.version == "5.4.2351"
    assert len(pinned.sha256) == 64
