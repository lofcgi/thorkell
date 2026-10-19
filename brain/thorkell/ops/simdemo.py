"""`thorkell sim`: talk to the brain in a terminal while it drives the 2D simulator.

Lines you type are what the leader says in game chat. Commands: /spawn (a hostile creature nearby),
/state, /quit. Bot speech and controller decisions are printed as they happen.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from thorkell import app
from thorkell.body import auth
from thorkell.config import ConfigError, load
from thorkell.paths import REPO_ROOT, THORKELL_HOME
from thorkell.sim.world import SimBody, SimWorld, forest, greydwarf
from thorkell.talk.audio import AudioError


async def run_sim_demo(config_path: Path | None, time_scale: float) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    try:
        config = load(config_path)
        token = auth.new_hex(32)
        brain = await app.build(config, token, REPO_ROOT / "brain")
    except ConfigError as error:
        print(f"[ERR] {error}")
        return 2

    world = SimWorld(forest(4))
    world.bot.inventory = {"돌도끼": 1, "곤봉": 1, "라즈베리": 3}
    world.bot.known = set(world.bot.inventory)
    stop = asyncio.Event()
    serve = asyncio.create_task(app.serve(brain, 0, stop))
    while brain.server._server is None:
        await asyncio.sleep(0.01)
    body = asyncio.create_task(SimBody(world, time_scale=time_scale).run(brain.server.port, token, stop))
    print(f"시뮬레이터 시작 (planner={config.planner.backend}, threat={config.decide.threat_response}).")
    print("리더로서 말을 입력하세요. 예: '토르켈, 나무 좀 해줘' / '뭐해?' / '토르켈 멈춰'")
    print("명령: /spawn (적 등장) /state (상태) /quit")

    async def echo() -> None:
        said, decided = 0, 0
        while not stop.is_set():
            for talker, text in world.said[said:]:
                print(f"  Thorkell[{talker}]: {text}")
            said = len(world.said)
            for decision in brain.controller.decisions[decided:]:
                if decision.kind != "speak":
                    print(f"  · {decision.kind}: {decision.reason_ko}")
            decided = len(brain.controller.decisions)
            await asyncio.sleep(0.1)

    printer = asyncio.create_task(echo())
    extra: list[asyncio.Task[None]] = []
    if config.voice.backend == "gemini-live":
        from thorkell.talk.wiring import build_voice

        voice, mic, speaker = build_voice(
            config.voice, brain.controller, brain.controller.decider, THORKELL_HOME / "secrets/live.handle"
        )
        try:
            mic.start()
            speaker.start()
        except AudioError as error:
            print(f"[ERR] {error}")
            stop.set()
            await asyncio.gather(serve, body, printer, return_exceptions=True)
            await brain.close()
            return 2
        voice.on_transcript = lambda who, text: print(f"  🎙 {who}: {text}")
        voice.on_down = lambda why: print(f"  [음성 꺼짐] {why} — 채팅으로는 계속 대화할 수 있어요.")
        extra.append(asyncio.create_task(voice.run(stop)))
        print("음성 켜짐: 마이크로 말하면 Thorkell이 대답합니다(헤드폰 권장).")
    try:
        while True:
            line = (await asyncio.to_thread(input, "> ")).strip()
            if line in ("/quit", "/q"):
                break
            if line == "/spawn":
                world.spawn(greydwarf(world.bot.x + 10, world.bot.z + 2))
                print("  (그레이드워프가 나타났다)")
            elif line == "/state":
                b = world.bot
                print(f"  hp {b.hp:.0f}/{b.hp_max:.0f} stamina {b.stamina:.0f} 위치 ({b.x:.1f},{b.z:.1f})")
                print(f"  인벤토리 {b.inventory}")
            elif line:
                world.leader_says(line)
    except EOFError:
        pass
    finally:
        stop.set()
        await asyncio.gather(serve, body, printer, *extra, return_exceptions=True)
        await brain.close()
    print(f"기록: {brain.run_dir}")
    return 0
