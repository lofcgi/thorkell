"""`thorkell` command line entry point."""

from __future__ import annotations

import argparse
import asyncio
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from thorkell.ops import backup, judgment, runtime, scenario, vendor, video
from thorkell.ops.simdemo import run_sim_demo
from thorkell.paths import REPO_ROOT, game_managed, game_root

API_CHECK = REPO_ROOT / "tools/Thorkell.ApiCheck/Thorkell.ApiCheck.csproj"
REQUIRED_API = REPO_ROOT / "plugin/Thorkell.Compat/RequiredApi.json"
TESTED_VERSIONS = REPO_ROOT / "plugin/Thorkell.Compat/tested-versions.json"
# talk는 따라가기·멀리 찾아가기까지 걸어 다녀서 길다.
SCENARIO_TIMEOUT_S = {"talk": 900, "skills": 1200, "boss": 1500, "fresh": 2700}


def cmd_vendor(_: argparse.Namespace) -> int:
    pinned = vendor.load()
    path = vendor.ensure(pinned)
    print(f"BepInExPack {pinned.version} ok: {path}")
    return 0


def cmd_verify_api(args: argparse.Namespace) -> int:
    command = [
        "dotnet",
        "run",
        "--project",
        str(API_CHECK),
        "-c",
        "Release",
        "--",
        "--game-root",
        str(args.game_root),
        "--required",
        str(REQUIRED_API),
        "--tested",
        str(TESTED_VERSIONS),
    ]
    return subprocess.run(command, check=False).returncode


def _unity_version(root: Path) -> str:
    info = plistlib.loads((root / "Valheim.app/Contents/Info.plist").read_bytes())
    text = str(info.get("CFBundleGetInfoString", ""))
    marker = "Unity Player version "
    if marker not in text:
        raise RuntimeError(f"Unity version not found in Info.plist: {text!r}")
    return text.split(marker, 1)[1].split(" ", 1)[0]


def cmd_doctor(args: argparse.Namespace) -> int:
    root: Path = args.game_root
    checks: list[tuple[str, bool, str, bool]] = []  # name, ok, detail, required

    sdks = subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True, check=False).stdout
    checks.append(
        ("dotnet SDK 9", any(line.startswith("9.") for line in sdks.splitlines()), sdks.strip(), True)
    )

    managed = game_managed(root)
    checks.append(("Valheim 설치", (managed / "assembly_valheim.dll").is_file(), str(root), True))
    if (root / "Valheim.app/Contents/Info.plist").is_file():
        checks.append(("Unity 버전", True, _unity_version(root), True))

    pinned = vendor.load()
    if pinned.zip.is_file():
        try:
            vendor.verify(pinned)
            checks.append((f"BepInExPack {pinned.version}", pinned.dir.is_dir(), str(pinned.dir), True))
        except RuntimeError as error:
            checks.append((f"BepInExPack {pinned.version}", False, str(error), True))
    else:
        checks.append((f"BepInExPack {pinned.version}", False, "missing: run `thorkell vendor`", True))

    rosetta = subprocess.run(["/usr/bin/arch", "-x86_64", "/usr/bin/true"], check=False).returncode == 0
    checks.append(("Rosetta (x86_64)", rosetta, "BepInEx doorstop은 x64만 있다", True))

    steam = subprocess.run(["pgrep", "-x", "steam_osx"], capture_output=True, check=False).returncode == 0
    checks.append(("Steam 실행 중", steam, "실게임 시나리오에 필요", False))

    checks.append(("1Password CLI", shutil.which("op") is not None, "비밀 주입용 `op run`", False))
    for key in ("GEMINI_API_KEY", "TYPESAFE_API_KEY"):
        checks.append((key, bool(os.environ.get(key)), "값은 출력하지 않음", False))

    failed_required = False
    for name, ok, detail, required in checks:
        mark = "OK " if ok else ("ERR" if required else "-- ")
        failed_required |= required and not ok
        print(f"[{mark}] {name}: {detail}")
    return 1 if failed_required else 0


def cmd_backup(args: argparse.Namespace) -> int:
    if args.verify:
        made = backup.latest()
        if made is None:
            print("[ERR] 아직 백업이 없습니다: `thorkell backup`")
            return 2
        broken = backup.verify(made)
        print(f"{'OK' if not broken else 'BROKEN'}: {made.root} ({len(made.manifest['files'])}개 파일)")
        for name in broken:
            print(f"  다름: {name}")
        return 1 if broken else 0
    try:
        scenario.refuse_while_valheim_runs(args.game_root)
        made = backup.create()
    except (scenario.ScenarioError, backup.BackupError) as error:
        print(f"[ERR] {error}")
        return 2
    files = made.manifest["files"]
    size = sum(entry[0] for entry in files.values())
    print(f"백업 완료: {made.root}")
    print(f"  파일 {len(files)}개, {size / 1e6:.1f} MB, sha256 검증 끝")
    print("  (APFS 복제라 원본이 바뀌기 전까지 디스크를 거의 쓰지 않습니다)")
    for prefix, source in made.manifest["sources"].items():
        print(f"  {prefix} ← {source}")
    print(f"  캐릭터 {len(made.characters())}개")
    return 0


def cmd_scenario(args: argparse.Namespace) -> int:
    if args.config is not None and args.name not in ("talk", "boss", "sight", "fresh"):
        print("[ERR] --config는 talk(실제 플래너로 잡담)와 boss(실제 모델로 싸움 판단·회고)에서만 씁니다.")
        return 2
    if args.record and args.name not in ("talk", "boss", "fresh"):
        print("[ERR] --record는 talk, fresh, boss에서만 씁니다(README 영상).")
        return 2
    if (args.mind is not None or args.together) and args.name != "boss":
        print("[ERR] --mind와 --together는 boss 시나리오에서만 씁니다.")
        return 2
    if args.mortal_leader and not args.together:
        print("[ERR] --mortal-leader는 --together와 같이 씁니다.")
        return 2
    timeout = args.timeout or SCENARIO_TIMEOUT_S.get(args.name, 300)
    try:
        if args.name == "talk":
            report = asyncio.run(
                scenario.run_talk(args.game_root, args.backend, timeout, args.config, args.record)
            )
        elif args.name == "fresh":
            report = asyncio.run(
                scenario.run_fresh(args.game_root, args.backend, timeout, args.config, args.record)
            )
        elif args.name == "travel":
            report = asyncio.run(scenario.run_travel(args.game_root, args.backend, timeout))
        elif args.name == "sight":
            report = asyncio.run(scenario.run_sight(args.game_root, args.backend, timeout, args.config))
        elif args.name == "boss":
            report = asyncio.run(
                scenario.run_boss(
                    args.game_root,
                    args.backend,
                    timeout,
                    args.config,
                    args.mind,
                    args.together,
                    args.record,
                    args.mortal_leader,
                )
            )
        else:
            runner = {
                "peer": scenario.run_peer,
                "primitives": scenario.run_primitives,
                "actions": scenario.run_actions,
                "shelter": scenario.run_shelter,
                "skills": scenario.run_skills,
                "rehearsal": scenario.run_rehearsal,
            }[args.name]
            report = asyncio.run(runner(args.game_root, args.backend, timeout))
    except scenario.ScenarioError as error:
        print(f"[ERR] {error}")
        return 2
    isolation = report["isolation"]
    verdict = "PASS" if report["passed"] else "FAIL"
    print(f"{verdict}: {report['scenario']}/{report['backend']} in {report['elapsed_s']}s")
    if report["failure"]:
        print(f"  failure: {report['failure']}")
    for step in report["steps"]:
        print(f"  [{'ok' if step['ok'] else 'XX'}] {step['name']} ({step['seconds']}s): {step['detail']}")
    for role in ("host", "body"):
        result = report["results"][role]
        print(f"  {role}: {result['detail'] if result else 'no result'}")
    print(f"  human prefs changed: {isolation['prefs_changed']} (restored: {isolation['prefs_restored']})")
    print(f"  human saves changed: {isolation['human_saves_changed']}")
    print(f"  report: {report['artifacts']}/report.json")
    return 0 if report["passed"] else 1


def cmd_contract(args: argparse.Namespace) -> int:
    from thorkell.config import ConfigError
    from thorkell.ops import contract

    try:
        return contract.main(args.name)
    except ConfigError as error:
        print(f"[ERR] {error}")
        return 2


def cmd_play(args: argparse.Namespace) -> int:
    from thorkell.ops import play

    return play.main(
        args.game_root,
        args.rehearsal,
        args.config,
        args.forget_password,
        ui_kind=args.ui,
        build=args.build,
        check_only=args.check,
        new_world=args.new,
    )


def cmd_sim(args: argparse.Namespace) -> int:
    return asyncio.run(run_sim_demo(args.config, args.time_scale))


def cmd_video(args: argparse.Namespace) -> int:
    for made in video.build(args.run):
        print(made)
    return 0


def cmd_judge(args: argparse.Namespace) -> int:
    return asyncio.run(judgment.run(args.case, args.model, args.language))


# 오래 쓰는 런타임: 봇 캐릭터(body)와 리허설 월드(rehearsal-host). 게임이 업데이트되면 다시 복제해야 한다.
LONG_LIVED_RUNTIMES = {"body": "body", "rehearsal-host": "host-rehearsal"}


def cmd_upgrade_runtimes(args: argparse.Namespace) -> int:
    bepinex = vendor.ensure(vendor.load()) / "BepInExPack_Valheim"
    plugins = {"body": runtime.PLUGIN_BUILDS["body"], "host-rehearsal": runtime.PLUGIN_BUILDS["host"]}
    for name, role in LONG_LIVED_RUNTIMES.items():
        root = runtime.RUNTIMES_DIR / name
        if not root.exists():
            print(f"{name}: 없음(처음 실행할 때 새 빌드로 만들어진다)")
            continue
        try:
            fresh, kept = runtime.upgrade(root, role, args.game_root, bepinex, [plugins[role]])
        except ValueError as error:
            print(f"{name}: 그대로 둠 ({error})")
            continue
        print(f"{name}: 새 빌드로 다시 복제하고 세이브를 옮김 -> {fresh.root} (이전 런타임: {kept})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thorkell")
    parser.add_argument("--game-root", type=Path, default=game_root())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("vendor", help="pinned BepInExPack을 받아 sha256을 검증한다").set_defaults(func=cmd_vendor)
    sub.add_parser("verify-api", help="게임 DLL이 Thorkell이 쓰는 API를 갖췄는지 오프라인 점검").set_defaults(
        func=cmd_verify_api
    )
    sub.add_parser("doctor", help="개발 환경 점검").set_defaults(func=cmd_doctor)
    backup_parser = sub.add_parser(
        "backup",
        help="사람의 Valheim 세이브(Steam Cloud·로컬)와 설정을 체크섬과 함께 백업한다(원본은 읽기만)",
    )
    backup_parser.add_argument(
        "--verify", action="store_true", help="가장 최근 백업이 그대로인지 다시 확인한다"
    )
    backup_parser.set_defaults(func=cmd_backup)
    peer = sub.add_parser("scenario", help="실게임 시나리오 (한 번에 하나)")
    peer.add_argument(
        "name",
        choices=[
            "peer",
            "primitives",
            "actions",
            "shelter",
            "skills",
            "boss",
            "rehearsal",
            "talk",
            "sight",
            "travel",
            "fresh",
        ],
    )
    peer.add_argument("--backend", choices=["steam", "playfab"], default="steam")
    peer.add_argument(
        "--timeout", type=int, default=None, help="초 (기본: talk 900, skills 1200, 나머지 300)"
    )
    peer.add_argument(
        "--config",
        type=Path,
        default=None,
        help="talk: 이 설정의 플래너(gemini)로 잡담 답변까지 확인. boss: 이 모델로 싸움을 판단하고 돌아본다",
    )
    peer.add_argument(
        "--mind",
        type=Path,
        default=None,
        help="boss: 토르켈의 기억(싸움 기록·교훈) 파일. 같은 파일로 다시 돌리면 지난 도전에서 배운 것을 쓴다",
    )
    peer.add_argument(
        "--together",
        action="store_true",
        help="boss: 리더가 '같이 잡자'고 하고 맨손으로 보스 곁에서 주의를 끈다(시험 전용 무적)",
    )
    peer.add_argument(
        "--mortal-leader",
        action="store_true",
        help="boss --together: 리더가 무적 없이 음식을 먹고 몽둥이로 막는다(사람 리더처럼 죽을 수 있다)",
    )
    peer.add_argument(
        "--record",
        action="store_true",
        help="README 영상: 토르켈 카메라 장면을 프레임으로, 말과 단계 시각을 timeline.jsonl로 남긴다",
    )
    peer.set_defaults(func=cmd_scenario)
    contract_parser = sub.add_parser(
        "contract", help="실제 API(Flash/Jev/Live)가 가정대로 동작하는지 확인 (키 필요)"
    )
    contract_parser.add_argument("name", choices=["flash", "jev", "live"])
    contract_parser.set_defaults(func=cmd_contract)
    play_parser = sub.add_parser(
        "play", help="토르켈과 같이 플레이한다(지금은 백업 복사본으로 하는 리허설만)"
    )
    play_parser.add_argument(
        "--rehearsal", metavar="WORLD", required=True, help="백업에 있는 월드 이름(예: helloworld)"
    )
    play_parser.add_argument("--config", type=Path, default=None, help="두뇌 설정(예: thorkell.play.toml)")
    play_parser.add_argument(
        "--forget-password", action="store_true", help="저장한 서버 비밀번호를 지우고 다시 묻는다"
    )
    play_parser.add_argument(
        "--ui",
        choices=["console", "jsonl"],
        default="console",
        help="jsonl: Thorkell.app 창과 JSON 줄로 대화",
    )
    play_parser.add_argument("--build", action="store_true", help="시작 전에 플러그인을 최신 코드로 빌드한다")
    play_parser.add_argument("--check", action="store_true", help="준비 상태만 점검하고 게임은 띄우지 않는다")
    play_parser.add_argument(
        "--new",
        action="store_true",
        help="백업 월드 대신 --rehearsal 이름으로 새 월드를 만들어 처음부터 같이 한다(게임 메뉴에서 만든다)",
    )
    play_parser.set_defaults(func=cmd_play)
    sub.add_parser(
        "upgrade-runtimes", help="게임 업데이트 뒤 봇·리허설 런타임을 새 빌드로 다시 복제한다(세이브 유지)"
    ).set_defaults(func=cmd_upgrade_runtimes)
    judge = sub.add_parser(
        "judge", help="목표의 열린 부탁(집 짓자, 멧돼지 잡아와…)을 실제 플래너로 판단해 본다"
    )
    judge.add_argument("--case", action="append", help="이 경우만 (여러 번 줄 수 있음)")
    judge.add_argument("--model", default="gemini-3.8-flash")
    judge.add_argument("--language", choices=["ko", "en"], default="ko", help="토르켈이 플레이하는 언어")
    judge.set_defaults(func=cmd_judge)
    film = sub.add_parser("video", help="녹화한 시나리오(--record)로 자막 입힌 영상과 단계별 GIF를 만든다")
    film.add_argument("run", type=Path, help="artifacts/native/<시나리오 실행> 폴더")
    film.set_defaults(func=cmd_video)
    sim = sub.add_parser("sim", help="게임 없이 2D 시뮬레이터에서 두뇌를 대화형으로 돌려 본다")
    sim.add_argument("--config", type=Path, default=None)
    sim.add_argument("--time-scale", type=float, default=1.0)
    sim.set_defaults(func=cmd_sim)
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
