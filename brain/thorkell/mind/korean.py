"""Small Korean helpers: particles (은/는, 이/가, 을/를) and damage-type words (Korean and English)."""

from __future__ import annotations

import re

from thorkell import lang

DAMAGE_KO = {
    "blunt": "둔기",
    "slash": "베기",
    "pierce": "찌르기",
    "fire": "불",
    "frost": "냉기",
    "lightning": "번개",
    "poison": "독",
    "spirit": "영혼",
}

# 사람이 말할 때 쓰는 표현 -> 피해 유형. 긴 표현을 먼저 본다.
DAMAGE_WORDS = [
    ("때리는 무기", "blunt"),
    ("둔기", "blunt"),
    ("몽둥이", "blunt"),
    ("곤봉", "blunt"),
    ("망치", "blunt"),
    ("베는", "slash"),
    ("칼", "slash"),
    ("검", "slash"),
    ("찌르는", "pierce"),
    ("창", "pierce"),
    ("화살", "pierce"),
    ("활", "pierce"),
    ("화염", "fire"),
    ("불", "fire"),
    ("얼음", "frost"),
    ("냉기", "frost"),
    ("독", "poison"),
    ("번개", "lightning"),
    ("전기", "lightning"),
    ("영혼", "spirit"),
]

DAMAGE_EN = {
    "blunt": "blunt",
    "slash": "slash",
    "pierce": "pierce",
    "fire": "fire",
    "frost": "frost",
    "lightning": "lightning",
    "poison": "poison",
    "spirit": "spirit",
}

# 영어로 말할 때 쓰는 표현 -> 피해 유형. 한국어 표와 같은 순서로 보고, 긴 표현을 먼저 본다.
# 단어 경계를 지켜서 "pickaxe"의 axe, "nice"의 ice, "elbow"의 bow는 잡지 않는다.
DAMAGE_WORDS_EN = [
    (re.compile(rf"\b(?:{words})\b", re.IGNORECASE), kind)
    for words, kind in (
        (r"blunt\s+weapons?|blunt|clubs?|maces?|hammers?", "blunt"),
        (r"slash(?:ing|es)?|swords?|axes?|knife|knives", "slash"),
        (r"pierc(?:e|es|ing)|spears?|arrows?|bows?", "pierce"),
        (r"fire|flames?", "fire"),
        (r"frost|ice", "frost"),
        (r"poison(?:ous)?", "poison"),
        (r"lightning|electricity", "lightning"),
        (r"spirit", "spirit"),
    )
]


def damage_from_words(text: str) -> str | None:
    for word, kind in DAMAGE_WORDS:
        if word in text:
            return kind
    if lang.current() != "en":
        return None
    for pattern, kind in DAMAGE_WORDS_EN:
        if pattern.search(text):
            return kind
    return None


def damage_name(kind: str) -> str:
    """A damage type as Thorkell says it in the language being played (unknown types as they are)."""
    return (DAMAGE_EN if lang.current() == "en" else DAMAGE_KO).get(kind, kind)


def _final(word: str) -> int | None:
    """Index of the last syllable's final consonant (0 = none); None if the word ends in non-Hangul."""
    for char in reversed(word):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28
        if char.isalnum():
            return None
    return None


RIEUL = 8


def josa(word: str, particle: str) -> str:
    """Attach a particle that depends on the final consonant.

    particle: "은는", "이가", "을를", "과와" (받침 있을 때 / 없을 때) or "으로" (으로 / 로, ㄹ 받침은 로).
    Words ending in non-Hangul are read as having no final consonant.
    """
    final = _final(word) or 0
    if particle == "으로":
        return word + ("으로" if final not in (0, RIEUL) else "로")
    if len(particle) != 2:
        raise ValueError(f"unknown particle pair {particle!r}")
    return word + (particle[0] if final else particle[1])
