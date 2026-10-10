"""fsm.py -- the Socratic tutoring state machine as pure functions (v1 spec §3.3,
v1.1 §4, §8). Nothing here touches disk: session.py replays the event log through
replay() on every CLI call, so state can never drift from the log. Facts that need
the student's text (a skip request was made, a real attempt happened) are computed
by session.py and written into the event's data; replay only reads those flags."""
from __future__ import annotations

from dataclasses import dataclass, replace

from agent.tutor.events import Event

LAUNCH = "LAUNCH"
WORKING = "WORKING"
VERIFIED = "VERIFIED"
AWAITING_ADVANCE = "AWAITING_ADVANCE"
SYNTHESIS = "SYNTHESIS"
DONE = "DONE"
PAUSED = "PAUSED"

SKIPPED = "skipped"
DEFERRED = "deferred"

INTENTS = {"attempt", "stuck", "hint_request", "define_request", "confirm_advance", "has_questions", "revisit", "other"}
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
    cursor: int = 0              # index of the next never-started part (0 = derive from part_index)
    skip_requests: int = 0       # skip requests on the current part
    real_attempt: bool = False   # the current attempt of the current part had a real attempt
    queue: tuple = ()            # parked part indices, oldest first
    ripe: tuple = ()             # parked parts that may be offered at the current/next check-in
    offered: tuple = ()          # parked parts already offered once at a check-in
    saved: tuple = ()            # ((index, hint_level, failed_at_level, status), ...) for parked parts
    resume_state: str = ""       # state to return to after PAUSED


def _without(items: tuple, i: int) -> tuple:
    return tuple(x for x in items if x != i)


def fresh_index(s: FsmState) -> int:
    return max(s.cursor, s.part_index + 1)


def status_of(s: FsmState, index: int) -> str | None:
    for idx, _hint, _failed, status in s.saved:
        if idx == index:
            return status
    return None


def offerable(s: FsmState) -> tuple:
    """Parked parts the tutor must offer in its next message: at a check-in only the ripe, never-offered ones;
    in the closing message every parked part."""
    if s.state == SYNTHESIS:
        return s.queue
    if s.state == VERIFIED:
        return tuple(i for i in s.queue if i in s.ripe and i not in s.offered)
    return ()


def _next_fresh(s: FsmState, n_parts: int) -> FsmState:
    idx = fresh_index(s)
    if idx >= n_parts:
        return replace(s, state=SYNTHESIS, cursor=idx, skip_requests=0, real_attempt=False)
    return replace(s, part_index=idx, cursor=idx + 1, state=LAUNCH, hint_level=0, failed_at_level=0,
                   skip_requests=0, real_attempt=False)


def _park(s: FsmState, status: str) -> FsmState:
    entry = (s.part_index, s.hint_level, s.failed_at_level, status)
    saved = tuple(x for x in s.saved if x[0] != s.part_index) + (entry,)
    return replace(s, saved=saved, queue=_without(s.queue, s.part_index) + (s.part_index,),
                   ripe=_without(s.ripe, s.part_index), offered=_without(s.offered, s.part_index))


def student_event(
    s: FsmState, intent: str, n_parts: int, made_progress: bool = True, *,
    skip: bool = False, real_attempt: bool = False, revisit: int | None = None,
) -> tuple[FsmState, dict]:
    if intent not in INTENTS:
        raise IllegalTransition(f"unknown intent {intent!r}; expected one of {sorted(INTENTS)}")
    if s.state == DONE:
        raise IllegalTransition("session is already DONE")
    if s.state == PAUSED:
        raise IllegalTransition("session is paused; run start to resume (or start --fresh)")
    info: dict = {"hint_capped": False}
    if intent == "revisit":
        if s.state not in (AWAITING_ADVANCE, SYNTHESIS):
            raise IllegalTransition("revisit is only valid at the check-in after a completed part or in the closing "
                                    f"message (state is {s.state})")
        if revisit is None or revisit not in s.queue:
            raise IllegalTransition("name a skipped or deferred part to go back to")
        entry = next(x for x in s.saved if x[0] == revisit)
        info["revisited"] = revisit
        return replace(s, part_index=revisit, state=WORKING, hint_level=entry[1], failed_at_level=entry[2],
                       skip_requests=0, real_attempt=False, queue=_without(s.queue, revisit),
                       ripe=_without(s.ripe, revisit), offered=_without(s.offered, revisit)), info
    if intent == "confirm_advance":
        if s.state not in (VERIFIED, AWAITING_ADVANCE):
            raise IllegalTransition(
                f"confirm_advance is only valid after the part is verified (state is {s.state})"
            )
        return _next_fresh(s, n_parts), info
    if s.state in (SYNTHESIS, VERIFIED, AWAITING_ADVANCE) or intent == "define_request":
        return s, info          # a closed part is never reopened by a side question
    if skip and s.state in (LAUNCH, WORKING):
        real = s.real_attempt or real_attempt
        if s.skip_requests == 0:
            info["skip_count"] = 1
            return replace(s, state=WORKING, skip_requests=1, real_attempt=real), info
        status = DEFERRED if real or status_of(s, s.part_index) == DEFERRED else SKIPPED
        info.update(skip_count=s.skip_requests + 1, skip_ended=True, part_status=status, had_real_attempt=real)
        return _next_fresh(_park(s, status), n_parts), info
    new = s
    if intent in ("stuck", "hint_request"):
        if s.hint_level >= MAX_HINT_LEVEL:
            info["hint_capped"] = True
        elif s.hint_level == 2 and s.failed_at_level < 2:
            info["hint_capped"] = True
        else:
            new = replace(s, hint_level=s.hint_level + 1, failed_at_level=0)
    elif intent == "attempt" and not made_progress:
        new = replace(s, failed_at_level=s.failed_at_level + 1)
    if real_attempt:
        new = replace(new, real_attempt=True)
    if new.state == LAUNCH:
        new = replace(new, state=WORKING)
    return new, info


def verdict_event(s: FsmState, assessment: str) -> FsmState:
    """v1 only; kept so v1 logs still replay."""
    if assessment not in ASSESSMENTS:
        raise IllegalTransition(f"unknown assessment {assessment!r}; expected one of {sorted(ASSESSMENTS)}")
    if s.state != WORKING:
        raise IllegalTransition(f"verdict is only valid while WORKING (state is {s.state})")
    if assessment == "correct":
        return replace(s, state=VERIFIED)
    return replace(s, failed_at_level=s.failed_at_level + 1)


def verify_clean_event(s: FsmState) -> FsmState:
    if s.state != WORKING:
        raise IllegalTransition(f"verify is only valid while WORKING (state is {s.state})")
    saved = tuple(x for x in s.saved if x[0] != s.part_index)      # a closed part is no longer parked
    return replace(s, state=VERIFIED, saved=saved, ripe=s.queue)


def checkin_event(s: FsmState) -> FsmState:
    if s.state != VERIFIED:
        return s
    return replace(s, state=AWAITING_ADVANCE, offered=s.offered + tuple(i for i in offerable(s) if i not in s.offered))


def pause_event(s: FsmState) -> FsmState:
    if s.state in (DONE, PAUSED):
        raise IllegalTransition(f"cannot pause from state {s.state}")
    return replace(s, state=PAUSED, resume_state=s.state)


def resume_event(s: FsmState) -> FsmState:
    if s.state != PAUSED:
        raise IllegalTransition(f"cannot resume from state {s.state}")
    return replace(s, state=s.resume_state, resume_state="")


def finish_event(s: FsmState) -> FsmState:
    if s.state != SYNTHESIS:
        raise IllegalTransition(f"cannot end the session from state {s.state}; finish all parts first")
    return replace(s, state=DONE)


def replay(events: list[Event], n_parts: int) -> FsmState:
    s = FsmState()
    for e in events:
        if e.type == "student":
            s, _ = student_event(s, e.intent, n_parts, e.data.get("made_progress", True),
                                 skip=bool(e.data.get("skip")), real_attempt=bool(e.data.get("real_attempt")),
                                 revisit=e.data.get("revisit"))
        elif e.type == "verdict":
            s = verdict_event(s, e.data["assessment"])
        elif e.type == "verify" and e.data.get("clean"):
            s = verify_clean_event(s)
        elif e.type == "tutor_say" and e.data.get("checkin"):
            s = checkin_event(s)
        elif e.type == "paused":
            s = pause_event(s)
        elif e.type == "resumed":
            s = resume_event(s)
        elif e.type == "session_end":
            s = replace(s, state=DONE) if e.data.get("partial") else finish_event(s)
    return s
