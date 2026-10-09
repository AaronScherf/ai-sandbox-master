# Socratic Tutor v1.1 — Plan B (skip / defer / revisit, pause, profile v2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the student an honest escape valve (two-request skip, parked parts, a revisit offer at the next check-in, a Proficient cap on revisits), let a session pause and resume, and record skipped/deferred work in a v2 learner profile, all gated by the CLI like Plan A.

**Architecture:** The pure FSM (`fsm.py`) gains a per-part skip count, a "real attempt" flag, a queue of parked parts with ripeness/offered bookkeeping, a cursor for the next fresh part, and `PAUSED`. `session.turn` computes the facts that need text (skip detected, real attempt) and writes them into the `student` event's `data`, so replay stays pure. `say` gets four new lint codes (skip nudge, revisit-offer missing, queued part mentioned mid-part, launch acknowledgement), `end` refuses to finish while parked parts were never offered, and the profile/summary/audit learn the `skipped`/`deferred` statuses. No model call is added.

**Tech Stack:** Python 3.13, `unittest`/pytest, existing `agent.tutor` package (Plan A, landed d0031a8).

**Spec:** `docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md` §4 (state), §5 (commands), §6 (rules), §8 (skip, defer, revisit), §9 (ratings, profile, pause), §10 (audit), §14 (build order). Amends the v1 spec the same way Plan A did.

## Global Constraints

- All paths below are relative to `ai-sandbox/academic-rag-model/` (the worktree root for this plan is `.worktrees/claude-tutor-v1-1-plan-b/`).
- Run tests as `.venv` python (`C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`) with `-m pytest tests/agent/tutor -q` from the worktree's `ai-sandbox/academic-rag-model/` directory.
- Stateless CLI: no state file; every command replays `events.jsonl`. New facts are written into event `data`; replay never inspects text.
- Skip request #1 keeps the part open and needs a "try it" nudge; request #2 (same part, any later turn) ends it. Statuses: `skipped` (no real attempt: no rating, not a gap) and `deferred` (≥1 real attempt: gap evidence).
- A real attempt = an `attempt` turn with ≥ 8 words outside the skip phrases (`MIN_ATTEMPT_WORDS = 8`, configurable constant) or any turn in which a claim or pitfall recognizer newly matched; a turn that carries `--admits-gap` is never a real attempt.
- The revisit offer appears only in the check-in after the next completed part (never mid-part); declining leaves the part queued for exactly one more offer in the closing message; `end` refuses until that closing offer was said.
- A revisited part reopens at its saved hint level with claims intact, a new attempt record starts, and its ratings are capped at Proficient on every axis.
- Profile `schema_version` 2: history entries carry `status` (`rated`/`deferred`/`skipped`) and `attempt`; v1 files load with every entry `status: "rated"`, `attempt: 1`.
- `pause` is an alias of `end --partial`; `start` resumes a paused session by default, `start --fresh` ends it as partial and begins a new one.
- Error JSON keeps `{"ok": false, "error": ..., "next": [...]}`. The audit never decides correctness.
- Stage explicit paths only (never `git add -A`); commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A real attempt that merely contains a skip phrase ("then I move on to the next step by multiplying", intent `attempt`, no `--skip`) must NOT count as a skip request; the audit flags it as uncounted so the agent cannot dodge the count silently (Task 2, Task 7).
2. Skipping the last fresh part must land in `SYNTHESIS` with the parked parts queued, and `end` must refuse until the closing message offered them (Task 1, Task 3).
3. Revisit with several parked parts and no `--part`, or with a part that is not parked, must be refused with the options listed, never guessed (Task 2).
4. Pause mid-part, then `turn`/`say` must be refused; `start` must restore an identical brief; `start --fresh` must close the paused session as partial; pausing then ending must not duplicate profile history (Task 5, Task 6).
5. A schema-1 profile on disk must load as v2 without losing history, and mixed rated/deferred/skipped entries must not crash `open_gaps` or the markdown render (Task 5).

---

### Task 1: FSM v2 — skip, park, revisit, pause

**Files:**
- Modify: `agent/tutor/fsm.py` (replace the whole file)
- Create: `tests/agent/tutor/test_tutor_fsm_skip.py`

**Interfaces:**
- Consumes: `agent.tutor.events.Event` (`id, ts, type, part, state, hint_level, intent, text, data`).
- Produces (used by every later task):
  - constants `PAUSED = "PAUSED"`, `SKIPPED = "skipped"`, `DEFERRED = "deferred"`; `INTENTS` gains `"revisit"`.
  - `FsmState(part_index=0, state=LAUNCH, hint_level=0, failed_at_level=0, cursor=0, skip_requests=0, real_attempt=False, queue=(), ripe=(), offered=(), saved=(), resume_state="")` (frozen; `queue/ripe/offered` are tuples of part indices; `saved` is a tuple of `(index, hint_level, failed_at_level, status)`).
  - `student_event(s, intent, n_parts, made_progress=True, *, skip=False, real_attempt=False, revisit=None) -> (FsmState, info)`; `info` always has `hint_capped`; adds `skip_count` on a skip turn, and `skip_ended`, `part_status`, `had_real_attempt` when the part is parked; `revisited` on a revisit.
  - `fresh_index(s) -> int` (next never-started part, `>= n_parts` means none), `status_of(s, index) -> str | None`, `offerable(s) -> tuple[int, ...]`.
  - `verify_clean_event(s)` (also marks every queued part ripe), `checkin_event(s)` (also marks offered), `pause_event(s)`, `resume_event(s)`.
  - `replay(events, n_parts)` reads student `data` keys `skip`, `real_attempt`, `revisit` and events `paused`, `resumed`, and `session_end` with `data.partial`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_fsm_skip.py
import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DEFERRED, DONE, LAUNCH, PAUSED, SKIPPED, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, fresh_index, offerable, pause_event, replay, resume_event,
    status_of, student_event, verify_clean_event,
)


def ev(i, type, **kw):
    return Event(id=i, ts="t", type=type, **kw)


def skip_twice(s, n=3, real_first=False):
    s, _ = student_event(s, "attempt" if real_first else "other", n, made_progress=False,
                         skip=True, real_attempt=real_first)
    return student_event(s, "other", n, skip=True)


class TestSkip(unittest.TestCase):
    def test_first_request_keeps_the_part_and_counts(self):
        s, info = student_event(FsmState(), "other", 3, skip=True)
        self.assertEqual((s.part_index, s.state, s.skip_requests), (0, WORKING, 1))
        self.assertEqual(info["skip_count"], 1)
        self.assertNotIn("skip_ended", info)

    def test_second_request_with_no_real_attempt_parks_as_skipped_and_launches_next(self):
        s, info = skip_twice(FsmState())
        self.assertEqual((s.part_index, s.state, s.skip_requests, s.queue, s.cursor), (1, LAUNCH, 0, (0,), 2))
        self.assertEqual((info["skip_ended"], info["part_status"], info["had_real_attempt"]), (True, SKIPPED, False))
        self.assertEqual(status_of(s, 0), SKIPPED)

    def test_a_real_attempt_before_the_second_request_makes_it_deferred(self):
        s, _ = student_event(FsmState(), "attempt", 3, made_progress=False, real_attempt=True)
        s, _ = student_event(s, "other", 3, skip=True)
        s, info = student_event(s, "other", 3, skip=True)
        self.assertEqual((info["part_status"], info["had_real_attempt"]), (DEFERRED, True))

    def test_the_real_attempt_may_be_in_the_ending_message_itself(self):
        s, _ = student_event(FsmState(), "other", 3, skip=True)
        s, info = student_event(s, "attempt", 3, skip=True, real_attempt=True)
        self.assertEqual(info["part_status"], DEFERRED)

    def test_hint_level_is_saved_for_the_revisit(self):
        s, _ = student_event(FsmState(), "stuck", 3)
        s, _ = skip_twice(s)
        self.assertEqual(s.saved, ((0, 1, 0, SKIPPED),))

    def test_skipping_the_last_fresh_part_goes_to_synthesis_with_the_queue(self):
        s = FsmState(part_index=2, state=WORKING, cursor=3)
        s, _ = skip_twice(s)
        self.assertEqual((s.state, s.queue, s.part_index), (SYNTHESIS, (2,), 2))

    def test_skip_is_ignored_once_the_part_is_closed(self):
        s = verify_clean_event(FsmState(state=WORKING))
        s2, info = student_event(s, "other", 3, skip=True)
        self.assertEqual((s2, "skip_count" in info), (s, False))


def parked_then_closed(n=3):
    s, _ = student_event(FsmState(), "stuck", n)            # hint level 1 on part 0
    s, _ = skip_twice(s, n)                                  # part 0 parked, part 1 in LAUNCH
    s, _ = student_event(s, "attempt", n)
    return verify_clean_event(s)


class TestOfferAndRevisit(unittest.TestCase):
    def test_a_parked_part_becomes_offerable_at_the_next_completed_parts_checkin_only(self):
        s = parked_then_closed()
        self.assertEqual((s.state, s.ripe, offerable(s)), (VERIFIED, (0,), (0,)))
        s = checkin_event(s)
        self.assertEqual((s.state, s.offered, offerable(s)), (AWAITING_ADVANCE, (0,), ()))

    def test_nothing_is_offerable_mid_part(self):
        s, _ = skip_twice(FsmState())
        self.assertEqual(offerable(s), ())

    def test_revisit_reopens_the_part_at_its_saved_hint_level(self):
        s = checkin_event(parked_then_closed())
        s, info = student_event(s, "revisit", 3, revisit=0)
        self.assertEqual((s.part_index, s.state, s.hint_level, s.queue, s.skip_requests), (0, WORKING, 1, (), 0))
        self.assertEqual(info["revisited"], 0)

    def test_advance_after_a_revisit_goes_to_the_next_fresh_part_not_index_plus_one(self):
        s = checkin_event(parked_then_closed())
        s, _ = student_event(s, "revisit", 3, revisit=0)
        s = checkin_event(verify_clean_event(s))
        self.assertEqual(fresh_index(s), 2)
        s, _ = student_event(s, "confirm_advance", 3)
        self.assertEqual((s.part_index, s.state), (2, LAUNCH))

    def test_declined_offer_is_made_once_more_at_synthesis(self):
        s = checkin_event(parked_then_closed())
        s, _ = student_event(s, "confirm_advance", 3)          # move on to part 2
        s, _ = skip_twice(s)                                    # last part parked too
        self.assertEqual((s.state, s.queue), (SYNTHESIS, (0, 2)))
        self.assertEqual(offerable(s), (0, 2))

    def test_revisit_is_refused_while_working_and_for_unparked_parts(self):
        with self.assertRaises(IllegalTransition):
            student_event(FsmState(state=WORKING), "revisit", 3, revisit=0)
        s = checkin_event(parked_then_closed())
        with self.assertRaises(IllegalTransition):
            student_event(s, "revisit", 3, revisit=1)
        with self.assertRaises(IllegalTransition):
            student_event(s, "revisit", 3)

    def test_a_revisit_that_is_skipped_again_stays_deferred_if_it_ever_was(self):
        s = FsmState(part_index=0, state=WORKING)
        s, _ = student_event(s, "attempt", 3, made_progress=False, real_attempt=True)
        s, _ = skip_twice(s)                                    # deferred
        s = checkin_event(verify_clean_event(student_event(s, "attempt", 3)[0]))
        s, _ = student_event(s, "revisit", 3, revisit=0)
        s, info = skip_twice(s)                                 # no real attempt this time
        self.assertEqual(info["part_status"], DEFERRED)


class TestPauseAndReplay(unittest.TestCase):
    def test_pause_and_resume_restore_the_state(self):
        s = FsmState(state=WORKING, hint_level=2)
        p = pause_event(s)
        self.assertEqual((p.state, p.resume_state), (PAUSED, WORKING))
        self.assertEqual(resume_event(p), s)

    def test_nothing_runs_while_paused_or_after_done(self):
        p = pause_event(FsmState(state=WORKING))
        with self.assertRaises(IllegalTransition):
            student_event(p, "attempt", 3)
        with self.assertRaises(IllegalTransition):
            pause_event(p)
        with self.assertRaises(IllegalTransition):
            pause_event(FsmState(state=DONE))
        with self.assertRaises(IllegalTransition):
            resume_event(FsmState(state=WORKING))

    def test_replay_reads_the_new_event_data(self):
        events = [ev(1, "student", intent="other", data={"skip": True}),
                  ev(2, "student", intent="other", data={"skip": True, "real_attempt": False}),
                  ev(3, "paused"), ev(4, "resumed")]
        s = replay(events, 3)
        self.assertEqual((s.part_index, s.state, s.queue), (1, LAUNCH, (0,)))

    def test_replay_of_a_partial_end_is_done_from_any_state(self):
        events = [ev(1, "student", intent="attempt", data={}), ev(2, "session_end", data={"partial": True})]
        self.assertEqual(replay(events, 2).state, DONE)

    def test_replay_revisit_uses_the_logged_index(self):
        events = [ev(1, "student", intent="other", data={"skip": True}),
                  ev(2, "student", intent="other", data={"skip": True}),
                  ev(3, "student", intent="attempt", data={}),
                  ev(4, "verify", data={"clean": True}),
                  ev(5, "tutor_say", data={"checkin": True}),
                  ev(6, "student", intent="revisit", data={"revisit": 0})]
        s = replay(events, 3)
        self.assertEqual((s.part_index, s.state), (0, WORKING))

    def test_old_v1_style_logs_still_replay_with_the_same_numbers(self):
        events = [ev(1, "student", intent="attempt", data={"made_progress": True}),
                  ev(2, "verify", data={"clean": True}), ev(3, "tutor_say", data={"checkin": True}),
                  ev(4, "student", intent="confirm_advance", data={})]
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state, s.hint_level), (1, LAUNCH, 0))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_fsm_skip.py -q`
Expected: collection error (`ImportError: cannot import name 'DEFERRED'` or similar).

- [ ] **Step 3: Write the implementation (replace the whole file)**

```python
# agent/tutor/fsm.py  (replace the whole file)
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
```

- [ ] **Step 4: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass (the 177 existing plus the new FSM tests). If a Plan A test fails because it built `FsmState(part_index=1, ...)` and expected `confirm_advance` to land on part 2, that still works (`fresh_index = part_index + 1`); investigate any other failure before continuing.

- [ ] **Step 5: Commit**

```bash
git add agent/tutor/fsm.py tests/agent/tutor/test_tutor_fsm_skip.py
git commit -m "feat(tutor): FSM skip, park, revisit and pause states"
```

---

### Task 2: Skip detection, real attempts, `turn --skip` / `--part`, brief fields

**Files:**
- Create: `agent/tutor/skip.py`
- Create: `tests/agent/tutor/skip_support.py` (shared test helpers for Tasks 2-8)
- Create: `tests/agent/tutor/test_tutor_skip.py`
- Modify: `agent/tutor/ledger.py:13` (`IGNORED_INTENTS` gains `"revisit"`)
- Modify: `agent/tutor/session.py` (`_NEXT`, `_rules`, `_brief`, `turn`)
- Modify: `agent/tutor/cli.py` (`turn --skip --part`)

**Interfaces:**
- Consumes (Task 1): `student_event(..., skip=, real_attempt=, revisit=)`, `fresh_index`, `offerable`, `status_of`, `FsmState.queue/skip_requests`.
- Produces:
  - `skip.SKIP_PHRASES`, `skip.MIN_ATTEMPT_WORDS = 8`, `skip.mentions_skip(text) -> bool`, `skip.words_outside_skip(text) -> int`, `skip.is_real_attempt(intent, text, recognizer_hit, admits_gap) -> bool`, `skip.counts_as_skip(intent, text, flag, in_play) -> bool`.
  - `Session.turn(..., skip: bool = False, revisit_part: str | None = None)`.
  - `student` event `data` keys: `skip`, `skip_count`, `skip_ended`, `real_attempt`, `revisit` (index), `revisit_part` (id). A skip-ending message is logged under the PARKED part (its claim words still count there); a `part_status` event follows it with `data {status, attempt, real_attempt, skip_requests}`.
  - `Session._attempt_no(pe) -> int` (1 + count of `revisit` student events in the part's events).
  - Brief keys `skip_requests`, `attempt`, `deferred_queue` (`[{part_id, label, status}]`), `revisit_offer` (at VERIFIED/SYNTHESIS), `revisit_options` (at AWAITING_ADVANCE/SYNTHESIS), `parked` (right after a skip-ending turn).
  - `tests/agent/tutor/skip_support.py` exports `make(tmp)`, `cover_q1(s)`, `cover_q2(s)`, `close_q1(s)`, `close_q2(s)`, `close_q1_said(s)`, `close_q2_said(s)` (the `_said` variants add a tutor reply after each student turn so the audit sees an honest flow), `park_q1(s, with_attempt=False)`, `M1..M3`, `N1..N3`, `CHECK_Q1`, `CHECK_Q2`, `CHECKIN`, `CHECKIN_OFFER`, `NUDGE`, `Q`, `codes(result)`.

- [ ] **Step 1: Write the shared helpers and the failing tests**

```python
# tests/agent/tutor/skip_support.py
import datetime

from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 9, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"
M1 = "the probabilities of everything in the set sum to 1"
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
CHECK_Q1 = [{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}]
CHECK_Q2 = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
            {"step": 3, "status": "confirmed", "quote": N3}]
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"
CHECKIN_OFFER = "Right. Do you have any lingering questions, or would you like to go back to Question 1 first?"
NUDGE = "What is the first thing you would try here?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def cover_q1(s):
    s.turn("attempt", M2)
    return s.turn("attempt", M3)


def cover_q2(s):
    s.turn("attempt", N1)
    s.turn("attempt", N2)
    return s.turn("attempt", N3)


def park_q1(s, with_attempt=False):
    """Skip q1 (two requests). Leaves the session in q2/LAUNCH. Returns the last brief."""
    if with_attempt:
        s.turn("attempt", M2)                      # recognizer match -> a real attempt
    s.turn("other", "I would rather skip this one", skip=True)
    s.say(NUDGE)
    return s.turn("other", "please, skip it, I want to move on", skip=True)


def close_q1(s):
    cover_q1(s)
    s.verify()
    return s.verify(CHECK_Q1)


def close_q2(s):
    cover_q2(s)
    s.verify()
    return s.verify(CHECK_Q2)


Q = "What makes you say that?"


def close_q1_said(s):
    """Like close_q1 but with a tutor reply after every student turn, so the audit sees an honest flow."""
    s.turn("attempt", M2)
    s.say(Q)
    s.turn("attempt", M3)
    s.verify()
    return s.verify(CHECK_Q1)


def close_q2_said(s):
    for text in (N1, N2):
        s.turn("attempt", text)
        s.say(Q)
    s.turn("attempt", N3)
    s.verify()
    return s.verify(CHECK_Q2)
```

```python
# tests/agent/tutor/test_tutor_skip.py
import tempfile
import unittest

from agent.tutor.session import Refused
from agent.tutor.skip import (
    MIN_ATTEMPT_WORDS, counts_as_skip, is_real_attempt, mentions_skip, words_outside_skip,
)
from skip_support import M1, M2, make, park_q1


class TestDetectors(unittest.TestCase):
    def test_phrases(self):
        for text in ("can we skip this", "let's move on", "next question please", "I'll come back to it", "skipping"):
            self.assertTrue(mentions_skip(text), text)
        for text in ("I think it is the sum", "the next step is to add them"):
            self.assertFalse(mentions_skip(text), text)

    def test_words_outside_skip_phrases(self):
        self.assertEqual(words_outside_skip("please skip this one, let's move on"), 4)
        self.assertGreaterEqual(MIN_ATTEMPT_WORDS, 1)

    def test_real_attempt_rules(self):
        long = "I think the answer has to do with how the other options are treated here"
        self.assertTrue(is_real_attempt("attempt", long, False, False))
        self.assertFalse(is_real_attempt("attempt", "I do not know where to start", False, False))
        self.assertFalse(is_real_attempt("other", long, False, False))              # only attempt turns by length
        self.assertTrue(is_real_attempt("other", "short", True, False))              # a recognizer matched
        self.assertFalse(is_real_attempt("attempt", long, False, True))              # an admitted gap is not an attempt
        self.assertFalse(is_real_attempt("attempt", "skip skip skip skip move on please next question " * 2, False, False))

    def test_counts_as_skip(self):
        self.assertTrue(counts_as_skip("other", "whatever", True, True))             # explicit flag
        self.assertTrue(counts_as_skip("other", "let's move on", False, True))       # phrase, non-attempt intent
        self.assertFalse(counts_as_skip("attempt", "then move on to the next step by adding", False, True))
        self.assertTrue(counts_as_skip("attempt", "whatever", True, True))
        self.assertFalse(counts_as_skip("other", "let's move on", False, False))     # closed part: confirm_advance's job
        self.assertFalse(counts_as_skip("confirm_advance", "move on", True, True))


class TestTurnSkip(unittest.TestCase):
    def test_first_request_counts_and_keeps_the_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("other", "I would rather skip this one")
            self.assertEqual((b["part_id"], b["state"], b["skip_requests"]), ("q1", "WORKING", 1))
            ev = s.log.load()[-1]
            self.assertTrue(ev.data["skip"])
            self.assertEqual(ev.data["skip_count"], 1)

    def test_an_attempt_that_merely_contains_a_skip_phrase_is_not_a_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = s.turn("attempt", "first I move on to the next step and multiply the probabilities")
            self.assertEqual(b["skip_requests"], 0)
            self.assertFalse(s.log.load()[-1].data.get("skip"))

    def test_the_flag_counts_even_with_an_attempt_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertEqual(s.turn("attempt", "no idea", skip=True)["skip_requests"], 1)

    def test_second_request_parks_the_part_and_launches_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = park_q1(s)
            self.assertEqual((b["part_id"], b["state"]), ("q2", "LAUNCH"))
            self.assertEqual(b["launch_text"], "Question 2. How would you like to approach this problem?")
            self.assertEqual(b["deferred_queue"], [{"part_id": "q1", "label": "Question 1", "status": "skipped"}])
            self.assertEqual(b["parked"], {"part_id": "q1", "label": "Question 1", "status": "skipped"})
            events = s.log.load()
            ending = [e for e in events if e.type == "student"][-1]
            self.assertEqual((ending.part, ending.data["skip_ended"]), ("q1", True))   # logged under the parked part
            status = [e for e in events if e.type == "part_status"][-1]
            self.assertEqual((status.part, status.data["status"], status.data["attempt"], status.data["real_attempt"]),
                             ("q1", "skipped", 1, False))
            self.assertEqual(s.turn("attempt", "just a first try at the new one")["claims_established"], [])

    def test_a_recognized_claim_before_skipping_makes_it_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = park_q1(s, with_attempt=True)
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")
            self.assertTrue([e for e in s.log.load() if e.type == "part_status"][-1].data["real_attempt"])

    def test_a_long_attempt_is_real_but_an_admitted_gap_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I really am not sure but I think the others somehow matter here", admits_gap="all")
            self.assertFalse(s.log.load()[-1].data["real_attempt"])
            s.turn("attempt", "I think it is about how the other options are treated in the model")
            self.assertTrue(s.log.load()[-1].data["real_attempt"])

    def test_words_in_the_ending_message_still_count_for_the_parked_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip please", skip=True)
            s.say(NUDGE_TEXT)
            s.turn("attempt", M2 + " but let us skip it", skip=True)
            b = s.view()
            self.assertEqual(b["part_id"], "q2")
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")   # the claim in the ending message was a real attempt
            self.assertEqual(s.turn("attempt", "something about the preference")["claims_established"], [])


NUDGE_TEXT = "What is the first thing you would try here?"


class TestRevisitTurn(unittest.TestCase):
    def test_revisit_needs_a_parked_part_and_the_right_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(Exception):
                s.turn("revisit", "go back to question one")                 # state LAUNCH: illegal

    def test_ambiguous_or_unknown_part_is_refused_with_the_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.turn("other", "skip this too", skip=True)
            s.say(NUDGE_TEXT)
            s.turn("other", "skip", skip=True)                                  # both parked -> SYNTHESIS
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            with self.assertRaises(Refused) as ctx:
                s.turn("revisit", "go back please")
            self.assertIn("q1", str(ctx.exception))
            self.assertIn("q2", str(ctx.exception))
            with self.assertRaises(Refused):
                s.turn("revisit", "go back please", revisit_part="q9")
            b = s.turn("revisit", "go back please", revisit_part="Question 2")
            self.assertEqual((b["part_id"], b["state"], b["attempt"]), ("q2", "WORKING", 2))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_skip.py -q`
Expected: `ModuleNotFoundError: No module named 'agent.tutor.skip'`.

- [ ] **Step 3: Write `agent/tutor/skip.py`**

```python
# agent/tutor/skip.py
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
```

- [ ] **Step 4: Edit `agent/tutor/ledger.py` line 13**

Replace `IGNORED_INTENTS = frozenset({"confirm_advance", "define_request"})` with:

```python
IGNORED_INTENTS = frozenset({"confirm_advance", "define_request", "revisit"})
```

- [ ] **Step 5: Edit `agent/tutor/session.py`**

(a) Imports: add `PAUSED, offerable, fresh_index, status_of` to the `from agent.tutor.fsm import (...)` list and add `from agent.tutor.skip import counts_as_skip, is_real_attempt`.

(b) Add to `_NEXT` after the existing entries (keep the others):

```python
    fsm.PAUSED: ["start (resume)", "start --fresh"],
```

(c) Add a module helper above `class Session` and `_attempt_no` as a static method:

```python
def _parked(packet, indices, s=None):
    return [{"part_id": packet.parts[i].part_id, "label": packet.parts[i].label or packet.parts[i].part_id,
             "status": (status_of(s, i) if s is not None else None)} for i in indices]
```

Inside `Session` (next to `_released`):

```python
    @staticmethod
    def _attempt_no(pe: list[Event]) -> int:
        return 1 + sum(1 for e in pe if e.type == "student" and e.intent == "revisit")
```

(d) In `_rules`, add a final parameter `extra=()` and append the extra sentences. Replace the signature line and the three early returns/ending so extras are appended: change `def _rules(self, s, ledger, unresolved, form):` to `def _rules(self, s, ledger, unresolved, form, extra=()):` and wrap: rename the existing body to `_rules_base` (same code, except the LAUNCH rule now reads "Send launch_text through say, then wait for the student." because a skip acknowledgement may precede it; no test pins the old wording) and add

```python
    def _rules(self, s, ledger, unresolved, form, extra=()):
        return " ".join([self._rules_base(s, ledger, unresolved, form), *extra])
```

(e) In `_brief`, before building `out`, compute (after `unresolved = ...`):

```python
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        answered = last_student is not None and any(e.type == "tutor_say" and e.id > last_student.id for e in events)
        extra = []
        nudge = (s.state == WORKING and s.skip_requests == 1 and last_student is not None
                 and last_student.data.get("skip") and not answered)
        if nudge:
            extra.append("The student asked to skip. Do NOT agree or move on, and do not mention the next question. "
                         "Reply with ONE question that invites them to try a first step. If they ask again, the "
                         "part is parked and can be revisited later.")
        parked_now = None
        if s.state == LAUNCH and last_student is not None and last_student.data.get("skip_ended") and not answered:
            idx = next(i for i, p in enumerate(self.packet.parts) if p.part_id == last_student.part)
            parked_now = _parked(self.packet, [idx], s)[0]
            extra.append("The previous question is parked. Send launch_text through say; you may put ONE short "
                         "sentence (max 20 words, no question, no content) before it saying the earlier question "
                         "can be revisited later.")
        offer = list(offerable(s))
        if offer:
            names = ", ".join(self.packet.parts[i].label or self.packet.parts[i].part_id for i in offer)
            extra.append(f"Parked earlier: {names}. Your message must also offer to go back to "
                         f"{'it' if len(offer) == 1 else 'them'} (name it); do not name the next question.")
        if s.state in (AWAITING_ADVANCE, SYNTHESIS) and s.queue:
            extra.append("If the student wants to go back, run turn --intent revisit --part <part_id> (a parked part "
                         "from revisit_options). If they want to move on, label it confirm_advance."
                         if s.state == AWAITING_ADVANCE else
                         "Offer the parked parts once more in the closing message; if the student declines, run end.")
        attempt_no = self._attempt_no(pe)
        if s.state == WORKING and attempt_no > 1:
            extra.append(f"This is a revisit (attempt {attempt_no}); the earlier work still counts. Hint level is "
                         f"restored to {s.hint_level}.")
```

and call `self._rules(s, ledger, unresolved, self._form_active(s, pe), extra)`. Add these keys to `out` after the existing dict is built:

```python
        out["skip_requests"] = s.skip_requests
        out["attempt"] = attempt_no
        out["deferred_queue"] = _parked(self.packet, s.queue, s)
        if offer:
            out["revisit_offer"] = _parked(self.packet, offer, s)
        if s.state in (AWAITING_ADVANCE, SYNTHESIS) and s.queue:
            out["revisit_options"] = _parked(self.packet, s.queue, s)
        if parked_now:
            out["parked"] = parked_now
```

(f) In `turn`: add parameters `skip: bool = False, revisit_part: str | None = None` to the signature; after `newly = [...]` add

```python
        new_pitfalls = [p.id for p in pc.pitfalls if p.id in now.pitfalls_hit and p.id not in prev.pitfalls_hit]
        skip_now = counts_as_skip(intent, text, skip, s.state in (LAUNCH, WORKING))
        real = is_real_attempt(intent, text, bool(newly or new_pitfalls), admits_gap is not None)
        target = self._resolve_revisit(s, intent, revisit_part)
```

Change the `student_event` call to `new, info = student_event(s, intent, len(self.packet.parts), bool(newly), skip=skip_now, real_attempt=real, revisit=target)`.

Replace the line `part_id = self.packet.parts[new.part_index].part_id` and the `data` block with:

```python
        part_id = part.part_id if info.get("skip_ended") else self.packet.parts[new.part_index].part_id
        data = dict(info)
        data["made_progress"] = bool(newly)
        data["established"] = newly
        data["real_attempt"] = real
        if skip_now:
            data["skip"] = True
        if target is not None:
            data["revisit"] = target
            data["revisit_part"] = self.packet.parts[target].part_id
        if admits_gap:
            data.update(admits_gap=True, gap_axis=admits_gap)
```

After the `if part_id == part.part_id:` block's `self._auto_resolve(part, pc, new)` line (still inside that block), add:

```python
            if info.get("skip_ended"):
                self.log.append("part_status", part=part.part_id, state=new.state, hint_level=s.hint_level,
                                data={"status": info["part_status"], "attempt": self._attempt_no(pe),
                                      "real_attempt": info["had_real_attempt"], "skip_requests": info["skip_count"]})
```

Add the resolver method to `Session`:

```python
    def _resolve_revisit(self, s: FsmState, intent: str, ref: str | None) -> int | None:
        if intent != "revisit":
            if ref:
                raise ValueError("--part is only used with --intent revisit")
            return None
        if s.state not in (AWAITING_ADVANCE, SYNTHESIS):
            return None                                   # the FSM explains why
        names = ", ".join(f"{p['part_id']} ({p['label']})" for p in _parked(self.packet, s.queue))
        if not s.queue:
            raise Refused("no parts are parked, so there is nothing to go back to", _NEXT.get(s.state, []))
        if ref is None:
            if len(s.queue) == 1:
                return s.queue[0]
            raise Refused(f"several parts are parked: {names}; pass --part with one of these ids",
                          ["turn --intent revisit --part <part_id> --stdin"])
        key = _norm(ref).lower()
        for i in s.queue:
            p = self.packet.parts[i]
            label = (p.label or "").lower()
            if key in (p.part_id.lower(), label, label.rsplit(" ", 1)[-1]):
                return i
        raise Refused(f"{ref!r} is not a parked part; parked: {names}", ["turn --intent revisit --part <part_id> --stdin"])
```

- [ ] **Step 6: Edit `agent/tutor/cli.py`**

In the `turn` parser add `t.add_argument("--skip", action="store_true")` and `t.add_argument("--part")`; in `_dispatch` pass `skip=args.skip, revisit_part=args.part` to `session.turn(...)`.

- [ ] **Step 7: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass. `park_q1` calls `s.say(NUDGE)` which in Task 2 is not yet linted for the nudge, so it simply logs; Task 3 makes it a gate.

- [ ] **Step 8: Commit**

```bash
git add agent/tutor/skip.py agent/tutor/ledger.py agent/tutor/session.py agent/tutor/cli.py tests/agent/tutor/skip_support.py tests/agent/tutor/test_tutor_skip.py
git commit -m "feat(tutor): two-request skip, real-attempt detection and revisit turns"
```

---

### Task 3: `say` rules (nudge, offer, mid-part, launch acknowledgement) and the `end` gate

**Files:**
- Modify: `agent/tutor/lint.py` (`lint_message` new parameters)
- Modify: `agent/tutor/session.py` (`say`, `end`, helpers)
- Create: `tests/agent/tutor/test_tutor_say_skip.py`

**Interfaces:**
- Consumes (Tasks 1-2): `fsm.offerable`, `fsm.fresh_index`, `FsmState.queue/skip_requests`, `student` event `data.skip/skip_ended`.
- Produces:
  - `lint_message(..., skip_nudge: bool = False, must_mention=(), queued_patterns=())` where `must_mention` and `queued_patterns` are sequences of `(label, compiled_regex)`. New codes: `SKIP_NUDGE`, `REVISIT_OFFER_MISSING`, `REVISIT_MID_PART`.
  - `Session.say` returns `LAUNCH_ACK` violations for a bad acknowledgement; logs `tutor_say` with `data {"checkin": bool, "offer": [part_id, ...]}`.
  - `Session.end` refuses (with `next`) when parked parts remain and the last `tutor_say` was not a SYNTHESIS message that offered them.
  - module helpers `session._mention(part) -> re.Pattern`, constant `MAX_ACK_WORDS = 20`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_say_skip.py
import tempfile
import unittest

from agent.tutor.session import Refused
from skip_support import (
    CHECKIN, CHECKIN_OFFER, CHECK_Q1, M2, NUDGE, close_q1, close_q2, codes, cover_q2, make, park_q1,
)

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


class TestSkipNudge(unittest.TestCase):
    def test_the_reply_to_a_first_skip_request_must_be_one_inviting_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "I would rather skip this one", skip=True)
            self.assertIn("SKIP_NUDGE", codes(s.say("Sure, we can skip it. What would you like to do?", check=True)))
            self.assertIn("SKIP_NUDGE", codes(s.say("Walking away is the complement of picking anything else.", check=True)))
            self.assertIn("NEXT_PART_REFERENCE", codes(s.say("What have you tried? Otherwise we could go to Question 2.", check=True)))
            r = s.say(NUDGE)
            self.assertTrue(r["ok"])

    def test_after_the_nudge_a_normal_reply_has_no_nudge_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "I would rather skip this one", skip=True)
            s.say(NUDGE)
            s.turn("attempt", "I guess I could start with the default option here")
            self.assertTrue(s.say("What do you mean by the default option?", check=True)["ok"])


class TestLaunchAck(unittest.TestCase):
    def test_one_short_acknowledgement_may_precede_the_launch_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            ok = s.say("We can come back to the earlier one later. " + LAUNCH_Q2, check=True)
            self.assertTrue(ok["ok"], ok)
            self.assertTrue(s.say(LAUNCH_Q2, check=True)["ok"])

    def test_the_acknowledgement_may_not_carry_content_or_be_long(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            leak = "Remember that the default is whatever is left when nothing else is picked. " + LAUNCH_Q2
            self.assertIn("REVEALS_CLAIM", codes(s.say(leak, check=True)))
            long = ("We can certainly come back to the earlier question another time once you have had a bit of a "
                    "break and a fresh look at everything else we have covered today. ") + LAUNCH_Q2
            self.assertIn("LAUNCH_ACK", codes(s.say(long, check=True)))
            self.assertIn("LAUNCH_ACK", codes(s.say("Want to come back later? " + LAUNCH_Q2, check=True)))
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say("Q2: pick an approach.", check=True)))

    def test_no_acknowledgement_is_allowed_without_a_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say("Welcome! Question 1. How would you like to approach this problem?", check=True)))


class TestRevisitOffer(unittest.TestCase):
    def test_the_checkin_after_the_next_completed_part_must_offer_the_parked_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2(s)
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say(CHECKIN, check=True)))
            r = s.say(CHECKIN_OFFER)
            self.assertTrue(r["ok"])
            self.assertEqual(s.log.load()[-1].data, {"checkin": True, "offer": ["q1"]})
            self.assertEqual(r["state"], "AWAITING_ADVANCE")
            self.assertEqual(r["revisit_options"], [{"part_id": "q1", "label": "Question 1", "status": "skipped"}])

    def test_no_offer_is_required_when_nothing_is_parked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            self.assertTrue(s.say(CHECKIN, check=True)["ok"])

    def test_a_parked_part_may_not_be_mentioned_while_another_part_is_being_worked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("attempt", "I think the preference is flat for the negative numbers")
            self.assertIn("REVISIT_MID_PART", codes(s.say("Would you like to go back to Question 1 now?", check=True)))
            self.assertTrue(s.say("What makes it flat there?", check=True)["ok"])

    def test_the_closing_message_must_offer_the_parked_parts_and_end_waits_for_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("other", "skip this too", skip=True)
            s.say(NUDGE)
            s.turn("other", "skip it", skip=True)                   # SYNTHESIS, both parked
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            self.assertEqual({o["part_id"] for o in s.view()["revisit_offer"]}, {"q1", "q2"})
            with self.assertRaises(Refused) as ctx:
                s.end("big picture")
            self.assertIn("offer", str(ctx.exception))
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say("That is all for today. Great work.", check=True)))
            self.assertTrue(s.say("That is all for today. Want to go back to Question 1 or Question 2 first?")["ok"])
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])

    def test_end_is_unaffected_when_nothing_is_parked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            s.say("Question 2. How would you like to approach this problem?")
            close_q2(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            self.assertTrue(s.end("Big picture text.")["ok"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_say_skip.py -q`
Expected: failures (`SKIP_NUDGE` etc. not produced; `end` not refused).

- [ ] **Step 3: Edit `agent/tutor/lint.py`**

Add near the other regexes:

```python
_INVITE = re.compile(r"\b(?:try|tried|trying|attempt|start|begin|first step|so far|instinct|idea|approach|guess)\b", re.I)
```

Extend the `lint_message` signature: after `last_student_text: str = "",` add `skip_nudge: bool = False, must_mention=(), queued_patterns=(),`. Insert before the `for pattern in forbidden_patterns:` loop:

```python
    if skip_nudge and not ("?" in text and _INVITE.search(text)):
        found.append(Violation("SKIP_NUDGE", "the student asked to skip: reply with one question that invites them to "
                                             "try a first step; do not agree and do not move on"))
    for label, rx in must_mention:
        if not rx.search(text):
            found.append(Violation("REVISIT_OFFER_MISSING", f"offer to go back to {label} (parked earlier)"))
    if state == WORKING:
        for label, rx in queued_patterns:
            if rx.search(text):
                found.append(Violation("REVISIT_MID_PART", f"do not bring up {label} while another part is being worked"))
                break
```

- [ ] **Step 4: Edit `agent/tutor/session.py`**

(a) Imports: `from agent.tutor.lint import Violation, lint_message`. Add constant `MAX_ACK_WORDS = 20` near `MIN_QUOTE_TOKENS`, and the helper (module level, below `split_steps`):

```python
def _mention(part) -> re.Pattern:
    """Matches the part by id, by label, or by the number at the end of its label ("1.2")."""
    alts = [rf"\b{re.escape(part.part_id)}\b"]
    if part.label:
        alts.append(re.escape(part.label) + r"(?!\d|\.\d)")
        tail = part.label.split()[-1]
        if any(ch.isdigit() for ch in tail):
            alts.append(rf"(?<![\d.]){re.escape(tail)}(?!\d)")
    return re.compile("|".join(alts), re.I)
```

(b) Replace the body of `say` from `forbidden = []` through the `violations = lint_message(...)` call and the `tutor_say` log with:

```python
        nxt_index = fsm.fresh_index(s)
        nudge = bool(last_student and last_student.data.get("skip") and not last_student.data.get("skip_ended")
                     and s.state == WORKING and not any(e.type == "tutor_say" and e.id > last_student.id for e in events))
        forbidden = []
        if (s.state in (VERIFIED, AWAITING_ADVANCE) or nudge) and nxt_index < len(self.packet.parts):
            n = self.packet.parts[nxt_index]
            forbidden = [rf"\b{re.escape(n.part_id)}\b"] + ([rf"\b{re.escape(n.label)}\b"] if n.label else [])
        blocked = {}
        if s.state == WORKING:
            nc = next_claim(pc, ledger)
            for c in pc.claims:
                if c.id in ledger.established or (s.hint_level >= 3 and nc is not None and c.id == nc.id):
                    continue
                blocked[c.id] = c.recognizer
        offer_parts = [self.packet.parts[i] for i in fsm.offerable(s)]
        must = [(p.label or p.part_id, _mention(p)) for p in offer_parts]
        queued = [(self.packet.parts[i].label or self.packet.parts[i].part_id, _mention(self.packet.parts[i])) for i in s.queue]
        ack_issues: list[Violation] = []
        if s.state == LAUNCH and last_student and last_student.data.get("skip_ended"):
            ack_issues = self._ack_issues(text, part, last_student.part)
            if not ack_issues and _norm(text) != _norm(part.launch_text()) and _norm(text).endswith(_norm(part.launch_text())):
                allowed.append(text)
        violations = lint_message(
            text, state=s.state, hint_level=s.hint_level, student_text=student_text, statement=part.statement,
            sealed_solution=sealed_section(self._solution, part.part_id) or "", allowed_exact=allowed,
            after_define=after_define, forbidden_patterns=forbidden, blocked_claims=blocked,
            form=self._form_active(s, pe), last_student_text=last_text,
            skip_nudge=nudge, must_mention=must, queued_patterns=queued,
        ) + ack_issues
        if violations:
            payload = [v.to_dict() for v in violations]
            if not check:
                self.log.append("lint_reject", part=part.part_id, state=s.state, hint_level=s.hint_level, text=text,
                                data={"violations": payload})
            return {"ok": False, "violations": payload,
                    "message": "Revise the draft and call say again. Send nothing to the student until it returns ok."}
        if check:
            return {"ok": True, "checked": True}
        checkin = s.state == VERIFIED
        new = fsm.checkin_event(s) if checkin else s
        self.log.append("tutor_say", part=part.part_id, state=new.state, hint_level=new.hint_level, text=text,
                        data={"checkin": checkin, "offer": [p.part_id for p in offer_parts]})
        return {**self._brief(), "send": text}
```

Remove the old `nxt_index = s.part_index + 1` / `forbidden = []` block above it (the new code replaces it; keep the `blocked` computation only once).

(c) Add the acknowledgement checker to `Session`:

```python
    def _ack_issues(self, text: str, part, parked_id: str) -> list[Violation]:
        launch, full = _norm(part.launch_text()), _norm(text)
        if not full.endswith(launch) or full == launch:
            return []                                              # plain LAUNCH_NOT_VERBATIM handles it
        prefix = full[: len(full) - len(launch)].strip()
        issues: list[Violation] = []
        if len(prefix.split()) > MAX_ACK_WORDS:
            issues.append(Violation("LAUNCH_ACK", f"keep the acknowledgement to {MAX_ACK_WORDS} words"))
        if "?" in prefix:
            issues.append(Violation("LAUNCH_ACK", "the acknowledgement must not be a question"))
        old = next(p for p in self.packet.parts if p.part_id == parked_id)
        old_pc = self.packet.claims[old.part_id]
        old_ledger = build_ledger(old_pc, self._part_events(self.log.load(), old.part_id))
        blocked = {c.id: c.recognizer for c in old_pc.claims if c.id not in old_ledger.established}
        issues += lint_message(prefix, state=WORKING, hint_level=0, statement=old.statement,
                               sealed_solution=sealed_section(self._solution, old.part_id) or "", blocked_claims=blocked)
        return issues
```

(d) In `end`, replace the `missing = [...]` check and add the offer gate:

```python
        parked = set(s.queue)
        missing = [p.part_id for i, p in enumerate(self.packet.parts) if not self._closed(events, p.part_id) and i not in parked]
        if missing:
            raise Refused(f"parts not closed: {missing}", ["verify"])
        last_say = next((e for e in reversed(events) if e.type == "tutor_say"), None)
        if parked and not (last_say and last_say.state == SYNTHESIS and last_say.data.get("offer")):
            names = ", ".join(self.packet.parts[i].label or self.packet.parts[i].part_id for i in s.queue)
            raise Refused(f"parked parts remain ({names}); say a closing message that offers to go back to them, "
                          "then run end", ["say (closing message offering the parked parts)"])
```

- [ ] **Step 5: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass. If a Plan A test relies on `s.part_index + 1` for the forbidden pattern, `fresh_index` gives the same value without parked parts.

- [ ] **Step 6: Commit**

```bash
git add agent/tutor/lint.py agent/tutor/session.py tests/agent/tutor/test_tutor_say_skip.py
git commit -m "feat(tutor): skip nudge, revisit offer, mid-part guard and closing-offer gate"
```

---

### Task 4: Revisit scoring (Proficient cap), attempt numbers, summary statuses

**Files:**
- Create: `agent/tutor/status.py`
- Modify: `agent/tutor/ratings.py` (`ceiling`, `cap_evidence`)
- Modify: `agent/tutor/session.py` (`verify`: `close_part` data gains `attempt`)
- Modify: `agent/tutor/render.py` (`render_summary`)
- Create: `tests/agent/tutor/test_tutor_revisit.py`

**Interfaces:**
- Consumes: `part_status` events (Task 2), `student` events with `intent == "revisit"` (Task 2), `close_part` events.
- Produces:
  - `status.attempt_records(events) -> list[dict]` — chronological `{part, attempt, status, event}` for every `close_part` (`status: "rated"`, with `ratings`) and `part_status` event (`status: "deferred"|"skipped"`); `status.final_status(events, part_id) -> str | None` (`"rated"`, `"deferred"`, `"skipped"`, `"revisiting"` or `None`).
  - `ratings.ceiling` returns Proficient at most (reason `"revisited after being parked"`) when the part's events contain a `revisit` student event; `cap_evidence` then includes that event's id.
  - `close_part` event `data` gains `attempt` (int).

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_revisit.py
import os
import tempfile
import unittest

from agent.tutor.render import render_summary
from agent.tutor.status import attempt_records, final_status
from skip_support import CHECKIN, CHECKIN_OFFER, DEV, MAST, PROF, close_q1, close_q2, cover_q1, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


def revisit_q1(s, deferred=False):
    park_q1(s, with_attempt=deferred)
    s.say(LAUNCH_Q2)
    close_q2(s)
    s.say(CHECKIN_OFFER)
    return s.turn("revisit", "yes let's go back to the first question")


class TestRevisitScoring(unittest.TestCase):
    def test_a_clean_revisit_is_capped_at_proficient_everywhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            b = revisit_q1(s)
            self.assertEqual((b["part_id"], b["state"], b["attempt"]), ("q1", "WORKING", 2))
            closed = close_q1(s)
            ratings = s.log.load()[-1].data["ratings"]
            self.assertTrue(closed["closed"])
            self.assertEqual({r["rating"] for r in ratings.values()}, {PROF})
            self.assertEqual(s.log.load()[-1].data["attempt"], 2)
            revisit_id = next(e.id for e in s.log.load() if e.type == "student" and e.intent == "revisit")
            self.assertTrue(all(revisit_id in r["evidence"] for r in ratings.values()))

    def test_a_part_never_parked_keeps_mastered(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            ratings = s.log.load()[-1].data["ratings"]
            self.assertEqual({r["rating"] for r in ratings.values()}, {MAST})
            self.assertEqual(s.log.load()[-1].data["attempt"], 1)

    def test_the_revisited_part_keeps_its_claims_and_hint_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("stuck", "I am stuck")                           # hint level 1
            s.turn("attempt", "walking away is whatever is left over when nothing else is chosen")   # C2
            s.turn("other", "skip", skip=True)
            s.say("What is the first thing you would try here?")
            s.turn("other", "skip it please", skip=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            b = s.turn("revisit", "go back to the first one")
            self.assertEqual((b["hint_level"], b["claims_established"]), (1, ["C2"]))


class TestStatusAndSummary(unittest.TestCase):
    def test_attempt_records_and_final_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            revisit_q1(s, deferred=True)
            close_q1(s)
            events = s.log.load()
            recs = [(r["part"], r["attempt"], r["status"]) for r in attempt_records(events)]
            self.assertEqual(recs, [("q1", 1, "deferred"), ("q2", 1, "rated"), ("q1", 2, "rated")])
            self.assertEqual(final_status(events, "q1"), "rated")
            self.assertIsNone(final_status(events[:1], "q1"))

    def test_final_status_while_parked_and_revisiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            self.assertEqual(final_status(s.log.load(), "q1"), "skipped")
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "let's go back")
            self.assertEqual(final_status(s.log.load(), "q1"), "revisiting")

    def test_summary_marks_parked_parts_and_lists_them_in_the_action_menu(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            events = s.log.load()
            text = render_summary(events, s.packet, "Big picture.", [], "2026-10-09")
            self.assertIn("| Question 1 |", text)
            self.assertIn("deferred", text)
            self.assertIn("Revisit `random-consideration-set`", text)
            skipped = make(tempfile.mkdtemp())[1]
            park_q1(skipped)
            text2 = render_summary(skipped.log.load(), skipped.packet, "Big picture.", [], "2026-10-09")
            self.assertIn("not covered", text2)
            self.assertNotIn("Revisit `random-consideration-set`", text2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_revisit.py -q`
Expected: `ModuleNotFoundError: No module named 'agent.tutor.status'`.

- [ ] **Step 3: Write `agent/tutor/status.py`**

```python
# agent/tutor/status.py
"""status.py -- what happened to each part, read from the log (v1.1 §8-§9). One record per
attempt that ended: a clean close (`rated`), or a skip request that parked it (`deferred` when
a real attempt was made first, else `skipped`)."""
from __future__ import annotations

from agent.tutor.events import Event


def attempt_records(events: list[Event]) -> list[dict]:
    out = []
    for e in events:
        if e.type == "close_part":
            out.append({"part": e.part, "attempt": e.data.get("attempt", 1), "status": "rated", "event": e})
        elif e.type == "part_status":
            out.append({"part": e.part, "attempt": e.data.get("attempt", 1), "status": e.data["status"], "event": e})
    return out


def final_status(events: list[Event], part_id: str) -> str | None:
    status = None
    for e in events:
        if e.part != part_id:
            continue
        if e.type == "close_part":
            status = "rated"
        elif e.type == "part_status":
            status = e.data["status"]
        elif e.type == "student" and e.intent == "revisit":
            status = "revisiting"
    return status
```

- [ ] **Step 4: Edit `agent/tutor/ratings.py`**

Rename the existing `ceiling` to `_base_ceiling` and add:

```python
def _revisits(part_events: list[Event]) -> list[Event]:
    return [e for e in part_events if e.type == "student" and e.intent == "revisit"]


def ceiling(part_events: list[Event], axis: str) -> tuple[str, list[str]]:
    rating, reasons = _base_ceiling(part_events, axis)
    if _revisits(part_events) and rating == RATINGS[2]:
        return RATINGS[1], reasons + ["revisited after being parked"]
    return rating, reasons
```

In `cap_evidence`, add after the `admits_gap` line (before `if not ids:`):

```python
    ids += [e.id for e in _revisits(part_events) if RATINGS.index(ceiling(part_events, axis)[0]) <= 1]
```

(The revisit event is cited whenever the axis is at most Proficient, so a `Mastered`-capped-by-revisit axis always carries it; Developing axes also list it, which is harmless.)

- [ ] **Step 5: Edit `agent/tutor/session.py` `verify`**

Change the `close_part` append to include the attempt:

```python
            self.log.append("close_part", state=VERIFIED, data={"ratings": ratings, "attempt": self._attempt_no(pe)}, **common)
```

- [ ] **Step 6: Edit `agent/tutor/render.py` `render_summary`**

Add `from agent.tutor.status import final_status` and replace the diagnostic-table cell logic and the Action Menu review loop:

```python
    for part in packet.parts:
        r = closed.get(part.part_id)
        st = final_status(events, part.part_id)
        word = {"deferred": "deferred", "skipped": "not covered", "revisiting": "in progress"}.get(st, "—")
        cells = [r[a]["rating"] if r and st == "rated" else word for a in AXES]
        lines.append(f"| {part.label or part.part_id} | {', '.join(part.concept_tags)} | " + " | ".join(cells) + " |")
```

(`closed` stays as built; a part that was rated, then not re-parked, has `st == "rated"`.) In the Action Menu, after the Developing loop and before the prior-gaps loop, add:

```python
    for part in packet.parts:
        st = final_status(events, part.part_id)
        if st == "deferred":
            for tag in part.concept_tags:
                lines.append(f"- Revisit `{tag}` ({part.label or part.part_id} was deferred after an attempt)")
        elif st == "skipped":
            lines.append(f"- {part.label or part.part_id} was not covered")
```

Change the final fallback condition to `if len(lines) > 0 and lines[-1].startswith("## 4")` pattern-free: keep `if not review and not prior_gaps:` but only emit "No review items flagged." when no deferred/skipped line was added: track with a local `flagged = False` set True inside the two new branches and test `if not review and not prior_gaps and not flagged`.

- [ ] **Step 7: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add agent/tutor/status.py agent/tutor/ratings.py agent/tutor/session.py agent/tutor/render.py tests/agent/tutor/test_tutor_revisit.py
git commit -m "feat(tutor): revisit scoring cap, attempt records and parked-part summary"
```

---

### Task 5: Profile v2

**Files:**
- Modify: `agent/tutor/profile.py` (replace the whole file)
- Modify: `tests/agent/tutor/test_tutor_render_profile.py` (one assertion if it pins `schema_version == 1`)
- Create: `tests/agent/tutor/test_tutor_profile_v2.py`

**Interfaces:**
- Consumes: `status.attempt_records` (Task 4), `close_part` data `ratings` and `attempt`.
- Produces: `SCHEMA_VERSION = 2`; `load_profile(path)` normalises a v1 file (every history entry gets `status: "rated"`, `attempt: 1`; version becomes 2); `update_profile(...)` is idempotent per `session_id` (re-running for the same session replaces that session's history entries); history entries: `{"session","date","part","status","attempt"}` plus `axis`/`rating` when `status == "rated"`; `open_gaps(profile)` counts a concept as a gap when its latest rated session has a Developing rating, it has an open misconception, or it has a `deferred` entry with no later rated entry; `render_profile_md` renders all three statuses.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_profile_v2.py
import json
import os
import tempfile
import unittest

from agent.tutor.profile import SCHEMA_VERSION, load_profile, open_gaps, render_profile_md, save_profile, update_profile
from skip_support import CHECKIN_OFFER, DEV, close_q1, close_q2, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"
V1 = {"schema_version": 1, "concepts": {
    "concavity": {"history": [{"session": "2026-09-01-1000", "date": "2026-09-01", "part": "q2", "axis": "rigor",
                               "rating": DEV}], "open_misconceptions": []}}}


def entries(profile, tag):
    return profile["concepts"][tag]["history"]


class TestProfileV2(unittest.TestCase):
    def test_a_v1_file_loads_as_v2_with_every_entry_rated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "learner_profile.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(V1, f)
            prof = load_profile(p)
            self.assertEqual(prof["schema_version"], SCHEMA_VERSION)
            self.assertEqual(SCHEMA_VERSION, 2)
            h = entries(prof, "concavity")[0]
            self.assertEqual((h["status"], h["attempt"], h["rating"]), ("rated", 1, DEV))
            self.assertEqual(open_gaps(prof), ["concavity"])

    def test_skipped_and_deferred_attempts_are_recorded_without_ratings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)             # q1 deferred
            s.say(LAUNCH_Q2)
            close_q2(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            q1 = [h for h in entries(prof, "random-consideration-set")]
            self.assertEqual([(h["part"], h["status"], h["attempt"]) for h in q1], [("q1", "deferred", 1)])
            self.assertNotIn("rating", q1[0])
            self.assertEqual(open_gaps(prof), ["default-alternative", "random-consideration-set"])

    def test_a_skipped_part_is_not_a_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            self.assertEqual(entries(prof, "random-consideration-set")[0]["status"], "skipped")
            self.assertEqual(open_gaps(prof), [])

    def test_a_later_rated_revisit_closes_the_deferred_gap_and_both_attempts_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s, with_attempt=True)
            s.say(LAUNCH_Q2)
            close_q2(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "go back to the first question")
            close_q1(s)
            prof = update_profile(load_profile(s.paths.profile_json), session_id=s.session_id, date="2026-10-09",
                                  events=s.log.load(), packet=s.packet)
            q1 = [(h["status"], h["attempt"]) for h in entries(prof, "random-consideration-set")
                  if h["part"] == "q1" and h.get("axis", "conceptual") == "conceptual"]
            self.assertEqual(q1, [("deferred", 1), ("rated", 2)])
            self.assertNotIn("random-consideration-set", open_gaps(prof))

    def test_updating_twice_for_the_same_session_does_not_duplicate_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            close_q1(s)
            args = dict(session_id=s.session_id, date="2026-10-09", events=s.log.load(), packet=s.packet)
            once = update_profile(load_profile(s.paths.profile_json), **args)
            twice = update_profile(once, **args)
            self.assertEqual(once, twice)

    def test_markdown_renders_all_statuses_without_crashing(self):
        prof = {"schema_version": 2, "concepts": {"t": {"history": [
            {"session": "s1", "date": "2026-10-09", "part": "q1", "status": "deferred", "attempt": 1},
            {"session": "s1", "date": "2026-10-09", "part": "q2", "status": "skipped", "attempt": 1},
            {"session": "s1", "date": "2026-10-09", "part": "q1", "status": "rated", "attempt": 2, "axis": "rigor", "rating": DEV}],
            "open_misconceptions": []}}}
        text = render_profile_md(prof)
        self.assertIn("deferred", text)
        self.assertIn("skipped", text)
        self.assertIn("(attempt 2)", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_profile_v2.py -q`
Expected: failures (`schema_version` still 1, no `status` keys).

- [ ] **Step 3: Replace `agent/tutor/profile.py`**

```python
# agent/tutor/profile.py  (replace the whole file)
"""profile.py -- per-course concept-gap tracker (v1 spec §6, v1.1 §9). Single writer: the
session (`end`, `pause`). schema_version 2 adds `status` (rated | deferred | skipped) and
`attempt` to every history entry; v1 files load with every entry `rated`, attempt 1. The
future learning-progress subproject builds on this schema."""
from __future__ import annotations

import copy
import json
import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS
from agent.tutor.status import attempt_records

SCHEMA_VERSION = 2


def _normalise(profile: dict) -> dict:
    prof = copy.deepcopy(profile)
    prof["schema_version"] = SCHEMA_VERSION
    for entry in prof.get("concepts", {}).values():
        for h in entry.get("history", []):
            h.setdefault("status", "rated")
            h.setdefault("attempt", 1)
    return prof


def load_profile(path: str) -> dict:
    if not os.path.exists(path):
        return {"schema_version": SCHEMA_VERSION, "concepts": {}}
    with open(path, "r", encoding="utf-8") as f:
        return _normalise(json.load(f))


def update_profile(profile: dict, *, session_id: str, date: str, events: list[Event], packet: Packet) -> dict:
    """Idempotent per session: this session's earlier entries are replaced, so `pause` followed by `end`
    does not duplicate history."""
    new = _normalise(profile)
    for entry in new["concepts"].values():
        entry["history"] = [h for h in entry["history"] if h["session"] != session_id]
    records = attempt_records(events)
    resolved = {(e.part, e.data["tag"]) for e in events if e.type == "misconception_resolved"}
    for part in packet.parts:
        for tag in part.concept_tags:
            entry = new["concepts"].setdefault(tag, {"history": [], "open_misconceptions": []})
            for rec in records:
                if rec["part"] != part.part_id:
                    continue
                base = {"session": session_id, "date": date, "part": part.part_id, "status": rec["status"],
                        "attempt": rec["attempt"]}
                if rec["status"] == "rated":
                    for axis, r in rec["event"].data["ratings"].items():
                        entry["history"].append({**base, "axis": axis, "rating": r["rating"]})
                else:
                    entry["history"].append(base)
            for e in events:
                if e.type == "misconception" and e.part == part.part_id:
                    mtag = e.data["tag"]
                    if (part.part_id, mtag) in resolved:
                        if mtag in entry["open_misconceptions"]:
                            entry["open_misconceptions"].remove(mtag)
                    elif mtag not in entry["open_misconceptions"]:
                        entry["open_misconceptions"].append(mtag)
            for (rpart, mtag) in resolved:
                if rpart == part.part_id and mtag in entry["open_misconceptions"]:
                    entry["open_misconceptions"].remove(mtag)
    return new


def _is_gap(entry: dict) -> bool:
    hist = entry["history"]
    rated = [h for h in hist if h.get("status", "rated") == "rated"]
    latest = max((h["session"] for h in rated), default=None)
    developing = any(h["rating"] == RATINGS[0] for h in rated if h["session"] == latest)
    key = lambda h: (h["session"], h.get("attempt", 1))
    last_rated = max((key(h) for h in rated), default=None)
    deferred_open = any(h.get("status") == "deferred" and (last_rated is None or key(h) > last_rated) for h in hist)
    return developing or bool(entry["open_misconceptions"]) or deferred_open


def open_gaps(profile: dict) -> list[str]:
    return [tag for tag, entry in sorted(profile["concepts"].items()) if _is_gap(entry)]


def render_profile_md(profile: dict) -> str:
    lines = ["# Learner profile", "", f"_schema v{profile['schema_version']}_", "", "## Open gaps", ""]
    gaps = open_gaps(profile)
    lines += [f"- `{t}`" + (f" — misconceptions: {', '.join(profile['concepts'][t]['open_misconceptions'])}"
                            if profile['concepts'][t]['open_misconceptions'] else "") for t in gaps] or ["- None"]
    lines += ["", "## History", ""]
    for tag, entry in sorted(profile["concepts"].items()):
        lines.append(f"### {tag}")
        for h in entry["history"]:
            suffix = f" (attempt {h['attempt']})" if h.get("attempt", 1) > 1 else ""
            status = h.get("status", "rated")
            if status == "rated":
                lines.append(f"- {h['date']} {h['part']} {h['axis']}: {h['rating']}{suffix}")
            elif status == "deferred":
                lines.append(f"- {h['date']} {h['part']}: deferred after an attempt (gap evidence){suffix}")
            else:
                lines.append(f"- {h['date']} {h['part']}: skipped (not covered){suffix}")
        lines.append("")
    return "\n".join(lines) + "\n"


def save_profile(json_path: str, md_path: str, profile: dict) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_profile_md(profile))
```

Watch out: `ratings.py` must not import `profile` or `status` (it does not), and `status.py` imports only `events`, so there is no cycle. In `test_tutor_render_profile.py`, update any `assertEqual(profile["schema_version"], 1)` to `2`.

- [ ] **Step 4: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add agent/tutor/profile.py tests/agent/tutor/test_tutor_profile_v2.py tests/agent/tutor/test_tutor_render_profile.py
git commit -m "feat(tutor): learner profile v2 with deferred and skipped attempts"
```

---

### Task 6: `pause`, resume, `start --fresh`, `end --partial`

**Files:**
- Modify: `agent/tutor/session.py` (`start`, `_require_live`, `pause`, `_render_partial`, `_end_partial`, `_brief`)
- Modify: `agent/tutor/cli.py` (`start --fresh`, `pause`, `end --partial`)
- Create: `tests/agent/tutor/test_tutor_pause.py`

**Interfaces:**
- Consumes: `fsm.pause_event/resume_event/PAUSED`, `profile.update_profile` idempotence (Task 5), `render.write_session_docs`.
- Produces:
  - `Session.pause() -> dict` (`{"ok": True, "paused": True, "transcript", "summary", "profile", "next"}`); logs `paused`; writes docs + profile.
  - `Session.start(paths, now=None, fresh=False)`: open+paused session → logs `resumed` (default), or with `fresh=True` ends it as partial (`session_end` with `data.partial`) and begins a new session; `fresh=True` also ends an open non-paused session as partial.
  - `Session._require_live(s)` refuses `PAUSED` with `next: ["start", "start --fresh"]`.
  - Brief key `resumed: True` when the last event is `resumed`.
  - CLI: `start --fresh`, `pause`, `end --partial` (alias of `pause`; `--big-picture-file` required only without `--partial`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_pause.py
import datetime
import json
import os
import tempfile
import unittest

from agent.tutor.cli import main
from agent.tutor.profile import load_profile
from agent.tutor.session import Refused, Session
from skip_support import NOW, M2, close_q1, make


class TestPause(unittest.TestCase):
    def test_pause_writes_docs_and_profile_and_blocks_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            close_q1(s)
            s.say("Right. Do you have any lingering questions, or are you ready to move on?")
            out = s.pause()
            self.assertTrue(out["paused"])
            self.assertTrue(os.path.exists(out["transcript"]))
            self.assertTrue(os.path.exists(out["summary"]))
            prof = load_profile(paths.profile_json)
            self.assertEqual(prof["concepts"]["random-consideration-set"]["history"][0]["part"], "q1")
            self.assertEqual(s.view()["state"], "PAUSED")
            with self.assertRaises(Refused) as ctx:
                s.turn("attempt", "I will keep going")
            self.assertIn("start", ctx.exception.next_commands)
            with self.assertRaises(Refused):
                s.say("anything")
            with self.assertRaises(Refused):
                s.pause()

    def test_start_resumes_a_paused_session_with_an_identical_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("stuck", "I am stuck")
            s.turn("attempt", M2)
            before = s._brief()
            s.pause()
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=2))
            after = again.view()
            self.assertTrue(after.pop("resumed"))
            self.assertEqual(after["session"], before["session"])
            self.assertEqual({k: v for k, v in after.items() if k not in ("rules",)},
                             {k: v for k, v in before.items() if k not in ("rules",)})
            self.assertEqual(again.turn("attempt", "so it is one minus the sum of the others")["state"], "WORKING")

    def test_pause_from_launch_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.pause()
            self.assertEqual(Session.start(paths, now=NOW).view()["state"], "LAUNCH")

    def test_fresh_ends_the_paused_session_as_partial_and_starts_a_new_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.turn("attempt", M2)
            s.pause()
            sid = s.session_id
            new = Session.start(paths, now=NOW + datetime.timedelta(days=1), fresh=True)
            self.assertNotEqual(new.session_id, sid)
            self.assertEqual(new.view()["state"], "LAUNCH")
            old_events = Session.open(paths, sid).log.load()
            self.assertEqual(old_events[-1].type, "session_end")
            self.assertTrue(old_events[-1].data["partial"])
            self.assertEqual(Session.latest_session_id(paths), new.session_id)
            self.assertEqual(Session._latest_open(paths), new.session_id)

    def test_pause_then_end_does_not_duplicate_profile_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            close_q1(s)
            s.say("Right. Do you have any lingering questions, or are you ready to move on?")
            s.pause()
            first = json.dumps(load_profile(paths.profile_json), sort_keys=True)
            s2 = Session.start(paths, now=NOW)
            s2.pause()
            self.assertEqual(json.dumps(load_profile(paths.profile_json), sort_keys=True), first)


class TestPauseCli(unittest.TestCase):
    def run_cli(self, tmp, *argv, stdin=None):
        import contextlib
        import io
        import sys
        out = io.StringIO()
        old = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out):
                code = main(["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *argv])
        finally:
            sys.stdin = old
        return code, json.loads(out.getvalue())

    def test_pause_and_end_partial_and_start_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            code, res = self.run_cli(tmp, "pause")
            self.assertEqual((code, res["paused"]), (0, True))
            code, res = self.run_cli(tmp, "start")
            self.assertEqual((code, res["resumed"]), (0, True))
            code, res = self.run_cli(tmp, "end", "--partial")
            self.assertEqual((code, res["paused"]), (0, True))
            code, res = self.run_cli(tmp, "start", "--fresh")
            self.assertEqual((code, res["state"]), (0, "LAUNCH"))
            self.assertNotEqual(res["session"], s.session_id)
            code, res = self.run_cli(tmp, "end")
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_pause.py -q`
Expected: failures (`Session.pause` missing, `start(fresh=...)` unknown).

- [ ] **Step 3: Edit `agent/tutor/session.py`**

(a) Replace `start`:

```python
    @classmethod
    def start(cls, paths: TutorPaths, now: datetime | None = None, fresh: bool = False) -> "Session":
        packet = load_packet(paths)
        sid = cls._latest_open(paths)
        if sid is not None and fresh:
            cls(paths, sid, packet)._end_partial()
            sid = None
        if sid is None:
            base = (now or datetime.now()).strftime("%Y-%m-%d-%H%M")
            sid, n = base, 1
            while os.path.exists(os.path.join(paths.sessions_dir, sid)):
                n += 1
                sid = f"{base}-{n}"
            session = cls(paths, sid, packet)
            session.log.append("session_start", part=packet.parts[0].part_id, state=LAUNCH,
                               data={"problem_set": paths.problem_set})
        else:
            session = cls(paths, sid, packet)
            s = session._fsm()
            if s.state == fsm.PAUSED:
                back = fsm.resume_event(s)
                session.log.append("resumed", part=packet.parts[s.part_index].part_id, state=back.state,
                                   hint_level=back.hint_level)
        session._write_prior_gaps()
        return session
```

(b) Replace `_require_live`:

```python
    @staticmethod
    def _require_live(s: FsmState) -> None:
        if s.state == fsm.DONE:
            raise Refused("session has ended; start a new session", ["start"])
        if s.state == fsm.PAUSED:
            raise Refused("session is paused; run start to resume it, or start --fresh to begin a new one",
                          ["start", "start --fresh"])
```

(c) Add the pause machinery before `end`:

```python
    def _render_partial(self, note: str) -> dict:
        events = self.log.load()
        date = self.session_id[:10]
        transcript, summary = write_session_docs(self.dir, events, self.packet, note, self._prior_gaps(), date)
        profile = update_profile(load_profile(self.paths.profile_json), session_id=self.session_id, date=date,
                                 events=events, packet=self.packet)
        save_profile(self.paths.profile_json, self.paths.profile_md, profile)
        return {"transcript": transcript, "summary": summary, "profile": self.paths.profile_json}

    def pause(self) -> dict:
        s = self._fsm()
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        self.log.append("paused", part=part.part_id, state=fsm.PAUSED, hint_level=s.hint_level)
        return {"ok": True, "paused": True, **self._render_partial("Session paused before every part was covered."),
                "next": ["start (resume)", "start --fresh"]}

    def _end_partial(self) -> None:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        self.log.append("session_end", part=part.part_id, state=fsm.DONE, data={"partial": True})
        self._render_partial("Session ended before every part was covered.")
```

`pause` cannot use `_require_live` for a paused session (it raises Refused with start hints, which is the behaviour the test expects).

(d) In `_brief`, after `out` is built add:

```python
        if events and events[-1].type == "resumed":
            out["resumed"] = True
```

- [ ] **Step 4: Edit `agent/tutor/cli.py`**

Parser: replace `sub.add_parser("start")` with

```python
    st = sub.add_parser("start")
    st.add_argument("--fresh", action="store_true")
    sub.add_parser("pause")
```

and the `end` parser with

```python
    e = sub.add_parser("end")
    e.add_argument("--big-picture-file")
    e.add_argument("--partial", action="store_true")
```

Dispatch: `start` → `Session.start(paths, fresh=args.fresh).view()`; before the `Session.open` fallthrough nothing changes; replace the `end` branch and add `pause`:

```python
    if args.cmd == "pause" or (args.cmd == "end" and args.partial):
        return session.pause()
    if args.cmd == "end":
        if not args.big_picture_file:
            raise ValueError("end needs --big-picture-file (or use --partial / pause to stop for now)")
        return session.end(_read(args.big_picture_file))
```

- [ ] **Step 5: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass. The CLI test's last assertion (`end` without a file → exit 2) exercises the new `ValueError` path.

- [ ] **Step 6: Commit**

```bash
git add agent/tutor/session.py agent/tutor/cli.py tests/agent/tutor/test_tutor_pause.py
git commit -m "feat(tutor): pause, resume, start --fresh and end --partial"
```

---

### Task 7: Audit additions

**Files:**
- Modify: `agent/tutor/audit.py`
- Create: `tests/agent/tutor/test_tutor_audit_skip.py`

**Interfaces:**
- Consumes: `fsm.replay`, `fsm.offerable`, `fsm.WORKING/LAUNCH`, `skip.mentions_skip`, `session._mention` (import the helper lazily to avoid a cycle: copy the 12-line helper into `audit.py` as `_mention`; `session.py` keeps its own).
- Produces new finding codes: `SKIP_TOO_EARLY` (a `part_status` with `skip_requests < 2`), `SKIP_WITHOUT_NUDGE` (no `tutor_say` between the first skip request and the ending one), `REVISIT_OFFER_MISSING` (a check-in or closing message missing a required offer, recomputed from a replay), `REVISIT_MID_PART` (a `tutor_say` in `WORKING` mentioning a parked part), `SKIP_PHRASE_UNCOUNTED` (a skip phrase in a `WORKING` student turn that was not counted). Existing `ADVANCE_WITHOUT_CONFIRM` is exempt for the parts a skip-ending, revisit or `confirm_advance` turn legitimately moves.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/tutor/test_tutor_audit_skip.py
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.events import Event
from skip_support import CHECKIN, CHECKIN_OFFER, NUDGE, Q, close_q1_said, close_q2, close_q2_said, make, park_q1

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


def codes(findings):
    return [f.code for f in findings]


class TestHonestFlowIsClean(unittest.TestCase):
    def test_skip_revisit_flow_through_the_gate_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2_said(s)
            s.say(CHECKIN_OFFER)
            s.turn("revisit", "yes let's go back to the first question")
            s.say(Q)
            close_q1_said(s)
            s.say(CHECKIN)
            s.turn("confirm_advance", "ready to move on")
            self.assertEqual(codes(audit(s.log.load(), s.packet)), [])


class TestFindings(unittest.TestCase):
    def test_uncounted_skip_phrase_in_an_attempt_is_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("attempt", "I will skip the algebra and move on to the idea of the default")
            self.assertIn("SKIP_PHRASE_UNCOUNTED", codes(audit(s.log.load(), s.packet)))

    def test_ending_skip_without_any_tutor_reply_in_between(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip this", skip=True)
            s.turn("other", "skip it please", skip=True)                    # no say between the two requests
            self.assertIn("SKIP_WITHOUT_NUDGE", codes(audit(s.log.load(), s.packet)))

    def test_part_status_with_fewer_than_two_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            events = s.log.load()
            for e in events:
                if e.type == "part_status":
                    e.data["skip_requests"] = 1
            self.assertIn("SKIP_TOO_EARLY", codes(audit(events, s.packet)))

    def test_checkin_without_the_offer_is_found_even_if_the_log_was_written_around_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            close_q2(s)
            last = s.log.load()[-1]
            events = s.log.load() + [Event(id=last.id + 1, ts="t", type="tutor_say", part="q2", state="AWAITING_ADVANCE",
                                           text=CHECKIN, data={"checkin": True, "offer": []})]
            self.assertIn("REVISIT_OFFER_MISSING", codes(audit(events, s.packet)))

    def test_a_parked_part_mentioned_while_another_is_worked(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            park_q1(s)
            s.say(LAUNCH_Q2)
            s.turn("attempt", "the preference looks flat for the negative numbers to me")
            last = s.log.load()[-1]
            events = s.log.load() + [Event(id=last.id + 1, ts="t", type="tutor_say", part="q2", state="WORKING",
                                           text="Should we go back to Question 1?", data={})]
            self.assertIn("REVISIT_MID_PART", codes(audit(events, s.packet)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/agent/tutor/test_tutor_audit_skip.py -q`
Expected: failures (`ADVANCE_WITHOUT_CONFIRM` already fires on the honest flow, and the new codes are missing).

- [ ] **Step 3: Edit `agent/tutor/audit.py`**

(a) Imports: add `import re` (present), `from agent.tutor import fsm`, `from agent.tutor.skip import mentions_skip`, and the helper:

```python
def _mention(part) -> re.Pattern:
    alts = [rf"\b{re.escape(part.part_id)}\b"]
    if part.label:
        alts.append(re.escape(part.label) + r"(?!\d|\.\d)")
        tail = part.label.split()[-1]
        if any(ch.isdigit() for ch in tail):
            alts.append(rf"(?<![\d.]){re.escape(tail)}(?!\d)")
    return re.compile("|".join(alts), re.I)
```

(b) Replace the `ADVANCE_WITHOUT_CONFIRM` test at the top of the loop with an exemption flag. Before the loop add `move_ok = False`. In the loop, replace the first `if e.part and prev_part ...` block with:

```python
        mover = e.type == "student" and (e.intent in ("confirm_advance", "revisit") or e.data.get("skip_ended"))
        if e.part and prev_part and e.part != prev_part:
            if not (mover or move_ok):
                found.append(Finding("ADVANCE_WITHOUT_CONFIRM", e.id, f"moved from {prev_part} to {e.part} without a student confirm_advance, revisit or second skip request"))
            move_ok = False
        if mover and e.data.get("skip_ended"):
            move_ok = True                                  # the next event is logged under the new part
```

(c) Inside the loop, add (after the `verify_release` block):

```python
        if e.type == "part_status":
            if e.data.get("skip_requests", 2) < 2:
                found.append(Finding("SKIP_TOO_EARLY", e.id, f"{e.part} was parked after fewer than two skip requests"))
            first = next((x for x in events if x.type == "student" and x.part == e.part and x.data.get("skip") and x.id < e.id
                          and x.data.get("skip_count") == 1), None)
            ending = next((x for x in reversed(events) if x.type == "student" and x.id < e.id and x.data.get("skip_ended")), None)
            if first is not None and ending is not None and not any(
                    x.type == "tutor_say" and first.id < x.id < ending.id for x in events):
                found.append(Finding("SKIP_WITHOUT_NUDGE", e.id, "no tutor reply between the first and the ending skip request"))
        if e.type == "student" and e.state in (fsm.WORKING, fsm.LAUNCH) and not e.data.get("skip") \
                and e.intent not in ("confirm_advance", "define_request", "revisit") and mentions_skip(e.text):
            found.append(Finding("SKIP_PHRASE_UNCOUNTED", e.id, "the message mentions skipping or moving on but was not counted as a skip request"))
        if e.type == "tutor_say":
            before = fsm.replay([x for x in events if x.id < e.id], len(packet.parts))
            if e.data.get("checkin") or before.state == fsm.SYNTHESIS:
                for i in fsm.offerable(before):
                    p = packet.parts[i]
                    if not _mention(p).search(e.text or ""):
                        found.append(Finding("REVISIT_OFFER_MISSING", e.id, f"the message did not offer to go back to {p.label or p.part_id}"))
            if before.state == fsm.WORKING:
                for i in before.queue:
                    if _mention(packet.parts[i]).search(e.text or ""):
                        found.append(Finding("REVISIT_MID_PART", e.id, f"{packet.parts[i].label or packet.parts[i].part_id} was brought up while another part was being worked"))
                        break
```

Note `fsm.replay` raises `IllegalTransition` on a malformed log; wrap the `tutor_say` replay in `try/except fsm.IllegalTransition: pass` so the audit still reports what it can.

- [ ] **Step 4: Run the new tests and the whole tutor suite**

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass. If `test_skip_revisit_flow_through_the_gate_has_no_findings` reports an unexpected code, read the finding's detail and fix the exemption logic, not the test.

- [ ] **Step 5: Commit**

```bash
git add agent/tutor/audit.py tests/agent/tutor/test_tutor_audit_skip.py
git commit -m "feat(tutor): audit checks for skips, revisit offers and mid-part mentions"
```

---

### Task 8: Contract, docs, regression scenarios

**Files:**
- Modify: `agent/tutor/bootstrap_prompt.md`
- Modify: `agent/tutor/README.md`
- Modify: `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md` (append a "v1.1 Plan B" section)
- Modify: `tests/agent/tutor/test_tutor_regression.py` (append the trial-3 analogue) or create `tests/agent/tutor/test_tutor_regression_skip.py`
- Modify: `tests/agent/tutor/test_tutor_cli.py` only if a Plan A assertion pins the command list.

**Interfaces:** consumes everything above; produces the agent-facing contract and the end-to-end regression for the live trial's "student asked three times to move on" failure.

- [ ] **Step 1: Write the regression test**

```python
# tests/agent/tutor/test_tutor_regression_skip.py
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.profile import load_profile, open_gaps
from skip_support import (
    CHECKIN, CHECKIN_OFFER, PROF, Q, close_q1_said, close_q2_said, codes, make,
)

LAUNCH_Q2 = "Question 2. How would you like to approach this problem?"


class TestTrialAnalogueStudentAsksToMoveOn(unittest.TestCase):
    """Live trial 1: the student asked three times to move on and the tutor kept forcing the problem."""

    def test_two_requests_are_enough_and_the_part_can_be_revisited_for_a_capped_rating(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.say("Question 1. How would you like to approach this problem?")
            s.turn("attempt", "I think it is the default minus something but I am not sure what")        # 14 words: real
            self.assertTrue(s.say("What does the default stand for in your sentence?")["ok"])
            s.turn("other", "I would like to move on to the next question please", skip=True)
            bad = s.say("Let's keep going, you can do this. Think about the probabilities.", check=True)
            self.assertIn("SKIP_NUDGE", codes(bad))
            self.assertTrue(s.say("What is the first thing you would try writing down about the default?")["ok"])
            b = s.turn("other", "no really, can we skip this one", skip=True)
            self.assertEqual((b["part_id"], b["state"]), ("q2", "LAUNCH"))
            self.assertEqual(b["deferred_queue"][0]["status"], "deferred")
            self.assertTrue(s.say("We can come back to it. " + LAUNCH_Q2)["ok"])
            close_q2_said(s)
            self.assertIn("REVISIT_OFFER_MISSING", codes(s.say(CHECKIN, check=True)))
            s.say(CHECKIN_OFFER)
            b = s.turn("revisit", "yes, go back to the first question")
            self.assertEqual((b["part_id"], b["attempt"]), ("q1", 2))
            s.say(Q)
            close_q1_said(s)
            self.assertEqual({r["rating"] for r in s.log.load()[-1].data["ratings"].values()}, {PROF})
            s.say(CHECKIN)
            s.turn("confirm_advance", "yes, I am done, thanks")
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])
            self.assertEqual([f.code for f in audit(s.log.load(), s.packet)], [])
            prof = load_profile(paths.profile_json)
            statuses = [(h["status"], h["attempt"]) for h in prof["concepts"]["random-consideration-set"]["history"]
                        if h.get("axis", "conceptual") == "conceptual"]
            self.assertEqual(statuses, [("deferred", 1), ("rated", 2)])
            self.assertNotIn("random-consideration-set", open_gaps(prof))

    def test_declining_the_offer_still_ends_cleanly_after_one_last_offer(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.turn("other", "skip this", skip=True)
            s.say("What is the first thing you would try here?")
            s.turn("other", "skip", skip=True)
            s.say(LAUNCH_Q2)
            close_q2_said(s)
            s.say(CHECKIN_OFFER)
            s.turn("confirm_advance", "ok, no thanks, let's finish")
            self.assertEqual(s.view()["state"], "SYNTHESIS")
            self.assertEqual(s.view()["revisit_offer"][0]["part_id"], "q1")
            s.say("That is everything for today. Do you want to go back to Question 1 before we stop?")
            out = s.end("Big picture text.")
            self.assertTrue(out["ok"])
            self.assertEqual([f.code for f in audit(s.log.load(), s.packet)], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails, then passes**

Run: `python -m pytest tests/agent/tutor/test_tutor_regression_skip.py -q`
Expected before this task's doc edits: it should already PASS if Tasks 1-7 are right (this test only composes them). If it fails, the failure is a Task 1-7 defect: fix it there with a covering test, not here.

- [ ] **Step 3: Edit `agent/tutor/bootstrap_prompt.md`**

(a) In "Every turn", add `revisit` to the intent list and add the flags `--skip` and `--part`. (b) Insert before "## Manual overrides":

```markdown
## Skipping, coming back, and pausing
- If the student asks to skip or move on while a part is open, run `turn --skip` (and the intent that fits). The first
  time, reply with ONE question that invites them to try a first step: do not agree, do not move on, do not mention
  the next question. If they ask again, the part is parked and the brief shows the next question's `launch_text`;
  you may put ONE short sentence (max 20 words, no question, no content) before it saying the earlier question can be
  revisited.
- At the check-in after the next completed part, the brief lists `revisit_offer`. Your check-in must also offer to go
  back to those parts (name them) without naming the next question. If the student wants to go back, run
  `turn --intent revisit --part <part_id> --stdin`; if they want to move on, `confirm_advance`.
- Never bring up a parked part while another part is being worked.
- When every part has been visited and parked parts remain, the closing message must offer them once more; then run
  `end`. `end` refuses until that offer was said.
- To stop for now, run `pause` (or `end --partial`). `start` resumes a paused session; `start --fresh` abandons it.
```

(c) In "Finishing a part" nothing changes. Update the sentence "After the last part is closed and the student confirms, run `end`" to "After every part is closed or parked and the student confirms (or declines the last offer), run `end`".

- [ ] **Step 4: Edit `agent/tutor/README.md`**

Replace the "Plan B ... are not built yet." sentence with a pointer to `docs/superpowers/plans/2026-10-09-socratic-tutor-v1-1-plan-b.md`; add rows to the commands table: `turn ... [--skip] [--part P]`, `pause`, `start [--fresh]`, `end [--partial]`; update the vault-output line to profile `schema_version` 2 and the "Known limits" bullet "Not yet built (Plan B)" to a bullet: "The 8-word real-attempt threshold, the 20-word acknowledgement and the 60-word question cap are guesses to tune from live runs."

- [ ] **Step 5: Append the status-doc section and run the full suite**

Append to `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md` a "v1.1 Plan B (skip / defer / revisit, pause, profile v2)" section: what landed, the rulings, and "live validation pending". Then run:

Run: `python -m pytest tests/agent/tutor -q`
Expected: all pass.

Run: `python -m tools.land_branch check --full` (from the worktree's `ai-sandbox/academic-rag-model/`, per the worktree workflow) 
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add agent/tutor/bootstrap_prompt.md agent/tutor/README.md docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md tests/agent/tutor/test_tutor_regression_skip.py
git commit -m "docs(tutor): Plan B contract, README, status and end-to-end skip regression"
```

---

## Self-review

**Spec coverage** (v1.1 spec → task):
- §4 states/events (`skip_request`, `part_status`, `revisit`, `paused`, `resumed`): the spec names a `skip_request` event; this plan folds it into the `student` event's `data.skip` (one event per message keeps the log and audit simpler). Ruling recorded below. `part_status`: Task 2. `revisit`: student `intent == "revisit"` + `data.revisit` (Tasks 1-2). `paused`/`resumed`: Tasks 1, 6.
- §5 commands (`pause`, `start --fresh`, `--skip`, brief fields `skip_requests`, `revisit_offer`): Tasks 2, 3, 6.
- §6 rules (skip nudge, check-in revisit offer, synthesis offer): Task 3.
- §8 counting, requests #1/#2, statuses, real attempt, offer timing, decline → one last offer, revisit restore, Proficient cap: Tasks 1-4.
- §9 ceiling extension, profile v2, `pause`/`start`: Tasks 4-6.
- §10 audit additions: Task 7.
- §11 testing (unit per behaviour, the trial 3 analogue): Tasks 1-8.

**Rulings baked into this plan (spec silent or ambiguous):**
1. `skip_request` is not a separate event; it is `data.skip` on the `student` event (replay-pure, one event per message).
2. A phrase hit counts as a skip only when the intent is not `attempt` (a real argument may say "then move on to the next step"); `--skip` always counts; the audit lists uncounted phrases.
3. The ending skip message is logged under the parked part (its claim words still count there) followed by a `part_status` event; the audit exempts that move.
4. `--admits-gap` turns are never a real attempt (a bare "I'm not sure where to begin" would otherwise reach 8 words).
5. The check-in offer names only the parked part(s); "move on" stays unnamed so the existing no-next-part rule is unchanged.
6. One short acknowledgement sentence (≤ 20 words, no question, no claim content) may precede the launch line after a skip, so the tutor can say "we can come back to this one".
7. `end` is gated on the closing message having offered the parked parts (`tutor_say` in `SYNTHESIS` with `data.offer`), so "one last offer" cannot be skipped by the agent.

**Placeholder scan:** no TBD/TODO steps; every code step carries its code.

**Type consistency:** `student_event` kwargs `skip/real_attempt/revisit`, `info` keys (`skip_count`, `skip_ended`, `part_status`, `had_real_attempt`, `revisited`), event `data` keys (`skip`, `real_attempt`, `revisit`, `revisit_part`, `skip_ended`), `fresh_index`, `offerable`, `status_of`, `attempt_records`, `final_status`, `_attempt_no`, `_mention`, `MAX_ACK_WORDS` are used with the same names in every task.
