"""The controller + skills against the 2D simulator over the real bridge protocol (no model calls)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from thorkell.body.link import BridgeServer
from thorkell.body.session import BodySession
from thorkell.control.controller import Controller
from thorkell.sim.world import SimBody, SimWorld, forest, greydwarf

TOKEN = "4d" * 32


@dataclass
class Rig:
    world: SimWorld
    session: BodySession
    controller: Controller

    async def until(self, predicate: Callable[[], bool], timeout: float = 30) -> None:
        async with asyncio.timeout(timeout):
            while not predicate():
                await asyncio.sleep(0.05)

    def kinds(self) -> list[tuple[str, str]]:
        goals = {}
        for d in self.controller.decisions:
            goals.setdefault(d.goal_id, None)
        return [(d.kind, d.reason_ko) for d in self.controller.decisions]

    def wood(self) -> int:
        return self.world.bot.inventory.get("나무", 0)


@pytest.fixture
async def rig() -> AsyncIterator[Rig]:
    world = SimWorld(forest(3))
    world.bot.inventory = {"돌도끼": 1, "곤봉": 1, "라즈베리": 3}
    world.bot.known = set(world.bot.inventory)
    # 이 파일은 일·중단·재개만 본다: 이미 먹은 상태로 시작해 생존 행동(먹기)이 끼어들지 않게 한다.
    world.bot.foods = {"라즈베리": 1200.0}
    session = BodySession()
    server = BridgeServer(TOKEN, session.on_message)
    session.attach(server)
    await server.start(0)
    stop = asyncio.Event()
    body_task = asyncio.create_task(SimBody(world, time_scale=8).run(server.port, TOKEN, stop))
    await session.wait_for(lambda: session.armed and session.scene is not None, 5)
    controller = Controller(session)
    controller_task = asyncio.create_task(controller.run(stop))
    yield Rig(world, session, controller)
    stop.set()
    await asyncio.gather(body_task, controller_task, return_exceptions=True)
    await server.close()


def said(rig: Rig) -> list[str]:
    return [text for _, text in rig.world.said]


async def test_gathers_requested_wood_and_reports(rig: Rig) -> None:
    rig.world.leader_says("토르켈, 나무 10개 캐줘")
    await rig.until(lambda: any(text.startswith("나무 1") and "모았어" in text for text in said(rig)))
    assert rig.wood() >= 10
    assert "나무 10개 해 올게." in said(rig)
    assert any(d.kind == "done" for d in rig.controller.decisions)


async def test_gathered_count_is_read_from_the_inventory(rig: Rig) -> None:
    # 게임은 2m 안의 아이템을 자동으로 줍는다. 줍기 명령의 증거만 세면 그만큼을 놓치고 필요 이상으로 벤다.
    rig.world.leader_says("토르켈, 나무 10개 캐줘")
    await rig.until(lambda: any(text.startswith("나무 ") and "모았어" in text for text in said(rig)))
    report = next(text for text in said(rig) if text.startswith("나무 ") and "모았어" in text)
    assert report == f"나무 {rig.wood()}개 모았어"
    # 10개를 부탁했고 통나무 하나가 5개를 준다. 20개 이상이면 자동으로 주운 나무를 세지 못한 것이다.
    assert rig.wood() < 20


async def test_after_a_fight_the_leaders_job_comes_before_following(rig: Rig) -> None:
    # 실게임(2026-10-20): 나무를 하다 그레이링과 싸운 뒤, 기다리던 "따라가기"(자기 일)를 먼저 골라
    # 멈춰 둔 리더의 부탁(나무)을 잊었다. 따라가기는 끝나지 않으니 나무는 영영 하지 않았다.
    from thorkell.control.goals import Goal, Tier

    rig.world.leader_says("나무 10개 해줘")
    await rig.until(lambda: rig.controller.current() is not None, 10)
    rig.controller.request(Goal("follow", Tier.AGENDA, source="self"))
    rig.world.at(rig.world.now + 3.0, lambda w: w.spawn(greydwarf(w.bot.x + 8, w.bot.z)))
    await rig.until(
        lambda: any(d.kind == "done" and d.goal_kind == "defend" for d in rig.controller.decisions), 45
    )
    await rig.until(lambda: any(text.startswith("나무 ") and "모았어" in text for text in said(rig)), 60)


async def test_attack_interrupts_gathering_then_it_resumes(rig: Rig) -> None:
    rig.world.leader_says("나무 10개 해줘")
    rig.world.at(rig.world.now + 4.0, lambda w: w.spawn(greydwarf(w.bot.x + 8, w.bot.z)))
    await rig.until(lambda: sum(d.kind == "done" for d in rig.controller.decisions) >= 2, timeout=45)
    flow = [
        (d.kind, d.goal_kind)
        for d in rig.controller.decisions
        if d.goal_kind in ("gather_wood", "defend") and d.kind not in ("speak", "threat")
    ]
    assert flow[:6] == [
        ("adopt", "gather_wood"),
        ("suspend", "gather_wood"),
        ("adopt", "defend"),
        ("done", "defend"),
        ("resume", "gather_wood"),
        ("done", "gather_wood"),
    ]
    assert not rig.world.bot.dead
    assert rig.wood() >= 10
    assert "7:900" not in rig.world.entities
    # Without any knowledge the bot trusts the tooltip numbers (axe slash 14 > club blunt 12),
    # so this first fight shows the creature shrugging off slashes.
    resisted = [e for e in rig.session.events_of("damage_dealt") if e.data["type"] == "resistant"]
    assert resisted, "a first fight without knowledge should show 'resistant' hits from the axe"


async def test_status_question_does_not_interrupt(rig: Rig) -> None:
    rig.world.leader_says("나무 10개 캐줘")
    await rig.until(lambda: rig.controller.current() is not None)
    await asyncio.sleep(0.3)
    rig.world.leader_says("토르켈 뭐해?")
    await rig.until(lambda: any(d.kind == "done" for d in rig.controller.decisions))
    assert any(text.startswith("나무 모으기 (") for text in said(rig))
    assert not any(d.kind == "suspend" for d in rig.controller.decisions)


async def test_stop_phrase_drops_work_quickly(rig: Rig) -> None:
    rig.world.leader_says("나무 30개 캐줘")
    await rig.until(lambda: rig.world.active is not None)
    rig.world.leader_says("토르켈 멈춰")
    loop = asyncio.get_running_loop()
    began = loop.time()
    await rig.until(lambda: rig.controller.current() is None and "알겠어, 멈출게." in said(rig), timeout=3)
    assert loop.time() - began < 1.5
    assert any(d.kind == "drop" for d in rig.controller.decisions)
    await asyncio.sleep(0.5)
    assert rig.world.active is None


async def test_takes_what_the_leader_hands_over_and_uses_it(rig: Rig) -> None:
    rig.world.bot.inventory = {}
    rig.world.bot.equipped = None
    rig.world.leader_drops("돌도끼")
    rig.world.leader_says("토르켈, 이 도끼 받아")
    await rig.until(lambda: any("받았어" in text for text in said(rig)))
    assert rig.world.bot.inventory.get("돌도끼") == 1
    rig.world.leader_says("나무 5개 캐줘")
    await rig.until(lambda: any(text.startswith("나무 ") and "모았어" in text for text in said(rig)), 60)
    assert rig.wood() >= 5


async def test_replies_are_shouted_when_the_leader_is_out_of_earshot(rig: Rig) -> None:
    # 게임의 일반 채팅은 15m 안에서만 보인다. 멀리 있는 리더에게는 외쳐야 답이 닿는다.
    # 리더 곁으로 가는 기본 자세가 거리를 바꾸지 않게 제자리에 둔다.
    rig.controller.stance = "wait"
    rig.world.leader = (60.0, 0.0)
    rig.world.leader_says("뭐해?")
    await rig.until(lambda: bool(rig.world.said))
    assert rig.world.said[-1][0] == "shout"
    rig.world.leader = (3.0, 0.0)
    # 리더가 다가온 것은 다음 장면(초당 두 번)에서야 보인다.
    await rig.until(lambda: rig.controller._leader_within(14.0))
    rig.world.leader_says("뭐해?")
    await rig.until(lambda: len(rig.world.said) >= 2)
    assert rig.world.said[-1][0] == "normal"


async def test_leader_chat_can_come_only_through_the_host(make_rig: Callable[..., Any]) -> None:
    # 실전에서는 사람 게임(호스트)이 리더의 말을 직접 넘긴다.
    # 봇이 가까이서 같은 말을 들어도 두 번 처리하지 않는다.
    rig = await make_rig(leader_chat_via_host=True)

    def status_replies() -> int:
        return sum(d.kind == "speak" and d.reason_ko.startswith("[status]") for d in rig.controller.decisions)

    rig.world.leader_says("뭐해?")
    await asyncio.sleep(1.0)
    assert status_replies() == 0
    await rig.controller.hear_leader("뭐해?")
    await rig.until(lambda: status_replies() == 1)


async def test_words_through_the_host_are_remembered(make_rig: Callable[..., Any]) -> None:
    # 호스트로 들어온 리더의 말도 대화 기억에 남는다. 안 남으면 플래너와 싸움 판단이 리더의 말을 모른다.
    from thorkell.mind.mind import Mind
    from thorkell.mind.store import Store

    rig = await make_rig(leader_chat_via_host=True, mind=Mind(Store()))
    await rig.controller.hear_leader("나는 멀리서 볼게")
    assert ("Leader", "나는 멀리서 볼게") in rig.controller.mind.store.recent_utterances()


async def test_follows_a_far_leader_found_on_the_map(rig: Rig) -> None:
    # 실게임: 토르켈이 시작 제단에 스폰했고 리더는 멀리 있었다. 리더 캐릭터는 가까이 와야 로드되므로
    # 장면에 리더가 없고, 지도에 공개된 위치만 보인다. 그 위치로 다가가다가 보이면 평소처럼 따라간다.
    rig.world.leader = (250.0, 160.0)
    rig.world.leader_says("따라와")
    await rig.until(lambda: any(text.startswith("지도에서 너를 찾았어") for text in said(rig)), 10)
    found = next(text for text in said(rig) if text.startswith("지도에서"))
    assert "북동쪽 300m" in found
    await rig.until(lambda: rig.world.distance(*rig.world.leader) <= 4.5, 60)
    goal = rig.controller.current()
    assert goal is not None and goal.kind == "follow"


async def test_far_leader_hidden_on_the_map_is_asked_to_share_it(rig: Rig) -> None:
    rig.world.leader = (250.0, 160.0)
    rig.world.leader_public = False
    rig.world.leader_says("따라와")
    await rig.until(lambda: any("위치 공개" in text for text in said(rig)), 10)
    assert rig.world.distance(*rig.world.leader) > 290


async def test_idle_companion_returns_to_the_leader_unless_told_to_wait(rig: Rig) -> None:
    rig.world.leader = (30.0, 0.0)
    await rig.until(lambda: (goal := rig.controller.current()) is not None and goal.kind == "follow", 10)
    await rig.until(lambda: rig.world.distance(*rig.world.leader) < 6, 20)
    rig.world.leader_says("기다려")
    await rig.until(lambda: (goal := rig.controller.current()) is not None and goal.kind == "wait", 5)
    rig.world.leader = (60.0, 0.0)
    await asyncio.sleep(1.5)
    assert (goal := rig.controller.current()) is not None and goal.kind == "wait"


async def test_after_dying_it_walks_back_and_takes_its_things_from_the_tombstone(rig: Rig) -> None:
    rig.world.bot.x, rig.world.bot.z = 25.0, 5.0
    rig.world.die()
    await rig.until(lambda: "아… 죽었어. 다시 일어났어. 내 물건 찾으러 갈게." in said(rig), 15)
    await rig.until(lambda: rig.world.bot.inventory.get("돌도끼", 0) == 1, 40)
    assert not any(e.kind == "tombstone" for e in rig.world.entities.values())
    await rig.until(lambda: "내 물건 다 찾았어. 다시 갈 수 있어!" in said(rig), 10)


async def test_a_food_the_body_refuses_is_not_retried_in_a_loop(rig: Rig) -> None:
    # 실게임(2026-10-17): 날고기는 음식 수치가 있지만 먹을 수 없다. 먹기에 실패하고도 "먹었어"라고 하며
    # 몇 분 동안 수천 번 다시 시도해서 다른 일을 전혀 못 했다.
    rig.world.bot.foods = {}
    rig.world.bot.inventory = {"상한 고기": 3}
    decisions = rig.controller.decisions
    await rig.until(lambda: any(d.kind == "fail" and d.goal_kind == "eat" for d in decisions), 10)
    await asyncio.sleep(2.0)
    tries = [d for d in rig.controller.decisions if d.kind == "adopt" and d.goal_kind == "eat"]
    assert len(tries) == 1
    failed = next(d for d in rig.controller.decisions if d.kind == "fail" and d.goal_kind == "eat")
    assert "먹었어" not in failed.reason_ko


async def test_after_eating_it_does_not_try_the_same_food_again(rig: Rig) -> None:
    # 실게임(2026-10-17): 먹은 직후 장면이 갱신되기 전에 같은 음식을 또 골라 "지금 못 먹겠어"라고 말했다.
    # 다친 상태(체력 40% 아래)라 세 칸을 연달아 채운다.
    rig.world.bot.hp = 5.0
    rig.world.bot.foods = {}
    rig.world.bot.inventory = {"구운 고기": 2, "버섯": 2, "라즈베리": 2}
    await rig.until(lambda: len(rig.world.bot.foods) == 3, 15)
    await asyncio.sleep(1.0)
    assert not any("못 먹겠어" in text for text in said(rig))


async def test_an_attacker_that_runs_off_is_not_reported_as_killed(rig: Rig) -> None:
    # 시뮬레이터(2026-10-17): 보스가 장면에 뜨기 전에 맞자 방어를 시작했고,
    # 상대가 안 보이니 "해치웠어"라고 했다.
    # 쓰러지는 것을 봐야 해치운 것이다.
    dwarf = rig.world.spawn(greydwarf(rig.world.bot.x + 3, rig.world.bot.z))
    dwarf.hp = dwarf.max_hp = 1000.0
    await rig.until(
        lambda: any(d.kind == "adopt" and d.goal_kind == "defend" for d in rig.controller.decisions)
    )
    dwarf.x, dwarf.hostile = dwarf.x + 300, False
    await rig.until(
        lambda: any(d.kind in ("done", "fail") and d.goal_kind == "defend" for d in rig.controller.decisions),
        20,
    )
    assert not any("해치웠어" in d.reason_ko for d in rig.controller.decisions)
    assert "7:900" in rig.world.entities
