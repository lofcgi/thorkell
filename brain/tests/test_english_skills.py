"""The skills played in English against the simulator: the body reports the English game's names, and
Thorkell matches them and talks about them in English."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from conftest import JudgmentModel, Rig, reflection, tactic

from thorkell import lang
from thorkell.control.fight import describe_looks
from thorkell.control.goals import Goal, Tier
from thorkell.control.making import _wall_and_roof
from thorkell.mind.mind import Mind
from thorkell.mind.store import Store
from thorkell.plan.tactics import Tactician
from thorkell.sim.world import SimEntity, SimWorld, deer, eikthyr, forest, pickable


def meadow() -> SimWorld:
    """Spawn-like ground: branches and stones lying about, a few trees further off, empty hands, fed."""
    entities: list[SimEntity] = forest(2)
    for index in range(6):
        entities.append(pickable("나뭇가지", ("나무", 1), 3.0 + 2.0 * index, -4.0, f"7:{100 + index}"))
    for index in range(4):
        entities.append(pickable("돌", ("돌", 1), -3.0 - 2.0 * index, 4.0, f"7:{200 + index}"))
    world = SimWorld(entities)
    world.bot.foods = {"라즈베리": 1200.0}
    return world


def offered(mind: Mind) -> list[str]:
    """Lines Thorkell wanted to say on his own: said, still waiting, or let go (self-talk is rate-limited)."""
    speech = mind.speech
    return [line.text for _, line in speech.spoken] + [line.text for line in speech.queue + speech.dropped]


def ended(rig: Rig, kind: str) -> bool:
    return any(d.kind in ("done", "fail") and d.goal_kind == kind for d in rig.controller.decisions)


@pytest.mark.usefixtures("english")
async def test_chops_wood_and_says_how_much_in_english(make_rig: Callable[..., Any]) -> None:
    rig: Rig = await make_rig()
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather", Tier.USER, {"item": "Wood", "count": 5}, source="leader"))
    await rig.until(
        lambda: any(text.startswith("Got ") and text.endswith(" Wood") for text in rig.said()), 60
    )
    assert rig.wood() >= 5


@pytest.mark.usefixtures("english")
async def test_without_an_axe_it_makes_a_hammer_from_branches(make_rig: Callable[..., Any]) -> None:
    # 도끼가 없으면 나무는 나뭇가지에서 얻는다. 처음 보는 나뭇가지는 주워 보고 무엇이 나오는지 배운다.
    world = meadow()
    world.bot.known = {"나무", "돌"}
    mind = Mind(Store())
    rig: Rig = await make_rig(world=world, mind=mind)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("craft", Tier.USER, {"item": "Hammer"}, source="leader"))
    await rig.until(lambda: "Made Hammer" in rig.said(), 90)
    assert rig.world.bot.inventory.get("망치", 0) == 1
    assert not any(e.kind == "log" for e in rig.world.entities.values())  # 나무는 베지 않았다
    assert rig.controller.world is not None
    assert rig.controller.world.sources("Wood")[0] == ("pickable", "Branch")
    assert "So Branch gives Wood." in offered(mind)


@pytest.mark.usefixtures("english")
async def test_gathering_without_a_count_counts_the_bushes_named_after_the_berries(
    make_rig: Callable[..., Any],
) -> None:
    # 영어 이름은 덤불이 단수다("Raspberry Bush"가 "Raspberries"를 준다). 그래도 이름으로 알아본다.
    world = meadow()
    for index in range(3):
        world.spawn(pickable("라즈베리 덤불", ("라즈베리", 1), 5.0, 2.0 + 2.0 * index, f"7:{400 + index}"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("gather", Tier.USER, {"item": "Raspberries"}, source="leader"))
    await rig.until(lambda: "Got 3 Raspberries" in rig.said(), 60)
    assert rig.world.bot.inventory.get("라즈베리", 0) == 3


@pytest.mark.parametrize(
    ("language", "menu", "chosen"),
    [
        (
            "ko",
            [
                "목책 담장",
                "나무 벽 26°",
                "나무 벽",
                "나무 지붕 교차형 26°",
                "초가지붕 용마루 26°",
                "초가지붕 26°",
            ],
            ("나무 벽", "초가지붕 26°"),
        ),
        (
            "en",
            [
                "Stakewall",
                "Wood Wall 26°",
                "Wood Wall",
                "Wood Roof Cross 26°",
                "Thatch Roof Ridge 26°",
                "Thatch Roof 26°",
            ],
            ("Wood Wall", "Thatch Roof 26°"),
        ),
    ],
)
def test_the_same_wall_and_roof_are_chosen_in_either_language(
    language: lang.Language, menu: list[str], chosen: tuple[str, str]
) -> None:
    # 같은 망치 메뉴(게임의 한국어·영어 이름, 모두 나무 2개)에서 같은 벽과 지붕을 고른다.
    pieces = [{"name": name, "resources": [{"name": "x", "amount": 2}]} for name in menu]
    lang.use(language)
    try:
        assert _wall_and_roof(pieces) == chosen
    finally:
        lang.use("ko")


@pytest.mark.usefixtures("english")
async def test_puts_walls_and_a_roof_over_the_workbench_in_english(make_rig: Callable[..., Any]) -> None:
    world = meadow()
    world.bot.inventory = {"나무": 30, "돌": 2, "망치": 1}
    world.bot.known = {"나무", "돌", "망치"}
    world.spawn(SimEntity("7:300", "station", "작업대", 2.0, 0.0, creator="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.stance = "wait"
    rig.controller.request(Goal("shelter", Tier.USER, {}, source="leader"))
    await rig.until(lambda: "Put walls and a roof over the Workbench. I can use it now!" in rig.said(), 60)
    assert rig.world.roofed(2.0, 0.0)
    built = {e.name for e in rig.world.entities.values() if e.creator == "Thorkell"}
    assert {"나무 벽", "초가지붕 26°"} <= built


@pytest.mark.usefixtures("english")
async def test_shoots_a_deer_and_learns_what_it_drops_in_english(make_rig: Callable[..., Any]) -> None:
    world = SimWorld([deer(22.0, 0.0)])
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.inventory = {"활": 1, "나무 화살": 20}
    world.bot.known = {"활", "나무 화살"}
    mind = Mind(Store())
    rig: Rig = await make_rig(world=world, mind=mind)
    rig.controller.request(Goal("hunt", Tier.USER, {"creature": "Deer", "count": 1}, source="leader"))
    await rig.until(lambda: "Caught 1 Deer" in rig.said(), 60)
    assert rig.world.bot.inventory.get("사슴 트로피", 0) == 1
    assert rig.controller.world is not None
    assert ("creature", "Deer") in rig.controller.world.sources("Deer Trophy")
    assert "So Deer drops Deer Trophy." in offered(mind)


@pytest.mark.usefixtures("english")
async def test_cooks_meat_over_a_campfire_it_builds(make_rig: Callable[..., Any]) -> None:
    world = SimWorld([])
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.inventory = {"날고기": 2, "나무": 12, "돌": 6, "망치": 1}
    world.bot.known = set(world.bot.inventory)
    world.spawn(SimEntity("7:300", "station", "작업대", -6.0, 0.0, creator="Thorkell"))
    rig: Rig = await make_rig(world=world)
    rig.controller.request(Goal("cook", Tier.USER, {"item": "Raw Meat", "count": 2}, source="leader"))
    await rig.until(lambda: "Cooked 2 Cooked Meat" in rig.said(), 90)
    assert rig.world.bot.inventory.get("구운 고기", 0) == 2
    assert any(e.kind == "fire" and e.name == "모닥불" for e in rig.world.entities.values())
    assert any(e.kind == "cooking" for e in rig.world.entities.values())


@pytest.mark.usefixtures("english")
async def test_the_english_kill_message_is_a_win_even_unseen(make_rig: Callable[..., Any]) -> None:
    # 쓰러지는 걸 못 봐도 화면 가운데에 "Eikthyr is slain"이 뜬다.
    model = JudgmentModel(
        [tactic(eat_first=False, impression_ko="A big health bar came up.", speech_ko="Bow it is!")],
        [reflection(what_happened_ko="We fought.", speech_ko="Next time I'll do better")],
    )
    world = SimWorld([SimEntity("7:500", "altar", "신비한 제단", 4.0, 0.0)])
    world.bot.inventory = {"사슴 트로피": 2, "활": 1, "나무 화살": 80, "곤봉": 1}
    world.bot.known = set(world.bot.inventory)
    world.bot.foods = {"라즈베리": 1200.0}
    world.bot.hp_max = world.bot.hp = 60.0
    rig: Rig = await make_rig(world=world, time_scale=4, tactician=Tactician(model), mind=Mind(Store()))
    rig.controller.stance = "wait"
    boss = eikthyr(25.0, 0.0)
    boss.speed, boss.ranged_m = 0.0, 0.0
    rig.world.spawn(boss)
    await rig.until(lambda: rig.world.bot.inventory["나무 화살"] < 80, 20)
    boss.hidden, boss.hp = True, 0.1
    rig.world.hit(boss)
    await rig.until(lambda: ended(rig, "fight"), 30)
    assert any(
        d.kind == "done" and d.goal_kind == "fight" and d.reason_ko == "Took down Eikthyr!"
        for d in rig.controller.decisions
    )
    # 판단 모델이 본 것(토르켈 자신의 화면)도 영어다.
    asked = model.prompts["tactic"][0]
    assert "Eikthyr: about 3m tall" in asked
    assert "Food slots" in asked and "Weapons: " in asked


def test_how_a_creature_looks_in_english(english: None) -> None:
    looks = describe_looks(
        {"height_m": 3.0, "top_bar": True, "health": 0.5, "distance": 20.4, "alerted": True}
    )
    assert looks == (
        "about 3m tall, a big health bar and name came up at the top of the screen, health 50%, 20m ahead, "
        "noticed me"
    )
