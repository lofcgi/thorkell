"""Where a line Thorkell decided to say goes.

  whisper (self-talk)  -> game chat whisper bubble; the voice model only gets it as context
  normal (to leader)   -> game chat bubble + spoken by the voice model when the floor is idle,
                          otherwise kept as context so the conversation is not cut
  shout (danger)       -> game chat shout + spoken immediately (may interrupt)
Both channels are sent by design; neither is a backup for the other.
"""

from __future__ import annotations

import logging

from thorkell.body.session import BodySession, CommandRejected
from thorkell.lang import tr
from thorkell.talk.live import LiveVoice

log = logging.getLogger(__name__)


class SpeechRouter:
    def __init__(self, session: BodySession, voice: LiveVoice | None) -> None:
        self.session = session
        self.voice = voice

    async def say(self, text: str, talker: str) -> None:
        try:
            await self.session.command("say", {"talker": talker, "text": text}, timeout=5)
        except (CommandRejected, TimeoutError) as error:
            log.error("chat line failed %r: %r", text, error)
        if self.voice is None or self.voice.status != "up":
            return
        if talker == "whisper":
            await self.voice.inject(tr(f"(혼잣말) {text}", f"(to himself) {text}"), speak=False)
        elif not await self.voice.inject(text, speak=True, urgent=talker == "shout"):
            unsaid = tr(
                f"(리더가 말하는 중이라 아직 못 한 말) {text}",
                f"(not said yet because the leader was talking) {text}",
            )
            await self.voice.inject(unsaid, speak=False)
