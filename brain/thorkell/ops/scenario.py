"""Native (real game) scenarios. Exactly one at a time; never touches the human's install or saves.

A run creates two disposable runtimes (host-test with Thorkell.Host + harness, body with Thorkell.Body
+ harness), launches both through Rosetta, optionally serves the brain bridge, and always ends with
SIGKILL + guard checks (prefs/saves) + a report under artifacts/native/<name>/.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import fcntl
import json
import math
import os
import re
import secrets
import shutil
import signal
import subprocess
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from thorkell import lang
from thorkell.body import auth
from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession
from thorkell.config import load, secret
from thorkell.control.controller import Controller
from thorkell.control.goals import Goal, Tier
from thorkell.lang import GAME_LANGUAGE, Language, tr
from thorkell.mind.mind import Mind
from thorkell.mind.store import Store
from thorkell.models.gemini import GeminiJson
from thorkell.ops import backup, guard, recording, runtime, vendor
from thorkell.paths import REPO_ROOT, THORKELL_HOME
from thorkell.plan.planner import Planner, PlannerConfig
from thorkell.plan.tactics import Tactician
from thorkell.world.sight import Eyes
from thorkell.world.where import distance_m

HARNESS_BUILD = REPO_ROOT / "tests/native/Thorkell.NativeHarness/bin/Release/netstandard2.1"
TEST_GAME_PORT = 54879
TEST_BRIDGE_PORT = 47821
WORLD = "ThorkellLab"
SEED = "ThorkellMeadows1"
LEADER = "Leader"
BOT = "Thorkell"
# 보스 시나리오의 리더(하네스)는 싸우지 않는다. 사람이라면 그렇다고 말해 준다.
LEADER_WATCHES = "나는 싸움은 못 도와줘. 멀리서 지켜볼게. 이번엔 너 혼자 해 봐"
# 같이 싸우는 시험(--together)의 리더가 하는 말.
LEADER_HOLDS = "같이 잡자! 내가 앞에서 막을게, 넌 뒤에서 활로 쏴 줘"
# 대답을 들은 리더가 보스를 불러내자고 하는 말.
LEADER_SUMMONS = "좋아, 사슴 트로피를 제단에 올려서 불러내 줘"
LEADER_SUMMONS_EN = "Alright, put the deer trophies on the altar and call him out"
LEADER_WATCHES_EN = "I can't help with the fighting. I'll watch from far away. You try it alone this time"
LEADER_HOLDS_EN = (
    "Let's take him down together! I'll hold him up front, you shoot him with the bow from behind"
)
# --mortal-leader: 사람 리더처럼 음식 세 칸을 채우고 싸운다(시험 fixture).
MORTAL_LEADER_FOOD = ["CookedMeat", "Raspberry", "Mushroom"]
GAME_ARGS = ["-batchmode", "-screen-width", "640", "-screen-height", "360", "-screen-fullscreen", "0"]
# 아침으로 넘긴 시간이 봇에게 전해질 때까지.
MORNING_SYNC_S = 3.0
RECORD_GAME_ARGS = ["-screen-width", "1280", "-screen-height", "720", "-screen-fullscreen", "0"]


class ScenarioError(Exception):
    """The scenario could not run (environment problem), as opposed to a failed check."""


class StepFailed(Exception):
    """A scenario expectation was not met."""


@contextmanager
def native_lock() -> Iterator[None]:
    THORKELL_HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (THORKELL_HOME / "native.lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ScenarioError("another native scenario is running") from error
        yield


def refuse_while_valheim_runs(game: Path) -> None:
    real = subprocess.run(
        ["pgrep", "-f", str(game / "Valheim.app")], capture_output=True, text=True, check=False
    )
    if real.stdout.strip():
        raise ScenarioError("the real Valheim is running; close it so prefs/save checks stay meaningful")


def preflight(game: Path) -> None:
    if subprocess.run(["pgrep", "-x", "steam_osx"], capture_output=True, check=False).returncode != 0:
        raise ScenarioError("Steam is not running; start Steam and sign in first")
    refuse_while_valheim_runs(game)
    for name, build in {**runtime.PLUGIN_BUILDS, "harness": HARNESS_BUILD}.items():
        if not any(build.glob("*.dll")):
            raise ScenarioError(f"{name} plugin not built: run `dotnet build Thorkell.sln -c Release`")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data: dict[str, Any] = json.loads(path.read_text())
    return data


@dataclass
class Setup:
    name: str
    backend: str = "steam"
    timeout_s: int = 300
    bridge: bool = False
    inventory_fixtures: str = ""
    world_fixtures: str = ""
    existing_targets: str = ""
    leader_offset: str = "flat"
    bot_offset: str = "4,0"
    # 시작 신전 말고 더 만들 장소(예: "Eikthyrnir"). 시험 월드는 속도 때문에 다른 장소를 만들지 않는다.
    locations: str = ""
    # 이름을 주면 테스트용 일회용 월드 대신, 가장 최근 백업의 그 월드를 복사해서 연다(사람의 원본은 그대로).
    backup_world: str | None = None
    # 두 게임과 두뇌가 쓰는 언어(config의 language).
    language: Language = "ko"
    # README 영상: 토르켈의 게임 창(1280x720)을 화면에서 녹화하고,
    # 자막에 쓸 말과 단계 시각을 timeline.jsonl로 남긴다.
    record: bool = False

    @property
    def world(self) -> str:
        return self.backup_world or WORLD


@dataclass
class Step:
    name: str
    ok: bool
    detail: Any
    seconds: float


@dataclass
class NativeRun:
    game: Path
    setup: Setup
    session: BodySession = field(default_factory=BodySession)
    steps: list[Step] = field(default_factory=list)
    report: dict[str, Any] = field(default_factory=dict)
    # 시나리오가 리포트에 덧붙이는 관찰(대화 기록, 지연 등)
    extra: dict[str, Any] = field(default_factory=dict)
    # 녹화할 때: 단계와 말(누가, 무엇을, 벽시계 시각). 영상 자막과 GIF 자르기에 쓴다.
    timeline: list[dict[str, Any]] = field(default_factory=list)
    recording: recording.WindowRecording | None = None

    async def __aenter__(self) -> NativeRun:
        preflight(self.game)
        bepinex = vendor.ensure(vendor.load()) / "BepInExPack_Valheim"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.label = f"{self.setup.name}-{self.setup.backend}-{stamp}"
        self.run_dir = THORKELL_HOME / "tests" / self.label
        self.artifacts = REPO_ROOT / "artifacts/native" / self.label
        self.artifacts.mkdir(parents=True)
        self._stack = ExitStack()
        self._stack.enter_context(native_lock())

        self.prefs_before = guard.snapshot_prefs()
        self.saves_before = guard.fingerprint()
        self.host = runtime.create(
            self.run_dir / "host",
            "host-test",
            self.game,
            bepinex,
            [runtime.PLUGIN_BUILDS["host"], HARNESS_BUILD],
        )
        self.body = runtime.create(
            self.run_dir / "body",
            "body",
            self.game,
            bepinex,
            [runtime.PLUGIN_BUILDS["body"], HARNESS_BUILD],
        )
        if self.setup.backup_world is not None:
            made = backup.latest()
            if made is None:
                raise ScenarioError("no backup yet: run `thorkell backup` first")
            runtime.seed_saves(self.host, made.world(self.setup.backup_world), [])
        self._configure()

        self.server: BridgeServer | None = None
        if self.setup.bridge:
            self.server = BridgeServer(self._token, self.session.on_message)
            self.session.attach(self.server)
            await self.server.start(TEST_BRIDGE_PORT)

        self.started = time.monotonic()
        self.samples: list[dict[str, Any]] = []
        self.processes: dict[str, subprocess.Popen[bytes]] = {}
        try:
            self.processes["host"] = self._launch(self.host, ["-thorkell-host", "-thorkell-harness"])
            await self.wait_files([(self.host, "host-ready.json")])
            body_args = ["-thorkell-body", "-thorkell-harness"]
            # 녹화할 때 토르켈 창은 사람이 보는 크기의 보통 창으로 띄운다(batchmode의 작은 창이 아니라).
            game_args = RECORD_GAME_ARGS if self.setup.record else GAME_ARGS
            self.processes["body"] = self._launch(self.body, body_args, game_args)
            ready = [(self.body, "client-ready.json")]
            if self.setup.inventory_fixtures or self.setup.world_fixtures or self.setup.existing_targets:
                ready.append((self.body, "fixtures-ready.json"))
            await self.wait_files(ready)
            if self.setup.record:
                self.recording = recording.WindowRecording(
                    self.processes["body"].pid,
                    self.artifacts / "thorkell.mp4",
                    lambda path, at: self.timeline.append({"kind": "video", "file": path.name, "start": at}),
                )
                await self.recording.start()
                await self.daylight(LeaderCues(self.host))
        except BaseException:
            await self._teardown(failure="setup failed")
            raise
        return self

    def _configure(self) -> None:
        self._token = auth.new_hex(32)
        password = secrets.token_urlsafe(12)
        s = self.setup
        game_language: dict[str, str | int | bool] = {"Language": GAME_LANGUAGE[s.language]}
        runtime.write_config(
            self.host,
            "thorkell.host",
            {"Listener": {"Port": TEST_GAME_PORT, "Worlds": s.world}, "Game": game_language},
        )
        runtime.write_config(
            self.host,
            "thorkell.harness",
            {
                "Harness": {
                    "Role": "host",
                    "Backend": s.backend,
                    "World": s.world,
                    "ExistingWorld": s.backup_world is not None,
                    "Seed": SEED,
                    "Password": password,
                    "LeaderName": LEADER,
                    "BotName": BOT,
                    "TimeoutSeconds": s.timeout_s,
                    "MoveOffset": s.leader_offset,
                    "Locations": s.locations,
                }
            },
        )
        body_config: dict[str, dict[str, str | int | bool]] = {
            "Join": {"Host": "127.0.0.1", "Port": TEST_GAME_PORT, "Password": password},
            "Body": {"CharacterFile": "thorkell", "CharacterName": BOT, "LeaderName": LEADER},
            "Game": game_language,
        }
        if s.bridge:
            body_config["Bridge"] = {"Port": TEST_BRIDGE_PORT, "Token": self._token}
        runtime.write_config(self.body, "thorkell.body", body_config)
        runtime.write_config(
            self.body,
            "thorkell.harness",
            {
                "Harness": {
                    "Role": "client",
                    "World": s.world,
                    "LeaderName": LEADER,
                    "BotName": BOT,
                    "TimeoutSeconds": s.timeout_s,
                    "MoveOffset": s.bot_offset,
                    "InventoryFixtures": s.inventory_fixtures,
                    "WorldFixtures": s.world_fixtures,
                    "ExistingTargets": s.existing_targets,
                }
            },
        )

    def _launch(
        self, rt: runtime.Runtime, flags: list[str], game_args: list[str] = GAME_ARGS
    ) -> subprocess.Popen[bytes]:
        log = (rt.logs / "launcher.log").open("wb")
        args = [*game_args, "-logFile", str(rt.logs / "Player.log"), *flags]
        return subprocess.Popen(
            runtime.launch_command(rt, args, self.game),
            cwd=rt.root,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def read_body(self, name: str) -> dict[str, Any]:
        data = _read(self.body.root / name)
        if data is None:
            raise StepFailed(f"{name} missing in body runtime")
        return data

    def read_host(self, name: str) -> dict[str, Any] | None:
        return _read(self.host.root / name)

    async def wait_files(self, targets: list[tuple[runtime.Runtime, str]]) -> None:
        next_sample = 0.0
        while time.monotonic() - self.started < self.setup.timeout_s:
            if all((rt.root / marker).is_file() for rt, marker in targets):
                return
            for role, process in self.processes.items():
                if process.poll() is not None:
                    raise StepFailed(f"{role} process exited with {process.returncode}")
            for rt, _ in targets:
                result = _read(rt.root / "result.json")
                if result is not None and not result.get("passed"):
                    raise StepFailed(f"{rt.role} harness failed: {result.get('detail')}")
            if time.monotonic() >= next_sample:
                next_sample = time.monotonic() + 2
                self._sample()
            await asyncio.sleep(0.5)
        raise StepFailed(f"timeout waiting for {[marker for _, marker in targets]}")

    def _sample(self) -> None:
        entry: dict[str, Any] = {"t": round(time.monotonic() - self.started, 1)}
        for role, process in self.processes.items():
            if process.poll() is not None:
                continue
            out = subprocess.run(
                ["ps", "-o", "rss=,pcpu=", "-p", str(process.pid)],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.split()
            if len(out) == 2:
                entry[role] = {"rss_mb": round(int(out[0]) / 1024), "cpu_pct": float(out[1])}
        self.samples.append(entry)

    async def step(self, name: str, action: Callable[[], Awaitable[Any]]) -> Any:
        began, wall = time.monotonic(), time.time()
        try:
            detail = await action()
        except (StepFailed, TimeoutError) as error:
            self.steps.append(
                Step(name, False, f"{type(error).__name__}: {error}", round(time.monotonic() - began, 2))
            )
            self.timeline.append(
                {"kind": "step", "name": name, "ok": False, "start": wall, "end": time.time()}
            )
            raise StepFailed(f"{name}: {error}") from error
        self.steps.append(Step(name, True, detail, round(time.monotonic() - began, 2)))
        self.timeline.append({"kind": "step", "name": name, "ok": True, "start": wall, "end": time.time()})
        return detail

    async def daylight(self, cues: LeaderCues) -> None:
        """Recording only: the test world often starts at night, too dark for a video. Skip to morning the
        way sleeping does; the harness answers once the skip is over."""
        if self.setup.record:
            done = await cues.do({"morning": True}, timeout=60)
            if done["detail"] == "morning":
                await asyncio.sleep(MORNING_SYNC_S)

    def note_said(self, who: str, text: str, at: float | None = None) -> None:
        self.timeline.append(
            {"kind": "said", "who": who, "text": text, "at": time.time() if at is None else at}
        )

    def note_thorkell(self, controller: Controller) -> None:
        """What Thorkell said (and murmured), at wall-clock times, for the video's captions."""
        offset = time.time() - time.monotonic()
        for decision in controller.decisions:
            if decision.kind == "speak":
                self.note_said(BOT, decision.reason_ko.split("] ", 1)[-1], decision.at + offset)

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> bool:
        failure = None if exc is None else f"{type(exc).__name__}: {exc}"
        await self._teardown(failure)
        # StepFailed is a recorded test failure (report.passed=False); anything else propagates.
        return exc_type is StepFailed

    async def _teardown(self, failure: str | None) -> None:
        if self.recording is not None:
            await self.recording.stop()
        for rt in (self.host, self.body):
            (rt.root / "stop.txt").write_text("stop\n")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not all(
            (rt.root / "result.json").is_file()
            for rt, role in ((self.host, "host"), (self.body, "body"))
            if role in self.processes
        ):
            await asyncio.sleep(0.5)
        exit_codes: dict[str, int | None] = {}
        for role, process in self.processes.items():
            # SIGKILL on purpose: a normal Unity quit writes Screenmanager* keys to the shared prefs domain.
            # The sandbox denies that write too, but we do not lean on a single layer.
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            exit_codes[role] = process.returncode
        if self.server is not None:
            await self.server.close()

        prefs_diff = guard.diff_prefs(self.prefs_before, guard.snapshot_prefs())
        restored = guard.restore_prefs(self.prefs_before, prefs_diff)
        saves_changed = guard.fingerprint_changes(self.saves_before, guard.fingerprint())
        results = {
            "host": _read(self.host.root / "result.json"),
            "body": _read(self.body.root / "result.json"),
        }
        passed = (
            failure is None
            and all(step.ok for step in self.steps)
            and all(r is not None and r.get("passed") for r in results.values())
            and not prefs_diff.keys
            and not saves_changed
        )
        self.report = {
            "scenario": self.setup.name,
            "backend": self.setup.backend,
            "passed": passed,
            "failure": failure,
            "elapsed_s": round(time.monotonic() - self.started, 1),
            "steps": [step.__dict__ for step in self.steps],
            "results": results,
            "host_ready": _read(self.host.root / "host-ready.json"),
            "host_peer_seen": _read(self.host.root / "host-peer-seen.json"),
            "client_ready": _read(self.body.root / "client-ready.json"),
            "fixtures": _read(self.body.root / "fixtures-ready.json"),
            "perf": {
                "host": _read(self.host.root / "perf.json"),
                "body": _read(self.body.root / "perf.json"),
            },
            "resources": self.samples,
            "exit_codes": exit_codes,
            "events": [{"kind": e.kind, "data": e.data} for e in self.session.events][-200:],
            "isolation": {
                "prefs_changed": list(prefs_diff.keys),
                "prefs_restored": restored,
                "human_saves_changed": saves_changed,
            },
            "logs": {"host": self._log_excerpt(self.host), "body": self._log_excerpt(self.body)},
            "run_dir": str(self.run_dir),
            "artifacts": str(self.artifacts),
            **self.extra,
        }
        for rt, role in ((self.host, "host"), (self.body, "body")):
            for source in (rt.bepinex_log, rt.logs / "Player.log", rt.logs / "launcher.log"):
                if source.is_file():
                    shutil.copy2(source, self.artifacts / f"{role}-{source.name}")
        (self.artifacts / "report.json").write_text(
            json.dumps(self.report, indent=2, ensure_ascii=False) + "\n"
        )
        if self.setup.record:
            with (self.artifacts / "timeline.jsonl").open("w") as out:
                for entry in sorted(self.timeline, key=lambda e: e.get("at", e.get("start", 0))):
                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._stack.close()

    @staticmethod
    def _log_excerpt(rt: runtime.Runtime) -> list[str]:
        if not rt.bepinex_log.is_file():
            return ["<no LogOutput.log>"]
        lines = rt.bepinex_log.read_text(errors="replace").splitlines()
        keep = [
            line for line in lines if any(m in line for m in ("THORKELL", "HARNESS", "Error", "Exception"))
        ]
        return keep[-80:]


async def run_rehearsal(
    game: Path, backend: str, timeout_s: int, world: str = "helloworld"
) -> dict[str, Any]:
    """Rehearsal smoke: the latest backup's copy of the human's world loads in an isolated test host,
    and the bot joins it with a password and links to the brain. The human's own saves are never opened."""
    run = NativeRun(
        game, Setup("rehearsal", backend=backend, timeout_s=timeout_s, bridge=True, backup_world=world)
    )
    async with run:
        s = run.session
        await run.step("peer_seen_by_host", lambda: run.wait_files([(run.host, "host-peer-seen.json")]))

        async def world_loaded() -> dict[str, Any]:
            ready = run.read_host("host-ready.json") or {}
            if ready.get("world") != world:
                raise StepFailed(f"host opened {ready.get('world')!r}, not the backed-up {world!r}")
            return ready

        await run.step("backed_up_world_open", world_loaded)
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))

        async def hello() -> dict[str, Any]:
            return _expect(
                await s.command("say", {"talker": "normal", "text": "토르켈 리허설 점검: 안녕!"}), {"said"}
            )

        await run.step("say_hello", hello)
    return run.report


async def run_peer(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    run = NativeRun(game, Setup("peer", backend=backend, timeout_s=timeout_s))
    async with run:
        await run.step("peer_seen_by_host", lambda: run.wait_files([(run.host, "host-peer-seen.json")]))
    return run.report


def _expect(result: Any, codes: set[str]) -> dict[str, Any]:
    if result.status != "succeeded" or result.code not in codes:
        raise StepFailed(f"{result.status}/{result.code} {result.evidence}")
    evidence: dict[str, Any] = {"code": result.code, **result.evidence}
    return evidence


async def run_primitives(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    """S1: the brain drives the bot through the bridge: equip, eat, move, pickup, chop, look, say,
    and the game's own auto-pickup."""
    setup = Setup(
        "primitives",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        inventory_fixtures="AxeStone:1,Raspberry:3",
        # 앞,오른쪽 오프셋의 기준 방향은 하네스가 고른다.
        # 봇 둘레에서 가장 평평하고 리더와 5m 이상 떨어진 방향이다.
        # 자동 줍기(Player.AutoPickup)는 아이템 기준점까지 2m로 판단한다. 나무 더미는 2m 남짓 길어서
        # 끝에 도착해도 기준점이 멀 수 있다. 그래서 작고 자동으로 주워지는 돌로 시험하고,
        # 굴러와 미리 주워지지 않게 멀리 둔다.
        world_fixtures="Wood@3,0;Stone@-5,-5",
        # 떨어뜨린 통나무는 조금만 기울어도 구른다. 베기는 이미 서 있는 나무로 시험한다.
        existing_targets="tree",
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        names = {p["prefab"]: p.get("name") for p in placed if p["where"] == "inventory"}
        ids = {p["prefab"]: p.get("id") for p in placed if p["where"] in ("world", "existing")}

        seen_names: dict[str, str | None] = {}

        async def perceived() -> dict[str, Any]:
            # 지각은 시야와 시선이 닿는 것만 넘긴다. 바로 앞의 나무만 요구하고, 나머지는 보였는지 기록만 한다.
            try:
                await s.wait_for(lambda: ids["Wood"] in {e["id"] for e in s.nearby()}, 15)
            except TimeoutError:
                nearest = sorted(s.nearby(), key=lambda e: e["distance"])[:8]
                summary = [(e.get("kind"), e.get("name"), round(e["distance"], 1)) for e in nearest]
                raise StepFailed(f"wood in front not perceived; nearest: {summary}") from None
            inventory = {i["name"] for i in s.inventory()}
            if not {names["AxeStone"], names["Raspberry"]} <= inventory:
                raise StepFailed(f"fixture items missing from inventory: {inventory}")
            seen = {e["id"]: e.get("name") for e in s.nearby()}
            seen_names.update({prefab: seen[i] for prefab, i in ids.items() if i in seen})
            return {
                "nearby": len(s.nearby()),
                "fixtures_seen": sorted(seen_names),
                "inventory": sorted(inventory),
            }

        await run.step("perceives_fixtures", perceived)

        async def act(op: str, args: dict[str, Any], codes: set[str], timeout: float = 30) -> dict[str, Any]:
            return _expect(await s.command(op, args, timeout=timeout), codes)

        await run.step(
            "equip_axe", lambda: act("equip", {"item": names["AxeStone"]}, {"equipped", "already_equipped"})
        )
        await run.step("eat_berries", lambda: act("eat", {"item": names["Raspberry"]}, {"eaten"}))
        # 게임의 자동 줍기는 수평 약 1.7m 안에서 일어난다.
        # 명시적 줍기(손 닿는 거리 2.5m)를 시험하려고 2.2m에서 멈춘다.
        await run.step(
            "walk_to_wood",
            lambda: act("move_to", {"target": {"id": ids["Wood"]}, "arrive_radius": 2.2}, {"arrived"}),
        )
        await run.step("pickup_wood", lambda: act("pickup", {"id": ids["Wood"]}, {"picked_up"}))
        await run.step(
            "walk_to_tree",
            lambda: act("move_to", {"target": {"id": ids["tree"]}, "arrive_radius": 1.6}, {"arrived"}),
        )

        async def chop() -> dict[str, Any]:
            # 한 번만 벤다. 나무가 쓰러지면 통나무가 굴러 다음 단계에 반사가 끼어든다.
            evidence = await act("attack", {"id": ids["tree"], "swings": 1}, {"swung", "destroyed"}, 30)
            if not evidence.get("destroyed") and not evidence.get("hp_after", 1e9) < evidence.get(
                "hp_before", 0
            ):
                raise StepFailed(f"tree health did not drop: {evidence}")

            # 한 번 휘두르면 옆 물체도 맞을 수 있다. 나무에 맞은 피해 숫자가 on_target으로 와야 한다.
            def on_target() -> list[dict[str, Any]]:
                return [e.data for e in s.events_of("damage_dealt") if e.data.get("on_target") is True]

            try:
                await s.wait_for(lambda: bool(on_target()), 5)
            except TimeoutError:
                hits = [e.data for e in s.events_of("damage_dealt")]
                raise StepFailed(f"no damage_dealt on the tree; all hits: {hits}") from None
            amounts = [float(e["amount"]) for e in on_target() if e.get("amount") is not None]
            if "hp_after" in evidence:
                drop = evidence["hp_before"] - evidence["hp_after"]
                if abs(sum(amounts) - drop) > 0.15:
                    raise StepFailed(f"on_target amounts {amounts} != tree health drop {drop:.1f}")
            return {
                **evidence,
                "damage_dealt_events": len(s.events_of("damage_dealt")),
                "on_target_amounts": amounts,
            }

        await run.step("chop_tree", chop)

        async def face_leader() -> dict[str, Any]:
            assert s.scene is not None
            leader = s.scene.data.get("leader")
            if not leader:
                raise StepFailed("leader not in scene")
            return await act("look_at", {"target": {"id": leader["id"]}}, {"facing"})

        await run.step("look_at_leader", face_leader)
        await run.step(
            "say_hello", lambda: act("say", {"talker": "normal", "text": "토르켈 테스트: 안녕!"}, {"said"})
        )

        def stones() -> int:
            return sum(int(i.get("stack", 0)) for i in s.inventory() if i.get("name") == seen_names["Stone"])

        async def auto_pickup() -> dict[str, Any]:
            if not seen_names.get("Stone"):
                raise StepFailed("the stone fixture was never perceived, so its name is unknown")
            # 게임은 기준점이 2m 안에 들어온 아이템을 끌어당겨 줍는다. 그게 도착 판정보다 늦을 수 있어서
            # move_to가 "arrived"로 끝나도 잠시 뒤 인벤토리가 늘었는지(월드 변화)로 확인한다.
            before = stones()
            evidence = await act(
                "move_to", {"target": {"id": ids["Stone"]}, "arrive_radius": 0.3}, {"picked_up", "arrived"}
            )
            try:
                await s.wait_for(lambda: stones() > before, 3)
            except TimeoutError:
                raise StepFailed(f"stone was not auto-picked: {evidence}") from None
            return {**evidence, "stones": stones()}

        await run.step("auto_pickup_stone", auto_pickup)
    return run.report


def _ahead(state: dict[str, Any], metres: float, turn_deg: float = 0.0) -> list[float]:
    """A point `metres` from the bot, `turn_deg` to the right of where its body faces (Unity yaw)."""
    yaw = math.radians(float(state["yaw"]) + turn_deg)
    x, y, z = state["pos"]
    return [x + metres * math.sin(yaw), y, z + metres * math.cos(yaw)]


async def run_actions(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    """E1: the new body actions in the real game: crafting menus, shooting a bow, building with the hammer,
    using an item on a building, dropping toward the leader. Every step checks a world change."""
    setup = Setup(
        "actions",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        inventory_fixtures="Wood:40,Stone:20,Bow:1,ArrowWood:30,RawMeat:2",
        # 활을 시험할 멧돼지. 봇은 하네스가 고른 평평한 방향(앞)을 보고 선다.
        world_fixtures="Boar@16,0",
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        names = {p["prefab"]: p.get("name") for p in placed if p["where"] == "inventory"}
        boar_id = next(p["id"] for p in placed if p["prefab"] == "Boar")
        built: dict[str, str] = {}
        built_at: dict[str, list[float]] = {}

        async def act(op: str, args: dict[str, Any], codes: set[str], timeout: float = 30) -> dict[str, Any]:
            return _expect(await s.command(op, args, timeout=timeout), codes)

        async def menu(what: str) -> list[dict[str, Any]]:
            answer = await s.query(what, {})
            if not answer.ok:
                raise StepFailed(f"query {what}: {answer.error}")
            entries: list[dict[str, Any]] = answer.data[what]
            return entries

        recipes: list[dict[str, Any]] = []

        async def crafting_menu() -> dict[str, Any]:
            recipes.extend(await menu("recipes"))
            by_hand = [r["name"] for r in recipes if r["station"] is None]
            if not by_hand:
                raise StepFailed(f"no hand recipes known: {recipes}")
            return {"known": len(recipes), "by_hand": by_hand}

        await run.step("crafting_menu_shows_known_recipes", crafting_menu)

        async def shoot() -> dict[str, Any]:
            await act("equip", {"item": names["Bow"]}, {"equipped", "already_equipped"})
            shots: list[dict[str, Any]] = []
            for _ in range(10):
                result = await s.command("shoot", {"id": boar_id}, timeout=20)
                shots.append({"code": result.code, **result.evidence})
                if result.code == "hit":
                    return {"shots": shots}
                if result.code in ("no_line_of_sight", "out_of_range"):
                    # 덤불·바위에 가리면 사람처럼 자리를 옮겨 다시 겨눈다(사냥 스킬도 같다).
                    closer = {"target": {"id": boar_id}, "arrive_radius": 9.0, "timeout_s": 10}
                    await s.command("move_to", closer, timeout=20)
                    continue
                if result.status == "preempted":
                    # 멧돼지가 덤벼 반사가 끼어들었다. 맞혔는지는 멧돼지 체력(이름표에 보이는 것)으로 본다.
                    boar = next((e for e in s.nearby() if e["id"] == boar_id), None)
                    if boar is None or float(boar.get("health", 1.0)) < 1.0:
                        return {"shots": shots, "boar_health": boar.get("health") if boar else 0}
                    continue
                if result.status != "succeeded":
                    raise StepFailed(f"shoot {result.status}/{result.code}: {shots}")
            raise StepFailed(f"no hit in 10 tries: {shots}")

        hammer = {"name": ""}

        async def craft_hammer() -> dict[str, Any]:
            # 망치는 맨손으로 만드는 레시피 가운데 건축 도구(Tool)다. 이름은 게임 언어를 따른다.
            tools = [
                r for r in recipes if r["station"] is None and r["type"] == "Tool" and r["have_materials"]
            ]
            if not tools:
                raise StepFailed(f"no hand-craftable tool: {recipes}")
            for tool in tools:
                result = await s.command("craft", {"item": tool["name"]}, timeout=20)
                if result.code != "crafted":
                    raise StepFailed(f"craft {tool['name']}: {result.status}/{result.code} {result.evidence}")
                if any(p["tool"] == tool["name"] for p in await menu("pieces")):
                    hammer["name"] = tool["name"]
                    return {"crafted": tool["name"], **result.evidence}
            raise StepFailed(f"crafted {[t['name'] for t in tools]} but none opened a build menu")

        await run.step("craft_hammer_by_hand", craft_hammer)

        pieces: list[dict[str, Any]] = []

        def piece_with(resources: dict[str, int]) -> str:
            for piece in pieces:
                if {r["name"]: r["amount"] for r in piece["resources"]} == resources:
                    return str(piece["name"])
            raise StepFailed(f"no known piece made of {resources}: {pieces}")

        async def build(resources: dict[str, int], turn_deg: float, key: str) -> dict[str, Any]:
            if not pieces:
                pieces.extend(await menu("pieces"))
            name = piece_with(resources)
            await act("equip", {"item": hammer["name"]}, {"equipped", "already_equipped"})
            assert s.state is not None
            # 사람처럼 놓을 수 있는 자리를 찾을 때까지 둘레를 돌아가며 겨눠 본다(짓기 스킬도 같다).
            tries: list[dict[str, Any]] = []
            for turn in (turn_deg, turn_deg + 45, turn_deg - 45, turn_deg + 90, turn_deg + 180):
                point = _ahead(s.state.data, 3.0, turn)
                result = await s.command("place", {"piece": name, "pos": point, "yaw": 0}, timeout=20)
                if result.code == "placed":
                    built[key] = result.evidence["id"]
                    built_at[key] = result.evidence["pos"]
                    return {"code": result.code, "tries": tries, **result.evidence}
                tries.append({"turn": turn, "code": result.code, **result.evidence})
            raise StepFailed(f"no spot accepted {name}: {tries}")

        wood, stone = names["Wood"], names["Stone"]
        await run.step("place_workbench", lambda: build({wood: 10}, -90, "workbench"))

        async def workbench_needs_a_roof() -> dict[str, Any]:
            # 지붕 없는 작업대는 쓸 수 없다. 사람처럼 열어 보고, 게임이 띄운 이유를 듣는다.
            # 작업대 레시피는 작업대 곁(4m)에 가서 작업대를 알게 된 뒤에야 메뉴에 나온다.
            # 제작대는 몸통 중심(루트)에서 2m 안이어야 열린다(CraftingStation.InUseDistance).
            await s.command(
                "move_to", {"target": {"pos": built_at["workbench"]}, "arrive_radius": 1.3}, timeout=30
            )
            recipes[:] = await menu("recipes")
            at_bench = [r for r in recipes if r["station"] and r["have_materials"]]
            if not at_bench:
                raise StepFailed(f"no workbench recipe with materials: {recipes}")
            messages = len(s.events_of("game_message"))
            result = await s.command(
                "craft", {"item": at_bench[0]["name"], "station_id": built["workbench"]}, timeout=20
            )
            if result.code != "station_unusable":
                raise StepFailed(f"expected station_unusable, got {result.status}/{result.code}")
            await s.wait_for(lambda: len(s.events_of("game_message")) > messages, 5)
            said = [e.data["text"] for e in s.events_of("game_message")[messages:]]
            return {"code": result.code, "game_said": said}

        await run.step("workbench_without_roof_is_refused", workbench_needs_a_roof)
        await run.step("place_campfire", lambda: build({stone: 5, wood: 2}, 90, "campfire"))
        await run.step(
            "fuel_campfire",
            lambda: act("use_item", {"item": wood, "id": built["campfire"]}, {"used"}),
        )

        async def hand_over() -> dict[str, Any]:
            assert s.scene is not None
            leader = s.scene.data.get("leader")
            if not leader:
                raise StepFailed("leader not in scene")
            return await act("drop", {"item": wood, "count": 3, "toward": {"id": leader["id"]}}, {"dropped"})

        await run.step("drop_wood_toward_leader", hand_over)

        async def pace(run_flag: bool) -> dict[str, Any]:
            # 걷기·달리기 속도를 잰다(멀리 따라가기가 초당 1~2m로 느렸다). 0.5초마다 위치와 몸 상태를 남긴다.
            assert s.state is not None
            start = list(s.state.data["pos"])
            goal = _ahead(s.state.data, 40.0, 180.0)
            samples: list[dict[str, Any]] = []

            async def sample() -> None:
                while True:
                    state = s.state.data if s.state else {}
                    samples.append(
                        {
                            "pos": [round(v, 1) for v in state.get("pos", [])],
                            "speed": round(math.hypot(state["vel"][0], state["vel"][2]), 1),
                            "run": state.get("running"),
                            "stamina": round(float(state.get("stamina", 0))),
                            "phase": (state.get("action") or {}).get("phase"),
                        }
                    )
                    await asyncio.sleep(0.5)

            sampler = asyncio.create_task(sample())
            began = time.monotonic()
            try:
                result = await s.command(
                    "move_to", {"target": {"pos": goal}, "arrive_radius": 2.0, "run": run_flag}, timeout=70
                )
            finally:
                sampler.cancel()
            seconds = time.monotonic() - began
            assert s.state is not None
            moved = distance_m(start, s.state.data["pos"])
            return {
                "code": result.code,
                "motor": {
                    k: result.evidence.get(k)
                    for k in ("frames", "stuck_frames", "detour_frames", "unstucks", "blockers", "motion")
                },
                "metres": round(moved, 1),
                "seconds": round(seconds, 1),
                "m_per_s": round(moved / max(0.1, seconds), 2),
                "samples": samples[::2],
            }

        await run.step("walk_40m", lambda: pace(False))
        await run.step("run_40m", lambda: pace(True))
        # 활은 마지막에 시험한다. 맞은 멧돼지는 덤벼서 반사(self_defense)가 몸을 잡는다.
        await run.step("shoot_boar_with_bow", shoot)
    return run.report


async def run_shelter(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    """E3: put a roof over a workbench the way a player builds, until the game lets it be used.
    Plan (bench 3 m wide x 1.1 m deep, yaw 0): two back walls, two side walls, two roof floors aimed at the
    inside face of the back wall (the game then sets them inside and snaps them to the wall tops), and two
    porch floors in front. The station's cover is read after every piece."""
    setup = Setup(
        "shelter",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        inventory_fixtures="Wood:80,Stone:20,Hammer:1",
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        names = {p["prefab"]: p.get("name") for p in placed if p["where"] == "inventory"}
        await s.command("equip", {"item": names["Hammer"]}, timeout=10)
        wood = names["Wood"]
        state: dict[str, Any] = {"log": []}

        async def pieces() -> dict[str, str]:
            listed = (await s.query("pieces", {})).data["pieces"]
            return {p["name"]: p["name"] for p in listed}

        async def put(
            piece: str, aim: list[float], stand: list[float], exact: bool, yaw: float = 0
        ) -> dict[str, Any]:
            await s.command("move_to", {"target": {"pos": stand}, "arrive_radius": 0.8}, timeout=20)
            args = {"piece": piece, "pos": aim, "yaw": yaw, "exact": exact}
            result = await s.command("place", args, timeout=20)
            entry = {"piece": piece, "code": result.code, **result.evidence}
            if "bench_id" in state:
                entry["cover"] = (await s.query("cover", {"id": state["bench_id"]})).data
            state["log"].append(entry)
            return entry

        async def bench() -> dict[str, Any]:
            assert s.state is not None
            spot = _ahead(s.state.data, 4.0)
            menu = await pieces()
            name = next(n for n in menu if n == "작업대")
            result = await put(name, spot, s.state.data["pos"], exact=False)
            if result["code"] != "placed":
                raise StepFailed(f"workbench: {result}")
            state["bench_id"], state["bench"] = result["id"], result["pos"]
            return result

        await run.step("workbench", bench)

        async def walls() -> dict[str, Any]:
            x, y, z = state["bench"]
            wall = "나무 벽"
            if wall not in await pieces():
                raise StepFailed(f"no {wall} in the hammer menu")
            # 겨누는 광선이 작업대에 먼저 맞지 않게, 짓는 벽 바깥쪽에 서서 겨눈다(사람도 돌아가서 짓는다).
            for dx, dz, yaw, sx, sz in (
                (-1.0, 1.0, 0.0, -1.0, 4.0),
                (1.0, 1.0, 0.0, 1.0, 4.0),
                (-2.0, 0.0, 90.0, -5.0, 0.0),
                (2.0, 0.0, 90.0, 5.0, 0.0),
            ):
                await put(wall, [x + dx, y, z + dz], [x + sx, y, z + sz], exact=False, yaw=yaw)
            return {"log": state["log"][-4:]}

        await run.step("walls", walls)

        async def roof() -> dict[str, Any]:
            x, y, z = state["bench"]
            # 바닥판은 "새는(leaky)" 조각이라 지붕으로 치지 않는다. 지붕은 지붕 조각(초가지붕)으로 덮는다.
            roof_piece = "초가지붕 26°"
            # 뒷벽(작업대보다 뒤, z가 큰 쪽) 꼭대기 높이. 옆벽은 비탈에 밀려 높이가 다를 수 있다.
            backs = [
                e["pos"]
                for e in state["log"]
                if e.get("piece") == "나무 벽" and e["code"] == "placed" and e["pos"][2] > z + 0.5
            ]
            if not backs:
                raise StepFailed(f"no back wall stands: {state['log']}")
            top = min(p[1] for p in backs) + 1.0
            stand = [x, y, z - 3.0]
            for dx, yaw in ((-1.0, 0.0), (1.0, 180.0)):
                await put(roof_piece, [x + dx, top - 0.25, z + 1.0 - 0.16], stand, exact=True, yaw=yaw)
            usable = state["log"][-1].get("cover", {}).get("usable")
            if not usable:
                # 앞쪽: 지붕 조각 아래 앞면을 겨눠 한 칸 더 낸다.
                for dx in (-1.0, 1.0):
                    await put(roof_piece, [x + dx, top + 0.3, z - 1.0], [x, y, z - 5.0], exact=True, yaw=0.0)
            final = (await s.query("cover", {"id": state["bench_id"]})).data
            if not final.get("usable"):
                raise StepFailed(f"workbench still unusable: {final}; log {state['log']}")
            return {"cover": final, "log": state["log"][-4:]}

        await run.step("roof", roof)

        async def use_it() -> dict[str, Any]:
            await s.command("move_to", {"target": {"pos": state["bench"]}, "arrive_radius": 1.3}, timeout=20)
            recipes = (await s.query("recipes", {})).data["recipes"]
            arrows = next((r for r in recipes if r["station"] and r["have_materials"]), None)
            if arrows is None:
                raise StepFailed(f"nothing to craft at the bench: {recipes}")
            result = await s.command(
                "craft", {"item": arrows["name"], "station_id": state["bench_id"]}, timeout=30
            )
            if result.code != "crafted":
                raise StepFailed(f"craft at bench: {result.status}/{result.code} {result.evidence}")
            return {"code": result.code, **result.evidence}

        await run.step("craft_at_roofed_bench", use_it)
        _ = wood
    return run.report


async def run_skills(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    """E3: the brain's own skills in the real game, through the same controller `thorkell play` uses
    (no model): roof the workbench, craft arrows there, hunt a boar with the bow, cook its meat."""
    setup = Setup(
        "skills",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        inventory_fixtures="Wood:60,Stone:20,Hammer:1,Bow:1,Club:1,RawMeat:2,Raspberry:5",
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        names = {p["prefab"]: p.get("name") for p in placed if p["where"] == "inventory"}
        mind = Mind(Store(run.run_dir / "knowledge.sqlite"), leader_name=LEADER)
        controller = Controller(s, leader_name=LEADER, mind=mind)
        controller.stance = "wait"
        stop = asyncio.Event()
        task = asyncio.create_task(controller.run(stop))

        def held(name: str | None) -> int:
            return sum(int(i.get("stack", 0)) for i in s.inventory() if i.get("name") == name)

        goal = _goal_runner(controller)

        try:
            await run.step("shelter_workbench", lambda: goal("shelter", {}, 240))

            async def arrows() -> dict[str, Any]:
                result = await goal("craft", {"item": "나무 화살", "count": 1}, 120)
                if held("나무 화살") < 20:
                    raise StepFailed(f"no arrows in the bag: {s.inventory()}")
                return {**result, "arrows": held("나무 화살")}

            await run.step("craft_arrows_at_the_bench", arrows)

            async def hunt() -> dict[str, Any]:
                # 시작 때 놓은 멧돼지는 쉼터를 짓는 동안 멀리 가 버린다. 사냥 직전에 앞 20m에 내보낸다.
                await LeaderCues(run.host).do({"spawn": "Boar", "near_bot": [20, 3]})
                meat_before = held(names["RawMeat"])
                result = await goal("hunt", {"creature": "멧돼지", "count": 1}, 240)
                return {**result, "meat": held(names["RawMeat"]) - meat_before}

            await run.step("hunt_boar", hunt)

            async def cook() -> dict[str, Any]:
                raw = held(names["RawMeat"])
                result = await goal("cook", {"item": names["RawMeat"], "count": min(2, raw)}, 240)
                return {**result, "inventory": [(i["name"], i["stack"]) for i in s.inventory()]}

            await run.step("cook_meat", cook)
        finally:
            stop.set()
            await asyncio.gather(task, return_exceptions=True)
            run.extra["decisions"] = [f"{d.kind}: {d.reason_ko}" for d in controller.decisions][-80:]
    return run.report


def _goal_runner(controller: Controller) -> Callable[[str, dict[str, Any], float], Awaitable[dict[str, Any]]]:
    """Asks the controller for a goal the way the leader's words would, waits for it to end and returns what
    Thorkell decided, said and gathered as evidence. A failed goal fails the step."""

    async def goal(kind: str, args: dict[str, Any], timeout: float) -> dict[str, Any]:
        before = len(controller.decisions)
        asked = Goal(kind, Tier.USER, args, source="leader")
        controller.request(asked)
        began = time.monotonic()
        while time.monotonic() - began < timeout:
            ended = [
                d for d in controller.decisions[before:] if d.kind in ("done", "fail") and d.goal_kind == kind
            ]
            if ended:
                said = [d.reason_ko for d in controller.decisions[before:] if d.kind == "speak"]
                finished = next((g for g in controller.finished if g.id == ended[0].goal_id), None)
                result = {
                    "decision": ended[0].kind,
                    "reason": ended[0].reason_ko,
                    "said": said[-6:],
                    "evidence": finished.progress.get("evidence") if finished else None,
                }
                if ended[0].kind != "done":
                    raise StepFailed(f"{kind}: {result}")
                return result
            await asyncio.sleep(0.5)
        progress = {k: v for k, v in asked.progress.items() if k not in ("children", "past_children")}
        raise StepFailed(
            f"{kind} did not finish in {timeout}s ({asked.status}); "
            f"current {controller.current()}; {progress}"
        )

    return goal


async def run_boss(
    game: Path,
    backend: str,
    timeout_s: int,
    config_path: Path | None = None,
    mind_path: Path | None = None,
    together: bool = False,
    record: bool = False,
    mortal_leader: bool = False,
) -> dict[str, Any]:
    """E5: the first boss in the real game. The leader stands near the Eikthyr altar (test-only move);
    Thorkell has two deer trophies, food and a bow and offers the trophies. Nobody tells him to fight: he
    notices what comes out, thinks what it is and how to fight it (the model in `config_path`, with what he
    remembers), fights, and thinks the fight over. `mind_path` keeps his memory across runs, so a second run
    is a second attempt by the same Thorkell. The server's 'defeated_eikthyr' key confirms a kill
    independently of what the brain believes. `together`: the leader says it will hold the boss and stays by
    it bare-handed (test-only god mode), like a person fighting in front; otherwise Thorkell fights alone.
    `mortal_leader` (with `together`): the leader has eaten and swings a club without god mode, so it can die
    like a person holding the boss; whether and when it died is in the report."""
    from thorkell.ops import play  # play imports this module

    if config_path is None:
        raise ScenarioError("boss: --config가 필요합니다(싸움 판단과 회고는 모델이 한다)")
    planner = _planner_from(config_path)
    tactician = Tactician(planner.model, planner.config)
    language = _language(config_path)
    eikthyr = tr("에이크쉬르", "Eikthyr")
    setup = Setup(
        "boss",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        inventory_fixtures="Bow:1,ArrowWood:100,TrophyDeer:2,CookedMeat:6,Raspberry:10,Mushroom:10,Club:1",
        leader_offset="location:Eikthyrnir:22:32",
        locations="Eikthyrnir",
        bot_offset="3,2",
        language=language,
        record=record,
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        names = {p["prefab"]: p.get("name") for p in placed if p["where"] == "inventory"}
        mind = Mind(Store(mind_path or run.run_dir / "knowledge.sqlite"), leader_name=LEADER)
        run.extra["lessons_before"] = [lesson.line() for lesson in mind.store.lessons()]
        controller = Controller(
            s, leader_name=LEADER, planner=planner, mind=mind, tactician=tactician, leader_chat_via_host=True
        )
        controller.stance = "wait"
        stop = asyncio.Event()

        async def relay() -> None:
            # 리더(하네스)가 게임 채팅으로 한 말은 실전처럼 호스트를 거쳐 들어온다.
            tail = play.LeaderChatTail(run.host.root / play.LEADER_CHAT)
            while not stop.is_set():
                for said in tail.read():
                    text = str(said.get("text", "")).strip()
                    if said.get("from") == LEADER and text:
                        await controller.hear_leader(text)
                await asyncio.sleep(0.2)

        task = asyncio.create_task(controller.run(stop))
        relaying = asyncio.create_task(relay())
        goal = _goal_runner(controller)
        cues = LeaderCues(run.host, run.note_said)
        try:

            async def altar() -> dict[str, Any]:
                # 사람은 베그비시르가 지도에 찍어 준 곳으로 걸어간다. 여기서는 그 자리(제단 가운데)를 준다.
                where = run.read_host("host-ready.json")
                if not s.nearby("altar") and where is not None and where.get("location"):
                    await s.command(
                        "move_to",
                        {"target": {"pos": where["location"]}, "arrive_radius": 8.0, "timeout_s": 60},
                        timeout=70,
                    )
                await s.wait_for(lambda: bool(s.nearby("altar")), 30)
                seen = s.nearby("altar")[0]
                return {
                    "altar": seen["name"],
                    "distance": seen["distance"],
                    "host": run.read_host("host-ready.json"),
                }

            seen = await run.step("altar_in_view", altar)
            run.extra["altar"] = seen

            async def offer() -> dict[str, Any]:
                # 리더(하네스)는 싸우지 않는다. 보스가 리더를 쫓지 않게 제단 반대쪽으로 40m 물러난다
                # (시험 전용 이동).
                leader = s.scene.data.get("leader") if s.scene else None
                where = s.nearby("altar")[0]["pos"]
                if leader is not None:
                    dx, dz = leader["pos"][0] - where[0], leader["pos"][2] - where[2]
                    length = math.hypot(dx, dz) or 1.0
                    await cues.do({"move": [dx / length * 40, dz / length * 40]})
                # 사람이라면 말로 알린다. 토르켈은 이 말을 듣고(기억에 남는다) 싸움을 판단할 때 떠올린다.
                # 듣고 스스로 제단에 바칠 수도 있다(플래너). 그러면 다시 시키지 않는다.
                answered = len(controller.decisions)
                if together:
                    await cues.do({"say": tr(LEADER_HOLDS, LEADER_HOLDS_EN)})
                else:
                    await cues.do({"say": tr(LEADER_WATCHES, LEADER_WATCHES_EN)})

                def offered() -> bool:
                    return not any(i["name"] == names["TrophyDeer"] for i in s.inventory())

                def replied() -> bool:
                    # 답(말)이나 부탁의 끝. 계획 끝이 "따라가기"면 부탁은 끝나지 않는다(실게임 2026-10-20).
                    return offered() or any(
                        d.kind == "speak" or (d.goal_kind == "request" and d.kind in ("done", "fail"))
                        for d in controller.decisions[answered:]
                    )

                await s.wait_for(replied, 120)
                if not offered():
                    # 사람 리더라면 이제 불러내자고 말한다. 토르켈이 듣고 스스로 바치는지 본다.
                    await cues.do({"say": tr(LEADER_SUMMONS, LEADER_SUMMONS_EN)})
                    with contextlib.suppress(TimeoutError):
                        await s.wait_for(offered, 120)
                if offered():
                    told = [f"{d.kind}: {d.reason_ko}" for d in controller.decisions[answered:]]
                    offered_by: dict[str, Any] = {"offered_by": "Thorkell's own plan", "decisions": told}
                else:
                    offered_by = await goal("offer", {"item": names["TrophyDeer"]}, 120)
                if together:
                    # 시험 전용: 사람이 앞에서 막듯 리더가 보스 곁에 붙는다(맨손이라 혼자서는 못 잡는다).
                    holds: dict[str, Any] = {"fight": "Eikthyr"}
                    if mortal_leader:
                        holds |= {"mortal": True, "weapon": "Club", "eat": MORTAL_LEADER_FOOD}
                    offered_by["leader"] = (await cues.do(holds))["detail"]
                return offered_by

            await run.step("offer_trophies", offer)

            async def fight_and_reflect() -> dict[str, Any]:
                # 싸우라고 시키지 않는다. 알아채고 생각해서 싸우고, 끝나면(이김·놓침·죽음) 돌아본다.
                before = len(mind.store.episodes(eikthyr, limit=1000))
                decided = len(controller.decisions)

                deaths = len(s.events_of("death"))

                def recorded() -> bool:
                    return len(mind.store.episodes(eikthyr, limit=1000)) > before

                def fight_over() -> bool:
                    ended = any(
                        d.goal_kind == "fight" and d.kind in ("done", "fail")
                        for d in controller.decisions[decided:]
                    )
                    # 계획 속 싸움은 싸움 목표의 결정을 남기지 않는다. 죽음은 어느 싸움이든 끝이다.
                    return recorded() or ended or len(s.events_of("death")) > deaths

                await s.wait_for(fight_over, 900)
                with contextlib.suppress(TimeoutError):
                    await s.wait_for(recorded, 10)
                if not recorded():
                    ended = [d.reason_ko for d in controller.decisions[decided:] if d.goal_kind == "fight"]
                    raise StepFailed(
                        f"the fight ended before Thorkell had decided how to fight: {ended[-3:]}"
                    )
                await s.wait_for(lambda: controller._reflection is None, 120)
                episode = mind.store.episodes(eikthyr, limit=1)[-1]
                thought = [d.reason_ko for d in controller.decisions if d.kind == "reflect"]
                return {
                    "outcome": episode.outcome,
                    "episode": episode.id,
                    "tactic": episode.record.get("tactic"),
                    "hits": episode.record.get("hits"),
                    "shots": episode.record.get("shots"),
                    "boss_health": episode.record.get("health", [])[-1:],
                    "reflection": thought[-1] if thought else None,
                }

            fought = await run.step("fight_and_reflect", fight_and_reflect)
            run.extra["fight"] = fought

            async def defeated() -> dict[str, Any]:
                killed = await cues.do({"global_key": "defeated_eikthyr"})
                if killed["detail"] != "set":
                    raise StepFailed(f"Eikthyr is alive (Thorkell's fight ended: {fought['outcome']})")
                return {"inventory": [(i["name"], i["stack"]) for i in s.inventory()]}

            await run.step("eikthyr_defeated", defeated)
        finally:
            stop.set()
            await asyncio.gather(task, relaying, return_exceptions=True)
            run.extra["decisions"] = [f"{d.kind}: {d.reason_ko}" for d in controller.decisions][-120:]
            run.note_thorkell(controller)
            run.extra["lessons_after"] = [lesson.line() for lesson in mind.store.lessons()]
            run.extra["model_calls"] = [
                {"input": u.input_tokens, "output": u.output_tokens} for u in tactician.usage
            ]
            run.extra["planner_calls"] = len(planner.usage)
            if mortal_leader:
                events = run.host.root / "leader-events.jsonl"
                run.extra["leader_died"] = [
                    json.loads(line) for line in (events.read_text().splitlines() if events.is_file() else [])
                ]
    return run.report


class LeaderCues:
    """Tells the harness leader (the human's stand-in) what to do; it acts in the game the way a person would
    (types in chat, toggles map sharing). Moves are test-only teleports. See Harness.Cues.cs."""

    def __init__(self, host: runtime.Runtime, on_say: Callable[[str, str], None] | None = None) -> None:
        self.cues = host.root / "leader-cue.jsonl"
        self.done = host.root / "leader-cue-done.jsonl"
        # 같은 실행에서 먼저 보낸 신호(녹화 전 아침 넘기기)와 번호가 겹치지 않게 이어서 매긴다.
        self.next_id = len(self.cues.read_text().splitlines()) if self.cues.is_file() else 0
        self.on_say = on_say

    async def do(self, cue: dict[str, Any], timeout: float = 40) -> dict[str, Any]:
        if self.on_say is not None and "say" in cue:
            self.on_say(LEADER, str(cue["say"]))
        self.next_id += 1
        cue_id = self.next_id
        with self.cues.open("a") as out:
            out.write(json.dumps({"id": cue_id, **cue}, ensure_ascii=False) + "\n")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in self.done.read_text().splitlines() if self.done.is_file() else []:
                done: dict[str, Any] = json.loads(line)
                if done["id"] != cue_id:
                    continue
                if not done["ok"]:
                    raise StepFailed(f"leader could not {cue}: {done['detail']}")
                return done
            await asyncio.sleep(0.2)
        raise StepFailed(f"leader cue {cue} not done in {timeout}s")


CHAT_LINE = re.compile(r"^<color=orange>(?P<name>.*?)</color>: <color=#[0-9A-Fa-f]+>(?P<text>.*)</color>$")


def host_chat(host: runtime.Runtime) -> list[tuple[str, str]]:
    """(name, text) of each line in the human's chat window, as the harness mirrored it."""
    path = host.root / "host-chat.jsonl"
    lines = [json.loads(line)["line"] for line in path.read_text().splitlines()] if path.is_file() else []
    return [(m["name"], m["text"]) for line in lines if (m := CHAT_LINE.match(line)) is not None]


def misnamed_after_arrival(lines: list[tuple[str, str]], leader: str, bot: str) -> list[str]:
    """Lines under the leader's name before the leader has said anything: Thorkell's words shown under the
    wrong name. The very first line is the leader's own arrival shout (the host spawns before the bot joins),
    so it is the leader's and does not count."""
    if lines and lines[0][0] == leader:
        lines = lines[1:]
    return [text for who, text in lines if who == leader]


async def run_sight(
    game: Path, backend: str, timeout_s: int, config_path: Path | None = None
) -> dict[str, Any]:
    """Thorkell's eyes in the real game (2026-10-18): the body renders what his camera sees (`look`) and the
    vision model says what is there. Things the old object list missed stand in front of him: a portal, a
    sign, a cart. Measures how long a frame and a reading take; the frames are kept in the report folder."""
    if config_path is None:
        raise ScenarioError("sight: --config가 필요합니다(화면을 이해하는 모델)")
    config = load(config_path)
    if config.vision.backend != "gemini":
        raise ScenarioError(f"{config_path}: vision.backend must be gemini, not {config.vision.backend!r}")
    setup = Setup(
        "sight",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        world_fixtures="portal_wood@7,0;sign@6,3;Cart@9,-3;Boar@16,2",
        language=_language(config_path),
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        eyes = Eyes(s, GeminiJson(secret("GEMINI_API_KEY")), config.vision)

        async def named() -> dict[str, Any]:
            # 예전 목록에 없던 것(포탈·표지판·수레)도 이름이 뜨면 장면에 들어와야 한다.
            await s.wait_for(lambda: len(s.nearby("thing")) >= 2, 30)
            return {"things": [(e["name"], round(e["distance"], 1)) for e in s.nearby("thing")]}

        run.extra["named"] = await run.step("named_things_in_scene", named)

        async def frames() -> dict[str, Any]:
            run.artifacts.mkdir(parents=True, exist_ok=True)
            began = time.monotonic()
            frame = await s.query("look", {"turn": [0, 90, 180, -90]}, timeout=10)
            if not frame.ok or frame.data is None:
                raise StepFailed(f"look failed: {frame.error}")
            sizes = []
            for index, picture in enumerate(frame.data["frames"]):
                jpeg = base64.b64decode(picture["jpeg"])
                sizes.append(len(jpeg))
                (run.artifacts / f"around-{index}.jpg").write_bytes(jpeg)
            return {
                "round_trip_s": round(time.monotonic() - began, 3),
                "render_ms": frame.data["ms"],
                "bytes": sizes,
                "yaws": [p["yaw"] for p in frame.data["frames"]],
            }

        run.extra["frames"] = await run.step("frames", frames)

        async def see() -> dict[str, Any]:
            around = await eyes.look(around=True)
            portal = next(e for e in s.nearby("thing") if e["name"] != tr("표지판", "Sign"))
            toward = await eyes.look(
                tr("저 돌 테두리 같은 건 뭐야?", "What's that stone frame thing?"), toward=list(portal["pos"])
            )
            frame = await s.query("look", {"toward": list(portal["pos"])}, timeout=5)
            if frame.ok and frame.data is not None:
                (run.artifacts / "toward-portal.jpg").write_bytes(
                    base64.b64decode(frame.data["frames"][0]["jpeg"])
                )
            return {
                "seeing_s": [around.seeing_s, toward.seeing_s],
                "around": around.lines(),
                "toward_portal": toward.lines(),
                "tokens": [(u.input_tokens, u.output_tokens) for u in eyes.usage],
            }

        run.extra["seen"] = await run.step("see", see)
    return run.report


async def run_fresh(
    game: Path, backend: str, timeout_s: int, config_path: Path | None = None, record: bool = False
) -> dict[str, Any]:
    """The first minutes of a new world together (2026-10-18: the user will play from the beginning to the
    first boss). Thorkell starts with nothing; the leader (harness) asks the way a person would and only
    talks. Real planner, eyes and memory, as in `thorkell play`."""
    from thorkell.ops import play  # play imports this module

    if config_path is None:
        raise ScenarioError("fresh: --config가 필요합니다(부탁을 판단하는 모델)")
    config = load(config_path)
    planner = _planner_from(config_path)
    setup = Setup(
        "fresh",
        backend=backend,
        timeout_s=timeout_s,
        bridge=True,
        language=_language(config_path),
        record=record,
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        play.log_to_file(run.run_dir)
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        mind = Mind(Store(run.run_dir / "knowledge.sqlite"), leader_name=LEADER)
        eyes = (
            Eyes(s, GeminiJson(secret("GEMINI_API_KEY")), config.vision)
            if config.vision.backend == "gemini"
            else None
        )
        controller = Controller(
            s,
            leader_name=LEADER,
            planner=planner,
            mind=mind,
            tactician=Tactician(planner.model, planner.config),
            eyes=eyes,
            leader_chat_via_host=True,
        )
        controller.stance = "follow"
        stop = asyncio.Event()

        async def relay() -> None:
            tail = play.LeaderChatTail(run.host.root / play.LEADER_CHAT)
            while not stop.is_set():
                for said in tail.read():
                    text = str(said.get("text", "")).strip()
                    if said.get("from") == LEADER and text:
                        await controller.hear_leader(text)
                await asyncio.sleep(0.2)

        task = asyncio.create_task(controller.run(stop))
        relaying = asyncio.create_task(relay())
        cues = LeaderCues(run.host, run.note_said)

        def held(word: str) -> int:
            return sum(int(i.get("stack", 0)) for i in s.inventory() if word in str(i.get("name", "")))

        def said_since(start: int) -> list[str]:
            return [d.reason_ko for d in controller.decisions[start:] if d.kind == "speak"]

        try:

            async def axe() -> dict[str, Any]:
                start = len(controller.decisions)
                await cues.do(
                    {
                        "say": tr(
                            "토르켈, 도끼부터 만들어 볼래? 나무랑 돌은 주변에서 주우면 돼",
                            "Thorkell, could you make us an axe first? There's wood and stone lying around",
                        )
                    }
                )
                await s.wait_for(lambda: held(tr("도끼", "Axe")) > 0, 600)
                return {
                    "inventory": [(i["name"], i["stack"]) for i in s.inventory()],
                    "said": said_since(start),
                }

            run.extra["axe"] = await run.step("makes_an_axe_from_nothing", axe)

            async def wood() -> dict[str, Any]:
                wood, axe = tr("나무", "Wood"), tr("도끼", "Axe")
                start, before, axes = len(controller.decisions), held(wood), held(axe)

                def chopped() -> int:
                    # 하다가 도끼가 부러져 새로 만들었으면(돌도끼에 나무 5개) 그 나무도 해 온 것이다.
                    return held(wood) - before + 5 * max(0, held(axe) - axes)

                await cues.do({"say": tr("나무 20개만 해줘", "Can you chop 20 wood for me?")})
                await s.wait_for(lambda: chopped() >= 20, 900)
                return {
                    "wood": held(wood),
                    "chopped": chopped(),
                    "axes": held(axe),
                    "said": said_since(start),
                }

            run.extra["wood"] = await run.step("cuts_twenty_wood", wood)

            async def house() -> dict[str, Any]:
                start = len(controller.decisions)
                await cues.do({"say": tr("집을 지어야겠어", "We should build a house")})
                await s.wait_for(lambda: len(said_since(start)) > 0, 90)
                await asyncio.sleep(20)
                return {"said": said_since(start)}

            run.extra["house"] = await run.step("answers_about_a_house", house)

            def built(kind: str) -> list[Goal]:
                # 부탁(계획)의 하위 목표 중 끝난 것: 지난 계획 것까지.
                requests = [g for g in controller.finished if g.kind == "request"]
                if controller.active is not None and controller.active.goal.kind == "request":
                    requests.append(controller.active.goal)
                children = [
                    c
                    for r in requests
                    for c in [*r.progress.get("past_children", []), *r.progress.get("children", {}).values()]
                ]
                return [c for c in children if c.kind == kind and c.status == "done"]

            async def shelter() -> dict[str, Any]:
                start = len(controller.decisions)
                await cues.do(
                    {
                        "say": tr(
                            "응, 작게 지어 줘. 비만 피하면 돼",
                            "Yeah, keep it small. Just enough to keep the rain off",
                        )
                    }
                )
                await s.wait_for(lambda: bool(built("shelter")), 900)
                stations = [e["name"] for e in s.nearby("station")]
                return {"stations": stations, "said": said_since(start)}

            run.extra["shelter"] = await run.step("builds_a_small_shelter", shelter)

            def food() -> int:
                eaten = len(s.scene.data.get("foods", [])) if s.scene else 0
                return eaten + sum(
                    int(i.get("stack", 0)) for i in s.inventory() if i.get("type") == "Consumable"
                )

            async def eats() -> dict[str, Any]:
                start, before = len(controller.decisions), food()
                await cues.do(
                    {
                        "say": tr(
                            "배고프다. 먹을 거 좀 구해 와", "I'm hungry. Can you find us something to eat?"
                        )
                    }
                )
                await s.wait_for(lambda: food() > before, 600)
                return {"food": food(), "said": said_since(start)}

            run.extra["food"] = await run.step("finds_something_to_eat", eats)

            async def deer() -> dict[str, Any]:
                start = len(controller.decisions)
                await cues.do(
                    {"say": tr("사슴 좀 잡아 와. 트로피가 필요해", "Go hunt a deer. We need its trophy")}
                )
                trophy = tr("트로피", "Trophy")
                await s.wait_for(lambda: held(trophy) > 0, 900)
                return {"trophies": held(trophy), "said": said_since(start)}

            run.extra["deer"] = await run.step("hunts_a_deer_for_its_trophy", deer)
        finally:
            stop.set()
            await asyncio.gather(task, relaying, return_exceptions=True)
            run.extra["decisions"] = [f"{d.kind}: {d.reason_ko}" for d in controller.decisions][-150:]
            run.note_thorkell(controller)
            run.extra["planner_calls"] = len(planner.usage)
            run.extra["eyes_calls"] = len(eyes.usage) if eyes is not None else 0
    return run.report


# 문 하나만 열린 작은 오두막(벽 11장 + 문)과 안에 놓인 나무, 이름표가 같은 포털 두 개.
# 오프셋은 봇 앞쪽 m, 오른쪽 m, 앞쪽에서 돌린 각도.
HUT = (
    "wood_door@8,0,0;woodwall#f1@8,-2,0;woodwall#f2@8,2,0;"
    "woodwall#b1@14,-2,0;woodwall#b2@14,0,0;woodwall#b3@14,2,0;"
    "woodwall#l1@9,-3,90;woodwall#l2@11,-3,90;woodwall#l3@13,-3,90;"
    "woodwall#r1@9,3,90;woodwall#r2@11,3,90;woodwall#r3@13,3,90;"
    "Wood@11,0"
)
PORTALS = "portal_wood#home@4,8,0;portal_wood#home@6,-40,0"


async def run_travel(game: Path, backend: str, timeout_s: int) -> dict[str, Any]:
    """Doors and portals in the real game (2026-10-18 rehearsal: Thorkell could not get into the leader's
    house and did not know the portal). He walks to a log inside a hut whose only way in is a closed door,
    then goes through a portal by its tag and comes out at the other one."""
    setup = Setup(
        "travel", backend=backend, timeout_s=timeout_s, bridge=True, world_fixtures=f"{HUT};{PORTALS}"
    )
    run = NativeRun(game, setup)
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        placed = run.read_body("fixtures-ready.json")["placed"]
        log_id = next(p["id"] for p in placed if p["prefab"] == "Wood")

        async def into_hut() -> dict[str, Any]:
            result = await s.command(
                "move_to", {"target": {"id": log_id}, "arrive_radius": 1.6, "timeout_s": 45}, timeout=60
            )
            if result.status != "succeeded" or not result.evidence.get("doors_opened"):
                raise StepFailed(f"did not get in through the door: {result.code} {result.evidence}")
            return {"code": result.code, "doors_opened": result.evidence["doors_opened"]}

        run.extra["hut"] = await run.step("into_the_hut_through_the_door", into_hut)

        async def portal() -> dict[str, Any]:
            def connected() -> bool:
                return any(p.get("tag") == "home" and p.get("connected") for p in s.nearby("portal"))

            await s.wait_for(connected, 30)
            controller = Controller(s, leader_name=LEADER)
            stop = asyncio.Event()
            task = asyncio.create_task(controller.run(stop))
            before = list(s.state.data["pos"]) if s.state else [0.0, 0.0, 0.0]
            try:
                controller.request(Goal("use_portal", Tier.USER, {"tag": "home"}, source="leader"))
                await s.wait_for(
                    lambda: any(
                        d.goal_kind == "use_portal" and d.kind in ("done", "fail")
                        for d in controller.decisions
                    ),
                    60,
                )
            finally:
                stop.set()
                await asyncio.gather(task, return_exceptions=True)
            after = list(s.state.data["pos"]) if s.state else before
            moved = math.hypot(after[0] - before[0], after[2] - before[2])
            said = [f"{d.kind}: {d.reason_ko}" for d in controller.decisions if d.goal_kind == "use_portal"]
            if moved < 30:
                raise StepFailed(f"did not come out at the other portal (moved {moved:.1f} m): {said}")
            return {"moved_m": round(moved, 1), "decisions": said}

        run.extra["portal"] = await run.step("through_the_portal", portal)
    return run.report


def _language(config_path: Path | None) -> Language:
    """The run's language (config `language`): the brain thinks and speaks in it and both games load it."""
    language = load(config_path).language if config_path is not None else "ko"
    lang.use(language)
    return language


def _planner_from(config_path: Path) -> Planner:
    config = load(config_path)
    if config.planner.backend != "gemini":
        raise ScenarioError(f"{config_path}: planner.backend must be gemini, not {config.planner.backend!r}")
    return Planner(
        GeminiJson(secret("GEMINI_API_KEY")),
        PlannerConfig(model=config.planner.model, thinking=config.planner.thinking),
    )


async def run_talk(
    game: Path, backend: str, timeout_s: int, planner_config: Path | None = None, record: bool = False
) -> dict[str, Any]:
    """S-talk: the leader talks in game chat like a person. The host plugin hands the words to the brain
    (the game does not deliver chat to the loopback bot), Thorkell answers in game chat under his own name,
    follows, stops, and finds a far leader on the map. With a planner config, small talk is answered by the
    real planner (keys come from the environment)."""
    from thorkell.ops import play  # play imports this module

    planner = _planner_from(planner_config) if planner_config is not None else None
    # 봇은 리더 앞 20m에 둔다: 일반 채팅(15m)이 닿지 않는 거리라 대답은 외침으로 가야 한다.
    # 멀리 따라가는 길에 그레이링이 덤빈다. 처음 몇 분 지난 사람처럼 곤봉과 먹을 것은 들고 시작한다
    # (빈손·빈속이면 체력 25로 그레이링 무리에 죽었다, 실게임 2026-10-17).
    run = NativeRun(
        game,
        Setup(
            "talk",
            backend=backend,
            timeout_s=timeout_s,
            bridge=True,
            bot_offset="20,0",
            inventory_fixtures="Club:1,Raspberry:6,Mushroom:6",
            language=_language(planner_config),
            record=record,
        ),
    )
    async with run:
        s = run.session
        await run.step("armed", lambda: s.wait_for(lambda: s.armed and s.scene is not None, 60))
        mind = Mind(Store(run.run_dir / "knowledge.sqlite"), leader_name=LEADER)
        controller = Controller(s, leader_name=LEADER, planner=planner, mind=mind, leader_chat_via_host=True)
        cues = LeaderCues(run.host, run.note_said)
        stop = asyncio.Event()
        heard: list[str] = []

        async def relay() -> None:
            tail = play.LeaderChatTail(run.host.root / play.LEADER_CHAT)
            while not stop.is_set():
                for said in tail.read():
                    text = str(said.get("text", "")).strip()
                    if said.get("from") == LEADER and text:
                        heard.append(text)
                        await controller.hear_leader(text)
                await asyncio.sleep(0.2)

        def by(name: str) -> list[str]:
            return [text for who, text in host_chat(run.host) if who == name]

        async def thorkell_says(predicate: Callable[[str], bool], timeout: float) -> tuple[str, float]:
            began = time.monotonic()
            while time.monotonic() - began < timeout:
                for text in by(BOT):
                    if predicate(text):
                        return text, round(time.monotonic() - began, 1)
                await asyncio.sleep(0.2)
            raise StepFailed(f"Thorkell did not say it within {timeout}s; Thorkell said {by(BOT)}")

        def leader_distance() -> float | None:
            leader = s.scene.data.get("leader") if s.scene else None
            return float(leader["distance"]) if leader else None

        async def near_leader(within: float, timeout: float) -> float:
            began = time.monotonic()
            await s.wait_for(lambda: (d := leader_distance()) is not None and d <= within, timeout)
            return round(time.monotonic() - began, 1)

        tasks = [asyncio.create_task(controller.run(stop)), asyncio.create_task(relay())]
        try:

            async def arrival_named() -> dict[str, Any]:
                # 토르켈의 첫 외침("내가 왔다!")이 사람 화면 채팅창에 토르켈 이름으로 찍혀야 한다.
                # 같은 Steam 계정이라 고치기 전에는 리더 이름으로 찍혔다.
                await thorkell_says(lambda text: True, 30)
                misnamed = misnamed_after_arrival(host_chat(run.host), LEADER, BOT)
                if misnamed:
                    raise StepFailed(f"lines under the leader's name before the leader spoke: {misnamed}")
                return {"thorkell_lines": by(BOT)}

            await run.step("arrival_shown_as_thorkell", arrival_named)

            async def follow() -> dict[str, Any]:
                start = leader_distance()
                await cues.do({"say": tr("토르켈, 따라와", "Thorkell, follow me")})
                following = tr("응, 따라갈게.", "Okay, I'll follow you.")
                # 멀면 외쳐서 답하고, 게임은 외침을 대문자로 보인다(영어에서만 드러난다).
                reply, ack_s = await thorkell_says(lambda text: text.upper() == following.upper(), 15)
                arrive_s = await near_leader(5.0, 45)
                return {"start_m": start, "reply": reply, "ack_s": ack_s, "arrive_s": arrive_s}

            await run.step("follow", follow)

            async def follow_on() -> dict[str, Any]:
                moved = await cues.do({"site": [14, 22]})
                return {"leader_at": moved["pos"], "arrive_s": await near_leader(5.0, 45)}

            await run.step("follow_after_leader_walks_off", follow_on)

            async def stop_on_word() -> dict[str, Any]:
                await cues.do({"say": tr("멈춰", "Stop")})
                stopping = tr("알겠어, 멈출게.", "Got it, I'll stop.")
                reply, ack_s = await thorkell_says(lambda text: text.upper() == stopping.upper(), 15)
                await s.wait_for(
                    lambda: (
                        controller.current() is None
                        and s.state is not None
                        and s.state.data.get("action") is None
                    ),
                    5,
                )
                return {"reply": reply, "ack_s": ack_s}

            await run.step("stop", stop_on_word)

            async def far_follow() -> dict[str, Any]:
                # 리더 캐릭터는 시뮬레이션 거리(기본 구역 ±2개, 약 160~226m, 설정에 따라 350m까지) 안에서만
                # 봇에게 로드된다. 그 밖이면 지도에 공개한 위치(leader_on_map)로 찾아온다.
                await cues.do({"share_position": True})
                moved = await cues.do({"site": [260, 320]}, timeout=60)
                try:
                    await s.wait_for(lambda: s.scene is not None and "leader_on_map" in s.scene.data, 20)
                    via = "map"
                except TimeoutError:
                    if not (s.scene and s.scene.data.get("leader")):
                        raise StepFailed("the leader is neither seen nor on the map after moving") from None
                    via = "sight"  # 시뮬레이션 거리가 커서 여전히 보인다
                assert s.scene is not None
                seen = s.scene.data.get("leader_on_map") or s.scene.data.get("leader") or {}
                start = seen.get("distance")
                await cues.do({"say": tr("따라와", "Follow me")})
                if via == "map":
                    expected = tr("지도에서 너를 찾았어", "Found you on the map")
                else:
                    expected = tr("응, 따라갈게.", "Okay, I'll follow you.")
                reply, ack_s = await thorkell_says(lambda text: text.upper().startswith(expected.upper()), 20)

                def host_distance() -> float | None:
                    status = play.read_status(run.host) or {}
                    bot = (status.get("thorkell") or {}).get("pos")
                    leader = status.get("leader_pos")
                    return distance_m(leader, bot) if bot and leader else None

                began = time.monotonic()
                # 실패하면 어디서 왜 멈췄는지 보이도록 5초마다 몸의 위치와 하던 동작을 남긴다.
                trail: list[dict[str, Any]] = []

                async def sample() -> None:
                    while True:
                        state = s.state.data if s.state else {}
                        trail.append(
                            {
                                "t": round(time.monotonic() - began),
                                "pos": [round(v) for v in state.get("pos", [])],
                                "speed": round(math.hypot(state["vel"][0], state["vel"][2]), 1)
                                if state.get("vel")
                                else None,
                                "run_walk_crouch": [
                                    state.get(k) for k in ("running", "walking", "crouching")
                                ],
                                "stamina": state.get("stamina"),
                                "glancing": state.get("glancing_at"),
                                "action": state.get("action"),
                                "reflex": state.get("reflex"),
                                "to_leader_m": host_distance(),
                            }
                        )
                        await asyncio.sleep(5)

                sampler = asyncio.create_task(sample())
                try:
                    await s.wait_for(lambda: (d := host_distance()) is not None and d <= 8.0, 240)
                except TimeoutError:
                    run.extra["far_follow_trail"] = trail
                    raise StepFailed(
                        f"still {host_distance()} m from the leader after 240s ({via}); "
                        f"Thorkell said {by(BOT)[-3:]}; trail {trail[:3]} ... {trail[-3:]}"
                    ) from None
                finally:
                    sampler.cancel()
                return {
                    "via": via,
                    "leader_at": moved["pos"],
                    "start_m": start,
                    "reply": reply,
                    "ack_s": ack_s,
                    "arrive_s": round(time.monotonic() - began, 1),
                }

            await run.step("far_follow", far_follow)

            if planner is not None:

                async def small_talk() -> dict[str, Any]:
                    before = len(by(BOT))
                    await cues.do(
                        {
                            "say": tr(
                                "안녕 토르켈, 오늘 기분 어때?", "Hey Thorkell, how are you feeling today?"
                            )
                        }
                    )
                    reply, latency = await thorkell_says(lambda text: len(by(BOT)) > before, 60)
                    reply = by(BOT)[before]
                    goal = controller.current()
                    return {"reply": reply, "latency_s": latency, "goal_after": goal.kind if goal else None}

                await run.step("small_talk_by_planner", small_talk)

            async def names() -> dict[str, Any]:
                spoken = [d.reason_ko.split("] ", 1)[-1] for d in controller.decisions if d.kind == "speak"]
                # 혼잣말(속삭임)은 리더가 가까이 있을 때만 보인다. 보였다면 토르켈 이름이어야 하는 것은 같다.
                aloud = [
                    d.reason_ko.split("] ", 1)[-1]
                    for d in controller.decisions
                    if d.kind == "speak" and d.talker != "whisper"
                ]
                shown = by(BOT)
                missing = [text for text in aloud if text not in shown and text.upper() not in shown]
                wrong = [text for text in by(LEADER) if text in spoken or text.upper() in spoken]
                if missing or wrong:
                    raise StepFailed(f"not shown as Thorkell: {missing}; shown as the leader: {wrong}")
                return {"spoken": len(spoken)}

            await run.step("every_line_shown_as_thorkell", names)
        finally:
            stop.set()
            await asyncio.gather(*tasks, return_exceptions=True)
            run.note_thorkell(controller)
            run.extra["conversation"] = {
                "heard": heard,
                "chat_window": [f"{who}: {text}" for who, text in host_chat(run.host)],
                "decisions": [f"{d.kind}: {d.reason_ko}" for d in controller.decisions],
            }
    return run.report
