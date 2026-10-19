"""Thorkell's eyes: his own game screen, understood by a multimodal model (pixel vision).

2026-10-18 rehearsal: with only a list of named objects he could not see the portal in front of the leader,
took the leader's summoned root for a monster and could not find the way into a house. The user asked for
screen understanding like a person's, if fast enough (gemini-3.5-flash-lite: about 1.2 s for a 640x360 frame).
The body renders what Thorkell's camera sees (`look`); this asks what is there, in words, tied to the
things the game has already named (ids), so the planner and the fight judgment can act on it.
Quick reactions keep using the state (scene); this is for slow judgment.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from thorkell.body.session import BodySession
from thorkell.config import VisionConfig
from thorkell.lang import answer_from_model, schema_for_model, tr
from thorkell.models.gemini import Usage

SYSTEM = """너는 Valheim을 처음 해 보는 바이킹 Thorkell의 눈이다.
토르켈 자신의 게임 화면을 보고, 사람이 화면을 보고 아는 만큼 말한다.
- 이 게임을 미리 아는 척하지 않는다. 처음 보는 것은 생김새를 그대로 말한다
  (예: 돌 테두리 안에 빛나는 소용돌이).
- 그림에 실제로 보이는 것만 말한다. 안 보이는 것을 있는 것처럼 말하지 않는다. 어두우면 어둡다고 한다.
- [이름표]는 근처에 있다고 게임이 알려 준 것들이다. 그림에 안 보일 수도 있다(뒤, 나무 뒤, 어둠 속).
  그림에 보이는 것이 그중 하나면 그 id를 붙이고, 안 보이면 things에 넣지 않는다.
- 그림 가운데 아래쪽 뒷모습은 토르켈 자신이다(카메라가 어깨 뒤에 있다). 다른 사람 모습은 리더다.
- 건물은 벽·문·지붕이 어떻게 둘러져 있는지, 들어갈 수 있는 곳(열린 문, 빈 틈)이 어디인지 본다.
- 방향은 화면 기준(왼쪽, 가운데, 오른쪽, 앞, 멀리)으로, 거리는 짐작이면 '쯤'을 붙인다.
Return JSON only."""

SYSTEM_EN = """You are the eyes of Thorkell, a Viking playing Valheim for the first time.
Look at Thorkell's own game screen and say as much as a person would know from looking at it.
- Don't pretend to know this game. Describe something new by how it looks
  (e.g. a glowing swirl inside a stone frame).
- Say only what is really in the picture. Don't talk about what you can't see as if it were there. If it is
  dark, say it is dark.
- [Name tags] are things the game says are nearby. They may not be in the picture (behind, behind a tree, in
  the dark). If something in the picture is one of them, give its id; if it isn't visible, leave it out of
  things.
- The figure seen from behind at the bottom middle of the picture is Thorkell himself (the camera is behind
  his shoulder). Another person is the leader.
- For buildings, see how the walls, doors and roof go round, and where you can get in (an open door, a gap).
- Directions are by the screen (left, middle, right, ahead, far); add "about" to a guessed distance.
- Write in English.
Return JSON only."""

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary_ko": {"type": "string"},
        "things": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "what_ko": {"type": "string"},
                    "where_ko": {"type": "string"},
                    "id": {"type": ["string", "null"]},
                    "note_ko": {"type": "string"},
                },
                "required": ["what_ko", "where_ko"],
            },
        },
        "ways": {"type": "array", "items": {"type": "string"}},
        "leader_ko": {"type": ["string", "null"]},
    },
    "required": ["summary_ko", "things", "ways"],
}


class SeeingModel(Protocol):
    async def see_json(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        images: tuple[str, ...],
        resolution: str,
        schema: dict[str, Any],
        thinking: str,
        max_output_tokens: int,
    ) -> tuple[dict[str, Any], Usage]: ...


@dataclass(frozen=True)
class View:
    """What Thorkell made of his screen at one moment."""

    summary_ko: str
    things: list[dict[str, Any]]
    ways: list[str]
    leader_ko: str | None
    yaw: float
    at: float = field(default_factory=time.monotonic)
    frame_ms: float = 0.0
    seeing_s: float = 0.0

    def lines(self) -> list[str]:
        """The view in a few lines, for another prompt."""
        out = [self.summary_ko]
        for thing in self.things:
            tag = f" [{thing['id']}]" if thing.get("id") else ""
            note = f" — {thing['note_ko']}" if thing.get("note_ko") else ""
            out.append(f"- {thing['what_ko']}{tag}: {thing['where_ko']}{note}")
        if self.ways:
            out.append(tr("지나갈 수 있는 곳: ", "Ways through: ") + ", ".join(self.ways))
        if self.leader_ko:
            out.append(tr("리더: ", "Leader: ") + self.leader_ko)
        return out


def _off_screen() -> str:
    return tr("화면 밖", "off screen")


def on_screen(bearing: float, fov_v: float, width: int, height: int) -> str:
    """Where a direction falls on the screen: left/centre/right, or off it (a person sees only the screen)."""
    half = math.degrees(math.atan(math.tan(math.radians(fov_v) / 2) * width / height))
    if abs(bearing) > half:
        side = tr("오른쪽", "right") if bearing > 0 else tr("왼쪽", "left")
        return _off_screen() + " " + side + ("" if abs(bearing) < 120 else tr(" 뒤", " behind"))
    third = half / 3
    if bearing < -third:
        return tr("화면 왼쪽", "screen left")
    return tr("화면 오른쪽", "screen right") if bearing > third else tr("화면 가운데", "screen middle")


def labels(session: BodySession, yaws: list[float], fov_v: float, width: int, height: int) -> list[str]:
    """Things the game has named around Thorkell, with which picture (and where in it) they would fall."""
    here = session.state.data["pos"] if session.state else [0.0, 0.0, 0.0]
    out = []
    for entity in session.nearby():
        if not entity.get("name") or entity.get("kind") == "player":
            continue
        dx, dz = float(entity["pos"][0]) - here[0], float(entity["pos"][2]) - here[2]
        heading = math.degrees(math.atan2(dx, dz))
        where = tr("어느 그림에도 안 걸림", "in no picture")
        for index, yaw in enumerate(yaws, start=1):
            spot = on_screen((heading - yaw + 180) % 360 - 180, fov_v, width, height)
            if not spot.startswith(_off_screen()):
                where = tr(
                    f"그림 {index} " + spot.removeprefix("화면 "),
                    f"picture {index} " + spot.removeprefix("screen "),
                )
                break
        distance = round(float(entity["distance"]))
        out.append(f"- {entity['id']} {entity['name']} ({entity['kind']}) {distance}m, {where}")
    return out


class Eyes:
    def __init__(self, session: BodySession, model: SeeingModel, config: VisionConfig) -> None:
        self.session = session
        self.model = model
        self.config = config
        self.usage: list[Usage] = []
        self.last: View | None = None

    async def look(
        self, question_ko: str | None = None, *, toward: list[float] | None = None, around: bool = False
    ) -> View:
        """Take what the camera sees now and say what is there (and answer a question about it, if any).
        `toward`: turn the view to that point first (where the leader points, a sound). `around`: look all
        round (four pictures), as a person turns the camera when asked what they can see."""
        args: dict[str, Any] = {"width": FRAME_W, "height": FRAME_H, "quality": FRAME_QUALITY}
        if toward is not None:
            args["toward"] = toward
        elif around:
            args["turn"] = list(AROUND)
        frame = await self.session.query("look", args, timeout=LOOK_TIMEOUT_S)
        if not frame.ok or frame.data is None:
            raise SightError(f"look failed: {frame.error}")
        data = frame.data
        pictures = data["frames"]
        yaws = [float(p["yaw"]) for p in pictures]
        named = labels(self.session, yaws, float(data["fov"]), int(data["width"]), int(data["height"]))
        picture = tr("그림", "picture")
        order = (
            f"{picture} 1"
            if len(pictures) == 1
            else ", ".join(f"{picture} {i}: {facing(y - yaws[0])}" for i, y in enumerate(yaws, start=1))
        )
        prompt = tr(
            f"[그림] {order}\n\n"
            "[이름표] 근처에 있다고 게임이 알려 준 것들(id, 이름, 종류, 거리, 걸릴 그림)."
            " 그림에 안 보일 수 있다\n"
            + ("\n".join(named) or "(없음)")
            + "\n\n[물음]\n그림에 보이는 것을 말해. summary_ko: 한두 문장."
            " things: 눈에 띄는 것마다 what_ko(무엇), where_ko(어디),"
            " id(이름표 중 하나면), note_ko(특이한 점)."
            " ways: 지나갈 수 있는 길·입구."
            " leader_ko: 리더가 보이면 무엇을 하고 어디를 보는지."
            + (f"\n특히: {question_ko}" if question_ko else ""),
            f"[Pictures] {order}\n\n"
            "[Name tags] Things the game says are nearby (id, name, kind, distance, the picture they would be"
            " in). They may not be visible in the picture\n"
            + ("\n".join(named) or "(none)")
            + "\n\n[Question]\nSay what is in the pictures. summary_en: one or two sentences."
            " things: for each thing that stands out, what_en (what), where_en (where),"
            " id (if it is one of the name tags), note_en (anything unusual)."
            " ways: paths and entrances you could go through."
            " leader_en: if the leader is visible, what they are doing and where they are looking."
            + (f"\nIn particular: {question_ko}" if question_ko else ""),
        )
        began = time.monotonic()
        answer, usage = await self.model.see_json(
            model=self.config.model,
            system=tr(SYSTEM, SYSTEM_EN),
            prompt=prompt,
            images=tuple(str(p["jpeg"]) for p in pictures),
            resolution=self.config.resolution,
            schema=schema_for_model(SCHEMA),
            thinking=self.config.thinking,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        self.usage.append(usage)
        answer = answer_from_model(answer)
        self.last = View(
            summary_ko=str(answer.get("summary_ko", "")),
            things=[t for t in answer.get("things", []) if isinstance(t, dict)],
            ways=[str(w) for w in answer.get("ways", [])],
            leader_ko=answer.get("leader_ko"),
            yaw=yaws[0],
            frame_ms=float(data.get("ms", 0.0)),
            seeing_s=round(time.monotonic() - began, 2),
        )
        return self.last


class SightError(Exception):
    pass


def facing(turn: float) -> str:
    turn = (turn + 180) % 360 - 180
    if abs(turn) < 30:
        return tr("앞", "ahead")
    if abs(turn) > 150:
        return tr("뒤", "behind")
    return tr("오른쪽", "right") if turn > 0 else tr("왼쪽", "left")


# 둘러볼 때 지금 화면에서 돌려 보는 각도(앞, 오른쪽, 뒤, 왼쪽).
AROUND = (0, 90, 180, -90)


# 몸 창(640x360)과 같은 크기. 줄이면 작은 것(멀리 있는 포탈)을 못 본다.
FRAME_W, FRAME_H, FRAME_QUALITY = 640, 360, 70
LOOK_TIMEOUT_S = 5.0
MAX_OUTPUT_TOKENS = 800
