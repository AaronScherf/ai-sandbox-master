"""fsm.py -- the Socratic tutoring state machine as pure functions (spec §3.3).
Nothing here touches disk: session.py replays the event log through
replay() on every CLI call, so state can never drift from the log."""
from __future__ import annotations

from dataclasses import dataclass, replace

from agent.tutor.events import Event

LAUNCH = "LAUNCH"
WORKING = "WORKING"
VERIFIED = "VERIFIED"
AWAITING_ADVANCE = "AWAITING_ADVANCE"
SYNTHESIS = "SYNTHESIS"
DONE = "DONE"

INTENTS = {"attempt", "stuck", "hint_request", "define_request", "confirm_advance", "has_questions", "other"}
ASSESSMENTS = {"correct", "on_track", "adjacent", "off_track"}
MAX_HINT_LEVEL = 3


class IllegalTransition(ValueError):
    pass


@dataclass(frozen=True)
class FsmState:
    part_index: int = 0
    state: str = LAUNCH
    hint_level: int = 0
    failed_at_level: int = 0


def student_event(s: FsmState, intent: str, n_parts: int) -> tuple[FsmState, dict]:
    if intent not in INTENTS:
        raise IllegalTransition(f"unknown intent {intent!r}; expected one of {sorted(INTENTS)}")
    if s.state == DONE:
        raise IllegalTransition("session is already DONE")
    if intent == "confirm_advance":
        if s.state not in (VERIFIED, AWAITING_ADVANCE):
            raise IllegalTransition(
                f"confirm_advance is only valid after the part is verified (state is {s.state})"
            )
        if s.part_index + 1 >= n_parts:
            return replace(s, state=SYNTHESIS), {"hint_capped": False}
        return FsmState(part_index=s.part_index + 1), {"hint_capped": False}
    info = {"hint_capped": False}
    if s.state == SYNTHESIS or intent == "define_request":
        return s, info
    new = s
    if intent in ("stuck", "hint_request"):
        if s.hint_level >= MAX_HINT_LEVEL:
            info["hint_capped"] = True
        elif s.hint_level == 2 and s.failed_at_level < 2:
            info["hint_capped"] = True
        else:
            new = replace(s, hint_level=s.hint_level + 1, failed_at_level=0)
    if new.state in (LAUNCH, VERIFIED, AWAITING_ADVANCE):
        new = replace(new, state=WORKING)
    return new, info


def verdict_event(s: FsmState, assessment: str) -> FsmState:
    if assessment not in ASSESSMENTS:
        raise IllegalTransition(f"unknown assessment {assessment!r}; expected one of {sorted(ASSESSMENTS)}")
    if s.state != WORKING:
        raise IllegalTransition(f"verdict is only valid while WORKING (state is {s.state})")
    if assessment == "correct":
        return replace(s, state=VERIFIED)
    return replace(s, failed_at_level=s.failed_at_level + 1)


def checkin_event(s: FsmState) -> FsmState:
    return replace(s, state=AWAITING_ADVANCE) if s.state == VERIFIED else s


def finish_event(s: FsmState) -> FsmState:
    if s.state != SYNTHESIS:
        raise IllegalTransition(f"cannot end the session from state {s.state}; finish all parts first")
    return replace(s, state=DONE)


def replay(events: list[Event], n_parts: int) -> FsmState:
    s = FsmState()
    for e in events:
        if e.type == "student":
            s, _ = student_event(s, e.intent, n_parts)
        elif e.type == "verdict":
            s = verdict_event(s, e.data["assessment"])
        elif e.type == "tutor_say" and e.data.get("checkin"):
            s = checkin_event(s)
        elif e.type == "session_end":
            s = finish_event(s)
    return s
