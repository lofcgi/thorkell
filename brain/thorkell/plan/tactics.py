"""How to face a creature, and what a fight taught: the slow brain's judgment (gemini-3.8-flash).

Code only decides when to think: something big has noticed Thorkell, or a fight has ended. The model decides
what the creature seems to be, how to fight it, and what to take from how the fight went. What it takes is
kept as text lessons in Thorkell's own memory (`Store.add_lesson`) with the episode it came from, and each
later fight that follows a lesson says whether it held. No creature-specific tactic lives in code.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

from thorkell import lang
from thorkell.lang import answer_from_model, schema_for_model, tr
from thorkell.mind.korean import damage_name, josa
from thorkell.mind.store import Episode, Lesson, general
from thorkell.models.gemini import JsonModel, Usage
from thorkell.plan.planner import PlannerConfig

log = logging.getLogger(__name__)

STYLES = ("ranged", "melee", "keep_away", "leave")
DOING_KO = {
    "shoot": "쏘기",
    "back_off": "물러나기",
    "roll": "구르기",
    "approach": "다가가기",
    "wait": "기다리기",
    "eat": "먹기",
    "other": "끼어든 놈 상대",
    "swing": "휘두르기",
    "reposition": "자리 옮기기",
}
DOING_EN = {
    "shoot": "shooting",
    "back_off": "backing off",
    "roll": "rolling",
    "approach": "closing in",
    "wait": "waiting",
    "eat": "eating",
    "other": "fighting another one",
    "swing": "swinging",
    "reposition": "repositioning",
}
AFTER_DEATH = ("alone", "with_leader")
DISTANCE_RANGE_M = (1.0, 60.0)
HITS_RANGE = (1, 10)
MAX_NEW_LESSONS = 3

SYSTEM = """너는 Valheim을 처음 해 보는 바이킹 Thorkell의 생각이다.
리더(사람 플레이어)와 같이 첫 보스까지 가는 동료다.
판단 원칙:
- 네가 아는 것은 아래에 나온 것(보이는 것, 내 상태, 싸운 기억, 교훈)뿐이다.
  이 게임 고유의 지식(어떤 몬스터가 어떤 공격을 하는지, 약점, 보스 패턴)은 미리 아는 척하지 않는다.
  사람이면 누구나 아는 일반 상식은 써도 된다.
- [교훈]은 네가 직접 겪고 얻은 것이다. 상식보다 교훈을 믿는다. 틀렸다고 판정된 교훈은 보여 주지 않는다.
- 거리는 m, 체력은 남은 비율(0~1)이다.
- 말(speech_ko)은 리더에게 하는 한두 마디다. 반말, 짧고 친근하게.
Return JSON only."""

SYSTEM_EN = """You are the thoughts of Thorkell, a Viking playing Valheim for the first time.
He is the companion of the leader (a human player), and they are going to the first boss together.
How to judge:
- All you know is what is shown below (what you see, your own state, fights you remember, lessons).
  Don't pretend to know things specific to this game in advance (what attacks a monster has, weaknesses,
  boss patterns). Common sense that anyone has is fine.
- [Lessons] are what you learned yourself, the hard way. Trust lessons over common sense. Lessons judged
  wrong are not shown.
- Distances are in m, health is the fraction left (0-1).
- The words (speech_en) are one or two lines to the leader. Casual, short and friendly.
- Write in English.
Return JSON only."""

TACTIC_TASK = """[물음]
저게 뭐로 보이는지(impression_ko), 싸울 상대인지, 어떻게 싸울지 정해.
- style: ranged(활로 거리를 두고 쏜다) | melee(붙어서 친다)
  | keep_away(싸우지 않고 거리를 두며 리더에게 알린다)
  | leave(싸울 상대가 아니다: 리더의 것, 길들인 것, 위험하지 않은 것. 건드리지 않고 하던 일을 한다)
- keep_m: ranged면 쏘면서 지키려는 거리. 이보다 가까우면 활을 당기면서 옆·뒤로 걷는다(당기며 걸을 수 있다).
  melee면 몇 번 치고 물러날 거리, keep_away면 머물 거리
- close_m: 이 안으로 들어오면 쏘지 않고 달려서 keep_m까지 물러난다(ranged·keep_away). keep_m보다 작아야 한다.
  쫓아오는 상대에게서는 달려도 거리가 잘 안 벌어지고, 그동안은 쏘지 못한다
- retreat_hp / return_hp: 체력이 retreat_hp 아래면 물러나 먹으며 회복하고 return_hp 위가 되면 돌아간다
- hits_then_back: melee에서 이만큼 치고 한 번 물러난다
- eat_first: 싸우기 전에 빈 음식 칸을 채울지
- dodge_within_m: 상대가 공격 동작을 시작하는 게 보이면(몸을 젖히거나 뿔을 숙인다) 이 거리 안에서는
  하던 것을 멈추고 옆으로 구른다. 0이면 구르지 않는다. 구르면 스태미나를 쓴다
- retreat_to_leader: 물러날 때 리더 쪽으로 갈지. 리더가 같이 싸워 줄 수 있으면 true.
  리더가 싸울 수 없거나 끌어들이면 안 되면 false(상대에게서 곧장 멀어진다)
- cites: 따른 교훈의 id(L…)"""

TACTIC_TASK_EN = """[Question]
Decide what that looks like (impression_en), whether it is something to fight, and how to fight it.
- style: ranged (keep your distance and shoot with the bow) | melee (get close and hit)
  | keep_away (don't fight; keep your distance and tell the leader)
  | leave (not something to fight: the leader's, tamed, or not dangerous. Leave it alone and carry on)
- keep_m: for ranged, the distance to hold while shooting. Closer than this, walk sideways or back while
  drawing the bow (you can walk while drawing). For melee, how far to back off after a few hits; for
  keep_away, the distance to stay at
- close_m: if it comes inside this, stop shooting and run back to keep_m (ranged, keep_away). Must be less
  than keep_m. Running rarely opens the gap on something chasing you, and you can't shoot meanwhile
- retreat_hp / return_hp: below retreat_hp health, back off and eat to recover; go back above return_hp
- hits_then_back: in melee, back off once after this many hits
- eat_first: whether to fill empty food slots before the fight
- dodge_within_m: when you see it start an attack (rearing up, lowering its antlers), within this distance
  stop what you're doing and roll sideways. 0 means never roll. Rolling uses stamina
- retreat_to_leader: whether to back off toward the leader. true if the leader can fight alongside you.
  false if the leader can't fight or must not be dragged in (back straight away from it)
- cites: ids (L…) of the lessons you followed"""

REFLECT_TASK = """[물음]
이 싸움을 돌아봐.
- what_happened_ko: 시간 순서로 무슨 일이 있었는지 두세 문장. 무엇이 통했고(상대 체력바가 줄었다)
  무엇이 안 통했는지(맞기만 했다, 물러나 있어도 내 체력이 안 찼다, 그동안 상대가 회복했다) 기록의 숫자를 들어
- lessons: 다음에 다르게 하거나 계속할 것. 안 통한 것은 바꾸고 통한 것은 이어 간다.
  기록의 숫자를 근거로 넣는다. 이미 있는 교훈과 같은 말은 다시 쓰지 않는다.
  about은 상대 이름이거나, 어떤 싸움에나 해당하면 "일반". 많아야 3개, 배울 게 없으면 비워 둔다
- verdicts: [따른 교훈]마다, 그리고 따른다고 하지 않았어도 이번 싸움으로 맞았는지 틀렸는지 드러난
  [지금 교훈]마다 맞았는지(held)와 이유. 그 교훈대로 했는데 안 통했으면 held=false
- after_death: 죽었을 때만. 지금 혼자 물건을 찾으러 갈지(alone) 리더와 같이 갈지(with_leader)
- speech_ko: 리더에게 할 말(무엇을 배웠는지)"""

REFLECT_TASK_EN = """[Question]
Look back on this fight.
- what_happened_en: two or three sentences, in order, about what happened. What worked (its health bar went
  down) and what didn't (I only got hit, my health didn't come back while I stayed back, it healed meanwhile),
  with the numbers from the record
- lessons: what to do differently next time, or keep doing. Change what didn't work, keep what did.
  Give the numbers from the record as grounds. Don't write again what an existing lesson already says.
  about is the creature's name, or "{general}" if it applies to any fight. At most 3; leave it empty if there
  is nothing to learn
- verdicts: for each [Lessons followed], and for each [Current lessons] this fight showed right or wrong
  even if you didn't say you followed it, whether it held (held) and why. If you did as the lesson said and
  it didn't work, held=false
- after_death: only if you died. Whether to go get your things alone now (alone) or with the leader
  (with_leader)
- speech_en: what to tell the leader (what you learned)"""


class Tactic(BaseModel):
    impression_ko: str
    style: str
    keep_m: float
    close_m: float
    retreat_hp: float
    return_hp: float
    hits_then_back: int
    eat_first: bool
    retreat_to_leader: bool
    dodge_within_m: float
    speech_ko: str
    cites: list[str] = Field(default_factory=list)


class NewLesson(BaseModel):
    about: str
    text_ko: str


class Verdict(BaseModel):
    lesson_id: str
    held: bool
    why_ko: str = ""


class Reflection(BaseModel):
    what_happened_ko: str
    lessons: list[NewLesson] = Field(default_factory=list)
    verdicts: list[Verdict] = Field(default_factory=list)
    after_death: str | None = None
    speech_ko: str


TACTIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "impression_ko": {"type": "string"},
        "style": {"type": "string", "enum": list(STYLES)},
        "keep_m": {"type": "number"},
        "close_m": {"type": "number"},
        "retreat_hp": {"type": "number"},
        "return_hp": {"type": "number"},
        "hits_then_back": {"type": "integer"},
        "eat_first": {"type": "boolean"},
        "retreat_to_leader": {"type": "boolean"},
        "dodge_within_m": {"type": "number"},
        "speech_ko": {"type": "string"},
        "cites": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "impression_ko",
        "style",
        "keep_m",
        "close_m",
        "retreat_hp",
        "return_hp",
        "hits_then_back",
        "eat_first",
        "retreat_to_leader",
        "dodge_within_m",
        "speech_ko",
    ],
}

REFLECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "what_happened_ko": {"type": "string"},
        "lessons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"about": {"type": "string"}, "text_ko": {"type": "string"}},
                "required": ["about", "text_ko"],
            },
        },
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lesson_id": {"type": "string"},
                    "held": {"type": "boolean"},
                    "why_ko": {"type": "string"},
                },
                "required": ["lesson_id", "held"],
            },
        },
        "after_death": {"type": ["string", "null"]},
        "speech_ko": {"type": "string"},
    },
    "required": ["what_happened_ko", "lessons", "verdicts", "speech_ko"],
}


@dataclass(frozen=True)
class FightView:
    """What Thorkell perceives as a fight begins, in words (only what his own screen shows)."""

    creature: str
    seen_ko: str
    me_ko: str
    leader_ko: str
    has_bow: bool
    sight_ko: str = ""  # 토르켈 자신의 화면을 본 것(Eyes). 눈이 없으면 비어 있다


class JudgmentRejected(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def check_tactic(tactic: Tactic, has_bow: bool, lesson_ids: set[str]) -> list[str]:
    problems: list[str] = []
    low, high = DISTANCE_RANGE_M
    if tactic.style not in STYLES:
        problems.append(f"style must be one of {', '.join(STYLES)}")
    if tactic.style == "leave":
        # 건드리지 않기로 했으면 거리·체력 기준은 쓰지 않는다.
        return problems + ([] if tactic.speech_ko.strip() else ["speech_ko is empty"])
    if tactic.style == "ranged" and not has_bow:
        problems.append("ranged needs a bow and arrows, and there are none in the bag")
    if not low <= tactic.keep_m <= high:
        problems.append(f"keep_m must be {low:g}~{high:g} m")
    if tactic.style != "melee" and not low <= tactic.close_m < tactic.keep_m:
        problems.append(f"close_m must be at least {low:g} m and less than keep_m")
    if not 0 < tactic.retreat_hp < tactic.return_hp <= 1:
        problems.append("need 0 < retreat_hp < return_hp <= 1 (fractions of health, not points)")
    if not 0 <= tactic.dodge_within_m <= high:
        problems.append(f"dodge_within_m must be 0~{high:g} m (0: do not roll)")
    if tactic.style == "melee" and not HITS_RANGE[0] <= tactic.hits_then_back <= HITS_RANGE[1]:
        problems.append(f"hits_then_back must be {HITS_RANGE[0]}~{HITS_RANGE[1]}")
    unknown = sorted(set(tactic.cites) - lesson_ids)
    if unknown:
        problems.append(f"cites lessons that are not shown: {', '.join(unknown)}")
    if not tactic.speech_ko.strip():
        problems.append("speech_ko is empty")
    return problems


def check_reflection(reflection: Reflection, died: bool, abouts: set[str], lesson_ids: set[str]) -> list[str]:
    problems: list[str] = []
    if len(reflection.lessons) > MAX_NEW_LESSONS:
        problems.append(f"at most {MAX_NEW_LESSONS} new lessons")
    for lesson in reflection.lessons:
        if lesson.about not in abouts:
            problems.append(
                f"lesson about '{lesson.about}': about must be one of {', '.join(sorted(abouts))}"
            )
        if not lesson.text_ko.strip():
            problems.append("a lesson has no text")
    unknown = sorted({v.lesson_id for v in reflection.verdicts} - lesson_ids)
    if unknown:
        problems.append(f"verdicts on lessons that are not shown: {', '.join(unknown)}")
    if died and reflection.after_death not in AFTER_DEATH:
        problems.append(f"after_death must be one of {', '.join(AFTER_DEATH)} (Thorkell died)")
    if not reflection.speech_ko.strip():
        problems.append("speech_ko is empty")
    return problems


def tactic_ko(tactic: dict[str, Any]) -> str:
    if lang.current() == "en":
        return _tactic_en(tactic)
    style = tactic.get("style")
    if style == "leave":
        return "싸우지 않고 그냥 둠"
    if style == "melee":
        head = f"붙어서 {tactic.get('hits_then_back')}번 치고 {tactic.get('keep_m'):g}m 물러나기"
    elif style == "keep_away":
        head = f"싸우지 않고 {tactic.get('keep_m'):g}m 밖에 머물기"
    else:
        head = f"활로 {tactic.get('keep_m'):g}m 거리 두기, {tactic.get('close_m'):g}m 안이면 물러나기"
    low, high = round(tactic["retreat_hp"] * 100), round(tactic["return_hp"] * 100)
    hp = f"체력 {low}% 아래면 물러나 회복, {high}%에서 복귀"
    eat = "빈 음식 칸부터 채우기" if tactic.get("eat_first") else "음식 칸을 더 채우지 않고 바로"
    parts = [head, hp, eat]
    if tactic.get("dodge_within_m"):
        parts.append(f"공격 동작이 보이면 {tactic['dodge_within_m']:g}m 안에서 구르기")
    if "retreat_to_leader" in tactic:
        parts.append("리더 쪽으로 물러나기" if tactic["retreat_to_leader"] else "리더 쪽으로 끌고 가지 않기")
    return ", ".join(parts)


def _tactic_en(tactic: dict[str, Any]) -> str:
    style = tactic.get("style")
    if style == "leave":
        return "left it alone, no fight"
    if style == "melee":
        head = f"up close, {tactic.get('hits_then_back')} hits then back off {tactic.get('keep_m'):g} m"
    elif style == "keep_away":
        head = f"no fight, stay {tactic.get('keep_m'):g} m away"
    else:
        head = f"bow from {tactic.get('keep_m'):g} m, back off if inside {tactic.get('close_m'):g} m"
    low, high = round(tactic["retreat_hp"] * 100), round(tactic["return_hp"] * 100)
    parts = [head, f"below {low}% health back off and recover, return at {high}%"]
    parts.append(
        "fill empty food slots first" if tactic.get("eat_first") else "straight in without more food"
    )
    if tactic.get("dodge_within_m"):
        parts.append(f"roll when an attack starts within {tactic['dodge_within_m']:g} m")
    if "retreat_to_leader" in tactic:
        parts.append(
            "back off toward the leader" if tactic["retreat_to_leader"] else "don't lead it to the leader"
        )
    return ", ".join(parts)


def _doing(what: str) -> str:
    return tr(DOING_KO.get(what, what), DOING_EN.get(what, what))


def episode_line(episode: Episode) -> str:
    """One line per earlier fight, for the tactic prompt."""
    record = episode.record
    hits = record.get("hits", [])
    shots = record.get("shots", {})
    fired = sum(shots.values())
    landed = shots.get("hit", 0) + shots.get("killed", 0)
    bar = record.get("health", [])
    seconds = round(record.get("seconds", 0))
    parts = [
        tr(f"{episode.id} ({episode.outcome}, {seconds}초)", f"{episode.id} ({episode.outcome}, {seconds} s)")
    ]
    known = [h[2] for h in hits if h[2] is not None and h[2] >= 0]
    if hits:
        span = f"{min(known):g}~{max(known):g}m" if known else ""
        parts.append(
            tr(
                f"맞은 것 {len(hits)}번" + (f"({span}에서)" if known else ""),
                f"got hit {len(hits)} times" + (f" (at {span})" if known else ""),
            )
        )
    else:
        parts.append(tr("한 번도 안 맞음", "never got hit"))
    if fired:
        # 쏘자마자 다음 화살로 넘어간 발("fired")은 맞았는지 모른다. 맞은 것은 상대 체력바로 본다.
        judged = landed + shots.get("missed", 0)
        parts.append(
            tr(
                f"화살 {fired}발" + (f" 중 {landed}발 맞힘" if judged else ""),
                f"{fired} arrows" + (f", {landed} hit" if judged else ""),
            )
        )
    blocked = shots.get("no_line_of_sight", 0)
    if blocked:
        parts.append(tr(f"시야가 막혀 못 쏜 것 {blocked}번", f"{blocked} shots blocked (no line of sight)"))
    if bar:
        start, end = round(bar[0][1] * 100), round(bar[-1][1] * 100)
        parts.append(tr(f"상대 체력 {start}%→{end}%", f"its health {start}%→{end}%"))
    if record.get("recovering_s"):
        away = round(record["recovering_s"])
        parts.append(tr(f"물러나 있던 시간 {away}초", f"{away} s spent backed off"))
    if record.get("time"):
        spent = sorted(record["time"].items(), key=lambda item: -item[1][1])
        unit = tr("초", " s")
        parts.append(
            tr("한 일: ", "time spent: ")
            + ", ".join(f"{_doing(what)} {round(secs)}{unit}" for what, (_, secs) in spent)
        )
    if record.get("leader_fell_s") is not None:
        fell = round(record["leader_fell_s"])
        parts.append(tr(f"리더가 {fell}초에 쓰러짐", f"the leader fell at {fell} s"))
    if record.get("others"):
        others = len(record["others"])
        parts.append(tr(f"다른 놈에게 맞은 것 {others}번", f"hit by others {others} times"))
    if "tactic" in record:
        parts.append(tr("쓴 방법: ", "how I fought: ") + tactic_ko(record["tactic"]))
    return ", ".join(parts)


def record_ko(episode: Episode) -> str:
    """The whole record of one fight, for reflection."""
    record = episode.record
    s = tr("초", " s")
    looks = f" ({record['looks']})" if record.get("looks") else ""
    lines = [tr(f"상대: {episode.about}{looks}", f"Opponent: {episode.about}{looks}")]
    if "tactic" in record:
        lines.append(tr("쓴 방법: ", "How I fought: ") + tactic_ko(record["tactic"]))
        lines.append(
            tr("그렇게 본 이유: ", "Why I saw it that way: ") + record["tactic"].get("impression_ko", "")
        )
    for at, changed in record.get("tactic_changes", []):
        lines.append(tr(f"{at:g}초에 바꾼 방법: ", f"Changed at {at:g} s to: ") + tactic_ko(changed))
    seconds = round(record.get("seconds", 0))
    lines.append(tr(f"결과: {episode.outcome} ({seconds}초)", f"Result: {episode.outcome} ({seconds} s)"))
    if record.get("leader_fell_s") is not None:
        fell = record["leader_fell_s"]
        lines.append(tr(f"리더가 쓰러진 때: {fell:g}초", f"The leader fell at: {fell:g} s"))
    if record.get("ate"):
        lines.append(tr("싸우기 전에 먹은 것: ", "Ate before the fight: ") + ", ".join(record["ate"]))
    slots = record.get("food_slots", "?")
    lines.append(tr(f"음식 칸: 싸움에 들어갈 때 {slots}칸", f"Food slots: {slots} going into the fight"))
    hits = record.get("hits", [])
    lines.append(
        tr(
            f"맞은 것: {len(hits)}번" + (" (경과 초, 피해, 그때 상대와 거리, 피해 종류)" if hits else ""),
            f"Got hit: {len(hits)} times"
            + (" (seconds in, damage, distance to it then, damage type)" if hits else ""),
        )
    )
    for at, amount, distance, kinds in hits:
        where = [
            f"{distance:g}m"
            if distance is not None and distance >= 0
            else tr("거리 모름", "distance unknown")
        ]
        where += ["·".join(damage_name(k) for k in kinds)] if kinds else []
        lines.append(f"  {at:g}{s} {amount:g} ({', '.join(where)})")
    if record.get("attackers"):
        lines.append(tr("때린 것: ", "What hit me: ") + ", ".join(record["attackers"]))
    others = record.get("others", [])
    if others:
        by: dict[str, list[float]] = {}
        for _, amount, who, _kinds in others:
            by.setdefault(who, []).append(amount)
        lines.append(
            tr(
                "다른 놈에게 맞은 것: "
                + ", ".join(f"{who} {len(amounts)}번(모두 {sum(amounts):g})" for who, amounts in by.items())
                + f" (처음 {others[0][0]:g}초, 마지막 {others[-1][0]:g}초)",
                "Hit by others: "
                + ", ".join(
                    f"{who} {len(amounts)} times ({sum(amounts):g} in all)" for who, amounts in by.items()
                )
                + f" (first at {others[0][0]:g} s, last at {others[-1][0]:g} s)",
            )
        )
    if record.get("handled"):
        lines.append(
            tr("싸우다 먼저 상대한 다른 놈: ", "Others I dealt with first: ") + ", ".join(record["handled"])
        )
    if record.get("time"):
        spent = sorted(record["time"].items(), key=lambda item: -item[1][1])
        lines.append(
            tr(
                "한 일: " + ", ".join(f"{_doing(what)} {n}번 {round(secs)}초" for what, (n, secs) in spent),
                "Time spent: "
                + ", ".join(f"{_doing(what)} {n} times {round(secs)} s" for what, (n, secs) in spent),
            )
        )
    if record.get("saw_attacks"):
        seen, dodged = record["saw_attacks"], record.get("dodged", 0)
        lines.append(
            tr(
                f"상대의 공격 동작을 본 것: {seen}번, 보고 구른 것: {dodged}번",
                f"Saw it start an attack: {seen} times, rolled away: {dodged} times",
            )
        )
    shots = record.get("shots", {})
    if shots:
        lines.append(
            tr("쏜 것: ", "Shots: ") + ", ".join(f"{code} {count}" for code, count in sorted(shots.items()))
        )
    if record.get("swings"):
        lines.append(tr(f"휘두른 것: {record['swings']}번", f"Swings: {record['swings']}"))
    if record.get("retreats"):
        away = round(record.get("recovering_s", 0))
        lines.append(
            tr(
                f"체력이 낮아 물러난 것: {record['retreats']}번, 모두 {away}초(그동안은 싸우지 않았다)",
                f"Backed off on low health: {record['retreats']} times, {away} s in all "
                "(not fighting meanwhile)",
            )
        )
    bar = record.get("health", [])
    if bar:
        lines.append(
            tr("상대 체력바: ", "Its health bar: ")
            + ", ".join(f"{at:g}{s} {round(frac * 100)}%" for at, frac in bar[:: max(1, len(bar) // 8)])
        )
    mine = record.get("my_health", [])
    if mine:
        shown = mine[:: max(1, len(mine) // 10)]
        shown += [] if shown[-1] is mine[-1] else [mine[-1]]
        lines.append(
            tr("내 체력: ", "My health: ")
            + ", ".join(f"{at:g}{s} {round(frac * 100)}%" for at, frac in shown)
        )
    lowest = round(record.get("my_hp_min", 1.0) * 100)
    lines.append(tr(f"내 체력 최저: {lowest}%", f"My lowest health: {lowest}%"))
    if record.get("leader_m") is not None:
        lines.append(
            tr(
                f"리더와 거리(시작할 때): {record['leader_m']:g}m",
                f"Distance to the leader (at the start): {record['leader_m']:g} m",
            )
        )
    return "\n".join(lines)


Answer = TypeVar("Answer", Tactic, Reflection)


class Tactician:
    def __init__(self, model: JsonModel, config: PlannerConfig | None = None) -> None:
        self.model = model
        self.config = config or PlannerConfig()
        self.usage: list[Usage] = []

    async def tactic(self, view: FightView, earlier: list[Episode], lessons: list[Lesson]) -> Tactic:
        fought = "\n".join(f"- {episode_line(e)}" for e in earlier)
        learned = "\n".join(f"- {lesson.line()}" for lesson in lessons)
        if lang.current() == "en":
            prompt = (
                f"[What I see]\n{view.seen_ko}\n\n"
                + (f"[Screen]\n{view.sight_ko}\n\n" if view.sight_ko else "")
                + f"[Me]\n{view.me_ko}\n\n[Leader]\n{view.leader_ko}\n\n"
                f"[Fights I remember with {view.creature}]\n{fought or '(first time I see it)'}\n\n"
                f"[Lessons]\n{learned or '(none yet)'}\n\n{TACTIC_TASK_EN}"
            )
        else:
            prompt = (
                f"[보이는 것]\n{view.seen_ko}\n\n"
                + (f"[화면]\n{view.sight_ko}\n\n" if view.sight_ko else "")
                + f"[나]\n{view.me_ko}\n\n[리더]\n{view.leader_ko}\n\n"
                f"[{josa(view.creature, '과와')} 싸운 기억]\n"
                + (fought or "(처음 본다)")
                + "\n\n[교훈]\n"
                + (learned or "(아직 없음)")
                + f"\n\n{TACTIC_TASK}"
            )
        ids = {lesson.id for lesson in lessons}
        return await self._ask(prompt, TACTIC_SCHEMA, Tactic, lambda t: check_tactic(t, view.has_bow, ids))

    async def reflect(
        self, episode: Episode, earlier: list[Episode], lessons: list[Lesson], followed: list[str]
    ) -> Reflection:
        died = episode.outcome == "died"
        shown = {lesson.id: lesson for lesson in lessons}
        fought = "\n".join(f"- {episode_line(e)}" for e in earlier)
        learned = "\n".join(f"- {lesson.line()}" for lesson in lessons)
        kept = ", ".join(i for i in followed if i in shown)
        if lang.current() == "en":
            prompt = (
                f"[Fight record {episode.id}]\n{record_ko(episode)}\n\n"
                f"[Earlier fights]\n{fought or '(none)'}\n\n"
                f"[Current lessons]\n{learned or '(none yet)'}\n\n[Lessons followed]\n{kept or '(none)'}\n\n"
                + REFLECT_TASK_EN.replace("{general}", general())
            )
        else:
            prompt = (
                f"[싸움 기록 {episode.id}]\n{record_ko(episode)}\n\n[전에 싸운 기록]\n"
                + (fought or "(없음)")
                + "\n\n[지금 교훈]\n"
                + (learned or "(아직 없음)")
                + "\n\n[따른 교훈]\n"
                + (kept or "(없음)")
                + f"\n\n{REFLECT_TASK}"
            )
        abouts = {episode.about, general()}
        ids = set(shown)
        return await self._ask(
            prompt, REFLECTION_SCHEMA, Reflection, lambda r: check_reflection(r, died, abouts, ids)
        )

    async def _ask(self, prompt: str, schema: dict[str, Any], kind: type[Answer], check: Any) -> Answer:
        """One answer, with one repair attempt carrying the problems (like the planner)."""
        problems: list[str] = []
        for attempt in range(2):
            asked = prompt
            if problems:
                asked += tr(
                    "\n\n[이전 답의 문제 — 고쳐서 다시]\n",
                    "\n\n[Problems with the last answer — fix them and try again]\n",
                ) + "\n".join(f"- {p}" for p in problems)
            data, usage = await self.model.generate_json(
                model=self.config.model,
                system=tr(SYSTEM, SYSTEM_EN),
                prompt=asked,
                schema=schema_for_model(schema),
                thinking=self.config.thinking,
                max_output_tokens=self.config.max_output_tokens,
            )
            self.usage.append(usage)
            data = answer_from_model(data)
            try:
                answer = kind.model_validate(data)
            except ValidationError as error:
                problems = [f"schema: {e['loc']}: {e['msg']}" for e in error.errors()]
                log.warning(
                    "%s attempt %d did not match the schema: %s", kind.__name__, attempt + 1, problems
                )
                continue
            problems = check(answer)
            if not problems:
                return answer
            log.warning(
                "%s attempt %d rejected: %s | %s",
                kind.__name__,
                attempt + 1,
                problems,
                json.dumps(data, ensure_ascii=False),
            )
        raise JudgmentRejected(problems)
