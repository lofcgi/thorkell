"""The language Thorkell plays in.

The game, what he hears, what he says and what he thinks share one language: a player who runs Valheim in
English reads English names and talks with friends in English. It is chosen once per run (`language` in
thorkell.toml) and handed to both games, so the names the body reports are in the brain's language.
"""

from __future__ import annotations

from typing import Any, Literal

Language = Literal["ko", "en"]

# 게임이 아는 언어 이름(Localization.SetupLanguage에 넘기는 값).
GAME_LANGUAGE: dict[Language, str] = {"ko": "Korean", "en": "English"}

_current: Language = "ko"


def use(language: Language) -> None:
    global _current
    _current = language


def current() -> Language:
    return _current


def tr(ko: str, en: str) -> str:
    """The line in the language being played."""
    return en if _current == "en" else ko


# 모델이 채우는 글 필드는 코드 안에서 `_ko`로 끝난다(speech_ko 등). 영어로 플레이할 때 모델에게 그 이름을
# 그대로 보이면 한국어로 답한다(실게임 2026-10-19: 영어 지시에도 summary_ko를 한국어로 썼다). 모델과 주고받는
# 경계에서만 `_en`으로 바꾼다.
def schema_for_model(schema: Any) -> Any:
    if _current != "en":
        return schema
    if isinstance(schema, dict):
        return {_to_en(key): schema_for_model(value) for key, value in schema.items()}
    if isinstance(schema, list):
        return [_to_en(item) if isinstance(item, str) else schema_for_model(item) for item in schema]
    return schema


def answer_from_model(data: Any) -> Any:
    if _current != "en":
        return data
    if isinstance(data, dict):
        return {_to_ko(key): answer_from_model(value) for key, value in data.items()}
    if isinstance(data, list):
        return [answer_from_model(item) for item in data]
    return data


def _to_en(name: str) -> str:
    return name[: -len("_ko")] + "_en" if name.endswith("_ko") else name


def _to_ko(name: str) -> str:
    return name[: -len("_en")] + "_ko" if name.endswith("_en") else name
