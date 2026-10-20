"""A small 2D stand-in for Thorkell.Body + Valheim that speaks the real bridge protocol.

It exists to test the brain (controller, skills, later planner/decisions/learning) without the game.
It is not a Valheim model: just enough mechanics — walking, trees -> logs -> wood, pickups, food,
hostile creatures that chase and hit, weapons with hidden damage multipliers, day/night — following
the same command/event contracts as plugin/Thorkell.Body (ack -> progress -> result, event kinds).
"""

from __future__ import annotations

import asyncio
import itertools
import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from thorkell import lang
from thorkell.body import auth
from thorkell.sim import english

STOP_PHRASE = re.compile(r"(thorkell|토르켈).{0,8}(stop|멈춰|그만|정지)", re.IGNORECASE)
WEAPON_TYPES = {"OneHandedWeapon", "TwoHandedWeapon", "Bow", "Tool"}
# plugin/Thorkell.Body Primitives.IsInstant과 같다: 모터를 쓰지 않는 명령은 반사 중에도 바로 실행된다.
INSTANT_OPS = {"say", "equip", "unequip", "eat"}
# 누워 있을 때 이 명령들은 몸을 일으키지 않는다. 나머지(걷기·싸우기·짓기 등)는 일으킨다
# (게임: 움직이면 AttachStop).
STAY_IN_BED_OPS = {"say", "wait", "look_at", "interact"}
BOT_NAME = "Thorkell"
# 게임 Bed: 침대 주인 이름은 가까이서 침대에 커서를 올리면 보인다. 불의 열기(Heat) 영역은 8m다.
BED_LABEL_M = 8.0
BED_FIRE_M = 8.0
# 지은 것의 반지름(가운데에서 겉면까지, m). 작업대는 폭 3m다.
FOOTPRINT_M = {"station": 1.5, "fire": 0.6, "cooking": 0.5, "bed": 1.0}
# 요리대는 불 바로 위여야 한다(게임: 불 영역 0.45m + 확인 반경 0.25m).
FIRE_UNDER_M = 0.6
# 두뇌가 싸움을 넘겨받는 명령(Body BodyLink.Dispatch). 반사를 바로 놓는다.
FIGHT_OPS = {"attack", "shoot", "dodge"}
# 게임의 자동 줍기(Player.AutoPickup): 발에서 1m 위를 중심으로 2m 안의 아이템을 줍는다.
# 바닥에 놓인 아이템이면 수평 거리 약 1.7m다.
AUTO_PICKUP_RADIUS = 1.7
# 리더 캐릭터가 봇 클라이언트에 로드되는 거리. 게임의 시뮬레이션 거리 기본값은 64m 구역 ±2개라
# 축 방향으로 약 160m다(설정에 따라 350m까지).
LEADER_LOADED_M = 160.0


# 웅크리고 다가가면 겁 많은 동물이 알아채는 거리가 이만큼으로 준다(게임의 은신).
SNEAK_NOTICE = 0.1


@dataclass(frozen=True)
class ItemSpec:
    name: str
    type: str
    weight: float
    damage: dict[str, float] = field(default_factory=dict)
    reach: float = 0.0
    tier: int = 0
    food: tuple[float, float, float] | None = None  # health, stamina, duration_s


ITEMS = {
    spec.name: spec
    for spec in (
        ItemSpec("돌도끼", "OneHandedWeapon", 2.0, {"chop": 20.0, "slash": 14.0}, 2.2, tier=1),
        ItemSpec("곤봉", "OneHandedWeapon", 2.0, {"blunt": 12.0}, 2.2),
        ItemSpec("나무", "Material", 2.0),
        ItemSpec("돌", "Material", 2.0),
        ItemSpec("가죽 조각", "Material", 0.5),
        ItemSpec("라즈베리", "Consumable", 0.1, food=(7.0, 20.0, 600.0)),
        ItemSpec("버섯", "Consumable", 0.1, food=(15.0, 15.0, 900.0)),
        ItemSpec("구운 고기", "Consumable", 1.0, food=(30.0, 10.0, 1200.0)),
        ItemSpec("날고기", "Material", 1.0),
        # 음식 수치는 있는데 먹을 수 없는 것(시험용): 몸이 거절하는 경우를 흉내 낸다.
        ItemSpec("상한 고기", "Consumable", 1.0, food=(20.0, 20.0, 600.0)),
        ItemSpec("부싯돌", "Material", 1.0),
        ItemSpec("수지", "Material", 0.3),
        ItemSpec("사슴 가죽", "Material", 1.0),
        ItemSpec("사슴 트로피", "Trophy", 2.0),
        ItemSpec("망치", "Tool", 2.0, {"blunt": 6.0}, 1.8),
        ItemSpec("횃불", "Torch", 1.0, {"fire": 4.0, "blunt": 4.0}, 1.8),
        ItemSpec("활", "Bow", 1.0, {"pierce": 22.0}, 0.0),
        ItemSpec("나무 화살", "Ammo", 0.1),
        ItemSpec("숯", "Material", 1.0),
        ItemSpec("에이크쉬르 트로피", "Trophy", 2.0),
    )
}


@dataclass(frozen=True)
class RecipeSpec:
    """Like ObjectDB recipes: known once every resource has been held (Player.UpdateKnownRecipesList)."""

    name: str
    resources: dict[str, int]
    station: str | None = None
    amount: int = 1


RECIPES = {
    r.name: r
    for r in (
        RecipeSpec("망치", {"나무": 3, "돌": 2}),
        RecipeSpec("돌도끼", {"나무": 5, "돌": 4}),
        RecipeSpec("곤봉", {"나무": 6}),
        RecipeSpec("횃불", {"나무": 1, "수지": 1}),
        RecipeSpec("활", {"나무": 10, "가죽 조각": 8}, station="작업대"),
        RecipeSpec("나무 화살", {"나무": 8}, station="작업대", amount=20),
    )
}


@dataclass(frozen=True)
class PieceSpec:
    """A hammer piece. `kind` is the scene kind the built piece shows up as."""

    name: str
    resources: dict[str, int]
    kind: str
    station: str | None = "작업대"


PIECES = {
    p.name: p
    for p in (
        PieceSpec("작업대", {"나무": 10}, "station", station=None),
        PieceSpec("모닥불", {"돌": 5, "나무": 2}, "fire", station=None),
        PieceSpec("나무 벽", {"나무": 2}, "piece"),
        PieceSpec("초가지붕 26°", {"나무": 2}, "piece"),
        PieceSpec("나무 문", {"나무": 4}, "door"),
        PieceSpec("침대", {"나무": 8}, "bed"),
        PieceSpec("요리대", {"나무": 2}, "cooking"),
    )
}
# 작업대는 지붕 아래에서만 쓸 수 있다(CraftingStation.m_craftRequireRoof).
# 시뮬레이터에서는 4m 안의 지붕 조각으로 본다.
ROOF_RADIUS = 4.0
MORNING = 0.26
STATION_RANGE = 20.0
PLACE_REACH = 5.0
COOK_SECONDS = 25.0
BURN_SECONDS = 50.0
# 생물 이름표(EnemyHud)가 보이는 거리. 게임은 쳐다본(조준한) 생물에게만 띄우고 몸(Attention)은 시야의 생물을
# 잠깐씩 쳐다본다. 시뮬레이터는 이 거리 안이면 쳐다본 것으로 친다. 그 밖에서는 종류 키와 덩치만 보인다.
HUD_RADIUS = 30.0
# look 질의에 돌려주는 자리표시 그림(base64). 시뮬레이터는 화면을 그리지 않는다.
SIM_FRAME = "c2ltLWZyYW1l"
# 포털 가운데 이만큼 안에 들어서면 건너간다.
PORTAL_STEP_M = 0.8
# 몸이 주변을 보는 거리(Body Scanner.Range). 큰 생물은 더 멀리서도 보인다(LargeRange).
SCENE_RANGE_M = 40.0
LARGE_SCENE_RANGE_M = 100.0
# 알아챈 보스의 체력바가 화면 위쪽에 뜨는 거리(EnemyHud, Parity.BossHudRadius). 가려져도 뜬다.
BOSS_BAR_M = 100.0
# 공격 동작이 보이고 나서 맞기까지(게임 시간 초). 그사이 구르면 빗나간다.
WIND_UP_S = 0.6
# 활을 당기며 걷는 속도(m/s)
DRAW_WALK_SPEED = 2.5
UNARMED = ItemSpec("맨손", "Unarmed", 0.0, {"blunt": 4.0}, 1.6)


@dataclass
class SimEntity:
    id: str
    kind: str
    name: str
    x: float
    z: float
    hp: float = 1.0
    max_hp: float = 1.0
    tier: int = 0
    multipliers: dict[str, float] = field(default_factory=dict)  # hidden from the brain
    drops: list[tuple[str, int]] = field(default_factory=list)
    becomes: list[tuple[str, str, float, list[tuple[str, int]]]] = field(default_factory=list)
    hostile: bool = False
    damage: float = 0.0
    speed: float = 0.0
    aggro: float = 0.0
    next_attack: float = 0.0
    stack: int = 1
    # 플레이어가 버린 아이템은 게임이 자동으로 줍지 않는다(ItemDrop.OnPlayerDrop).
    auto_pickup: bool = True
    # 생물: 종류 키(로컬라이즈 토큰), 덩치, 겁이 많은가(사슴처럼 다가오면 달아남).
    key: str = ""
    size: str = "medium"
    height: float = 1.5
    # 보스: 알아채면 체력바가 화면 위쪽에 뜬다. 멀리서 던지는 공격(에이크쉬르의 번개)이 닿는 거리와 피해.
    boss: bool = False
    ranged_m: float = 0.0
    ranged_damage: float = 0.0
    skittish: float = 0.0
    provoked: bool = False
    # 공격 동작 중: (맞는 시각, 피해 종류, 피해, 동작을 시작할 때까지 봇이 구른 횟수)
    winding: tuple[float, str, float, int] | None = None
    # 시험용 가림(나무·언덕 뒤). 시뮬레이터에는 시야 계산이 없어서 직접 정한다.
    hidden: bool = False
    # 시험용: 이 자리(3m 안)에서는 보이긴 해도 화살 길이 막힌다(나무 사이로 보이는 것).
    cover_from: tuple[float, float] | None = None
    # 시험용: 보이지만 다가갈 수 없다(바위 틈에 낀 통나무). Body MoveTo처럼 막혔다(blocked)고 돌아온다.
    unreachable: bool = False
    # 건축물: 지은 사람. 줍는 것(pickable): 주우면 생기는 아이템.
    creator: str = ""
    # 포털: 이름표와 이어진 다른 포털(id). 걸어 들어가면 그 포털 앞으로 나온다(Body: TeleportWorld).
    tag: str = ""
    partner: str | None = None
    gives: tuple[str, int] | None = None
    # 묘비에 든 물건
    stored: dict[str, int] = field(default_factory=dict)
    # 모닥불 연료, 요리대에 올린 날고기(올린 시각)
    fuel: float = 0.0
    cooking: list[float] = field(default_factory=list)
    # 침대 주인(이름). 비어 있으면 아무나 차지할 수 있다.
    owner: str = ""


@dataclass
class Bot:
    x: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    hp: float = 25.0
    hp_max: float = 25.0
    stamina: float = 50.0
    stamina_max: float = 50.0
    inventory: dict[str, int] = field(default_factory=dict)
    equipped: str | None = None
    foods: dict[str, float] = field(default_factory=dict)
    known: set[str] = field(default_factory=set)
    dead: bool = False
    last_hurt: float = -1e9
    in_bed: bool = False
    # 활 내구도: 남은 발수(None이면 닳지 않는다). 0이면 부서져서 못 쓴다(게임은 내구도 0인 무기를 못 쓴다).
    bow_uses: int | None = None
    # 웅크림(몰래 걷기). Body처럼 move_to/attack의 sneak이 정하고, 치고 나면 일어선다.
    crouching: bool = False
    # 도구가 닳는 것: 이름별로 지금 쓰는 것이 몇 번 더 휘두르면 부러지는지(없으면 닳지 않는다). 부러진 것은
    # broken으로 옮겨 가방에 내구도 0으로 남고, 게임처럼 손에 들 수 없다. 새로 만든 것은 처음 값부터 닳는다.
    wear: dict[str, int] = field(default_factory=dict)
    wear_full: dict[str, int] = field(default_factory=dict)
    broken: dict[str, int] = field(default_factory=dict)


@dataclass
class _Running:
    cmd: dict[str, Any]
    action: _SimAction
    started: float


class _SimAction:
    phase = "running"

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        raise NotImplementedError

    def progress(self, world: SimWorld) -> dict[str, Any]:
        return {"phase": self.phase}

    def stop(self, world: SimWorld) -> None:
        """Body IAction.Stop: what the action leaves behind when it ends."""


class SimWorld:
    """World state + body behaviour. `step(dt)` advances simulated time; the protocol loop calls it."""

    def __init__(
        self, seed_entities: list[SimEntity] | None = None, leader_at: tuple[float, float] = (6.0, 0.0)
    ):
        self.bot = Bot()
        self.leader = leader_at
        # 리더가 지도에서 위치 공개를 켰는가. 멀어서 보이지 않을 때 지도로만 위치를 알 수 있다.
        self.leader_public = True
        self.leader_facing = 0.0  # 북 0°, 동 90° (Body Snapshot leader.facing)
        self.leader_in_bed = False
        self.entities: dict[str, SimEntity] = {e.id: e for e in seed_entities or []}
        self.now = 0.0
        self.dt = 0.0
        self.day_fraction = 0.3
        self.day_length = 1800.0
        self.said: list[tuple[str, str]] = []
        self.dodges = 0
        self.commands: dict[str, int] = {}
        # 시험용: 땅의 높낮이(m). 집터 찾기가 이것보다 엄격하면 터를 못 찾는다.
        self.ground_relief = 0.0
        self.outbox: list[dict[str, Any]] = []
        self.active: _Running | None = None
        self.queued: _Running | None = None
        self.schedule: list[tuple[float, Callable[[SimWorld], None]]] = []
        self._ids = itertools.count(1000)
        # self_defense reflex, like plugin/Thorkell.Body/Reflex/Reflexes.cs
        self.reflex_attacker: str | None = None
        self._stamina_seen = 0.0
        self._stamina_used_at = -1e9
        self.reflex_hit_at = -1e9
        self.reflex_next_swing = 0.0
        self.brain_fighting_until = -1e9

    # --- helpers ---------------------------------------------------------------------------
    def new_id(self) -> str:
        return f"7:{next(self._ids)}"

    def emit(self, t: str, **body: Any) -> None:
        self.outbox.append({"t": t, **body})

    def event(self, kind: str, data: dict[str, Any]) -> None:
        self.emit("event", kind=kind, tick=int(self.now * 30), data=data)

    def distance(self, x: float, z: float) -> float:
        return math.hypot(x - self.bot.x, z - self.bot.z)

    def weapon(self) -> ItemSpec:
        if self.bot.equipped and self.bot.inventory.get(self.bot.equipped, 0) > 0:
            return ITEMS[self.bot.equipped]
        return UNARMED

    def add_item(self, name: str, count: int) -> None:
        self.bot.inventory[name] = self.bot.inventory.get(name, 0) + count
        if name not in self.bot.known:
            self.bot.known.add(name)
            self.event("item_discovered", {"name": name, "type": ITEMS[name].type})

    def known_recipes(self) -> list[RecipeSpec]:
        return [r for r in RECIPES.values() if set(r.resources) <= self.bot.known]

    def known_pieces(self) -> list[PieceSpec]:
        if not any(ITEMS[n].type == "Tool" and n == "망치" for n, c in self.bot.inventory.items() if c > 0):
            return []
        return [p for p in PIECES.values() if set(p.resources) <= self.bot.known]

    def has(self, resources: dict[str, int], times: int = 1) -> bool:
        return all(self.bot.inventory.get(n, 0) >= c * times for n, c in resources.items())

    def missing(self, resources: dict[str, int], times: int = 1) -> list[dict[str, Any]]:
        return [
            {"name": n, "need": c * times, "have": self.bot.inventory.get(n, 0)}
            for n, c in resources.items()
            if self.bot.inventory.get(n, 0) < c * times
        ]

    def consume(self, resources: dict[str, int], times: int = 1) -> None:
        for name, count in resources.items():
            self.bot.inventory[name] -= count * times

    def roofed(self, x: float, z: float) -> bool:
        """A roof piece over it and at least three walls around (the game's cover rays need both)."""
        near = [
            e
            for e in self.entities.values()
            if e.kind == "piece" and math.hypot(e.x - x, e.z - z) <= ROOF_RADIUS
        ]
        return any("지붕" in e.name for e in near) and sum("벽" in e.name for e in near) >= 3

    def station_near(self, name: str) -> bool:
        return any(
            e.kind == "station" and e.name == name and self.distance(e.x, e.z) <= STATION_RANGE
            for e in self.entities.values()
        )

    def query(self, what: str, args: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if what == "look":
            # 시뮬레이터에는 그림이 없다. 화면 이해는 시험에서 대역 모델이 맡는다(모양은 Body Sight.Look).
            turns = (args or {}).get("turn") or [0]
            frames = [{"jpeg": SIM_FRAME, "yaw": self.bot.yaw + float(t), "pitch": 0.0} for t in turns]
            return {"frames": frames, "width": 640, "height": 360, "fov": 65.0, "ms": 1}
        if what == "recipes":
            return {
                "recipes": [
                    {
                        "name": r.name,
                        "amount": r.amount,
                        "station": r.station,
                        "station_level": 1,
                        "resources": [
                            {"name": n, "amount": c, "have": self.bot.inventory.get(n, 0)}
                            for n, c in r.resources.items()
                        ],
                        "have_materials": self.has(r.resources),
                        "type": ITEMS[r.name].type,
                    }
                    for r in self.known_recipes()
                ]
            }
        if what == "site":
            # 시뮬레이터 땅의 높낮이는 어디나 ground_relief다(Body처럼 max_relief 기준, 기본 0.4m).
            x, z = self.bot.x + 3.0, self.bot.z + 3.0
            if self.ground_relief >= float((args or {}).get("max_relief", 0.4)):
                return {"sites": []}
            return {"sites": [{"pos": [x, 0.0, z], "relief_m": self.ground_relief}]}
        if what == "pieces":
            return {
                "pieces": [
                    {
                        "name": p.name,
                        "tool": "망치",
                        "category": "Misc",
                        "station": p.station,
                        "resources": [
                            {"name": n, "amount": c, "have": self.bot.inventory.get(n, 0)}
                            for n, c in p.resources.items()
                        ],
                        "have_materials": self.has(p.resources),
                    }
                    for p in self.known_pieces()
                ]
            }
        return None

    def pick_up(self, entity: SimEntity) -> None:
        del self.entities[entity.id]
        self.add_item(entity.name, entity.stack)
        message = {"where": "top_left", "text": f"추가됨 {entity.name}", "amount": entity.stack}
        self.event("game_message", message)

    def spawn(self, entity: SimEntity) -> SimEntity:
        self.entities[entity.id] = entity
        return entity

    def leader_drops(self, name: str, count: int = 1) -> SimEntity:
        """The leader puts an item down at their feet (how a player hands something over)."""
        x, z = self.leader
        return self.spawn(
            SimEntity(self.new_id(), "item", name, x + 0.6, z + 0.6, stack=count, auto_pickup=False)
        )

    def leader_falls(self, respawn_at: tuple[float, float] = (0.0, -300.0)) -> None:
        """The leader dies: the body drops where they stood (Body `creature_died` with the leader's id), and
        they come back at the spawn far away."""
        x, z = self.leader
        if self.distance(x, z) <= LEADER_LOADED_M:
            self.event("creature_died", {"id": "7:1", "size": "medium", "pos": [x, 0.0, z]})
        self.leader = respawn_at

    def leader_says(self, text: str, talker: str = "normal") -> None:
        data: dict[str, Any] = {"from": "Leader", "talker": talker, "text": text, "distance": 6.0}
        if STOP_PHRASE.search(text):
            self.stop_all("chat_stop_phrase")
            data["stop_phrase"] = True
        self.event("chat", data)

    def at(self, sim_time: float, action: Callable[[SimWorld], None]) -> None:
        self.schedule.append((sim_time, action))
        self.schedule.sort(key=lambda entry: entry[0])

    # --- commands ---------------------------------------------------------------------------
    def submit(self, cmd: dict[str, Any]) -> None:
        self.commands[cmd["op"]] = self.commands.get(cmd["op"], 0) + 1
        if self.bot.dead:
            self.emit("ack", cmd_id=cmd["id"], accepted=False, code="not_armed")
            return
        try:
            action = _make(cmd["op"], cmd["args"])
        except ValueError as error:
            self.emit("ack", cmd_id=cmd["id"], accepted=False, code=str(error))
            return
        if self.bot.in_bed and cmd["op"] not in STAY_IN_BED_OPS:
            self.bot.in_bed = False
        if cmd["op"] in INSTANT_OPS:
            self.emit("ack", cmd_id=cmd["id"], accepted=True, code="ok")
            status, code, evidence = action.tick(self, self.now) or (
                "failed",
                "instant_op_did_not_finish",
                {},
            )
            self.emit("result", cmd_id=cmd["id"], status=status, code=code, evidence=evidence)
            return
        if cmd["op"] in FIGHT_OPS:
            self.brain_fighting_until = self.now + 2.5
            if self.reflex_attacker is not None:
                self._release_reflex()
        elif self.reflex_attacker is not None:
            # Body ActionRunner와 같다: 반사가 몸을 잡고 있으면 다른 명령은 바로 밀렸다고 알린다.
            self.emit("ack", cmd_id=cmd["id"], accepted=True, code="ok")
            self.emit("result", cmd_id=cmd["id"], status="preempted", code="self_defense", evidence={})
            return
        running = _Running(cmd, action, self.now)
        if cmd.get("mode", "replace") == "queue" and self.active is not None:
            self.emit("ack", cmd_id=cmd["id"], accepted=True, code="queued")
            if self.queued is not None:
                self._result(self.queued, "cancelled", "superseded", {})
            self.queued = running
            return
        self.emit("ack", cmd_id=cmd["id"], accepted=True, code="ok")
        if self.active is not None:
            self._finish("cancelled", "replaced", {})
        self.active = running

    def cancel(self, cmd_id: str, reason: str) -> None:
        if self.active is not None and self.active.cmd["id"] == cmd_id:
            self._finish("cancelled", reason, {})
        elif self.queued is not None and self.queued.cmd["id"] == cmd_id:
            self._result(self.queued, "cancelled", reason, {})
            self.queued = None

    def stop_all(self, reason: str) -> None:
        if self.queued is not None:
            self._result(self.queued, "cancelled", reason, {})
            self.queued = None
        if self.active is not None:
            self._finish("cancelled", reason, {})

    def _result(self, running: _Running, status: str, code: str, evidence: dict[str, Any]) -> None:
        self.emit("result", cmd_id=running.cmd["id"], status=status, code=code, evidence=evidence)

    def _finish(self, status: str, code: str, evidence: dict[str, Any]) -> None:
        assert self.active is not None
        evidence = {**evidence, "duration_ms": int((self.now - self.active.started) * 1000)}
        self._result(self.active, status, code, evidence)
        self.active.action.stop(self)
        self.active = None
        if self.queued is not None:
            self.active, self.queued = self.queued, None
            self.active.started = self.now

    # --- simulation -------------------------------------------------------------------------
    def step(self, dt: float) -> None:
        self.dt = dt
        self.now += dt
        while self.schedule and self.schedule[0][0] <= self.now:
            _, action = self.schedule.pop(0)
            action(self)
        was_night = self.night
        self.day_fraction = (self.day_fraction + dt / self.day_length) % 1.0
        if self.night != was_night:
            self.event("env_changed", {"night": self.night})
        if self.bot.in_bed and self.leader_in_bed and self.can_sleep:
            # 서버 Game.UpdateSleeping: 모든 플레이어가 누우면 아침으로 넘기고 모두 깨운다.
            self.day_fraction = MORNING
            self.bot.in_bed = self.leader_in_bed = False
            self.event("env_changed", {"night": False})
            self.event("game_message", {"where": "center", "text": "좋은 아침입니다", "amount": 0})
        for name in list(self.bot.foods):
            self.bot.foods[name] -= dt
            if self.bot.foods[name] <= 0:
                del self.bot.foods[name]
        if self.reflex_attacker is not None:
            self._reflex()
        elif self.active is not None and not self.bot.dead:
            outcome = self.active.action.tick(self, self.now)
            if outcome is not None:
                self._finish(*outcome)
        if not self.bot.dead:
            self._auto_pickup()
        # 게임처럼 스태미나는 마지막으로 쓴 지 1초가 지나면 무엇을 하든 다시 찬다(달리기·공격·구르기가 쓴다).
        if self.bot.stamina < self._stamina_seen:
            self._stamina_used_at = self.now
        if self.now - self._stamina_used_at > 1.0:
            self.bot.stamina = min(self.bot.stamina_max, self.bot.stamina + 12 * dt)
        self._stamina_seen = self.bot.stamina
        if not self.bot.dead and self.now - self.bot.last_hurt > 5:
            regen = 0.3 * (1 + len(self.bot.foods)) * dt
            self.bot.hp = min(self.bot.hp_max, self.bot.hp + regen)
        self._creatures(dt)
        self._portals()
        for entity in self.entities.values():
            if entity.kind == "fire" and entity.fuel > 0:
                entity.fuel = max(0.0, entity.fuel - dt / 60.0)

    def _portals(self) -> None:
        """Like the game: stepping into a connected portal's middle comes out in front of the other one."""
        if self.bot.dead:
            return
        for portal in list(self.entities.values()):
            if portal.kind != "portal" or portal.partner not in self.entities:
                continue
            if self.distance(portal.x, portal.z) <= PORTAL_STEP_M:
                other = self.entities[portal.partner]
                self.bot.x, self.bot.z = other.x + PORTAL_STEP_M * 3, other.z
                return

    def _auto_pickup(self) -> None:
        for entity in list(self.entities.values()):
            if (
                entity.kind == "item"
                and entity.auto_pickup
                and self.distance(entity.x, entity.z) <= AUTO_PICKUP_RADIUS
            ):
                self.pick_up(entity)

    @property
    def night(self) -> bool:
        return self.day_fraction < 0.25 or self.day_fraction > 0.75

    @property
    def can_sleep(self) -> bool:
        """EnvMan.CanSleep: afternoon or night."""
        return self.day_fraction < 0.25 or self.day_fraction > 0.7

    def _creatures(self, dt: float) -> None:
        for creature in list(self.entities.values()):
            if creature.kind == "creature" and creature.skittish > 0 and not self.bot.dead:
                # 사슴처럼 겁 많은 동물은 가까이 오면 반대쪽으로 달아난다.
                # 웅크리고 다가가면 훨씬 가까이서야 안다.
                distance = self.distance(creature.x, creature.z)
                notice = creature.skittish * (SNEAK_NOTICE if self.bot.crouching else 1.0)
                if 0 < distance < notice:
                    step = creature.speed * dt
                    creature.x += (creature.x - self.bot.x) / distance * step
                    creature.z += (creature.z - self.bot.z) / distance * step
                continue
            if creature.kind != "creature" or not (creature.hostile or creature.provoked) or self.bot.dead:
                continue
            distance = self.distance(creature.x, creature.z)
            # 게임의 MonsterAI처럼 멀리 달아나면(경계 거리의 두 배) 쫓기를 그만둔다.
            if creature.provoked and distance > 2 * max(creature.aggro, 10.0):
                creature.provoked = False
            if distance > creature.aggro and not creature.provoked:
                continue
            if creature.winding is not None:
                # Body AttackWatch처럼 공격은 동작으로 먼저 보이고 조금 뒤에 맞는다. 그사이 구르면 빗나간다.
                hit_at, kind, amount, dodges = creature.winding
                if self.now >= hit_at:
                    creature.winding = None
                    reach = creature.ranged_m if kind == "lightning" else 2.5
                    if self.dodges == dodges and distance <= reach:
                        self._hurt_by(creature, amount, kind)
                continue
            if distance > 1.5:
                step = min(creature.speed * dt, distance - 1.4)
                creature.x += (self.bot.x - creature.x) / distance * step
                creature.z += (self.bot.z - creature.z) / distance * step
                if distance <= creature.ranged_m and self.now >= creature.next_attack:
                    creature.next_attack = self.now + 3.0
                    self._wind_up(creature, distance, "lightning", creature.ranged_damage)
            elif self.now >= creature.next_attack:
                creature.next_attack = self.now + 2.0
                self._wind_up(creature, distance, "blunt", creature.damage)

    def _wind_up(self, creature: SimEntity, distance: float, kind: str, amount: float) -> None:
        creature.winding = (self.now + WIND_UP_S, kind, amount, self.dodges)
        if distance <= SCENE_RANGE_M:
            self.event(
                "creature_attacking",
                {"id": creature.id, "distance": round(distance, 1), "size": creature.size, "facing_me": True},
            )

    def _hurt_by(self, creature: SimEntity, amount: float, kind: str) -> None:
        self.bot.hp = max(0.0, self.bot.hp - amount)
        self.bot.last_hurt = self.now
        self._engage_reflex(creature)
        self.event(
            "damage_taken",
            {
                "amount": amount,
                "hp_after": round(self.bot.hp, 1),
                "types": {kind: amount},
                "blocked": False,
                "hit_type": "EnemyHit",
                "attacker_id": creature.id,
                "attacker_name": creature.name,
                "attacker_kind": "creature",
                "attacker_size": creature.size,
            },
        )
        if self.bot.hp <= 0:
            self.die()

    def die(self) -> None:
        """Like the game: the body drops everything into a tombstone where it fell and respawns at the start
        stones (no bed) a few seconds later with empty hands and no food."""
        self.bot.dead = True
        self.event("death", {"pos": [round(self.bot.x, 2), 0.0, round(self.bot.z, 2)]})
        self.stop_all("dead")
        self.reflex_attacker = None
        items = {name: count for name, count in self.bot.inventory.items() if count > 0}
        self.spawn(
            SimEntity(self.new_id(), "tombstone", "묘비 Thorkell", self.bot.x, self.bot.z, stored=items)
        )
        self.bot.inventory, self.bot.equipped, self.bot.foods = {}, None, {}
        self.at(self.now + 3.0, _respawn)

    def _engage_reflex(self, creature: SimEntity) -> None:
        self.reflex_hit_at = self.now
        busy_fighting = (self.active is not None and self.active.cmd["op"] in FIGHT_OPS) or (
            self.now < self.brain_fighting_until
        )
        if busy_fighting or self.reflex_attacker == creature.id:
            return
        # Body Reflexes.Defending과 같다: 큰 적(보스)이나 활을 든 싸움은 두뇌가 맡는다.
        if creature.size == "large" or self.weapon().type == "Bow":
            return
        self.reflex_attacker = creature.id
        if self.active is not None:
            self._finish("preempted", "self_defense", {})
        weapon = self.weapon()
        self.event(
            "reflex_engaged",
            {
                "mode": "self_defense",
                "reason": "attacked",
                "attacker_id": creature.id,
                "attacker_name": creature.name,
                "weapon": {"name": weapon.name, "damage": dict(weapon.damage)},
            },
        )

    def _release_reflex(self) -> None:
        self.event("reflex_released", {"mode": "self_defense", "reason": "attacked"})
        self.reflex_attacker = None

    def _reflex(self) -> None:
        target = self.entities.get(self.reflex_attacker or "")
        if target is None or self.now - self.reflex_hit_at > 10 or self.distance(target.x, target.z) > 12:
            self._release_reflex()
            return
        distance = self.distance(target.x, target.z)
        reach = self.weapon().reach + 0.4
        if distance > reach:
            step = min(4.0 * self.dt, distance - reach * 0.8)
            self.bot.x += (target.x - self.bot.x) / distance * step
            self.bot.z += (target.z - self.bot.z) / distance * step
        elif self.now >= self.reflex_next_swing and self.bot.stamina >= 10:
            self.bot.stamina -= 10
            self.reflex_next_swing = self.now + 1.0
            self.hit(target)
            if target.hp <= 0:
                self._release_reflex()

    def hit(self, target: SimEntity) -> dict[str, Any]:
        weapon = self.weapon()
        before = target.hp
        text_type = "normal"
        if target.kind in ("tree", "log", "rock"):
            chop = weapon.damage.get("chop", 0.0)
            if weapon.tier < target.tier or chop <= 0:
                amount, text_type = 0.0, "too_hard"
            else:
                amount = chop
        else:
            amount = 0.0
            for kind, value in weapon.damage.items():
                if kind == "chop":
                    continue
                multiplier = target.multipliers.get(kind, 1.0)
                amount += value * multiplier
                if multiplier == 0:
                    text_type = "immune"
                elif multiplier > 1:
                    text_type = "weak"
                elif multiplier < 1:
                    text_type = "resistant"
        target.hp = max(0.0, target.hp - amount)
        target.provoked = target.kind == "creature" and target.damage > 0
        self._wear(weapon.name)
        self.event(
            "damage_dealt",
            {
                "type": text_type,
                "text": f"{amount:g}",
                "amount": amount,
                "pos": [target.x, 1.0, target.z],
                "weapon": {"name": weapon.name, "damage": dict(weapon.damage)},
                # 시뮬레이터의 휘두르기는 겨냥한 대상 하나만 맞힌다.
                "on_target": True,
            },
        )
        if target.hp <= 0:
            del self.entities[target.id]
            if target.kind == "creature" and not target.hidden:
                # Body Hooks.Fell과 같다: 쓰러지는 것이 보인다(시체가 생긴다).
                self.event(
                    "creature_died", {"id": target.id, "size": target.size, "pos": [target.x, 0.0, target.z]}
                )
            if target.boss:
                # 실게임(2026-10-18): 보스가 쓰러지면 화면 가운데에 이렇게 뜬다. 보이지 않아도 뜬다.
                self.event(
                    "game_message", {"where": "center", "text": f"{target.name}를 처치했습니다", "amount": 0}
                )
            for index, (kind, name, hp, drops) in enumerate(target.becomes):
                self.spawn(
                    SimEntity(
                        self.new_id(), kind, name, target.x + 1.5 * index, target.z + 1.0, hp, hp, drops=drops
                    )
                )
            for index, (item, count) in enumerate(target.drops):
                self.spawn(
                    SimEntity(
                        self.new_id(), "item", item, target.x + 0.5 * index, target.z - 0.5, stack=count
                    )
                )
        return {"hp_before": round(before, 1), "hp_after": round(target.hp, 1), "destroyed": target.hp <= 0}

    def _wear(self, name: str) -> None:
        if name not in self.bot.wear:
            return
        self.bot.wear_full.setdefault(name, self.bot.wear[name])
        self.bot.wear[name] -= 1
        if self.bot.wear[name] > 0:
            return
        self.bot.inventory[name] -= 1
        self.bot.broken[name] = self.bot.broken.get(name, 0) + 1
        self.bot.wear[name] = self.bot.wear_full[name]
        if self.bot.equipped == name:
            self.bot.equipped = None

    # --- observations -----------------------------------------------------------------------
    def state(self) -> dict[str, Any]:
        b = self.bot
        data: dict[str, Any] = {
            "pos": [round(b.x, 2), 0.0, round(b.z, 2)],
            "yaw": round(b.yaw, 1),
            "hp": round(b.hp, 1),
            "hp_max": b.hp_max,
            "stamina": round(b.stamina, 1),
            "stamina_max": b.stamina_max,
            "dead": b.dead,
            "in_bed": b.in_bed,
            "swimming": False,
            "in_attack": False,
        }
        if self.active is not None:
            data["action"] = {
                "cmd_id": self.active.cmd["id"],
                "op": self.active.cmd["op"],
                "phase": self.active.action.phase,
            }
        return data

    def scene(self) -> dict[str, Any]:
        nearby = []
        boss_bars = []
        for e in sorted(self.entities.values(), key=lambda e: self.distance(e.x, e.z)):
            distance = self.distance(e.x, e.z)
            if e.boss and distance <= BOSS_BAR_M and (distance <= e.aggro or e.provoked):
                boss_bars.append({"id": e.id, "name": e.name, "health": round(e.hp / e.max_hp, 2)})
            seen_range = LARGE_SCENE_RANGE_M if e.kind == "creature" and e.size == "large" else SCENE_RANGE_M
            if distance > seen_range or e.hidden:
                continue
            entry: dict[str, Any] = {
                "id": e.id,
                "kind": e.kind,
                "name": e.name,
                "distance": round(distance, 2),
                "bearing": 0.0,
                "pos": [round(e.x, 2), 0.0, round(e.z, 2)],
                "visible": True,
            }
            if e.kind == "item":
                entry["stack"] = e.stack
            if e.kind in FOOTPRINT_M:
                # Body Snapshot과 같다: pos는 다가갈 지점(가장 가까운 겉면), center는 가운데.
                reach = min(FOOTPRINT_M[e.kind], distance)
                dx, dz = self.bot.x - e.x, self.bot.z - e.z
                length = math.hypot(dx, dz) or 1.0
                entry["pos"] = [round(e.x + dx / length * reach, 2), 0.0, round(e.z + dz / length * reach, 2)]
                entry["center"] = [round(e.x, 2), 0.0, round(e.z, 2)]
                entry["yaw"] = 0.0
            if e.kind == "portal":
                entry["tag"] = e.tag
                entry["connected"] = e.partner in self.entities
                entry["center"] = [round(e.x, 2), 0.0, round(e.z, 2)]
            if e.kind == "bed" and distance <= BED_LABEL_M:
                entry["owner"] = e.owner
                entry["mine"] = e.owner == BOT_NAME
            if e.kind == "creature":
                # Body Scanner와 같다: 이름·체력은 머리 위 HUD가 보이는 거리 안에서만.
                # 보스는 알아챘을 때 화면 위쪽에 뜬다.
                alerted = distance <= e.aggro
                if alerted if e.boss else distance <= HUD_RADIUS:
                    entry["health"] = round(e.hp / e.max_hp, 2)
                    entry["stars"] = 0
                    entry["alerted"] = alerted
                    if e.boss:
                        entry["top_bar"] = True
                else:
                    entry["name"] = ""
                if e.key:
                    entry["key"] = e.key
                entry["size"] = e.size
                entry["height_m"] = e.height
            nearby.append(entry)
        inventory = []
        for name, count in self.bot.inventory.items():
            if count <= 0:
                continue
            spec = ITEMS[name]
            item: dict[str, Any] = {
                "name": name,
                "stack": count,
                "quality": 1,
                "type": spec.type,
                "weight": spec.weight * count,
                "equipped": self.bot.equipped == name,
            }
            if name == "활" and self.bot.bow_uses is not None:
                item["durability"] = 1.0 if self.bot.bow_uses > 0 else 0.0
            if spec.food:
                item["food"] = {
                    "health": spec.food[0],
                    "stamina": spec.food[1],
                    "eitr": 0,
                    "duration_s": spec.food[2],
                }
            if name in self.bot.wear:
                item["durability"] = round(
                    self.bot.wear[name] / self.bot.wear_full.get(name, self.bot.wear[name]), 2
                )
            if spec.damage:
                item["damage"] = dict(spec.damage)
            inventory.append(item)
        for name, count in self.bot.broken.items():
            spec = ITEMS[name]
            inventory.append(
                {
                    "name": name,
                    "stack": count,
                    "quality": 1,
                    "type": spec.type,
                    "weight": spec.weight * count,
                    "equipped": False,
                    "durability": 0.0,
                    "damage": dict(spec.damage),
                }
            )
        # Body Scanner처럼 가까운 48개, 그리고 그 밖의 큰 생물.
        beyond = nearby[48:]
        shown = nearby[:48] + [e for e in beyond if e.get("size") == "large"]
        # Body Scanner처럼 그 밖의 나무·통나무도 몇 개 보인다(커서 멀리서도 눈에 띈다).
        for kind in ("tree", "log"):
            shown += [e for e in beyond if e["kind"] == kind][:6]
        return {
            "nearby": shown,
            **({"boss_bars": boss_bars} if boss_bars else {}),
            "inventory": inventory,
            "weight": sum(i["weight"] for i in inventory),
            "weight_max": 300,
            "foods": [{"name": n, "remaining_s": int(t)} for n, t in self.bot.foods.items()],
            "biome": "초원",
            "effects": self.effects(),
            "env": {
                "night": self.night,
                "day": 1,
                "day_fraction": round(self.day_fraction, 3),
                "weather": "Clear",
            },
            **self._leader_seen(),
        }

    def effects(self) -> list[str]:
        near_fire = any(
            e.kind == "fire" and e.fuel > 0 and self.distance(e.x, e.z) <= 5 for e in self.entities.values()
        )
        sheltered = self.roofed(self.bot.x, self.bot.z)
        return [name for name, on in (("쉼터", sheltered), ("따뜻함", near_fire)) if on]

    def _leader_seen(self) -> dict[str, Any]:
        # 몸(BodyLink): 가까우면 로드된 리더 캐릭터(leader), 멀면 지도에 공개된 위치(leader_on_map)만 있다.
        distance = round(self.distance(*self.leader), 2)
        pos = [self.leader[0], 0.0, self.leader[1]]
        if distance <= LEADER_LOADED_M:
            seen = {
                "id": "7:1",
                "name": "Leader",
                "distance": distance,
                "bearing": 0.0,
                "pos": pos,
                "facing": self.leader_facing,
                "in_bed": self.leader_in_bed,
            }
            return {"leader": seen}
        if self.leader_public:
            return {"leader_on_map": {"name": "Leader", "distance": distance, "pos": pos}}
        return {}


# --- actions -------------------------------------------------------------------------------
def _target_point(world: SimWorld, target: dict[str, Any]) -> tuple[float, float] | None:
    if "pos" in target:
        return float(target["pos"][0]), float(target["pos"][2])
    if target.get("id") == "7:1":
        return world.leader
    entity = world.entities.get(target.get("id", ""))
    return None if entity is None else (entity.x, entity.z)


class _MoveTo(_SimAction):
    def __init__(self, args: dict[str, Any]):
        if "target" not in args:
            raise ValueError("bad_args:target")
        self.target = args["target"]
        self.sneak = bool(args.get("sneak", False))
        self.run = bool(args.get("run", False)) and not self.sneak
        self.arrive = float(args.get("arrive_radius", 1.5))
        self.timeout = float(args.get("timeout_s", 60.0))
        self.started: float | None = None
        self.remaining = -1.0
        self.phase = "moving"
        self.item: tuple[str, int] | None = None

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        world.bot.crouching = self.sneak
        if self.started is None:
            self.started = now
            entity = world.entities.get(self.target.get("id", ""))
            if entity is not None and entity.kind == "item":
                self.item = (entity.name, world.bot.inventory.get(entity.name, 0))
        point = _target_point(world, self.target)
        if point is None:
            # Body MoveTo와 같다: 목표 아이템이 자동 줍기로 사라졌으면 인벤토리 증가로 확인한다.
            if self.item is not None and world.bot.inventory.get(self.item[0], 0) > self.item[1]:
                added = world.bot.inventory[self.item[0]] - self.item[1]
                return "succeeded", "picked_up", {"item": self.item[0], "added": added, "auto": True}
            return "failed", "target_lost", {}
        self.remaining = world.distance(*point)
        target = world.entities.get(self.target.get("id", ""))
        if target is not None and target.unreachable and self.remaining <= 4.0:
            return "failed", "blocked", {"remaining_m": round(self.remaining, 2)}
        if self.remaining <= self.arrive:
            return "succeeded", "arrived", {"remaining_m": round(self.remaining, 2)}
        if now - self.started > self.timeout:
            return "failed", "timeout", {"remaining_m": round(self.remaining, 2)}
        speed = 7.0 if self.run and world.bot.stamina > 15 else 2.0 if self.sneak else 4.0
        if speed > 4.0:
            world.bot.stamina -= 5 * world.dt
        step = min(speed * world.dt, self.remaining - self.arrive * 0.5)
        world.bot.x += (point[0] - world.bot.x) / self.remaining * step
        world.bot.z += (point[1] - world.bot.z) / self.remaining * step
        return None

    def progress(self, world: SimWorld) -> dict[str, Any]:
        return {"remaining_m": round(self.remaining, 2), "phase": self.phase}

    def stop(self, world: SimWorld) -> None:
        world.bot.crouching = self.sneak  # 몰래 다가간 뒤에는 웅크린 채로(다음 동작이 정한다)


class _Attack(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.id = args.get("id")
        self.swings = int(args.get("swings", 1))
        self.sneak = bool(args.get("sneak", False))
        self.done = 0
        self.next_swing: float | None = None
        self.evidence: dict[str, Any] = {}
        self.phase = "aiming"

    def stop(self, world: SimWorld) -> None:
        world.bot.crouching = False  # 치고 나면 일어선다

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        world.bot.crouching = self.sneak
        target = world.entities.get(self.id or "")
        if target is None:
            return (
                ("succeeded", "destroyed", {**self.evidence, "destroyed": True})
                if self.done
                else ("failed", "not_found", {})
            )
        reach = world.weapon().reach + 0.4
        distance = world.distance(target.x, target.z)
        if distance > reach:
            return "failed", "out_of_reach", {"distance_m": round(distance, 2), "reach_m": reach}
        if self.next_swing is None or now >= self.next_swing:
            if world.bot.stamina < 10:
                return "failed", "cannot_attack", {"stamina": round(world.bot.stamina, 1)}
            world.bot.stamina -= 10
            result = world.hit(target)
            result["weapon"] = world.weapon().name
            self.evidence = {
                "hp_before": self.evidence.get("hp_before", result["hp_before"]),
                **result,
                "swings": self.done + 1,
            }
            self.done += 1
            self.next_swing = now + 1.0
            self.phase = "swinging"
            if result["destroyed"]:
                return "succeeded", "destroyed", self.evidence
            if self.done >= self.swings:
                return "succeeded", "swung", self.evidence
        return None


class _Pickup(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.id = args.get("id", "")

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        entity = world.entities.get(self.id)
        if entity is None or entity.kind != "item":
            return "failed", "not_found", {}
        distance = world.distance(entity.x, entity.z)
        if distance > 2.5:
            return "failed", "out_of_reach", {"distance_m": round(distance, 2)}
        world.pick_up(entity)
        return "succeeded", "picked_up", {"item": entity.name, "added": entity.stack}


class _Equip(_SimAction):
    def __init__(self, args: dict[str, Any], equip: bool):
        self.item = args.get("item", "")
        self.equip = equip

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        if world.bot.inventory.get(self.item, 0) <= 0:
            if world.bot.broken.get(self.item):
                # 부러진 것만 있으면 게임처럼 손에 들지 못한다.
                return "failed", "cannot_equip", {"item": self.item}
            return "failed", "not_found", {}
        if not self.equip:
            world.bot.equipped = None if world.bot.equipped == self.item else world.bot.equipped
            return "succeeded", "unequipped", {"item": self.item}
        if ITEMS[self.item].type not in WEAPON_TYPES:
            return "failed", "cannot_equip", {"item": self.item}
        code = "already_equipped" if world.bot.equipped == self.item else "equipped"
        world.bot.equipped = self.item
        return "succeeded", code, {"item": self.item}


class _Eat(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.item = args.get("item", "")

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        spec = ITEMS.get(self.item)
        if world.bot.inventory.get(self.item, 0) <= 0 or spec is None:
            return "failed", "not_found", {}
        if spec.food is None:
            return "failed", "not_food", {"item": self.item}
        if self.item == "상한 고기":
            return "failed", "cannot_eat_now", {"item": self.item}
        if self.item in world.bot.foods or len(world.bot.foods) >= 3:
            return "failed", "cannot_eat_now", {"item": self.item}
        before = len(world.bot.foods)
        world.bot.inventory[self.item] -= 1
        world.bot.foods[self.item] = spec.food[2]
        world.bot.hp_max = 25.0
        for name in world.bot.foods:
            food = ITEMS[name].food
            if food is not None:
                world.bot.hp_max += food[0]
        return "succeeded", "eaten", {"item": self.item, "foods_before": before, "foods_after": before + 1}


def _near(world: SimWorld, entity_id: str, reach: float) -> SimEntity | tuple[str, str, dict[str, Any]]:
    entity = world.entities.get(entity_id)
    if entity is None:
        return "failed", "not_found", {}
    distance = world.distance(entity.x, entity.z)
    if distance > reach:
        return "failed", "out_of_reach", {"distance_m": round(distance, 2)}
    return entity


class _Craft(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.item = str(args.get("item", ""))
        self.count = int(args.get("count", 1))
        self.station_id = args.get("station_id")
        self.made = 0
        self.next_at: float | None = None
        self.phase = "opening"

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        station_name = None
        if self.station_id is not None:
            station = _near(world, str(self.station_id), 3.0)
            if isinstance(station, tuple):
                return station
            station_name = station.name
            if not world.roofed(station.x, station.z):
                world.event("game_message", {"where": "center", "text": "지붕이 필요합니다", "amount": 0})
                return "failed", "station_unusable", {"station": station.name}
        recipe = RECIPES.get(self.item)
        if recipe is None or recipe not in world.known_recipes() or recipe.station != station_name:
            return (
                "failed",
                "recipe_not_in_menu",
                {"item": self.item, "station": station_name or "", "made": 0},
            )
        if self.next_at is None:
            if not world.has(recipe.resources):
                evidence = {"item": self.item, "missing": world.missing(recipe.resources), "made": self.made}
                return "failed", "missing_requirements", evidence
            self.next_at = now + 2.0
            self.phase = "crafting"
            return None
        if now < self.next_at:
            return None
        world.consume(recipe.resources)
        world.add_item(recipe.name, recipe.amount)
        self.made += 1
        self.next_at = None
        if self.made >= self.count:
            have = world.bot.inventory.get(recipe.name, 0)
            return "succeeded", "crafted", {"item": recipe.name, "made": self.made, "have": have}
        return None


class _Place(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.piece = str(args.get("piece", ""))
        pos = args.get("pos")
        if not isinstance(pos, list) or len(pos) != 3:
            raise ValueError("bad_args:pos")
        self.x, self.z = float(pos[0]), float(pos[2])
        within = args.get("within_m")
        if within is not None and not 0.05 <= float(within) <= 3.0:
            raise ValueError("bad_args:within_m")
        self.at: float | None = None

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        if world.bot.equipped != "망치":
            return "failed", "no_build_tool", {}
        spec = PIECES.get(self.piece)
        if spec is None or spec not in world.known_pieces():
            return "failed", "piece_not_known", {"piece": self.piece}
        if world.distance(self.x, self.z) > PLACE_REACH:
            return "failed", "out_of_reach", {"distance_m": round(world.distance(self.x, self.z), 2)}
        if self.at is None:
            missing = world.missing(spec.resources)
            if missing or (spec.station is not None and not world.station_near(spec.station)):
                return (
                    "failed",
                    "missing_requirements",
                    {
                        "piece": spec.name,
                        "missing": missing,
                        "needs_station": spec.station,
                    },
                )
            self.at = now + 0.5
            return None
        if now < self.at:
            return None
        world.consume(spec.resources)
        built = world.spawn(
            SimEntity(world.new_id(), spec.kind, spec.name, self.x, self.z, creator="Thorkell")
        )
        if spec.kind == "fire":
            built.fuel = 1.0
        return "succeeded", "placed", {"piece": spec.name, "id": built.id, "pos": [self.x, 0.0, self.z]}


class _UseItem(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.item = str(args.get("item", ""))
        self.id = str(args.get("id", ""))

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        target = _near(world, self.id, 3.0)
        if isinstance(target, tuple):
            return target
        if world.bot.inventory.get(self.item, 0) <= 0:
            return "failed", "item_not_found", {}
        evidence = {"item": self.item, "target": target.name}
        used = 0
        if target.kind == "fire" and self.item == "나무" and target.fuel < 10:
            target.fuel += 1
            used = 1
        elif target.kind == "cooking" and self.item == "날고기" and len(target.cooking) < 2:
            fire = any(
                e.kind == "fire" and e.fuel > 0 and math.hypot(e.x - target.x, e.z - target.z) < FIRE_UNDER_M
                for e in world.entities.values()
            )
            if not fire:
                world.event(
                    "game_message",
                    {"where": "center", "text": "요리 작업대 아래에 불을 피워야 합니다", "amount": 0},
                )
            else:
                target.cooking.append(now)
                used = 1
        elif target.kind == "altar" and self.item == "사슴 트로피" and world.bot.inventory[self.item] >= 2:
            used = 2
            world.at(now + 3.0, _summon(target.x + 6, target.z))
        if not used:
            return "failed", "refused", {**evidence, "used": 0}
        world.bot.inventory[self.item] -= used
        return "succeeded", "used", {**evidence, "used": used}


def _respawn(world: SimWorld) -> None:
    world.bot.dead = False
    world.bot.x, world.bot.z = 0.0, 0.0
    world.bot.hp_max = world.bot.hp = 25.0
    world.bot.stamina = world.bot.stamina_max


def _summon(x: float, z: float) -> Callable[[SimWorld], None]:
    def appear(world: SimWorld) -> None:
        world.spawn(eikthyr(x, z))

    return appear


class _Drop(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.item = str(args.get("item", ""))
        self.count = int(args.get("count", 1))

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        have = world.bot.inventory.get(self.item, 0)
        if have <= 0:
            return "failed", "not_found", {}
        count = min(have, self.count)
        world.bot.inventory[self.item] -= count
        world.spawn(
            SimEntity(
                world.new_id(),
                "item",
                self.item,
                world.bot.x + 1.0,
                world.bot.z,
                stack=count,
                auto_pickup=False,
            )
        )
        return "succeeded", "dropped", {"item": self.item, "dropped": count, "left": have - count}


class _Shoot(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.id = str(args.get("id", ""))
        # Body Shoot와 같다: false면 화살이 나가자마자 "fired"로 끝난다.
        self.wait_hit = bool(args.get("wait_hit", True))
        self.release_at: float | None = None
        # Body Shoot와 같다: 시위를 당기는 동안 strafe 쪽(수평)으로 걷는다.
        strafe = args.get("strafe")
        self.strafe: tuple[float, float] | None = None
        if isinstance(strafe, list):
            length = math.hypot(float(strafe[0]), float(strafe[2]))
            if length > 0.01:
                self.strafe = (float(strafe[0]) / length, float(strafe[2]) / length)
        self.ticked_at = 0.0

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        target = world.entities.get(self.id)
        if target is None:
            return "failed", "not_found", {}
        if world.bot.equipped != "활" or world.bot.bow_uses == 0:
            return "failed", "no_bow", {}
        if world.bot.inventory.get("나무 화살", 0) <= 0:
            return "failed", "no_ammo", {}
        distance = world.distance(target.x, target.z)
        if distance > 60:
            return "failed", "out_of_range", {"distance_m": round(distance, 1)}
        if target.cover_from is not None and world.distance(*target.cover_from) <= 3.0:
            return "failed", "no_line_of_sight", {"distance_m": round(distance, 1)}
        if self.release_at is None:
            self.release_at = now + 1.2
            self.ticked_at = now
            self.phase = "drawing"
            return None
        if now < self.release_at:
            if self.strafe is not None:
                step = DRAW_WALK_SPEED * (now - self.ticked_at)
                world.bot.x += self.strafe[0] * step
                world.bot.z += self.strafe[1] * step
            self.ticked_at = now
            return None
        world.bot.inventory["나무 화살"] -= 1
        if world.bot.bow_uses is not None:
            world.bot.bow_uses -= 1
        before = target.hp
        hit = distance <= 30
        if hit:
            world.hit(target)
        killed = target.id not in world.entities
        if not self.wait_hit:
            return "succeeded", "fired", {"arrows_left": world.bot.inventory["나무 화살"]}
        # Body Shoot와 같다: 체력은 체력바 비율로만.
        evidence = {
            "hit": hit,
            "health_before": round(before / target.max_hp, 3),
            "health_after": round(target.hp / target.max_hp, 3),
            "killed": killed,
            "arrows_left": world.bot.inventory["나무 화살"],
        }
        return "succeeded", "hit" if hit else "missed", evidence


class _Dodge(_SimAction):
    """A roll: a quick 4 m step toward `toward` (or backwards), costing stamina."""

    def __init__(self, args: dict[str, Any]):
        toward = args.get("toward")
        self.toward = (float(toward[0]), float(toward[2])) if isinstance(toward, list) else None

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        if world.bot.stamina < 10:
            return "failed", "dodge_not_started", {"stamina": round(world.bot.stamina, 1)}
        world.bot.stamina -= 10
        world.dodges += 1
        if self.toward is not None:
            dx, dz = self.toward[0] - world.bot.x, self.toward[1] - world.bot.z
            length = math.hypot(dx, dz) or 1.0
            world.bot.x += dx / length * 4.0
            world.bot.z += dz / length * 4.0
        return "succeeded", "dodged", {"stamina": round(world.bot.stamina, 1)}


class _Interact(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.id = str(args.get("id", ""))

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        target = _near(world, self.id, 3.0)
        if isinstance(target, tuple):
            return target
        if target.kind == "pickable" and target.gives is not None:
            del world.entities[target.id]
            world.add_item(*target.gives)
            return "succeeded", "interacted", {"target": target.name, "picked": target.gives[0]}
        if target.kind == "tombstone":
            for name, count in target.stored.items():
                world.add_item(name, count)
            del world.entities[target.id]
            return "succeeded", "interacted", {"target": target.name}
        if target.kind == "station":
            opened = world.roofed(target.x, target.z)
            if not opened:
                world.event(
                    "game_message",
                    {"where": "center", "text": "제작 작업대에 지붕이 필요합니다", "amount": 0},
                )
            return "succeeded", "interacted", {"target": target.name, "opened": opened}
        if target.kind == "bed":
            return _use_bed(world, target)
        if target.kind == "cooking":
            done = [t for t in target.cooking if now - t >= COOK_SECONDS]
            for started in done:
                target.cooking.remove(started)
                world.add_item("구운 고기" if now - started < BURN_SECONDS else "숯", 1)
        return "succeeded", "interacted", {"target": target.name}


def _use_bed(world: SimWorld, bed: SimEntity) -> tuple[str, str, dict[str, Any]]:
    """Bed.Interact: claim an unowned bed (roof needed), lie in your own one, ignore someone else's."""
    evidence: dict[str, Any] = {"target": bed.name}
    refusal = None
    if bed.owner == "":
        if world.roofed(bed.x, bed.z):
            bed.owner = BOT_NAME
            world.event(
                "game_message", {"where": "center", "text": "스폰 지점이 설정되었습니다", "amount": 0}
            )
        else:
            refusal = "침대 위에 지붕이 필요합니다"
    elif bed.owner == BOT_NAME:
        fire = any(
            e.kind == "fire" and e.fuel > 0 and math.hypot(e.x - bed.x, e.z - bed.z) <= BED_FIRE_M
            for e in world.entities.values()
        )
        if not world.can_sleep:
            refusal = "지금은 잘 수 없습니다"
        elif not world.roofed(bed.x, bed.z):
            refusal = "침대 위에 지붕이 필요합니다"
        elif not fire:
            refusal = "주변에 불이 필요합니다"
        else:
            world.bot.in_bed = True
    if refusal is not None:
        world.event("game_message", {"where": "center", "text": refusal, "amount": 0})
    evidence["in_bed"] = world.bot.in_bed
    return "succeeded", "interacted", evidence


class _Say(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.text = str(args.get("text", ""))
        self.talker = str(args.get("talker", "normal"))
        if not self.text:
            raise ValueError("bad_args:text")

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        world.said.append((self.talker, self.text))
        return "succeeded", "said", {}


class _Instant(_SimAction):
    def __init__(self, code: str):
        self.code = code

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        return "succeeded", self.code, {}


class _Wait(_SimAction):
    def __init__(self, args: dict[str, Any]):
        self.seconds = float(args.get("seconds", 1.0))
        self.until: float | None = None
        self.phase = "waiting"

    def tick(self, world: SimWorld, now: float) -> tuple[str, str, dict[str, Any]] | None:
        self.until = now + self.seconds if self.until is None else self.until
        return ("succeeded", "waited", {}) if now >= self.until else None


def _make(op: str, args: dict[str, Any]) -> _SimAction:
    match op:
        case "move_to":
            return _MoveTo(args)
        case "attack":
            return _Attack(args)
        case "pickup":
            return _Pickup(args)
        case "equip":
            return _Equip(args, equip=True)
        case "unequip":
            return _Equip(args, equip=False)
        case "eat":
            return _Eat(args)
        case "say":
            return _Say(args)
        case "look_at":
            return _Instant("facing")
        case "interact":
            return _Interact(args)
        case "craft":
            return _Craft(args)
        case "place":
            return _Place(args)
        case "use_item":
            return _UseItem(args)
        case "drop":
            return _Drop(args)
        case "shoot":
            return _Shoot(args)
        case "dodge":
            return _Dodge(args)
        case "wait":
            return _Wait(args)
    raise ValueError("unknown_op")


# --- protocol client ----------------------------------------------------------------------
class SimBody:
    """Connects a SimWorld to the brain's BridgeServer as role "body"."""

    def __init__(self, world: SimWorld, time_scale: float = 1.0):
        self.world = world
        self.time_scale = time_scale
        self.seq = 0
        # 토르켈이 영어로 플레이하면 몸이 보내는 이름도 영어 게임의 이름이다.
        self.english = lang.current() == "en"

    async def run(self, port: int, token: str, stop: asyncio.Event) -> None:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        challenge = json.loads(await reader.readline())
        session = auth.new_hex(16)
        await self._send(
            writer,
            {
                "t": "hello",
                "role": "body",
                "proto": [1, 0],
                "plugin": "sim",
                "game": {"version": "sim", "network": 40, "assembly_sha256": "00"},
                "session": session,
                "caps": ["observe", "move", "act", "say"],
                "mac": auth.mac(token, challenge["nonce"], "body", session),
            },
        )
        welcome = json.loads(await reader.readline())
        if welcome["t"] != "welcome":
            raise ConnectionError(f"sim body rejected: {welcome}")
        incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def read() -> None:
            while line := await reader.readline():
                await incoming.put(json.loads(line))

        reader_task = asyncio.create_task(read())
        last = time.monotonic()
        next_state = next_scene = next_status = 0.0
        try:
            while not stop.is_set():
                now = time.monotonic()
                dt = (now - last) * self.time_scale
                last = now
                while not incoming.empty():
                    self._dispatch(incoming.get_nowait())
                self.world.step(dt)
                # 관측 주기는 시뮬레이션 시간 기준(state 10Hz, scene 2Hz, status 1Hz)이라 time_scale을 올려도
                # 두뇌가 보는 세계의 갱신 빈도는 실제 게임과 같다.
                sim_now = self.world.now
                if sim_now >= next_state:
                    next_state = sim_now + 0.1
                    self.world.emit("state", tick=int(sim_now * 30), data=self.world.state())
                if sim_now >= next_scene:
                    next_scene = sim_now + 0.5
                    self.world.emit("scene", tick=int(sim_now * 30), data=self.world.scene())
                if sim_now >= next_status:
                    next_status = sim_now + 1.0
                    self.world.emit(
                        "status",
                        armed=not self.world.bot.dead,
                        ready=True,
                        reasons=["dead"] if self.world.bot.dead else [],
                        version_gate={"ok": True, "found": "sim", "tested": "sim"},
                    )
                for message in self.world.outbox:
                    await self._send(writer, message)
                self.world.outbox.clear()
                await asyncio.sleep(0.02)
        finally:
            reader_task.cancel()
            writer.close()

    def _dispatch(self, message: dict[str, Any]) -> None:
        if self.english:
            message = english.back(message)
        match message["t"]:
            case "cmd":
                self.world.submit(message)
            case "cancel":
                self.world.cancel(message["cmd_id"], message["reason"])
            case "stop_all":
                self.world.stop_all(message["reason"])
            case "query":
                data = self.world.query(message["what"], message.get("args"))
                if data is None:
                    self.world.emit("query_result", id=message["id"], ok=False, error="unknown_query")
                else:
                    self.world.emit("query_result", id=message["id"], ok=True, data=data)

    async def _send(self, writer: asyncio.StreamWriter, body: dict[str, Any]) -> None:
        if self.english:
            body = english.out(body)
        self.seq += 1
        line = json.dumps(
            {"v": 1, "seq": self.seq, "ts": int(time.time() * 1000), **body}, ensure_ascii=False
        )
        writer.write((line + "\n").encode())
        await writer.drain()


def forest(world_trees: int = 3) -> list[SimEntity]:
    """A small meadow edge: a few trees (-> logs -> wood) and berry bushes' worth of food items."""
    entities = []
    for index in range(world_trees):
        entities.append(
            SimEntity(
                f"7:{10 + index}",
                "tree",
                "",
                12.0 + 4.0 * index,
                3.0 * (index % 2),
                hp=40.0,
                max_hp=40.0,
                tier=0,
                becomes=[("log", "", 40.0, [("나무", 5)]), ("log", "", 40.0, [("나무", 5)])],
            )
        )
    return entities


def greydwarf(x: float, z: float, id: str = "7:900") -> SimEntity:
    return SimEntity(
        id,
        "creature",
        "그레이드워프",
        x,
        z,
        hp=40.0,
        max_hp=40.0,
        hostile=True,
        damage=4.0,
        speed=3.0,
        aggro=15.0,
        multipliers={"blunt": 1.5, "slash": 0.5},
        drops=[("돌", 1)],
        key="$enemy_greydwarf",
        size="medium",
    )


def boar(x: float, z: float, id: str = "7:910") -> SimEntity:
    """Wanders until hit, then charges (Valheim boars only fight back)."""
    return SimEntity(
        id,
        "creature",
        "멧돼지",
        x,
        z,
        hp=20.0,
        max_hp=20.0,
        damage=3.0,
        speed=4.0,
        aggro=0.0,
        drops=[("날고기", 1), ("가죽 조각", 1)],
        key="$enemy_boar",
        size="small",
    )


def deer(x: float, z: float, id: str = "7:920") -> SimEntity:
    return SimEntity(
        id,
        "creature",
        "사슴",
        x,
        z,
        hp=10.0,
        max_hp=10.0,
        # 게임의 사슴은 사람이 달리는 것(약 7m/s)보다 빠르다. 쫓아가서는 못 잡는다.
        speed=9.0,
        skittish=15.0,
        drops=[("날고기", 1), ("사슴 가죽", 1), ("사슴 트로피", 1)],
        key="$enemy_deer",
        size="medium",
    )


def eikthyr(x: float, z: float, id: str = "7:990") -> SimEntity:
    return SimEntity(
        id,
        "creature",
        "에이크쉬르",
        x,
        z,
        hp=500.0,
        max_hp=500.0,
        hostile=True,
        damage=10.0,
        speed=4.0,
        aggro=40.0,
        drops=[("에이크쉬르 트로피", 1)],
        key="$enemy_eikthyr",
        size="large",
        height=3.0,
        boss=True,
        ranged_m=18.0,
        ranged_damage=6.0,
    )


def pickable(name: str, gives: tuple[str, int], x: float, z: float, id: str) -> SimEntity:
    return SimEntity(id, "pickable", name, x, z, gives=gives)
