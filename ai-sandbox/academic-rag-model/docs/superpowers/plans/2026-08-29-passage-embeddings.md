# Passage-Level Embeddings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chunk every already-indexed file into citable passages, embed each one, and add passage-level search on top of the existing file-level search.

**Architecture:** A new module `chunk_index.py` (mirroring `retag.py`'s separation from `index_card.py`) owns the tiered chunking algorithm, per-file chunk generation, and chunk storage. `index_search.py` gets `search_passages()` (a three-stage funnel reusing the existing `search()` for its file-level pass) plus CLI wiring for a new `chunk` subcommand and a `query --passages` flag.

**Tech Stack:** Python 3, `google-genai` (already in use), `unittest` (this repo's existing test framework, not pytest), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-29-passage-embeddings-design.md`

## Global Constraints

- No new third-party dependencies (chunking is pure-Python `re`/string logic; embedding reuses the existing `google-genai` client already wired through `gemini_utils.get_gemini_client()`).
- Every Gemini call goes through `gemini_utils.call_with_retries` — no bespoke retry logic anywhere in this plan.
- Chunks reuse the file-level embedding model/dimensionality unchanged: `EMBEDDING_MODEL = "gemini-embedding-001"`, `EMBEDDING_DIMENSIONALITY = 768` (both already defined in `index_card.py` — import, don't redefine).
- Storage stays flat JSON + brute-force NumPy cosine similarity, no ANN index (spec §9 — explicit YAGNI, unchanged from the original indexer).
- Test runner is `unittest`, not `pytest`: `./.venv/Scripts/python.exe -m unittest discover -s tests` (Windows venv path — this repo's actual convention, confirmed throughout this session).
- Every task's failing-test step must actually be run and confirmed failing before implementing (TDD, per this repo's established practice all session).

---

## File Structure

```
ai-sandbox/marker-conversion/
  chunk_index.py                    # NEW -- tiered chunking, generation, chunk storage I/O
  index_search.py                   # MODIFIED -- SearchResult.file_id, search_passages(), CLI wiring
  tests/
    test_chunk_index.py             # NEW
    test_index_search.py            # MODIFIED
```

`chunk_index.py` is deliberately a new, separate module rather than added to `index_card.py` or `retag.py` — same single-responsibility reasoning `retag.py`'s own docstring already gives for its own separation ("looks at content on its own explicit schedule, not per-file"). Chunking is per-file, like `index_card.py`, but a genuinely different concern (structural text splitting, not LLM-generated metadata) with its own storage shard, so it earns its own file rather than growing either existing module.

---

## Task 1: Chunk shard storage I/O

**Files:**
- Create: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Produces: `chunks_dir(academic_hub_root: str) -> str`, `chunks_path(academic_hub_root: str, course: str) -> str`, `load_chunks(academic_hub_root: str, course: str) -> list[dict]`, `save_chunks(academic_hub_root: str, course: str, chunks: list[dict]) -> None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_chunk_index.py
import os
import tempfile
import unittest

from chunk_index import chunks_path, load_chunks, save_chunks


class TestChunkStorage(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_chunks(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = [{"chunk_id": "abc-000", "file_id": "abc", "text": "hello"}]
            save_chunks(tmp, "math-camp", chunks)
            self.assertEqual(load_chunks(tmp, "math-camp"), chunks)

    def test_chunks_path_lives_under_index_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = chunks_path(tmp, "math-camp")
            self.assertTrue(path.replace("\\", "/").endswith(".index/chunks/math-camp.json"))

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_chunks(tmp, "math-camp", [])
            self.assertTrue(os.path.isdir(os.path.join(tmp, ".index", "chunks")))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL/ERROR — `chunk_index` module doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# chunk_index.py
"""
chunk_index.py
Passage-level chunking, embedding, and storage for the academic-hub
source indexer (spec: docs/superpowers/specs/2026-08-29-passage-embeddings-design.md).

Deliberately separate from index_card.py (per-file cards) and
retag.py (corpus-wide tag mining) -- chunking is per-file like cards,
but runs on its own explicit schedule (index_search.py's `chunk`
subcommand), not automatically inside a pipeline hook, for the same
reason retag stays a separate pass: a first-time capability like this
is lower-risk built and proven standalone first, and hook-time
chunking would mean a single textbook conversion run also pays for
potentially hundreds of chunk-embedding calls inline with no separate
control over when that cost is paid.
"""
from __future__ import annotations

import json
import os


def chunks_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "chunks")


def chunks_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(chunks_dir(academic_hub_root), f"{course}.json")


def load_chunks(academic_hub_root: str, course: str) -> list[dict]:
    path = chunks_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chunks(academic_hub_root: str, course: str, chunks: list[dict]) -> None:
    path = chunks_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add chunk shard storage I/O"
```

---

## Task 2: Frontmatter stripping and page-marker helpers

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: nothing new (pure string/regex logic)
- Produces: `_strip_yaml_frontmatter(text: str) -> str`, `_strip_front_matter_by_page(body: str, front_matter_end: int) -> str`, `_PAGE_MARKER_RE` (module-level compiled regex), `_page_markers(body: str) -> list[tuple[int, int]]` (list of `(page_number, char_offset)`, sorted by offset)

- [ ] **Step 1: Write the failing tests**

```python
class TestStripYamlFrontmatter(unittest.TestCase):
    def test_strips_frontmatter_block(self):
        text = "---\nsource_pdf: a.pdf\ntags: []\n---\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), "Body content.")

    def test_no_frontmatter_returns_text_unchanged(self):
        text = "<!-- page 1 -->\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), text)


class TestStripFrontMatterByPage(unittest.TestCase):
    def test_drops_pages_at_or_before_the_boundary(self):
        body = (
            "<!-- page 1 -->\n\nTitle page.\n\n"
            "<!-- page 14 -->\n\nTable of contents.\n\n"
            "<!-- page 15 -->\n\nReal chapter 1 content."
        )
        result = _strip_front_matter_by_page(body, front_matter_end=14)
        self.assertNotIn("Title page", result)
        self.assertNotIn("Table of contents", result)
        self.assertIn("Real chapter 1 content", result)
        self.assertTrue(result.startswith("<!-- page 15 -->"))

    def test_every_page_is_front_matter_keeps_everything(self):
        # Pathological/empty-doc edge case -- don't return an empty
        # string just because front_matter_end covers every page found.
        body = "<!-- page 1 -->\n\nOnly page."
        self.assertEqual(_strip_front_matter_by_page(body, front_matter_end=99), body)


class TestPageMarkers(unittest.TestCase):
    def test_finds_every_marker_with_offsets(self):
        body = "before<!-- page 1 -->mid<!-- page 2 -->after"
        markers = _page_markers(body)
        self.assertEqual([p for p, _ in markers], [1, 2])
        self.assertEqual(body[markers[0][1]:markers[0][1] + 6], "<!-- p")

    def test_no_markers_returns_empty_list(self):
        self.assertEqual(_page_markers("no markers here"), [])
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — the three functions/regex don't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

import re

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.DOTALL)
_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


def _strip_yaml_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _page_markers(body: str) -> list[tuple[int, int]]:
    return [(int(m.group(1)), m.start()) for m in _PAGE_MARKER_RE.finditer(body)]


def _strip_front_matter_by_page(body: str, front_matter_end: int) -> str:
    """Drops everything up to and including the last front-matter page
    (title page, author, table of contents) for a textbook -- confirmed
    live that Marker's conversion marks front-matter lines with `#`
    (e.g. a bare author name), which would otherwise produce garbage
    heading-tier chunks. front_matter_end is the same boundary
    describe_images.py's load_front_matter_end() already reads from
    run_config.json for exactly this purpose on the image-description
    side."""
    for page, offset in _page_markers(body):
        if page > front_matter_end:
            return body[offset:]
    return body  # nothing past the boundary was found -- keep everything
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Task 1 and 2)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add frontmatter stripping and page-marker helpers"
```

---

## Task 3: Tier 1 -- heading-based splitting

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `_Span` (a small dataclass: `start: int, end: int, tier: str, heading_path: list[str] | None = None, problem_label: str | None = None`), `_split_by_headings(body: str) -> list[_Span] | None` (None signals "not enough heading structure, try the next tier")

- [ ] **Step 1: Write the failing tests**

```python
class TestSplitByHeadings(unittest.TestCase):
    def test_splits_at_each_heading_with_correct_spans(self):
        body = "# One\n\nFirst section.\n\n# Two\n\nSecond section."
        spans = _split_by_headings(body)
        self.assertEqual(len(spans), 2)
        self.assertEqual(body[spans[0].start:spans[0].end], "# One\n\nFirst section.\n\n")
        self.assertEqual(body[spans[1].start:spans[1].end], "# Two\n\nSecond section.")

    def test_nested_headings_build_a_heading_path(self):
        body = (
            "# 3 Optimization in Euclidean Space\n\nIntro.\n\n"
            "## 3.7 Optimization over a Convex Set\n\nContent."
        )
        spans = _split_by_headings(body)
        self.assertEqual(spans[0].heading_path, ["3 Optimization in Euclidean Space"])
        self.assertEqual(
            spans[1].heading_path,
            ["3 Optimization in Euclidean Space", "3.7 Optimization over a Convex Set"],
        )

    def test_sibling_after_deeper_heading_pops_the_stack(self):
        body = (
            "# One\n\nA.\n\n## One point one\n\nB.\n\n# Two\n\nC."
        )
        spans = _split_by_headings(body)
        # "Two" is a sibling of "One", not nested under "One point one"
        self.assertEqual(spans[2].heading_path, ["Two"])

    def test_every_span_tagged_with_heading_tier(self):
        body = "# One\n\nA.\n\n# Two\n\nB."
        spans = _split_by_headings(body)
        self.assertTrue(all(s.tier == "heading" for s in spans))
        self.assertTrue(all(s.problem_label is None for s in spans))

    def test_too_few_headings_returns_none(self):
        # Confirmed live: old_exam_2021.md has exactly 1 heading in a
        # 22-page document -- not real structure, must fall through to
        # the next tier rather than produce one giant "chunk".
        body = "Some text.\n\n### Standard Counterexamples\n\nMore text."
        self.assertIsNone(_split_by_headings(body))

    def test_no_headings_returns_none(self):
        self.assertIsNone(_split_by_headings("Just plain text, no headings at all."))
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `_Span`/`_split_by_headings` don't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

from dataclasses import dataclass, field


@dataclass
class _Span:
    start: int
    end: int
    tier: str
    heading_path: list[str] | None = None
    problem_label: str | None = None


_HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.*)$")
_MIN_HEADING_MATCHES = 2  # confirmed live: old_exam_2021.md has exactly 1
# real heading in 22 pages -- not real document structure. 2+ is the
# floor for "this file is actually organized into headed sections."


def _split_by_headings(body: str) -> list[_Span] | None:
    matches = list(_HEADING_RE.finditer(body))
    if len(matches) < _MIN_HEADING_MATCHES:
        return None

    spans = []
    stack: list[tuple[int, str]] = []  # (heading level, heading text)
    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading_text = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)

        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading_text))

        spans.append(_Span(
            start=start, end=end, tier="heading",
            heading_path=[h for _, h in stack],
        ))
    return spans
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-3)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add heading-based chunking tier"
```

---

## Task 4: Tier 2 -- numbered-problem detection

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: `_Span` (Task 3)
- Produces: `_detect_problem_boundaries(body: str) -> list[_Span] | None`

- [ ] **Step 1: Write the failing tests**

```python
class TestDetectProblemBoundaries(unittest.TestCase):
    def test_plain_numbered_problems(self):
        # Real convention confirmed live in old_problem_set.md.
        body = (
            "1. For each of the following functions, state...\n\n"
            "2. Consider a production function...\n\n"
            "3. In an economy with n goods...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")
        self.assertEqual(spans[2].problem_label, "Problem 3")
        self.assertTrue(all(s.tier == "problem_number" for s in spans))

    def test_bold_practice_problem_convention(self):
        # Real convention confirmed live in Practice Sheet.md -- doesn't
        # match a bare "N." pattern since it's wrapped in ** and has a title.
        body = (
            "**Practice Problem 1. Involutions**\n\nLet V be...\n\n"
            "**Practice Problem 2. Norms**\n\nShow that...\n\n"
            "**Practice Problem 3. Rank**\n\nDetermine...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")

    def test_points_annotated_problems(self):
        # Real convention confirmed live in old_exam_2021.md.
        body = (
            "1. **(40 points)** Are the following statements true or false?\n\n"
            "2. **(15 points)** Consider the following matrix\n\n"
            "3. **(15 points)**. Consider the following function\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)

    def test_too_few_matches_returns_none(self):
        # A single accidental match (e.g. one stray "1." in prose) must
        # not be trusted as real document structure -- same "empirically
        # validate before trusting" bar retag.py's discovery phase uses.
        body = "Some prose that happens to mention item 1. and nothing else numbered."
        self.assertIsNone(_detect_problem_boundaries(body))

    def test_no_matches_returns_none(self):
        self.assertIsNone(_detect_problem_boundaries("No numbered problems in here."))
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `_detect_problem_boundaries` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),
    re.compile(r"(?m)^\*\*Practice Problem \d+"),
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same reasoning as retag.py's MIN_TAG_CLUSTER_SIZE:
# a weak/sparse match count isn't trusted as real document structure.
_PROBLEM_LABEL_RE = re.compile(r"^\**\s*(?:Practice Problem|Problem|Question)?\s*(\d+)", re.IGNORECASE)


def _problem_label_at(body: str, start: int) -> str:
    first_line = body[start:start + 80].split("\n", 1)[0]
    m = _PROBLEM_LABEL_RE.match(first_line)
    return f"Problem {m.group(1)}" if m else "Problem"


def _detect_problem_boundaries(body: str) -> list[_Span] | None:
    starts = set()
    for pattern in _PROBLEM_BOUNDARY_PATTERNS:
        starts.update(m.start() for m in pattern.finditer(body))
    if len(starts) < _MIN_PROBLEM_MATCHES:
        return None

    ordered = sorted(starts)
    spans = []
    for i, start in enumerate(ordered):
        end = ordered[i + 1] if i + 1 < len(ordered) else len(body)
        spans.append(_Span(
            start=start, end=end, tier="problem_number",
            problem_label=_problem_label_at(body, start),
        ))
    return spans
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-4)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add numbered-problem detection tier"
```

---

## Task 5: Tier 3 -- page-based fallback

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: `_Span`, `_page_markers` (Tasks 2-3)
- Produces: `_split_by_pages(body: str) -> list[_Span]` (never returns None -- the universal fallback, always succeeds)

- [ ] **Step 1: Write the failing tests**

```python
class TestSplitByPages(unittest.TestCase):
    def test_one_span_per_page_marker(self):
        body = "<!-- page 1 -->\n\nFirst.\n\n<!-- page 2 -->\n\nSecond."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 2)
        self.assertTrue(all(s.tier == "page" for s in spans))
        self.assertEqual(body[spans[0].start:spans[0].end], "<!-- page 1 -->\n\nFirst.\n\n")

    def test_no_page_markers_returns_one_span_covering_everything(self):
        # Practice Sheet.md-style pathological case: even the universal
        # fallback needs to degrade gracefully if a file somehow has
        # neither headings, numbered problems, nor page markers.
        body = "Just some text with nothing structural in it at all."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].start, 0)
        self.assertEqual(spans[0].end, len(body))
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `_split_by_pages` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

def _split_by_pages(body: str) -> list[_Span]:
    markers = _page_markers(body)
    if not markers:
        return [_Span(start=0, end=len(body), tier="page")]

    spans = []
    for i, (_, offset) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(body)
        spans.append(_Span(start=offset, end=end, tier="page"))
    return spans
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-5)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add page-based fallback tier"
```

---

## Task 6: Uniform size cap, minimum-length filter, and finalization

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: `_Span`, `_page_markers` (Tasks 2-5)
- Produces: `_subdivide_oversized(spans: list[_Span], body: str) -> list[_Span]`, `_page_range_for_span(start: int, end: int, markers: list[tuple[int, int]]) -> list[int] | None`, `_finalize_chunks(spans: list[_Span], body: str) -> list[dict]` (drops anything under the minimum length, attaches `page_range`, extracts `text`)

- [ ] **Step 1: Write the failing tests**

```python
class TestSubdivideOversized(unittest.TestCase):
    def test_span_under_the_cap_is_untouched(self):
        body = "# One\n\n" + ("x" * 100)
        spans = [_Span(0, len(body), "heading", heading_path=["One"])]
        result = _subdivide_oversized(spans, body)
        self.assertEqual(result, spans)

    def test_oversized_span_splits_at_paragraph_breaks(self):
        # Confirmed live: LN_Optimization.md has a real 34,054-char
        # section with no sub-headings -- must not become one giant chunk.
        paragraph = "x" * 1500
        body = f"{paragraph}\n\n{paragraph}\n\n{paragraph}"  # ~4500 chars, 3 paragraphs
        spans = [_Span(0, len(body), "heading", heading_path=["Big Section"])]
        result = _subdivide_oversized(spans, body)
        self.assertGreater(len(result), 1)
        for s in result:
            self.assertLessEqual(s.end - s.start, _CHUNK_MAX_CHARS)
            self.assertEqual(s.heading_path, ["Big Section"])  # metadata carried through

    def test_oversized_span_with_no_paragraph_breaks_stays_one_span(self):
        # No structural boundary to split at -- can't manufacture one,
        # so the size cap is a best-effort, not an absolute guarantee.
        body = "x" * (_CHUNK_MAX_CHARS + 500)
        spans = [_Span(0, len(body), "page")]
        result = _subdivide_oversized(spans, body)
        self.assertEqual(len(result), 1)


class TestPageRangeForSpan(unittest.TestCase):
    def test_span_spanning_multiple_pages(self):
        body = "<!-- page 44 -->\n\nA.\n\n<!-- page 45 -->\n\nB."
        markers = _page_markers(body)
        self.assertEqual(_page_range_for_span(0, len(body), markers), [44, 45])

    def test_span_starting_mid_page_uses_preceding_marker(self):
        body = "<!-- page 44 -->\n\nA.\n\nB."
        markers = _page_markers(body)
        mid_start = body.index("B.")
        self.assertEqual(_page_range_for_span(mid_start, len(body), markers), [44, 44])

    def test_no_markers_at_all_returns_none(self):
        self.assertEqual(_page_range_for_span(0, 10, []), None)


class TestFinalizeChunks(unittest.TestCase):
    def test_extracts_text_and_attaches_page_range(self):
        body = "<!-- page 1 -->\n\n# One\n\nReal content here, long enough to keep."
        spans = [_Span(body.index("# One"), len(body), "heading", heading_path=["One"])]
        chunks = _finalize_chunks(spans, body)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Real content here", chunks[0]["text"])
        self.assertEqual(chunks[0]["page_range"], [1, 1])
        self.assertEqual(chunks[0]["heading_path"], ["One"])
        self.assertIsNone(chunks[0]["problem_label"])

    def test_drops_chunks_under_the_minimum_length(self):
        body = "# One\n\n# Two\n\nReal content, long enough to clear the minimum length filter easily."
        spans = _split_by_headings(body)  # "# One" section is empty -- just the heading itself
        chunks = _finalize_chunks(spans, body)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Two", chunks[0]["heading_path"])
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — the three functions and `_CHUNK_MAX_CHARS` don't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

_CHUNK_MAX_CHARS = 3000  # confirmed live against LN_Optimization.md's 112 real
# sections: median 678 chars, p90 1,937, but a real max of 34,054 -- this
# sits above the real p90 (rarely fires on well-structured content) while
# firmly bounding the outlier tail.
_CHUNK_MIN_CHARS = 80  # drops a heading immediately followed by another
# heading with no real content between them -- noise, not retrievable content.

_PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")


def _subdivide_oversized(spans: list[_Span], body: str) -> list[_Span]:
    result = []
    for span in spans:
        if span.end - span.start <= _CHUNK_MAX_CHARS:
            result.append(span)
            continue
        result.extend(_split_span_by_paragraph(span, body))
    return result


def _split_span_by_paragraph(span: _Span, body: str) -> list[_Span]:
    """Greedily fills each sub-span up to _CHUNK_MAX_CHARS, cutting only
    at blank-line paragraph breaks -- the one structural boundary
    guaranteed to exist regardless of which tier produced the oversized
    span (a lettered sub-part like "(a)"/"(b)" is itself normally
    paragraph-separated already, so this one rule covers both cases
    without separate sub-part-detection logic)."""
    text = body[span.start:span.end]
    break_ends = [0] + [m.end() for m in _PARAGRAPH_BREAK_RE.finditer(text)] + [len(text)]

    boundaries = [break_ends[0]]
    chunk_start = break_ends[0]
    for i in range(1, len(break_ends)):
        if break_ends[i] - chunk_start > _CHUNK_MAX_CHARS and break_ends[i - 1] > chunk_start:
            boundaries.append(break_ends[i - 1])
            chunk_start = break_ends[i - 1]
    boundaries.append(break_ends[-1])

    return [
        _Span(
            start=span.start + boundaries[i], end=span.start + boundaries[i + 1],
            tier=span.tier, heading_path=span.heading_path, problem_label=span.problem_label,
        )
        for i in range(len(boundaries) - 1)
    ]


def _page_range_for_span(start: int, end: int, markers: list[tuple[int, int]]) -> list[int] | None:
    in_span = [page for page, offset in markers if start <= offset < end]
    if in_span:
        return [min(in_span), max(in_span)]
    before = [page for page, offset in markers if offset <= start]
    return [before[-1], before[-1]] if before else None


def _finalize_chunks(spans: list[_Span], body: str) -> list[dict]:
    markers = _page_markers(body)
    result = []
    for span in spans:
        text = body[span.start:span.end].strip()
        if len(text) < _CHUNK_MIN_CHARS:
            continue
        result.append({
            "text": text,
            "tier": span.tier,
            "heading_path": span.heading_path,
            "problem_label": span.problem_label,
            "page_range": _page_range_for_span(span.start, span.end, markers),
        })
    return result
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-6)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add uniform size cap, min-length filter, and chunk finalization"
```

---

## Task 7: `chunk_file()` -- the top-level dispatcher

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: everything from Tasks 1-6
- Produces: `chunk_file(text: str, doc_type: str, folder_category: str, front_matter_end: int | None = None) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

```python
class TestChunkFile(unittest.TestCase):
    def test_strips_yaml_frontmatter_before_chunking(self):
        text = (
            "---\nsource_pdf: a.pdf\ntags: []\n---\n\n"
            "# One\n\nFirst.\n\n# Two\n\nSecond, long enough to clear the minimum length."
        )
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all("source_pdf" not in c["text"] for c in chunks))

    def test_uses_heading_tier_when_available(self):
        text = "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough."
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all(c["tier"] == "heading" for c in chunks))

    def test_falls_back_to_problem_number_tier_for_problem_sets(self):
        text = (
            "1. First problem, long enough to clear the minimum length filter easily.\n\n"
            "2. Second problem, long enough to clear the minimum length filter easily.\n\n"
            "3. Third problem, long enough to clear the minimum length filter easily.\n\n"
        )
        chunks = chunk_file(text, doc_type="problem_set", folder_category="problem_sets")
        self.assertTrue(all(c["tier"] == "problem_number" for c in chunks))

    def test_does_not_attempt_problem_number_tier_outside_problem_sets(self):
        # Same numbered-looking content, but not a problem_sets file --
        # tier 2 is scoped to problem_sets/recitation_slides only (spec §4).
        text = (
            "1. First point, long enough to clear the minimum length filter easily.\n\n"
            "2. Second point, long enough to clear the minimum length filter easily.\n\n"
            "3. Third point, long enough to clear the minimum length filter easily.\n\n"
        )
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes")
        self.assertTrue(all(c["tier"] == "page" for c in chunks))

    def test_falls_back_to_page_tier_when_nothing_else_matches(self):
        text = "<!-- page 1 -->\n\nJust some unstructured prose, long enough to keep as a chunk."
        chunks = chunk_file(text, doc_type="problem_set", folder_category="problem_sets")
        self.assertTrue(all(c["tier"] == "page" for c in chunks))

    def test_textbook_front_matter_is_skipped(self):
        text = (
            "<!-- page 1 -->\n\n# Sheldon Axler\n\nAuthor bio front matter.\n\n"
            "<!-- page 14 -->\n\n# Contents\n\nTOC front matter.\n\n"
            "<!-- page 15 -->\n\n# 1 Vector Spaces\n\nReal chapter content, long enough."
        )
        chunks = chunk_file(text, doc_type="textbook", folder_category="textbooks-and-papers", front_matter_end=14)
        all_text = " ".join(c["text"] for c in chunks)
        self.assertNotIn("Author bio", all_text)
        self.assertNotIn("TOC front matter", all_text)
        self.assertIn("Real chapter content", all_text)

    def test_notes_files_are_unaffected_by_front_matter_end(self):
        # front_matter_end is only ever passed for doc_type == "textbook" --
        # confirms notes content is never accidentally truncated by it.
        text = "# Sheldon Axler\n\nThis is real notes content, not front matter here.\n\n# Two\n\nMore."
        chunks = chunk_file(text, doc_type="ta_notes", folder_category="ta_notes", front_matter_end=14)
        all_text = " ".join(c["text"] for c in chunks)
        self.assertIn("real notes content", all_text)
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `chunk_file` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

_PROBLEM_TIER_FOLDER_CATEGORIES = ("problem_sets", "recitation_slides")


def chunk_file(
    text: str, doc_type: str, folder_category: str, front_matter_end: int | None = None,
) -> list[dict]:
    """Tiered chunking (spec §4): headings first, numbered-problem
    detection second (problem_sets/recitation_slides only, empirically
    validated before being trusted), page-based fallback always
    available. Every tier's output goes through the same size cap and
    minimum-length filter. Pure function -- no file I/O, no network
    calls; front_matter_end is computed by the caller (generation
    happens in generate_chunks_for_file, which has filesystem access)
    via describe_images.py's existing load_front_matter_end()."""
    body = _strip_yaml_frontmatter(text)
    if doc_type == "textbook" and front_matter_end is not None:
        body = _strip_front_matter_by_page(body, front_matter_end)

    spans = _split_by_headings(body)
    if spans is None and folder_category in _PROBLEM_TIER_FOLDER_CATEGORIES:
        spans = _detect_problem_boundaries(body)
    if spans is None:
        spans = _split_by_pages(body)

    spans = _subdivide_oversized(spans, body)
    return _finalize_chunks(spans, body)
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-7)

- [ ] **Step 5: Spot-check against real corpus files**

Run this one-off script (not a unit test -- a real-data sanity check before moving to the embedding-generation task):

```bash
./.venv/Scripts/python.exe -c "
from chunk_index import chunk_file
for path, doc_type, folder_category in [
    ('../academic-hub/academic_notes/math-camp/ta_notes/processed_outputs/LN_Optimization.md', 'ta_notes', 'ta_notes'),
    ('../academic-hub/academic_notes/math-camp/problem_sets/processed_outputs/old_exam_2021.md', 'problem_set', 'problem_sets'),
    ('../academic-hub/academic_notes/math-camp/problem_sets/processed_outputs/Practice Sheet.md', 'problem_set', 'problem_sets'),
]:
    text = open(path, encoding='utf-8').read()
    chunks = chunk_file(text, doc_type, folder_category)
    tiers = {}
    for c in chunks:
        tiers[c['tier']] = tiers.get(c['tier'], 0) + 1
    print(path.split('/')[-1], '->', len(chunks), 'chunks,', tiers)
"
```

Expected: `LN_Optimization.md` -> mostly `heading` tier; `old_exam_2021.md` -> `problem_number` tier; `Practice Sheet.md` -> `problem_number` tier (its `**Practice Problem N**` convention matches `_PROBLEM_BOUNDARY_PATTERNS`) or `page` tier if that pattern doesn't clear `_MIN_PROBLEM_MATCHES` in practice -- either is a correct outcome per the tiered design, but confirm the chunk counts look sane (roughly in the dozens, not one giant chunk or thousands of one-line fragments) before proceeding.

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add chunk_file() top-level dispatcher"
```

---

## Task 8: `generate_chunks_for_file()` -- embed and store one file's chunks

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: `chunk_file()` (Task 7), `chunks_path`/`load_chunks`/`save_chunks` (Task 1), `index_card.EMBEDDING_MODEL`, `index_card.EMBEDDING_DIMENSIONALITY`, `index_card.EMBEDDING_MODEL_ID`, `gemini_utils.call_with_retries`
- Produces: `_folder_category_from_path(path: str) -> str`, `generate_chunks_for_file(academic_hub_root: str, course: str, card: dict, client) -> dict` (stats: `{"chunks_written": int}`, raises on total failure -- caller decides how to log/skip)

**Real interface note:** cards don't store `folder_category` as a field
-- confirmed against the real corpus: `generate_index_card()`'s dict
(`index_card.py`) has no such key, and `doc_type` alone isn't a safe
substitute (confirmed live: `Math_Camp_Recitation_2 with solution.md`
was classified `doc_type: "ta_notes"`, not `"problem_set"`, so gating
tier 2 on `doc_type` would incorrectly skip real problem-set structure
for that file). `folder_category` is derived from `card["path"]`
instead, the same folder segment `index_search.py`'s `rebuild()`
already computes when it first discovers a file.

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import MagicMock

from index_card import save_shard


class TestFolderCategoryFromPath(unittest.TestCase):
    def test_notes_path(self):
        path = "academic_notes/math-camp/recitation_slides/processed_outputs/a.md"
        self.assertEqual(_folder_category_from_path(path), "recitation_slides")

    def test_textbook_path(self):
        path = "academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler/Axler.rag.md"
        self.assertEqual(_folder_category_from_path(path), "textbooks-and-papers")

    def test_path_with_no_processed_outputs_segment_returns_empty_string(self):
        self.assertEqual(_folder_category_from_path("weird/path.md"), "")


def _fake_embed_client(dim=3):
    client = MagicMock()
    def embed_content(model, contents, config):
        response = MagicMock()
        embedding = MagicMock()
        embedding.values = [0.1] * dim
        response.embeddings = [embedding]
        return response
    client.models.embed_content.side_effect = embed_content
    return client


def _write_notes_md(tmp, rel_path, content):
    full_path = os.path.join(tmp, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


_A_MD = "academic_notes/math-camp/ta_notes/processed_outputs/a.md"
_B_MD = "academic_notes/math-camp/ta_notes/processed_outputs/b.md"


class TestGenerateChunksForFile(unittest.TestCase):
    def test_writes_chunks_for_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 2)
            chunks = load_chunks(tmp, "math-camp")
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]["file_id"], "abc123")
            self.assertEqual(chunks[0]["chunk_id"], "abc123-000")
            self.assertEqual(chunks[0]["content_hash"], "hash1")
            self.assertEqual(chunks[0]["embedding"], [0.1, 0.1, 0.1])

    def test_up_to_date_chunks_are_skipped_without_calling_the_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, client)
            client.models.embed_content.reset_mock()

            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 0)
            client.models.embed_content.assert_not_called()

    def test_stale_content_hash_regenerates_all_chunks_for_that_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, client)

            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# One\n\nDifferent first, long enough.\n\n# Two\n\nDifferent second, long enough.\n\n# Three\n\nA new third section, long enough to keep.")
            card["content_hash"] = "hash2"
            stats = generate_chunks_for_file(tmp, "math-camp", card, client)
            self.assertEqual(stats["chunks_written"], 3)
            chunks = load_chunks(tmp, "math-camp")
            self.assertEqual(len(chunks), 3)  # old 2 replaced, not appended to
            self.assertTrue(all(c["content_hash"] == "hash2" for c in chunks))

    def test_other_files_chunks_are_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            _write_notes_md(tmp, _B_MD, "# X\n\nThird, long enough.\n\n# Y\n\nFourth, long enough.")
            client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp",
                {"file_id": "aaa", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "h1"}, client)
            generate_chunks_for_file(tmp, "math-camp",
                {"file_id": "bbb", "path": _B_MD, "doc_type": "ta_notes", "content_hash": "h2"}, client)
            file_ids = {c["file_id"] for c in load_chunks(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa", "bbb"})

    def test_embedding_failure_leaves_existing_chunks_untouched(self):
        # Atomicity (spec §5): a partial failure must not leave a
        # half-updated, inconsistent chunk set for this file.
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            card = {"file_id": "abc123", "path": _A_MD, "doc_type": "ta_notes", "content_hash": "hash1"}
            good_client = _fake_embed_client()
            generate_chunks_for_file(tmp, "math-camp", card, good_client)
            original = load_chunks(tmp, "math-camp")

            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# One\n\nRewritten, long enough.\n\n# Two\n\nAlso rewritten, long enough.")
            card["content_hash"] = "hash2"
            bad_client = MagicMock()
            bad_client.models.embed_content.side_effect = RuntimeError("quota exceeded")
            with self.assertRaises(RuntimeError):
                generate_chunks_for_file(tmp, "math-camp", card, bad_client)
            self.assertEqual(load_chunks(tmp, "math-camp"), original)
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `_folder_category_from_path`/`generate_chunks_for_file` don't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

from google.genai import types

from gemini_utils import call_with_retries
from index_card import EMBEDDING_DIMENSIONALITY, EMBEDDING_MODEL, EMBEDDING_MODEL_ID


def _folder_category_from_path(path: str) -> str:
    """The literal folder segment two levels up from processed_outputs/
    (e.g. "recitation_slides", "textbooks-and-papers") -- cards don't
    store this directly (only the LLM-classified doc_type, a separate,
    imperfect signal), so it's re-derived from the path exactly the way
    index_search.py's rebuild() computes it when a file is first
    discovered. Card paths are always stored with "/" separators
    regardless of OS."""
    parts = path.split("/")
    if "processed_outputs" not in parts:
        return ""
    idx = parts.index("processed_outputs")
    return parts[idx - 1] if idx >= 1 else ""


def _embed_chunk_text(client, text: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL, contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def generate_chunks_for_file(academic_hub_root: str, course: str, card: dict, client) -> dict:
    """Chunk + embed one file's content, atomically (spec §5): parses
    structure locally first (no API cost via chunk_file()), then embeds
    every resulting chunk one at a time through call_with_retries (each
    call already retried/backed-off independently -- if any single
    chunk's embedding call ultimately fails after retries, the whole
    file's update is abandoned before anything is written, so a partial
    failure never leaves a half-updated, inconsistent set for this file
    in .index/chunks/<course>.json). Skips entirely (no API calls at
    all) when the file's chunks are already up to date with its current
    content_hash."""
    file_id = card["file_id"]
    existing = load_chunks(academic_hub_root, course)
    current_for_file = [c for c in existing if c["file_id"] == file_id]
    if current_for_file and all(c["content_hash"] == card["content_hash"] for c in current_for_file):
        return {"chunks_written": 0}

    md_path = os.path.join(academic_hub_root, card["path"])
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    front_matter_end = None
    if card["doc_type"] == "textbook":
        from describe_images import load_front_matter_end
        book_dir = os.path.dirname(md_path)
        front_matter_end = load_front_matter_end(book_dir)

    folder_category = _folder_category_from_path(card["path"])
    raw_chunks = chunk_file(text, card["doc_type"], folder_category, front_matter_end)

    new_chunks = []
    for i, raw in enumerate(raw_chunks):
        embedding = call_with_retries(lambda t=raw["text"]: _embed_chunk_text(client, t))
        new_chunks.append({
            "chunk_id": f"{file_id}-{i:03d}",
            "file_id": file_id,
            "chunk_index": i,
            "tier": raw["tier"],
            "heading_path": raw["heading_path"],
            "problem_label": raw["problem_label"],
            "page_range": raw["page_range"],
            "text": raw["text"],
            "embedding": embedding,
            "embedding_model": EMBEDDING_MODEL_ID,
            "content_hash": card["content_hash"],
        })

    remaining = [c for c in existing if c["file_id"] != file_id]
    save_chunks(academic_hub_root, course, remaining + new_chunks)
    return {"chunks_written": len(new_chunks)}
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-8)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add generate_chunks_for_file() with atomicity and staleness"
```

---

## Task 9: `chunk()` orchestration pass

**Files:**
- Modify: `ai-sandbox/marker-conversion/chunk_index.py`
- Test: `ai-sandbox/marker-conversion/tests/test_chunk_index.py`

**Interfaces:**
- Consumes: `generate_chunks_for_file()` (Task 8), `index_card.list_courses`, `index_card.load_shard`
- Produces: `chunk(academic_hub_root: str, client, course: str | None = None, file: str | None = None, dry_run: bool = False) -> dict` (stats: `{"chunked": int, "unchanged": int, "failed": int, "skipped_no_embedding": int}`)

- [ ] **Step 1: Write the failing tests**

```python
from index_card import save_shard

_MISSING_MD = "academic_notes/math-camp/ta_notes/processed_outputs/missing.md"


def _make_card(file_id, path, doc_type="ta_notes", content_hash="h1", embedding=None):
    # No folder_category key -- real cards don't have one (see Task 8's
    # "Real interface note"); generate_chunks_for_file() derives it from
    # `path` via _folder_category_from_path().
    return {
        "file_id": file_id, "path": path, "course": "math-camp",
        "doc_type": doc_type, "content_hash": content_hash, "embedding": embedding or [0.1, 0.2],
        "orphaned": False, "needs_indexing": False,
    }


class TestChunkOrchestration(unittest.TestCase):
    def test_chunks_every_indexed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(len(load_chunks(tmp, "math-camp")), 2)

    def test_second_run_with_no_changes_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            client = _fake_embed_client()
            chunk(tmp, client=client)
            client.models.embed_content.reset_mock()

            stats = chunk(tmp, client=client)
            self.assertEqual(stats["chunked"], 0)
            self.assertEqual(stats["unchanged"], 1)
            client.models.embed_content.assert_not_called()

    def test_skips_cards_with_no_embedding_yet(self):
        # A needs_indexing card has no embedding -- nothing to chunk yet.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "aaa", "path": _A_MD, "course": "math-camp",
                "doc_type": "ta_notes", "content_hash": None, "embedding": [], "needs_indexing": True,
            }])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["skipped_no_embedding"], 1)
            self.assertEqual(stats["chunked"], 0)

    def test_one_file_failure_does_not_abort_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            # _MISSING_MD deliberately not written -- generate_chunks_for_file
            # will fail to open it.
            save_shard(tmp, "math-camp", [
                _make_card("aaa", _A_MD), _make_card("bbb", _MISSING_MD),
            ])
            stats = chunk(tmp, client=_fake_embed_client())
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(stats["failed"], 1)
            file_ids = {c["file_id"] for c in load_chunks(tmp, "math-camp")}
            self.assertEqual(file_ids, {"aaa"})  # a.md's chunks still written

    def test_dry_run_calls_no_api_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            client = _fake_embed_client()
            stats = chunk(tmp, client=client, dry_run=True)
            client.models.embed_content.assert_not_called()
            self.assertEqual(load_chunks(tmp, "math-camp"), [])
            self.assertEqual(stats["chunked"], 1)  # reports what WOULD be chunked

    def test_scoped_to_one_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_notes_md(tmp, _A_MD, "# One\n\nFirst, long enough.\n\n# Two\n\nSecond, long enough.")
            _write_notes_md(tmp, _B_MD, "# X\n\nThird, long enough.\n\n# Y\n\nFourth, long enough.")
            save_shard(tmp, "math-camp", [_make_card("aaa", _A_MD)])
            save_shard(tmp, "econ-101", [_make_card("bbb", _B_MD)])
            stats = chunk(tmp, client=_fake_embed_client(), course="math-camp")
            self.assertEqual(stats["chunked"], 1)
            self.assertEqual(load_chunks(tmp, "econ-101"), [])
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: FAIL — `chunk` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# Add to chunk_index.py

from index_card import list_courses, load_shard


def chunk(
    academic_hub_root: str, client, course: str | None = None,
    file: str | None = None, dry_run: bool = False,
) -> dict:
    """Iterates every non-orphaned, embedded card (needs_indexing cards
    have no embedding yet -- nothing to chunk) and calls
    generate_chunks_for_file() for each. One file's failure is logged
    and skipped, never aborts the pass (same failure-isolation
    philosophy as index_search.py's rebuild()). dry_run reports what
    WOULD be (re-)chunked without calling the API or writing anything."""
    stats = {"chunked": 0, "unchanged": 0, "failed": 0, "skipped_no_embedding": 0}

    for course_name in list_courses(academic_hub_root):
        if course is not None and course_name != course:
            continue
        for card in load_shard(academic_hub_root, course_name):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                stats["skipped_no_embedding"] += 1
                continue
            if file is not None and not card["path"].endswith(file):
                continue

            if dry_run:
                existing = load_chunks(academic_hub_root, course_name)
                current = [c for c in existing if c["file_id"] == card["file_id"]]
                if current and all(c["content_hash"] == card["content_hash"] for c in current):
                    stats["unchanged"] += 1
                else:
                    stats["chunked"] += 1
                continue

            try:
                result = generate_chunks_for_file(academic_hub_root, course_name, card, client)
            except Exception as err:
                print(f"WARNING: chunking failed for {card['path']} ({err}); "
                      f"rerun `python index_search.py chunk` later to retry.")
                stats["failed"] += 1
                continue

            if result["chunks_written"] > 0:
                stats["chunked"] += 1
            else:
                stats["unchanged"] += 1

    return stats
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_chunk_index -v`
Expected: PASS (all tests from Tasks 1-9)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/chunk_index.py ai-sandbox/marker-conversion/tests/test_chunk_index.py
git commit -m "feat(chunks): add chunk() orchestration pass"
```

---

## Task 10: Add `file_id` to `SearchResult`

**Files:**
- Modify: `ai-sandbox/marker-conversion/index_search.py`
- Test: `ai-sandbox/marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Produces: `SearchResult.file_id: str` (new field, populated by `search()`)

**Why:** `search_passages()` (Task 11) needs to look up a file's chunks by `file_id` after `search()` finds the relevant files -- `SearchResult` currently only carries `path`, which isn't the chunk-lookup key. Confirmed live: no existing test constructs `SearchResult` directly or asserts on a closed field set, so adding a field is additive and safe.

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_index_search.py, inside class TestSearch

    def test_result_carries_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "xyz789", "path": "a.md", "course": "math-camp", "doc_type": "ta_notes",
                "embedding": [1.0, 0.0], "summary": "s",
            }])
            recompute_course_entry(tmp, "math-camp")
            client = MagicMock()
            embed_response = MagicMock()
            embedding = MagicMock()
            embedding.values = [1.0, 0.0]
            embed_response.embeddings = [embedding]
            client.models.embed_content.return_value = embed_response
            results = search(tmp, "query", client=client)
            self.assertEqual(results[0].file_id, "xyz789")
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: FAIL — `SearchResult` has no `file_id` attribute.

- [ ] **Step 3: Implement**

```python
# index_search.py -- modify the existing SearchResult dataclass and search()

@dataclass
class SearchResult:
    path: str
    course: str
    doc_type: str
    score: float
    reason: str
    file_id: str
```

```python
# In search(), the existing SearchResult(...) construction becomes:
            scored.append(SearchResult(
                path=result_path, course=card["course"], doc_type=card["doc_type"],
                score=score, reason=card.get("summary", ""), file_id=card["file_id"],
            ))
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: PASS (all existing tests plus the new one -- confirms the additive field change breaks nothing)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/index_search.py ai-sandbox/marker-conversion/tests/test_index_search.py
git commit -m "feat(search): add file_id to SearchResult"
```

---

## Task 11: `search_passages()` -- three-stage passage search

**Files:**
- Modify: `ai-sandbox/marker-conversion/index_search.py`
- Test: `ai-sandbox/marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `search()` (Task 10), `chunk_index.load_chunks`, `index_card.cosine_similarity`, `_embed_query` (already in `index_search.py`)
- Produces: `PassageResult` (dataclass: `chunk_id: str, file_id: str, path: str, course: str, score: float, text: str, citation: str`), `search_passages(academic_hub_root: str, query: str, client, course: str | None = None, top_k: int = 5, file_top_k: int = 5) -> list[PassageResult]`, `_render_citation(chunk: dict) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/test_index_search.py

from chunk_index import save_chunks
from index_search import PassageResult, search_passages, _render_citation


class TestRenderCitation(unittest.TestCase):
    def test_heading_tier_citation(self):
        chunk = {"tier": "heading", "heading_path": ["3", "3.7 Optimization"], "page_range": [44, 45], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "§3.7 Optimization, p. 44")

    def test_problem_number_tier_citation(self):
        chunk = {"tier": "problem_number", "heading_path": None, "page_range": [12, 12], "problem_label": "Problem 4"}
        self.assertEqual(_render_citation(chunk), "Problem 4, p. 12")

    def test_page_tier_citation(self):
        chunk = {"tier": "page", "heading_path": None, "page_range": [8, 8], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "p. 8")

    def test_multi_page_range_renders_as_a_span(self):
        chunk = {"tier": "page", "heading_path": None, "page_range": [8, 9], "problem_label": None}
        self.assertEqual(_render_citation(chunk), "p. 8-9")

    def test_no_page_range_falls_back_to_heading_or_label_only(self):
        chunk = {"tier": "heading", "heading_path": ["Intro"], "page_range": None, "problem_label": None}
        self.assertEqual(_render_citation(chunk), "§Intro")


class TestSearchPassages(unittest.TestCase):
    def test_ranks_passages_within_the_top_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "aaa", "path": "a.md", "course": "math-camp", "doc_type": "ta_notes",
                "embedding": [1.0, 0.0], "summary": "s",
            }])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": "aaa-000", "file_id": "aaa", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "close match", "embedding": [0.9, 0.1], "embedding_model": "m", "content_hash": "h"},
                {"chunk_id": "aaa-001", "file_id": "aaa", "chunk_index": 1, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [2, 2],
                 "text": "far match", "embedding": [0.0, 1.0], "embedding_model": "m", "content_hash": "h"},
            ])
            client = MagicMock()
            embed_response = MagicMock()
            embedding = MagicMock()
            embedding.values = [1.0, 0.0]
            embed_response.embeddings = [embedding]
            client.models.embed_content.return_value = embed_response

            results = search_passages(tmp, "query", client=client)
            self.assertEqual(results[0].text, "close match")
            self.assertGreater(results[0].score, results[1].score)
            self.assertEqual(results[0].file_id, "aaa")
            self.assertEqual(results[0].chunk_id, "aaa-000")

    def test_file_with_no_chunks_yet_is_skipped_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "aaa", "path": "a.md", "course": "math-camp", "doc_type": "ta_notes",
                "embedding": [1.0, 0.0], "summary": "s",
            }])
            recompute_course_entry(tmp, "math-camp")
            # No save_chunks() call at all -- chunk hasn't been run yet.
            client = MagicMock()
            embed_response = MagicMock()
            embedding = MagicMock()
            embedding.values = [1.0, 0.0]
            embed_response.embeddings = [embedding]
            client.models.embed_content.return_value = embed_response

            results = search_passages(tmp, "query", client=client)
            self.assertEqual(results, [])

    def test_top_k_limits_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{
                "file_id": "aaa", "path": "a.md", "course": "math-camp", "doc_type": "ta_notes",
                "embedding": [1.0, 0.0], "summary": "s",
            }])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": f"aaa-{i:03d}", "file_id": "aaa", "chunk_index": i, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [i, i],
                 "text": f"chunk {i}", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"}
                for i in range(5)
            ])
            client = MagicMock()
            embed_response = MagicMock()
            embedding = MagicMock()
            embedding.values = [1.0, 0.0]
            embed_response.embeddings = [embedding]
            client.models.embed_content.return_value = embed_response

            results = search_passages(tmp, "query", client=client, top_k=2)
            self.assertEqual(len(results), 2)
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: FAIL — `PassageResult`/`search_passages`/`_render_citation` don't exist yet.

- [ ] **Step 3: Implement**

```python
# index_search.py -- add near SearchResult

@dataclass
class PassageResult:
    chunk_id: str
    file_id: str
    path: str
    course: str
    score: float
    text: str
    citation: str


def _render_citation(chunk: dict) -> str:
    parts = []
    if chunk.get("heading_path"):
        parts.append(f"§{chunk['heading_path'][-1]}")
    elif chunk.get("problem_label"):
        parts.append(chunk["problem_label"])
    page_range = chunk.get("page_range")
    if page_range:
        start, end = page_range
        parts.append(f"p. {start}" if start == end else f"p. {start}-{end}")
    return ", ".join(parts)


def search_passages(
    academic_hub_root: str, query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5,
) -> list[PassageResult]:
    """Three-stage funnel (spec §6): reuses search() for the file-level
    pass (100% of the existing course-then-file filtering, not
    duplicated), then ranks that shortlist's chunks by cosine similarity
    to the same query embedding. A file with no chunks yet (chunk
    hasn't been run against it) contributes nothing and is silently
    skipped, not an error -- degrades gracefully during the transition
    period before `chunk` has been run corpus-wide."""
    file_results = search(academic_hub_root, query, client, course=course, top_k=file_top_k)
    if not file_results:
        return []

    query_embedding = _embed_query(query, client)
    chunks_by_course: dict[str, list[dict]] = {}
    scored: list[PassageResult] = []
    for file_result in file_results:
        if file_result.course not in chunks_by_course:
            chunks_by_course[file_result.course] = load_chunks(academic_hub_root, file_result.course)
        for c in chunks_by_course[file_result.course]:
            if c["file_id"] != file_result.file_id:
                continue
            score = cosine_similarity(query_embedding, c["embedding"])
            scored.append(PassageResult(
                chunk_id=c["chunk_id"], file_id=c["file_id"], path=file_result.path,
                course=file_result.course, score=score, text=c["text"],
                citation=_render_citation(c),
            ))

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:top_k]
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: PASS (all tests from Task 10-11 plus every pre-existing test)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/index_search.py ai-sandbox/marker-conversion/tests/test_index_search.py
git commit -m "feat(search): add search_passages() three-stage passage search"
```

---

## Task 12: CLI wiring -- `chunk` subcommand and `query --passages`

**Files:**
- Modify: `ai-sandbox/marker-conversion/index_search.py`
- Test: `ai-sandbox/marker-conversion/tests/test_index_search.py`

**Interfaces:**
- Consumes: `chunk_index.chunk` (Task 9), `search_passages` (Task 11), the existing `build_arg_parser()`/`main()`

- [ ] **Step 1: Write the failing tests**

```python
# Add to tests/test_index_search.py, inside class TestCLIArgParsing

    def test_chunk_subcommand_defaults(self):
        parser = build_arg_parser()
        args = parser.parse_args(["chunk"])
        self.assertEqual(args.command, "chunk")
        self.assertIsNone(args.course)
        self.assertIsNone(args.file)
        self.assertFalse(args.dry_run)

    def test_chunk_subcommand_with_flags(self):
        parser = build_arg_parser()
        args = parser.parse_args(["chunk", "--course", "math-camp", "--file", "a.md", "--dry-run"])
        self.assertEqual(args.course, "math-camp")
        self.assertEqual(args.file, "a.md")
        self.assertTrue(args.dry_run)

    def test_query_passages_flag(self):
        parser = build_arg_parser()
        args = parser.parse_args(["query", "something", "--passages"])
        self.assertTrue(args.passages)

    def test_query_passages_flag_defaults_false(self):
        parser = build_arg_parser()
        args = parser.parse_args(["query", "something"])
        self.assertFalse(args.passages)
```

- [ ] **Step 2: Run to verify failure**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: FAIL — `chunk` isn't a valid subcommand, `--passages` isn't a valid `query` flag yet.

- [ ] **Step 3: Implement**

`build_arg_parser()`'s current, real, complete body (as of this plan being written):

```python
def build_arg_parser() -> argparse.ArgumentParser:
    default_root = os.path.join(os.path.dirname(__file__), "..", "academic-hub")
    parser = argparse.ArgumentParser(description="Search and maintain the academic-hub source index.")
    parser.add_argument("--academic-hub", default=default_root, help="Path to the academic-hub root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Search the index for relevant sources.")
    query.add_argument("query")
    query.add_argument("--course", default=None)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--doc-type", default=None)
    query.add_argument("--has-solutions", type=_bool_arg, default=None)
    query.add_argument("--max-level", default=None, choices=list(KNOWN_LEVELS))

    rebuild_p = subparsers.add_parser("rebuild", help="Backfill/reconcile index cards.")
    rebuild_p.add_argument("--course", default=None)
    rebuild_p.add_argument("--force", action="store_true")
    rebuild_p.add_argument("--prune", action="store_true")

    retag_p = subparsers.add_parser("retag", help="Mine and apply tags across the whole corpus.")
    retag_p.add_argument("--dry-run", action="store_true")

    return parser
```

Replace it with (two additions: `query.add_argument("--passages", ...)` inserted into the existing `query` block, and a new `chunk_p` subparser block inserted after `retag_p`, before `return parser`):

```python
def build_arg_parser() -> argparse.ArgumentParser:
    default_root = os.path.join(os.path.dirname(__file__), "..", "academic-hub")
    parser = argparse.ArgumentParser(description="Search and maintain the academic-hub source index.")
    parser.add_argument("--academic-hub", default=default_root, help="Path to the academic-hub root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Search the index for relevant sources.")
    query.add_argument("query")
    query.add_argument("--course", default=None)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--doc-type", default=None)
    query.add_argument("--has-solutions", type=_bool_arg, default=None)
    query.add_argument("--max-level", default=None, choices=list(KNOWN_LEVELS))
    query.add_argument("--passages", action="store_true",
                        help="Return passage-level results instead of file-level results.")

    rebuild_p = subparsers.add_parser("rebuild", help="Backfill/reconcile index cards.")
    rebuild_p.add_argument("--course", default=None)
    rebuild_p.add_argument("--force", action="store_true")
    rebuild_p.add_argument("--prune", action="store_true")

    retag_p = subparsers.add_parser("retag", help="Mine and apply tags across the whole corpus.")
    retag_p.add_argument("--dry-run", action="store_true")

    chunk_p = subparsers.add_parser("chunk", help="Chunk and embed indexed files into citable passages.")
    chunk_p.add_argument("--course", default=None)
    chunk_p.add_argument("--file", default=None)
    chunk_p.add_argument("--dry-run", action="store_true")

    return parser
```

`main()`'s current, real, complete body:

```python
def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "query":
        results = search(
            args.academic_hub, args.query, client, course=args.course, top_k=args.top_k,
            doc_type=args.doc_type, has_solutions=args.has_solutions, max_level=args.max_level,
        )
        for r in results:
            print(f"{r.score:.3f}  [{r.course}/{r.doc_type}]  {r.path}\n    {r.reason}")
    elif args.command == "rebuild":
        stats = rebuild(args.academic_hub, client, course=args.course, force=args.force, prune=args.prune)
        print(stats)
    elif args.command == "retag":
        stats = retag(args.academic_hub, client, dry_run=args.dry_run)
        print(stats)
```

Replace the `if args.command == "query":` branch and add a new `elif args.command == "chunk":` branch after the existing `retag` branch:

```python
def main() -> None:
    args = build_arg_parser().parse_args()
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        raise SystemExit(1)

    if args.command == "query":
        if args.passages:
            results = search_passages(args.academic_hub, args.query, client, course=args.course, top_k=args.top_k)
            for r in results:
                print(f"{r.score:.3f}  [{r.course}]  {r.path}  ({r.citation})\n    {r.text[:200]}")
        else:
            results = search(
                args.academic_hub, args.query, client, course=args.course, top_k=args.top_k,
                doc_type=args.doc_type, has_solutions=args.has_solutions, max_level=args.max_level,
            )
            for r in results:
                print(f"{r.score:.3f}  [{r.course}/{r.doc_type}]  {r.path}\n    {r.reason}")
    elif args.command == "rebuild":
        stats = rebuild(args.academic_hub, client, course=args.course, force=args.force, prune=args.prune)
        print(stats)
    elif args.command == "retag":
        stats = retag(args.academic_hub, client, dry_run=args.dry_run)
        print(stats)
    elif args.command == "chunk":
        stats = chunk(args.academic_hub, client, course=args.course, file=args.file, dry_run=args.dry_run)
        print(stats)
```

`search_passages` is already in scope (defined in this same file, Task 11). Add `chunk` to the top-of-file import instead of importing it inline: `chunk_index.py` does not import `index_search.py`, so there's no circularity — `from retag import retag` at the top of `index_search.py` becomes:

```python
from chunk_index import chunk
from retag import retag
```

- [ ] **Step 4: Run to verify pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_index_search -v`
Expected: PASS (all tests, this task's new ones plus every pre-existing test in the file)

- [ ] **Step 5: Run the full suite**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests`
Expected: PASS, every test in the project (not just the two files touched this plan)

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/marker-conversion/index_search.py ai-sandbox/marker-conversion/tests/test_index_search.py
git commit -m "feat(cli): add chunk subcommand and query --passages flag"
```

---

## After This Plan

Not part of this plan (deliberately, per spec §9 and this plan's own scope):
- Running `chunk` for real against the live `academic-hub` corpus (a real-data validation step, follow this session's established pattern: `chunk --dry-run` first, spot-check a few real chunks by hand, then a real run) -- do this once the plan above is fully implemented and tested, as a separate follow-up action, not a plan task.
- Wiring `chunk` into any pipeline hook (explicitly deferred, spec §2/§9).
- Cross-chunk deduplication, chunk-level tags, ANN indexing (all spec §9, explicitly not built here).
