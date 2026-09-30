# Notes-Transcription Post-Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `postprocess_notes.py`, a downstream correction pass over `transcribe_notes.py`'s already-produced `.md` files that catches errors on local-only pages (pages never seen by a vision model), auto-corrects high-confidence findings in place, and surfaces review only for genuine patterns rather than every instance.

**Architecture:** Pure-logic pieces (frontmatter/page parsing, candidate-pool derivation, suppression, structural pre-filtering, pattern aggregation, cross-reference search) live in two dependency-free modules, unit-tested directly. Local-model scoring (masked-LM + causal z-score) lives in its own module that imports `transformers`/`torch` only inside its functions, matching this project's existing discipline, and is validated against real documents rather than unit-tested (same split this project already uses for PyMuPDF/network code). The CLI driver wires everything together and reuses `transcribe_notes.py`'s existing, already-validated repair machinery for verification — confidence comes from re-checking a flagged page against its real source image, never from a model's self-reported score on text alone.

**Tech Stack:** Python 3.13, `transformers` + `torch` (CPU) for local model scoring, `PyMuPDF` for page rendering/dict-mode text, `google-genai` (via `gemini_utils.py`) for verification calls, `PyYAML` (already present in this venv, `6.0.3`) for frontmatter parsing, stdlib `unittest` for tests.

**Spec:** `ai-sandbox/marker-conversion/docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md`

## Global Constraints

- Textbook output is never a correction target (no `routing` field in its frontmatter is exactly how it's distinguished from notes output).
- Multiple detection signal sources are kept side by side, not narrowed to one — this is deliberate, per the spec's explicit "test them all in production" direction.
- No dependency on RAG Analysis's retrieval (not built yet); cross-referencing is plain keyword search only.
- Never surface a review prompt for a single low-confidence finding — only when a document crosses the pattern-review threshold.
- Every applied fix is logged to `<name>_postprocess_log.json`; nothing is silently altered without a record.
- A document is marked `postprocessed: true` in its own frontmatter the moment its correction pass finishes — this is the only "already handled" tracking mechanism; no separate state file.

---

### Task 1: Rename four cross-module helpers from private to public in `transcribe_notes.py`

`postprocess_notes.py` (Task 9) needs to import `is_expected_char`, `ALLOWED_MATH_RANGES`, `repair_page_individually`, and `repair_batch` from `transcribe_notes.py`. They're currently underscore-prefixed, signaling module-private — since they're about to become a real cross-module interface, the leading underscore should come off. Pure rename, zero behavior change, verified by the existing test suite staying green.

**Files:**
- Modify: `transcribe_notes.py` (11 occurrences across lines 98, 308, 314, 374, 742, 753, 838, 851, 877 (comment), 909, 923)

**Interfaces:**
- Produces: `ALLOWED_MATH_RANGES` (tuple of `(int, int)` ranges), `is_expected_char(c: str) -> bool`, `repair_batch(client, model: str, pdf_path: str, batch: list[int], prompt: str) -> dict[int, str]`, `repair_page_individually(client, model: str, pdf_path: str, page_num: int, hint_text: str, total_pages: int) -> str` — all four now importable by name from `transcribe_notes` by later tasks.

- [ ] **Step 1: Confirm current test baseline passes**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest discover -s tests`
Expected: `OK` (160 tests, matching the count before this change — this is the baseline to diff against after the rename)

- [ ] **Step 2: Rename `_ALLOWED_MATH_RANGES` to `ALLOWED_MATH_RANGES`**

In `transcribe_notes.py`, change the definition at line 98 (`_ALLOWED_MATH_RANGES = (`) to `ALLOWED_MATH_RANGES = (`, and its one internal reference at line 314 (`return any(lo <= cp <= hi for lo, hi in _ALLOWED_MATH_RANGES)`) to use `ALLOWED_MATH_RANGES`.

- [ ] **Step 3: Rename `_is_expected_char` to `is_expected_char`**

Change the `def _is_expected_char(c: str) -> bool:` at line 308 to `def is_expected_char(c: str) -> bool:`, and its one call site at line 374 (`not _is_expected_char(c)`) to `not is_expected_char(c)`.

- [ ] **Step 4: Rename `_repair_batch` to `repair_batch`**

Change `def _repair_batch(...)` at line 742 to `def repair_batch(...)`, and both call sites (originally lines 838 and 909, inside `lambda: _repair_batch(...)`) to `repair_batch(...)`. Also update the explanatory comment near line 877 that mentions `_repair_batch` by name.

- [ ] **Step 5: Rename `_repair_page_individually` to `repair_page_individually`**

Change `def _repair_page_individually(...)` at line 753 to `def repair_page_individually(...)`, and both call sites (originally lines 851 and 923, `cache[str(p)] = _repair_page_individually(...)`) to `repair_page_individually(...)`.

- [ ] **Step 6: Run the full test suite to confirm zero behavior change**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest discover -s tests`
Expected: `OK` (same 160 tests as Step 1 — a rename touches no logic, so any new failure here means a reference was missed)

- [ ] **Step 7: Commit**

```bash
git add ai-sandbox/marker-conversion/transcribe_notes.py
git commit -m "Rename is_expected_char/ALLOWED_MATH_RANGES/repair_batch/repair_page_individually to public

These four are about to become a real cross-module interface for
postprocess_notes.py (suppression layer and verification step). Pure
rename, zero behavior change -- full test suite confirmed still green."
```

---

### Task 2: `postprocess_discovery.py` — frontmatter/page parsing and candidate-pool derivation

**Files:**
- Create: `postprocess_discovery.py`
- Test: `tests/test_postprocess_discovery.py`

**Interfaces:**
- Consumes: nothing from other new modules.
- Produces: `parse_frontmatter(md_text: str) -> tuple[dict, str]`, `split_pages_by_tag(body: str) -> dict[int, str]`, `derive_eligible_pages(frontmatter: dict) -> list[int]`, `is_correction_target(frontmatter: dict) -> bool` — all consumed by Task 9.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_postprocess_discovery.py
import unittest

from postprocess_discovery import (
    derive_eligible_pages,
    is_correction_target,
    parse_frontmatter,
    split_pages_by_tag,
)


class TestParseFrontmatter(unittest.TestCase):
    def test_splits_real_hybrid_frontmatter_from_body(self):
        md_text = (
            "---\n"
            "source_pdf: Practice Sheet.pdf\n"
            "folder_category: problem_sets\n"
            "total_pages: 43\n"
            "routing: hybrid\n"
            "model: gemini-3.1-flash-lite\n"
            "pages_repaired: 2\n"
            "repaired_pages: [35, 43]\n"
            "tags: []\n"
            "---\n\n"
            "<!-- page 1 -->\n\nHello."
        )
        metadata, body = parse_frontmatter(md_text)
        self.assertEqual(metadata["routing"], "hybrid")
        self.assertEqual(metadata["total_pages"], 43)
        self.assertEqual(metadata["repaired_pages"], [35, 43])
        self.assertEqual(body, "<!-- page 1 -->\n\nHello.")

    def test_missing_frontmatter_returns_empty_dict_and_full_text(self):
        # Real case: Analysis_Exercises.md before its 2026-08-26 re-run
        # had no frontmatter block at all.
        md_text = "<!-- page 1 -->\n\nAnalysis: Guided Exercises"
        metadata, body = parse_frontmatter(md_text)
        self.assertEqual(metadata, {})
        self.assertEqual(body, md_text)


class TestSplitPagesByTag(unittest.TestCase):
    def test_splits_multiple_pages_by_their_tags(self):
        body = "<!-- page 1 -->\n\nFirst.\n\n<!-- page 2 -->\n\nSecond."
        pages = split_pages_by_tag(body)
        self.assertEqual(pages[1], "First.")
        self.assertEqual(pages[2], "Second.")

    def test_single_page_body(self):
        body = "<!-- page 1 -->\n\nOnly page."
        pages = split_pages_by_tag(body)
        self.assertEqual(pages, {1: "Only page."})

    def test_empty_body_returns_empty_dict(self):
        self.assertEqual(split_pages_by_tag(""), {})


class TestDeriveEligiblePages(unittest.TestCase):
    def test_local_routing_makes_every_page_eligible(self):
        frontmatter = {"routing": "local", "total_pages": 5}
        self.assertEqual(derive_eligible_pages(frontmatter), [1, 2, 3, 4, 5])

    def test_hybrid_routing_excludes_repaired_pages(self):
        frontmatter = {"routing": "hybrid", "total_pages": 5, "repaired_pages": [2, 4]}
        self.assertEqual(derive_eligible_pages(frontmatter), [1, 3, 5])

    def test_gemini_batched_has_no_eligible_pages(self):
        # Already fully model-verified -- nothing left for this pass to check.
        frontmatter = {"routing": "gemini_batched", "total_pages": 43, "repaired_pages": [1, 2, 3]}
        self.assertEqual(derive_eligible_pages(frontmatter), [])

    def test_gemini_accumulating_has_no_eligible_pages(self):
        frontmatter = {"routing": "gemini_accumulating", "total_pages": 25}
        self.assertEqual(derive_eligible_pages(frontmatter), [])

    def test_missing_routing_has_no_eligible_pages(self):
        # Textbook output, or any file without this project's own routing field.
        self.assertEqual(derive_eligible_pages({"total_pages": 300}), [])

    def test_missing_total_pages_has_no_eligible_pages(self):
        self.assertEqual(derive_eligible_pages({"routing": "local"}), [])


class TestIsCorrectionTarget(unittest.TestCase):
    def test_notes_document_not_yet_postprocessed_is_a_target(self):
        self.assertTrue(is_correction_target({"routing": "hybrid"}))

    def test_already_postprocessed_document_is_not_a_target(self):
        self.assertFalse(is_correction_target({"routing": "hybrid", "postprocessed": True}))

    def test_textbook_output_without_routing_is_not_a_target(self):
        self.assertFalse(is_correction_target({"total_pages": 300}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_discovery -v`
Expected: `ModuleNotFoundError: No module named 'postprocess_discovery'`

- [ ] **Step 3: Write the implementation**

```python
# postprocess_discovery.py
"""
Frontmatter/page parsing and candidate-pool derivation for
postprocess_notes.py -- see
docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Pure Python, no PyMuPDF/transformers/network import at module scope,
matching chapter_index.py/page_markers.py's dependency-free-module
pattern in this project.
"""
from __future__ import annotations

import re

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n\n?", re.DOTALL)
_PAGE_TAG_RE = re.compile(r"<!-- page (\d+) -->\n\n")


def parse_frontmatter(md_text: str) -> tuple[dict, str]:
    """
    Splits a transcribe_notes.py-produced .md file's leading YAML
    frontmatter block from its body. Returns ({}, md_text unchanged) for
    any file with no frontmatter block at all -- a normal, expected case
    (e.g. Analysis_Exercises.md before its 2026-08-26 re-run, or any
    textbook output this project doesn't control the format of), not an
    error condition.
    """
    match = _FRONTMATTER_RE.match(md_text)
    if not match:
        return {}, md_text
    metadata = yaml.safe_load(match.group(1)) or {}
    body = md_text[match.end():]
    return metadata, body


def split_pages_by_tag(body: str) -> dict[int, str]:
    """
    Inverse of transcribe_notes.py's build_final_markdown: splits a
    <!-- page N --> tagged body back into {page_number: page_text}.
    """
    matches = list(_PAGE_TAG_RE.finditer(body))
    pages: dict[int, str] = {}
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        pages[page_num] = body[start:end].rstrip("\n")
    return pages


def derive_eligible_pages(frontmatter: dict) -> list[int]:
    """
    Local-only pages eligible for post-processing, per the design spec's
    table: routing="local" -> every page; routing="hybrid" -> every page
    except repaired_pages; anything else (gemini_batched,
    gemini_accumulating, or missing routing entirely -- textbook output)
    -> no eligible pages, since those are already fully model-verified
    or aren't a notes-transcription document at all.
    """
    routing = frontmatter.get("routing")
    total_pages = frontmatter.get("total_pages")
    if not isinstance(total_pages, int) or total_pages < 1:
        return []
    if routing == "local":
        return list(range(1, total_pages + 1))
    if routing == "hybrid":
        repaired = set(frontmatter.get("repaired_pages") or [])
        return [p for p in range(1, total_pages + 1) if p not in repaired]
    return []


def is_correction_target(frontmatter: dict) -> bool:
    """
    True for a notes-transcription document (has a "routing" field --
    textbook output never does) that hasn't already been through this
    post-processing pass.
    """
    return "routing" in frontmatter and not frontmatter.get("postprocessed", False)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_discovery -v`
Expected: `OK` (14 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_discovery.py ai-sandbox/marker-conversion/tests/test_postprocess_discovery.py
git commit -m "Add postprocess_discovery.py: frontmatter/page parsing and candidate-pool derivation"
```

---

### Task 3: `postprocess_discovery.py` — recursive document discovery

**Files:**
- Modify: `postprocess_discovery.py`
- Test: `tests/test_postprocess_discovery.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `discover_markdown_files(root_dirs: list[str]) -> list[str]` — consumed by Task 9.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_postprocess_discovery.py
import os
import tempfile


class TestDiscoverMarkdownFiles(unittest.TestCase):
    def test_finds_md_files_only_under_processed_outputs_folders(self):
        with tempfile.TemporaryDirectory() as root:
            po1 = os.path.join(root, "problem_sets", "processed_outputs")
            po2 = os.path.join(root, "ta_notes", "processed_outputs")
            os.makedirs(po1)
            os.makedirs(po2)
            open(os.path.join(po1, "Practice Sheet.md"), "w").close()
            open(os.path.join(po2, "LN_Analysis.md"), "w").close()
            # A markdown file OUTSIDE any processed_outputs/ folder must not
            # be picked up -- e.g. a stray README living under the same root.
            open(os.path.join(root, "README.md"), "w").close()

            found = discover_markdown_files([root])

            self.assertEqual(len(found), 2)
            self.assertTrue(any(f.endswith("Practice Sheet.md") for f in found))
            self.assertTrue(any(f.endswith("LN_Analysis.md") for f in found))

    def test_multiple_root_dirs_in_one_call(self):
        with tempfile.TemporaryDirectory() as root1, tempfile.TemporaryDirectory() as root2:
            po1 = os.path.join(root1, "processed_outputs")
            po2 = os.path.join(root2, "processed_outputs")
            os.makedirs(po1)
            os.makedirs(po2)
            open(os.path.join(po1, "a.md"), "w").close()
            open(os.path.join(po2, "b.md"), "w").close()

            found = discover_markdown_files([root1, root2])

            self.assertEqual(len(found), 2)

    def test_no_processed_outputs_folder_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(discover_markdown_files([root]), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_discovery.TestDiscoverMarkdownFiles -v`
Expected: `ImportError: cannot import name 'discover_markdown_files'`

- [ ] **Step 3: Write the implementation**

```python
# add to postprocess_discovery.py, near the top with the other imports
import os
```

```python
# add to postprocess_discovery.py, after is_correction_target
def discover_markdown_files(root_dirs: list[str]) -> list[str]:
    """
    Recursively finds every .md file under any processed_outputs/ folder
    beneath the given root directories -- so problem_sets, ta_notes,
    handwritten_notes, and any future course folder are all picked up in
    one call without enumerating them by name. Deliberately narrow (only
    inside processed_outputs/ folders) to avoid accidentally picking up
    unrelated markdown files (READMEs, design specs) that happen to live
    under the same root.
    """
    found = []
    for root_dir in root_dirs:
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            if os.path.basename(dirpath) != "processed_outputs":
                continue
            for name in sorted(filenames):
                if name.lower().endswith(".md"):
                    found.append(os.path.join(dirpath, name))
    return sorted(found)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_discovery -v`
Expected: `OK` (17 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_discovery.py ai-sandbox/marker-conversion/tests/test_postprocess_discovery.py
git commit -m "Add discover_markdown_files to postprocess_discovery.py"
```

---

### Task 4: `postprocess_findings.py` — suppression layer and structural pre-filter

**Files:**
- Create: `postprocess_findings.py`
- Test: `tests/test_postprocess_findings.py`

**Interfaces:**
- Consumes: `is_expected_char` from `transcribe_notes` (Task 1's renamed public function).
- Produces: `is_allowlisted_span(text: str) -> bool`, `find_isolated_candidate_spans(lines: list[list[dict]]) -> list[dict]` — consumed by Task 9.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_postprocess_findings.py
import unittest

from postprocess_findings import find_isolated_candidate_spans, is_allowlisted_span


class TestIsAllowlistedSpan(unittest.TestCase):
    def test_ordinary_ascii_letter_is_allowlisted(self):
        # Confirmed real finding: the allowlist can't distinguish the
        # radical-as-p bug from any other ordinary ASCII letter -- both
        # pass this check. Suppression only helps the *other* false-
        # positive class (see the next tests).
        self.assertTrue(is_allowlisted_span("p"))

    def test_greek_letter_is_allowlisted(self):
        # Real case from the design spike: xi/eta are legitimate math
        # notation, already covered by transcribe_notes.py's own
        # ALLOWED_MATH_RANGES (Greek and Coptic).
        self.assertTrue(is_allowlisted_span("ξ"))  # xi

    def test_private_use_area_character_is_not_allowlisted(self):
        self.assertFalse(is_allowlisted_span(""))

    def test_whitespace_only_span_is_allowlisted(self):
        self.assertTrue(is_allowlisted_span("   "))


class TestFindIsolatedCandidateSpans(unittest.TestCase):
    def test_single_span_line_with_one_character_is_a_candidate(self):
        # Real case: Analysis_Exercises.pdf page 6, a radical sign
        # extracting as a standalone "p" on its own line.
        lines = [[{"text": "p", "origin": (100.0, 200.0)}]]
        candidates = find_isolated_candidate_spans(lines)
        self.assertEqual(candidates, [{"text": "p", "origin": (100.0, 200.0)}])

    def test_multi_span_line_is_not_a_candidate(self):
        lines = [[{"text": "5. Divide by", "origin": (0.0, 0.0)}, {"text": " ", "origin": (0.0, 0.0)}]]
        self.assertEqual(find_isolated_candidate_spans(lines), [])

    def test_single_span_multi_character_line_is_not_a_candidate(self):
        lines = [[{"text": "h^2 + k^2", "origin": (0.0, 0.0)}]]
        self.assertEqual(find_isolated_candidate_spans(lines), [])

    def test_empty_lines_list_returns_empty(self):
        self.assertEqual(find_isolated_candidate_spans([]), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings -v`
Expected: `ModuleNotFoundError: No module named 'postprocess_findings'`

- [ ] **Step 3: Write the implementation**

```python
# postprocess_findings.py
"""
Detection-support and finding-management logic for postprocess_notes.py
-- see docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Pure Python, no PyMuPDF/transformers/network import at module scope.
"""
from __future__ import annotations

from transcribe_notes import is_expected_char


def is_allowlisted_span(text: str) -> bool:
    """
    True if every non-whitespace character in this span is already
    covered by transcribe_notes.py's own is_expected_char allowlist --
    the suppression signal confirmed necessary in the design spike: a
    candidate whose actual character is a legitimate math-range symbol
    (e.g. a Greek letter) must never be flagged, regardless of how
    surprising a small local model finds it. Confirmed in the same spike
    that this does NOT help distinguish an ordinary-but-wrong ASCII
    character (the ALLOWED_MATH_RANGES/is_expected_char check treats all
    ASCII as expected) -- that class of error relies on the model-based
    signals in local_model_scoring.py instead, not this suppression
    layer.
    """
    stripped = text.strip()
    if not stripped:
        return True
    return all(is_expected_char(c) for c in stripped)


def find_isolated_candidate_spans(lines: list[list[dict]]) -> list[dict]:
    """
    Structural pre-filter: a line consisting of exactly one span, whose
    text (stripped) is exactly one character, is structurally what a
    stripped operator/delimiter glyph looks like once mis-mapped to an
    ordinary character (confirmed real case: Analysis_Exercises.pdf page
    6, a radical sign extracting as a standalone "p" on its own line).
    `lines` is a list of PyMuPDF dict-mode lines, each a list of span
    dicts (the same shape reconstruct_line_with_scripts() already
    consumes). Zero-cost, no model involved -- this is one of three
    complementary detection signals (see local_model_scoring.py for the
    other two), not expected to be the only one.
    """
    candidates = []
    for spans in lines:
        if len(spans) != 1:
            continue
        text = spans[0].get("text", "").strip()
        if len(text) == 1:
            candidates.append({"text": text, "origin": spans[0].get("origin")})
    return candidates
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings -v`
Expected: `OK` (8 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_findings.py ai-sandbox/marker-conversion/tests/test_postprocess_findings.py
git commit -m "Add postprocess_findings.py: allowlist suppression and structural pre-filter"
```

---

### Task 5: `postprocess_findings.py` — pattern-level aggregation and review threshold

**Files:**
- Modify: `postprocess_findings.py`
- Test: `tests/test_postprocess_findings.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `group_findings_by_signature(findings: list[dict]) -> dict[str, list[dict]]`, `documents_needing_review(grouped: dict[str, list[dict]], threshold: int) -> list[str]` — consumed by Task 9. Each finding dict must have `"document"` and `"flagged_text"` keys.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_postprocess_findings.py
from postprocess_findings import documents_needing_review, group_findings_by_signature


class TestGroupFindingsBySignature(unittest.TestCase):
    def test_groups_same_text_same_document_together(self):
        findings = [
            {"document": "a.md", "flagged_text": "p"},
            {"document": "a.md", "flagged_text": "p"},
            {"document": "a.md", "flagged_text": "q"},
        ]
        grouped = group_findings_by_signature(findings)
        self.assertEqual(len(grouped["a.md::p"]), 2)
        self.assertEqual(len(grouped["a.md::q"]), 1)

    def test_same_text_different_documents_stay_separate(self):
        findings = [
            {"document": "a.md", "flagged_text": "p"},
            {"document": "b.md", "flagged_text": "p"},
        ]
        grouped = group_findings_by_signature(findings)
        self.assertEqual(len(grouped), 2)


class TestDocumentsNeedingReview(unittest.TestCase):
    def test_document_crossing_threshold_is_flagged(self):
        grouped = {
            "a.md::p": [{"document": "a.md", "flagged_text": "p"}] * 5,
        }
        self.assertEqual(documents_needing_review(grouped, threshold=5), ["a.md"])

    def test_document_below_threshold_is_not_flagged(self):
        # This is the explicit requirement this design exists to satisfy:
        # don't surface a review for every single potentially-corrupted
        # character, only for a real pattern.
        grouped = {
            "a.md::p": [{"document": "a.md", "flagged_text": "p"}] * 2,
        }
        self.assertEqual(documents_needing_review(grouped, threshold=5), [])

    def test_no_findings_returns_empty_list(self):
        self.assertEqual(documents_needing_review({}, threshold=5), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings.TestGroupFindingsBySignature tests.test_postprocess_findings.TestDocumentsNeedingReview -v`
Expected: `ImportError: cannot import name 'group_findings_by_signature'`

- [ ] **Step 3: Write the implementation**

```python
# add to postprocess_findings.py
def group_findings_by_signature(findings: list[dict]) -> dict[str, list[dict]]:
    """
    Groups low-confidence findings by document + flagged text, so
    repeated instances of the same kind of thing in the same document
    cluster together rather than each counting as its own isolated data
    point.
    """
    groups: dict[str, list[dict]] = {}
    for finding in findings:
        key = f"{finding['document']}::{finding['flagged_text']}"
        groups.setdefault(key, []).append(finding)
    return groups


def documents_needing_review(grouped: dict[str, list[dict]], threshold: int) -> list[str]:
    """
    Documents where at least one finding signature recurs `threshold`+
    times -- a genuine pattern, not an isolated one-off. Below that, a
    finding is logged (see build_changelog_entry) but never surfaced --
    the explicit requirement this exists to satisfy: don't review every
    single potentially-corrupted character across hundreds of pages.
    """
    documents = set()
    for group_findings in grouped.values():
        if len(group_findings) >= threshold:
            documents.update(f["document"] for f in group_findings)
    return sorted(documents)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings -v`
Expected: `OK` (13 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_findings.py ai-sandbox/marker-conversion/tests/test_postprocess_findings.py
git commit -m "Add pattern-level aggregation to postprocess_findings.py"
```

---

### Task 6: `postprocess_findings.py` — cross-reference keyword search

**Files:**
- Modify: `postprocess_findings.py`
- Test: `tests/test_postprocess_findings.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `search_reference_documents(term: str, reference_texts: dict[str, str], context_chars: int = 80) -> list[dict]` — consumed by Task 9.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_postprocess_findings.py
from postprocess_findings import search_reference_documents


class TestSearchReferenceDocuments(unittest.TestCase):
    def test_finds_term_with_surrounding_context(self):
        refs = {"textbook.md": "The Hessian matrix H_f(x) is symmetric under mild conditions."}
        matches = search_reference_documents("Hessian", refs, context_chars=10)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["document"], "textbook.md")
        self.assertIn("Hessian", matches[0]["context"])

    def test_case_insensitive(self):
        refs = {"a.md": "the hessian matrix"}
        matches = search_reference_documents("Hessian", refs)
        self.assertEqual(len(matches), 1)

    def test_finds_multiple_occurrences_across_documents(self):
        refs = {"a.md": "Hessian here.", "b.md": "Hessian there too."}
        matches = search_reference_documents("Hessian", refs)
        self.assertEqual(len(matches), 2)

    def test_no_match_returns_empty_list(self):
        refs = {"a.md": "no relevant content"}
        self.assertEqual(search_reference_documents("Hessian", refs), [])

    def test_blank_term_returns_empty_list(self):
        self.assertEqual(search_reference_documents("   ", {"a.md": "text"}), [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings.TestSearchReferenceDocuments -v`
Expected: `ImportError: cannot import name 'search_reference_documents'`

- [ ] **Step 3: Write the implementation**

```python
# add to postprocess_findings.py
def search_reference_documents(
    term: str, reference_texts: dict[str, str], context_chars: int = 80,
) -> list[dict]:
    """
    Plain substring search for `term` across every reference document's
    text, returning each match's surrounding context -- deliberately not
    semantic/vector search, since RAG Analysis (this project's sibling
    for that) isn't built yet; see the design spec's explicit decision to
    keep this self-contained rather than depend on it. Case-insensitive,
    since the same term can legitimately vary in case across documents
    written by different people. `reference_texts` maps document path to
    its full text.
    """
    term_lower = term.lower()
    if not term_lower.strip():
        return []
    matches = []
    for doc_path, text in reference_texts.items():
        text_lower = text.lower()
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break
            ctx_start = max(0, idx - context_chars)
            ctx_end = min(len(text), idx + len(term) + context_chars)
            matches.append({"document": doc_path, "context": text[ctx_start:ctx_end]})
            start = idx + len(term)
    return matches
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings -v`
Expected: `OK` (18 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_findings.py ai-sandbox/marker-conversion/tests/test_postprocess_findings.py
git commit -m "Add search_reference_documents to postprocess_findings.py"
```

---

### Task 7: `postprocess_findings.py` — changelog record builder

**Files:**
- Modify: `postprocess_findings.py`
- Test: `tests/test_postprocess_findings.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `build_changelog_entry(page: int, flagged_text: str, corrected_text: str | None, signal_sources: list[str], confidence: str, reasoning: str) -> dict` — consumed by Task 9. `confidence` is one of `"high"`, `"low"`, `"unverifiable"`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_postprocess_findings.py
from postprocess_findings import build_changelog_entry


class TestBuildChangelogEntry(unittest.TestCase):
    def test_builds_a_high_confidence_applied_fix_record(self):
        entry = build_changelog_entry(
            page=6, flagged_text="p", corrected_text="\\sqrt{h^2+k^2}",
            signal_sources=["structural"], confidence="high",
            reasoning="re-verified against source image; text differed, applied correction",
        )
        self.assertEqual(entry["page"], 6)
        self.assertEqual(entry["flagged_text"], "p")
        self.assertEqual(entry["corrected_text"], "\\sqrt{h^2+k^2}")
        self.assertEqual(entry["signal_sources"], ["structural"])
        self.assertEqual(entry["confidence"], "high")

    def test_unverifiable_entry_has_no_corrected_text(self):
        entry = build_changelog_entry(
            page=6, flagged_text="p", corrected_text=None,
            signal_sources=["masked_lm"], confidence="unverifiable",
            reasoning="source PDF not found",
        )
        self.assertIsNone(entry["corrected_text"])
        self.assertEqual(entry["confidence"], "unverifiable")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings.TestBuildChangelogEntry -v`
Expected: `ImportError: cannot import name 'build_changelog_entry'`

- [ ] **Step 3: Write the implementation**

```python
# add to postprocess_findings.py
def build_changelog_entry(
    page: int,
    flagged_text: str,
    corrected_text: str | None,
    signal_sources: list[str],
    confidence: str,
    reasoning: str,
) -> dict:
    """
    One record of a postprocess run's decision about a single candidate
    -- an applied fix, a confirmed-clean check, or an unresolved
    low-confidence/unverifiable finding. Mirrors the shape written to
    <name>_postprocess_log.json, the companion audit file the design
    spec requires for every in-place edit -- nothing is silently altered
    without a record.
    """
    return {
        "page": page,
        "flagged_text": flagged_text,
        "corrected_text": corrected_text,
        "signal_sources": signal_sources,
        "confidence": confidence,
        "reasoning": reasoning,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m unittest tests.test_postprocess_findings -v`
Expected: `OK` (20 tests)

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_findings.py ai-sandbox/marker-conversion/tests/test_postprocess_findings.py
git commit -m "Add build_changelog_entry to postprocess_findings.py"
```

---

### Task 8: `local_model_scoring.py` — masked-LM and causal-z-score detection signals

Not unit-tested, matching this project's established split for anything touching a model or the network (`transcribe_page_via_gemini`, `render_page_to_image_bytes`, etc. are the same way). Validated instead against the real bug this whole subproject started from.

**Files:**
- Create: `local_model_scoring.py`

**Interfaces:**
- Consumes: nothing from other new modules.
- Produces: `score_masked_candidates(model_name: str, text: str, candidate_spans: list[tuple[int, int]]) -> list[dict]`, `score_causal_zscore(model_name: str, text: str, window: int = 10) -> list[dict]` — consumed by Task 9.

- [ ] **Step 1: Install dependencies (already proven to work in this exact venv during the design spike)**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu`
Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe -m pip install transformers`
Expected: both complete without error (already confirmed during the spike this exact environment installs cleanly)

- [ ] **Step 2: Write the implementation**

```python
# local_model_scoring.py
"""
Local small-model scoring for postprocess_notes.py's detection layer --
see docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Loaded via HuggingFace `transformers` (PyTorch CPU backend) -- Ollama
was the original candidate but was dropped: verified against its own
official docs that neither its native nor OpenAI-compatible API
supports scoring caller-provided text (no echo/prompt-logprobs mode),
only probabilities for tokens the model generates itself.

Touches transformers/torch -- not unit-tested locally, matching this
project's established split for anything model- or network-dependent
(transcribe_page_via_gemini, render_page_to_image_bytes, etc. are the
same way). Validated instead against real documents; see Task 8's
validation script in the implementation plan for the concrete real-bug
check this was built against.
"""
from __future__ import annotations

import statistics


def score_masked_candidates(
    model_name: str, text: str, candidate_spans: list[tuple[int, int]],
) -> list[dict]:
    """
    For each (start, end) character span in `text`, masks exactly that
    span and reads the model's own probability for the actual text that
    was there -- the signal confirmed strongest in the design spike
    (DistilBERT correctly scored a real bug at probability 0.0018, ~40x
    below its top candidate, using both left and right context). Skips
    any span whose text isn't exactly one model token (multi-token
    masked scoring needs a different approach than single-token
    probability lookup; out of scope here). Returns one dict per scored
    span: {"start", "end", "text", "probability", "rank"}.
    """
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForMaskedLM.from_pretrained(model_name)
    model.eval()

    results = []
    for start, end in candidate_spans:
        target_text = text[start:end]
        target_ids = tokenizer(target_text, add_special_tokens=False)["input_ids"]
        if len(target_ids) != 1:
            continue
        masked_text = text[:start] + tokenizer.mask_token + text[end:]
        inputs = tokenizer(masked_text, return_tensors="pt")
        mask_positions = (inputs["input_ids"][0] == tokenizer.mask_token_id).nonzero()
        if len(mask_positions) == 0:
            continue
        mask_idx = mask_positions[0].item()
        with torch.no_grad():
            logits = model(**inputs).logits[0, mask_idx]
        probs = torch.softmax(logits, dim=-1)
        target_id = target_ids[0]
        probability = probs[target_id].item()
        rank = (probs > probs[target_id]).sum().item() + 1
        results.append({
            "start": start, "end": end, "text": target_text,
            "probability": probability, "rank": rank,
        })
    return results


def score_causal_zscore(model_name: str, text: str, window: int = 10) -> list[dict]:
    """
    Per-token causal surprisal, converted to a local z-score against
    each token's own neighborhood rather than ranked globally across the
    whole page -- confirmed in the design spike to modestly outperform
    raw global ranking (moved the real bug from rank 6 to rank 3 of 523
    tokens on the same real test page). Kept as a secondary signal
    alongside score_masked_candidates: this needs only one forward pass
    for an entire page, versus one pass per candidate span for masked
    scoring, so it's a cheaper first coarse pass. Returns one dict per
    token: {"text", "start", "end", "surprisal", "z_score"}.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()

    enc = tokenizer(text, return_tensors="pt", return_offsets_mapping=True)
    input_ids = enc["input_ids"]
    offsets = enc["offset_mapping"][0].tolist()[1:]
    with torch.no_grad():
        logits = model(input_ids).logits[:, :-1, :]
    targets = input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    token_logprob = log_probs.gather(2, targets.unsqueeze(-1)).squeeze(-1)[0]
    surprisal = (-token_logprob).tolist()
    token_strs = tokenizer.convert_ids_to_tokens(input_ids[0])[1:]

    results = []
    n = len(surprisal)
    for i in range(n):
        lo, hi = max(0, i - window), min(n, i + window + 1)
        neighborhood = surprisal[lo:i] + surprisal[i + 1:hi]
        if len(neighborhood) < 4:
            z = 0.0
        else:
            mean = statistics.mean(neighborhood)
            stdev = statistics.pstdev(neighborhood) or 1e-6
            z = (surprisal[i] - mean) / stdev
        start, end = offsets[i]
        results.append({
            "text": token_strs[i], "start": start, "end": end,
            "surprisal": surprisal[i], "z_score": z,
        })
    return results
```

- [ ] **Step 3: Validate against the real bug this subproject started from**

This mirrors the design spike exactly, against the real file, as a real (not synthetic) correctness check before this module is trusted by Task 9.

```python
# scratch validation script -- not committed, run directly
import sys
sys.path.insert(0, ".")
from transcribe_notes import extract_page_text
from local_model_scoring import score_masked_candidates

path = "../academic-hub/academic_notes/math-camp/problem_sets/Analysis_Exercises.pdf"
text = extract_page_text(path, 5)  # page 6, the real radical-as-p bug
bug_start = text.index("\np\n") + 1
bug_end = bug_start + 1

results = score_masked_candidates("distilbert-base-cased", text, [(bug_start, bug_end)])
print(results)
assert results, "expected the bug span to be scoreable"
assert results[0]["probability"] < 0.01, f"expected low probability, got {results[0]['probability']}"
print("PASS: real bug scored low-probability as expected")
```

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe path/to/scratch_validation.py`
Expected: `PASS: real bug scored low-probability as expected` (the spike's uncased run scored this specific case at 0.0018; the cased model is untested territory per the spec's open question, so if this assertion fails, that's a real, useful finding to bring back to the design rather than a bug in the module itself -- see the spec's "cased vs. uncased" open question)

- [ ] **Step 4: Commit**

```bash
git add ai-sandbox/marker-conversion/local_model_scoring.py
git commit -m "Add local_model_scoring.py: masked-LM and causal-z-score detection signals

Not unit-tested (model/network-dependent, matching this project's
existing split) -- validated against the real Analysis_Exercises.pdf
page 6 bug this subproject started from instead."
```

---

### Task 9: `postprocess_notes.py` — CLI driver and full pipeline integration

**Files:**
- Create: `postprocess_notes.py`

**Interfaces:**
- Consumes: everything from Tasks 1-8 (`postprocess_discovery`, `postprocess_findings`, `local_model_scoring`, and `transcribe_notes`'s `ALLOWED_MATH_RANGES`/`is_expected_char`/`repair_page_individually`/`build_final_markdown`/`build_frontmatter`/`_MODEL_TYPESET`, plus `gemini_utils`'s `get_gemini_client`/`load_dotenv_override`).
- Produces: the `postprocess_notes.py` CLI entry point; nothing else consumes this.

- [ ] **Step 1: Write the implementation**

```python
# postprocess_notes.py
#!/usr/bin/env python3
"""
postprocess_notes.py
Downstream correction pass over transcribe_notes.py's already-produced
.md output -- see
docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md for
the full design. Targets local-only pages (never seen by a vision
model); re-verifies flagged candidates against their real source PDF
page, reusing transcribe_notes.py's existing repair machinery, rather
than trusting a model's self-reported confidence on text alone.
"""
from __future__ import annotations

import argparse
import json
import os

from gemini_utils import get_gemini_client, load_dotenv_override
from local_model_scoring import score_causal_zscore, score_masked_candidates
from postprocess_discovery import (
    derive_eligible_pages,
    discover_markdown_files,
    is_correction_target,
    parse_frontmatter,
    split_pages_by_tag,
)
from postprocess_findings import (
    build_changelog_entry,
    documents_needing_review,
    find_isolated_candidate_spans,
    group_findings_by_signature,
    is_allowlisted_span,
    search_reference_documents,
)
from transcribe_notes import (
    _MODEL_TYPESET,
    build_final_markdown,
    build_frontmatter,
    repair_page_individually,
)

_MASKED_MODEL = "distilbert-base-cased"
_CAUSAL_MODEL = "gpt2"
_MASKED_PROBABILITY_THRESHOLD = 0.01
_CAUSAL_ZSCORE_THRESHOLD = 3.0
_PATTERN_REVIEW_THRESHOLD = 5


def find_source_pdf(md_path: str, frontmatter: dict) -> str | None:
    """
    The source PDF for a processed_outputs/<name>.md file lives one
    directory up, named from frontmatter["source_pdf"]. Returns None
    (rather than raising) if it's missing -- detection still runs,
    verification is skipped for that document (see the design spec's
    edge case for a moved/deleted source PDF).
    """
    source_pdf = frontmatter.get("source_pdf")
    if not source_pdf:
        return None
    candidate = os.path.join(os.path.dirname(os.path.dirname(md_path)), source_pdf)
    return candidate if os.path.isfile(candidate) else None


def page_lines_from_source(pdf_path: str, page_index: int) -> list[list[dict]]:
    """Touches PyMuPDF -- not unit-tested locally, matching extract_all_page_texts's own split."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        text_dict = doc[page_index].get_text("dict")
        return [
            line.get("spans", [])
            for block in text_dict.get("blocks", [])
            for line in block.get("lines", [])
        ]
    finally:
        doc.close()


def find_candidates_for_page(pdf_path: str, page_num: int, page_text: str) -> list[dict]:
    """
    Runs all three detection signals for one page and merges them into a
    single candidate list, deliberately kept side by side per the design
    spec rather than narrowed to one -- structural (free, targets the
    confirmed real bug shape directly), masked-LM (strongest signal in
    the design spike), and causal z-score (cheaper single-pass signal).
    Each candidate is a dict with at least "text" and "start"/"end" (or
    "origin" for structural-only candidates without character offsets).
    """
    lines = page_lines_from_source(pdf_path, page_num - 1)
    candidates = [
        {**c, "source": "structural"} for c in find_isolated_candidate_spans(lines)
    ]

    masked_spans = [
        (i, i + 1) for i, ch in enumerate(page_text) if ch.strip() and not ch.isspace()
    ]
    for hit in score_masked_candidates(_MASKED_MODEL, page_text, masked_spans):
        if hit["probability"] < _MASKED_PROBABILITY_THRESHOLD:
            candidates.append({**hit, "source": "masked_lm"})

    for hit in score_causal_zscore(_CAUSAL_MODEL, page_text):
        if hit["z_score"] > _CAUSAL_ZSCORE_THRESHOLD:
            candidates.append({**hit, "source": "causal_zscore"})

    return [c for c in candidates if not is_allowlisted_span(c["text"])]


def process_document(
    md_path: str, client, reference_texts: dict[str, str], dry_run: bool = False,
) -> list[dict]:
    """
    Runs the full detection -> suppression -> verification -> correction
    pipeline against one target document. Returns the list of unresolved
    (low-confidence/unverifiable) findings, for the caller to fold into
    corpus-wide pattern aggregation. High-confidence fixes are written
    directly into md_path (unless dry_run); every decision is appended
    to <name>_postprocess_log.json. `reference_texts` (document path ->
    full text, built once in main() from every discovered .md file) is
    used to fold cross-reference hits into the hint text sent to
    verification -- extra context for the judge, per the design spec,
    never a deciding vote on its own (the source-image re-check is still
    what decides the fix).
    """
    with open(md_path, encoding="utf-8") as f:
        original_text = f.read()
    frontmatter, body = parse_frontmatter(original_text)
    eligible_pages = derive_eligible_pages(frontmatter)
    if not eligible_pages:
        return []

    source_pdf = find_source_pdf(md_path, frontmatter)
    total_pages = frontmatter["total_pages"]
    pages_text = split_pages_by_tag(body)

    unresolved: list[dict] = []
    changelog: list[dict] = []
    any_change = False

    for page_num in eligible_pages:
        page_text = pages_text.get(page_num, "")
        if not page_text:
            continue

        if source_pdf is None:
            entry = build_changelog_entry(
                page_num, "", None, [], "unverifiable",
                "source PDF not found; detection skipped entirely for this document",
            )
            changelog.append(entry)
            unresolved.append({"document": md_path, "flagged_text": "", **entry})
            continue

        candidates = find_candidates_for_page(source_pdf, page_num, page_text)
        if not candidates:
            continue

        # Cross-reference: fold hits for each candidate's flagged text
        # into the hint sent to verification -- confirming/clarifying
        # domain terminology the judge might not otherwise recognize.
        # Informational only; the source-image re-check below is still
        # the deciding signal (see the design spec's edge case for
        # conflicting cross-reference readings).
        cross_ref_notes = []
        for candidate in candidates:
            for hit in search_reference_documents(candidate["text"], reference_texts, context_chars=60)[:3]:
                cross_ref_notes.append(hit["context"])
        hint_text = page_text
        if cross_ref_notes:
            hint_text += "\n\n(Similar text found elsewhere in the corpus, for context: " + " | ".join(cross_ref_notes) + ")"

        try:
            corrected = repair_page_individually(
                client, _MODEL_TYPESET, source_pdf, page_num, hint_text, total_pages,
            )
        except Exception as err:
            for candidate in candidates:
                entry = build_changelog_entry(
                    page_num, candidate["text"], None, [candidate["source"]],
                    "unverifiable", str(err),
                )
                changelog.append(entry)
                unresolved.append({"document": md_path, "flagged_text": candidate["text"], **entry})
            continue

        signal_sources = sorted({c["source"] for c in candidates})
        if corrected.strip() == page_text.strip():
            changelog.append(build_changelog_entry(
                page_num, "", None, signal_sources, "high",
                "re-verified against source image; matched existing text, no change needed",
            ))
            continue

        pages_text[page_num] = corrected
        any_change = True
        changelog.append(build_changelog_entry(
            page_num, page_text, corrected, signal_sources, "high",
            "re-verified against source image; text differed, applied correction",
        ))

    if changelog and not dry_run:
        log_path = md_path.replace(".md", "_postprocess_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2)

        frontmatter["postprocessed"] = True
        new_body = build_final_markdown(
            {str(k): v for k, v in pages_text.items()}, total_pages,
        ) if any_change else body
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(build_frontmatter(frontmatter) + new_body)

    return unresolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post-process transcribe_notes.py output: catch and correct errors "
                    "on local-only pages that were never seen by a vision model."
    )
    parser.add_argument(
        "--root", action="append", required=True,
        help="Root directory to scan recursively for processed_outputs/*.md files "
             "(repeatable, e.g. --root academic-hub/academic_notes/math-camp).",
    )
    parser.add_argument("--file", default=None, help="Only process this one target .md filename.")
    parser.add_argument(
        "--reprocess", action="store_true",
        help="Reprocess documents even if already marked postprocessed: true.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be flagged/fixed without writing anything.",
    )
    args = parser.parse_args()

    load_dotenv_override()
    all_files = discover_markdown_files(args.root)

    reference_texts = {}
    targets = []
    for path in all_files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        frontmatter, body = parse_frontmatter(text)
        reference_texts[path] = body
        is_target = args.reprocess or is_correction_target(frontmatter)
        if is_target and "routing" in frontmatter:
            if args.file is None or os.path.basename(path) == args.file:
                targets.append(path)

    if not targets:
        print("No target documents found.")
        return

    client = None if args.dry_run else get_gemini_client()
    if not args.dry_run and client is None:
        return

    all_unresolved: list[dict] = []
    for path in targets:
        print(f"[{os.path.basename(path)}] processing...")
        unresolved = process_document(path, client, reference_texts, dry_run=args.dry_run)
        all_unresolved.extend(unresolved)

    grouped = group_findings_by_signature(all_unresolved)
    review_needed = documents_needing_review(grouped, threshold=_PATTERN_REVIEW_THRESHOLD)
    if review_needed:
        print(f"\nDocuments with a consistent low-confidence pattern (>= {_PATTERN_REVIEW_THRESHOLD} similar findings):")
        for doc in review_needed:
            print(f"  {doc}")
    else:
        print("\nNo documents crossed the pattern-review threshold.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run against a real, already-processed document**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe postprocess_notes.py --root ../academic-hub/academic_notes/math-camp/problem_sets --file "Practice Sheet.md" --dry-run`
Expected: runs without error, reports what (if anything) it would flag/verify for `Practice Sheet.md` (already dict-mode-corrected in an earlier session, so expect few or no candidates) -- no `.md`/`_postprocess_log.json` files written, since `--dry-run` is set

- [ ] **Step 3: Real run against `Analysis_Exercises.md`, the document this whole subproject started from**

Run: `cd ai-sandbox/marker-conversion && .venv/Scripts/python.exe postprocess_notes.py --root ../academic-hub/academic_notes/math-camp/problem_sets --file "Analysis_Exercises.md"`
Expected: page 6's radical-as-`p` bug is found by at least the structural signal, re-verified against the real source PDF, and corrected in place; `Analysis_Exercises_postprocess_log.json` is written recording the fix; re-reading `Analysis_Exercises.md` afterward shows `\sqrt{h^2+k^2}` (or equivalent) on page 6 instead of the bare `p`

- [ ] **Step 4: Commit**

```bash
git add ai-sandbox/marker-conversion/postprocess_notes.py
git commit -m "Add postprocess_notes.py: CLI driver wiring detection, suppression, verification, and correction together

Validated against the real Analysis_Exercises.pdf page 6 bug this
subproject started from -- the radical-as-p error is found, re-verified
against the source PDF, and corrected in place."
```
