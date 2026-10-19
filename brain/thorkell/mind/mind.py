"""What Thorkell knows and how it learns it — like a first-time player.

Sources, in order of trust: what the game UI shows (names, discoveries), what he sees happen
(damage texts while *he* is hitting something, who attacks him), and what the leader tells him.
Told facts stay hypotheses until his own experience supports or refutes them; either outcome is a
realization worth saying out loud.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from thorkell import lang
from thorkell.body import protocol
from thorkell.lang import tr
from thorkell.mind.korean import damage_from_words, damage_name, josa
from thorkell.mind.speech import Line, SpeechQueue
from thorkell.mind.store import Fact, Lesson, Store, general

TOOL_TYPES = {"chop", "pickaxe"}
OUTCOME_PREDICATE = {"weak": "weak_to", "resistant": "resists", "immune": "immune_to"}
RIVALS = {
    "weak_to": ("resists", "immune_to"),
    "resists": ("weak_to", "immune_to"),
    "immune_to": ("weak_to", "resists"),
}

# 주어는 조사(은/는/이/가) 바로 뒤에 공백이 오는 한 단어다. 게으른 매칭이 "그레이드워프"를 "그레"+"이"로
# 자르지 않도록 단어 경계를 요구한다.
TELL_WEAK = re.compile(
    r"(?P<x>[^\s,.!?]+?)(은|는|이|가)\s+(?P<t>.+?)(에|에는|한테|엔)\s*(정말\s*)?약(해|하|함|다)"
)
TELL_STRONG = re.compile(
    r"(?P<x>[^\s,.!?]+?)(은|는|이|가)\s+(?P<t>.+?)(에|에는|한테|엔)\s*(강해|강하|잘\s*안\s*들|안\s*통)"
)
ASK_WEAKNESS = re.compile(r"(?P<x>[^\s,.!?]+)\s*(의\s*)?(약점|뭐에\s*약|뭐가\s*약)")
PARTICLES = ("은", "는", "이", "가", "의")

# 영어로 하는 말. 주어(생물 이름)는 동사 바로 앞(또는 "on" 뒤)의 한두 단어이고,
# "I heard", "the" 같은 말에서 끊는다.
# 동사의 수(are/is, hate/hates)로 리더가 복수형("greydwarves")을 썼는지 안다.
_EN_FILL = r"(?:really\s+|very\s+|super\s+|pretty\s+|so\s+|quite\s+)?"
# 피해 유형은 같은 마디 안에서만 찾는다("greydwarves hate me, they ... fire"는 불 얘기가 아니다).
_EN_REST = r"(?P<t>[^.!?;,]+)"
_EN_WEAKNESS = r"weak(?:ness(?:es)?|\s+spots?|\s+points?)"
# (패턴, 술어, 주어 자리)
EN_TELL = [
    (
        re.compile(
            rf"\b(?P<v>are|is|'re|'s)\s+{_EN_FILL}(?:resistant|immune|strong|tough)\s+(?:to|against)\s+{_EN_REST}",
            re.IGNORECASE,
        ),
        "resists",
        "before",
    ),
    (re.compile(rf"\b(?P<v>resists?)\s+{_EN_REST}", re.IGNORECASE), "resists", "before"),
    (
        re.compile(
            r"\b(?:doesn't|does\s+not|don't|do\s+not|won't|can't)\s+(?:really\s+)?"
            r"(?:work|do\s+much|do\s+anything|hurt)\s+(?:well\s+|much\s+)?(?:on|against)\s+",
            re.IGNORECASE,
        ),
        "resists",
        "after",
    ),
    (
        re.compile(
            rf"\b(?P<v>are|is|'re|'s)\s+{_EN_FILL}(?:weak|vulnerable)\s+(?:to|against)\s+{_EN_REST}",
            re.IGNORECASE,
        ),
        "weak_to",
        "before",
    ),
    (re.compile(rf"\b(?P<v>hates?)\s+{_EN_REST}", re.IGNORECASE), "weak_to", "before"),
]
EN_ASK = [
    (
        re.compile(
            r"\bwhat\s*(?P<v>are|is|'re|'s)\s+(?:the\s+|a\s+|an\s+)?"
            r"(?P<x>[a-z][a-z'-]*(?:\s+[a-z][a-z'-]*)?)\s+weak\s+(?:to|against)\b",
            re.IGNORECASE,
        ),
        "x",
    ),
    (re.compile(rf"\b{_EN_WEAKNESS}\s+(?:of|for)\s+", re.IGNORECASE), "after"),
    (re.compile(r"\bwhat\s+(?:works|is\s+good|'s\s+good)\s+(?:on|against)\s+", re.IGNORECASE), "after"),
    (re.compile(rf"\b{_EN_WEAKNESS}\b", re.IGNORECASE), "before"),
]
EN_PLURAL_VERBS = {"are", "'re", "hate", "resist"}
# 생물 이름이 아닌 말. 주어를 고를 때 여기서 끊는다.
EN_NOT_NAMES = re.compile(
    r"a|an|the|i|you|we|they|he|she|it|me|us|them|him|her|this|that|these|those|there|here|my|your|our|"
    r"their|his|its|and|but|or|so|if|when|because|then|also|too|heard|hear|think|thought|know|knew|"
    r"remember|guess|said|say|says|told|tell|read|saw|see|seen|apparently|actually|really|very|btw|hey|oh|"
    r"ok|okay|well|yeah|yes|no|not|at|all|in|on|of|to|for|with|from|by|about|like|just|some|any|most|every|"
    r"each|what|who|which|how|why|where|do|does|did|is|are|was|were|be|been|can|will|would|should|could|"
    r"might|must|thorkell|man|dude|bro|buddy|friend",
    re.IGNORECASE,
)


def _singular(word: str) -> str:
    """An English plural made singular ("greydwarves" -> "greydwarf", "trolls" -> "troll")."""
    lower = word.lower()
    if lower.endswith("ves") and len(word) > 4:
        return word[:-3] + "f"
    if lower.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if lower.endswith(("ches", "shes", "xes", "zes", "sses", "oes")):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith("ss") and len(word) > 2:
        return word[:-1]
    return word


def _name_words(words: list[str]) -> list[str]:
    """Up to two words of a name, nearest the verb first; stops at a word that is not part of a name."""
    picked: list[str] = []
    for word in words:
        word = word.removesuffix("'s").removesuffix("'")
        if len(picked) == 2 or not word or EN_NOT_NAMES.fullmatch(word):
            break
        picked.append(word)
    return picked


def _words_before(text: str, end: int) -> str | None:
    clause = re.split(r"[,.!?;:]", text[:end])[-1]
    picked = _name_words(re.findall(r"[A-Za-z][A-Za-z'-]*", clause)[::-1])
    return " ".join(reversed(picked)) or None


def _words_after(text: str, start: int) -> str | None:
    clause = re.split(r"[,.!?;:]", text[start:])[0]
    clause = re.sub(r"^\s*(?:the|a|an)\s+", "", clause, flags=re.IGNORECASE)
    return " ".join(_name_words(re.findall(r"[A-Za-z][A-Za-z'-]*", clause))) or None


def _subject(token: str) -> str:
    for particle in PARTICLES:
        if token.endswith(particle) and len(token) > 1:
            return token[: -len(particle)]
    return token


def _weapon(weapon: dict[str, Any] | None) -> tuple[str, str | None]:
    """(name, dominant combat damage type or None if mixed/none)."""
    damage = (weapon or {}).get("damage", {})
    combat = {k: float(v) for k, v in damage.items() if k not in TOOL_TYPES and float(v) > 0}
    dominant = None
    if combat:
        kind, value = max(combat.items(), key=lambda kv: kv[1])
        if value >= 0.7 * sum(combat.values()):
            dominant = kind
    return str((weapon or {}).get("name", tr("맨손", "Unarmed"))), dominant


@dataclass
class Attack:
    target: str
    kind: str
    weapon: str
    damage_type: str | None
    source: str = "brain"  # brain | reflex


@dataclass
class Mind:
    store: Store
    speech: SpeechQueue = field(default_factory=SpeechQueue)
    leader_name: str = "Leader"

    def __post_init__(self) -> None:
        self.attack: Attack | None = None

    # --- wiring ---------------------------------------------------------------------------------
    def on_event(self, event: protocol.Event) -> None:
        self.store.log_event(event.kind, json.dumps(event.data, ensure_ascii=False))
        match event.kind:
            case "damage_dealt" if event.data.get("on_target") is True:
                # 한 번 휘두르면 범위 안의 다른 물체도 맞는다.
                # 몸이 겨냥한 대상에 맞았다고 확인한 타격으로만 배운다.
                self._hit(str(event.data.get("type", "")), event.data.get("weapon"))
            case "damage_taken" if event.data.get("attacker_kind") == "creature":
                name = str(event.data.get("attacker_name") or "")
                if name:
                    self.store.know_entity(name, "creature", "attacked_me")
                    _, after = self.store.observe(name, "hostile", "true")
                    if after.support == 1:
                        self.speech.offer(
                            Line(
                                tr(f"{josa(name, '이가')} 날 공격했어!", f"{name} attacked me!"),
                                2,
                                "normal",
                                f"hostile:{name}",
                            )
                        )
            case "item_discovered":
                self.store.know_entity(str(event.data["name"]), "item", "game_ui")
            case "recipe_unlocked":
                name = str(event.data["name"])
                if self.store.know_entity(f"recipe:{name}", "recipe", "game_ui"):
                    self.speech.offer(
                        Line(
                            tr(f"이제 {josa(name, '을를')} 만들 수 있겠어.", f"I can make {name} now."),
                            1,
                            "whisper",
                            f"recipe:{name}",
                        )
                    )
            case "biome_entered":
                name = str(event.data["name"])
                if self.store.know_entity(name, "biome", "game_ui"):
                    self.speech.offer(
                        Line(
                            tr(
                                f"여긴 {name}인가 봐. 처음 와 보네.",
                                f"This must be the {name}. First time here.",
                            ),
                            1,
                            "normal",
                            f"biome:{name}",
                        )
                    )
            case "text_read":
                label = str(event.data.get("label") or "")
                self.store.know_entity(f"text:{label}", "text", "game_ui")
                self.store.log_text(label, str(event.data.get("text") or ""))
            case "reflex_engaged" if event.data.get("mode") == "self_defense":
                # 반사로 반격하는 동안의 타격도 자기 타격이다.
                # 같은 상대를 두뇌가 이미 맡고 있으면 두뇌의 맥락을 그대로 둔다.
                name = str(event.data.get("attacker_name") or "")
                brain_on_it = (
                    self.attack is not None and self.attack.source == "brain" and self.attack.target == name
                )
                if not brain_on_it:
                    self.attacking(name, "creature", event.data.get("weapon"), source="reflex")
            case "reflex_released" if event.data.get("mode") == "self_defense":
                # 두뇌가 공격 명령으로 넘겨받으면서 풀린 경우, 이미 두뇌가 새 맥락을 잡았으니 지우지 않는다.
                if self.attack is not None and self.attack.source == "reflex":
                    self.attack_done()
            case "chat" if event.data.get("from") == self.leader_name:
                self.store.log_utterance(self.leader_name, str(event.data.get("text", "")))

    def on_scene(self, scene: dict[str, Any]) -> None:
        for entity in scene.get("nearby", []):
            if entity.get("kind") == "creature" and entity.get("name"):
                name = str(entity["name"])
                if self.store.know_entity(name, "creature", "seen"):
                    self.speech.offer(
                        Line(
                            tr(f"저건 처음 보는 놈인데... {name}?", f"Never seen that one before... {name}?"),
                            1,
                            "whisper",
                            f"seen:{name}",
                            15,
                        )
                    )

    # --- attacks: which damage texts are ours ---------------------------------------------------
    def attacking(
        self, target_name: str, target_kind: str, weapon: dict[str, Any] | None, source: str = "brain"
    ) -> None:
        self.attack = Attack(target_name, target_kind, *_weapon(weapon), source=source)

    def attack_done(self) -> None:
        self.attack = None

    def _hit(self, outcome: str, weapon: dict[str, Any] | None) -> None:
        attack = self.attack
        if attack is None or not attack.target:
            return
        if weapon is not None:
            # 이벤트에 실린 타격 순간의 무기가 가장 정확하다(반사 중 무기를 바꿨을 수 있다).
            attack = Attack(attack.target, attack.kind, *_weapon(weapon), source=attack.source)
        if outcome == "too_hard":
            _, after = self.store.observe(attack.target, "too_hard_for", attack.weapon)
            if after.support == 1:
                self.speech.offer(
                    Line(
                        tr(
                            f"{josa(attack.weapon, '으로')}는 {josa(attack.target, '이가')} 안 깨지네.",
                            f"Can't break {attack.target} with {attack.weapon}.",
                        ),
                        1,
                        "normal",
                    )
                )
            return
        if attack.kind != "creature" or attack.damage_type is None:
            return
        damage_type = attack.damage_type
        predicate = OUTCOME_PREDICATE.get(outcome)
        rivals = RIVALS[predicate] if predicate else ("weak_to", "resists", "immune_to")
        for rival in rivals:
            changed = self.store.contradict(attack.target, rival, damage_type)
            if changed is not None:
                self._realize(*changed)
        if predicate is not None:
            self._realize(*self.store.observe(attack.target, predicate, damage_type))

    # --- what the leader says -------------------------------------------------------------------
    def hear(self, text: str) -> str | None:
        """Learn from the leader's words. Returns an immediate acknowledgement to say, if any."""
        if (match := ASK_WEAKNESS.search(text)) is not None:
            return self.answer_weakness(_subject(match.group("x")))
        # 영어 문장은 영어로 플레이할 때만 읽는다(한국어 플레이에서는 전처럼 플래너가 듣는다).
        english = lang.current() == "en"
        if english and (asked := self._asked_en(text)) is not None:
            return self.answer_weakness(asked)
        for pattern, predicate in ((TELL_STRONG, "resists"), (TELL_WEAK, "weak_to")):
            match = pattern.search(text)
            if match is None:
                continue
            damage_type = damage_from_words(match.group("t"))
            subject = match.group("x")
            if damage_type is None:
                return None
            return self._told(subject, subject, False, predicate, damage_type)
        return self._told_en(text) if english else None

    def _told_en(self, text: str) -> str | None:
        """An English fact: "greydwarves are weak to blunt weapons", "trolls hate fire",
        "trolls resist slash", "slash doesn't work on trolls"."""
        for pattern, predicate, where in EN_TELL:
            match = pattern.search(text)
            if match is None:
                continue
            if where == "before":
                said, rest = _words_before(text, match.start()), match.group("t")
                plural = match.group("v").lower() in EN_PLURAL_VERBS
            else:
                said = _words_after(text, match.end())
                rest = re.split(r"[,.!?;:]", text[: match.start()])[-1]
                plural = said is not None and _singular(said.split()[-1]) != said.split()[-1]
            if said is None:
                continue
            damage_type = damage_from_words(rest)
            if damage_type is None:
                return None
            # 되물을 때는 리더가 말한 그대로("the troll") 말한다.
            the = re.search(rf"\bthe\s+{re.escape(said)}\b", text, re.IGNORECASE) is not None
            shown = f"the {said}" if the else said
            return self._told(shown, self._creature_en(said, plural), plural, predicate, damage_type)
        return None

    def _told(self, said: str, subject: str, plural: bool, predicate: str, damage_type: str) -> str:
        """Remember a told fact about `subject` (the leader called it `said`) and acknowledge it."""
        self.store.know_entity(subject, "creature", "told")
        _, after = self.store.tell(subject, predicate, damage_type)
        kind = damage_name(damage_type)
        if predicate == "weak_to":
            claim = tr(
                f"{josa(subject, '은는')} {kind}에 약하다",
                f"{said} {'are' if plural else 'is'} weak to {kind}",
            )
        else:
            claim = tr(
                f"{josa(subject, '은는')} {kind}에 잘 안 통한다", f"{kind} doesn't work well on {said}"
            )
        if after.status == "verified":
            return tr(
                f"응, 나도 겪어 봤어. {claim}.",
                f"Yeah, I found that out too. {claim[:1].upper()}{claim[1:]}.",
            )
        return tr(
            f"알았어. {claim}는 거지? 싸울 때 확인해 볼게.",
            f"Got it. So {claim}? I'll check next time I fight.",
        )

    def _asked_en(self, text: str) -> str | None:
        """The creature an English question about weaknesses is about, if it is one."""
        for pattern, where in EN_ASK:
            match = pattern.search(text)
            if match is None:
                continue
            plural: bool | None = None
            if where == "x":
                said = " ".join(_name_words(match.group("x").split()[::-1])[::-1]) or None
                plural = match.group("v").lower() in EN_PLURAL_VERBS
            elif where == "after":
                said = _words_after(text, match.end())
            else:
                said = _words_before(text, match.start())
            if said is not None:
                return self._creature_en(said, plural)
        return None

    def _creature_en(self, said: str, plural: bool | None) -> str:
        """The game's name for a creature the leader named in English: one Thorkell already knows by that name
        (any case, singular or plural), else the name as the game writes names ("greydwarves" -> "Greydwarf").
        `plural` is what the verb said; None if it did not say."""
        *head, last = said.split()
        singular = " ".join([*head, _singular(last)])
        known = {name.casefold(): name for name in self.store.entity_names()}
        for candidate in (said, singular):
            if candidate.casefold() in known:
                return known[candidate.casefold()]
        name = said if plural is False else singular
        return " ".join(word[:1].upper() + word[1:].lower() for word in name.split())

    def answer_weakness(self, subject: str) -> str:
        facts = [
            f for f in self.store.facts_about(subject) if f.predicate in ("weak_to", "resists", "immune_to")
        ]
        weak = [f for f in facts if f.predicate == "weak_to" and f.status in ("supported", "verified")]
        told = [f for f in facts if f.predicate == "weak_to" and f.status == "hypothesis"]
        if weak:
            kinds = ", ".join(damage_name(f.object) for f in weak)
            return tr(
                f"{josa(subject, '은는')} {kinds}에 약해. 직접 싸워 보고 알았어.",
                f"{subject} is weak to {kinds}. I found out fighting one myself.",
            )
        if told:
            kinds = ", ".join(damage_name(f.object) for f in told)
            return tr(
                f"네가 {kinds}에 약하다고 했었지. 아직 직접 확인은 못 했어.",
                f"You said it's weak to {kinds}. Haven't checked it myself yet.",
            )
        return tr(
            f"{josa(subject, '은는')} 아직 잘 몰라. 싸워 보면 알 수 있을 것 같아.",
            f"I don't know much about {subject} yet. I'll find out once I fight one.",
        )

    def recall(self, query: str) -> str:
        """What Thorkell knows about something, with how he knows it. Never guesses."""
        if (match := ASK_WEAKNESS.search(query)) is not None:
            return self.answer_weakness(_subject(match.group("x")))
        if (asked := self._asked_en(query)) is not None:
            return self.answer_weakness(asked)
        subject = _subject(query.split()[0]) if query.split() else query
        if re.match(r"[A-Za-z]", subject):
            subject = self._creature_en(_words_after(query, 0) or subject, None)
        facts = [f for f in self.store.facts_about(subject) if f.status != "refuted"]
        if not facts:
            return tr(f"{josa(subject, '은는')} 아직 잘 몰라.", f"I don't know much about {subject} yet.")
        return "; ".join(f"{f.predicate} {damage_name(f.object)} ({f.status}, {f.provenance})" for f in facts)

    # --- realizations ---------------------------------------------------------------------------
    def _realize(self, before: Fact, after: Fact) -> None:
        if before.status == after.status:
            return
        subject, kind = after.subject, damage_name(after.object)
        topic = f"fact:{after.id}:{after.status}"
        if after.predicate == "weak_to" and after.status == "verified" and after.told:
            text = tr(
                f"네 말이 맞았어! {josa(subject, '은는')} 정말 {kind}에 약하네.",
                f"You were right! {subject} really is weak to {kind}.",
            )
            self.speech.offer(Line(text, 1, "normal", topic))
        elif after.predicate == "weak_to" and after.status == "supported":
            text = tr(
                f"{josa(subject, '은는')} {kind}에 약한 것 같아!", f"I think {subject} is weak to {kind}!"
            )
            self.speech.offer(Line(text, 1, "normal", topic))
        elif after.predicate == "resists" and after.status == "supported":
            text = tr(
                f"{kind} 공격이 {subject}한테는 잘 안 먹히네.",
                f"{kind[:1].upper()}{kind[1:]} attacks don't do much to {subject}.",
            )
            self.speech.offer(Line(text, 1, "whisper", topic))
        elif after.status == "refuted" and after.told:
            text = tr(
                f"{josa(subject, '이가')} {kind}에 약하다고 했는데, 해 보니까 아닌 것 같아.",
                f"You said {subject} was weak to {kind}, but I tried it and I don't think so.",
            )
            self.speech.offer(Line(text, 1, "normal", topic))

    def learned(self, text: str, topic: str) -> None:
        """Something worked out from experience (where an item comes from): worth a quiet remark."""
        self.speech.offer(Line(text, 1, "whisper", topic))

    # --- lessons from fights ---------------------------------------------------------------------
    def lessons_for(self, name: str) -> list[Lesson]:
        """Standing lessons about this creature and about fights in general."""
        return self.store.lessons((name, general()))

    # --- for the planner ------------------------------------------------------------------------
    def facts_for_prompt(self, limit: int = 30) -> tuple[list[str], frozenset[str]]:
        facts = self.store.all_facts(limit)
        lessons = self.store.lessons(limit=limit)
        lines = [f.line() for f in facts] + [lesson.line() for lesson in lessons]
        return lines, frozenset(f.id for f in facts) | frozenset(lesson.id for lesson in lessons)
