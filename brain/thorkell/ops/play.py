"""`thorkell play --rehearsal <world>`: play with Thorkell on a copy of one of your worlds.

The human plays in an isolated host runtime (host-rehearsal): its saves are a copy of <world> and of the
human's characters from the latest `thorkell backup`, Steam Cloud is off, and the shared prefs are read-only.
The human's own saves, Steam Cloud and settings are never written; the guard checks that at the end.

  1. checks: Steam on, the real Valheim closed, plugin builds (rebuilt with --build) and a backup with <world>
  2. server password: kept in a 0600 file, asked once; the human uses the same one in the game menu
  3. host runtime: created and seeded once (later runs keep the rehearsal's progress); the game window opens
  4. the human starts <world> as a server; the host plugin's status file says when the listener is open
     and which character is the leader
  5. brain (bridge on 127.0.0.1) + bot runtime (isolated, its own persistent character) -> the bot joins
  6. Thorkell's lines and decisions are shown; the human's typed lines reach Thorkell like the leader's chat
  7. quit: the bot saves its character and quits; the human's game stays open

Two front ends: a terminal (`--ui console`) and the Thorkell.app window (`--ui jsonl`: one JSON object per
line on stdout; commands as JSON lines on stdin: say, status, quit, password).
"""

from __future__ import annotations

import asyncio
import getpass
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar, TextIO

from thorkell import app
from thorkell.body import auth
from thorkell.config import ConfigError, LeaderConfig, load, secret
from thorkell.lang import GAME_LANGUAGE, Language, tr
from thorkell.ops import backup, guard, runtime, scenario, vendor
from thorkell.paths import REPO_ROOT, THORKELL_HOME
from thorkell.world.where import where_ko

HOST_PORT = 54880
HOST_STATUS = "thorkell-host-status.json"
# 사람 게임(호스트 플러그인)이 리더가 보낸 채팅을 한 줄씩 덧붙이는 파일.
# 게임의 채팅 전달은 토르켈에게 닿지 않는다: 루프백으로 들어온 토르켈은 플랫폼 ID가 비어 있어
# 보내기 전 권한 확인이 Error로 끝난다. 일반 채팅은 15m 제한도 있다.
LEADER_CHAT = "thorkell-leader-chat.jsonl"
PASSWORD_FILE = THORKELL_HOME / "secrets/server-password"
BOT_NAME = "Thorkell"
# 리허설 캐릭터는 실제 월드용 캐릭터와 따로 둔다: 실전 첫 등장은 다시 시작 신전이어야 한다.
REHEARSAL_CHARACTER = "thorkell_rehearsal"
BOT_ARGS = ["-batchmode", "-screen-width", "640", "-screen-height", "360", "-screen-fullscreen", "0"]
BUILD_LOG = REPO_ROOT / "artifacts/play-build.log"
DEAD_ENDS = {
    "untested_build": "이 Valheim 빌드는 Thorkell이 시험한 버전이 아닙니다(게임 업데이트 뒤라면 지원부터).",
    "not_a_thorkell_runtime": "호스트 플러그인이 Thorkell 런타임 밖에서 실행됐습니다.",
    "crossplay_shim_unavailable": "crossplay 호환 패치를 쓸 수 없습니다. crossplay를 끄고 다시 열어 주세요.",
    "listen_failed": "Thorkell용 접속 포트를 열지 못했습니다. 다른 프로그램이 포트를 쓰는지 확인하세요.",
    "bad_address": "Thorkell용 접속 주소가 잘못됐습니다.",
    "steam_host_busy": "Steam 호스트 소켓이 이미 있어 리스너를 열지 않았습니다.",
    "unsupported_backend": "이 접속 방식(백엔드)은 아직 지원하지 않습니다.",
}

log = logging.getLogger(__name__)


class PlayError(Exception):
    pass


def log_to_file(run_dir: Path) -> Path:
    """Keep the brain's decisions and warnings in the run directory while playing, so what Thorkell is stuck
    on can be read from outside the app. The terminal and the app still get warnings only."""
    path = run_dir / "brain.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    for shown in logging.getLogger().handlers:
        shown.setLevel(logging.WARNING)
    brain = logging.getLogger("thorkell")
    brain.setLevel(logging.INFO)
    brain.addHandler(handler)
    return path


# --- server password ------------------------------------------------------------------------------
def stored_password(path: Path = PASSWORD_FILE) -> str | None:
    return path.read_text() if path.is_file() else None


def save_password(password: str, path: Path = PASSWORD_FILE) -> str:
    """Kept only in a 0600 file; never printed or put on a command line."""
    if len(password) < 5:
        raise PlayError("Valheim 서버 비밀번호는 5자 이상이어야 합니다.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(password)
    os.chmod(path, 0o600)
    return password


# --- front ends -----------------------------------------------------------------------------------
class ConsoleUi:
    """A terminal: messages are printed, the password is asked without echo, typed lines are chat."""

    PREFIX: ClassVar[dict[str, str]] = {
        "thorkell": "  토르켈: ",
        "status": "  ",
        "warn": "[!] ",
        "error": "[ERR] ",
    }

    def __init__(self) -> None:
        self._lines: asyncio.Queue[str | None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def emit(self, kind: str, text: str = "", **extra: Any) -> None:
        # 위치는 걷는 동안 계속 바뀐다. 터미널에서는 대화에 섞지 않고 /status 답에 붙인다.
        if kind in ("phase", "need_password", "where"):
            return
        if kind == "decision":
            text = f"  · {extra.get('decision')}: {text}"
        print(self.PREFIX.get(kind, "") + text, flush=True)

    async def ask_password(self, problem: str | None) -> str:
        if problem:
            print(problem)
        print(
            "Thorkell이 서버에 들어갈 때 쓸 비밀번호를 정합니다. "
            "서버를 열 때 메뉴에도 같은 비밀번호를 넣어 주세요."
        )
        return await asyncio.to_thread(
            getpass.getpass, "서버 비밀번호(5자 이상, 입력이 화면에 보이지 않음): "
        )

    def lines(self) -> asyncio.Queue[str | None]:
        # 비밀번호를 물은 뒤에 연다: 둘 다 같은 표준 입력을 읽는다.
        if self._lines is None:
            assert self._loop is not None
            self._lines = asyncio.Queue()
            threading.Thread(target=self._read, args=(self._loop, self._lines), daemon=True).start()
        return self._lines

    @staticmethod
    def _read(loop: asyncio.AbstractEventLoop, lines: asyncio.Queue[str | None]) -> None:
        while True:
            try:
                line = input()
            except EOFError:
                loop.call_soon_threadsafe(lines.put_nowait, None)
                return
            loop.call_soon_threadsafe(lines.put_nowait, line)


class JsonUi:
    """The Thorkell.app window. Out: {"type", "text", ...} per line. In: {"type": "say"|"status"|"quit"|
    "password", ...} per line; end of input counts as quit."""

    def __init__(self, out: TextIO = sys.stdout, inp: TextIO = sys.stdin) -> None:
        self._out, self._in = out, inp
        self._lines: asyncio.Queue[str | None] = asyncio.Queue()
        self._passwords: asyncio.Queue[str | None] = asyncio.Queue()
        self._write = threading.Lock()

    def attach(self, loop: asyncio.AbstractEventLoop) -> None:
        threading.Thread(target=self._read, args=(loop,), daemon=True).start()

    def emit(self, kind: str, text: str = "", **extra: Any) -> None:
        with self._write:
            self._out.write(json.dumps({"type": kind, "text": text, **extra}, ensure_ascii=False) + "\n")
            self._out.flush()

    async def ask_password(self, problem: str | None) -> str:
        self.emit("need_password", problem or "Thorkell이 서버에 들어갈 때 쓸 비밀번호를 정해 주세요.")
        password = await self._passwords.get()
        if password is None:
            raise PlayError("서버 비밀번호를 정하지 않아 멈췄습니다.")
        return password

    def lines(self) -> asyncio.Queue[str | None]:
        return self._lines

    def _quit(self, loop: asyncio.AbstractEventLoop) -> None:
        # 비밀번호를 기다리던 중이어도 끝낼 수 있게 두 줄 모두에 알린다.
        loop.call_soon_threadsafe(self._lines.put_nowait, None)
        loop.call_soon_threadsafe(self._passwords.put_nowait, None)

    def _read(self, loop: asyncio.AbstractEventLoop) -> None:
        for raw in self._in:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                self.emit("warn", f"알 수 없는 입력을 무시했습니다: {raw.strip()[:80]}")
                continue
            match message.get("type"):
                case "say":
                    loop.call_soon_threadsafe(self._lines.put_nowait, str(message.get("text", "")))
                case "status":
                    loop.call_soon_threadsafe(self._lines.put_nowait, "/status")
                case "quit":
                    self._quit(loop)
                case "password":
                    loop.call_soon_threadsafe(self._passwords.put_nowait, str(message.get("value", "")))
                case other:
                    self.emit("warn", f"알 수 없는 명령을 무시했습니다: {other}")
        self._quit(loop)


Ui = ConsoleUi | JsonUi


# --- the rehearsal --------------------------------------------------------------------------------
def prepare_rehearsal_host(
    root: Path,
    game: Path,
    bepinex: Path,
    plugin_dirs: Sequence[Path],
    made: backup.Backup,
    world: str,
    language: Language,
) -> tuple[runtime.Runtime, bool]:
    """The human's rehearsal runtime. Seeded from the backup only when created, so progress carries over."""
    created = not root.exists()
    host = runtime.ensure(root, "host-rehearsal", game, bepinex, plugin_dirs)
    if created:
        runtime.seed_saves(host, made.world(world), made.characters())
        (host.root / "seeded-from.json").write_text(json.dumps({"backup": str(made.root), "world": world}))
    runtime.write_config(
        host,
        "thorkell.host",
        {"Listener": {"Port": HOST_PORT, "Worlds": world}, "Game": {"Language": GAME_LANGUAGE[language]}},
    )
    return host, created


def prepare_fresh_host(
    root: Path,
    game: Path,
    bepinex: Path,
    plugin_dirs: Sequence[Path],
    made: backup.Backup | None,
    world: str,
    language: Language,
) -> tuple[runtime.Runtime, bool]:
    """A runtime for a brand-new world the human makes in the game menu, to play from the start together
    (the rehearsal copy is a late-game world). Only the characters come from the backup; a new one can be
    made in the menu. The world's progress stays in this runtime for the next session."""
    created = not root.exists()
    host = runtime.ensure(root, "host-rehearsal", game, bepinex, plugin_dirs)
    if created and made is not None:
        folder = host.saves / "characters_local"
        folder.mkdir(parents=True, exist_ok=True)
        for character in made.characters():
            shutil.copy2(character, folder / character.name)
        (host.root / "seeded-from.json").write_text(json.dumps({"backup": str(made.root), "world": None}))
    runtime.write_config(
        host,
        "thorkell.host",
        {"Listener": {"Port": HOST_PORT, "Worlds": world}, "Game": {"Language": GAME_LANGUAGE[language]}},
    )
    return host, created


class LeaderChatTail:
    """Lines the host plugin appended to the leader-chat file since this session started."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = path.stat().st_size if path.is_file() else 0

    def read(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
        end = data.rfind(b"\n") + 1  # 아직 덜 쓴 마지막 줄은 다음에 읽는다
        self.offset += end
        return [json.loads(line) for line in data[:end].decode().splitlines() if line.strip()]


def read_status(host: runtime.Runtime) -> dict[str, Any] | None:
    path = host.root / HOST_STATUS
    if not path.is_file():
        return None
    status: dict[str, Any] = json.loads(path.read_text())  # 호스트가 통째로 바꿔 끼우므로 반쯤 쓴 파일은 없다
    return status


def ready(status: dict[str, Any] | None) -> bool:
    return (
        status is not None
        and str(status.get("listener", "")).startswith("open")
        and bool(status.get("leader"))
    )


def thorkell_where(status: dict[str, Any] | None) -> str | None:
    """Where Thorkell is from the leader, as the host sees both players (shown to the human only)."""
    leader = status.get("leader_pos") if status else None
    bot = (status.get("thorkell") or {}).get("pos") if status else None
    if not leader or not bot:
        return None
    where = where_ko(leader, bot)
    return tr(f"토르켈은 내 {where}에 있어요", f"Thorkell is {where}")


def waiting_hint(status: dict[str, Any] | None, world: str, new: bool = False) -> str:
    """What to tell the human while waiting; raises on states that will not get better by waiting."""
    state = status.get("listener") if status else None
    if state in DEAD_ENDS:
        raise PlayError(DEAD_ENDS[str(state)])
    if state == "world_not_allowed":
        assert status is not None
        opened = status.get("world")
        return (
            f"'{opened}' 월드가 열렸습니다. 리허설은 '{world}'로만 합니다. 나갔다가 '{world}'를 열어 주세요."
        )
    if state is not None and str(state).startswith("open"):
        return "서버가 열렸습니다. 월드에 들어오는 중..."
    if new:
        return (
            "게임 창에서 캐릭터를 고르거나 새로 만들고(처음부터 같이 하려면 새 캐릭터), "
            f"'새 월드'로 '{world}'를 만든 뒤(시드는 아무거나) '서버 시작'을 켜고(crossplay 켬) "
            "정해 둔 비밀번호로 시작해 주세요. "
            "두 번째부터는 만든 월드를 고르면 됩니다."
        )
    return (
        f"게임 창에서 캐릭터를 고르고 월드 '{world}'를 선택한 뒤, '서버 시작'을 켜고(crossplay 켬) "
        "정해 둔 비밀번호로 시작해 주세요."
    )


def check_machine(game: Path) -> None:
    if subprocess.run(["pgrep", "-x", "steam_osx"], capture_output=True, check=False).returncode != 0:
        raise PlayError("Steam이 꺼져 있습니다. Steam을 켜고 로그인한 뒤 다시 시작하세요.")
    try:
        scenario.refuse_while_valheim_runs(game)
    except scenario.ScenarioError:
        raise PlayError("진짜 Valheim이 켜져 있습니다. 게임을 끄고 다시 시작하세요.") from None


def build_plugins() -> None:
    BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with BUILD_LOG.open("w") as out:
        done = subprocess.run(
            ["dotnet", "build", str(REPO_ROOT / "Thorkell.sln"), "-c", "Release", "-nologo", "-v", "quiet"],
            stdout=out,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if done.returncode != 0:
        raise PlayError(f"플러그인 빌드가 실패했습니다. 로그: {BUILD_LOG}")


def _running(rt: runtime.Runtime) -> bool:
    found = subprocess.run(["pgrep", "-f", str(rt.executable)], capture_output=True, text=True, check=False)
    return bool(found.stdout.strip())


def _launch(rt: runtime.Runtime, args: list[str], game: Path) -> subprocess.Popen[bytes]:
    out = (rt.logs / "launcher.log").open("ab")
    # 새 세션으로 띄워서 터미널의 Ctrl-C나 앱 종료 신호가 게임 창까지 끄지 않게 한다.
    return subprocess.Popen(
        runtime.launch_command(rt, args, game),
        cwd=rt.root,
        stdout=out,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


async def _stop_bot(
    ui: Ui, body: runtime.Runtime, bot: subprocess.Popen[bytes], timeout_s: float = 20
) -> None:
    if bot.poll() is not None:
        return
    (body.root / "quit.txt").write_text("quit\n")
    deadline = time.monotonic() + timeout_s
    while bot.poll() is None and time.monotonic() < deadline:
        await asyncio.sleep(0.5)
    if bot.poll() is None:
        ui.emit(
            "warn", f"토르켈 창이 {timeout_s:.0f}초 안에 닫히지 않아 강제로 껐습니다(캐릭터 저장은 요청했음)."
        )
        os.killpg(bot.pid, signal.SIGKILL)
        bot.wait(timeout=10)
    (body.root / "quit.txt").unlink(missing_ok=True)


async def rehearse(
    game: Path,
    world: str,
    config_path: Path | None,
    ui: Ui,
    build: bool = False,
    check_only: bool = False,
    new_world: bool = False,
) -> int:
    ui.attach(asyncio.get_running_loop())
    ui.emit("phase", "준비 상태를 확인하는 중", phase="checking")
    config = load(config_path)
    if config.voice.backend != "none":
        raise PlayError('play는 아직 게임 채팅만 지원합니다. 설정에서 voice.backend = "none"으로 두세요.')
    for name in config.required_secrets():
        secret(name)
    models = "Gemini Flash + Jev" if config.planner.backend == "gemini" else "모델 없음(정해진 말만 알아들음)"
    if config.vision.backend == "gemini":
        models += f" + 눈({config.vision.model})"
    check_machine(game)
    ui.emit("step", "✓ Steam 실행 중, 진짜 Valheim은 꺼져 있음")
    if build:
        ui.emit("step", "플러그인을 최신 코드로 빌드하는 중...")
        build_plugins()
        ui.emit("step", "✓ 플러그인 빌드")
    made = backup.latest()
    if made is None and not check_only:
        ui.emit("step", "백업이 아직 없어 먼저 만듭니다(원본은 읽기만 합니다)...")
        made = backup.create()
    if new_world:
        ui.emit("step", f"✓ 새 월드 '{world}'로 처음부터 같이 합니다(캐릭터만 백업에서 가져옵니다)")
    elif made is not None:
        made.world(world)
        ui.emit("step", f"✓ 백업 {made.root.name}에 '{world}' 있음")
    ui.emit("step", f"✓ 두뇌: {models}")
    if check_only:
        has_password = stored_password() is not None
        ui.emit("step", "✓ 서버 비밀번호 저장됨" if has_password else "· 서버 비밀번호는 시작할 때 정합니다")
        ui.emit("phase", "점검 끝: 시작할 수 있습니다", phase="ready", password_saved=has_password)
        return 0

    password = stored_password()
    problem: str | None = None
    while password is None:
        try:
            password = save_password(await ui.ask_password(problem))
        except PlayError as error:
            problem = str(error)
    bepinex = vendor.ensure(vendor.load()) / "BepInExPack_Valheim"
    knowledge = THORKELL_HOME / "knowledge" / f"{world}-{'new' if new_world else 'rehearsal'}.sqlite"
    knowledge.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    with scenario.native_lock():
        prefs_before = guard.snapshot_prefs()
        saves_before = guard.fingerprint()
        host_root = runtime.RUNTIMES_DIR / (f"new-{world}" if new_world else "rehearsal-host")
        if host_root.exists() and _running(runtime.open_existing(host_root)):
            # 이미 떠 있는 게임의 플러그인 파일이나 설정은 건드리지 않는다.
            host = runtime.open_existing(host_root)
            ui.emit("step", "리허설 게임 창이 이미 떠 있습니다. 그대로 씁니다.")
        elif new_world:
            host, created = prepare_fresh_host(
                host_root, game, bepinex, [runtime.PLUGIN_BUILDS["host"]], made, world, config.language
            )
            origin = "새 월드(게임 메뉴에서 만듭니다)" if created else f"'{world}'를 이어서"
            ui.emit("step", f"월드 준비: {origin}")
            _launch(host, ["-thorkell-host", "-logFile", str(host.logs / "Player.log")], game)
            ui.emit("step", "내 게임 창을 띄웠습니다(처음엔 1분쯤 걸릴 수 있습니다).")
        else:
            assert made is not None
            host, created = prepare_rehearsal_host(
                host_root, game, bepinex, [runtime.PLUGIN_BUILDS["host"]], made, world, config.language
            )
            origin = f"백업 {made.root.name}에서 새로 복사" if created else "이전 리허설을 이어서"
            ui.emit("step", f"리허설 월드 준비: {origin}")
            _launch(host, ["-thorkell-host", "-logFile", str(host.logs / "Player.log")], game)
            ui.emit("step", "내 게임 창을 띄웠습니다(처음엔 1분쯤 걸릴 수 있습니다).")

        ui.emit("phase", "서버가 열리기를 기다리는 중", phase="waiting_server")
        told = ""
        while not ready(status := read_status(host)):
            hint = waiting_hint(status, world, new=new_world)
            if hint != told:
                ui.emit("hint", hint)
                told = hint
            if not _running(host):
                raise PlayError("리허설 게임 창이 닫혔습니다.")
            await asyncio.sleep(1)
        assert status is not None
        leader = str(status["leader"])
        if not status.get("leader_chat"):
            ui.emit(
                "warn",
                "내 게임 창이 옛 버전 플러그인으로 떠 있어 게임 채팅이 토르켈에게 전해지지 않습니다. "
                "게임을 저장하고 끈 뒤 '리허설 시작'을 다시 누르세요(그동안은 이 창으로 말할 수 있습니다).",
            )
        ui.emit("phase", f"리더 {leader}. 토르켈을 부르는 중", phase="starting_bot", leader=leader)

        config = config.model_copy(update={"leader": LeaderConfig(name=leader)})
        token = auth.new_hex(32)
        brain = await app.build(config, token, THORKELL_HOME, knowledge=knowledge)
        ui.emit("step", f"두뇌 기록: {log_to_file(brain.run_dir)}")
        brain.controller.leader_chat_via_host = True
        leader_chat = LeaderChatTail(host.root / LEADER_CHAT)
        stop = asyncio.Event()
        serve = asyncio.create_task(app.serve(brain, config.bridge.port, stop))
        body_root = runtime.RUNTIMES_DIR / "body"
        if body_root.exists() and _running(runtime.open_existing(body_root)):
            raise PlayError(f"이전 토르켈 창이 아직 떠 있습니다. 닫고 다시 시작해 주세요: {body_root}")
        body = runtime.ensure(body_root, "body", game, bepinex, [runtime.PLUGIN_BUILDS["body"]])
        (body.root / "quit.txt").unlink(missing_ok=True)
        runtime.write_config(
            body,
            "thorkell.body",
            {
                "Join": {"Host": "127.0.0.1", "Port": HOST_PORT, "Password": password},
                "Body": {
                    "CharacterFile": REHEARSAL_CHARACTER,
                    "CharacterName": BOT_NAME,
                    "LeaderName": leader,
                },
                "Bridge": {"Port": config.bridge.port, "Token": token},
                "Game": {"Language": GAME_LANGUAGE[config.language]},
            },
        )
        bot = _launch(body, [*BOT_ARGS, "-logFile", str(body.logs / "Player.log"), "-thorkell-body"], game)
        ui.emit(
            "hint",
            "토르켈 창(작고 소리 없음)을 띄웠습니다. "
            "처음엔 시작 신전에, 그다음부터는 지난번에 끝낸 자리에 나타납니다.",
        )

        lines = ui.lines()
        seen, armed, next_host_check = 0, False, 0.0
        where: str | None = None
        try:
            while True:
                if time.monotonic() >= next_host_check:
                    next_host_check = time.monotonic() + 2
                    status = read_status(host)
                    if not ready(status):
                        ui.emit("warn", "내 서버가 닫혔거나 리더가 월드를 나갔습니다. 토르켈도 정리합니다.")
                        break
                    if (now_where := thorkell_where(status)) != where:
                        where = now_where
                        ui.emit("where", where or "")
                if bot.poll() is not None:
                    ui.emit(
                        "warn",
                        f"토르켈 창이 끝났습니다(종료 코드 {bot.returncode}). "
                        f"로그: {body.logs / 'Player.log'}",
                    )
                    break
                if brain.session.armed and not armed:
                    armed = True
                    ui.emit("phase", "토르켈이 접속했습니다", phase="connected")
                for said in leader_chat.read():
                    text = str(said.get("text", "")).strip()
                    if said.get("from") == leader and text:
                        ui.emit("heard", text)
                        await brain.controller.hear_leader(text)
                for decision in brain.controller.decisions[seen:]:
                    if decision.kind == "speak":
                        ui.emit("thorkell", decision.reason_ko.split("] ", 1)[-1])
                    else:
                        ui.emit("decision", decision.reason_ko, decision=decision.kind)
                seen = len(brain.controller.decisions)
                try:
                    line = await asyncio.wait_for(lines.get(), timeout=0.2)
                except TimeoutError:
                    continue
                if line is None or line.strip() == "/quit":
                    break
                if line.strip() == "/status":
                    ui.emit("status", " ".join(filter(None, [brain.controller.status_ko(), where])))
                elif line.strip():
                    await brain.controller.hear_leader(line.strip())
        finally:
            ui.emit("phase", "토르켈을 정리하는 중(캐릭터 저장 후 종료)", phase="stopping")
            await _stop_bot(ui, body, bot)
            stop.set()
            await asyncio.gather(serve, return_exceptions=True)
            await brain.close()
            _report_isolation(ui, game, prefs_before, saves_before)
            ui.emit("step", f"기록: {brain.run_dir}")
    return 0


def _report_isolation(
    ui: Ui, game: Path, prefs_before: dict[str, Any], saves_before: dict[str, tuple[int, int]]
) -> None:
    prefs = guard.diff_prefs(prefs_before, guard.snapshot_prefs())
    saves = guard.fingerprint_changes(saves_before, guard.fingerprint())
    if not prefs.keys and not saves:
        ui.emit("isolation", "확인: 내 실제 세이브·Steam Cloud·설정은 바뀌지 않았습니다.", ok=True)
        return
    ui.emit("isolation", f"리허설 중 바뀐 것: 설정 {list(prefs.keys)}, 세이브 {saves}", ok=False)
    try:
        scenario.refuse_while_valheim_runs(game)
    except scenario.ScenarioError:
        ui.emit("warn", "진짜 Valheim이 켜져 있어서 설정을 되돌리지 않았습니다.")
        return
    if prefs.keys:
        ui.emit("warn", f"설정을 리허설 전으로 되돌렸습니다: {guard.restore_prefs(prefs_before, prefs)}")


def main(
    game: Path,
    world: str,
    config_path: Path | None,
    forget_password: bool,
    ui_kind: str = "console",
    build: bool = False,
    check_only: bool = False,
    new_world: bool = False,
) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    ui: Ui = JsonUi() if ui_kind == "jsonl" else ConsoleUi()
    if forget_password:
        PASSWORD_FILE.unlink(missing_ok=True)
        ui.emit("step", "저장해 둔 서버 비밀번호를 지웠습니다.")
    try:
        code = asyncio.run(
            rehearse(game, world, config_path, ui, build=build, check_only=check_only, new_world=new_world)
        )
    except (PlayError, ConfigError, scenario.ScenarioError, backup.BackupError) as error:
        ui.emit("error", str(error))
        ui.emit("phase", "멈춤", phase="failed")
        return 2
    except KeyboardInterrupt:
        return 130
    if not check_only:
        ui.emit("phase", "끝", phase="finished")
    return code
