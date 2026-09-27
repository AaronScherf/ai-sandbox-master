# Problem-Set Tutor Diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four REPL commands to `rag/rag_agent.py` (`/draft`, `/hint`, `/verify`, `/summarize`) plus a per-course session log, so the tutor can diagnose a student's own attempt against a grounded reference answer, give pre-attempt hints, cross-check answers against an independent model, and summarize a whole problem set's worth of history with a numeric rubric.

**Architecture:** Three new independently-testable modules under `rag/` (`session_log.py`, `problem_set_parser.py`, `tutor_diagnosis.py`), a small refactor of `rag_agent.py`'s existing retrieval and `AnswerResult`, and REPL-only glue in `rag_agent.py`'s `main()` wiring them together. All four new LLM-calling functions mirror `_generate_answer()`'s existing prompt-template-and-`call_with_retries` shape.

**Tech Stack:** Python 3.13, `google-genai` (via `common/gemini_utils.py`), `unittest` (stdlib), JSON Lines for the session log.

**Spec:** `docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md`

## Global Constraints

- Session log lives at `<academic_hub_root>/.session_log/<course>.jsonl`, i.e. `roots[0]/.session_log/<course>.jsonl` (spec §8) — matches `.reports/`/`.viz/`/`.problem_corpus/` placement, not under `academic-rag-model/`.
- Add `**/.session_log/` to the root `.gitignore` (spec §8), alongside the existing `**/.reports/` etc. entries.
- `diagnose_draft()`, `generate_hint()`, `summarize_unit()` use `TUTOR_MODEL` (`"gemini-3.1-flash-lite"`, already defined in `rag_agent.py`) — same cheap tier as the existing `_generate_answer()`. Only `generate_verification()` uses the new `VERIFY_MODEL = "gemini-3.6-flash"` (spec §7).
- `gap_tag` is free text, never a fixed taxonomy (spec §5).
- Rubric scores are integers 0–5 across three dimensions: `correctness`, `rigor`, `course_fit` (spec §5). A malformed/missing rubric line from the model must raise, never silently default to 0 (spec §12).
- `extract_question()` is scoped to fresh, unsolved files only — not the historical `_notes`/`_guided` files (spec §2, §6).
- No auto-adjudication in `/verify` — display both outputs, no third model call judging them (spec §2, §7).
- Session log and gap-tag injection are scoped per-course only, matching `answer_question()`'s existing `course` parameter (spec §2).
- REPL glue in `main()` stays untested by `pytest`, matching this project's existing convention for every other `main()` (spec §12) — verified manually instead.

## Review Focus

- A `diagnose_draft()` response missing or malforming its `CORRECTNESS:`/`RIGOR:`/`COURSE_FIT:`/`GAP_TAG:` lines must raise `DiagnosisParseError`, not silently produce a score of 0 that would corrupt every later `/summarize` average. (Task 4)
- `load_events()` on a course with no session log file yet (first-ever run) must return `[]`, not raise `FileNotFoundError`. (Task 2)
- `/verify` and `/draft` invoked before any question has been asked in the session must print a clear message, not crash on `last_question`/`last_answer` being `None`. (Tasks 10, 12)
- `answer_question()` called with `course=None` (a valid, already-supported call shape) must skip gap-tag injection entirely, not attempt to build a session-log path with no course name. (Task 8)
- `extract_question()` matching question ref `"1"` must not match `"## Question 10"` or a `"10. ..."` numbered item — a naive substring or unanchored-digit match would silently hint the wrong question. (Task 3)

---

## File Structure

- **Modify `rag/rag_agent.py`**: extract `retrieve_passages()` from `answer_question()`; add `passages` field to `AnswerResult`; add gap-tag injection (`_recent_gap_tags()`, `_ANSWER_PROMPT_TEMPLATE`/`_generate_answer()` gain a `gap_tags` block); extend `main()` with `--unit`, session-log writes on every answer, and the four new commands.
- **Create `rag/session_log.py`**: `Event` dataclass, `append_event()`, `load_events()`. Pure JSON I/O.
- **Create `rag/problem_set_parser.py`**: `extract_question()`, `QuestionNotFoundError`. Pure text parsing.
- **Create `rag/tutor_diagnosis.py`**: `Diagnosis` dataclass, `DiagnosisParseError`, `diagnose_draft()`, `generate_hint()`, `VERIFY_MODEL`, `generate_verification()`, `summarize_unit()`, `_rubric_averages_line()`.
- **Modify `tests/test_rag_agent.py`**: tests for `retrieve_passages()`, `AnswerResult.passages`, gap-tag injection.
- **Create `tests/test_session_log.py`**, **`tests/test_problem_set_parser.py`**, **`tests/test_tutor_diagnosis.py`**.
- **Modify root `.gitignore`**: add `**/.session_log/`.

---

### Task 1: Shared retrieval refactor + `AnswerResult.passages`

**Files:**
- Modify: `rag/rag_agent.py:37-52` (`AnswerResult`), `:185-295` (`answer_question()`)
- Test: `tests/test_rag_agent.py`

**Interfaces:**
- Produces: `retrieve_passages(roots: list[str], query: str, client, course: str | None = None, top_k: int = 6, max_per_file: int = 3) -> list[PassageResult]` — public (no leading underscore), importable from `rag.rag_agent`. `AnswerResult.passages: list[PassageResult] | None = None` — populated on the normal Q&A path only (left `None` on the problem-generation path).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rag_agent.py` (new imports needed: add `retrieve_passages` to the existing `from rag.rag_agent import (...)` line):

```python
class TestRetrievePassages(unittest.TestCase):
    def test_calls_search_and_diversifies(self):
        client = MagicMock()
        passages = [_passage(f"aaa-{i:03d}", "aaa") for i in range(5)]
        with patch("rag.rag_agent.search_passages", return_value=passages) as mock_search:
            result = retrieve_passages(["/root"], "q", client, course="math-camp", top_k=6, max_per_file=2)
        mock_search.assert_called_once_with(["/root"], "q", client, course="math-camp", top_k=12)
        self.assertEqual(len(result), 2)  # capped by max_per_file, only one file present


class TestAnswerQuestionPassages(unittest.TestCase):
    def test_passages_populated_on_normal_qa_path(self):
        client = _fake_generate_client("answer")
        passages = [_passage("aaa-000", "aaa")]
        with patch("rag.rag_agent.search_passages", return_value=passages):
            result = answer_question(["/root"], "q", client)
        self.assertEqual(result.passages, passages)

    def test_passages_none_on_problem_generation_path(self):
        client = _fake_generate_client("unused")
        fake_generated = MagicMock(problem_text="Find X.", sources=[])
        with patch("problem_gen.generator.generate_problem", return_value=fake_generated):
            result = answer_question(["/root"], "give me a practice problem on eigenvalues", client)
        self.assertIsNone(result.passages)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rag_agent.py -k "RetrievePassages or AnswerQuestionPassages" -v`
Expected: FAIL — `retrieve_passages` doesn't exist yet / `AnswerResult` has no `passages` attribute.

- [ ] **Step 3: Implement**

In `rag/rag_agent.py`, add `passages` to `AnswerResult` (after the existing `generated_problem` field):

```python
    generated_problem: GeneratedProblem | None = None  # problem_gen.generator.GeneratedProblem --
    # not imported at module level either, same reasoning as visualization above. No
    # import or alias is needed for this to resolve: `from __future__ import annotations`
    # (top of this file) makes every annotation a lazily-evaluated string, exactly like
    # `visualization: VizResult | None` above needs none either.
    passages: list[PassageResult] | None = None  # populated on the normal Q&A path only
    # (rag/tutor_diagnosis.py's diagnose_draft() needs the same passages the reference
    # answer was grounded in) -- left None on the problem-generation path above, where
    # "reference passages" isn't the same concept (generated.sources plays that role
    # there, already surfaced via `citations`).
```

Replace the inlined retrieval in `answer_question()` (currently `passages = search_passages(...); passages = _diversify_by_file(...)`) by adding this new function just above `answer_question()`, right after `_generate_answer()`:

```python
def retrieve_passages(
    roots: list[str], query: str, client,
    course: str | None = None, top_k: int = 6, max_per_file: int = 3,
) -> list[PassageResult]:
    """Retrieval step factored out of answer_question() so /hint
    (rag/tutor_diagnosis.py) can call it directly without duplicating
    the diversify-then-cap logic (spec §3). Renamed without a leading
    underscore since it's now called from another module."""
    passages = search_passages(roots, query, client, course=course, top_k=top_k * 2)
    return _diversify_by_file(passages, max_per_file)[:top_k]
```

In `answer_question()`, replace:

```python
    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]
```

with:

```python
    passages = retrieve_passages(roots, retrieval_query, client, course=course, top_k=top_k, max_per_file=max_per_file)
```

And update the final `return AnswerResult(...)` in the normal Q&A path (the one after `report_path_value = ...`) to include `passages=passages`:

```python
    return AnswerResult(
        answer=answer, citations=citations, history=updated_history,
        visualization=visualization, report_path=report_path_value, passages=passages,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rag_agent.py -v`
Expected: PASS (all existing tests plus the two new classes).

- [ ] **Step 5: Commit**

```bash
git add rag/rag_agent.py tests/test_rag_agent.py
git commit -m "refactor(rag): extract retrieve_passages() and surface passages on AnswerResult"
```

---

### Task 2: Session log module + gitignore

**Files:**
- Create: `rag/session_log.py`
- Test: `tests/test_session_log.py`
- Modify: `.gitignore` (repo root, `C:\Users\theaa\ai-sandbox-master\.gitignore`)

**Interfaces:**
- Consumes: `Citation` from `rag.rag_agent`.
- Produces: `Event` dataclass, `append_event(roots: list[str], event: Event) -> None`, `load_events(roots: list[str], course: str, unit: str | None = None) -> list[Event]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_session_log.py`:

```python
import os
import tempfile
import unittest

from rag.rag_agent import Citation
from rag.session_log import Event, append_event, load_events


def _event(**overrides):
    defaults = dict(
        type="answer", course="microecon", unit="homework_3", question="q",
        text="a", citations=[Citation(chunk_id="c-1", file_id="c", path="c.md", citation="p. 1", root="/root")],
        timestamp="2026-09-27T00:00:00+00:00", gap_tag=None, correctness=None, rigor=None, course_fit=None,
    )
    defaults.update(overrides)
    return Event(**defaults)


class TestLoadEventsMissingFile(unittest.TestCase):
    def test_returns_empty_list_when_no_log_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_events([tmp], "microecon"), [])


class TestAppendAndLoadRoundTrip(unittest.TestCase):
    def test_round_trips_a_single_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event())
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].question, "q")
        self.assertEqual(loaded[0].citations[0].citation, "p. 1")

    def test_appends_do_not_overwrite_prior_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(question="q1"))
            append_event([tmp], _event(question="q2"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual([e.question for e in loaded], ["q1", "q2"])

    def test_unit_filter_excludes_other_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(unit="homework_3", question="q1"))
            append_event([tmp], _event(unit="homework_4", question="q2"))
            loaded = load_events([tmp], "microecon", unit="homework_3")
        self.assertEqual([e.question for e in loaded], ["q1"])

    def test_no_unit_filter_loads_all_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(unit="homework_3"))
            append_event([tmp], _event(unit="homework_4"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 2)

    def test_course_filter_excludes_other_courses(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(course="microecon"))
            append_event([tmp], _event(course="econometrics"))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(len(loaded), 1)

    def test_draft_fields_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            append_event([tmp], _event(type="draft", gap_tag="vacuous-case", correctness=4, rigor=3, course_fit=5))
            loaded = load_events([tmp], "microecon")
        self.assertEqual(loaded[0].gap_tag, "vacuous-case")
        self.assertEqual((loaded[0].correctness, loaded[0].rigor, loaded[0].course_fit), (4, 3, 5))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_session_log.py -v`
Expected: FAIL — `rag.session_log` doesn't exist.

- [ ] **Step 3: Implement**

Create `rag/session_log.py`:

```python
"""
session_log.py
Per-course, append-only log of REPL tutoring events (answer / draft /
hint / verify) -- spec: docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md
§8. Stored as JSON Lines under <academic_hub_root>/.session_log/<course>.jsonl,
matching where .reports/, .viz/, and .problem_corpus/ already live
(rag/report_builder.py's report_path() convention) -- derived,
corpus-grounded content rooted alongside the corpus itself, not under
academic-rag-model/. JSON Lines rather than a single JSON array so each
event is an independent append (open(path, "a")), not a
read-modify-write of the whole file on every action.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

from rag.rag_agent import Citation


@dataclass
class Event:
    type: str              # "answer" | "draft" | "hint" | "verify"
    course: str
    unit: str | None       # e.g. "homework_3"
    question: str
    text: str               # the generated output: answer / diagnosis / hint / verify text
    citations: list[Citation]
    timestamp: str          # ISO 8601
    gap_tag: str | None = None       # set only for type == "draft"
    correctness: int | None = None   # set only for type == "draft"
    rigor: int | None = None         # set only for type == "draft"
    course_fit: int | None = None    # set only for type == "draft"


def _log_path(roots: list[str], course: str) -> str:
    return os.path.join(roots[0], ".session_log", f"{course}.jsonl")


def append_event(roots: list[str], event: Event) -> None:
    path = _log_path(roots, event.course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event)) + "\n")


def load_events(roots: list[str], course: str, unit: str | None = None) -> list[Event]:
    path = _log_path(roots, course)
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            data["citations"] = [Citation(**c) for c in data["citations"]]
            events.append(Event(**data))
    if unit is not None:
        events = [e for e in events if e.unit == unit]
    return events
```

Add to `.gitignore` (repo root), immediately after the existing `**/.problem_corpus/` block (search for that string to find the spot):

```
# Per-course tutoring session log (.session_log/) -- same derivative,
# corpus-grounded-content posture as .reports/, .viz/, and
# .problem_corpus/ above: event text embeds excerpt citations and
# quoted corpus content.
**/.session_log/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_session_log.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/session_log.py tests/test_session_log.py .gitignore
git commit -m "feat(rag): add per-course session log (Event, append_event, load_events)"
```

---

### Task 3: Problem set parser (`extract_question`)

**Files:**
- Create: `rag/problem_set_parser.py`
- Test: `tests/test_problem_set_parser.py`

**Interfaces:**
- Produces: `extract_question(file_path: str, question_ref: str) -> str`, `QuestionNotFoundError(ValueError)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_problem_set_parser.py`:

```python
import tempfile
import os
import unittest

from rag.problem_set_parser import extract_question, QuestionNotFoundError

_HEADING_STYLE = """## Question 1

First question text,
on two lines.

## Question 2

Second question text.

## Question 10

Tenth question text.
"""

_NUMBERED_STYLE = """Some preamble line.

1. First numbered question.

2. Second numbered question,
   also two lines.

10. Tenth numbered question.
"""


def _write(tmp, name, content):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestExtractQuestionHeadingStyle(unittest.TestCase):
    def test_extracts_by_heading_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "2")
        self.assertIn("Second question text.", result)
        self.assertNotIn("Tenth question text.", result)

    def test_multi_line_question_captured_in_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "1")
        self.assertIn("First question text,", result)
        self.assertIn("on two lines.", result)

    def test_ref_does_not_match_prefixed_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            result = extract_question(path, "1")
        self.assertNotIn("Tenth question text.", result)


class TestExtractQuestionNumberedStyle(unittest.TestCase):
    def test_extracts_by_numbered_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _NUMBERED_STYLE)
            result = extract_question(path, "2")
        self.assertIn("Second numbered question,", result)
        self.assertIn("also two lines.", result)
        self.assertNotIn("Tenth numbered question.", result)

    def test_ref_one_does_not_match_ref_ten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _NUMBERED_STYLE)
            result = extract_question(path, "1")
        self.assertIn("First numbered question.", result)
        self.assertNotIn("Tenth numbered question.", result)


class TestExtractQuestionNotFound(unittest.TestCase):
    def test_raises_when_ref_not_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "hw.md", _HEADING_STYLE)
            with self.assertRaises(QuestionNotFoundError):
                extract_question(path, "99")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_problem_set_parser.py -v`
Expected: FAIL — `rag.problem_set_parser` doesn't exist.

- [ ] **Step 3: Implement**

Create `rag/problem_set_parser.py`:

```python
"""
problem_set_parser.py
Extracts a single question's text from a fresh, unsolved problem-set
file, for /hint -- spec: docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md
§6. Scoped to clean files like academic-hub's homework_3.md -- NOT the
historical _notes/_guided files, which mix questions and solutions in
ways this parser isn't built to separate (spec §2).
"""
from __future__ import annotations

import re


class QuestionNotFoundError(ValueError):
    """Raised when question_ref doesn't match any heading or numbered
    item in the file -- surfaced directly rather than guessing, since a
    wrong guess would silently generate a hint for the wrong question."""


_STOP_HEADING = re.compile(r"^##\s+")
_STOP_NUMBERED = re.compile(r"^\d+\.\s+")


def extract_question(file_path: str, question_ref: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ref = re.escape(question_ref)
    heading_pattern = re.compile(rf"^##\s+Question\s+{ref}\b")
    numbered_pattern = re.compile(rf"^{ref}\.\s+")

    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if heading_pattern.match(stripped) or numbered_pattern.match(stripped):
            start = i
            break
    if start is None:
        raise QuestionNotFoundError(f"no question matching {question_ref!r} found in {file_path}")

    # Runs until the next top-level heading or numbered item, whichever
    # comes first -- covers both conventions seen across courses
    # (econometrics uses bare numbered items, microecon uses ## Question
    # N headings), so a numbered item's text doesn't run into a later
    # heading's, or vice versa.
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if _STOP_HEADING.match(stripped) or _STOP_NUMBERED.match(stripped):
            end = i
            break

    return "".join(lines[start:end]).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_problem_set_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/problem_set_parser.py tests/test_problem_set_parser.py
git commit -m "feat(rag): add extract_question() for fresh problem-set files"
```

---

### Task 4: `diagnose_draft()` + grading rubric

**Files:**
- Create: `rag/tutor_diagnosis.py`
- Test: `tests/test_tutor_diagnosis.py`

**Interfaces:**
- Consumes: `TUTOR_MODEL` from `rag.rag_agent`; `PassageResult` from `indexer.index_search`; `call_with_retries` from `common.gemini_utils`.
- Produces: `Diagnosis` dataclass, `DiagnosisParseError(ValueError)`, `diagnose_draft(question: str, reference_answer: str, passages: list[PassageResult], draft: str, client) -> Diagnosis`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tutor_diagnosis.py`:

```python
import unittest
from unittest.mock import MagicMock

from indexer.index_search import PassageResult
from rag.tutor_diagnosis import Diagnosis, DiagnosisParseError, diagnose_draft


def _passage(chunk_id="a-000", file_id="a", text="text", citation="p. 1", root="/root"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="microecon",
        score=1.0, text=text, citation=citation, root=root,
    )


def _fake_client(response_text):
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


_WELL_FORMED = """The attempt correctly states Axiom alpha but never checks the beta case.

CORRECTNESS: 3
RIGOR: 2
COURSE_FIT: 4
GAP_TAG: beta-case-overlooked"""


class TestDiagnoseDraftWellFormed(unittest.TestCase):
    def test_parses_text_and_rubric_scores(self):
        client = _fake_client(_WELL_FORMED)
        diagnosis = diagnose_draft("q", "reference", [_passage()], "my draft", client)
        self.assertIsInstance(diagnosis, Diagnosis)
        self.assertIn("never checks the beta case", diagnosis.text)
        self.assertNotIn("CORRECTNESS", diagnosis.text)
        self.assertEqual(diagnosis.correctness, 3)
        self.assertEqual(diagnosis.rigor, 2)
        self.assertEqual(diagnosis.course_fit, 4)
        self.assertEqual(diagnosis.gap_tag, "beta-case-overlooked")

    def test_uses_tutor_model(self):
        client = _fake_client(_WELL_FORMED)
        diagnose_draft("q", "reference", [_passage()], "my draft", client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_includes_reference_and_draft(self):
        client = _fake_client(_WELL_FORMED)
        diagnose_draft("what is X", "X is Y", [_passage()], "I think X is Z", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("X is Y", prompt)
        self.assertIn("I think X is Z", prompt)
        self.assertIn("what is X", prompt)


class TestDiagnoseDraftMalformed(unittest.TestCase):
    def test_missing_rubric_lines_raises_instead_of_defaulting(self):
        client = _fake_client("Just some prose with no rubric lines at all.")
        with self.assertRaises(DiagnosisParseError):
            diagnose_draft("q", "reference", [_passage()], "draft", client)

    def test_partial_rubric_lines_raises(self):
        client = _fake_client("Some analysis.\n\nCORRECTNESS: 3\nRIGOR: 2")
        with self.assertRaises(DiagnosisParseError):
            diagnose_draft("q", "reference", [_passage()], "draft", client)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tutor_diagnosis.py -v`
Expected: FAIL — `rag.tutor_diagnosis` doesn't exist.

- [ ] **Step 3: Implement**

Create `rag/tutor_diagnosis.py`:

```python
"""
tutor_diagnosis.py
Four LLM-calling functions closing the loop between rag_agent's
grounded Q&A and the student's own problem-set workflow -- spec:
docs/superpowers/specs/2026-09-27-tutor-diagnosis-design.md. Each
mirrors rag_agent._generate_answer()'s existing shape: build a prompt,
call_with_retries, return/parse the result. Kept out of rag_agent.py
for the same isolation reason viz/ and problem_gen/ are their own
packages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from common.gemini_utils import call_with_retries
from indexer.index_search import PassageResult
from rag.rag_agent import TUTOR_MODEL


@dataclass
class Diagnosis:
    text: str          # what the draft covered correctly, what's missing or wrong --
                        # each claim grounded back to the reference answer/excerpts
    gap_tag: str        # short free-text label, e.g. "vacuous-case-overlooked"
    correctness: int    # 0-5
    rigor: int           # 0-5
    course_fit: int      # 0-5


class DiagnosisParseError(ValueError):
    """Raised when a diagnosis response is missing or malforms its
    CORRECTNESS/RIGOR/COURSE_FIT/GAP_TAG lines -- surfaced rather than
    silently defaulting a score to 0, which would corrupt every later
    /summarize rubric average with fabricated data."""


_DIAGNOSIS_PROMPT_TEMPLATE = """You are comparing a student's own attempt at a problem against a \
reference answer grounded in their course materials. Identify what the attempt covers correctly, \
and what's missing, incorrect, or under-justified -- ground each claim you make back to the \
reference answer or the excerpts below, the same way you would cite a source.

Then score the attempt on three 0-5 scales:
- CORRECTNESS: does it reach the right conclusion through valid reasoning?
- RIGOR: is each step justified or proven rather than asserted -- are edge cases and assumptions \
addressed the way the reference does?
- COURSE_FIT: does it use the course's own notation, definitions, and framing (as reflected in the \
excerpts) rather than generic phrasing?

End your response with exactly these four lines, in this order, and nothing after them:
CORRECTNESS: <0-5>
RIGOR: <0-5>
COURSE_FIT: <0-5>
GAP_TAG: <a short kebab-case label for the single most important gap, e.g. vacuous-case-overlooked>

Reference answer:
{reference_answer}

Excerpts the reference answer was grounded in:
{excerpts_block}

Question: {question}

Student's attempt:
{draft}

Diagnosis:"""


_DIAGNOSIS_LINE_PATTERN = re.compile(
    r"CORRECTNESS:\s*(\d+)\s*\n"
    r"RIGOR:\s*(\d+)\s*\n"
    r"COURSE_FIT:\s*(\d+)\s*\n"
    r"GAP_TAG:\s*(.+)",
    re.IGNORECASE,
)


def diagnose_draft(
    question: str, reference_answer: str, passages: list[PassageResult],
    draft: str, client,
) -> Diagnosis:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    prompt = _DIAGNOSIS_PROMPT_TEMPLATE.format(
        reference_answer=reference_answer, excerpts_block=excerpts_block,
        question=question, draft=draft,
    )
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    raw = (response.text or "").strip()
    match = _DIAGNOSIS_LINE_PATTERN.search(raw)
    if match is None:
        raise DiagnosisParseError(
            f"diagnosis response missing CORRECTNESS/RIGOR/COURSE_FIT/GAP_TAG lines: {raw!r}"
        )
    text = raw[:match.start()].strip()
    correctness, rigor, course_fit, gap_tag = match.groups()
    return Diagnosis(
        text=text, gap_tag=gap_tag.strip(),
        correctness=int(correctness), rigor=int(rigor), course_fit=int(course_fit),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tutor_diagnosis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/tutor_diagnosis.py tests/test_tutor_diagnosis.py
git commit -m "feat(rag): add diagnose_draft() with correctness/rigor/course-fit rubric"
```

---

### Task 5: `generate_hint()`

**Files:**
- Modify: `rag/tutor_diagnosis.py`
- Test: `tests/test_tutor_diagnosis.py`

**Interfaces:**
- Produces: `generate_hint(question: str, passages: list[PassageResult], client) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tutor_diagnosis.py` (add `generate_hint` to the existing `from rag.tutor_diagnosis import (...)` line):

```python
class TestGenerateHint(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_client("Think about the Projection Theorem.")
        generate_hint("q", [_passage()], client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_bars_stating_the_final_answer(self):
        client = _fake_client("hint")
        generate_hint("q", [_passage()], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Do NOT state the final answer", prompt)

    def test_prompt_includes_excerpts_and_question(self):
        client = _fake_client("hint")
        generate_hint("what is X", [_passage(text="excerpt content", citation="p. 9")], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("excerpt content", prompt)
        self.assertIn("p. 9", prompt)
        self.assertIn("what is X", prompt)

    def test_returns_stripped_response_text(self):
        client = _fake_client("  a hint with whitespace  \n")
        result = generate_hint("q", [_passage()], client)
        self.assertEqual(result, "a hint with whitespace")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tutor_diagnosis.py -k Hint -v`
Expected: FAIL — `generate_hint` doesn't exist.

- [ ] **Step 3: Implement**

Append to `rag/tutor_diagnosis.py`:

```python
_HINT_PROMPT_TEMPLATE = """A student is about to attempt the question below, using ONLY the excerpts \
from their own course materials given here. Give them a motivating sketch of the right technique or \
theorem to reach for -- enough to get them unstuck and pointed in the right direction.

Do NOT state the final answer, a verdict (e.g. True/False), or a worked derivation. If you find \
yourself about to write out the conclusion, stop and describe the approach instead.

Excerpts:
{excerpts_block}

Question: {question}

Hint:"""


def generate_hint(question: str, passages: list[PassageResult], client) -> str:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    prompt = _HINT_PROMPT_TEMPLATE.format(excerpts_block=excerpts_block, question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tutor_diagnosis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/tutor_diagnosis.py tests/test_tutor_diagnosis.py
git commit -m "feat(rag): add generate_hint() for pre-attempt guidance"
```

---

### Task 6: `generate_verification()` + `VERIFY_MODEL`

**Files:**
- Modify: `rag/tutor_diagnosis.py`
- Test: `tests/test_tutor_diagnosis.py`

**Interfaces:**
- Produces: `VERIFY_MODEL = "gemini-3.6-flash"`, `generate_verification(question: str, client) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tutor_diagnosis.py` (add `generate_verification`, `VERIFY_MODEL` to the imports):

```python
class TestGenerateVerification(unittest.TestCase):
    def test_uses_verify_model_not_tutor_model(self):
        client = _fake_client("An independent solution.")
        generate_verification("q", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], VERIFY_MODEL)
        from rag.rag_agent import TUTOR_MODEL
        self.assertNotEqual(VERIFY_MODEL, TUTOR_MODEL)

    def test_prompt_does_not_assume_a_prior_answer_is_correct(self):
        client = _fake_client("solution")
        generate_verification("q", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Do not assume any prior answer is correct", prompt)

    def test_prompt_contains_only_the_question_no_excerpts_or_prior_answer(self):
        client = _fake_client("solution")
        generate_verification("what is X", client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("what is X", prompt)
        self.assertNotIn("Excerpts", prompt)

    def test_returns_stripped_response_text(self):
        client = _fake_client("  solution text  \n")
        result = generate_verification("q", client)
        self.assertEqual(result, "solution text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tutor_diagnosis.py -k Verification -v`
Expected: FAIL — `generate_verification`/`VERIFY_MODEL` don't exist.

- [ ] **Step 3: Implement**

Append to `rag/tutor_diagnosis.py`:

```python
VERIFY_MODEL = "gemini-3.6-flash"  # this project's existing "stronger" tier (already
# used for textbook conversion and transcription, indexer/index_card.py and
# textbook/convert_textbook.py) -- chosen over TUTOR_MODEL specifically because this
# call exists to catch reasoning errors the cheap tier makes; checking a cheap model's
# output with the same cheap model is weak evidence. Opt-in and per-question, not run
# on every query, so the cost difference doesn't compound the way it would if this
# were the default generation path.

_VERIFY_PROMPT_TEMPLATE = """Solve the following problem yourself, from first principles. Do not \
assume any prior answer is correct -- you have not been shown one. Show your full reasoning.

Question: {question}

Solution:"""


def generate_verification(question: str, client) -> str:
    prompt = _VERIFY_PROMPT_TEMPLATE.format(question=question)
    response = call_with_retries(lambda: client.models.generate_content(
        model=VERIFY_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tutor_diagnosis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add rag/tutor_diagnosis.py tests/test_tutor_diagnosis.py
git commit -m "feat(rag): add generate_verification() as an independent cross-check"
```

---

### Task 7: `summarize_unit()` + rubric averaging

**Files:**
- Modify: `rag/tutor_diagnosis.py`
- Test: `tests/test_tutor_diagnosis.py`

**Interfaces:**
- Consumes: `Event` from `rag.session_log`.
- Produces: `summarize_unit(events: list[Event], client) -> str`, `_rubric_averages_line(events: list[Event]) -> str | None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tutor_diagnosis.py` (add `summarize_unit`, `_rubric_averages_line` to imports; add `from rag.session_log import Event` and `from rag.rag_agent import Citation`):

```python
def _event(**overrides):
    defaults = dict(
        type="answer", course="microecon", unit="homework_3", question="q", text="a",
        citations=[Citation(chunk_id="c", file_id="c", path="c.md", citation="p. 1", root="/root")],
        timestamp="2026-09-27T00:00:00+00:00", gap_tag=None, correctness=None, rigor=None, course_fit=None,
    )
    defaults.update(overrides)
    return Event(**defaults)


class TestRubricAveragesLine(unittest.TestCase):
    def test_none_when_no_draft_events(self):
        events = [_event(type="answer"), _event(type="hint")]
        self.assertIsNone(_rubric_averages_line(events))

    def test_averages_only_draft_events(self):
        events = [
            _event(type="answer"),
            _event(type="draft", correctness=4, rigor=2, course_fit=5),
            _event(type="draft", correctness=2, rigor=4, course_fit=3),
        ]
        line = _rubric_averages_line(events)
        self.assertIn("Correctness 3.0/5", line)
        self.assertIn("Rigor 3.0/5", line)
        self.assertIn("Course-fit 4.0/5", line)
        self.assertIn("2 attempt", line)


class TestSummarizeUnit(unittest.TestCase):
    def test_uses_tutor_model(self):
        client = _fake_client("What we learned...\n\nWhat to focus on...")
        summarize_unit([_event()], client)
        from rag.rag_agent import TUTOR_MODEL
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], TUTOR_MODEL)

    def test_prompt_includes_event_question_and_text(self):
        client = _fake_client("summary")
        summarize_unit([_event(question="what is X", text="X is Y")], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("what is X", prompt)
        self.assertIn("X is Y", prompt)

    def test_appends_rubric_averages_when_draft_events_present(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="draft", correctness=5, rigor=5, course_fit=5)], client)
        self.assertIn("summary text", result)
        self.assertIn("Correctness 5.0/5", result)

    def test_no_rubric_line_when_no_draft_events(self):
        client = _fake_client("summary text")
        result = summarize_unit([_event(type="answer")], client)
        self.assertEqual(result, "summary text")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tutor_diagnosis.py -k "RubricAverages or SummarizeUnit" -v`
Expected: FAIL — `summarize_unit`/`_rubric_averages_line` don't exist.

- [ ] **Step 3: Implement**

Append to `rag/tutor_diagnosis.py` (add `from rag.session_log import Event` to the top-of-file imports):

```python
_SUMMARY_PROMPT_TEMPLATE = """Below is a session's worth of events from a student working through one \
unit of a course (their questions, your grounded answers, their own draft attempts and how those were \
diagnosed, and any independent verifications). Using only this history, write two sections:

## What we learned
Synthesize what the session actually covered, citing sources the same way the events themselves do.

## What to focus on
The recurring gaps and any unresolved discrepancies between a tutor answer and an independent \
verification, prioritized by how often they came up.

Session events:
{events_block}

Summary:"""


def _format_event(event: Event) -> str:
    lines = [f"[{event.type}] Q: {event.question}", event.text]
    if event.gap_tag:
        lines.append(f"(gap tag: {event.gap_tag})")
    if event.citations:
        lines.append("Citations: " + "; ".join(c.citation for c in event.citations))
    return "\n".join(lines)


def _rubric_averages_line(events: list[Event]) -> str | None:
    draft_events = [e for e in events if e.type == "draft"]
    if not draft_events:
        return None
    avg_correctness = sum(e.correctness for e in draft_events) / len(draft_events)
    avg_rigor = sum(e.rigor for e in draft_events) / len(draft_events)
    avg_course_fit = sum(e.course_fit for e in draft_events) / len(draft_events)
    return (
        f"Rubric averages this unit ({len(draft_events)} attempt(s)): "
        f"Correctness {avg_correctness:.1f}/5, Rigor {avg_rigor:.1f}/5, "
        f"Course-fit {avg_course_fit:.1f}/5"
    )


def summarize_unit(events: list[Event], client) -> str:
    events_block = "\n\n---\n\n".join(_format_event(e) for e in events)
    prompt = _SUMMARY_PROMPT_TEMPLATE.format(events_block=events_block)
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    text = (response.text or "").strip()
    stats_line = _rubric_averages_line(events)
    if stats_line:
        text = f"{text}\n\n{stats_line}"
    return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tutor_diagnosis.py -v`
Expected: PASS (whole file, all tasks 4-7 tests together)

- [ ] **Step 5: Commit**

```bash
git add rag/tutor_diagnosis.py tests/test_tutor_diagnosis.py
git commit -m "feat(rag): add summarize_unit() with computed rubric averages"
```

---

### Task 8: Phase 2 -- gap-tag context injection into `answer_question()`

**Files:**
- Modify: `rag/rag_agent.py:153-182` (`_ANSWER_PROMPT_TEMPLATE`/`_generate_answer()`), `:185-295` (`answer_question()`)
- Test: `tests/test_rag_agent.py`

**Interfaces:**
- Consumes: `load_events` from `rag.session_log` (function-scoped import, same isolation pattern as `viz`/`problem_gen`).
- Produces: `_recent_gap_tags(roots: list[str], course: str | None, limit: int = 5) -> list[str]`; `_generate_answer()` gains a `gap_tags: list[str] | None = None` keyword parameter.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rag_agent.py`:

```python
class TestRecentGapTags(unittest.TestCase):
    def test_course_none_returns_empty_without_touching_session_log(self):
        from rag.rag_agent import _recent_gap_tags
        with patch("rag.session_log.load_events") as mock_load:
            result = _recent_gap_tags(["/root"], None)
        self.assertEqual(result, [])
        mock_load.assert_not_called()

    def test_filters_to_draft_events_with_a_gap_tag(self):
        from rag.rag_agent import _recent_gap_tags
        events = [
            MagicMock(type="answer", gap_tag=None),
            MagicMock(type="draft", gap_tag="vacuous-case"),
            MagicMock(type="draft", gap_tag=None),
        ]
        with patch("rag.session_log.load_events", return_value=events):
            result = _recent_gap_tags(["/root"], "microecon")
        self.assertEqual(result, ["vacuous-case"])

    def test_caps_to_limit_most_recent(self):
        from rag.rag_agent import _recent_gap_tags
        events = [MagicMock(type="draft", gap_tag=f"gap-{i}") for i in range(10)]
        with patch("rag.session_log.load_events", return_value=events):
            result = _recent_gap_tags(["/root"], "microecon", limit=3)
        self.assertEqual(result, ["gap-7", "gap-8", "gap-9"])


class TestGenerateAnswerGapTags(unittest.TestCase):
    def test_no_gap_tags_omits_block(self):
        client = _fake_generate_client("answer")
        _generate_answer("q", [], [], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertNotIn("previously struggled", prompt)

    def test_gap_tags_included_in_prompt(self):
        client = _fake_generate_client("answer")
        _generate_answer("q", [], [], client, gap_tags=["vacuous-case", "ties-not-checked"])
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("vacuous-case", prompt)
        self.assertIn("ties-not-checked", prompt)
        self.assertIn("previously struggled", prompt)


class TestAnswerQuestionGapTagInjection(unittest.TestCase):
    def test_course_none_skips_gap_tag_lookup(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("rag.session_log.load_events") as mock_load:
            answer_question(["/root"], "q", client, course=None)
        mock_load.assert_not_called()

    def test_course_set_injects_gap_tags_into_answer_prompt(self):
        client = _fake_generate_client("answer")
        events = [MagicMock(type="draft", gap_tag="vacuous-case")]
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("rag.session_log.load_events", return_value=events):
            answer_question(["/root"], "q", client, course="microecon")
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("vacuous-case", prompt)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rag_agent.py -k "RecentGapTags or GapTags or GapTagInjection" -v`
Expected: FAIL — `_recent_gap_tags` doesn't exist; `_generate_answer` has no `gap_tags` parameter.

- [ ] **Step 3: Implement**

In `rag/rag_agent.py`, add `_recent_gap_tags()` just above `_ANSWER_PROMPT_TEMPLATE`:

```python
def _recent_gap_tags(roots: list[str], course: str | None, limit: int = 5) -> list[str]:
    """Feeds phase 2 of the tutor-diagnosis spec (§10): the last `limit`
    gap tags this student's own /draft diagnoses have logged for this
    course, so a new answer can proactively flag a known blind spot.
    course=None (a valid, already-supported answer_question() call
    shape) returns [] without touching the session log at all -- there's
    no per-course file to read without a course name."""
    if course is None:
        return []
    from rag.session_log import load_events  # function-scoped: keeps session_log's file
    # I/O out of every answer_question() call path that doesn't set course, matching
    # this file's existing function-scoped viz/problem_gen/report_builder imports.
    events = load_events(roots, course)
    tags = [e.gap_tag for e in events if e.type == "draft" and e.gap_tag]
    return tags[-limit:]
```

Update `_ANSWER_PROMPT_TEMPLATE` to add a `{gap_hint_block}` placeholder right after `{history_block}`:

```python
_ANSWER_PROMPT_TEMPLATE = """You are tutoring a student using ONLY the excerpts below, drawn from \
their own course materials. Answer their question clearly and thoroughly, the way a good TA would \
explain it -- but do not introduce any claim, fact, or worked step that isn't supported by the \
excerpts. If the excerpts don't actually contain enough to answer the question, say so plainly \
rather than filling the gap from general knowledge.

When you use something from an excerpt, cite it inline using the citation label given with it \
(e.g. "(§3.7, p. 44)"), so the student can find it in their own materials.
{history_block}{gap_hint_block}
Excerpts:
{excerpts_block}

Question: {question}

Answer:"""
```

Update `_generate_answer()` to build and pass that block:

```python
def _generate_answer(
    question: str, history: list[Turn], passages: list[PassageResult], client,
    gap_tags: list[str] | None = None,
) -> str:
    excerpts_block = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    history_block = ""
    if history:
        recent = "\n".join(f"{t.role}: {t.text}" for t in history[-6:])
        history_block = f"\nRecent conversation, for continuity:\n{recent}\n"
    gap_hint_block = ""
    if gap_tags:
        gap_hint_block = (
            f"\nThe student has previously struggled with: {', '.join(gap_tags)}. "
            "If this question touches any of these, address them explicitly.\n"
        )
    prompt = _ANSWER_PROMPT_TEMPLATE.format(
        history_block=history_block, gap_hint_block=gap_hint_block,
        excerpts_block=excerpts_block, question=question,
    )
    response = call_with_retries(lambda: client.models.generate_content(
        model=TUTOR_MODEL, contents=prompt, config={"temperature": 0.2},
    ))
    return (response.text or "").strip()
```

In `answer_question()`, right before the line `answer = _generate_answer(question, history, passages, client)` (the normal Q&A path, not the problem-generation branch above it), replace it with:

```python
    gap_tags = _recent_gap_tags(roots, course)
    answer = _generate_answer(question, history, passages, client, gap_tags=gap_tags)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rag_agent.py -v`
Expected: PASS (full file, including every pre-existing test -- confirms the new `gap_tags` parameter and prompt placeholder don't break any existing call site).

- [ ] **Step 5: Commit**

```bash
git add rag/rag_agent.py tests/test_rag_agent.py
git commit -m "feat(rag): inject recent gap tags into answer_question()'s prompt"
```

---

### Task 9: REPL `--unit` flag + answer-event logging

**Files:**
- Modify: `rag/rag_agent.py:298-344` (`main()`)

**Interfaces:**
- Consumes: `Event`, `append_event` from `rag.session_log` (function-scoped import inside `main()`).

- [ ] **Step 1: Implement**

Replace `main()` in its entirety:

```python
def main() -> None:
    from datetime import datetime, timezone
    from rag.session_log import Event, append_event
    from rag.tutor_diagnosis import (
        diagnose_draft, generate_hint, generate_verification, summarize_unit,
    )
    from rag.problem_set_parser import extract_question, QuestionNotFoundError

    parser = argparse.ArgumentParser(description="Interactive tutor grounded in one or more indexed corpora.")
    parser.add_argument(
        "--root", action="append", default=None,
        help="Path to a corpus root's own .index/ (repeatable, e.g. --root academic-hub --root "
             "research -- grounds answers in passages from every root given). Default if omitted: "
             "[academic-hub].",
    )
    parser.add_argument("--course", default=None)
    parser.add_argument("--unit", default=None,
                         help="Tags every logged event this session with this unit (e.g. homework_3), "
                              "so /summarize can retrieve just this unit's history.")
    parser.add_argument("--visualize", action="store_true",
                         help="Also generate an interactive visualization for each question's concept.")
    parser.add_argument("--report", action="store_true",
                         help="Also combine the answer, citations, and visualization (if any) into one "
                              "self-contained HTML report.")
    args = parser.parse_args()
    roots = args.root or [os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")]

    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    history: list[Turn] = []
    unit = args.unit
    last_question: str | None = None
    last_answer: str | None = None
    last_passages: list[PassageResult] = []

    print("Ask a question (Ctrl+C to exit).")
    print("Commands: /draft, /hint <file> <question-ref>, /verify, /summarize [unit]")
    while True:
        line = input("> ").strip()
        if not line:
            continue

        question = line
        result = answer_question(
            roots, question, client, history=history, course=args.course,
            visualize=args.visualize, report=args.report,
        )
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.generated_problem:
            print(f"\n--- Solution ---\n{result.generated_problem.solution_text}\n")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        if result.report_path:
            print(f"  report: {result.report_path}")
        print()
        history = result.history
        last_question = question
        last_answer = result.answer
        last_passages = result.passages or []
        if args.course:
            append_event(roots, Event(
                type="answer", course=args.course, unit=unit, question=question, text=result.answer,
                citations=result.citations, timestamp=datetime.now(timezone.utc).isoformat(),
            ))


if __name__ == "__main__":
    main()
```

This step intentionally reproduces the existing normal-question flow unchanged (still handles every question typed, including anything starting with `/` for now -- Tasks 10-13 insert the command branches *before* this fallthrough) plus the two additions: `--unit` parsing and `unit`/`last_question`/`last_answer`/`last_passages` state, and appending an `"answer"` `Event` after every answered question when `--course` is set. `search_passages`'s `PassageResult` is already imported at module level in this file (`from indexer.index_search import PassageResult, search_passages`), so `last_passages: list[PassageResult]` needs no new import.

- [ ] **Step 2: Manually verify**

Run: `python -m rag.rag_agent --course microecon --unit smoke_test` (from `academic-rag-model/`, with `.env`'s `GEMINI_API_KEY` set). Ask one real question, confirm the answer and citations print as before. Exit with Ctrl+C. Then check the log file was written:

Run: `python -c "from rag.session_log import load_events; print(load_events(['../academic-hub'], 'microecon'))"`
Expected: one `Event(type='answer', ...)` printed, with the question you asked and `unit='smoke_test'`.

- [ ] **Step 3: Commit**

```bash
git add rag/rag_agent.py
git commit -m "feat(rag): add --unit flag and answer-event logging to the REPL"
```

---

### Task 10: REPL `/draft` command

**Files:**
- Modify: `rag/rag_agent.py` (`main()`, inside the `while True:` loop from Task 9)

- [ ] **Step 1: Implement**

In `main()`, insert this block immediately after the `if not line: continue` check and *before* the `question = line` fallthrough added in Task 9:

```python
        if line == "/draft":
            if last_answer is None:
                print("Ask a question first, then /draft your attempt at it.\n")
                continue
            print("Paste your attempt (blank line or /end to finish):")
            draft_lines: list[str] = []
            while True:
                draft_line = input()
                if draft_line.strip() in ("", "/end"):
                    break
                draft_lines.append(draft_line)
            draft = "\n".join(draft_lines).strip()
            if not draft:
                print("Empty draft, skipping.\n")
                continue
            diagnosis = diagnose_draft(last_question, last_answer, last_passages, draft, client)
            print(f"\n{diagnosis.text}\n")
            print(
                f"Correctness: {diagnosis.correctness}/5  "
                f"Rigor: {diagnosis.rigor}/5  Course-fit: {diagnosis.course_fit}/5\n"
            )
            if args.course:
                append_event(roots, Event(
                    type="draft", course=args.course, unit=unit, question=last_question,
                    text=diagnosis.text,
                    citations=[
                        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path,
                                 citation=p.citation, root=p.root)
                        for p in last_passages
                    ],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    gap_tag=diagnosis.gap_tag, correctness=diagnosis.correctness,
                    rigor=diagnosis.rigor, course_fit=diagnosis.course_fit,
                ))
            continue

```

- [ ] **Step 2: Manually verify**

Run: `python -m rag.rag_agent --course microecon --unit smoke_test`. Ask a question, then type `/draft`, paste a short (even deliberately wrong or incomplete) attempt, end with a blank line. Confirm the diagnosis text and three scores print. Exit, then run the same `load_events` check as Task 9's Step 2 and confirm a second event with `type='draft'` and non-`None` `gap_tag`/`correctness`/`rigor`/`course_fit` is present.

Also verify the guard: restart the REPL fresh and type `/draft` as the very first input (before asking any question) -- confirm it prints "Ask a question first..." and does not call the model.

- [ ] **Step 3: Commit**

```bash
git add rag/rag_agent.py
git commit -m "feat(rag): add /draft command for reconciling an attempt against the reference"
```

---

### Task 11: REPL `/hint` command

**Files:**
- Modify: `rag/rag_agent.py` (`main()`)

- [ ] **Step 1: Implement**

Insert this block right after the `/draft` block from Task 10 (still before the `question = line` fallthrough):

```python
        if line.startswith("/hint"):
            parts = line.split(maxsplit=2)
            if len(parts) != 3:
                print("Usage: /hint <file> <question-ref>\n")
                continue
            _, file_path, question_ref = parts
            try:
                question_text = extract_question(file_path, question_ref)
            except QuestionNotFoundError as err:
                print(f"{err}\n")
                continue
            hint_passages = retrieve_passages(roots, question_text, client, course=args.course)
            hint = generate_hint(question_text, hint_passages, client)
            print(f"\n{hint}\n")
            for p in hint_passages:
                print(f"  - [{p.root}] {p.path} ({p.citation})")
            print()
            last_question = question_text
            last_answer = None
            last_passages = hint_passages
            if args.course:
                append_event(roots, Event(
                    type="hint", course=args.course, unit=unit, question=question_text, text=hint,
                    citations=[
                        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path,
                                 citation=p.citation, root=p.root)
                        for p in hint_passages
                    ],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))
            continue

```

Note: `last_answer = None` after a hint is deliberate -- a hint is not a reference answer, so `/draft` immediately after a bare `/hint` (with no normal question asked yet) should still hit its "ask a question first" guard from Task 10, not diagnose against a hint that was explicitly barred from stating the answer.

- [ ] **Step 2: Manually verify**

Using `academic-hub/academic_notes/microecon/problem_sets/homework_3.md` (unsolved, real file in this repo): run the REPL and type `/hint ../academic-hub/academic_notes/microecon/problem_sets/homework_3.md 1` (adjust the relative path to wherever you're running from). Confirm a hint prints that does *not* state a final answer/verdict, plus a citation list. Then type `/hint <same file> 99` and confirm it prints the `QuestionNotFoundError` message instead of crashing.

- [ ] **Step 3: Commit**

```bash
git add rag/rag_agent.py
git commit -m "feat(rag): add /hint command for pre-attempt guidance from a problem-set file"
```

---

### Task 12: REPL `/verify` command

**Files:**
- Modify: `rag/rag_agent.py` (`main()`)

- [ ] **Step 1: Implement**

Insert this block right after the `/hint` block from Task 11:

```python
        if line == "/verify":
            if last_question is None:
                print("Ask a question, request a hint, or draft an attempt first.\n")
                continue
            verification = generate_verification(last_question, client)
            shown_answer = last_answer or "(no grounded answer yet -- only a hint/draft exists for this question)"
            print(f"\n--- Tutor's answer ---\n{shown_answer}\n")
            print(f"--- Independent verification ---\n{verification}\n")
            if args.course:
                append_event(roots, Event(
                    type="verify", course=args.course, unit=unit, question=last_question,
                    text=verification, citations=[], timestamp=datetime.now(timezone.utc).isoformat(),
                ))
            continue

```

- [ ] **Step 2: Manually verify**

Ask a question, then type `/verify`. Confirm both the tutor's original answer and an independently-generated solution print, and that they can visibly differ in wording/approach (confirming the verify call isn't just echoing the same prompt). Then restart the REPL fresh and type `/verify` as the first input -- confirm the "ask a question..." guard fires instead of crashing on `last_question is None`.

- [ ] **Step 3: Commit**

```bash
git add rag/rag_agent.py
git commit -m "feat(rag): add /verify command for an independent cross-check"
```

---

### Task 13: REPL `/summarize` command

**Files:**
- Modify: `rag/rag_agent.py` (`main()`)

- [ ] **Step 1: Implement**

Insert this block right after the `/verify` block from Task 12, still before the `question = line` fallthrough:

```python
        if line == "/summarize" or line.startswith("/summarize "):
            if not args.course:
                print("Set --course to use /summarize.\n")
                continue
            parts = line.split(maxsplit=1)
            target_unit = parts[1].strip() if len(parts) == 2 else unit
            events = load_events(roots, args.course, unit=target_unit)
            if not events:
                print(f"No session history yet for unit {target_unit!r}.\n")
                continue
            summary = summarize_unit(events, client)
            print(f"\n{summary}\n")
            continue

```

This also needs `load_events` imported alongside `Event`/`append_event` at the top of `main()` (Task 9 already imports `from rag.session_log import Event, append_event` -- change that line to `from rag.session_log import Event, append_event, load_events`).

- [ ] **Step 2: Manually verify**

After exercising `/draft`, `/hint`, and `/verify` at least once each in a `--unit smoke_test` session (they can be from this or prior tasks' manual runs, since the log persists across REPL restarts), run `/summarize smoke_test`. Confirm it prints a "What we learned" section, a "What to focus on" section, and (since at least one `/draft` was logged) a "Rubric averages" line with real numbers. Then try `/summarize nonexistent_unit` and confirm it prints the "No session history yet" message instead of calling the model with an empty event list.

- [ ] **Step 3: Commit**

```bash
git add rag/rag_agent.py
git commit -m "feat(rag): add /summarize command for a unit-level retrospective"
```

---

## Post-plan cleanup

After Task 13, run the full test suite once to confirm nothing regressed across the whole sequence:

Run: `python -m pytest tests/ -v`
Expected: PASS (every existing test in the project, plus every new test added in Tasks 1-8).
