from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from thorkell import lang
from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession
from thorkell.control.controller import Controller
from thorkell.models.gemini import Usage
from thorkell.sim.world import SimBody, SimWorld, forest

TOKEN = "4d" * 32


@pytest.fixture
def english() -> Iterator[None]:
    """Thorkell plays this test in English: the (simulated) game's names, what he hears, says and thinks."""
    lang.use("en")
    yield
    lang.use("ko")


class ScriptedModel:
    """Stands in for gemini-3.8-flash: returns prepared JSON objects in order and records prompts."""

    def __init__(self, *responses: dict[str, Any]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.systems: list[str] = []

    async def generate_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        self.prompts.append(prompt)
        self.systems.append(system)
        return self.responses.pop(0), Usage(input_tokens=100, output_tokens=50)


class JudgmentModel:
    """Stands in for gemini-3.8-flash as Thorkell's fight judgment: answers a tactic question with the next
    prepared tactic and a reflection with the next prepared reflection, and records each prompt by kind."""

    def __init__(self, tactics: list[dict[str, Any]], reflections: list[dict[str, Any]]) -> None:
        self.answers = {"tactic": list(tactics), "reflection": list(reflections)}
        self.prompts: dict[str, list[str]] = {"tactic": [], "reflection": []}

    async def generate_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]:
        kind = "tactic" if "style" in schema["properties"] else "reflection"
        self.prompts[kind].append(prompt)
        return self.answers[kind].pop(0), Usage(input_tokens=100, output_tokens=50)


def tactic(**overrides: Any) -> dict[str, Any]:
    """A ranged tactic as the model would answer it."""
    return {
        "impression_ko": "화면 위에 큰 체력바가 떴어. 보스 같아",
        "style": "ranged",
        "keep_m": 24.0,
        "close_m": 14.0,
        "retreat_hp": 0.35,
        "return_hp": 0.7,
        "hits_then_back": 2,
        "eat_first": True,
        "retreat_to_leader": True,
        "dodge_within_m": 0.0,
        "speech_ko": "보스 같아! 멀리서 활로 쏠게",
        "cites": [],
        **overrides,
    }


def reflection(**overrides: Any) -> dict[str, Any]:
    return {
        "what_happened_ko": "싸웠다",
        "lessons": [],
        "verdicts": [],
        "after_death": None,
        "speech_ko": "다음엔 더 잘할게",
        **overrides,
    }


@dataclass
class Rig:
    world: SimWorld
    session: BodySession
    controller: Controller
    tasks: list[asyncio.Task[Any]] = field(default_factory=list)

    async def until(self, predicate: Callable[[], bool], timeout: float = 30) -> None:
        async with asyncio.timeout(timeout):
            while not predicate():
                await asyncio.sleep(0.05)

    def wood(self) -> int:
        return self.world.bot.inventory.get("나무", 0)

    def said(self) -> list[str]:
        return [text for _, text in self.world.said]


@pytest.fixture
async def make_rig() -> AsyncIterator[Callable[..., Any]]:
    stops: list[asyncio.Event] = []
    servers: list[BridgeServer] = []
    tasks: list[asyncio.Task[Any]] = []

    async def build(world: SimWorld | None = None, time_scale: float = 8, **controller_args: Any) -> Rig:
        if world is None:
            world = SimWorld(forest(3))
            world.bot.inventory = {"돌도끼": 1, "곤봉": 1, "라즈베리": 3}
            world.bot.known = set(world.bot.inventory)
        session = BodySession()
        server = BridgeServer(TOKEN, session.on_message)
        session.attach(server)
        await server.start(0)
        stop = asyncio.Event()
        tasks.append(asyncio.create_task(SimBody(world, time_scale=time_scale).run(server.port, TOKEN, stop)))
        await session.wait_for(lambda: session.armed and session.scene is not None, 5)
        controller = Controller(session, **controller_args)
        tasks.append(asyncio.create_task(controller.run(stop)))
        stops.append(stop)
        servers.append(server)
        return Rig(world, session, controller)

    yield build
    for stop in stops:
        stop.set()
    await asyncio.gather(*tasks, return_exceptions=True)
    for server in servers:
        await server.close()
