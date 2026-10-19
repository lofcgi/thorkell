"""What Thorkell remembers about the world, the way a player does: which creature is which (once its
name tag was seen up close), where the workbench and the altar are, and where stones or flint lay.

Creature names are only on screen while the game shows their head-up name (about 10 m, or when looked
at). The body still sends a species key for every creature it sees, so a creature recognised once is
recognised again from afar, like a person who has met a boar before. Keys never reach a model prompt.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from thorkell.lang import tr
from thorkell.mind.store import Store

SCHEMA = """
CREATE TABLE IF NOT EXISTS species (key TEXT PRIMARY KEY, name TEXT NOT NULL, learned REAL NOT NULL);
CREATE TABLE IF NOT EXISTS places (
  name TEXT PRIMARY KEY, kind TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL, z REAL NOT NULL,
  updated REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  item TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL, times INTEGER NOT NULL, updated REAL NOT NULL,
  PRIMARY KEY (item, kind, source)
);
CREATE TABLE IF NOT EXISTS sightings (
  name TEXT NOT NULL, kind TEXT NOT NULL, cell TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL,
  z REAL NOT NULL, seen REAL NOT NULL, PRIMARY KEY (name, cell)
);
"""

# 한 번 보면 기억해 두는 고정된 곳. 같은 이름이 여럿이면(작업대 두 개) 가장 최근에 본 것을 쓴다.
PLACE_KINDS = frozenset(
    {"station", "cooking", "fire", "bed", "altar", "runestone", "chest", "smelter", "vegvisir", "item_stand"}
)
# 다시 찾아갈 자원. 같은 칸(이 크기의 격자) 안에서는 하나만 남긴다.
RESOURCE_KINDS = frozenset({"pickable", "tree", "rock", "item"})
CELL_M = 16.0
SIZE_KO = {"small": "작은", "medium": "중간 크기", "large": "큰"}
SIZE_EN = {"small": "small", "medium": "medium-sized", "large": "big"}


@dataclass(frozen=True)
class Place:
    name: str
    kind: str
    pos: tuple[float, float, float]


class WorldMemory:
    def __init__(self, store: Store) -> None:
        self.db = store.db
        self.db.executescript(SCHEMA)

    def on_scene(self, scene: dict[str, Any], here: Sequence[float]) -> list[str]:
        """Remember what this scene shows. Returns creature names learned for the first time."""
        learned: list[str] = []
        now = time.time()
        for entity in scene.get("nearby", []):
            kind, name, pos = entity.get("kind"), str(entity.get("name") or ""), entity.get("pos")
            if kind == "creature" and name and entity.get("key"):
                cursor = self.db.execute(
                    "INSERT OR IGNORE INTO species(key, name, learned) VALUES (?, ?, ?)",
                    (entity["key"], name, now),
                )
                if cursor.rowcount == 1:
                    learned.append(name)
            elif kind in PLACE_KINDS and name and pos:
                self.db.execute(
                    "INSERT INTO places(name, kind, x, y, z, updated) VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, x=excluded.x, y=excluded.y, "
                    "z=excluded.z, updated=excluded.updated",
                    (name, kind, *pos, now),
                )
            elif kind in RESOURCE_KINDS and name and pos:
                cell = f"{math.floor(pos[0] / CELL_M)}:{math.floor(pos[2] / CELL_M)}"
                self.db.execute(
                    "INSERT INTO sightings(name, kind, cell, x, y, z, seen) VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(name, cell) DO UPDATE SET x=excluded.x, y=excluded.y, z=excluded.z, "
                    "seen=excluded.seen",
                    (name, kind, cell, *pos, now),
                )
        # 지도에 찍힌 표시(베그비시르가 알려 준 보스 자리 등)도 가 볼 수 있는 곳이다.
        for pin in scene.get("pins", []):
            if pin.get("name") and pin.get("type") != "Death":
                self.db.execute(
                    "INSERT INTO places(name, kind, x, y, z, updated) VALUES (?, 'pin', ?, ?, ?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET x=excluded.x, y=excluded.y, z=excluded.z",
                    (pin["name"], *pin["pos"], now),
                )
        self.db.commit()
        return learned

    # --- creatures ------------------------------------------------------------------------------
    def species_name(self, key: str) -> str | None:
        row = self.db.execute("SELECT name FROM species WHERE key=?", (key,)).fetchone()
        return None if row is None else str(row["name"])

    def knows_creature(self, name: str) -> bool:
        return self.db.execute("SELECT 1 FROM species WHERE name=?", (name,)).fetchone() is not None

    def creature_names(self) -> list[str]:
        return [str(row["name"]) for row in self.db.execute("SELECT name FROM species ORDER BY learned")]

    def creature_label(self, entity: dict[str, Any]) -> str:
        """How Thorkell would call this creature right now."""
        if entity.get("name"):
            return str(entity["name"])
        known = self.species_name(str(entity.get("key", ""))) if entity.get("key") else None
        if known is not None:
            return tr(f"{known}(멀리)", f"{known} (far off)")
        size = str(entity.get("size"))
        return tr(
            f"처음 보는 {SIZE_KO.get(size, '')} 생물", f"unfamiliar {SIZE_EN.get(size, '')} creature"
        ).replace("  ", " ")

    # --- places ---------------------------------------------------------------------------------
    def remember_place(self, name: str, kind: str, pos: Sequence[float]) -> None:
        self.db.execute(
            "INSERT INTO places(name, kind, x, y, z, updated) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, x=excluded.x, y=excluded.y, z=excluded.z, "
            "updated=excluded.updated",
            (name, kind, *pos, time.time()),
        )
        self.db.commit()

    def place(self, name: str) -> Place | None:
        row = self.db.execute("SELECT * FROM places WHERE name=?", (name,)).fetchone()
        return None if row is None else Place(row["name"], row["kind"], (row["x"], row["y"], row["z"]))

    def places(self) -> list[Place]:
        rows = self.db.execute("SELECT * FROM places ORDER BY name")
        return [Place(row["name"], row["kind"], (row["x"], row["y"], row["z"])) for row in rows]

    # --- where things come from ------------------------------------------------------------------
    def learn_source(self, item: str, kind: str, source: str) -> bool:
        """Thorkell got `item` from `source` (a pickable's name, a creature's name, "tree"). Returns True the
        first time, which is worth saying out loud."""
        cursor = self.db.execute(
            "INSERT INTO sources(item, kind, source, times, updated) VALUES (?, ?, ?, 1, ?) "
            "ON CONFLICT(item, kind, source) DO UPDATE SET times=times+1, updated=excluded.updated",
            (item, kind, source, time.time()),
        )
        first = cursor.rowcount == 1 and self.source_times(item, kind, source) == 1
        self.db.commit()
        return first

    def source_times(self, item: str, kind: str, source: str) -> int:
        row = self.db.execute(
            "SELECT times FROM sources WHERE item=? AND kind=? AND source=?", (item, kind, source)
        ).fetchone()
        return 0 if row is None else int(row["times"])

    def sources(self, item: str) -> list[tuple[str, str]]:
        """(kind, source) Thorkell has got `item` from, most used first."""
        rows = self.db.execute(
            "SELECT kind, source FROM sources WHERE item=? ORDER BY times DESC, updated DESC", (item,)
        )
        return [(str(row["kind"]), str(row["source"])) for row in rows]

    def yields(self, kind: str, source: str) -> list[str]:
        rows = self.db.execute("SELECT item FROM sources WHERE kind=? AND source=?", (kind, source))
        return [str(row["item"]) for row in rows]

    # --- resources ------------------------------------------------------------------------------
    def where_seen(self, name: str, here: Sequence[float]) -> tuple[float, float, float] | None:
        rows = self.db.execute("SELECT x, y, z FROM sightings WHERE name=?", (name,)).fetchall()
        if not rows:
            return None
        best = min(rows, key=lambda r: math.hypot(r["x"] - here[0], r["z"] - here[2]))
        return (best["x"], best["y"], best["z"])

    def forget_sighting(self, name: str, pos: Sequence[float]) -> None:
        """The thing is gone from where it was seen (picked, or never there again)."""
        cell = f"{math.floor(pos[0] / CELL_M)}:{math.floor(pos[2] / CELL_M)}"
        self.db.execute("DELETE FROM sightings WHERE name=? AND cell=?", (name, cell))
        self.db.commit()

    def seen_names(self) -> list[str]:
        return [str(row["name"]) for row in self.db.execute("SELECT DISTINCT name FROM sightings")]
