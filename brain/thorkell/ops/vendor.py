"""Pinned third-party downloads (vendor.json at the repo root)."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from thorkell.paths import REPO_ROOT


@dataclass(frozen=True)
class Pinned:
    name: str
    version: str
    url: str
    sha256: str
    zip: Path
    dir: Path


def load(name: str = "bepinexpack") -> Pinned:
    entry = json.loads((REPO_ROOT / "vendor.json").read_text())[name]
    return Pinned(
        name=name,
        version=entry["version"],
        url=entry["url"],
        sha256=entry["sha256"],
        zip=REPO_ROOT / entry["zip"],
        dir=REPO_ROOT / entry["dir"],
    )


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(pinned: Pinned) -> None:
    actual = sha256_of(pinned.zip)
    if actual != pinned.sha256:
        raise RuntimeError(f"{pinned.zip.name} sha256 {actual} != pinned {pinned.sha256}")


def ensure(pinned: Pinned) -> Path:
    if not pinned.zip.is_file():
        pinned.zip.parent.mkdir(parents=True, exist_ok=True)
        partial = pinned.zip.with_suffix(".part")
        urllib.request.urlretrieve(pinned.url, partial)
        partial.rename(pinned.zip)
    verify(pinned)
    if not pinned.dir.is_dir():
        with zipfile.ZipFile(pinned.zip) as archive:
            archive.extractall(pinned.dir)
    return pinned.dir
