"""Wiring: bridge server + body session + controller (+ planner / decisions per config)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from thorkell import lang
from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession
from thorkell.config import Config, secret
from thorkell.control.controller import Controller
from thorkell.decide.runner import Decider, DecisionRunner, RuleDecider, SystemOneDecider
from thorkell.mind.mind import Mind
from thorkell.mind.store import Store
from thorkell.models.gemini import GeminiJson
from thorkell.models.systemone import Backend, SystemOne
from thorkell.plan.planner import Planner, PlannerConfig
from thorkell.plan.tactics import Tactician
from thorkell.talk.live import LiveVoice
from thorkell.world.sight import Eyes

log = logging.getLogger(__name__)


@dataclass
class Brain:
    config: Config
    run_dir: Path
    session: BodySession
    server: BridgeServer
    controller: Controller
    http: httpx.AsyncClient
    voice: LiveVoice | None = None

    async def close(self) -> None:
        await self.server.close()
        await self.http.aclose()


def _deciders(config: Config, http: httpx.AsyncClient) -> dict[str, Decider]:
    shared: dict[str, Decider] = {"rules": RuleDecider()}
    deciders: dict[str, Decider] = {}
    for point in ("threat_response", "speak_worthy", "intent_guard"):
        backend = getattr(config.decide, point)
        if backend not in shared:
            settings = getattr(config.decide, backend)
            key = secret("TYPESAFE_API_KEY") if backend == "jev" else None
            shared[backend] = SystemOneDecider(
                SystemOne(Backend(backend, settings.base_url, settings.model, key), http)
            )
        deciders[point] = shared[backend]
    return deciders


async def build(config: Config, token: str, root: Path, knowledge: Path | None = None) -> Brain:
    """`knowledge`: the world's knowledge DB. None keeps it inside this run's directory (fresh start,
    e.g. the simulator) so simulated learning never mixes into a real world's memory."""
    lang.use(config.language)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = root / config.runs_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    http = httpx.AsyncClient()
    session = BodySession()
    server = BridgeServer(token, session.on_message)
    session.attach(server)
    planner = None
    if config.planner.backend == "gemini":
        planner = Planner(
            GeminiJson(secret("GEMINI_API_KEY")),
            PlannerConfig(model=config.planner.model, thinking=config.planner.thinking),
        )
    decider = DecisionRunner(_deciders(config, http), run_dir / "decisions.jsonl")
    mind = Mind(Store(knowledge or run_dir / "knowledge.sqlite"), leader_name=config.leader.name)
    controller = Controller(
        session,
        leader_name=config.leader.name,
        planner=planner,
        tactician=Tactician(planner.model, planner.config) if planner is not None else None,
        eyes=Eyes(session, GeminiJson(secret("GEMINI_API_KEY")), config.vision)
        if config.vision.backend == "gemini"
        else None,
        decider=decider,
        mind=mind,
    )
    decider.on_breaker_open = lambda: log.error("decision backend failing; autonomy paused for the cooldown")
    return Brain(config, run_dir, session, server, controller, http)


async def serve(brain: Brain, port: int, stop: asyncio.Event) -> None:
    await brain.server.start(port)
    log.info("brain listening on 127.0.0.1:%d, run dir %s", port, brain.run_dir)
    await brain.controller.run(stop)
