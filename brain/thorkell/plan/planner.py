"""The slow brain's planner: one structured JSON plan per new request (gemini-3.8-flash).

Known request kinds can skip the model entirely (templates); this module is for the rest.
A rejected plan gets exactly one repair attempt with the validator's problems; a second rejection
is a failed goal with the reason spoken, never a silent default.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from thorkell.lang import answer_from_model, schema_for_model, tr
from thorkell.models.gemini import JsonModel, ModelError, Usage
from thorkell.plan.schema import SKILL_CATALOG, Names, Plan, plan_schema, skill_description
from thorkell.plan.validate import Context, validate

log = logging.getLogger(__name__)

SYSTEM = """너는 Valheim을 처음 해 보는 바이킹 Thorkell의 생각이다.
리더(사람 플레이어)와 같이 첫 보스까지 가는 동료다.
판단 원칙:
- 네가 아는 것은 [상황]과 [알고 있는 사실]에 나온 것뿐이다. 게임 고유의 지식(어떤 몬스터가 무엇에 약한지,
  레시피, 보스 소환법, 아이템이 어디서 나는지)은 미리 아는 척하지 않는다. 일반 상식(나무를 베면 목재가 나온다,
  밤은 위험하다, 날고기는 구워 먹는다, 지붕이 있어야 비를 피한다)은 써도 된다.
- 이름은 게임이 보여 준 것(메뉴·이름표·인벤토리·기억)이나 리더가 말한 것만 쓴다.
  리더가 네가 모르는 것을 말하면: 싸게 해 볼 수 있으면 search로 찾아보거나 gather로 주워 보고,
  무엇인지 짐작도 안 되면 clarify로 물어본다(예: "멧돼지? 아직 못 봤어. 어떻게 생겼어?").
- 만들기는 craft, 짓기는 build, 재료는 gather, 사냥은 hunt, 굽기는 cook. 재료 계산·이동·제작대 찾기는 스킬이
  알아서 한다. 단계는 꼭 필요한 것만 쓴다.
- 일이 크거나 모호하면(예: "집을 지어야겠어") 지금 가진 재료와 메뉴를 보고 구체적으로 제안하며
  clarify로 묻는다.
  예: "작업대 둘레에 벽 몇 개랑 지붕이면 나무 30개쯤 들 것 같아. 그 정도로 지을까, 더 크게 할까?"
- 인사·잡담·질문이면 steps 없이 speech_gist_ko로만 답한다. 리더가 시키지 않은 이동이나 일은 하지 않는다.
- 위험하거나 되돌릴 수 없는 일(보스 소환, 남의 물건 쓰기)은 리더가 분명히 원할 때만 한다.
- speech_gist_ko는 Thorkell이 리더에게 할 한두 마디다. 반말, 짧고 친근하게. 처음 하는 사람처럼 궁금해하거나
  놀라도 된다. 하겠다는 일과 이유를 짧게 말한다.
- 지금 아는 것으로 부탁을 끝까지 계획할 수 없으면(예: 재료를 모아야 제작 메뉴에 뜬다,
  찾아봐야 어디 있는지 안다) 할 수 있는 데까지 단계를 쓰고 think_again_after를 true로 한다.
  그 단계를 마치면 다시 생각하게 된다.
- [이 부탁으로 해 본 것]은 이 부탁으로 이미 한 단계와 결과다. 된 것은 되풀이하지 않고 이어서 한다.
  안 된 것은 왜 안 됐는지 보고 다른 방법을 고르거나, 더 해 볼 방법이 없으면 리더에게 묻거나(clarify)
  안 되는 이유를 말한다. 같은 방법을 그대로 되풀이하지 않는다. speech_gist_ko에 지금 어떻게 할지 짧게 말한다.
- abort_if의 hp_below 값은 남은 체력 비율(0~1)이다. 체력 점수나 퍼센트를 넣지 않는다.
- 숫자 계산은 주어진 값만 쓴다.
Return JSON only."""

SYSTEM_EN = """You are the thoughts of Thorkell, a Viking playing Valheim for the first time.
He is the companion of the leader (a human player), and they are going to the first boss together.
How to judge:
- All you know is what [Situation] and [Known facts] show. Don't pretend to know game-specific things in
  advance (which monster is weak to what, recipes, how to summon a boss, where an item comes from). General
  common sense is fine (chopping trees gives wood, night is dangerous, raw meat gets cooked before eating, a
  roof keeps the rain off).
- Use only names the game has shown you (menus, name tags, inventory, memory) or the leader has said.
  If the leader mentions something you don't know: if it is cheap to try, look for it with search or try
  picking it up with gather; if you can't even guess what it is, ask with clarify
  (e.g. "A boar? Haven't seen one yet. What does it look like?").
- Making is craft, building is build, materials are gather, hunting is hunt, roasting is cook. The skills
  work out materials, walking and finding stations by themselves. Write only the steps you really need.
- If the job is big or vague (e.g. "We should build a house"), look at the materials and menus you have,
  make a concrete suggestion and ask with clarify.
  e.g. "A few walls and a roof around the workbench would take about 30 wood. Build that, or bigger?"
- For greetings, chit-chat and questions, answer only with speech_gist_en and no steps. Don't go anywhere or
  do any work the leader didn't ask for.
- Dangerous or irreversible things (summoning a boss, using someone else's things) only when the leader
  clearly wants them.
- speech_gist_en is the one or two lines Thorkell says to the leader. Casual, short and friendly. He may be
  curious or surprised like a first-timer. Say briefly what he'll do and why.
- If you can't plan the request to the end with what you know now (e.g. a recipe shows up in the menu only
  once you have its materials; you have to look around to know where something is), write the steps as far
  as you can and set think_again_after to true. You'll think again after those steps.
- [Tried for this request] lists the steps already taken for this request and how they went. Don't repeat
  what worked; carry on from there. For what failed, see why it failed and pick another way; if there's
  nothing left to try, ask the leader (clarify) or say why it can't be done. Don't repeat the same way
  unchanged. Say briefly in speech_gist_en what you'll do now.
- abort_if hp_below is the fraction of health left (0-1), not health points or a percentage.
- For numbers, use only the values given.
- Write in English.
Return JSON only."""


class PlanRejected(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class PlannerConfig:
    model: str = "gemini-3.8-flash"
    thinking: str = "low"
    max_output_tokens: int = 2048


class Planner:
    def __init__(self, model: JsonModel, config: PlannerConfig | None = None) -> None:
        self.model = model
        self.config = config or PlannerConfig()
        self.usage: list[Usage] = []

    def _prompt(self, request_ko: str, situation: str, context: Context, facts: list[str]) -> str:
        skills = "\n".join(
            f"- {name}({', '.join(args)}): {skill_description(name)}"
            for name, (args, _) in SKILL_CATALOG.items()
        )
        feasible = context.feasible.describe() if context.feasible else "unknown"
        known = chr(10).join(facts) if facts else tr("(아직 없음)", "(none yet)")
        return tr(
            f"[요청]\n{request_ko}\n\n[상황]\n{situation}\n\n[가능한 최대 수량]\n{feasible}\n\n"
            f"[알고 있는 사실]\n{known}\n\n[스킬]\n{skills}",
            f"[Request]\n{request_ko}\n\n[Situation]\n{situation}\n\n[Most that is possible]\n{feasible}\n\n"
            f"[Known facts]\n{known}\n\n[Skills]\n{skills}",
        )

    async def plan(
        self, request_ko: str, situation: str, context: Context, facts: list[str] | None = None
    ) -> Plan:
        schema = plan_schema(
            Names(
                items=tuple(sorted(context.inventory | context.items)),
                recipes=tuple(sorted(context.recipes)),
                pieces=tuple(sorted(context.pieces)),
                places=tuple(sorted(context.places)),
            )
        )
        prompt = self._prompt(request_ko, situation, context, facts or [])
        problems: list[str] = []
        for attempt in range(2):
            if problems:
                prompt += tr(
                    "\n\n[이전 계획의 문제 — 고쳐서 다시]\n",
                    "\n\n[Problems with the last plan — fix them and try again]\n",
                ) + "\n".join(f"- {p}" for p in problems)
            data, usage = await self.model.generate_json(
                model=self.config.model,
                system=tr(SYSTEM, SYSTEM_EN),
                prompt=prompt,
                schema=schema_for_model(schema),
                thinking=self.config.thinking,
                max_output_tokens=self.config.max_output_tokens,
            )
            self.usage.append(usage)
            data = answer_from_model(data)
            try:
                plan = Plan.model_validate(data)
            except ValidationError as error:
                problems = [f"schema: {e['loc']}: {e['msg']}" for e in error.errors()]
                log.warning("plan attempt %d did not match the schema: %s", attempt + 1, problems)
                continue
            problems = validate(plan, context)
            if not problems:
                return plan
            log.warning(
                "plan attempt %d rejected: %s | %s",
                attempt + 1,
                problems,
                json.dumps(data, ensure_ascii=False),
            )
        raise PlanRejected(problems)


__all__ = ["ModelError", "PlanRejected", "Planner", "PlannerConfig"]


def context_from_scene(
    scene: dict[str, Any],
    feasible: Any = None,
    fact_ids: frozenset[str] = frozenset(),
    *,
    recipes: list[dict[str, Any]] | None = None,
    pieces: list[dict[str, Any]] | None = None,
    places: list[str] | None = None,
    creatures: list[str] | None = None,
    items: list[str] | None = None,
    request: str = "",
) -> Context:
    inventory = scene.get("inventory", [])
    recipe_names = frozenset(r["name"] for r in recipes or [])
    materials = frozenset(m["name"] for r in (recipes or []) + (pieces or []) for m in r["resources"])
    return Context(
        inventory=frozenset(i["name"] for i in inventory),
        known_fact_ids=fact_ids,
        feasible=feasible,
        edible=frozenset(i["name"] for i in inventory if i.get("food")),
        recipes=recipe_names,
        pieces=frozenset(p["name"] for p in pieces or []),
        places=frozenset(places or []),
        creatures=frozenset(creatures or []),
        items=frozenset(items or []) | materials | recipe_names,
        request=request,
    )
