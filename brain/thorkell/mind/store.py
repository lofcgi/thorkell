"""Knowledge store (SQLite, WAL). Facts carry provenance and a status that only evidence changes.

status:
  hypothesis  told by someone (or inferred) and not yet seen
  supported   seen at least once, never contradicted more than supported
  verified    seen >= 3 times, or told and then seen
  refuted     contradicted at least twice and more often than supported

Lessons are what Thorkell took from an episode (a fight) in his own words. They start as hypotheses and the
same evidence rule moves them: each later episode that followed a lesson says whether it held.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thorkell.lang import tr

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS entities (
  name TEXT PRIMARY KEY, kind TEXT NOT NULL, first_seen REAL NOT NULL, via TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS facts (
  id TEXT PRIMARY KEY,
  subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL,
  provenance TEXT NOT NULL,
  told INTEGER NOT NULL DEFAULT 0, support INTEGER NOT NULL DEFAULT 0, contradict INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
  UNIQUE(subject, predicate, object)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, kind TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS utterances (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL, speaker TEXT NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS texts (
  label TEXT PRIMARY KEY, text TEXT NOT NULL, at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
  id TEXT PRIMARY KEY, at REAL NOT NULL, about TEXT NOT NULL, outcome TEXT NOT NULL, record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
  id TEXT PRIMARY KEY, about TEXT NOT NULL, text TEXT NOT NULL, learned_from TEXT NOT NULL,
  support INTEGER NOT NULL DEFAULT 0, contradict INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL
);
"""
# 특정 상대가 아니라 싸움 전반에 대한 교훈의 about 값
GENERAL = "일반"
GENERAL_EN = "general"


def general() -> str:
    """The `about` of a lesson for any fight, in the language being played."""
    return tr(GENERAL, GENERAL_EN)


@dataclass(frozen=True)
class Fact:
    id: str
    subject: str
    predicate: str
    object: str
    provenance: str
    told: int
    support: int
    contradict: int
    status: str

    def line(self) -> str:
        how = f"seen {self.support}x" + (f", contradicted {self.contradict}x" if self.contradict else "")
        head = f"{self.id} {self.subject} {self.predicate} {self.object}"
        return f"{head} ({self.status}; {self.provenance}; {how})"


@dataclass(frozen=True)
class Episode:
    id: str
    about: str
    outcome: str
    record: dict[str, Any]


@dataclass(frozen=True)
class Lesson:
    id: str
    about: str
    text: str
    learned_from: str
    support: int
    contradict: int
    status: str

    def line(self) -> str:
        how = tr(f"맞았음 {self.support}번", f"held {self.support}x") + (
            tr(f", 틀렸음 {self.contradict}번", f", wrong {self.contradict}x") if self.contradict else ""
        )
        learned = tr(f"{self.learned_from}에서 배움", f"learned from {self.learned_from}")
        return f"{self.id} [{self.about}] {self.text} ({self.status}; {learned}; {how})"


def status_of(told: int, support: int, contradict: int) -> str:
    if contradict >= 2 and contradict > support:
        return "refuted"
    if support >= 3 or (told and support >= 1):
        return "verified"
    if support >= 1:
        return "supported"
    return "hypothesis"


class Store:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # --- entities -------------------------------------------------------------------------------
    def know_entity(self, name: str, kind: str, via: str) -> bool:
        """Returns True if this is the first time Thorkell knows of this name."""
        cursor = self.db.execute(
            "INSERT OR IGNORE INTO entities(name, kind, first_seen, via) VALUES (?, ?, ?, ?)",
            (name, kind, time.time(), via),
        )
        self.db.commit()
        return cursor.rowcount == 1

    def entity_names(self) -> set[str]:
        return {row["name"] for row in self.db.execute("SELECT name FROM entities")}

    # --- facts ----------------------------------------------------------------------------------
    def fact(self, subject: str, predicate: str, obj: str) -> Fact | None:
        row = self.db.execute(
            "SELECT * FROM facts WHERE subject=? AND predicate=? AND object=?", (subject, predicate, obj)
        ).fetchone()
        return None if row is None else _fact(row)

    def _upsert(self, subject: str, predicate: str, obj: str, provenance: str) -> Fact:
        existing = self.fact(subject, predicate, obj)
        if existing is not None:
            return existing
        count = self.db.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        now = time.time()
        self.db.execute(
            "INSERT INTO facts(id, subject, predicate, object, provenance, status, created, updated) "
            "VALUES (?, ?, ?, ?, ?, 'hypothesis', ?, ?)",
            (f"F{count + 1}", subject, predicate, obj, provenance, now, now),
        )
        created = self.fact(subject, predicate, obj)
        assert created is not None
        return created

    def _bump(self, fact: Fact, told: int = 0, support: int = 0, contradict: int = 0) -> tuple[Fact, Fact]:
        t, s, c = fact.told + told, fact.support + support, fact.contradict + contradict
        self.db.execute(
            "UPDATE facts SET told=?, support=?, contradict=?, status=?, updated=? WHERE id=?",
            (t, s, c, status_of(t, s, c), time.time(), fact.id),
        )
        self.db.commit()
        after = self.fact(fact.subject, fact.predicate, fact.object)
        assert after is not None
        return fact, after

    def tell(self, subject: str, predicate: str, obj: str) -> tuple[Fact, Fact]:
        return self._bump(self._upsert(subject, predicate, obj, "told"), told=1)

    def observe(self, subject: str, predicate: str, obj: str) -> tuple[Fact, Fact]:
        return self._bump(self._upsert(subject, predicate, obj, "observed"), support=1)

    def contradict(self, subject: str, predicate: str, obj: str) -> tuple[Fact, Fact] | None:
        existing = self.fact(subject, predicate, obj)
        return None if existing is None else self._bump(existing, contradict=1)

    def facts_about(self, subject: str) -> list[Fact]:
        rows = self.db.execute("SELECT * FROM facts WHERE subject=? ORDER BY id", (subject,))
        return [_fact(row) for row in rows]

    def all_facts(self, limit: int = 200) -> list[Fact]:
        rows = self.db.execute(
            "SELECT * FROM facts WHERE status != 'refuted' ORDER BY updated DESC LIMIT ?", (limit,)
        )
        return [_fact(row) for row in rows]

    # --- logs -----------------------------------------------------------------------------------
    def log_event(self, kind: str, data: str) -> None:
        self.db.execute("INSERT INTO events(at, kind, data) VALUES (?, ?, ?)", (time.time(), kind, data))
        self.db.commit()

    def log_utterance(self, speaker: str, text: str) -> None:
        self.db.execute(
            "INSERT INTO utterances(at, speaker, text) VALUES (?, ?, ?)", (time.time(), speaker, text)
        )
        self.db.commit()

    def recent_utterances(self, limit: int = 8, since: float = 0.0) -> list[tuple[str, str]]:
        rows = self.db.execute(
            "SELECT speaker, text FROM utterances WHERE at >= ? ORDER BY id DESC LIMIT ?", (since, limit)
        )
        return [(str(row["speaker"]), str(row["text"])) for row in rows][::-1]

    # --- texts the game showed (runestones, the raven) --------------------------------------------
    def log_text(self, label: str, text: str) -> None:
        self.db.execute(
            "INSERT INTO texts(label, text, at) VALUES (?, ?, ?) ON CONFLICT(label) DO NOTHING",
            (label, text, time.time()),
        )
        self.db.commit()

    def recent_texts(self, limit: int = 6) -> list[tuple[str, str]]:
        rows = self.db.execute("SELECT label, text FROM texts ORDER BY at DESC LIMIT ?", (limit,))
        return [(str(row["label"]), str(row["text"])) for row in rows]

    # --- episodes and the lessons taken from them ---------------------------------------------------
    def add_episode(self, about: str, outcome: str, record: dict[str, Any]) -> Episode:
        count = self.db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        episode = Episode(f"E{count + 1}", about, outcome, record)
        self.db.execute(
            "INSERT INTO episodes(id, at, about, outcome, record) VALUES (?, ?, ?, ?, ?)",
            (episode.id, time.time(), about, outcome, json.dumps(record, ensure_ascii=False)),
        )
        self.db.commit()
        return episode

    def episodes(self, about: str, limit: int = 3) -> list[Episode]:
        """The latest episodes about `about`, oldest first."""
        rows = self.db.execute(
            "SELECT * FROM episodes WHERE about=? ORDER BY at DESC, id DESC LIMIT ?", (about, limit)
        )
        return [Episode(row["id"], row["about"], row["outcome"], json.loads(row["record"])) for row in rows][
            ::-1
        ]

    def add_lesson(self, about: str, text: str, learned_from: str) -> Lesson:
        count = self.db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        now = time.time()
        lesson_id = f"L{count + 1}"
        self.db.execute(
            "INSERT INTO lessons(id, about, text, learned_from, status, created, updated) "
            "VALUES (?, ?, ?, ?, 'hypothesis', ?, ?)",
            (lesson_id, about, text, learned_from, now, now),
        )
        self.db.commit()
        lesson = self.lesson(lesson_id)
        assert lesson is not None
        return lesson

    def lesson(self, lesson_id: str) -> Lesson | None:
        row = self.db.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        return None if row is None else _lesson(row)

    def judge_lesson(self, lesson_id: str, held: bool) -> tuple[Lesson, Lesson]:
        """A later episode followed the lesson and it held (or not)."""
        before = self.lesson(lesson_id)
        if before is None:
            raise KeyError(f"no lesson {lesson_id}")
        support, contradict = before.support + int(held), before.contradict + int(not held)
        self.db.execute(
            "UPDATE lessons SET support=?, contradict=?, status=?, updated=? WHERE id=?",
            (support, contradict, status_of(0, support, contradict), time.time(), lesson_id),
        )
        self.db.commit()
        after = self.lesson(lesson_id)
        assert after is not None
        return before, after

    def lessons(self, about: tuple[str, ...] | None = None, limit: int = 20) -> list[Lesson]:
        """Lessons still standing (not refuted), oldest first; only those about `about` if given."""
        rows = self.db.execute("SELECT * FROM lessons WHERE status != 'refuted' ORDER BY created, id")
        found = [_lesson(row) for row in rows if about is None or row["about"] in about]
        return found[-limit:]


def _lesson(row: sqlite3.Row) -> Lesson:
    return Lesson(
        row["id"],
        row["about"],
        row["text"],
        row["learned_from"],
        row["support"],
        row["contradict"],
        row["status"],
    )


def _fact(row: sqlite3.Row) -> Fact:
    return Fact(
        row["id"],
        row["subject"],
        row["predicate"],
        row["object"],
        row["provenance"],
        row["told"],
        row["support"],
        row["contradict"],
        row["status"],
    )
