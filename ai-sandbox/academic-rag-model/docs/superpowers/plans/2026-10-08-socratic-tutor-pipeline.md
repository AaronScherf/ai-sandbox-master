# Socratic Tutor Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agent/tutor/`, a local CLI that gates a live IDE agent (Antigravity) through a Socratic tutoring FSM, lints every tutor message, caps ratings by evidence, and persists sessions and a learner-gap profile into the vault.

**Architecture:** Stateless CLI: every command replays an append-only `events.jsonl` through a pure FSM, so there is no separate state file. Offline `prep` collects/validates a "packet" (statements, glossary, rubric, sealed hints/solution) that the live agent authors under lint. Rendering, profile and audit are pure functions over the event log.

**Tech Stack:** Python 3.13 stdlib only (argparse, json, re, hashlib, dataclasses, unittest-style tests run by pytest). Retrieval reuses `agent.rag.rag_agent.retrieve_passages` (Gemini query embedding, free tier) and `agent.rag.problem_set_parser.extract_question`.

**Spec:** `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md` (commit `d6e2e09`). Read it first; this plan implements its §3–§9. §10 is out of scope.

## Global Constraints

- No paid LLM calls anywhere in `agent/tutor/`. The only network call is the Gemini query embedding inside `retrieve_passages`, made only by `prep-collect` in `cli.py`. No other module may import `google.genai` or `rag_agent`.
- Python stdlib only for new code; no new dependencies.
- Chat-facing text uses Unicode math; full LaTeX lives only in vault markdown files (spec §4).
- Hint levels are 0–3; level 3 requires ≥2 logged failed attempts at level 2; the tutor can never raise the level (spec §3.3).
- Ratings are exactly `Mastered`, `Proficient`, `Developing / Needs Review`; axes are `conceptual`, `rigor`, `directness` (spec §5).
- Event log is append-only JSONL; the learner profile has a single writer (`Session.end`) and a `schema_version` field (spec §6, §10.2).
- Tests mirror the package: `tests/agent/tutor/test_tutor_<module>.py` (unique basenames; `tests/` has no `__init__.py`). Tests use `unittest.TestCase` + `tempfile` like `tests/agent/rag/test_session_log.py`, and never touch the live vault.
- All work happens in a dedicated worktree on branch `claude/socratic-tutor` (repo `CLAUDE.md` + `docs/WORKTREE_WORKFLOW.md`). Stage explicit paths only; never `git add -A` / `git add .`. Append the session's attribution trailer to every commit.
- Run Python with the main checkout's venv (worktrees have none). In every command block below:
  `$PY = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe"` and the working directory is `<worktree>\ai-sandbox\academic-rag-model`.

## Review Focus

Input classes the spec implies but no happy-path test covers; each has a pinning test in the task named in brackets.

1. **Math/quotes in student text passed on a Windows command line** (`$`, `"`, `\`, non-ASCII `≽`): the agent must be able to use `--text-file`, and UTF-8 must round-trip into the log and transcript. [Task 10]
2. **Student says "ready to move on" before `close-part`, or while still WORKING**: must fail with a clear error and log nothing, rather than silently advancing or silently skipping the rating. [Task 8]
3. **Benign tutor feedback must pass lint** ("Good, that holds. What does your definition say about the boundary?") so the gate does not train the agent to bypass it. [Task 4]
4. **Packet edited after validation** (human tweaks `sealed/solution.md`): `start` must refuse until `prep-submit` is re-run. [Task 5]
5. **Resuming mid-session after the CLI process exits** (stateless replay) and a **half-written last line in `events.jsonl`**: state must be identical after reload; corruption must raise an error naming the file and line. [Tasks 1, 8]

---

## File Structure

```
agent/tutor/
  __init__.py
  paths.py          # TutorPaths: where everything lives in the vault
  events.py         # Event dataclass + EventLog (append-only JSONL)
  fsm.py            # pure FSM: states, transitions, replay()
  ratings.py        # rating ceiling + close-part validation
  lint.py           # tutor-message lint + glossary lint
  packet.py         # Packet/Part, validation, sealed sections, hash marker
  prep.py           # collect() skeleton + submit() validation
  sample_packet.py  # valid 2-part fixture packet (tests + docs)
  render.py         # transcript.md + summary.md from events
  profile.py        # learner_profile.json/.md update + open gaps
  session.py        # Session: start/student/say/define/sealed/verdict/misconception/close_part/end
  audit.py          # audit(events, packet) -> findings
  cli.py            # argparse wiring, JSON stdout, bootstrap
  bootstrap_prompt.md
  README.md
tests/agent/tutor/
  test_tutor_events.py  test_tutor_fsm.py  test_tutor_ratings.py  test_tutor_lint.py
  test_tutor_packet.py  test_tutor_prep.py  test_tutor_render_profile.py
  test_tutor_session.py test_tutor_audit.py test_tutor_cli.py test_tutor_regression.py
```

Vault layout produced (all under `<hub>/academic_notes/<course>/tutoring/`): `learner_profile.json|md`, `<ps>/packet/…`, `<ps>/sessions/<YYYY-MM-DD-HHMM>/{events.jsonl,transcript.md,summary.md}`.

Event types in the log: `session_start`, `student`, `tutor_say`, `lint_reject`, `define`, `sealed`, `verdict`, `misconception`, `misconception_resolved`, `close_part`, `synthesis`, `session_end`. Every event stores `part` and `state` as they are *after* the event.

## Spec amendments decided while planning (applied in Task 12)

- A student may `confirm_advance` from `VERIFIED` as well as `AWAITING_ADVANCE` (student-initiated; the pacing rule is that only a student event advances). The part must be closed first.
- `say` allows a technique word the **student already used** at any hint level (spec §4 said "at level 2"); the word is blocked otherwise below level 3.
- Commands are flat: `prep-collect`, `prep-submit`, `start`, `student`, `say`, `define`, `sealed`, `verdict`, `misconception`, `close-part`, `end`, `audit`, `bootstrap`.
- `prior_gaps.md` is refreshed by `start` (the profile changes between sessions), not by `prep`.
- The "missing `say` coverage" audit check is implemented as a proxy: a student turn followed by another student turn (or session end) with no `tutor_say` in between.

---

### Task 0: Worktree and baseline

**Files:** none (environment only)

- [ ] **Step 1: Create the worktree from the repo root**

```powershell
Set-Location C:\Users\theaa\ai-sandbox-master
git status --short
git worktree list
git check-ignore .worktrees/probe
$taskBase = git rev-parse main
git worktree add -b claude/socratic-tutor .worktrees/claude-socratic-tutor $taskBase
```

Expected: `git check-ignore` prints `.worktrees/probe`; worktree added. Open the IDE/agent session in `.worktrees\claude-socratic-tutor`.

- [ ] **Step 2: Confirm location and baseline**

```powershell
Set-Location C:\Users\theaa\ai-sandbox-master\.worktrees\claude-socratic-tutor\ai-sandbox\academic-rag-model
git rev-parse --show-toplevel
git branch --show-current
$PY = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe"
& $PY -m pytest tests/agent/rag/test_session_log.py -q
```

Expected: toplevel is the worktree, branch `claude/socratic-tutor`, existing tests pass.

---

### Task 1: Paths and event log

**Files:**
- Create: `agent/tutor/__init__.py` (empty), `agent/tutor/paths.py`, `agent/tutor/events.py`
- Test: `tests/agent/tutor/test_tutor_events.py`

**Interfaces:**
- Produces: `TutorPaths(hub_root, course, problem_set)` with properties `tutoring_dir`, `problem_set_dir`, `packet_dir`, `sessions_dir`, `profile_json`, `profile_md`.
- Produces: `Event(id, ts, type, part=None, state=None, hint_level=0, intent=None, text=None, data={})`; `EventLog(path)` with `.load() -> list[Event]` (raises `ValueError` naming path and line on corruption) and `.append(type, **fields) -> Event`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_events.py
import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.paths import TutorPaths


class TestTutorPaths(unittest.TestCase):
    def test_layout(self):
        p = TutorPaths("/hub", "microecon", "homework_4")
        norm = lambda s: s.replace("\\", "/")
        self.assertEqual(norm(p.tutoring_dir), "/hub/academic_notes/microecon/tutoring")
        self.assertEqual(norm(p.packet_dir), "/hub/academic_notes/microecon/tutoring/homework_4/packet")
        self.assertEqual(norm(p.sessions_dir), "/hub/academic_notes/microecon/tutoring/homework_4/sessions")
        self.assertEqual(norm(p.profile_json), "/hub/academic_notes/microecon/tutoring/learner_profile.json")
        self.assertEqual(norm(p.profile_md), "/hub/academic_notes/microecon/tutoring/learner_profile.md")


class TestEventLog(unittest.TestCase):
    def test_missing_file_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(EventLog(os.path.join(tmp, "e.jsonl")).load(), [])

    def test_append_assigns_sequential_ids_and_round_trips_unicode(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = EventLog(os.path.join(tmp, "sub", "e.jsonl"))
            a = log.append("student", part="q1", state="WORKING", hint_level=1, intent="attempt", text="x ≽ y, \"quoted\" $a$")
            b = log.append("tutor_say", part="q1", state="WORKING", text="ok", data={"k": 1})
            self.assertEqual((a.id, b.id), (1, 2))
            loaded = log.load()
            self.assertEqual(loaded[0].text, "x ≽ y, \"quoted\" $a$")
            self.assertEqual(loaded[1].data, {"k": 1})
            self.assertEqual(loaded[0].hint_level, 1)

    def test_corrupt_line_raises_with_path_and_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "e.jsonl")
            log = EventLog(path)
            log.append("student", text="a")
            with open(path, "a", encoding="utf-8") as f:
                f.write('{"id": 2, "ts": "t", "ty')  # half-written crash
            with self.assertRaises(ValueError) as ctx:
                log.load()
            self.assertIn("line 2", str(ctx.exception))
            self.assertIn(path, str(ctx.exception))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_events.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.tutor'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/paths.py
"""paths.py -- where the Socratic tutor keeps everything in the vault
(spec: docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md §3.1, §6)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TutorPaths:
    hub_root: str
    course: str
    problem_set: str

    @property
    def tutoring_dir(self) -> str:
        return os.path.join(self.hub_root, "academic_notes", self.course, "tutoring")

    @property
    def problem_set_dir(self) -> str:
        return os.path.join(self.tutoring_dir, self.problem_set)

    @property
    def packet_dir(self) -> str:
        return os.path.join(self.problem_set_dir, "packet")

    @property
    def sessions_dir(self) -> str:
        return os.path.join(self.problem_set_dir, "sessions")

    @property
    def profile_json(self) -> str:
        return os.path.join(self.tutoring_dir, "learner_profile.json")

    @property
    def profile_md(self) -> str:
        return os.path.join(self.tutoring_dir, "learner_profile.md")
```

```python
# agent/tutor/events.py
"""events.py -- append-only JSONL session log; the source of truth for a
tutoring session (spec §6). Each event records the part and FSM state as
they are AFTER the event, so any log can be replayed through fsm.replay()."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Event:
    id: int
    ts: str
    type: str
    part: str | None = None
    state: str | None = None
    hint_level: int = 0
    intent: str | None = None
    text: str | None = None
    data: dict = field(default_factory=dict)


class EventLog:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[Event]:
        if not os.path.exists(self.path):
            return []
        events = []
        with open(self.path, "r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(Event(**json.loads(line)))
                except (json.JSONDecodeError, TypeError) as err:
                    raise ValueError(f"{self.path}: corrupt event on line {n}: {err}") from err
        return events

    def append(self, type: str, **fields) -> Event:
        events = self.load()
        next_id = max((e.id for e in events), default=0) + 1
        event = Event(
            id=next_id, ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            type=type, **fields,
        )
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event
```

Also create the empty `agent/tutor/__init__.py`.

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_events.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/__init__.py agent/tutor/paths.py agent/tutor/events.py tests/agent/tutor/test_tutor_events.py
git commit -m "feat(tutor): add vault paths and append-only event log"
```

---

### Task 2: Pure FSM

**Files:**
- Create: `agent/tutor/fsm.py`
- Test: `tests/agent/tutor/test_tutor_fsm.py`

**Interfaces:**
- Consumes: `agent.tutor.events.Event`.
- Produces: constants `LAUNCH, WORKING, VERIFIED, AWAITING_ADVANCE, SYNTHESIS, DONE`; `INTENTS`, `ASSESSMENTS`; `IllegalTransition(ValueError)`; frozen dataclass `FsmState(part_index=0, state=LAUNCH, hint_level=0, failed_at_level=0)`; `student_event(s, intent, n_parts) -> (FsmState, dict)` where dict has `hint_capped: bool`; `verdict_event(s, assessment) -> FsmState`; `checkin_event(s) -> FsmState`; `finish_event(s) -> FsmState`; `replay(events, n_parts) -> FsmState`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_fsm.py
import unittest

from agent.tutor.events import Event
from agent.tutor.fsm import (
    AWAITING_ADVANCE, DONE, LAUNCH, SYNTHESIS, VERIFIED, WORKING,
    FsmState, IllegalTransition, checkin_event, finish_event, replay, student_event, verdict_event,
)


def S(**kw):
    return FsmState(**kw)


class TestStudentEvents(unittest.TestCase):
    def test_first_attempt_moves_launch_to_working(self):
        s, info = student_event(S(), "attempt", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 0))

    def test_define_request_never_changes_state_or_hint_level(self):
        s, _ = student_event(S(state=WORKING, hint_level=2), "define_request", 2)
        self.assertEqual((s.state, s.hint_level), (WORKING, 2))
        s, _ = student_event(S(), "define_request", 2)
        self.assertEqual(s.state, LAUNCH)

    def test_stuck_raises_hint_one_level_at_a_time(self):
        s, _ = student_event(S(state=WORKING), "stuck", 2)
        self.assertEqual(s.hint_level, 1)
        s, _ = student_event(s, "hint_request", 2)
        self.assertEqual(s.hint_level, 2)

    def test_level_three_requires_two_failed_attempts_at_level_two(self):
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=1), "stuck", 2)
        self.assertEqual(s.hint_level, 2)
        self.assertTrue(info["hint_capped"])
        s, info = student_event(S(state=WORKING, hint_level=2, failed_at_level=2), "stuck", 2)
        self.assertEqual(s.hint_level, 3)
        self.assertFalse(info["hint_capped"])

    def test_attempt_alone_never_raises_hint_level(self):
        s, _ = student_event(S(state=WORKING, hint_level=1), "attempt", 2)
        self.assertEqual(s.hint_level, 1)

    def test_confirm_advance_illegal_while_working_or_launch(self):
        for st in (LAUNCH, WORKING):
            with self.assertRaises(IllegalTransition):
                student_event(S(state=st), "confirm_advance", 2)

    def test_confirm_advance_from_awaiting_goes_to_next_part_launch_and_resets_hints(self):
        s, _ = student_event(S(part_index=0, state=AWAITING_ADVANCE, hint_level=2, failed_at_level=1), "confirm_advance", 2)
        self.assertEqual(s, FsmState(part_index=1, state=LAUNCH, hint_level=0, failed_at_level=0))

    def test_confirm_advance_from_verified_is_allowed(self):
        s, _ = student_event(S(state=VERIFIED), "confirm_advance", 2)
        self.assertEqual(s.part_index, 1)

    def test_confirm_on_last_part_goes_to_synthesis(self):
        s, _ = student_event(S(part_index=1, state=AWAITING_ADVANCE), "confirm_advance", 2)
        self.assertEqual((s.part_index, s.state), (1, SYNTHESIS))

    def test_questions_after_verification_return_to_working_same_part(self):
        s, _ = student_event(S(state=AWAITING_ADVANCE), "has_questions", 2)
        self.assertEqual((s.part_index, s.state), (0, WORKING))

    def test_unknown_intent_and_done_state_rejected(self):
        with self.assertRaises(IllegalTransition):
            student_event(S(), "dance", 2)
        with self.assertRaises(IllegalTransition):
            student_event(S(state=DONE), "attempt", 2)


class TestTutorSideEvents(unittest.TestCase):
    def test_verdict_correct_verifies_and_other_verdicts_count_failures(self):
        s = verdict_event(S(state=WORKING), "off_track")
        self.assertEqual((s.state, s.failed_at_level), (WORKING, 1))
        s = verdict_event(s, "correct")
        self.assertEqual(s.state, VERIFIED)

    def test_verdict_only_while_working(self):
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=LAUNCH), "correct")
        with self.assertRaises(IllegalTransition):
            verdict_event(S(state=WORKING), "great")

    def test_checkin_only_moves_verified(self):
        self.assertEqual(checkin_event(S(state=VERIFIED)).state, AWAITING_ADVANCE)
        self.assertEqual(checkin_event(S(state=WORKING)).state, WORKING)

    def test_finish_requires_synthesis(self):
        self.assertEqual(finish_event(S(state=SYNTHESIS)).state, DONE)
        with self.assertRaises(IllegalTransition):
            finish_event(S(state=WORKING))


class TestReplay(unittest.TestCase):
    def test_replay_reproduces_state(self):
        ev = lambda i, t, **kw: Event(id=i, ts="t", type=t, **kw)
        events = [
            ev(1, "session_start"),
            ev(2, "student", intent="attempt"),
            ev(3, "verdict", data={"assessment": "correct"}),
            ev(4, "tutor_say", data={"checkin": True}),
            ev(5, "student", intent="confirm_advance"),
        ]
        s = replay(events, 2)
        self.assertEqual((s.part_index, s.state), (1, LAUNCH))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_fsm.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.fsm`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/fsm.py
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_fsm.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/fsm.py tests/agent/tutor/test_tutor_fsm.py
git commit -m "feat(tutor): pure Socratic FSM with hint-level gating"
```

---

### Task 3: Rating ceiling and close-part validation

**Files:**
- Create: `agent/tutor/ratings.py`
- Test: `tests/agent/tutor/test_tutor_ratings.py`

**Interfaces:**
- Consumes: `Event` (events of ONE part).
- Produces: `AXES = ("conceptual","rigor","directness")`; `RATINGS = ("Developing / Needs Review","Proficient","Mastered")` (ascending); `RatingRejected(ValueError)`; `ceiling(part_events, axis) -> (rating, reasons: list[str])`; `validate_close_part(ratings, part_events) -> None` where `ratings = {axis: {"rating": str, "evidence": [int | str, ...]}}`.
- Event conventions: `misconception` events carry `data={"tag", "axis"}` (axis `"all"` default); `misconception_resolved` carry `data={"tag"}`; `student` events may carry `data={"admits_gap": True, "gap_axis": "all"|axis}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_ratings.py
import unittest

from agent.tutor.events import Event
from agent.tutor.ratings import RatingRejected, ceiling, validate_close_part

DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def ev(i, type, hint=0, text=None, **data):
    return Event(id=i, ts="t", type=type, part="q1", hint_level=hint, text=text, intent=data.pop("intent", None), data=data)


class TestCeiling(unittest.TestCase):
    def test_clean_part_can_be_mastered(self):
        events = [ev(1, "student", text="my answer", intent="attempt")]
        self.assertEqual(ceiling(events, "rigor")[0], MAST)

    def test_hint_level_one_caps_at_proficient(self):
        events = [ev(1, "student", hint=1, text="a", intent="stuck")]
        self.assertEqual(ceiling(events, "rigor")[0], PROF)

    def test_hint_level_two_caps_at_developing(self):
        events = [ev(1, "student", hint=2, text="a", intent="stuck")]
        rating, reasons = ceiling(events, "rigor")
        self.assertEqual(rating, DEV)
        self.assertTrue(any("hint level" in r for r in reasons))

    def test_unresolved_misconception_caps_at_developing(self):
        events = [ev(1, "student", text="a", intent="attempt"), ev(2, "misconception", tag="closed-implies-bounded")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)

    def test_resolved_misconception_caps_at_proficient_not_mastered(self):
        events = [
            ev(1, "misconception", tag="t"),
            ev(2, "misconception_resolved", tag="t"),
        ]
        self.assertEqual(ceiling(events, "conceptual")[0], PROF)

    def test_axis_scoped_misconception_only_caps_that_axis(self):
        events = [ev(1, "misconception", tag="t", axis="rigor")]
        self.assertEqual(ceiling(events, "rigor")[0], DEV)
        self.assertEqual(ceiling(events, "conceptual")[0], MAST)

    def test_student_admitted_gap_caps_axis(self):
        events = [ev(1, "student", text="I don't understand concavity", intent="other", admits_gap=True, gap_axis="conceptual")]
        self.assertEqual(ceiling(events, "conceptual")[0], DEV)
        self.assertEqual(ceiling(events, "rigor")[0], MAST)


class TestValidateClosePart(unittest.TestCase):
    def _events(self):
        return [
            ev(1, "student", hint=2, text="a closed set must be bounded", intent="attempt"),
            ev(2, "misconception", hint=2, tag="closed-implies-bounded"),
        ]

    def _ratings(self, rating, evidence=(2,)):
        return {a: {"rating": rating, "evidence": list(evidence)} for a in ("conceptual", "rigor", "directness")}

    def test_rating_above_ceiling_rejected_with_reason(self):
        with self.assertRaises(RatingRejected) as ctx:
            validate_close_part(self._ratings(PROF), self._events())
        self.assertIn("ceiling", str(ctx.exception))
        self.assertIn("Developing", str(ctx.exception))

    def test_rating_at_ceiling_with_evidence_accepted(self):
        validate_close_part(self._ratings(DEV), self._events())

    def test_missing_axis_empty_evidence_and_bad_rating_rejected(self):
        events = self._events()
        r = self._ratings(DEV)
        del r["rigor"]
        with self.assertRaises(RatingRejected):
            validate_close_part(r, events)
        r = self._ratings(DEV, evidence=())
        with self.assertRaises(RatingRejected):
            validate_close_part(r, events)
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings("Excellent"), events)

    def test_evidence_must_reference_real_event_ids_or_student_quotes(self):
        events = self._events()
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings(DEV, evidence=(99,)), events)
        validate_close_part(self._ratings(DEV, evidence=("closed set must be  bounded",)), events)  # whitespace-normalized quote
        with self.assertRaises(RatingRejected):
            validate_close_part(self._ratings(DEV, evidence=("the student said something never said",)), events)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_ratings.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.ratings`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/ratings.py
"""ratings.py -- evidence-capped tri-axial rating (spec §5). The agent
PROPOSES ratings; this module computes the highest rating the event log
supports and rejects anything above it, which is the anti-inflation
mechanism for the HW4 'everything is Proficient' failure."""
from __future__ import annotations

from agent.tutor.events import Event

AXES = ("conceptual", "rigor", "directness")
RATINGS = ("Developing / Needs Review", "Proficient", "Mastered")  # ascending


class RatingRejected(ValueError):
    pass


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def ceiling(part_events: list[Event], axis: str) -> tuple[str, list[str]]:
    applies = lambda e, key: e.data.get(key, "all") in (axis, "all")
    max_hint = max((e.hint_level for e in part_events), default=0)
    miscs = [e for e in part_events if e.type == "misconception" and applies(e, "axis")]
    resolved_tags = {e.data["tag"] for e in part_events if e.type == "misconception_resolved"}
    unresolved = [e for e in miscs if e.data["tag"] not in resolved_tags]
    gaps = [e for e in part_events if e.type == "student" and e.data.get("admits_gap") and applies(e, "gap_axis")]

    reasons = []
    if max_hint >= 2:
        reasons.append(f"hint level reached {max_hint}")
    if unresolved:
        reasons.append("unresolved misconception(s): " + ", ".join(sorted({e.data['tag'] for e in unresolved})))
    if gaps:
        reasons.append("student stated they did not understand")
    if reasons:
        return RATINGS[0], reasons
    if max_hint == 0 and not miscs:
        return RATINGS[2], []
    why = []
    if max_hint == 1:
        why.append("hint level reached 1")
    if miscs:
        why.append("a misconception occurred (resolved)")
    return RATINGS[1], why


def validate_close_part(ratings: dict, part_events: list[Event]) -> None:
    ids = {e.id for e in part_events}
    student_texts = [_norm(e.text) for e in part_events if e.type == "student"]
    for axis in AXES:
        entry = ratings.get(axis)
        if not isinstance(entry, dict) or "rating" not in entry:
            raise RatingRejected(f"missing rating for axis {axis!r}")
        rating = entry["rating"]
        if rating not in RATINGS:
            raise RatingRejected(f"axis {axis!r}: rating {rating!r} is not one of {list(RATINGS)}")
        evidence = entry.get("evidence") or []
        if not evidence:
            raise RatingRejected(f"axis {axis!r}: at least one evidence item (event id or student quote) is required")
        for item in evidence:
            if isinstance(item, int):
                if item not in ids:
                    raise RatingRejected(f"axis {axis!r}: evidence event id {item} is not an event of this part")
            elif isinstance(item, str):
                if not any(_norm(item) in t for t in student_texts):
                    raise RatingRejected(f"axis {axis!r}: evidence quote not found in this part's student messages")
            else:
                raise RatingRejected(f"axis {axis!r}: evidence items must be event ids or quote strings")
        cap, reasons = ceiling(part_events, axis)
        if RATINGS.index(rating) > RATINGS.index(cap):
            raise RatingRejected(
                f"axis {axis!r}: rating {rating!r} exceeds the evidence-based ceiling {cap!r} "
                f"({'; '.join(reasons) or 'no concerns logged'}). Rate at or below the ceiling."
            )
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_ratings.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/ratings.py tests/agent/tutor/test_tutor_ratings.py
git commit -m "feat(tutor): evidence-capped tri-axial rating validation"
```

---

### Task 4: Message lint and glossary lint

**Files:**
- Create: `agent/tutor/lint.py`
- Test: `tests/agent/tutor/test_tutor_lint.py`

**Interfaces:**
- Consumes: state constants from `agent.tutor.fsm`.
- Produces: `Violation(code, detail)` frozen dataclass with `.to_dict()`; `extract_symbols(statement) -> set[str]`; `symbol_hits(text, symbols) -> list[str]`; `lint_message(text, *, state, hint_level, student_text="", statement="", sealed_solution="", allowed_exact=(), after_define=False, forbidden_patterns=()) -> list[Violation]`; `lint_glossary(glossary: dict[str,str], statements: list[str]) -> list[Violation]`.
- Violation codes: `LAUNCH_NOT_VERBATIM`, `TECHNIQUE`, `NOTATION_BRIDGE`, `SEALED_OVERLAP`, `SUBQUESTION_LIST`, `NEXT_PART_REFERENCE`, `CHECKIN_MISSING`, `LATEX_IN_CHAT`, `GLOSSARY_NOTATION`, `GLOSSARY_BACKREF`.
- A draft whose whitespace-normalized text equals an `allowed_exact` entry (launch text, a glossary definition) returns `[]` immediately.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_lint.py
import unittest

from agent.tutor.lint import extract_symbols, lint_glossary, lint_message, symbol_hits

STATEMENT = "Choice overload suggests a consumer may walk away. Let $d$ be the default and $p(d, A)$ the probability of $\\Gamma$."
SOLUTION = "The probability of walking away equals one minus the total probability of choosing any listed alternative from the set."


def codes(violations):
    return {v.code for v in violations}


def lint(text, **kw):
    base = dict(state="WORKING", hint_level=0)
    base.update(kw)
    return lint_message(text, **base)


class TestSymbols(unittest.TestCase):
    def test_extract_symbols(self):
        self.assertEqual(extract_symbols(STATEMENT), {"d", "p", "\\Gamma"})

    def test_symbol_hits(self):
        self.assertEqual(symbol_hits("so d is chosen", {"d", "p"}), ["d"])
        self.assertEqual(symbol_hits("a standard result", {"d", "p"}), [])  # no match inside words
        self.assertEqual(symbol_hits("the Γ set", {"\\Gamma"}), ["\\Gamma"])  # unicode form of a latex command


class TestLintMessage(unittest.TestCase):
    def test_benign_feedback_passes(self):
        self.assertEqual(lint("Good, that holds. What does your definition say about the boundary?"), [])

    def test_launch_requires_verbatim_text(self):
        launch = "Question 1. Do the thing.\n\nHow would you like to approach this problem?"
        self.assertEqual(lint(launch, state="LAUNCH", allowed_exact=[launch]), [])
        self.assertEqual(lint(launch.replace("\n\n", "  "), state="LAUNCH", allowed_exact=[launch]), [])  # whitespace-insensitive
        v = lint(launch + " Assume the first option is better.", state="LAUNCH", allowed_exact=[launch])
        self.assertIn("LAUNCH_NOT_VERBATIM", codes(v))

    def test_technique_blocked_unless_student_named_it_or_level_three(self):
        draft = "Suppose, for the sake of contradiction, that f is concave."
        self.assertIn("TECHNIQUE", codes(lint(draft)))
        self.assertIn("TECHNIQUE", codes(lint(draft, hint_level=2)))
        self.assertEqual(codes(lint(draft, hint_level=3)) & {"TECHNIQUE"}, set())
        self.assertEqual(codes(lint(draft, student_text="maybe I can use contradiction")) & {"TECHNIQUE"}, set())

    def test_notation_bridge_after_define(self):
        v = lint("Choice overload raises the chance of d.", statement=STATEMENT, after_define=True)
        self.assertIn("NOTATION_BRIDGE", codes(v))
        ok = lint("Choice overload is when many options make a person less likely to choose anything.", statement=STATEMENT, after_define=True)
        self.assertEqual(ok, [])

    def test_sealed_overlap(self):
        draft = "Notice it equals one minus the total probability of choosing any item."
        self.assertIn("SEALED_OVERLAP", codes(lint(draft, sealed_solution=SOLUTION)))
        self.assertEqual(lint("What does the probability of walking away depend on?", sealed_solution=SOLUTION), [])

    def test_leading_subquestion_list_blocked_while_working(self):
        draft = "Consider:\n1. What happens when x is negative?\n2. What happens when x is positive?"
        self.assertIn("SUBQUESTION_LIST", codes(lint(draft)))
        self.assertEqual(codes(lint(draft, hint_level=3)) & {"SUBQUESTION_LIST"}, set())

    def test_verified_requires_checkin_and_forbids_next_part(self):
        v = lint("Correct.", state="VERIFIED")
        self.assertIn("CHECKIN_MISSING", codes(v))
        ok = lint("Correct. Do you have any lingering questions, or are you ready to move on?", state="VERIFIED")
        self.assertEqual(ok, [])
        bad = lint("Correct. Ready for Question 2?", state="VERIFIED", forbidden_patterns=[r"\bQuestion 2\b"])
        self.assertIn("NEXT_PART_REFERENCE", codes(bad))

    def test_latex_in_chat_blocked(self):
        self.assertIn("LATEX_IN_CHAT", codes(lint("Is $x \\succeq y$ transitive?")))
        self.assertEqual(lint("Is x ≽ y transitive?"), [])


class TestLintGlossary(unittest.TestCase):
    def test_definition_using_problem_notation_rejected(self):
        v = lint_glossary({"choice overload": "Choice overload means d is chosen more often."}, [STATEMENT])
        self.assertEqual(codes(v), {"GLOSSARY_NOTATION"})

    def test_backreference_rejected(self):
        v = lint_glossary({"choice overload": "See part 1 for how this works."}, [STATEMENT])
        self.assertEqual(codes(v), {"GLOSSARY_BACKREF"})

    def test_clean_definition_and_unrelated_term_pass(self):
        g = {"choice overload": "A finding that many options can make people choose nothing.", "lattice": "A poset with joins and meets."}
        self.assertEqual(lint_glossary(g, [STATEMENT]), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_lint.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.lint`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/lint.py
"""lint.py -- conservative lexical checks on a tutor draft before it is sent
(spec §4) and on glossary definitions at prep time (spec §3.1). A false
positive costs one revision; a false negative costs a leak, so rules lean
strict. Cannot catch paraphrased strategy hints (spec §11)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.fsm import LAUNCH, VERIFIED, WORKING


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "detail": self.detail}


TECHNIQUES = {
    "contradiction": re.compile(r"contradiction|reductio|for the sake of", re.I),
    "contrapositive": re.compile(r"contraposit", re.I),
    "induction": re.compile(r"\binduct(?:ion|ive)\b", re.I),
    "construction": re.compile(r"\bconstruct(?:ion|ive)?\b|counterexample", re.I),
}
_MATH = re.compile(r"\$([^$]+)\$")
_LATEX_CMD = re.compile(r"\\[A-Za-z]+")
_GREEK = re.compile(r"[α-ωΑ-Ω]")
_LETTER = re.compile(r"(?<![A-Za-z\\])[A-Za-z](?![A-Za-z])")
_COMMON_LETTERS = {"a", "A", "I"}
_UNICODE_FOR_LATEX = {
    "\\succeq": "≽", "\\succ": "≻", "\\preceq": "≼", "\\prec": "≺", "\\in": "∈", "\\cup": "∪", "\\cap": "∩",
    "\\gamma": "γ", "\\Gamma": "Γ", "\\lambda": "λ", "\\Lambda": "Λ", "\\mu": "μ", "\\sigma": "σ",
    "\\epsilon": "ε", "\\delta": "δ", "\\Delta": "Δ", "\\alpha": "α", "\\beta": "β", "\\theta": "θ",
}
_SUBQ_LINE = re.compile(r"^\s*(?:\d+[.)]|[A-Za-z][.)]|[-*•])\s+.*\?\s*$", re.M)
_LATEX_IN_CHAT = re.compile(r"\$|\\\(|\\\[|\\[A-Za-z]{2,}")
_CHECKIN = re.compile(r"lingering|any questions|ready to move on|move on", re.I)
_BACKREF = re.compile(r"\b(?:part|question|problem)\s+\d", re.I)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def extract_symbols(statement: str) -> set[str]:
    symbols: set[str] = set()
    for math in _MATH.findall(statement):
        symbols.update(_LATEX_CMD.findall(math))
        symbols.update(_GREEK.findall(math))
        symbols.update(l for l in _LETTER.findall(math) if l not in _COMMON_LETTERS)
    symbols.update(_GREEK.findall(statement))
    return symbols


def symbol_hits(text: str, symbols: set[str]) -> list[str]:
    hits = []
    for sym in sorted(symbols):
        if sym.startswith("\\"):
            if sym in text or _UNICODE_FOR_LATEX.get(sym, "\0") in text:
                hits.append(sym)
        elif len(sym) > 1 or not sym.isascii():
            if sym in text:
                hits.append(sym)
        elif re.search(rf"(?<![A-Za-z]){re.escape(sym)}(?![A-Za-z])", text):
            hits.append(sym)
    return hits


def _ngrams(text: str, n: int = 6) -> set[tuple]:
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def lint_message(
    text: str, *, state: str, hint_level: int, student_text: str = "", statement: str = "",
    sealed_solution: str = "", allowed_exact=(), after_define: bool = False, forbidden_patterns=(),
) -> list[Violation]:
    if _normalize(text) in {_normalize(a) for a in allowed_exact}:
        return []
    found: list[Violation] = []
    if state == LAUNCH:
        found.append(Violation("LAUNCH_NOT_VERBATIM", "In LAUNCH send exactly the launch text, nothing added or changed."))
    if hint_level < 3:
        for name, rx in TECHNIQUES.items():
            if rx.search(text) and not rx.search(student_text):
                found.append(Violation("TECHNIQUE", f"names the proof technique '{name}' before the student did"))
    if after_define:
        hits = symbol_hits(text, extract_symbols(statement))
        if hits:
            found.append(Violation("NOTATION_BRIDGE", f"a definition answer must not use the problem's notation: {hits}"))
    if sealed_solution and len(_ngrams(text) & _ngrams(sealed_solution)) >= 2:
        found.append(Violation("SEALED_OVERLAP", "draft repeats a phrase from the sealed solution"))
    if state == WORKING and hint_level < 3 and len(_SUBQ_LINE.findall(text)) >= 2:
        found.append(Violation("SUBQUESTION_LIST", "leading sub-question list before the student proposed a plan"))
    if state == VERIFIED and not (_CHECKIN.search(text) and "?" in text):
        found.append(Violation("CHECKIN_MISSING", "ask whether they have lingering questions or are ready to move on"))
    for pattern in forbidden_patterns:
        if re.search(pattern, text, re.I):
            found.append(Violation("NEXT_PART_REFERENCE", "do not mention the next part before the student confirms advancing"))
            break
    if _LATEX_IN_CHAT.search(text):
        found.append(Violation("LATEX_IN_CHAT", "use Unicode math (≽, ≤, λ, ℝ) in chat; keep LaTeX for vault files"))
    return found


def lint_glossary(glossary: dict[str, str], statements: list[str]) -> list[Violation]:
    found: list[Violation] = []
    for term, definition in glossary.items():
        if _BACKREF.search(definition):
            found.append(Violation("GLOSSARY_BACKREF", f"{term!r}: definition refers to a part/question number"))
        for statement in statements:
            if term.lower() in statement.lower():
                hits = symbol_hits(definition, extract_symbols(statement))
                if hits:
                    found.append(Violation("GLOSSARY_NOTATION", f"{term!r}: definition uses the problem's notation {hits}"))
                    break
    return found
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_lint.py -q`
Expected: all passed. If `test_extract_symbols` fails on `p`, check `_LETTER` handling of `p(d, A)`.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/lint.py tests/agent/tutor/test_tutor_lint.py
git commit -m "feat(tutor): message and glossary lint"
```

---

### Task 5: Packet model, validation, hash marker, sample fixture

**Files:**
- Create: `agent/tutor/packet.py`, `agent/tutor/sample_packet.py`
- Test: `tests/agent/tutor/test_tutor_packet.py`

**Interfaces:**
- Consumes: `TutorPaths`, `ratings.AXES/RATINGS`, `lint.lint_glossary`.
- Produces: `PacketError(ValueError)`; `LAUNCH_SUFFIX`; `Part(part_id, statement, concept_tags, expected_evidence, label=None, chat_statement=None)` with `.launch_text()`; `Packet(course, problem_set, parts, glossary, rubric)`; `sealed_section(markdown, part_id) -> str | None`; `validate_packet(packet_dir) -> list[str]`; `compute_hash(packet_dir) -> str`; `write_validated(packet_dir)`; `is_validated(packet_dir) -> bool`; `load_packet(paths) -> Packet` (raises `PacketError` unless validated); `read_sealed(packet_dir) -> (hints_md, solution_md)`.
- Packet files in `packet_dir`: `parts.json`, `glossary.json`, `rubric.json`, `grounding.md`, `sealed/hints.md`, `sealed/solution.md` (each with `## <part_id>` sections), `validated.json`.
- `sample_packet.write_sample_packet(paths) -> None` writes a valid 2-part packet (`q1`, `q2`) and the validated marker.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_packet.py
import json
import os
import tempfile
import unittest

from agent.tutor.packet import (
    LAUNCH_SUFFIX, PacketError, is_validated, load_packet, sealed_section, validate_packet, write_validated,
)
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet


def _paths(tmp):
    return TutorPaths(tmp, "microecon", "homework_4")


class TestSealedSection(unittest.TestCase):
    def test_extracts_section_by_part_id(self):
        md = "## q1\nfirst\nmore\n## q2\nsecond\n"
        self.assertEqual(sealed_section(md, "q1"), "first\nmore")
        self.assertEqual(sealed_section(md, "q2"), "second")
        self.assertIsNone(sealed_section(md, "q3"))

    def test_part_id_with_regex_characters(self):
        self.assertEqual(sealed_section("## q1.2\nbody", "q1.2"), "body")
        self.assertIsNone(sealed_section("## q1x2\nbody", "q1.2"))


class TestSamplePacket(unittest.TestCase):
    def test_sample_is_valid_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertEqual(validate_packet(paths.packet_dir), [])
            packet = load_packet(paths)
            self.assertEqual([p.part_id for p in packet.parts], ["q1", "q2"])
            self.assertTrue(packet.parts[0].launch_text().endswith(LAUNCH_SUFFIX))


class TestValidation(unittest.TestCase):
    def _edit_json(self, paths, name, fn):
        path = os.path.join(paths.packet_dir, name)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        fn(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_reports_each_kind_of_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self._edit_json(paths, "parts.json", lambda d: d[0].update(concept_tags=[], expected_evidence=[]))
            self._edit_json(paths, "rubric.json", lambda d: d["q2"]["rigor"].pop("Mastered"))
            self._edit_json(paths, "glossary.json", lambda d: d.update({"choice overload": "Means d is chosen more."}))
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "w", encoding="utf-8") as f:
                f.write("## q1\nonly q1\n")
            errors = "\n".join(validate_packet(paths.packet_dir))
            self.assertIn("q1: concept_tags", errors)
            self.assertIn("q1: expected_evidence", errors)
            self.assertIn("rubric q2.rigor missing 'Mastered'", errors)
            self.assertIn("GLOSSARY_NOTATION", errors)
            self.assertIn("sealed/solution.md has no '## q2' section", errors)

    def test_missing_files_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(_paths(tmp).packet_dir)
            self.assertIn("parts.json missing", validate_packet(_paths(tmp).packet_dir))


class TestValidatedMarker(unittest.TestCase):
    def test_edit_after_validation_invalidates_until_resubmitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertTrue(is_validated(paths.packet_dir))
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "a", encoding="utf-8") as f:
                f.write("\nhuman tweak\n")
            self.assertFalse(is_validated(paths.packet_dir))
            with self.assertRaises(PacketError) as ctx:
                load_packet(paths)
            self.assertIn("prep-submit", str(ctx.exception))
            write_validated(paths.packet_dir)
            load_packet(paths)

    def test_crlf_conversion_does_not_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "rb") as f:
                raw = f.read()
            with open(sol, "wb") as f:
                f.write(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertTrue(is_validated(paths.packet_dir))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_packet.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.packet`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/packet.py
"""packet.py -- the contract between offline prep and the live session
(spec §3.1). Anything that produces a valid packet can drive a session."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass

from agent.tutor.lint import lint_glossary
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

LAUNCH_SUFFIX = "How would you like to approach this problem?"
_HASHED = ("parts.json", "glossary.json", "rubric.json", os.path.join("sealed", "hints.md"), os.path.join("sealed", "solution.md"))


class PacketError(ValueError):
    pass


@dataclass
class Part:
    part_id: str
    statement: str
    concept_tags: list[str]
    expected_evidence: list[str]
    label: str | None = None
    chat_statement: str | None = None

    def launch_text(self) -> str:
        return f"{(self.chat_statement or self.statement).strip()}\n\n{LAUNCH_SUFFIX}"


@dataclass
class Packet:
    course: str
    problem_set: str
    parts: list[Part]
    glossary: dict
    rubric: dict


def sealed_section(markdown: str, part_id: str) -> str | None:
    m = re.search(rf"^##\s+{re.escape(part_id)}\s*$", markdown, re.M)
    if not m:
        return None
    rest = markdown[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    return body.strip() or None


def _read(packet_dir: str, rel: str) -> str:
    with open(os.path.join(packet_dir, rel), "r", encoding="utf-8") as f:
        return f.read()


def _load_json(packet_dir: str, rel: str):
    return json.loads(_read(packet_dir, rel))


def validate_packet(packet_dir: str) -> list[str]:
    errors: list[str] = []
    for rel in _HASHED:
        if not os.path.exists(os.path.join(packet_dir, rel)):
            errors.append(f"{rel.replace(os.sep, '/')} missing")
    if errors:
        return errors
    try:
        parts = _load_json(packet_dir, "parts.json")
        glossary = _load_json(packet_dir, "glossary.json")
        rubric = _load_json(packet_dir, "rubric.json")
    except json.JSONDecodeError as err:
        return [f"invalid JSON: {err}"]
    if not isinstance(parts, list) or not parts:
        return ["parts.json must be a non-empty list"]
    ids = [p.get("part_id") for p in parts]
    if len(set(ids)) != len(ids) or not all(ids):
        errors.append("parts.json: part_id values must be present and unique")
    hints, solution = _read(packet_dir, os.path.join("sealed", "hints.md")), _read(packet_dir, os.path.join("sealed", "solution.md"))
    for p in parts:
        pid = p.get("part_id", "?")
        if not str(p.get("statement", "")).strip():
            errors.append(f"{pid}: statement is empty")
        if not p.get("concept_tags"):
            errors.append(f"{pid}: concept_tags must be non-empty")
        if not p.get("expected_evidence"):
            errors.append(f"{pid}: expected_evidence must be non-empty")
        for axis in AXES:
            for rating in RATINGS:
                if not str(rubric.get(pid, {}).get(axis, {}).get(rating, "")).strip():
                    errors.append(f"rubric {pid}.{axis} missing '{rating}'")
        for name, text in (("hints.md", hints), ("solution.md", solution)):
            if sealed_section(text, pid) is None:
                errors.append(f"sealed/{name} has no '## {pid}' section")
    if not isinstance(glossary, dict) or not glossary:
        errors.append("glossary.json must be a non-empty object")
    else:
        for v in lint_glossary(glossary, [p.get("statement", "") for p in parts]):
            errors.append(f"{v.code}: {v.detail}")
    return errors


def compute_hash(packet_dir: str) -> str:
    h = hashlib.sha256()
    for rel in _HASHED:
        with open(os.path.join(packet_dir, rel), "rb") as f:
            h.update(rel.encode())
            h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def write_validated(packet_dir: str) -> None:
    with open(os.path.join(packet_dir, "validated.json"), "w", encoding="utf-8") as f:
        json.dump({"sha256": compute_hash(packet_dir)}, f)


def is_validated(packet_dir: str) -> bool:
    marker = os.path.join(packet_dir, "validated.json")
    try:
        with open(marker, "r", encoding="utf-8") as f:
            return json.load(f)["sha256"] == compute_hash(packet_dir)
    except (OSError, KeyError, json.JSONDecodeError):
        return False


def load_packet(paths: TutorPaths) -> Packet:
    if not is_validated(paths.packet_dir):
        raise PacketError(
            f"packet at {paths.packet_dir} is missing or changed since validation; run prep-submit first"
        )
    parts = [Part(**p) for p in _load_json(paths.packet_dir, "parts.json")]
    return Packet(
        course=paths.course, problem_set=paths.problem_set, parts=parts,
        glossary=_load_json(paths.packet_dir, "glossary.json"), rubric=_load_json(paths.packet_dir, "rubric.json"),
    )


def read_sealed(packet_dir: str) -> tuple[str, str]:
    return _read(packet_dir, os.path.join("sealed", "hints.md")), _read(packet_dir, os.path.join("sealed", "solution.md"))
```

```python
# agent/tutor/sample_packet.py
"""sample_packet.py -- a small valid packet used by tests and docs. Not real course content."""
from __future__ import annotations

import json
import os

from agent.tutor.packet import write_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

Q1 = (
    "Question 1. Choice overload suggests a consumer may walk away without choosing. Let $d$ be the default "
    "alternative and let $p(d, A)$ denote the probability that she walks away from the set $A$. Express "
    "$p(d, A)$ in terms of the probabilities of choosing each element of $A$."
)
Q2 = (
    "Question 2. Let $\\succeq$ be a preference relation on $\\mathbb{R}$ that ranks every non-positive number "
    "below every positive number but reverses the usual order on each side. Show that no concave function "
    "represents $\\succeq$."
)
PARTS = [
    {"part_id": "q1", "label": "Question 1", "statement": Q1,
     "concept_tags": ["random-consideration-set", "default-alternative"],
     "expected_evidence": ["identifies p(d, A) as the complement of the choice probabilities"]},
    {"part_id": "q2", "label": "Question 2", "statement": Q2,
     "concept_tags": ["preference-topology", "concavity"],
     "expected_evidence": ["finds a violation of concave representability"]},
]
GLOSSARY = {
    "choice overload": "The empirical finding that facing many options can make a person less likely to choose anything at all.",
    "concave function": "A function whose value at any weighted average of two points is at least the weighted average of its values at those points.",
}
HINTS = "## q1\nThink about what the probabilities must sum to.\n\n## q2\nConsider how a concave function behaves on an interval.\n"
SOLUTION = (
    "## q1\nThe probability of walking away equals one minus the total probability of choosing any listed alternative from the set.\n\n"
    "## q2\nA concave function would have to be monotone across the break and also jump, which no concave function on the real line can do.\n"
)


def write_sample_packet(paths: TutorPaths) -> None:
    d = paths.packet_dir
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    rubric = {
        p["part_id"]: {a: {r: f"{p['part_id']} {a} {r} descriptor" for r in RATINGS} for a in AXES} for p in PARTS
    }
    for name, payload in (("parts.json", PARTS), ("glossary.json", GLOSSARY), ("rubric.json", rubric)):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    with open(os.path.join(d, "grounding.md"), "w", encoding="utf-8") as f:
        f.write("# Grounding (sample)\n")
    for name, text in (("hints.md", HINTS), ("solution.md", SOLUTION)):
        with open(os.path.join(d, "sealed", name), "w", encoding="utf-8") as f:
            f.write(text)
    write_validated(d)
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_packet.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/packet.py agent/tutor/sample_packet.py tests/agent/tutor/test_tutor_packet.py
git commit -m "feat(tutor): packet model, validation and validated-hash marker"
```

---

### Task 6: Prep (collect + submit)

**Files:**
- Create: `agent/tutor/prep.py`
- Test: `tests/agent/tutor/test_tutor_prep.py`

**Interfaces:**
- Consumes: `agent.rag.problem_set_parser.extract_question`, `packet.validate_packet/write_validated`, `TutorPaths`.
- Produces: `collect(paths, problem_set_file, question_refs, retrieve, hints_file=None, solutions_file=None, force=False) -> dict` where `retrieve: Callable[[str], list]` returns objects with `.citation`, `.path`, `.score`, `.text`; writes skeleton `parts.json` (part_id `q<ref>`, label `Question <ref>`, empty tags/evidence), `glossary.json` `{}`, `rubric.json` `{}`, `grounding.md`, `sealed/*.md`, `worklist.md`; raises `FileExistsError` if `parts.json` exists and `force` is false. `submit(paths) -> dict` returns `{"ok": True}` after writing the marker, or `{"ok": False, "errors": [...]}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_prep.py
import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from agent.tutor import prep
from agent.tutor.packet import is_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import GLOSSARY, HINTS, SOLUTION, write_sample_packet

PS = "## Question 1\nFirst question text with $d$.\n\n## Question 2\nSecond question text.\n"


def _retrieve(query):
    return [SimpleNamespace(citation="p. 3", path="notes/a.md", score=0.81, text="line one\nline two")]


class TestCollect(unittest.TestCase):
    def test_writes_skeleton_grounding_and_worklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            psf = os.path.join(tmp, "homework_4.md")
            with open(psf, "w", encoding="utf-8") as f:
                f.write(PS)
            hints = os.path.join(tmp, "hints.md")
            with open(hints, "w", encoding="utf-8") as f:
                f.write("hint text")
            out = prep.collect(paths, psf, ["1", "2"], _retrieve, hints_file=hints)
            parts = json.load(open(os.path.join(paths.packet_dir, "parts.json"), encoding="utf-8"))
            self.assertEqual([p["part_id"] for p in parts], ["q1", "q2"])
            self.assertIn("First question text", parts[0]["statement"])
            self.assertEqual(parts[0]["concept_tags"], [])
            grounding = open(os.path.join(paths.packet_dir, "grounding.md"), encoding="utf-8").read()
            self.assertIn("## q1", grounding)
            self.assertIn("p. 3", grounding)
            self.assertEqual(open(os.path.join(paths.packet_dir, "sealed", "hints.md"), encoding="utf-8").read(), "hint text")
            self.assertEqual(open(os.path.join(paths.packet_dir, "sealed", "solution.md"), encoding="utf-8").read(), "")
            self.assertTrue(os.path.exists(os.path.join(paths.packet_dir, "worklist.md")))
            self.assertFalse(out["validated"])

    def test_refuses_to_overwrite_existing_parts_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            psf = os.path.join(tmp, "homework_4.md")
            with open(psf, "w", encoding="utf-8") as f:
                f.write(PS)
            with self.assertRaises(FileExistsError):
                prep.collect(paths, psf, ["1"], _retrieve)
            prep.collect(paths, psf, ["1"], _retrieve, force=True)


class TestSubmit(unittest.TestCase):
    def test_skeleton_fails_validation_with_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            psf = os.path.join(tmp, "homework_4.md")
            with open(psf, "w", encoding="utf-8") as f:
                f.write(PS)
            prep.collect(paths, psf, ["1"], _retrieve)
            result = prep.submit(paths)
            self.assertFalse(result["ok"])
            self.assertTrue(result["errors"])
            self.assertFalse(is_validated(paths.packet_dir))

    def test_valid_packet_gets_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            os.remove(os.path.join(paths.packet_dir, "validated.json"))
            self.assertEqual(prep.submit(paths), {"ok": True})
            self.assertTrue(is_validated(paths.packet_dir))
```

(`GLOSSARY, HINTS, SOLUTION` imports are intentionally unused-safe; remove if your linter complains.)

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_prep.py -q`
Expected: FAIL `ImportError: cannot import name 'prep'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/prep.py
"""prep.py -- deterministic half of offline prep (spec §3.1). collect()
parses the problem set, retrieves grounding passages and writes a packet
skeleton plus a worklist; the live IDE agent then authors the glossary,
rubric, tags, evidence and sealed sections, and submit() validates them.
No LLM call happens here; the caller supplies `retrieve`."""
from __future__ import annotations

import json
import os
import re
from typing import Callable

from agent.rag.problem_set_parser import extract_question
from agent.tutor.packet import validate_packet, write_validated
from agent.tutor.paths import TutorPaths

WORKLIST = """# Prep worklist (for the IDE agent)

Complete these in `packet/`, then run `prep-submit` and fix every reported error.

1. `parts.json`: split each question into the parts the student will work through (one entry per sub-part is
   fine). Per part set `part_id` (unique, e.g. `q1_2`), `label`, `statement` (verbatim, neutral, no hints),
   `concept_tags` (kebab-case, reusable across problem sets), `expected_evidence` (what a correct attempt must show).
   Optional `chat_statement`: the statement with Unicode math instead of LaTeX, for chat bubbles.
2. `glossary.json`: `{term: generic domain definition}` for every term a student might ask about. A definition
   must NOT use the problem's variables or notation and must NOT refer to a part or question number.
3. `rubric.json`: `{part_id: {axis: {rating: descriptor}}}` with axes `conceptual`, `rigor`, `directness` and
   ratings `Developing / Needs Review`, `Proficient`, `Mastered`.
4. `sealed/hints.md` and `sealed/solution.md`: one `## <part_id>` section per part. Solutions are for internal
   verification only. If a guided-solutions file exists, restructure it into these sections; otherwise write them.
5. Read `grounding.md` for the course's own notation and sources; prefer it over generic textbook conventions.
"""


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _slug(ref: str) -> str:
    return "q" + re.sub(r"[^A-Za-z0-9]+", "_", ref).strip("_")


def collect(
    paths: TutorPaths, problem_set_file: str, question_refs: list[str], retrieve: Callable[[str], list],
    hints_file: str | None = None, solutions_file: str | None = None, force: bool = False,
) -> dict:
    d = paths.packet_dir
    if os.path.exists(os.path.join(d, "parts.json")) and not force:
        raise FileExistsError(f"{d}/parts.json already exists; pass force=True to overwrite")
    parts, grounding = [], ["# Grounding passages (internal; never quote to the student)\n"]
    for ref in question_refs:
        statement = extract_question(problem_set_file, ref)
        pid = _slug(ref)
        parts.append({"part_id": pid, "label": f"Question {ref}", "statement": statement,
                      "concept_tags": [], "expected_evidence": []})
        grounding.append(f"\n## {pid}\n")
        for p in retrieve(statement):
            snippet = p.text[:600].replace("\n", " ")
            grounding.append(f"- {p.citation} ({p.path}, score {p.score:.2f})\n  > {snippet}\n")
    _write(os.path.join(d, "parts.json"), json.dumps(parts, ensure_ascii=False, indent=2))
    _write(os.path.join(d, "glossary.json"), "{}")
    _write(os.path.join(d, "rubric.json"), "{}")
    _write(os.path.join(d, "grounding.md"), "\n".join(grounding))
    for name, src in (("hints.md", hints_file), ("solution.md", solutions_file)):
        text = ""
        if src:
            with open(src, "r", encoding="utf-8") as f:
                text = f.read()
        _write(os.path.join(d, "sealed", name), text)
    _write(os.path.join(d, "worklist.md"), WORKLIST)
    return {"ok": True, "packet_dir": d, "parts": [p["part_id"] for p in parts], "validated": False}


def submit(paths: TutorPaths) -> dict:
    errors = validate_packet(paths.packet_dir)
    if errors:
        return {"ok": False, "errors": errors}
    write_validated(paths.packet_dir)
    return {"ok": True}
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_prep.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/prep.py tests/agent/tutor/test_tutor_prep.py
git commit -m "feat(tutor): prep collect/submit with worklist"
```

---

### Task 7: Rendering and learner profile

**Files:**
- Create: `agent/tutor/render.py`, `agent/tutor/profile.py`
- Test: `tests/agent/tutor/test_tutor_render_profile.py`

**Interfaces:**
- Consumes: `Event`, `Packet`/`Part`, `ratings.AXES/RATINGS`.
- Produces (render): `render_transcript(events) -> str`; `render_summary(events, packet, big_picture, prior_gaps, date) -> str`; `write_session_docs(session_dir, events, packet, big_picture, prior_gaps, date) -> (transcript_path, summary_path)`.
- Produces (profile): `SCHEMA_VERSION = 1`; `load_profile(path) -> dict` (empty profile if missing); `update_profile(profile, *, session_id, date, events, packet) -> dict` (returns new dict); `save_profile(json_path, md_path, profile)`; `render_profile_md(profile) -> str`; `open_gaps(profile) -> list[str]`.
- Profile shape: `{"schema_version": 1, "concepts": {tag: {"history": [{"session","date","part","axis","rating"}], "open_misconceptions": [str]}}}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_render_profile.py
import json
import os
import tempfile
import unittest

from agent.tutor.events import Event
from agent.tutor.packet import Packet, Part
from agent.tutor.profile import SCHEMA_VERSION, load_profile, open_gaps, render_profile_md, save_profile, update_profile
from agent.tutor.render import render_summary, render_transcript, write_session_docs

DEV, PROF = "Developing / Needs Review", "Proficient"


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


def ratings(conc, rigor, direct, evidence):
    return {"conceptual": {"rating": conc, "evidence": evidence}, "rigor": {"rating": rigor, "evidence": evidence},
            "directness": {"rating": direct, "evidence": evidence}}


PACKET = Packet("microecon", "homework_4", [
    Part("q1", "S1", ["random-consideration-set"], ["e"], label="Question 1"),
    Part("q2", "S2", ["concavity"], ["e"], label="Question 2"),
], {}, {})
EVENTS = [
    ev(1, "student", text="I think the set is bounded", intent="attempt"),
    ev(2, "tutor_say", text="What does closed mean here?"),
    ev(3, "misconception", data={"tag": "closed-implies-bounded", "axis": "all"}),
    ev(4, "close_part", data={"ratings": ratings(DEV, DEV, PROF, [1])}),
    ev(5, "student", part="q2", text="ok next", intent="confirm_advance"),
    ev(6, "close_part", part="q2", data={"ratings": ratings(PROF, PROF, PROF, [5])}),
]


class TestRender(unittest.TestCase):
    def test_transcript_lists_student_and_tutor_turns_only(self):
        t = render_transcript(EVENTS)
        self.assertIn("**Student:** I think the set is bounded", t)
        self.assertIn("**Tutor:** What does closed mean here?", t)
        self.assertNotIn("closed-implies-bounded", t)

    def test_summary_has_four_sections_with_calibrated_ratings(self):
        s = render_summary(EVENTS, PACKET, "Big picture prose.", ["concavity"], "2026-10-08")
        for heading in ("## 1. Diagnostic", "## 2. Big Picture", "## 3. Tri-Axial Rubric", "## 4. Action Menu"):
            self.assertIn(heading, s)
        self.assertIn("Big picture prose.", s)
        self.assertIn("Conceptual Fluency", s)
        self.assertIn("I think the set is bounded", s)  # event-id evidence rendered as the quote
        self.assertIn("random-consideration-set", s.split("## 4. Action Menu")[1])  # Developing part -> review item
        self.assertIn("concavity", s.split("## 4. Action Menu")[1])  # previously flagged gap carried forward

    def test_write_session_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            t, s = write_session_docs(tmp, EVENTS, PACKET, "bp", [], "2026-10-08")
            self.assertTrue(os.path.exists(t) and os.path.exists(s))


class TestProfile(unittest.TestCase):
    def test_missing_profile_is_empty_versioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = load_profile(os.path.join(tmp, "nope.json"))
            self.assertEqual(p, {"schema_version": SCHEMA_VERSION, "concepts": {}})

    def test_update_records_history_and_open_misconceptions(self):
        p = update_profile(load_profile("/nonexistent"), session_id="2026-10-08-1000", date="2026-10-08", events=EVENTS, packet=PACKET)
        hist = p["concepts"]["random-consideration-set"]["history"]
        self.assertEqual({(h["axis"], h["rating"]) for h in hist}, {("conceptual", DEV), ("rigor", DEV), ("directness", PROF)})
        self.assertEqual(p["concepts"]["random-consideration-set"]["open_misconceptions"], ["closed-implies-bounded"])
        self.assertEqual(p["concepts"]["concavity"]["open_misconceptions"], [])

    def test_resolved_misconception_is_not_left_open(self):
        events = EVENTS + [ev(7, "misconception_resolved", data={"tag": "closed-implies-bounded"})]
        p = update_profile(load_profile("/nonexistent"), session_id="s", date="d", events=events, packet=PACKET)
        self.assertEqual(p["concepts"]["random-consideration-set"]["open_misconceptions"], [])

    def test_open_gaps_uses_latest_session_and_open_misconceptions(self):
        p = update_profile(load_profile("/nonexistent"), session_id="2026-10-01-1000", date="2026-10-01", events=EVENTS, packet=PACKET)
        self.assertEqual(open_gaps(p), ["random-consideration-set"])
        better = [ev(1, "close_part", data={"ratings": ratings(PROF, PROF, PROF, [1])})]
        p2 = update_profile(p, session_id="2026-10-08-1000", date="2026-10-08", events=better, packet=PACKET)
        # Latest rating is fine but the misconception from the earlier session is still open.
        self.assertEqual(open_gaps(p2), ["random-consideration-set"])
        fixed = better + [ev(2, "misconception_resolved", data={"tag": "closed-implies-bounded"})]
        p3 = update_profile(p, session_id="2026-10-09-1000", date="2026-10-09", events=fixed, packet=PACKET)
        self.assertEqual(open_gaps(p3), [])

    def test_save_and_reload_round_trip_and_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = update_profile(load_profile("/nonexistent"), session_id="s", date="d", events=EVENTS, packet=PACKET)
            jp, mp = os.path.join(tmp, "p.json"), os.path.join(tmp, "p.md")
            save_profile(jp, mp, p)
            self.assertEqual(load_profile(jp), p)
            self.assertIn("random-consideration-set", open(mp, encoding="utf-8").read())
            self.assertIn("random-consideration-set", render_profile_md(p))
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_render_profile.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.render`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/render.py
"""render.py -- vault markdown from the event log (spec §5, §6)."""
from __future__ import annotations

import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import AXES, RATINGS

AXIS_NAMES = {"conceptual": "Conceptual Fluency", "rigor": "Mathematical Rigor & Notation", "directness": "Directness & Proof Elegance"}


def render_transcript(events: list[Event]) -> str:
    lines = ["# Transcript", ""]
    for e in events:
        if e.type == "student":
            lines += [f"**Student:** {e.text}", ""]
        elif e.type == "tutor_say":
            lines += [f"**Tutor:** {e.text}", ""]
    return "\n".join(lines)


def _evidence_text(item, by_id: dict) -> str:
    if isinstance(item, int):
        e = by_id.get(item)
        text = (e.text or e.data.get("tag", "")) if e else f"event {item}"
        return f'"{" ".join(text.split())[:140]}" (event {item})'
    return f'"{item}"'


def render_summary(events: list[Event], packet: Packet, big_picture: str, prior_gaps: list[str], date: str) -> str:
    by_id = {e.id: e for e in events}
    closed = {e.part: e.data["ratings"] for e in events if e.type == "close_part"}
    lines = [f"# Session Summary — {packet.problem_set} ({date})", "", "## 1. Diagnostic", "",
             "| Part | Concepts | " + " | ".join(AXIS_NAMES[a] for a in AXES) + " |",
             "|---|---|" + "---|" * len(AXES)]
    for part in packet.parts:
        r = closed.get(part.part_id)
        cells = [r[a]["rating"] if r else "—" for a in AXES]
        lines.append(f"| {part.label or part.part_id} | {', '.join(part.concept_tags)} | " + " | ".join(cells) + " |")
    lines += ["", "## 2. Big Picture", "", big_picture.strip(), "", "## 3. Tri-Axial Rubric", ""]
    for part in packet.parts:
        r = closed.get(part.part_id)
        if not r:
            continue
        lines.append(f"### {part.label or part.part_id}")
        for a in AXES:
            ev_text = "; ".join(_evidence_text(i, by_id) for i in r[a]["evidence"])
            lines.append(f"- **{AXIS_NAMES[a]} — {r[a]['rating']}**: {ev_text}")
        lines.append("")
    lines += ["## 4. Action Menu", ""]
    review = []
    for part in packet.parts:
        r = closed.get(part.part_id)
        if r and any(r[a]["rating"] == RATINGS[0] for a in AXES):
            review += [t for t in part.concept_tags if t not in review]
    for tag in review:
        lines.append(f"- Review `{tag}` (rated Developing / Needs Review this session)")
    for tag in prior_gaps:
        if tag not in review:
            lines.append(f"- Previously flagged, still open: `{tag}`")
    if not review and not prior_gaps:
        lines.append("- No review items flagged.")
    return "\n".join(lines) + "\n"


def write_session_docs(session_dir, events, packet, big_picture, prior_gaps, date) -> tuple[str, str]:
    os.makedirs(session_dir, exist_ok=True)
    t = os.path.join(session_dir, "transcript.md")
    s = os.path.join(session_dir, "summary.md")
    with open(t, "w", encoding="utf-8") as f:
        f.write(render_transcript(events))
    with open(s, "w", encoding="utf-8") as f:
        f.write(render_summary(events, packet, big_picture, prior_gaps, date))
    return t, s
```

```python
# agent/tutor/profile.py
"""profile.py -- per-course concept-gap tracker (spec §6). Single writer:
Session.end(). schema_version is stable so the future learning-progress
subproject (spec §10.2) can build on it."""
from __future__ import annotations

import copy
import json
import os

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS

SCHEMA_VERSION = 1


def load_profile(path: str) -> dict:
    if not os.path.exists(path):
        return {"schema_version": SCHEMA_VERSION, "concepts": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def update_profile(profile: dict, *, session_id: str, date: str, events: list[Event], packet: Packet) -> dict:
    new = copy.deepcopy(profile)
    resolved = {(e.part, e.data["tag"]) for e in events if e.type == "misconception_resolved"}
    for part in packet.parts:
        for tag in part.concept_tags:
            entry = new["concepts"].setdefault(tag, {"history": [], "open_misconceptions": []})
            for e in events:
                if e.type == "close_part" and e.part == part.part_id:
                    for axis, r in e.data["ratings"].items():
                        entry["history"].append({"session": session_id, "date": date, "part": part.part_id,
                                                 "axis": axis, "rating": r["rating"]})
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


def open_gaps(profile: dict) -> list[str]:
    gaps = []
    for tag, entry in sorted(profile["concepts"].items()):
        hist = entry["history"]
        latest = max((h["session"] for h in hist), default=None)
        developing = any(h["rating"] == RATINGS[0] for h in hist if h["session"] == latest)
        if developing or entry["open_misconceptions"]:
            gaps.append(tag)
    return gaps


def render_profile_md(profile: dict) -> str:
    lines = ["# Learner profile", "", f"_schema v{profile['schema_version']}_", "", "## Open gaps", ""]
    gaps = open_gaps(profile)
    lines += [f"- `{t}`" + (f" — misconceptions: {', '.join(profile['concepts'][t]['open_misconceptions'])}"
                            if profile['concepts'][t]['open_misconceptions'] else "") for t in gaps] or ["- None"]
    lines += ["", "## History", ""]
    for tag, entry in sorted(profile["concepts"].items()):
        lines.append(f"### {tag}")
        for h in entry["history"]:
            lines.append(f"- {h['date']} {h['part']} {h['axis']}: {h['rating']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def save_profile(json_path: str, md_path: str, profile: dict) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_profile_md(profile))
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_render_profile.py -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/render.py agent/tutor/profile.py tests/agent/tutor/test_tutor_render_profile.py
git commit -m "feat(tutor): session rendering and learner profile"
```

---

### Task 8: Session orchestration

**Files:**
- Create: `agent/tutor/session.py`
- Test: `tests/agent/tutor/test_tutor_session.py`

**Interfaces:**
- Consumes: everything above.
- Produces: class `Session` with
  - `Session.start(paths, now=None) -> Session` (resumes the latest unfinished session dir, else creates `YYYY-MM-DD-HHMM`; adds `-2`, `-3`… on collision; refreshes `packet/prior_gaps.md`);
  - `Session.open(paths, session_id=None) -> Session` (latest unfinished, or the named one; `ValueError` if none);
  - `view() -> dict` with keys `ok, session, state, part_id, part_index, n_parts, hint_level, guidance, prior_gaps` and `launch_text` in LAUNCH;
  - `student(intent, text, misconceptions=(), admits_gap=None) -> dict` (view + `hint_capped`); raises `IllegalTransition` (nothing logged);
  - `say(text) -> dict` (`ok: True, send: text` + view, or `ok: False, violations: [...]`);
  - `define(term) -> dict`; `sealed(kind) -> dict` (`kind` in `hint|solution`); `verdict(assessment, note="") -> dict`;
  - `misconception(tag, axis="all", resolved=False) -> dict`; `close_part(ratings) -> dict`; `end(big_picture) -> dict` (`ok, transcript, summary, profile`).
- Raises: `IllegalTransition`, `RatingRejected`, `PacketError`, `ValueError`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_session.py
import datetime
import os
import tempfile
import unittest

from agent.tutor.events import EventLog
from agent.tutor.fsm import IllegalTransition
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.sample_packet import SOLUTION, write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def rate(rating, evidence):
    return {a: {"rating": rating, "evidence": evidence} for a in ("conceptual", "rigor", "directness")}


def solve_part(s, attempt="my answer"):
    s.student("attempt", attempt)
    s.verdict("correct")


class TestStartAndResume(unittest.TestCase):
    def test_start_creates_session_and_shows_verbatim_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            v = s.view()
            self.assertEqual((v["state"], v["part_id"], v["session"]), ("LAUNCH", "q1", "2026-10-08-1000"))
            self.assertTrue(v["launch_text"].endswith("How would you like to approach this problem?"))
            self.assertTrue(os.path.exists(os.path.join(paths.sessions_dir, "2026-10-08-1000", "events.jsonl")))

    def test_restart_resumes_same_session_with_identical_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.student("stuck", "no idea")
            again = Session.start(paths, now=NOW + datetime.timedelta(hours=1))
            self.assertEqual(again.view()["session"], s.view()["session"])
            self.assertEqual((again.view()["state"], again.view()["hint_level"]), ("WORKING", 1))

    def test_new_session_after_finished_one_gets_new_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            sid = s.view()["session"]
            EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).append("session_end", state="DONE")
            s2 = Session.start(paths, now=NOW)
            self.assertEqual(s2.view()["session"], sid + "-2")

    def test_unvalidated_packet_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "a", encoding="utf-8") as f:
                f.write("\nedit")
            with self.assertRaises(Exception) as ctx:
                Session.start(paths, now=NOW)
            self.assertIn("prep-submit", str(ctx.exception))

    def test_open_without_any_session_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            with self.assertRaises(ValueError):
                Session.open(paths)


class TestStudentAndSay(unittest.TestCase):
    def test_say_launch_text_ok_and_extra_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            launch = s.view()["launch_text"]
            self.assertTrue(s.say(launch)["ok"])
            r = s.say(launch + " Assume the first option is better.")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "LAUNCH_NOT_VERBATIM")

    def test_rejected_draft_is_logged_but_not_in_transcript_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            s.student("attempt", "hm")
            s.say("Use contradiction here.")
            types = [e.type for e in s.log.load()]
            self.assertIn("lint_reject", types)
            self.assertNotIn("tutor_say", types)

    def test_hint_level_rises_only_on_student_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "first try")
            self.assertEqual(s.view()["hint_level"], 0)
            self.assertEqual(s.student("stuck", "I'm stuck")["hint_level"], 1)
            self.assertEqual(s.student("attempt", "another try")["hint_level"], 1)

    def test_define_flow_returns_glossary_text_and_say_must_stay_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("define_request", "what is choice overload?")
            d = s.define("Choice Overload")
            self.assertTrue(d["ok"])
            self.assertTrue(s.say(d["definition"])["ok"])
            self.assertFalse(s.say("It means d gets chosen more.")["ok"])
            self.assertFalse(s.define("nonexistent term")["ok"])

    def test_empty_student_text_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(ValueError):
                s.student("attempt", "   ")


class TestSealed(unittest.TestCase):
    def test_refused_before_first_attempt_then_allowed_and_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            self.assertFalse(s.sealed("solution")["ok"])
            s.student("attempt", "first try")
            r = s.sealed("solution")
            self.assertTrue(r["ok"])
            self.assertIn("one minus the total probability", r["text"])
            self.assertIn("sealed", [e.type for e in s.log.load()])
            self.assertFalse(s.sealed("secret")["ok"])


class TestAdvanceGating(unittest.TestCase):
    def test_full_two_part_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = make(tmp)
            solve_part(s)
            self.assertEqual(s.view()["state"], "VERIFIED")
            ev_id = [e for e in s.log.load() if e.type == "student"][0].id
            self.assertFalse(s.say("Correct.")["ok"])  # no check-in question
            s.close_part(rate(MAST, [ev_id]))
            r = s.say("Correct. Do you have any lingering questions, or are you ready to move on?")
            self.assertTrue(r["ok"])
            self.assertEqual((r["state"], r["part_id"]), ("AWAITING_ADVANCE", "q1"))  # tutor cannot advance
            v = s.student("confirm_advance", "ready, next please")
            self.assertEqual((v["state"], v["part_id"], v["hint_level"]), ("LAUNCH", "q2", 0))
            solve_part(s, "part two answer")
            e2 = [e for e in s.log.load() if e.type == "student"][-1].id
            s.close_part(rate(MAST, [e2]))
            s.say("Correct. Do you have any lingering questions, or are you ready to move on?")
            self.assertEqual(s.student("confirm_advance", "done")["state"], "SYNTHESIS")
            out = s.end("Big picture text.")
            self.assertTrue(os.path.exists(out["summary"]))
            self.assertTrue(os.path.exists(out["profile"]))
            self.assertEqual(s.log.load()[-1].type, "session_end")
            with self.assertRaises(IllegalTransition):
                s.student("attempt", "more")

    def test_say_in_verified_cannot_mention_next_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            solve_part(s)
            r = s.say("Correct. Ready for Question 2, or any lingering questions?")
            self.assertFalse(r["ok"])
            self.assertEqual(r["violations"][0]["code"], "NEXT_PART_REFERENCE")

    def test_confirm_advance_before_close_part_or_while_working_fails_and_logs_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "try")
            n = len(s.log.load())
            with self.assertRaises(IllegalTransition):
                s.student("confirm_advance", "ready to move on")  # still WORKING
            s.verdict("correct")
            n = len(s.log.load())
            with self.assertRaises(IllegalTransition) as ctx:
                s.student("confirm_advance", "ready to move on")  # VERIFIED but not closed
            self.assertIn("close-part", str(ctx.exception))
            self.assertEqual(len(s.log.load()), n)

    def test_end_requires_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            with self.assertRaises(IllegalTransition):
                s.end("too early")


class TestClosePart(unittest.TestCase):
    def test_inflated_rating_rejected_with_misconception_on_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "a closed set must be bounded", misconceptions=(("closed-implies-bounded", "all"),))
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            with self.assertRaises(RatingRejected):
                s.close_part(rate(PROF, [att]))
            s.close_part(rate(DEV, [att]))
            with self.assertRaises(IllegalTransition):
                s.close_part(rate(DEV, [att]))  # already closed

    def test_close_part_only_when_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "try")
            with self.assertRaises(IllegalTransition):
                s.close_part(rate(DEV, [2]))

    def test_misconception_resolved_event_and_student_admits_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = make(tmp)
            s.student("attempt", "I don't get concavity", admits_gap="conceptual")
            s.misconception("secant-chords", axis="rigor")
            s.misconception("secant-chords", resolved=True)
            types = [e.type for e in s.log.load()]
            self.assertIn("misconception", types)
            self.assertIn("misconception_resolved", types)
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            with self.assertRaises(RatingRejected):
                s.close_part({**rate(MAST, [att]), "conceptual": {"rating": PROF, "evidence": [att]}})
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_session.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.session`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/session.py
"""session.py -- ties the FSM, lint, ratings, packet and persistence together
(spec §3.2). Stateless: every method replays events.jsonl, so a CLI process
can exit between calls and state is identical on reload."""
from __future__ import annotations

import os
import re
from datetime import datetime

from agent.tutor import fsm
from agent.tutor.events import Event, EventLog
from agent.tutor.fsm import (
    AWAITING_ADVANCE, LAUNCH, SYNTHESIS, VERIFIED, WORKING, IllegalTransition,
    FsmState, replay, student_event,
)
from agent.tutor.lint import lint_message
from agent.tutor.packet import Packet, load_packet, read_sealed, sealed_section
from agent.tutor.paths import TutorPaths
from agent.tutor.profile import load_profile, open_gaps, save_profile, update_profile
from agent.tutor.ratings import validate_close_part
from agent.tutor.render import write_session_docs

_GUIDANCE = {
    LAUNCH: "Send ONLY the launch text via say. No hints, setup or roadmap. Then wait for the student.",
    SYNTHESIS: "All parts are closed. Write the big-picture synthesis and call end.",
    VERIFIED: "Confirm correctness without extending the solution. Call close-part, then say a check-in "
              "asking whether they have lingering questions or are ready to move on. Do not mention the next part.",
    AWAITING_ADVANCE: "Wait for the student. Answer their questions under the normal Socratic rules. "
                      "Never mention the next part until they confirm.",
}
_WORKING_GUIDANCE = {
    0: "Level 0: give minimal evaluative feedback on what the student wrote; ask what they are thinking. "
       "No hints, no proof technique, no leading sub-questions.",
    1: "Level 1: Socratic check only (what intuition or definition applies?). No direction yet.",
    2: "Level 2: a targeted nudge about analytical direction is allowed; still do not name a proof technique "
       "the student has not named.",
    3: "Level 3 (last resort): intermediate steps allowed. Keep them minimal; never quote the sealed solution.",
}


class Session:
    def __init__(self, paths: TutorPaths, session_id: str, packet: Packet):
        self.paths, self.session_id, self.packet = paths, session_id, packet
        self.dir = os.path.join(paths.sessions_dir, session_id)
        self.log = EventLog(os.path.join(self.dir, "events.jsonl"))
        self._hints, self._solution = read_sealed(paths.packet_dir)

    # ---- construction -------------------------------------------------
    @staticmethod
    def _is_open(paths: TutorPaths, sid: str) -> bool:
        events = EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).load()
        return bool(events) and not any(e.type == "session_end" for e in events)

    @classmethod
    def _latest_open(cls, paths: TutorPaths) -> str | None:
        if not os.path.isdir(paths.sessions_dir):
            return None
        for sid in sorted(os.listdir(paths.sessions_dir), reverse=True):
            if cls._is_open(paths, sid):
                return sid
        return None

    @classmethod
    def start(cls, paths: TutorPaths, now: datetime | None = None) -> "Session":
        packet = load_packet(paths)
        sid = cls._latest_open(paths)
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
        session._write_prior_gaps()
        return session

    @classmethod
    def open(cls, paths: TutorPaths, session_id: str | None = None) -> "Session":
        packet = load_packet(paths)
        sid = session_id or cls._latest_open(paths)
        if sid is None:
            raise ValueError("no open session; run start first")
        return cls(paths, sid, packet)

    # ---- helpers ------------------------------------------------------
    def _prior_gaps(self) -> list[str]:
        tags = {t for p in self.packet.parts for t in p.concept_tags}
        return [g for g in open_gaps(load_profile(self.paths.profile_json)) if g in tags]

    def _write_prior_gaps(self) -> None:
        gaps = self._prior_gaps()
        text = "# Prior gaps (informational; never a source of hints)\n\n" + (
            "\n".join(f"- `{g}`" for g in gaps) if gaps else "- None") + "\n"
        with open(os.path.join(self.paths.packet_dir, "prior_gaps.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def _fsm(self, events: list[Event] | None = None) -> FsmState:
        return replay(self.log.load() if events is None else events, len(self.packet.parts))

    def _guidance(self, s: FsmState) -> str:
        return _WORKING_GUIDANCE[s.hint_level] if s.state == WORKING else _GUIDANCE.get(s.state, "Session finished.")

    def view(self) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        out = {"ok": True, "session": self.session_id, "state": s.state, "part_id": part.part_id,
               "part_index": s.part_index, "n_parts": len(self.packet.parts), "hint_level": s.hint_level,
               "guidance": self._guidance(s), "prior_gaps": self._prior_gaps()}
        if s.state == LAUNCH:
            out["launch_text"] = part.launch_text()
        return out

    @staticmethod
    def _closed(events: list[Event], part_id: str) -> bool:
        return any(e.type == "close_part" and e.part == part_id for e in events)

    # ---- commands -----------------------------------------------------
    def student(self, intent: str, text: str, misconceptions=(), admits_gap: str | None = None) -> dict:
        """misconceptions: iterable of (tag, axis) pairs, axis in conceptual|rigor|directness|all."""
        if not (text or "").strip():
            raise ValueError("student text is empty; log the student's verbatim message")
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if intent == "confirm_advance" and s.state in (VERIFIED, AWAITING_ADVANCE) and not self._closed(events, part.part_id):
            raise IllegalTransition(f"call close-part for {part.part_id} before the student can advance")
        new, info = student_event(s, intent, len(self.packet.parts))
        part_id = self.packet.parts[new.part_index].part_id
        data = dict(info)
        if admits_gap:
            data.update(admits_gap=True, gap_axis=admits_gap)
        self.log.append("student", part=part_id, state=new.state, hint_level=new.hint_level,
                        intent=intent, text=text, data=data)
        for tag, axis in misconceptions:
            self.log.append("misconception", part=part_id, state=new.state, hint_level=new.hint_level,
                            data={"tag": tag, "axis": axis})
        return {**self.view(), "hint_capped": info["hint_capped"]}

    def say(self, text: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        part_events = [e for e in events if e.part == part.part_id]
        student_text = " ".join(e.text or "" for e in part_events if e.type == "student")
        allowed = [part.launch_text()] if s.state == LAUNCH else []
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        after_define = bool(last_student and last_student.intent == "define_request")
        if after_define:
            for e in reversed(events):
                if e.type == "define":
                    allowed.append(e.data["definition"])
                    break
                if e.type == "student":
                    break
        forbidden = []
        nxt = s.part_index + 1
        if s.state in (VERIFIED, AWAITING_ADVANCE) and nxt < len(self.packet.parts):
            n = self.packet.parts[nxt]
            forbidden = [rf"\b{re.escape(n.part_id)}\b"] + ([rf"\b{re.escape(n.label)}\b"] if n.label else [])
        solution = sealed_section(self._solution, part.part_id) or ""
        violations = lint_message(
            text, state=s.state, hint_level=s.hint_level, student_text=student_text, statement=part.statement,
            sealed_solution=solution, allowed_exact=allowed, after_define=after_define, forbidden_patterns=forbidden,
        )
        if violations:
            self.log.append("lint_reject", part=part.part_id, state=s.state, hint_level=s.hint_level, text=text,
                            data={"violations": [v.to_dict() for v in violations]})
            return {"ok": False, "violations": [v.to_dict() for v in violations],
                    "message": "Revise the draft and call say again. Send nothing to the student until it returns ok."}
        checkin = s.state == VERIFIED
        new = fsm.checkin_event(s) if checkin else s
        self.log.append("tutor_say", part=part.part_id, state=new.state, hint_level=new.hint_level, text=text,
                        data={"checkin": checkin})
        return {**self.view(), "send": text}

    def define(self, term: str) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        for key, definition in self.packet.glossary.items():
            if key.lower() == term.strip().lower():
                self.log.append("define", part=part.part_id, state=s.state, hint_level=s.hint_level,
                                data={"term": key, "definition": definition})
                return {"ok": True, "term": key, "definition": definition}
        return {"ok": False, "error": f"no glossary entry for {term!r}",
                "terms": sorted(self.packet.glossary)}

    def sealed(self, kind: str) -> dict:
        if kind not in ("hint", "solution"):
            return {"ok": False, "error": "kind must be 'hint' or 'solution'"}
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        attempted = any(e.type == "student" and e.part == part.part_id and e.intent == "attempt" for e in events)
        if not attempted or s.state == LAUNCH:
            return {"ok": False, "error": "sealed content is released only after the student has logged an attempt on this part"}
        text = sealed_section(self._hints if kind == "hint" else self._solution, part.part_id)
        self.log.append("sealed", part=part.part_id, state=s.state, hint_level=s.hint_level, data={"kind": kind})
        return {"ok": True, "kind": kind, "part_id": part.part_id, "text": text,
                "warning": "internal verification only: never quote, summarize or outline this to the student"}

    def verdict(self, assessment: str, note: str = "") -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if not any(e.type == "student" and e.part == part.part_id and e.intent == "attempt" for e in events):
            raise IllegalTransition("record a student attempt before giving a verdict")
        new = fsm.verdict_event(s, assessment)
        self.log.append("verdict", part=part.part_id, state=new.state, hint_level=new.hint_level, text=note or None,
                        data={"assessment": assessment})
        return self.view()

    def misconception(self, tag: str, axis: str = "all", resolved: bool = False) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        self.log.append("misconception_resolved" if resolved else "misconception", part=part.part_id,
                        state=s.state, hint_level=s.hint_level, data={"tag": tag, "axis": axis})
        return {"ok": True}

    def close_part(self, ratings: dict) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if s.state not in (VERIFIED, AWAITING_ADVANCE):
            raise IllegalTransition(f"close-part is only valid once the part is verified (state is {s.state})")
        if self._closed(events, part.part_id):
            raise IllegalTransition(f"{part.part_id} is already closed")
        validate_close_part(ratings, [e for e in events if e.part == part.part_id])
        self.log.append("close_part", part=part.part_id, state=s.state, hint_level=s.hint_level,
                        data={"ratings": ratings})
        return self.view()

    def end(self, big_picture: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        if s.state != SYNTHESIS:
            raise IllegalTransition(f"cannot end from state {s.state}; finish and close every part first")
        missing = [p.part_id for p in self.packet.parts if not self._closed(events, p.part_id)]
        if missing:
            raise IllegalTransition(f"parts not closed: {missing}")
        last = self.packet.parts[-1].part_id
        self.log.append("synthesis", part=last, state=SYNTHESIS, text=big_picture)
        self.log.append("session_end", part=last, state=fsm.DONE)
        events = self.log.load()
        date = self.session_id[:10]
        transcript, summary = write_session_docs(self.dir, events, self.packet, big_picture, self._prior_gaps(), date)
        profile = update_profile(load_profile(self.paths.profile_json), session_id=self.session_id, date=date,
                                 events=events, packet=self.packet)
        save_profile(self.paths.profile_json, self.paths.profile_md, profile)
        return {"ok": True, "transcript": transcript, "summary": summary, "profile": self.paths.profile_json}
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_session.py -q`
Expected: all passed. If `test_define_flow...` fails on the second `say`, confirm `after_define` is True because the last student event has intent `define_request`.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/session.py tests/agent/tutor/test_tutor_session.py
git commit -m "feat(tutor): session orchestration over the event log"
```

---

### Task 9: Audit

**Files:**
- Create: `agent/tutor/audit.py`
- Test: `tests/agent/tutor/test_tutor_audit.py`

**Interfaces:**
- Consumes: `Event`, `Packet`, `ratings.ceiling/RATINGS`.
- Produces: `Finding(code, event_id, detail)` frozen dataclass with `.to_dict()`; `audit(events, packet) -> list[Finding]`.
- Codes: `ADVANCE_WITHOUT_CONFIRM`, `HINT_JUMP`, `SEALED_EARLY`, `INTENT_MISMATCH`, `UNANSWERED_STUDENT_TURN`, `RATING_OVER_CEILING`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_audit.py
import datetime
import tempfile
import unittest

from agent.tutor.audit import audit
from agent.tutor.events import Event
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)


def codes(findings):
    return [f.code for f in findings]


def ev(i, type, part="q1", **kw):
    data = kw.pop("data", {})
    return Event(id=i, ts="t", type=type, part=part, data=data, **kw)


class TestAudit(unittest.TestCase):
    def _packet(self, tmp):
        paths = TutorPaths(tmp, "microecon", "homework_4")
        write_sample_packet(paths)
        return paths, Session.start(paths, now=NOW)

    def test_clean_session_has_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths, s = self._packet(tmp)
            s.say(s.view()["launch_text"])
            s.student("attempt", "my try")
            s.say("What made you choose that?")
            self.assertEqual(audit(s.log.load(), s.packet), [])

    def test_unanswered_student_turn_flags_possible_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, s = self._packet(tmp)
            s.student("attempt", "first")
            s.student("attempt", "second")  # no tutor say in between
            # Only the first turn is flagged: the second is still pending and the session has not ended.
            self.assertEqual(codes(audit(s.log.load(), s.packet)), ["UNANSWERED_STUDENT_TURN"])

    def test_tampered_log_findings(self):
        packet_events = [
            ev(1, "session_start"),
            ev(2, "sealed", data={"kind": "solution"}),                                  # before any attempt
            ev(3, "student", text="I like pizza", intent="confirm_advance"),            # label contradicts text
            ev(4, "tutor_say", text="ok"),
            ev(5, "student", part="q2", text="hmm", intent="attempt"),                   # part change without confirm_advance
            ev(6, "tutor_say", part="q2", text="ok"),
            ev(7, "student", part="q2", text="a", intent="attempt", hint_level=2),       # hint 0 -> 2 on an attempt
            ev(8, "tutor_say", part="q2", text="ok"),
            ev(9, "close_part", part="q2", hint_level=2, data={"ratings": {
                a: {"rating": "Mastered", "evidence": [7]} for a in ("conceptual", "rigor", "directness")}}),
        ]
        from agent.tutor.packet import Packet, Part
        packet = Packet("c", "p", [Part("q1", "s", ["t"], ["e"]), Part("q2", "s", ["t"], ["e"])], {}, {})
        found = codes(audit(packet_events, packet))
        for expected in ("SEALED_EARLY", "INTENT_MISMATCH", "ADVANCE_WITHOUT_CONFIRM", "HINT_JUMP", "RATING_OVER_CEILING"):
            self.assertIn(expected, found)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_audit.py -q`
Expected: FAIL `ModuleNotFoundError: agent.tutor.audit`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/audit.py
"""audit.py -- re-lints a finished (or in-progress) session from its log
(spec §7). The stand-in for the hard file-access wall the user declined:
drift becomes visible even when it was not blocked. UNANSWERED_STUDENT_TURN
is a proxy for 'the agent replied without calling say' because the CLI
cannot observe the chat itself."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.events import Event
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS, ceiling

_CONFIRM_WORDS = re.compile(r"move on|next|ready|continue|go ahead|yes|\bok\b|okay|sure|proceed|done|good", re.I)
_STUCK_WORDS = re.compile(r"stuck|help|hint|don't know|do not know|not sure|no idea|lost|confus", re.I)


@dataclass(frozen=True)
class Finding:
    code: str
    event_id: int
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "event_id": self.event_id, "detail": self.detail}


def audit(events: list[Event], packet: Packet) -> list[Finding]:
    found: list[Finding] = []
    prev_part, prev_level = None, 0
    pending: Event | None = None
    for e in events:
        if e.part and prev_part and e.part != prev_part and not (e.type == "student" and e.intent == "confirm_advance"):
            found.append(Finding("ADVANCE_WITHOUT_CONFIRM", e.id, f"moved from {prev_part} to {e.part} without a student confirm_advance"))
        if e.part and e.part == prev_part and e.hint_level > prev_level:
            ok = e.type == "student" and e.intent in ("stuck", "hint_request") and e.hint_level - prev_level == 1
            if not ok:
                found.append(Finding("HINT_JUMP", e.id, f"hint level rose {prev_level}->{e.hint_level} without a single-step student request"))
        if e.part:
            prev_part, prev_level = e.part, e.hint_level
        if e.type == "sealed":
            attempted = any(x.type == "student" and x.part == e.part and x.intent == "attempt" and x.id < e.id for x in events)
            if not attempted:
                found.append(Finding("SEALED_EARLY", e.id, "sealed content released before any student attempt on this part"))
        if e.type == "student":
            if e.intent == "confirm_advance" and not _CONFIRM_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, "labelled confirm_advance but the text does not ask to move on"))
            if e.intent in ("stuck", "hint_request") and not _STUCK_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, f"labelled {e.intent} but the text does not ask for help"))
            if pending is not None:
                found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "no tutor say before the next student turn"))
            pending = None if e.state == "SYNTHESIS" else e
        elif e.type == "tutor_say":
            pending = None
        elif e.type == "close_part":
            part_events = [x for x in events if x.part == e.part and x.id < e.id]
            for axis, r in e.data["ratings"].items():
                cap, _ = ceiling(part_events, axis)
                if RATINGS.index(r["rating"]) > RATINGS.index(cap):
                    found.append(Finding("RATING_OVER_CEILING", e.id, f"{axis}: {r['rating']} exceeds ceiling {cap}"))
    if pending is not None and any(x.type == "session_end" for x in events):
        found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "session ended with an unanswered student turn"))
    return found
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_audit.py -q`
Expected: 3 passed. (A trailing unanswered student turn is flagged only after `session_end`, so the open-session test yields exactly one finding.)

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/audit.py tests/agent/tutor/test_tutor_audit.py
git commit -m "feat(tutor): session audit"
```

---

### Task 10: CLI and bootstrap prompt

**Files:**
- Create: `agent/tutor/cli.py`, `agent/tutor/bootstrap_prompt.md`
- Test: `tests/agent/tutor/test_tutor_cli.py`

**Interfaces:**
- Consumes: `Session`, `prep`, `audit`, `TutorPaths`.
- Produces: `main(argv=None) -> int`; global options `--hub-root` (default `<repo>/ai-sandbox/academic-hub`), `--course`, `--problem-set`, `--session`; subcommands `prep-collect`, `prep-submit`, `start`, `student`, `say`, `define`, `sealed`, `verdict`, `misconception`, `close-part`, `end`, `audit`, `bootstrap`. Prints JSON to stdout (UTF-8); exit 0 when `ok` is true, 2 otherwise. `student`/`say` accept `--text` or `--text-file`. `student` accepts repeatable `--misconception tag[:axis]` and `--admits-gap [axis]`. `close-part --ratings-file`, `end --big-picture-file`.
- `bootstrap` prints `bootstrap_prompt.md` with `{PYTHON}`, `{HUB_ROOT}`, `{COURSE}`, `{PROBLEM_SET}` substituted.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/tutor/test_tutor_cli.py
import contextlib
import io
import json
import os
import tempfile
import unittest

from agent.tutor import cli
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet


def run(tmp, *args):
    out = io.StringIO()
    argv = ["--hub-root", tmp, "--course", "microecon", "--problem-set", "homework_4", *args]
    with contextlib.redirect_stdout(out):
        code = cli.main(argv)
    return code, json.loads(out.getvalue())


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        write_sample_packet(TutorPaths(self.tmp.name, "microecon", "homework_4"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_start_then_student_via_text_file_with_math_and_unicode(self):
        code, v = run(self.tmp.name, "start")
        self.assertEqual((code, v["state"]), (0, "LAUNCH"))
        text_file = os.path.join(self.tmp.name, "msg.txt")
        msg = 'Is $x \\succeq y$ transitive? She said "maybe" — ≽'
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(msg)
        code, v = run(self.tmp.name, "student", "--intent", "attempt", "--text-file", text_file)
        self.assertEqual((code, v["state"]), (0, "WORKING"))
        events = open(os.path.join(TutorPaths(self.tmp.name, "microecon", "homework_4").sessions_dir,
                                   v["session"], "events.jsonl"), encoding="utf-8").read()
        self.assertIn("≽", events)

    def test_say_violation_exits_2_with_violations(self):
        run(self.tmp.name, "start")
        run(self.tmp.name, "student", "--intent", "attempt", "--text", "hm")
        code, v = run(self.tmp.name, "say", "--text", "Try proof by contradiction.")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertEqual(v["violations"][0]["code"], "TECHNIQUE")

    def test_illegal_transition_is_reported_as_error_json_not_traceback(self):
        run(self.tmp.name, "start")
        code, v = run(self.tmp.name, "student", "--intent", "confirm_advance", "--text", "next")
        self.assertEqual(code, 2)
        self.assertFalse(v["ok"])
        self.assertIn("confirm_advance", v["error"])

    def test_misconception_flag_and_admits_gap(self):
        run(self.tmp.name, "start")
        code, v = run(self.tmp.name, "student", "--intent", "attempt", "--text", "closed means bounded",
                      "--misconception", "closed-implies-bounded:conceptual", "--admits-gap", "conceptual")
        self.assertEqual(code, 0)

    def test_define_sealed_verdict_and_audit_commands(self):
        run(self.tmp.name, "start")
        run(self.tmp.name, "student", "--intent", "define_request", "--text", "what is choice overload?")
        code, d = run(self.tmp.name, "define", "choice overload")
        self.assertTrue(d["ok"])
        code, s = run(self.tmp.name, "sealed", "hint")
        self.assertEqual(code, 2)  # no attempt yet
        run(self.tmp.name, "student", "--intent", "attempt", "--text", "try")
        code, s = run(self.tmp.name, "sealed", "hint")
        self.assertEqual(code, 0)
        code, v = run(self.tmp.name, "verdict", "--assessment", "correct")
        self.assertEqual(v["state"], "VERIFIED")
        code, a = run(self.tmp.name, "audit")
        self.assertIn("findings", a)

    def test_close_part_and_end_via_files(self):
        run(self.tmp.name, "start")
        for _ in range(2):
            run(self.tmp.name, "student", "--intent", "attempt", "--text", "answer")
            _, v = run(self.tmp.name, "verdict", "--assessment", "correct")
            rf = os.path.join(self.tmp.name, "r.json")
            with open(rf, "w", encoding="utf-8") as f:
                json.dump({a: {"rating": "Mastered", "evidence": ["answer"]} for a in ("conceptual", "rigor", "directness")}, f)
            code, _ = run(self.tmp.name, "close-part", "--ratings-file", rf)
            self.assertEqual(code, 0)
            run(self.tmp.name, "say", "--text", "Right. Any lingering questions, or ready to move on?")
            run(self.tmp.name, "student", "--intent", "confirm_advance", "--text", "ready, next")
        bp = os.path.join(self.tmp.name, "bp.md")
        with open(bp, "w", encoding="utf-8") as f:
            f.write("The big picture.")
        code, out = run(self.tmp.name, "end", "--big-picture-file", bp)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(out["summary"]))

    def test_bootstrap_fills_placeholders(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["--hub-root", "/H", "--course", "microecon", "--problem-set", "homework_4", "bootstrap"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("/H", text)
        self.assertIn("homework_4", text)
        self.assertNotIn("{HUB_ROOT}", text)
        self.assertNotIn("{PYTHON}", text)
```

- [ ] **Step 2: Run to verify it fails**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_cli.py -q`
Expected: FAIL `ImportError: cannot import name 'cli'`.

- [ ] **Step 3: Implement**

```python
# agent/tutor/cli.py
"""cli.py -- the command surface the live IDE agent calls every turn
(spec §3.2). JSON on stdout, exit 0 when ok else 2. Run as
`python -m agent.tutor.cli --hub-root H --course C --problem-set PS <command> ...`."""
from __future__ import annotations

import argparse
import json
import os
import sys

from agent.tutor import audit as audit_mod
from agent.tutor import prep
from agent.tutor.fsm import INTENTS, IllegalTransition
from agent.tutor.packet import PacketError
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.session import Session

_DEFAULT_HUB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


def _text(args) -> str:
    if getattr(args, "text_file", None):
        with open(args.text_file, "r", encoding="utf-8") as f:
            return f.read()
    if getattr(args, "text", None) is not None:
        return args.text
    raise ValueError("provide --text or --text-file")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Socratic tutor session gate.")
    p.add_argument("--hub-root", default=_DEFAULT_HUB)
    p.add_argument("--course", required=True)
    p.add_argument("--problem-set", required=True)
    p.add_argument("--session", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("prep-collect")
    c.add_argument("--problem-set-file", required=True)
    c.add_argument("--question-ref", action="append", required=True)
    c.add_argument("--hints-file")
    c.add_argument("--solutions-file")
    c.add_argument("--force", action="store_true")
    sub.add_parser("prep-submit")
    sub.add_parser("start")

    s = sub.add_parser("student")
    s.add_argument("--intent", required=True, choices=sorted(INTENTS))
    s.add_argument("--text")
    s.add_argument("--text-file")
    s.add_argument("--misconception", action="append", default=[])
    s.add_argument("--admits-gap", nargs="?", const="all", default=None)

    sy = sub.add_parser("say")
    sy.add_argument("--text")
    sy.add_argument("--text-file")

    d = sub.add_parser("define")
    d.add_argument("term")
    sd = sub.add_parser("sealed")
    sd.add_argument("kind", choices=["hint", "solution"])
    v = sub.add_parser("verdict")
    v.add_argument("--assessment", required=True)
    v.add_argument("--note", default="")
    m = sub.add_parser("misconception")
    m.add_argument("tag")
    m.add_argument("--axis", default="all")
    m.add_argument("--resolved", action="store_true")
    cp = sub.add_parser("close-part")
    cp.add_argument("--ratings-file", required=True)
    e = sub.add_parser("end")
    e.add_argument("--big-picture-file", required=True)
    sub.add_parser("audit")
    sub.add_parser("bootstrap")
    return p


def _dispatch(args, paths: TutorPaths) -> dict:
    if args.cmd == "prep-collect":
        from core.env.gemini_utils import get_gemini_client, load_dotenv_override
        from agent.rag.rag_agent import retrieve_passages
        load_dotenv_override()
        client = get_gemini_client()
        if client is None:
            raise SystemExit(1)
        retrieve = lambda q: retrieve_passages([paths.hub_root], q, client, course=paths.course)
        return prep.collect(paths, args.problem_set_file, args.question_ref, retrieve,
                            hints_file=args.hints_file, solutions_file=args.solutions_file, force=args.force)
    if args.cmd == "prep-submit":
        return prep.submit(paths)
    if args.cmd == "bootstrap":
        template = _read(os.path.join(os.path.dirname(__file__), "bootstrap_prompt.md"))
        for key, value in (("{PYTHON}", sys.executable), ("{HUB_ROOT}", paths.hub_root),
                           ("{COURSE}", paths.course), ("{PROBLEM_SET}", paths.problem_set)):
            template = template.replace(key, value)
        return {"ok": True, "_raw": template}
    if args.cmd == "start":
        return Session.start(paths).view()
    session = Session.open(paths, args.session)
    if args.cmd == "student":
        miscs = []
        for item in args.misconception:
            tag, _, axis = item.partition(":")
            miscs.append((tag, axis or "all"))
        return session.student(args.intent, _text(args), misconceptions=miscs, admits_gap=args.admits_gap)
    if args.cmd == "say":
        return session.say(_text(args))
    if args.cmd == "define":
        return session.define(args.term)
    if args.cmd == "sealed":
        return session.sealed(args.kind)
    if args.cmd == "verdict":
        return session.verdict(args.assessment, args.note)
    if args.cmd == "misconception":
        return session.misconception(args.tag, args.axis, args.resolved)
    if args.cmd == "close-part":
        return session.close_part(json.loads(_read(args.ratings_file)))
    if args.cmd == "end":
        return session.end(_read(args.big_picture_file))
    if args.cmd == "audit":
        findings = [f.to_dict() for f in audit_mod.audit(session.log.load(), session.packet)]
        return {"ok": True, "findings": findings}
    raise ValueError(f"unknown command {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    paths = TutorPaths(args.hub_root, args.course, args.problem_set)
    try:
        result = _dispatch(args, paths)
    except (IllegalTransition, RatingRejected, PacketError, ValueError, FileExistsError, OSError) as err:
        result = {"ok": False, "error": str(err)}
    if "_raw" in result:
        print(result["_raw"])
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
```

```markdown
<!-- agent/tutor/bootstrap_prompt.md -->
# Socratic tutor session — operating contract

You are the live tutor for ONE office-hours session. You are not free-running: a local gate owns the session
state, and you must call it every turn. Gate command (run from the academic-rag-model directory):

    {PYTHON} -m agent.tutor.cli --hub-root "{HUB_ROOT}" --course {COURSE} --problem-set {PROBLEM_SET} <command>

## Every turn
1. Student speaks → `student --intent <attempt|stuck|hint_request|define_request|confirm_advance|has_questions|other> --text-file <file>`
   (always write the student's message to a file; never paste math into the shell). Add
   `--misconception <tag>[:axis]` when they show a conceptual error, `--admits-gap [axis]` when they say they do not understand.
2. Read the returned `state`, `hint_level` and `guidance`. Follow `guidance` exactly.
3. Draft your reply to a file, run `say --text-file <file>`. Send the student ONLY the `send` text from an `ok` result.
   If it returns violations, revise and call `say` again. Never send an unlinted message.
4. First message of a part: send the `launch_text` through `say` verbatim. Nothing else.

## Other commands
- `start` (once, resumes if interrupted). `define "<term>"` for "what does X mean?" (send the definition only, via `say`).
- `verdict --assessment <correct|on_track|adjacent|off_track>` after judging an attempt. Use `sealed hint|solution`
  only to verify the student's work; its text is internal and must never be quoted, summarized or outlined.
- `misconception <tag> [--axis A] [--resolved]`; `close-part --ratings-file` (ratings at or below the evidence ceiling,
  each axis cites an event id or a student quote); `end --big-picture-file` after the last part.

## Hard rules
- Never open files under `packet/sealed/` directly; use the `sealed` command so reveals are logged.
- Never advance a part yourself. Only a logged student `confirm_advance` moves on, after `close-part` and a check-in question.
- Never name a proof technique before the student does. Never connect a definition to the problem's variables.
- Use Unicode math in chat (≽, ≤, λ, ℝ). Be frank in ratings: struggle is signal, not an insult.
```

- [ ] **Step 4: Run to verify it passes**

Run: `& $PY -m pytest tests/agent/tutor -q`
Expected: all tutor tests pass.

- [ ] **Step 5: Commit**

```powershell
git add agent/tutor/cli.py agent/tutor/bootstrap_prompt.md tests/agent/tutor/test_tutor_cli.py
git commit -m "feat(tutor): CLI gate and bootstrap prompt"
```

---

### Task 11: HW4 regression replay

**Files:**
- Test: `tests/agent/tutor/test_tutor_regression.py`

**Interfaces:** consumes `Session`, `sample_packet`. One test per beta deviation (meta-lessons doc §2); each asserts the pipeline blocks the behavior.

- [ ] **Step 1: Write the test**

```python
# tests/agent/tutor/test_tutor_regression.py
"""Replays the five HW4 beta failures (tutoring_pipeline_meta_lessons_learned.md §2).
Each must be blocked by the FSM, `say` lint, or `close-part`."""
import datetime
import tempfile
import unittest

from agent.tutor.fsm import IllegalTransition
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 8, 10, 0)
CHECKIN = "Correct. Do you have any lingering questions, or are you ready to move on?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


class TestHw4Deviations(unittest.TestCase):
    def test_1_premature_scaffolding_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            launch = s.view()["launch_text"]
            roadmap = launch + " Assume the first option is better, then cancel the ratio and find an intermediate option."
            self.assertIn("LAUNCH_NOT_VERBATIM", codes(s.say(roadmap)))
            s.student("attempt", "not sure where to begin")
            leak = "Notice it equals one minus the total probability of choosing any item."
            self.assertIn("SEALED_OVERLAP", codes(s.say(leak)))

    def test_2_unsolicited_advancement_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "answer")
            s.verdict("correct")
            self.assertIn("NEXT_PART_REFERENCE", codes(s.say("Correct. Now on to Question 2!")))
            att = [e for e in s.log.load() if e.type == "student"][0].id
            s.close_part({a: {"rating": "Mastered", "evidence": [att]} for a in ("conceptual", "rigor", "directness")})
            self.assertTrue(s.say(CHECKIN)["ok"])
            self.assertEqual(s.view()["part_id"], "q1")  # still on the same part until the student confirms
            self.assertEqual(s.student("confirm_advance", "ready")["part_id"], "q2")

    def test_3_over_bridging_a_definition_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("define_request", "what is choice overload?")
            s.define("choice overload")
            bridged = "Choice overload is when people walk away, which is your default alternative d from Part 1."
            self.assertIn("NOTATION_BRIDGE", codes(s.say(bridged)))

    def test_4_prescribing_a_proof_technique_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "I'm not sure how to start the non-concavifiability proof")
            prescribe = "Suppose, for the sake of contradiction, that f is concave.\n1. What if x is at most 0?\n2. What if x is positive?"
            self.assertTrue({"TECHNIQUE", "SUBQUESTION_LIST"} <= codes(s.say(prescribe)))
            s.student("other", "maybe contradiction works?")
            self.assertTrue(s.say("Contradiction is a fine option. What would you assume?")["ok"])

    def test_5_grade_inflation_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "closed sets must be bounded", misconceptions=(("closed-implies-bounded", "all"),))
            s.student("stuck", "I'm stuck")
            s.student("hint_request", "can I get a hint?")
            s.verdict("correct")
            att = [e for e in s.log.load() if e.type == "student"][0].id
            inflated = {a: {"rating": "Proficient", "evidence": [att]} for a in ("conceptual", "rigor", "directness")}
            with self.assertRaises(RatingRejected):
                s.close_part(inflated)
            frank = {a: {"rating": "Developing / Needs Review", "evidence": [att]} for a in ("conceptual", "rigor", "directness")}
            s.close_part(frank)

    def test_confirm_cannot_be_smuggled_in_mid_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = make(tmp)
            s.student("attempt", "working on it")
            with self.assertRaises(IllegalTransition):
                s.student("confirm_advance", "ok next")
```

- [ ] **Step 2: Run**

Run: `& $PY -m pytest tests/agent/tutor/test_tutor_regression.py -q`
Expected: all passed. A failure means a rule is too loose; fix the rule in `lint.py`/`session.py`, not the fixture. In `test_3` confirm that `d` and `p` come from the q1 statement symbols.

- [ ] **Step 3: Full tutor suite**

Run: `& $PY -m pytest tests/agent/tutor -q`
Expected: every test passes.

- [ ] **Step 4: Commit**

```powershell
git add tests/agent/tutor/test_tutor_regression.py
git commit -m "test(tutor): replay the five HW4 deviations as regression fixtures"
```

---

### Task 12: Docs, spec amendments, landing check

**Files:**
- Create: `agent/tutor/README.md`, `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md`
- Modify: `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md` (§3.2 command table names, §3.3 `confirm_advance` from VERIFIED, §4 technique rule, §3.1 prior_gaps, §7 audit proxy); `README.md` subproject map in `academic-rag-model/` (one line for `agent/tutor/`)
- Modify (routing, so an agent asked to "start a tutoring session" picks the right pipeline): `academic-rag-model/CLAUDE.md`, `docs/AGENT_ROUTING.md` (repo root `docs/`), `agent/rag/README.md`. The full naming clean-up is a separate pending to-do ("Socratic Tutor vs RAG Tutor Disentanglement" in `docs/trackers/academic_hub_to_do.md`); do not attempt it here.

- [ ] **Step 1: Write `agent/tutor/README.md`**

Cover: purpose (one paragraph), the packet layout (copy the file list from spec §3.1 and the rubric JSON shape from `prep.WORKLIST`), the command table with one example per command, the per-turn loop (`student` → follow `guidance` → `say`), the vault layout, the event types, how to run a prep session (`prep-collect`, agent fills the worklist, `prep-submit`), how to start a live session (`bootstrap` output pasted into Antigravity), and the known limits (soft wall, lexical lint, intent labelling by the agent, `retrieve_passages` needs the free Gemini key for query embeddings). Keep it under 120 lines.

- [ ] **Step 2: Apply the five spec amendments listed in "Spec amendments decided while planning" above**

Edit the named sections of the spec in place; keep each change to one or two sentences.

- [ ] **Step 2b: Add the routing edits**

Read each target first, then make these three small additions (match the surrounding style; do not rename or reword anything else):

1. `academic-rag-model/CLAUDE.md`: add a `## Tutoring sessions` section before `## Multi-agent routing`:

```markdown
## Tutoring sessions

Two different things are both called "tutor" in this repo; do not mix them up.
- **Interactive Socratic tutoring session** (the user says "start a tutoring session", "tutor me on homework N", "office hours"): use `agent/tutor/`. Run `python -m agent.tutor.cli --hub-root <hub> --course <course> --problem-set <ps> bootstrap`, then follow the printed contract on every turn (`student` -> follow `guidance` -> `say`). Never improvise a tutoring session from `rag_agent.py`.
- **One-off lookups and draft diagnosis** (`agent/rag/rag_agent.py` REPL: `/draft`, `/hint`, `/verify`, `/summarize`): the older metered-Gemini RAG Q&A agent. Use it only when the user asks for a quick grounded answer or a rubric check of a draft.
```

2. `docs/AGENT_ROUTING.md`: add one bullet under the Gemini (Antigravity) defaults: live Socratic tutoring sessions run through `agent/tutor` (`bootstrap` prompt); `agent/rag` is for lookups and `/draft` diagnosis.
3. `agent/rag/README.md`: add a one-line note at the top: "Interactive tutoring sessions live in `agent/tutor/`; this package is the RAG Q&A and draft-diagnosis agent."

- [ ] **Step 3: Write the status doc**

Create `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md` with: what shipped, test counts from `pytest tests/agent/tutor -q`, what has **not** been validated (no live Antigravity run yet), and a "What's next" list: (1) real prep + first live HW run on Antigravity, (2) check Antigravity workflow/shell-permission support for the bootstrap, (3) spec §10.1 session modes, (4) spec §10.2 progress tracker. State clearly that the end-to-end live run is the open validation.

- [ ] **Step 4: Run the full landing gate**

```powershell
& $PY -m tools.land_branch check --full
```

Expected: branch clean, rebased on `main`, full suite passes, overlaps reported. Fix anything it reports before continuing.

- [ ] **Step 5: Commit and ask to land**

```powershell
git add agent/tutor/README.md docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md README.md CLAUDE.md agent/rag/README.md
git add ../../docs/AGENT_ROUTING.md
git commit -m "docs(tutor): README, status doc and spec amendments"
```

Then ask the user, in one message, whether to merge and push the head SHA to `main` (branch, SHA, changed paths, check result, overlaps, main checkout `git status --short`, known risks). Do not merge or push without a yes (`docs/WORKTREE_WORKFLOW.md` "Integrate one task at a time").

---

## Self-review

**Spec coverage:** §3.1 prep (Tasks 5, 6; no paid key, embedding only in `cli.py`), §3.2 commands (Tasks 8, 10), §3.3 FSM (Task 2), §4 lint (Task 4), §5 ratings and summary (Tasks 3, 7), §6 persistence/profile (Tasks 1, 7, 8), §7 audit (Task 9), §8 testing incl. HW4 replay (Task 11), §9 integration reuse (Task 6 uses `extract_question`; `retrieve_passages` in Task 10), spec amendments (Task 12). §10 intentionally absent.

**Known soft spots to watch during execution:**
- `Session.student` takes `misconceptions` as `(tag, axis)` pairs everywhere (Tasks 8, 10, 11); a bare string will fail to unpack.
- Lexical lint thresholds (sealed overlap ≥ 2 six-grams, technique lexicon) are tuned on fixtures only; the first real prep run should add false-positive cases to `test_tutor_lint.py`.
- `prep-collect` is not covered by an automated CLI test (needs the embedding client); `prep.collect` itself is covered with an injected `retrieve`.
