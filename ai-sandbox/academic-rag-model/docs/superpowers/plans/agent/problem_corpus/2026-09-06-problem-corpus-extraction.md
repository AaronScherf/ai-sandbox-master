# Problem Corpus Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `problem_corpus/`, a new sub-agent that extracts every distinct problem from math-camp's problem-bearing content (problem sets, textbooks, recitation slides) into a structured, persistent JSON corpus — topic tag, problem text, solution text if present (honestly tagged `"student_attempt"`, never `"verified"`), course, and provenance.

**Architecture:** Four focused modules — `boundaries.py` (pure regex-based problem-span detection, duplicated from `indexer/chunk_index.py`'s own proven logic), `llm_extract.py` (one narrow Gemini call per span to structure it), `store.py` (JSON read/write mirroring `indexer/chunk_index.py`'s `.index/chunks/<course>.json` convention), and `extractor.py` (orchestration + its own CLI, iterating indexed cards via `indexer/index_card.py` the same way `chunk_index.chunk()` already does).

**Tech Stack:** Python, `google-genai` (Gemini Developer API, model `gemini-3.1-flash-lite` by default), stdlib `re`/`json`/`hashlib`/`argparse`.

**Spec:** `docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`

## Global Constraints

- No `"verified"` solution provenance anywhere in this codebase — only `"student_attempt"` or `null`. `solution_text`/`solution_provenance` are always both `null` together, or both set together, never independently null.
- `problem_corpus/` depends on `indexer/` for file discovery only (`index_card.list_courses()`, `load_shard()`, `now_iso()`) — never that module's private (`_`-prefixed) internals. `indexer/` gains no new dependency in the other direction.
- Regex patterns for problem-boundary detection and frontmatter-stripping are **duplicated** from `indexer/chunk_index.py`, not imported — same precedent as `rag/report_builder.py`'s duplicated `_slugify`.
- All Gemini calls go through `common.gemini_utils.call_with_retries`; a call that exhausts retries returns `None`, never raises past its caller.
- Scope is math-camp only for now, via a `--course` CLI filter (not hardcoded) — the tool iterates `list_courses()` like `chunk_index.chunk()` does.
- This subproject stops at producing the stored corpus. No wiring into `problem_gen`'s generation prompt, no UI/CLI for browsing records beyond raw JSON inspection.
- Model default: `PROBLEM_CORPUS_GEMINI_MODEL = os.environ.get("PROBLEM_CORPUS_GEMINI_MODEL", "gemini-3.1-flash-lite")`.

---

### Task 1: Package scaffold + boundary detection (`problem_corpus/boundaries.py`)

**Files:**
- Create: `problem_corpus/__init__.py`
- Create: `problem_corpus/boundaries.py`
- Test: `tests/test_boundaries.py`

**Interfaces:**
- Produces: `ProblemSpan` dataclass (`text: str`, `problem_label: str`), `detect_spans(body: str) -> list[ProblemSpan]`. Later tasks (`extractor.py`) call `detect_spans()` and iterate the returned list by index.

- [ ] **Step 1: Create the package**

`problem_corpus/__init__.py` (empty file):

```python
```

- [ ] **Step 2: Write the failing tests**

`tests/test_boundaries.py`:

```python
import unittest

from problem_corpus.boundaries import ProblemSpan, detect_spans


class TestDetectSpans(unittest.TestCase):
    def test_plain_numbered_problems(self):
        # Real convention confirmed live in old_problem_set.md.
        body = (
            "1. For each of the following functions, state...\n\n"
            "2. Consider a production function...\n\n"
            "3. In an economy with n goods...\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")
        self.assertEqual(spans[2].problem_label, "Problem 3")

    def test_bold_practice_problem_convention(self):
        # Real convention confirmed live in Practice Sheet.md.
        body = (
            "**Practice Problem 1. Involutions**\n\nLet V be...\n\n"
            "**Practice Problem 2. Norms**\n\nShow that...\n\n"
            "**Practice Problem 3. Rank**\n\nDetermine...\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")

    def test_points_annotated_problems(self):
        # Real convention confirmed live in old_exam_2021.md.
        body = (
            "1. **(40 points)** Are the following statements true or false?\n\n"
            "2. **(15 points)** Consider the following matrix\n\n"
            "3. **(15 points)**. Consider the following function\n\n"
        )
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)

    def test_question_label_convention(self):
        body = "Question 1\nDoes X hold?\n\nQuestion 2\nDoes Y hold?\n\nQuestion 3\nDoes Z hold?\n\n"
        spans = detect_spans(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")  # label word is always "Problem"

    def test_too_few_matches_returns_empty_list(self):
        # A single accidental match (e.g. one stray "1." in prose) must
        # not be trusted as real document structure -- same bar
        # chunk_index.py's own _detect_problem_boundaries uses.
        body = "Some prose that happens to mention item 1. and nothing else numbered."
        self.assertEqual(detect_spans(body), [])

    def test_no_matches_returns_empty_list(self):
        self.assertEqual(detect_spans("No numbered problems in here."), [])

    def test_span_runs_to_start_of_next_boundary(self):
        body = "1. First problem text here.\n\n2. Second problem text here.\n\n3. Third problem text here.\n\n"
        spans = detect_spans(body)
        self.assertIn("First problem text here.", spans[0].text)
        self.assertNotIn("Second problem", spans[0].text)

    def test_last_span_runs_to_end_of_document(self):
        body = "1. First.\n\n2. Second.\n\n3. Third, running all the way to the end of the document here.\n"
        spans = detect_spans(body)
        self.assertIn("running all the way to the end", spans[-1].text)

    def test_span_text_is_stripped(self):
        body = "1. First.\n\n2. Second.\n\n3. Third.\n\n   \n"
        spans = detect_spans(body)
        self.assertEqual(spans[-1].text, spans[-1].text.strip())

    def test_problem_span_is_a_dataclass_with_text_and_label(self):
        span = ProblemSpan(text="Find X.", problem_label="Problem 1")
        self.assertEqual(span.text, "Find X.")
        self.assertEqual(span.problem_label, "Problem 1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_boundaries -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_corpus.boundaries'`

- [ ] **Step 4: Implement `boundaries.py`**

```python
"""
boundaries.py
Pure, no-I/O detection of per-problem text spans in a file's body (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 3). Regex patterns and the label-extraction logic are
duplicated from indexer/chunk_index.py's _detect_problem_boundaries /
_problem_label_at / _PROBLEM_BOUNDARY_PATTERNS, not imported -- same
precedent as rag/report_builder.py's _slugify (explicitly duplicated
from viz/viz_agent.py rather than imported), so this lower-level,
independently-testable module never reaches into another package's
underscore-prefixed internals for one piece of logic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),
    re.compile(r"(?m)^\*\*Practice Problem \d+"),
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same threshold and reasoning as chunk_index.py's
# own constant -- a weak/sparse match count isn't trusted as real structure.
_PROBLEM_LABEL_RE = re.compile(r"^\**\s*(?:Practice Problem|Problem|Question)?\s*(\d+)", re.IGNORECASE)


@dataclass
class ProblemSpan:
    text: str
    problem_label: str  # e.g. "Problem 1" -- falls back to the bare word
    # "Problem" (no number) if _PROBLEM_LABEL_RE finds no digit near the
    # boundary match, same as chunk_index.py's own _problem_label_at. Not
    # assumed unique within a file (two spans can both fall back to
    # "Problem") -- extractor.py's record-id hash includes the span's
    # index within the file specifically to stay collision-safe when
    # that happens, rather than relying on problem_label alone.


def _problem_label_at(body: str, start: int) -> str:
    first_line = body[start:start + 80].split("\n", 1)[0]
    m = _PROBLEM_LABEL_RE.match(first_line)
    return f"Problem {m.group(1)}" if m else "Problem"


def detect_spans(body: str) -> list[ProblemSpan]:
    """Returns one span per detected problem boundary (that problem's own
    text through the start of the next one, or end of document for the
    last one), or an empty list if fewer than _MIN_PROBLEM_MATCHES
    boundaries are found -- a file whose folder_category qualifies but
    whose content isn't actually numbered problems (e.g. a mini-lecture
    chapter intro) degrades to "nothing extracted here", not an error."""
    starts = set()
    for pattern in _PROBLEM_BOUNDARY_PATTERNS:
        starts.update(m.start() for m in pattern.finditer(body))
    if len(starts) < _MIN_PROBLEM_MATCHES:
        return []

    ordered = sorted(starts)
    spans = []
    for i, start in enumerate(ordered):
        end = ordered[i + 1] if i + 1 < len(ordered) else len(body)
        spans.append(ProblemSpan(text=body[start:end].strip(), problem_label=_problem_label_at(body, start)))
    return spans
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_boundaries -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add problem_corpus/__init__.py problem_corpus/boundaries.py tests/test_boundaries.py
git commit -m "feat(problem_corpus): add pure problem-boundary span detection"
```

---

### Task 2: Structured extraction via Gemini (`problem_corpus/llm_extract.py`)

**Files:**
- Create: `problem_corpus/llm_extract.py`
- Test: `tests/test_llm_extract.py`

**Interfaces:**
- Consumes: `common.gemini_utils.call_with_retries` (existing).
- Produces: `PROBLEM_CORPUS_GEMINI_MODEL: str`, `ExtractedRecord` dataclass (`problem_text: str`, `solution_text: str | None`, `topic_tag: str`), `extract_record(span_text: str, client) -> ExtractedRecord | None`. `extractor.py` (Task 4) calls `extract_record()` once per `ProblemSpan.text`.

- [ ] **Step 1: Write the failing tests**

`tests/test_llm_extract.py`:

```python
import unittest
from unittest.mock import MagicMock, patch

from problem_corpus.llm_extract import (
    PROBLEM_CORPUS_GEMINI_MODEL, ExtractedRecord, _build_extraction_prompt, _parse_response, extract_record,
)


class TestBuildExtractionPrompt(unittest.TestCase):
    def test_includes_the_span_text(self):
        prompt = _build_extraction_prompt("1. Find the eigenvalues of A.")
        self.assertIn("Find the eigenvalues of A.", prompt)

    def test_instructs_none_for_missing_solution(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("NONE", prompt)

    def test_asks_for_three_labeled_sections(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("## Problem", prompt)
        self.assertIn("## Solution", prompt)
        self.assertIn("## Topic", prompt)

    def test_instructs_verbatim_solution_not_a_rewrite(self):
        prompt = _build_extraction_prompt("some span")
        self.assertIn("verbatim", prompt)


class TestParseResponse(unittest.TestCase):
    def test_parses_all_three_sections(self):
        text = "## Problem\nFind X.\n\n## Solution\nX = 1.\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertEqual(result, ExtractedRecord(problem_text="Find X.", solution_text="X = 1.", topic_tag="algebra"))

    def test_none_solution_becomes_python_none(self):
        text = "## Problem\nFind X.\n\n## Solution\nNONE\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertIsNone(result.solution_text)

    def test_none_solution_is_case_insensitive(self):
        text = "## Problem\nFind X.\n\n## Solution\nnone\n\n## Topic\nalgebra"
        result = _parse_response(text)
        self.assertIsNone(result.solution_text)

    def test_case_insensitive_headings(self):
        text = "## problem\nFind X.\n\n## solution\nNONE\n\n## topic\nalgebra"
        result = _parse_response(text)
        self.assertEqual(result.problem_text, "Find X.")

    def test_returns_none_when_topic_section_missing(self):
        self.assertIsNone(_parse_response("## Problem\nFind X.\n\n## Solution\nNONE"))

    def test_returns_none_when_problem_section_empty(self):
        self.assertIsNone(_parse_response("## Problem\n\n## Solution\nNONE\n\n## Topic\nalgebra"))

    def test_returns_none_when_topic_section_empty(self):
        self.assertIsNone(_parse_response("## Problem\nFind X.\n\n## Solution\nNONE\n\n## Topic\n"))

    def test_returns_none_when_no_sections_at_all(self):
        self.assertIsNone(_parse_response("just some prose"))

    def test_sections_are_stripped(self):
        text = "## Problem\n  Find X.  \n\n## Solution\nNONE\n\n## Topic\n  algebra  "
        result = _parse_response(text)
        self.assertEqual(result.problem_text, "Find X.")
        self.assertEqual(result.topic_tag, "algebra")


class TestExtractRecord(unittest.TestCase):
    def test_returns_parsed_record_on_success(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nFind X.\n\n## Solution\nX = 1.\n\n## Topic\nalgebra"
        )
        result = extract_record("1. Find X.", client)
        self.assertEqual(result, ExtractedRecord(problem_text="Find X.", solution_text="X = 1.", topic_tag="algebra"))

    def test_uses_the_configured_model(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nX\n\n## Solution\nNONE\n\n## Topic\nt"
        )
        extract_record("span", client)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], PROBLEM_CORPUS_GEMINI_MODEL)

    def test_passes_the_span_text_through(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(
            text="## Problem\nX\n\n## Solution\nNONE\n\n## Topic\nt"
        )
        extract_record("a very specific span of text", client)
        self.assertIn("a very specific span of text", client.models.generate_content.call_args.kwargs["contents"])

    def test_returns_none_when_call_with_retries_raises(self):
        client = MagicMock()
        with patch("problem_corpus.llm_extract.call_with_retries", side_effect=Exception("quota exceeded")):
            result = extract_record("span", client)
        self.assertIsNone(result)

    def test_returns_none_when_response_does_not_parse(self):
        client = MagicMock()
        client.models.generate_content.return_value = MagicMock(text="not in the expected format")
        result = extract_record("span", client)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_extract -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_corpus.llm_extract'`

- [ ] **Step 3: Implement `llm_extract.py`**

```python
"""
llm_extract.py
One Gemini call per detected problem span, turning its raw text into a
structured record: a cleaned problem statement, the solution verbatim
if one is present (else None), and a short topic tag (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 4). Always Gemini -- unlike problem_gen/llm_gen.py and
viz/llm_fallback.py, there is no local-Ollama backend toggle here: this
only runs as an occasional offline batch tool, not a live per-request
path, so there's no equivalent reliability-vs-latency tradeoff to weigh.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from common.gemini_utils import call_with_retries

PROBLEM_CORPUS_GEMINI_MODEL = os.environ.get("PROBLEM_CORPUS_GEMINI_MODEL", "gemini-3.1-flash-lite")

_EXTRACTION_PROMPT_TEMPLATE = """You are extracting one practice problem from a student's own course materials \
for a structured problem corpus. Below is one detected problem, possibly followed by the student's own worked \
attempt at a solution.

Source text:
{span_text}

Respond in exactly this format, with all three sections present:

## Problem
<the problem statement, cleaned up -- remove any leading label like "Practice Problem 3." or a bare "1.", but \
keep the actual mathematical content verbatim, do not rephrase or simplify it>

## Solution
<the student's worked solution, verbatim, if the source text above actually contains one -- if there is no \
solution attempt in the source text at all, respond with exactly the word NONE for this section and nothing else>

## Topic
<a short, specific topic tag for this problem, e.g. "compactness" or "diagonalizability" -- not a broad subject \
area like "real analysis" or "linear algebra">
"""

_SECTION_PATTERN = re.compile(
    r"##\s*Problem\s*\n(.*?)\n##\s*Solution\s*\n(.*?)\n##\s*Topic\s*\n(.*)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ExtractedRecord:
    problem_text: str
    solution_text: str | None
    topic_tag: str
    # No solution_provenance field here -- the model reports what it
    # found (solution_text or None), and extractor.py derives
    # solution_provenance deterministically when assembling the final
    # stored record ("student_attempt" if solution_text is not None,
    # else None), rather than asking the model to name it. Keeps the
    # "never verified" guarantee independent of model output.


def _build_extraction_prompt(span_text: str) -> str:
    return _EXTRACTION_PROMPT_TEMPLATE.format(span_text=span_text)


def _parse_response(response_text: str) -> ExtractedRecord | None:
    match = _SECTION_PATTERN.search(response_text)
    if match is None:
        return None
    problem_text = match.group(1).strip()
    solution_raw = match.group(2).strip()
    topic_tag = match.group(3).strip()
    if not problem_text or not topic_tag:
        return None
    solution_text = None if solution_raw.upper() == "NONE" else solution_raw
    return ExtractedRecord(problem_text=problem_text, solution_text=solution_text, topic_tag=topic_tag)


def extract_record(span_text: str, client) -> ExtractedRecord | None:
    """One Gemini call via common.gemini_utils.call_with_retries -- returns
    None (not raising) if the call fails after retries or the response
    doesn't parse into the three expected sections. A None here is a
    per-span failure, isolated from the rest of the file by extractor.py."""
    prompt = _build_extraction_prompt(span_text)
    try:
        response = call_with_retries(lambda: client.models.generate_content(
            model=PROBLEM_CORPUS_GEMINI_MODEL, contents=prompt, config={"temperature": 0.1},
        ))
        response_text = (response.text or "").strip()
    except Exception as err:
        print(f"WARNING: Gemini call to model '{PROBLEM_CORPUS_GEMINI_MODEL}' failed after retries ({err})")
        return None
    return _parse_response(response_text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_extract -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add problem_corpus/llm_extract.py tests/test_llm_extract.py
git commit -m "feat(problem_corpus): add Gemini-backed per-span structured extraction"
```

---

### Task 3: Storage (`problem_corpus/store.py`)

**Files:**
- Create: `problem_corpus/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces: `corpus_dir(academic_hub_root: str) -> str`, `corpus_path(academic_hub_root: str, course: str) -> str`, `load_records(academic_hub_root: str, course: str) -> list[dict]`, `save_file_records(academic_hub_root: str, course: str, file_id: str, records: list[dict]) -> None`. `extractor.py` (Task 4) calls all four.
- Record dict shape (produced by `extractor.py`, stored as-is): `{"id", "course", "topic_tag", "problem_text", "solution_text", "solution_provenance", "source": {"file_id", "path", "root", "citation", "folder_category"}, "content_hash", "extracted_at"}`. `save_file_records()` reads `record["source"]["file_id"]` to key its upsert.

- [ ] **Step 1: Write the failing tests**

`tests/test_store.py`:

```python
import os
import tempfile
import unittest

from problem_corpus.store import corpus_dir, corpus_path, load_records, save_file_records


def _record(file_id, record_id, topic="algebra"):
    return {
        "id": record_id, "course": "math-camp", "topic_tag": topic,
        "problem_text": "Find X.", "solution_text": None, "solution_provenance": None,
        "source": {
            "file_id": file_id, "path": "a.md", "root": "/x", "citation": "a.md, Problem 1",
            "folder_category": "problem_sets",
        },
        "content_hash": "h1", "extracted_at": "2026-09-06T00:00:00+00:00",
    }


class TestCorpusPaths(unittest.TestCase):
    def test_corpus_dir_lives_under_problem_corpus(self):
        self.assertEqual(corpus_dir("/root"), os.path.join("/root", ".problem_corpus"))

    def test_corpus_path_is_course_scoped_json(self):
        path = corpus_path("/root", "math-camp")
        self.assertEqual(path, os.path.join("/root", ".problem_corpus", "math-camp.json"))


class TestLoadRecords(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_records(tmp, "math-camp"), [])


class TestSaveFileRecords(unittest.TestCase):
    def test_round_trips_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            records = load_records(tmp, "math-camp")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["id"], "id1")
            self.assertEqual(records[0]["topic_tag"], "algebra")

    def test_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            self.assertTrue(os.path.exists(corpus_path(tmp, "math-camp")))

    def test_replaces_only_the_target_files_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "math-camp", "bbb", [_record("bbb", "id2")])
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id3")])
            ids = {r["id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(ids, {"id2", "id3"})  # id1 was replaced by id3; id2 untouched

    def test_empty_records_list_removes_the_files_prior_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "math-camp", "aaa", [])
            self.assertEqual(load_records(tmp, "math-camp"), [])

    def test_other_courses_are_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "econ-101", "bbb", [_record("bbb", "id2")])
            self.assertEqual(len(load_records(tmp, "math-camp")), 1)
            self.assertEqual(len(load_records(tmp, "econ-101")), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_store -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_corpus.store'`

- [ ] **Step 3: Implement `store.py`**

```python
"""
store.py
Read/write for the extracted problem corpus at
<academic_hub_root>/.problem_corpus/<course>.json -- mirrors
indexer/chunk_index.py's .index/chunks/<course>.json convention exactly
(spec: docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 5).
"""
from __future__ import annotations

import json
import os


def corpus_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".problem_corpus")


def corpus_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(corpus_dir(academic_hub_root), f"{course}.json")


def load_records(academic_hub_root: str, course: str) -> list[dict]:
    path = corpus_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_file_records(academic_hub_root: str, course: str, file_id: str, records: list[dict]) -> None:
    """Atomically replaces every existing record for this file_id with
    `records` (upsert-by-file_id, not upsert-by-record-id) -- loads the
    course's full record list, drops anything already tagged with this
    file_id, appends the new set, writes the whole file back. One file's
    re-extraction never touches another file's already-stored records."""
    existing = load_records(academic_hub_root, course)
    remaining = [r for r in existing if r["source"]["file_id"] != file_id]
    path = corpus_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(remaining + records, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_store -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add problem_corpus/store.py tests/test_store.py
git commit -m "feat(problem_corpus): add per-file-atomic JSON corpus storage"
```

---

### Task 4: Orchestration & CLI (`problem_corpus/extractor.py`)

**Files:**
- Create: `problem_corpus/extractor.py`
- Test: `tests/test_extractor.py`

**Interfaces:**
- Consumes: `indexer.index_card.list_courses(academic_hub_root) -> list[str]`, `indexer.index_card.load_shard(academic_hub_root, course) -> list[dict]`, `indexer.index_card.now_iso() -> str` (all existing, public); `problem_corpus.boundaries.detect_spans(body: str) -> list[ProblemSpan]` (Task 1); `problem_corpus.llm_extract.extract_record(span_text: str, client) -> ExtractedRecord | None` (Task 2); `problem_corpus.store.load_records`/`save_file_records` (Task 3).
- Produces: `extract_problems(academic_hub_root: str, client, course: str | None = None, file: str | None = None, dry_run: bool = False) -> dict` (the public entry point), `build_arg_parser() -> argparse.ArgumentParser`, `main() -> None`.

**Real interface note:** a real card dict has `file_id`, `path` (forward-slash-separated, relative to `academic_hub_root`), `course`, `doc_type`, `content_hash`, `embedding`, `orphaned`, `needs_indexing` keys — **no `folder_category` key**; it's derived from `path` (same as `indexer/chunk_index.py`'s own `_folder_category_from_path`, duplicated here per this package's module-boundary convention).

- [ ] **Step 1: Write the failing tests**

`tests/test_extractor.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from indexer.index_card import save_shard

from problem_corpus.extractor import (
    _extract_file, _folder_category_from_path, _record_id, build_arg_parser,
    extract_problems, _single_root, _DEFAULT_ROOT,
)
from problem_corpus.llm_extract import ExtractedRecord
from problem_corpus.store import load_records


def _write_md(tmp, rel_path, content):
    full_path = os.path.join(tmp, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


_PROBLEM_SET_MD = "academic_notes/math-camp/problem_sets/processed_outputs/set.md"
_MISSING_MD = "academic_notes/math-camp/problem_sets/processed_outputs/missing.md"
_TEXTBOOK_MD = "academic_resources/math-camp/textbooks/processed_outputs/book.md"
_NOTES_MD = "academic_notes/math-camp/ta_notes/processed_outputs/notes.md"

_THREE_PROBLEMS = (
    "1. Find the eigenvalues of A.\n\n"
    "2. Prove the set is compact.\n\n"
    "3. Show the sequence converges.\n\n"
)

_TWO_PROBLEMS_ONLY = "1. Find X.\n\n2. Find Y.\n\n"  # below _MIN_PROBLEM_MATCHES -- no spans detected


def _make_card(file_id, path, content_hash="h1"):
    # No folder_category key -- real cards don't have one; extractor.py
    # derives it from `path` via _folder_category_from_path().
    return {
        "file_id": file_id, "path": path, "course": "math-camp",
        "doc_type": "problem_set", "content_hash": content_hash, "embedding": [0.1],
        "orphaned": False, "needs_indexing": False,
    }


def _fake_client():
    """A Gemini client stand-in isn't used directly by these tests --
    extract_record() itself is mocked (per this project's established
    network-call-mocked-only convention) -- but _extract_file/
    extract_problems still take a `client` positional argument, so a
    plain placeholder is enough."""
    return MagicMock()


class TestFolderCategoryFromPath(unittest.TestCase):
    def test_problem_sets_path(self):
        self.assertEqual(_folder_category_from_path(_PROBLEM_SET_MD), "problem_sets")

    def test_textbook_path(self):
        self.assertEqual(_folder_category_from_path(_TEXTBOOK_MD), "textbooks")

    def test_path_with_no_processed_outputs_segment_returns_empty_string(self):
        self.assertEqual(_folder_category_from_path("some/other/path.md"), "")


class TestRecordId(unittest.TestCase):
    def test_same_inputs_produce_same_id(self):
        self.assertEqual(_record_id("aaa", 0, "Problem 1"), _record_id("aaa", 0, "Problem 1"))

    def test_different_span_index_produces_different_id(self):
        # Collision-safety for two spans that both fall back to the bare
        # label "Problem" (no number) -- span index disambiguates them.
        self.assertNotEqual(_record_id("aaa", 0, "Problem"), _record_id("aaa", 1, "Problem"))

    def test_different_file_id_produces_different_id(self):
        self.assertNotEqual(_record_id("aaa", 0, "Problem 1"), _record_id("bbb", 0, "Problem 1"))


class TestExtractFile(unittest.TestCase):
    def test_extracts_every_span_in_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            responses = [
                ExtractedRecord(problem_text="Find the eigenvalues of A.", solution_text=None, topic_tag="eigenvalues"),
                ExtractedRecord(problem_text="Prove the set is compact.", solution_text="Proof.", topic_tag="compactness"),
                ExtractedRecord(problem_text="Show the sequence converges.", solution_text=None, topic_tag="convergence"),
            ]
            with patch("problem_corpus.extractor.extract_record", side_effect=responses):
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "extracted", "problems_extracted": 3})
            records = load_records(tmp, "math-camp")
            self.assertEqual(len(records), 3)
            self.assertEqual(records[1]["solution_text"], "Proof.")
            self.assertEqual(records[1]["solution_provenance"], "student_attempt")
            self.assertIsNone(records[0]["solution_provenance"])

    def test_solution_and_provenance_are_both_null_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
            records = load_records(tmp, "math-camp")
            for r in records:
                self.assertIsNone(r["solution_text"])
                self.assertIsNone(r["solution_provenance"])

    def test_record_source_fields_are_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
            record = load_records(tmp, "math-camp")[0]
            self.assertEqual(record["source"]["file_id"], "aaa")
            self.assertEqual(record["source"]["path"], _PROBLEM_SET_MD)
            self.assertEqual(record["source"]["root"], tmp)
            self.assertEqual(record["source"]["folder_category"], "problem_sets")
            self.assertIn("set.md", record["source"]["citation"])
            self.assertIn("Problem 1", record["source"]["citation"])
            self.assertEqual(record["content_hash"], "h1")
            self.assertEqual(record["course"], "math-camp")

    def test_unchanged_content_hash_is_skipped_without_calling_gemini(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                _extract_file(tmp, "math-camp", card, _fake_client())
                mock_extract.reset_mock()
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "unchanged"})
            mock_extract.assert_not_called()

    def test_stale_content_hash_re_extracts_and_replaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                _extract_file(tmp, "math-camp", card, _fake_client())
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(_THREE_PROBLEMS + "\n4. A fourth problem.\n\n")
                card["content_hash"] = "h2"
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result["status"], "extracted")
            records = load_records(tmp, "math-camp")
            self.assertTrue(all(r["content_hash"] == "h2" for r in records))

    def test_zero_spans_detected_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _TWO_PROBLEMS_ONLY)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "skipped_no_problems"})
            self.assertEqual(load_records(tmp, "math-camp"), [])

    def test_one_failed_span_does_not_drop_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            responses = [
                ExtractedRecord(problem_text="Find the eigenvalues of A.", solution_text=None, topic_tag="eigenvalues"),
                None,  # this span's extraction failed
                ExtractedRecord(problem_text="Show the sequence converges.", solution_text=None, topic_tag="convergence"),
            ]
            with patch("problem_corpus.extractor.extract_record", side_effect=responses):
                result = _extract_file(tmp, "math-camp", card, _fake_client())
            self.assertEqual(result, {"status": "extracted", "problems_extracted": 2})
            self.assertEqual(len(load_records(tmp, "math-camp")), 2)

    def test_frontmatter_is_stripped_before_boundary_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = "---\nsource_pdf: set.pdf\ntags: [algebra]\n---\n\n" + _THREE_PROBLEMS
            _write_md(tmp, _PROBLEM_SET_MD, content)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                _extract_file(tmp, "math-camp", card, _fake_client())
            first_span_arg = mock_extract.call_args_list[0].args[0]
            self.assertNotIn("source_pdf", first_span_arg)


class TestExtractProblems(unittest.TestCase):
    def test_extracts_every_problem_bearing_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(stats["problems_extracted"], 3)

    def test_non_problem_bearing_folder_category_is_skipped_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _NOTES_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _NOTES_MD)])
            with patch("problem_corpus.extractor.extract_record") as mock_extract:
                stats = extract_problems(tmp, _fake_client())
            mock_extract.assert_not_called()
            self.assertEqual(stats["extracted"], 0)

    def test_orphaned_cards_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            card["orphaned"] = True
            save_shard(tmp, "math-camp", [card])
            stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 0)
            self.assertEqual(stats["unchanged"], 0)
            self.assertEqual(stats["skipped_no_problems"], 0)

    def test_needs_indexing_cards_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            card = _make_card("aaa", _PROBLEM_SET_MD)
            card["needs_indexing"] = True
            save_shard(tmp, "math-camp", [card])
            stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 0)

    def test_second_run_with_no_changes_reports_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted) as mock_extract:
                extract_problems(tmp, _fake_client())
                mock_extract.reset_mock()
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["unchanged"], 1)
            self.assertEqual(stats["extracted"], 0)
            mock_extract.assert_not_called()

    def test_one_file_failure_does_not_abort_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            # _MISSING_MD deliberately not written -- _extract_file will
            # fail to open it.
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _PROBLEM_SET_MD), _make_card("bbb", _MISSING_MD),
            ])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client())
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(stats["failed"], 1)
            file_ids = {r["source"]["file_id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})

    def test_dry_run_calls_no_gemini_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            with patch("problem_corpus.extractor.extract_record") as mock_extract:
                stats = extract_problems(tmp, _fake_client(), dry_run=True)
            mock_extract.assert_not_called()
            self.assertEqual(load_records(tmp, "math-camp"), [])
            self.assertEqual(stats["extracted"], 1)  # reports what WOULD be extracted

    def test_scoped_to_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            other_md = "academic_notes/econ-101/problem_sets/processed_outputs/set.md"
            _write_md(tmp, other_md, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [_make_card("aaa", _PROBLEM_SET_MD)])
            save_shard(tmp, "econ-101", [_make_card("bbb", other_md)])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client(), course="math-camp")
            self.assertEqual(stats["extracted"], 1)
            self.assertEqual(load_records(tmp, "econ-101"), [])

    def test_scoped_to_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_md(tmp, _PROBLEM_SET_MD, _THREE_PROBLEMS)
            other_md = "academic_notes/math-camp/problem_sets/processed_outputs/other.md"
            _write_md(tmp, other_md, _THREE_PROBLEMS)
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _PROBLEM_SET_MD), _make_card("bbb", other_md),
            ])
            extracted = ExtractedRecord(problem_text="p", solution_text=None, topic_tag="t")
            with patch("problem_corpus.extractor.extract_record", return_value=extracted):
                stats = extract_problems(tmp, _fake_client(), file="set.md")
            self.assertEqual(stats["extracted"], 1)
            file_ids = {r["source"]["file_id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})


class TestBuildArgParser(unittest.TestCase):
    def test_extract_subcommand_defaults(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertEqual(args.command, "extract")
        self.assertIsNone(args.course)
        self.assertIsNone(args.file)
        self.assertFalse(args.dry_run)

    def test_extract_subcommand_with_flags(self):
        args = build_arg_parser().parse_args(["extract", "--course", "math-camp", "--file", "a.md", "--dry-run"])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.file, "a.md")
        self.assertTrue(args.dry_run)

    def test_root_defaults_to_none_when_omitted(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertIsNone(args.root)

    def test_root_is_repeatable_at_parse_time(self):
        args = build_arg_parser().parse_args(["--root", "a", "--root", "b", "extract"])
        self.assertEqual(args.root, ["a", "b"])


class TestSingleRoot(unittest.TestCase):
    def test_defaults_when_no_root_given(self):
        args = build_arg_parser().parse_args(["extract"])
        self.assertEqual(_single_root(args), _DEFAULT_ROOT)

    def test_returns_the_one_given_root(self):
        args = build_arg_parser().parse_args(["--root", "/x", "extract"])
        self.assertEqual(_single_root(args), "/x")

    def test_raises_on_more_than_one_root(self):
        args = build_arg_parser().parse_args(["--root", "/x", "--root", "/y", "extract"])
        with self.assertRaises(SystemExit):
            _single_root(args)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_extractor -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_corpus.extractor'`

- [ ] **Step 3: Implement `extractor.py`**

```python
"""
extractor.py
Orchestration and CLI for the problem corpus extraction tool (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 6). Iterates indexed cards via indexer/index_card.py (the same
public interface indexer/chunk_index.py's chunk() already uses for its
own per-file iteration) -- never that or any other module's private
internals. Own standalone CLI entry point, mirroring viz/viz_agent.py's
and rag/rag_agent.py's own argparse-based main(), rather than a new
index_search.py subcommand: extraction is a problem_gen-adjacent
subproject that depends on the indexer, not an indexer-internal
operation (indexer/ gains no new dependency in the other direction).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re

from common.gemini_utils import get_gemini_client, load_dotenv_override
from indexer.index_card import list_courses, load_shard, now_iso
from problem_corpus.boundaries import detect_spans
from problem_corpus.llm_extract import extract_record
from problem_corpus.store import load_records, save_file_records

_PROBLEM_BEARING_FOLDER_CATEGORIES = ("problem_sets", "textbooks", "recitation_slides")

# Duplicated from indexer/chunk_index.py's own _FRONTMATTER_RE, per this
# package's module-boundary convention (see boundaries.py's own docstring).
_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.DOTALL)

_DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "academic-hub")


def _folder_category_from_path(path: str) -> str:
    """Duplicated from indexer/chunk_index.py's own private helper of the
    same name -- card paths are always stored with "/" separators
    regardless of OS (matching that function's own assumption)."""
    parts = path.split("/")
    if "processed_outputs" not in parts:
        return ""
    idx = parts.index("processed_outputs")
    return parts[idx - 1] if idx >= 1 else ""


def _record_id(file_id: str, span_index: int, problem_label: str) -> str:
    """Truncated SHA-256 of file_id + the span's own index within the
    file + its label -- the span index keeps this collision-safe even
    when two spans in the same file both fall back to the bare label
    "Problem" (see boundaries.ProblemSpan's own docstring)."""
    joined = f"{file_id}:{span_index}:{problem_label}"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _extract_file(academic_hub_root: str, course: str, card: dict, client) -> dict:
    """Extracts every problem in one file, mirroring
    chunk_index.generate_chunks_for_file()'s content-hash-based
    idempotency and per-file atomicity. Returns {"status": "unchanged"}
    if this file's content_hash already matches its stored records,
    {"status": "skipped_no_problems"} if zero spans are detected, or
    {"status": "extracted", "problems_extracted": N} otherwise. Per span,
    a None from llm_extract.extract_record() is skipped (logged as a
    WARNING) without aborting the rest of the file."""
    file_id = card["file_id"]
    existing = load_records(academic_hub_root, course)
    current_for_file = [r for r in existing if r["source"]["file_id"] == file_id]
    if current_for_file and all(r["content_hash"] == card["content_hash"] for r in current_for_file):
        return {"status": "unchanged"}

    md_path = os.path.join(academic_hub_root, card["path"])
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    body = _FRONTMATTER_RE.sub("", text, count=1)

    spans = detect_spans(body)
    if not spans:
        return {"status": "skipped_no_problems"}

    folder_category = _folder_category_from_path(card["path"])
    new_records = []
    for i, span in enumerate(spans):
        extracted = extract_record(span.text, client)
        if extracted is None:
            print(f"WARNING: extraction failed for {card['path']} ({span.problem_label}); skipping this problem.")
            continue
        solution_provenance = "student_attempt" if extracted.solution_text is not None else None
        new_records.append({
            "id": _record_id(file_id, i, span.problem_label),
            "course": course,
            "topic_tag": extracted.topic_tag,
            "problem_text": extracted.problem_text,
            "solution_text": extracted.solution_text,
            "solution_provenance": solution_provenance,
            "source": {
                "file_id": file_id,
                "path": card["path"],
                "root": academic_hub_root,
                "citation": f"{os.path.basename(card['path'])}, {span.problem_label}",
                "folder_category": folder_category,
            },
            "content_hash": card["content_hash"],
            "extracted_at": now_iso(),
        })

    save_file_records(academic_hub_root, course, file_id, new_records)
    return {"status": "extracted", "problems_extracted": len(new_records)}


def extract_problems(
    academic_hub_root: str, client, course: str | None = None,
    file: str | None = None, dry_run: bool = False,
) -> dict:
    """Iterates every non-orphaned, non-needs_indexing card across the
    given course (or every course via list_courses() if course is None)
    whose folder_category is problem-bearing. A file-level exception
    (unreadable file, bad frontmatter) is caught, logged as a WARNING
    with a rerun hint, and processing continues to the next file --
    never aborts the whole run. dry_run reports what WOULD be
    (re-)extracted (by the same content_hash comparison _extract_file
    uses) without calling Gemini or writing anything."""
    stats = {"extracted": 0, "unchanged": 0, "skipped_no_problems": 0, "failed": 0, "problems_extracted": 0}

    for course_name in list_courses(academic_hub_root):
        if course is not None and course_name != course:
            continue
        for card in load_shard(academic_hub_root, course_name):
            if card.get("orphaned") or card.get("needs_indexing"):
                continue
            folder_category = _folder_category_from_path(card["path"])
            if folder_category not in _PROBLEM_BEARING_FOLDER_CATEGORIES:
                continue
            if file is not None and not card["path"].endswith(file):
                continue

            if dry_run:
                existing = load_records(academic_hub_root, course_name)
                current = [r for r in existing if r["source"]["file_id"] == card["file_id"]]
                if current and all(r["content_hash"] == card["content_hash"] for r in current):
                    stats["unchanged"] += 1
                else:
                    stats["extracted"] += 1
                continue

            try:
                result = _extract_file(academic_hub_root, course_name, card, client)
            except Exception as err:
                print(f"WARNING: extraction failed for {card['path']} ({err}); "
                      f"rerun `python -m problem_corpus.extractor extract` later to retry.")
                stats["failed"] += 1
                continue

            if result["status"] == "unchanged":
                stats["unchanged"] += 1
            elif result["status"] == "skipped_no_problems":
                stats["skipped_no_problems"] += 1
            else:
                stats["extracted"] += 1
                stats["problems_extracted"] += result["problems_extracted"]

    return stats


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract a structured problem corpus from indexed course content.")
    parser.add_argument(
        "--root", action="append", default=None,
        help=f"Path to a corpus root's own .index/ (default: {_DEFAULT_ROOT}). Exactly one root.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract_p = subparsers.add_parser("extract", help="Extract problems into .problem_corpus/<course>.json.")
    extract_p.add_argument("--course", default=None)
    extract_p.add_argument("--file", default=None)
    extract_p.add_argument("--dry-run", action="store_true")
    return parser


def _single_root(args) -> str:
    """extract is a per-corpus maintenance operation, not query-time
    federation -- it writes into exactly one root's own .problem_corpus/,
    so more than one --root is a usage error, matching
    indexer/index_search.py's own _single_root for the same reason."""
    roots = args.root or [_DEFAULT_ROOT]
    if len(roots) > 1:
        raise SystemExit(
            f"'{args.command}' operates on one corpus root at a time, got {len(roots)} "
            f"(--root {', '.join(roots)}). Pass exactly one --root."
        )
    return roots[0]


def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "extract":
        stats = extract_problems(
            _single_root(args), client, course=args.course, file=args.file, dry_run=args.dry_run,
        )
        print(stats)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_extractor -v`
Expected: all tests PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests`
Expected: all tests PASS (no existing test touched any of these new files, so this should be a pure addition)

- [ ] **Step 6: Commit**

```bash
git add problem_corpus/extractor.py tests/test_extractor.py
git commit -m "feat(problem_corpus): add extraction orchestration and CLI"
```

---

### Task 5: Documentation & IP policy

**Files:**
- Create: `problem_corpus/README.md`
- Modify: `README.md` (root, subproject list + Requirements section)
- Modify: `../.gitignore` (the ai-sandbox-master repo root, **not** `academic-rag-model/.gitignore` — this is where `.index/`, `.viz/`, `.reports/` are actually gitignored, since `.problem_corpus/` lives under the sibling `academic-hub/` directory, outside this repo's own root)

**Interfaces:** None — this task is documentation and config only, no code.

- [ ] **Step 1: Add the `.problem_corpus/` gitignore entry**

Open `../.gitignore` (relative to `academic-rag-model/` — i.e. the `ai-sandbox-master` repo root) and find this existing block (search for `**/.reports/`):

```
# Combined-report output (.reports/) is the same kind of derivative,
# corpus-grounded generated content as .viz/ -- same IP posture, same
# any-root coverage rationale.
**/.reports/
```

Add immediately after it:

```
# Extracted problem corpus (.problem_corpus/) contains problem text
# pulled directly from the corpus (textbooks, problem sets) -- closer to
# .index/chunks/'s "direct reproduction of copyrighted material" concern
# than .viz/'s generated charts, and gitignored for that same reason.
**/.problem_corpus/
```

- [ ] **Step 2: Verify the gitignore change**

Run (from `academic-rag-model/`): `cd .. && git check-ignore -v academic-hub/.problem_corpus/math-camp.json`
Expected: prints a match against the new `**/.problem_corpus/` line (confirms the pattern actually matches before relying on it)

- [ ] **Step 3: Write `problem_corpus/README.md`**

```markdown
# Problem Corpus Extraction

Extracts a structured, persistent corpus of practice problems (topic
tag, problem text, solution text if present, course, provenance) from
math-camp's own problem sets, textbooks, and recitation slides. First
of six future-development ideas flagged in
[`../docs/status/2026-09-05-problem-generation-status.md`](../docs/status/2026-09-05-problem-generation-status.md)'s
"Future development ideas" section — the one everything else there
depends on.

**No `"verified"` solutions here.** Inspecting the actual corpus found
no answer-key tier at all: textbook exercises have no solutions in the
converted text, and problem sets are either solution-less or carry the
student's own worked attempt under an explicit `### Handwritten
Solutions:` heading — unverified, possibly wrong. Every extracted
record's `solution_provenance` is either `"student_attempt"` or
`null`, never `"verified"`.

**This subproject stops at producing the stored corpus.** Wiring it
into `problem_gen`'s generation prompt or any direct-serve matching is
a separate, later idea — see the status doc above.

Run directly:

```powershell
python -m problem_corpus.extractor --root ../academic-hub extract --course math-camp
python -m problem_corpus.extractor --root ../academic-hub extract --dry-run
```

Uses the same `GEMINI_API_KEY` this project already requires for
retrieval — no extra setup. One Gemini call (`gemini-3.1-flash-lite` by
default, override with `PROBLEM_CORPUS_GEMINI_MODEL`) per detected
problem span.

## Key files

- `extractor.py` — the one public entry point, `extract_problems()`,
  plus this subproject's own CLI (`main()`). Iterates indexed cards via
  [`../indexer/`](../indexer/)'s `index_card.load_shard()`/
  `list_courses()` — the same public interface
  `indexer/chunk_index.py`'s own `chunk()` already uses — filtered to
  problem-bearing folder categories (`problem_sets`, `textbooks`,
  `recitation_slides`). Content-hash-based incremental extraction: an
  unchanged file since its last run costs nothing (no re-read, no
  Gemini call), mirroring `chunk_index.py`'s own idempotency. Failure
  is isolated at both file granularity (one unreadable file doesn't
  stop the rest of a run) and per-problem granularity (one failed
  extraction within an otherwise-fine file doesn't drop its other
  problems).
- `boundaries.py` — pure, no-I/O detection of per-problem text spans.
  Regex patterns duplicated from `indexer/chunk_index.py`'s own
  proven problem-boundary detection, not imported (avoids reaching
  into another package's private internals for one piece of logic).
- `llm_extract.py` — one Gemini call per detected span, turning its raw
  text into a structured record (cleaned problem statement, solution
  verbatim if present, a short topic tag).
- `store.py` — read/write for `<root>/.problem_corpus/<course>.json`,
  mirroring `indexer/chunk_index.py`'s `.index/chunks/<course>.json`
  convention exactly.

Output goes to `<root>/.problem_corpus/<course>.json`, gitignored by
default (see the root `.gitignore`) — same IP posture as
`.index/chunks/`, since extracted problem text is pulled directly from
the corpus rather than being an LLM-authored summary of it.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`.
```

- [ ] **Step 4: Update the root `README.md`'s subproject list**

In `README.md`, find this line (the `problem_gen/` bullet):

```
- [`problem_gen/`](problem_gen/README.md) — the problem-generation sub-agent: retrieves the student's own real problems and textbook content for a topic, then generates a new, self-verified practice problem via a local Ollama model (`qwen2-math:7b`). No paid API call for generation itself. Wired into `rag/` via automatic intent detection on the question text — no flag needed.
```

Add immediately after it:

```
- [`problem_corpus/`](problem_corpus/README.md) — extracts a structured problem corpus (topic tag, problem text, solution if present, provenance) from math-camp's problem sets, textbooks, and recitation slides. Standalone batch tool, run on demand — not wired into `rag/` or `problem_gen/` yet (that's a later, separate idea). See `docs/status/2026-09-05-problem-generation-status.md`'s "Future development ideas" section.
```

- [ ] **Step 5: Update the root `README.md`'s Requirements section**

Find this line (the `problem_gen/` Requirements bullet):

```
- **Problem generation sub-agent only** (`problem_gen/`, reached via `rag/`'s automatic intent detection on the question text): ...
```

Add immediately after its paragraph (before the `video_notes/` bullet):

```
- **Problem corpus extraction only** (`problem_corpus/`, run directly — not reached via `rag/`): uses the same `GEMINI_API_KEY` as the Baseline row above, no extra setup. No local-Ollama option (this only runs as an occasional offline batch tool, not a live per-request path, so there's no equivalent reliability-vs-latency tradeoff to weigh).
```

- [ ] **Step 6: Commit**

```bash
cd ..
git add academic-rag-model/problem_corpus/README.md academic-rag-model/README.md .gitignore
git commit -m "docs(problem_corpus): add README, root README entry, and gitignore rule"
```

---

### Task 6: Real end-to-end validation

**Files:** None created or modified by this task's own steps beyond a new status doc.
- Create: `docs/status/2026-09-06-problem-corpus-extraction-status.md`

**Interfaces:** None — this task exercises the finished tool for real, no new code.

- [ ] **Step 1: Run a dry run first**

Run: `.\.venv\Scripts\python.exe -m problem_corpus.extractor --root ../academic-hub extract --course math-camp --dry-run`

Record the printed stats dict in your notes — this is what you expect the real run to report.

- [ ] **Step 2: Run the real extraction**

Run: `.\.venv\Scripts\python.exe -m problem_corpus.extractor --root ../academic-hub extract --course math-camp`

Record the printed stats dict and how long it took.

- [ ] **Step 3: Inspect the output file**

Open `../academic-hub/.problem_corpus/math-camp.json` and check:
- At least one record from a solution-less file (e.g. `Practice Sheet.md` or one of the `old_exam_*.md` files) has `"solution_text": null` and `"solution_provenance": null`.
- At least one record from `Real Analysis Problem Set_Solutions.md` or `Linear Algebra Problem Set AMS Solutions.md` has a non-null `"solution_text"` and `"solution_provenance": "student_attempt"` — **never `"verified"`**.
- `topic_tag` values are specific (e.g. "compactness"), not just a copy of the file's coarse front-matter `tags` list.
- `problem_text` doesn't still contain a leading artifact like `**Practice Problem 3.**` — it should read as a clean problem statement.

If any of these look wrong, that's a real finding — note it, don't silently accept it.

- [ ] **Step 4: Spot-check the textbook path**

Run: `.\.venv\Scripts\python.exe -m problem_corpus.extractor --root ../academic-hub extract --course math-camp --file "Axler"`

Confirm this extracted at least some records (Axler's `## Exercises 1A`-style sections should produce numbered-problem spans) and that every one of them has `"solution_text": null` (Axler has no solutions in the converted text, per this design's own corpus-inspection finding).

- [ ] **Step 5: Confirm idempotency**

Run the same `extract --course math-camp` command again. The printed stats should show `"unchanged"` equal to the total number of problem-bearing files processed in Step 2, and `"extracted": 0` — confirming no wasted Gemini calls on a second run with no source changes.

- [ ] **Step 6: Write the status doc**

Create `docs/status/2026-09-06-problem-corpus-extraction-status.md`:

```markdown
# Problem Corpus Extraction: Real Validation

Spec: `docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md`
Plan: `docs/superpowers/plans/2026-09-06-problem-corpus-extraction.md`

## Real run results

<Fill in: the dry-run stats dict, the real-run stats dict, wall-clock
time, and the Axler spot-check result from Steps 1-4 above.>

## Findings

<Fill in: anything from Step 3's inspection that looked wrong or
surprising -- e.g. a topic tag that was too generic, a problem_text
that still had a boundary-detection artifact in it, a file that should
have produced spans but didn't. If everything looked correct, say so
explicitly rather than leaving this section implying it wasn't
checked.>

## Known limitations

- Only math-camp is covered; other courses are empty or near-empty in
  this corpus right now (per this project's own earlier finding during
  `problem_gen`'s Gemini feasibility spike).
- No verified-solution tier exists anywhere in this corpus -- see the
  spec's own Section 1 finding.
- This subproject stops at the stored corpus; nothing yet consumes
  `.problem_corpus/<course>.json` (see the five other future-development
  ideas flagged in `docs/status/2026-09-05-problem-generation-status.md`).
```

- [ ] **Step 7: Commit**

```bash
git add docs/status/2026-09-06-problem-corpus-extraction-status.md
git commit -m "docs(problem_corpus): record real end-to-end validation results"
```
