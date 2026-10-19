"""thorkell.toml: which model backs which role. Unknown keys are an error; secrets come only from env.

Secrets (injected with `op run --env-file brain/secrets.op -- ...`):
  GEMINI_API_KEY    planner (and later live voice / reflection)
  TYPESAFE_API_KEY  Jev decisions
A configured backend whose key is missing is a startup error, not a silent downgrade.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from thorkell.lang import Language


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BridgeConfig(_Strict):
    port: int = 47811


class LeaderConfig(_Strict):
    name: str = "Leader"


class PlannerConfig(_Strict):
    backend: Literal["gemini", "none"] = "none"
    model: str = "gemini-3.8-flash"
    # minimal은 gemini-3.8-flash가 400으로 거절한다(2026-10-02 `thorkell contract flash`).
    thinking: Literal["low", "medium", "high"] = "low"


class VisionConfig(_Strict):
    # 토르켈 자신의 화면을 이해하는 모델(픽셀 비전, 2026-10-18). none이면 화면을 보지 않고
    # 장면(이름표 목록)만 쓴다. flash-lite가 640x360 한 장에 약 1.2초(flash는 2.5~3초).
    backend: Literal["gemini", "none"] = "none"
    model: str = "gemini-3.5-flash-lite"
    resolution: Literal["low", "medium", "high"] = "low"
    thinking: Literal["minimal", "low", "medium"] = "minimal"


class VoiceSettings(_Strict):
    backend: Literal["none", "gemini-live"] = "none"
    model: str = "gemini-3.8-live"
    voice: str = "Kore"
    silence_ms: int = 600


class SystemOneConfig(_Strict):
    base_url: str
    model: str


class DecideConfig(_Strict):
    threat_response: Literal["rules", "jev", "laya"] = "rules"
    speak_worthy: Literal["rules", "jev", "laya"] = "rules"
    intent_guard: Literal["rules", "jev", "laya"] = "rules"
    jev: SystemOneConfig = SystemOneConfig(base_url="https://api.typesafe.ai", model="jev-1.13.0")
    laya: SystemOneConfig = SystemOneConfig(base_url="http://127.0.0.1:8000", model="typed-decisions")


class Config(_Strict):
    # 토르켈이 플레이하는 언어. 두 게임의 언어도 이걸로 띄운다(이름표·메뉴를 같은 언어로 읽는다).
    language: Language = "ko"
    bridge: BridgeConfig = Field(default_factory=BridgeConfig)
    leader: LeaderConfig = Field(default_factory=LeaderConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    decide: DecideConfig = Field(default_factory=DecideConfig)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    runs_dir: str = "runs"

    def required_secrets(self) -> list[str]:
        needed = []
        if "gemini" in (self.planner.backend, self.vision.backend) or self.voice.backend == "gemini-live":
            needed.append("GEMINI_API_KEY")
        if "jev" in (self.decide.threat_response, self.decide.speak_worthy, self.decide.intent_guard):
            needed.append("TYPESAFE_API_KEY")
        return needed


class ConfigError(Exception):
    pass


def load(path: Path | None) -> Config:
    if path is None:
        return Config()
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    try:
        return Config.model_validate(data)
    except ValidationError as error:
        raise ConfigError(f"invalid {path}: {error}") from error


def secret(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ConfigError(f"{name} is not set; inject it with `op run --env-file brain/secrets.op -- ...`")
    return value
