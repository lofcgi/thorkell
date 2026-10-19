"""Goals and decision records.

Tiers: P0 survival > P1 user request > P2 own agenda > P3 curiosity. The controller is the only
writer of goals; every adopt/suspend/resume/drop/speak becomes a Decision so that speech can only
refer to things the controller actually decided (PIANO-style coherence).
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from thorkell.lang import tr
from thorkell.mind.korean import josa


class Tier(IntEnum):
    SURVIVAL = 0
    USER = 1
    AGENDA = 2
    CURIOSITY = 3


_goal_ids = itertools.count(1)
_decision_ids = itertools.count(1)


@dataclass
class Goal:
    kind: str
    tier: Tier
    args: dict[str, Any] = field(default_factory=dict)
    source: str = "self"
    id: str = field(default_factory=lambda: f"g{next(_goal_ids)}")
    created: float = field(default_factory=time.monotonic)
    # Progress is measured from the world (e.g. items actually picked up), so a resumed goal continues.
    progress: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | active | suspended | done | failed | dropped
    outcome: str = ""

    def describe_ko(self) -> str:
        args = self.args
        match self.kind:
            case "gather_wood":
                count = f"({self.progress.get('gathered', 0)}/{args.get('count')})"
                return tr(f"나무 모으기 {count}", f"gathering Wood {count}")
            case "defend":
                return tr(
                    f"{args.get('name') or '적'}와 싸우기", f"fighting {args.get('name') or 'an enemy'}"
                )
            case "follow":
                return tr("따라가기", "following you")
            case "wait":
                return tr("제자리에서 기다리기", "waiting here")
            case "pick_up":
                return tr("건네준 것 받기", "taking what you handed me")
            case "retreat":
                return tr("물러나기", "falling back")
            case "eat":
                return tr(f"{args.get('item')} 먹기", f"eating {args.get('item')}")
            case "recover":
                return tr("묘비에서 내 물건 찾기", "getting my stuff back from my tombstone")
            case "gather":
                return tr(f"{args.get('item')} 모으기", f"gathering {args.get('item')}")
            case "craft":
                return tr(f"{args.get('item')} 만들기", f"making {args.get('item')}")
            case "build":
                return tr(f"{args.get('piece')} 짓기", f"building {args.get('piece')}")
            case "hunt":
                return tr(f"{args.get('creature')} 사냥", f"hunting {args.get('creature')}")
            case "search":
                return tr(f"{args.get('name')} 찾아보기", f"looking for {args.get('name')}")
            case "cook":
                return tr(f"{args.get('item')} 굽기", f"cooking {args.get('item')}")
            case "give":
                return tr(f"{args.get('item')} 건네기", f"handing over {args.get('item')}")
            case "use_portal":
                tag = f" ({args['tag']})" if args.get("tag") else ""
                return tr(f"포털로 건너가기{tag}", f"going through the portal{tag}")
            case "go_to":
                return tr(f"{args.get('place')}(으)로 가기", f"going to {args.get('place')}")
            case "shelter":
                return tr("작업대에 벽과 지붕 올리기", "putting up walls and a roof over the workbench")
            case "register_location":
                return tr("빛나는 돌 만져 보기", "touching the glowing stone")
            case "offer":
                return tr(f"제단에 {args.get('item')} 바치기", f"offering {args.get('item')} at the altar")
            case "sleep":
                return tr("침대에서 자기", "sleeping in a bed")
            case "fight":
                creature = str(args.get("creature"))
                return tr(f"{josa(creature, '과와')} 싸우기", f"fighting {creature}")
            case "request":
                plan = self.progress.get("plan")
                return (
                    plan.interpretation_ko
                    if plan is not None
                    else tr(
                        f"부탁 처리하기: {args.get('text')}", f"working on your request: {args.get('text')}"
                    )
                )
        return self.kind


@dataclass(frozen=True)
class Decision:
    kind: str  # adopt | suspend | resume | drop | done | fail | speak | threat | reflect
    goal_id: str | None
    reason_ko: str
    refs: tuple[str, ...] = ()
    goal_kind: str | None = None
    # speak: 채팅 종류(normal | shout | whisper). 속삭임은 가까이 있는 사람에게만 보인다.
    talker: str | None = None
    id: str = field(default_factory=lambda: f"d{next(_decision_ids)}")
    at: float = field(default_factory=time.monotonic)
