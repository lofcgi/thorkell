"""The simulator in English: the names and messages the English game shows, at the body's edge.

The simulated world keeps its own (Korean) names inside. What it reports goes out under the names the game
uses in English (from the game's localization table, Valheim 1.0.20), and names in the brain's commands come
back to the world's own. A test of English play reads exactly what the English game would show.
"""

from __future__ import annotations

import re
from typing import Any

NAMES = {
    "돌도끼": "Stone Axe",
    "곤봉": "Club",
    "나무": "Wood",
    "돌": "Stone",
    "가죽 조각": "Leather Scraps",
    "라즈베리": "Raspberries",
    "버섯": "Mushroom",
    "구운 고기": "Cooked Meat",
    "날고기": "Raw Meat",
    "상한 고기": "Rotten Meat",
    "부싯돌": "Flint",
    "수지": "Resin",
    "사슴 가죽": "Deer Hide",
    "사슴 트로피": "Deer Trophy",
    "에이크쉬르 트로피": "Eikthyr Trophy",
    "망치": "Hammer",
    "횃불": "Torch",
    "활": "Crude Bow",
    "나무 화살": "Wood Arrow",
    "숯": "Coal",
    "맨손": "Unarmed",
    "작업대": "Workbench",
    "모닥불": "Campfire",
    "나무 벽": "Wood Wall",
    "초가지붕 26°": "Thatch Roof 26°",
    "나무 문": "Wood Door",
    "침대": "Bed",
    "요리대": "Cooking Station",
    "나뭇가지": "Branch",
    "라즈베리 덤불": "Raspberry Bush",
    "그레이드워프": "Greydwarf",
    "멧돼지": "Boar",
    "사슴": "Deer",
    "에이크쉬르": "Eikthyr",
    "초원": "Meadows",
    "쉼터": "Shelter",
    "따뜻함": "Warm",
    "좋은 아침입니다": "Good morning",
    "지붕이 필요합니다": "Requires a roof",
    "스폰 지점이 설정되었습니다": "Spawn point set",
    "지금은 잘 수 없습니다": "You can't sleep at this time",
    "침대 위에 지붕이 필요합니다": "The bed must be placed under a roof",
    "주변에 불이 필요합니다": "The bed needs to be placed near a fire",
    "제작 작업대에 지붕이 필요합니다": "The crafting station needs a roof",
    "요리 작업대 아래에 불을 피워야 합니다": "You need to have a lit fire below the cooking station",
}
BACK = {english: korean for korean, english in NAMES.items()}

# 이름이 들어간 메시지(게임의 "$msg_added", "$enemy_..._deathmessage", 묘비 이름표).
PATTERNS = [
    (re.compile(r"^추가됨 (.+)$"), "Added {}"),
    (re.compile(r"^(.+)를 처치했습니다$"), "{} is slain"),
    (re.compile(r"^묘비 (.+)$"), "Here rests {}"),
]


def _shown(text: str) -> str:
    if text in NAMES:
        return NAMES[text]
    for pattern, english in PATTERNS:
        if match := pattern.match(text):
            return english.format(_shown(match.group(1)))
    return text


def out(value: Any) -> Any:
    """A message from the world as the English game would show it."""
    if isinstance(value, str):
        return _shown(value)
    if isinstance(value, dict):
        return {key: out(item) for key, item in value.items()}
    if isinstance(value, list):
        return [out(item) for item in value]
    return value


def back(value: Any) -> Any:
    """A command's names in the world's own words."""
    if isinstance(value, str):
        return BACK.get(value, value)
    if isinstance(value, dict):
        return {key: back(item) for key, item in value.items()}
    if isinstance(value, list):
        return [back(item) for item in value]
    return value
