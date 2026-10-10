"""skip.py -- deterministic skip-request and real-attempt detection (v1.1 §8). The agent's
intent label is advisory; these helpers decide what the gate counts. A phrase hit inside an
`attempt` turn is not counted on its own (a real argument may say "then move on to the next
step"); the audit lists such turns so the agent cannot dodge the count silently."""
from __future__ import annotations

import re

SKIP_PHRASES = re.compile(r"\b(?:skip(?:ped|ping)?|move on|moving on|next question|come back)\b", re.I)
MIN_ATTEMPT_WORDS = 8
_WORD = re.compile(r"[A-Za-z0-9']+")
_NEVER_SKIP = ("confirm_advance", "define_request", "revisit")


def mentions_skip(text: str | None) -> bool:
    return bool(SKIP_PHRASES.search(text or ""))


def words_outside_skip(text: str | None) -> int:
    return len(_WORD.findall(SKIP_PHRASES.sub(" ", text or "")))


def is_real_attempt(intent: str, text: str | None, recognizer_hit: bool, admits_gap: bool) -> bool:
    if admits_gap:
        return False
    return bool(recognizer_hit) or (intent == "attempt" and words_outside_skip(text) >= MIN_ATTEMPT_WORDS)


def counts_as_skip(intent: str, text: str | None, flag: bool, in_play: bool) -> bool:
    if not in_play or intent in _NEVER_SKIP:
        return False
    return bool(flag) or (mentions_skip(text) and intent != "attempt")
