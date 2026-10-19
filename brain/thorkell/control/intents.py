"""Rule-based reading of the leader's chat (M3 baseline, no model).

M4/M6 replace this with the planner and the Live model's tool calls; until then these patterns let
the controller be exercised end to end. Anything not matched is left for the conversational layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# 한국어와 영어 모두 늘 알아듣는다. 영어는 단어 경계로만 잡는다(짧은 단어가 다른 말 속에서 잡히지 않게).
# "hold on"은 "잠깐, 확인해 볼게"처럼 멈추라는 뜻이 아닐 때가 많아 넣지 않는다.
STOP = re.compile(r"(멈춰|그만|정지|\bstop\b|\bhalt\b)", re.IGNORECASE)
# "어때"만으로는 잡지 않는다. "오늘 기분 어때?"는 잡담이다(플래너가 답한다). "how are you?"도 마찬가지다.
STATUS = re.compile(
    r"(뭐\s*해|뭐\s*하(고|는)|상태|잘\s*(돼|되)\s*가|어떻게\s*(돼|되)\s*가"
    r"|\bwhat(\s+are|['\u2019]re)\s+you\s+(doing|up\s+to)\b"
    r"|\bhow(['\u2019]s|\s+is)\s+(it|that|the\s+\w+)\s+going\b|\bstatus\b)",
    re.IGNORECASE,
)
# 영어는 나무를 해 오라는 동사가 있어야 한다. "we need wood for a house"만으로는 일을 시킨 것이 아니다.
WOOD = re.compile(
    r"(나무.*(캐|베|해|모아|구해|가져)|\b(chop|cut|gather|get|collect|bring|fetch)\b[^.?!]*\bwood\b)",
    re.IGNORECASE,
)
FOLLOW = re.compile(r"(따라\s*(와|오)|\bfollow\b|\bcome\s+(with|along\s+with)\s+(me|us)\b)", re.IGNORECASE)
WAIT = re.compile(r"(기다려|여기\s*있어|대기|\bwait\b|\bstay\s+(here|there|put)\b)", re.IGNORECASE)
# "take it easy"는 받으라는 말이 아니다.
PICK_UP = re.compile(
    r"(받아|주워|챙겨|가져가"
    r"|\btake\s+(it|this|that|these|them)\b(?!\s+(easy|slow))"
    r"|\bpick\s+(it|this|that|these|them)\s+up\b|\bpick\s+up\s+(it|this|that|these|them)\b"
    r"|\bgrab\s+(it|this|that|these|them)\b)",
    re.IGNORECASE,
)
# "did you sleep well?"은 자자는 말이 아니다. 영어는 자러 가자는 표현만 잡는다.
SLEEP = re.compile(
    r"(자자|자러\s*가|잘\s*시간|잠\s*자|눕자"
    r"|\blet['\u2019]?s\s+(go\s+to\s+)?sleep\b|\b(go|going|get|head)\s+to\s+(bed|sleep)\b"
    r"|\btime\s+(to\s+sleep|for\s+bed|to\s+go\s+to\s+bed)\b|\bbedtime\b)",
    re.IGNORECASE,
)
COUNT = re.compile(r"(\d+)\s*(개|개만|개쯤)?")


@dataclass(frozen=True)
class Intent:
    kind: str  # stop | status | gather_wood | follow | wait | pick_up | sleep
    count: int | None = None


def read(text: str) -> Intent | None:
    if STOP.search(text):
        return Intent("stop")
    if STATUS.search(text):
        return Intent("status")
    if WOOD.search(text):
        match = COUNT.search(text)
        return Intent("gather_wood", int(match.group(1)) if match else None)
    if SLEEP.search(text):
        return Intent("sleep")
    if FOLLOW.search(text):
        return Intent("follow")
    if WAIT.search(text):
        return Intent("wait")
    if PICK_UP.search(text):
        return Intent("pick_up")
    return None
