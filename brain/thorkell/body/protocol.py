"""Bridge protocol v1 (brain <-> BepInEx plugins).

Mirrors plugin/Thorkell.Wire. Every message is one flat JSON object per line:
{"v": 1, "t": "<type>", "seq": n, "ts": unix_ms, ...body}. The shared fixtures in
protocol/v1/fixtures pin the exact shape for both implementations.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

MAJOR = 1
MINOR = 0
MAX_LINE_BYTES = 256 * 1024


class ProtocolError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)


class GameInfo(_Model):
    version: str
    network: int
    assembly_sha256: str


class VersionGateInfo(_Model):
    ok: bool
    found: str
    tested: str


class _Message(_Model):
    v: int = MAJOR
    seq: int
    ts: int


class Challenge(_Message):
    t: Literal["challenge"] = "challenge"
    nonce: str
    proto: tuple[int, int] = (MAJOR, MINOR)


class Hello(_Message):
    t: Literal["hello"] = "hello"
    role: Literal["body", "host"]
    proto: tuple[int, int]
    plugin: str
    game: GameInfo
    session: str
    caps: tuple[str, ...]
    mac: str


class Welcome(_Message):
    t: Literal["welcome"] = "welcome"
    accepted_caps: tuple[str, ...]
    state_hz: int
    scene_hz: int


class Reject(_Message):
    t: Literal["reject"] = "reject"
    reason: str


class Status(_Message):
    t: Literal["status"] = "status"
    armed: bool
    ready: bool
    reasons: tuple[str, ...]
    version_gate: VersionGateInfo
    perf: dict[str, Any] | None = None


class State(_Message):
    t: Literal["state"] = "state"
    tick: int
    data: dict[str, Any]


class Scene(_Message):
    t: Literal["scene"] = "scene"
    tick: int
    data: dict[str, Any]


class Event(_Message):
    t: Literal["event"] = "event"
    kind: str
    tick: int
    data: dict[str, Any]


class Command(_Message):
    t: Literal["cmd"] = "cmd"
    id: str
    op: str
    args: dict[str, Any]
    mode: Literal["replace", "queue", "interrupt"] = "replace"
    priority: int = 0
    based_on_seq: int
    ttl_ms: int
    resume: bool = False


class Cancel(_Message):
    t: Literal["cancel"] = "cancel"
    cmd_id: str
    reason: str


class StopAll(_Message):
    t: Literal["stop_all"] = "stop_all"
    reason: str


class Ack(_Message):
    t: Literal["ack"] = "ack"
    cmd_id: str
    accepted: bool
    code: str


class Progress(_Message):
    t: Literal["progress"] = "progress"
    cmd_id: str
    metrics: dict[str, Any]


class Result(_Message):
    t: Literal["result"] = "result"
    cmd_id: str
    status: Literal["succeeded", "failed", "cancelled", "preempted"]
    code: str
    evidence: dict[str, Any]


class Query(_Message):
    t: Literal["query"] = "query"
    id: str
    what: str
    args: dict[str, Any]


class QueryResult(_Message):
    t: Literal["query_result"] = "query_result"
    id: str
    ok: bool
    data: Any = None
    error: str | None = None


class Config(_Message):
    t: Literal["config"] = "config"
    values: dict[str, Any]


Message = (
    Challenge
    | Hello
    | Welcome
    | Reject
    | Status
    | State
    | Scene
    | Event
    | Command
    | Cancel
    | StopAll
    | Ack
    | Progress
    | Result
    | Query
    | QueryResult
    | Config
)

TYPES: dict[str, type[_Message]] = {
    "challenge": Challenge,
    "hello": Hello,
    "welcome": Welcome,
    "reject": Reject,
    "status": Status,
    "state": State,
    "scene": Scene,
    "event": Event,
    "cmd": Command,
    "cancel": Cancel,
    "stop_all": StopAll,
    "ack": Ack,
    "progress": Progress,
    "result": Result,
    "query": Query,
    "query_result": QueryResult,
    "config": Config,
}


def decode(line: str) -> Message:
    if len(line.encode("utf-8")) > MAX_LINE_BYTES:
        raise ProtocolError("line_too_long", f"incoming line exceeds {MAX_LINE_BYTES} bytes")
    try:
        envelope = json.loads(line)
    except json.JSONDecodeError as error:
        raise ProtocolError("bad_json", str(error)) from error
    if not isinstance(envelope, dict):
        raise ProtocolError("bad_envelope", "message is not a JSON object")

    version = envelope.get("v")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ProtocolError("bad_envelope", "missing integer v")
    if version != MAJOR:
        raise ProtocolError("major_mismatch", f"got v={version}, expected {MAJOR}")

    kind = envelope.get("t")
    if not isinstance(kind, str):
        raise ProtocolError("bad_envelope", "missing string t")
    model = TYPES.get(kind)
    if model is None:
        raise ProtocolError("unknown_type", kind)

    try:
        message = model.model_validate_json(line)
    except ValidationError as error:
        raise ProtocolError("bad_body", f"{kind}: {error}") from error
    return message  # type: ignore[return-value]


def encode(message: Message) -> str:
    line = message.model_dump_json(exclude_none=True)
    if len(line.encode("utf-8")) > MAX_LINE_BYTES:
        raise ProtocolError("line_too_long", f"{message.t} exceeds {MAX_LINE_BYTES} bytes")
    return line
