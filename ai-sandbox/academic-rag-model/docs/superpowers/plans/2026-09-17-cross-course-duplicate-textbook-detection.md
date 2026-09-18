# Cross-Course Duplicate Textbook Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before a textbook PDF is uploaded/converted, detect whether it (or a different scan of the same book) has already been converted under a different course's folder, and if so skip reconversion and copy the existing artifacts instead — plus give an autonomous agent a self-contained instructions file for running the whole conversion pipeline.

**Architecture:** A new pure-Python, offline module `indexer/duplicate_check.py` (no torch/marker/pypdf/genai import, matching `indexer/index_card.py`'s existing constraint) with two independent matching tiers — exact (PDF byte-hash, via the existing `indexer.index_card.find_card_by_file_id`) and fuzzy (title/author/year similarity scoring) — a small persisted dismissal list for rejected fuzzy matches, and a CLI that supports both an interactive human mode and a non-blocking `--non-interactive`/`--resolve` mode for an agent driving it without a live stdin.

**Tech Stack:** Python 3 stdlib only (`difflib`, `argparse`, `json`, `os`, `shutil`, `glob`, `pathlib`) plus the existing `indexer.index_card` and `textbook.bib_info` modules. Tests via `unittest` (matching `tests/test_index_card.py`'s existing style), run with `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md`

## Global Constraints

- No GPU/CUDA/torch/marker/pypdf/genai import anywhere in `indexer/duplicate_check.py` — it must be importable and testable with no VM, no network, no API key (spec §1).
- Tier 2 (fuzzy) matches are **never** auto-skipped regardless of score — always require an explicit decision (spec §1, §4).
- A dismissed (file_id_a, file_id_b) pair is never surfaced again (spec §4).
- On any per-candidate error (corrupt shard, unreadable card, exception during scoring), log a warning and treat that one candidate as no-match — fail toward converting, never toward silently skipping (spec §6).
- The canonical course's own card and files are never modified by a copy operation (spec §5).
- A cloned card's `file_id` must never collide with its canonical card's `file_id` — always minted via `indexer.index_card.compute_id_from_parts([canonical_file_id, new_course])` (spec §5).
- Run from the `academic-rag-model` project root; `conftest.py` already puts that root on `sys.path`, so `from indexer.duplicate_check import ...` and `from textbook.bib_info import ...` both resolve.

---

### Task 1: Title normalization and fuzzy-match scoring

**Files:**
- Create: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Produces: `normalize_title(title: str) -> str`, `parse_author_year_from_folder_name(folder_name: str) -> tuple[str, str]`, `SURFACE_THRESHOLD: float`, `score_candidate(incoming: dict, candidate_title: str, candidate_author: str, candidate_year: str) -> dict` (returns `{"title_score": float, "author_bonus": float, "year_bonus": float, "combined": float}`). `incoming` is the dict shape returned by `textbook.bib_info.extract_bibliographic_info_from_filename` (keys `"title"`, `"author"`, `"year"`, all strings, possibly empty).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_duplicate_check.py
import unittest

from indexer.duplicate_check import (
    normalize_title,
    parse_author_year_from_folder_name,
    score_candidate,
    SURFACE_THRESHOLD,
)


class TestNormalizeTitle(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(normalize_title("Microeconomic Theory!"), "microeconomic theory")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize_title("  Real   Analysis  "), "real analysis")

    def test_empty_input(self):
        self.assertEqual(normalize_title(""), "")
        self.assertEqual(normalize_title(None), "")


class TestParseAuthorYearFromFolderName(unittest.TestCase):
    def test_typical_folder_name(self):
        author, year = parse_author_year_from_folder_name("Ok_RealAnalysisWithEconomicApplications_2007")
        self.assertEqual(author, "Ok")
        self.assertEqual(year, "2007")

    def test_single_token_folder_name_has_no_year(self):
        author, year = parse_author_year_from_folder_name("converted_textbook")
        self.assertEqual(author, "converted")
        self.assertEqual(year, "")


class TestScoreCandidate(unittest.TestCase):
    def test_identical_title_author_year_scores_at_or_near_one(self):
        incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
        result = score_candidate(incoming, "Real Analysis with Economic Applications", "Ok", "2007")
        self.assertGreaterEqual(result["combined"], 0.95)

    def test_similar_but_different_books_surface_above_threshold(self):
        # Real risk case (spec Testing section): Mas-Colell's "Microeconomic
        # Theory" vs. Rubinstein's "Lecture Notes in Microeconomic Theory"
        # -- different books, but title overlap alone clears the surfacing
        # threshold. This is *expected* -- it's why Tier 2 never auto-skips
        # on score alone (see Task 6's orchestration, which never treats a
        # high score as a "yes" by itself).
        incoming = {"title": "Microeconomic Theory", "author": "Mas-Colell", "year": "1995"}
        result = score_candidate(incoming, "Lecture Notes in Microeconomic Theory", "Rubinstein", "2012")
        self.assertGreaterEqual(result["combined"], SURFACE_THRESHOLD)

    def test_unrelated_titles_score_low(self):
        incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
        result = score_candidate(incoming, "Introduction to Spanish Grammar", "Garcia", "2015")
        self.assertLess(result["combined"], SURFACE_THRESHOLD)

    def test_year_off_by_one_gets_partial_bonus(self):
        # Title deliberately not a perfect match (score ~0.82, no author
        # bonus since author is omitted) so the combined score has
        # headroom below 1.0 -- otherwise min(1.0, ...) clipping would
        # erase the very year-bonus difference this test checks for
        # (confirmed while writing this plan: a same-title/same-author
        # pairing saturates past 1.0 regardless of year, making every
        # variant compare equal).
        incoming = {"title": "Elements of Microeconomic Analysis", "author": "", "year": "2020"}
        exact_year = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "2020")
        off_by_one = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "2021")
        off_by_many = score_candidate(incoming, "Foundations of Microeconomic Analysis", "", "1999")
        self.assertGreater(exact_year["combined"], off_by_one["combined"])
        self.assertGreater(off_by_one["combined"], off_by_many["combined"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'indexer.duplicate_check'`

- [ ] **Step 3: Write the module (this task's portion only)**

```python
# indexer/duplicate_check.py
"""
duplicate_check.py
Cross-course duplicate-textbook detection, run as a pre-flight step
before any PDF in a course's textbook folder is uploaded/converted (see
convert_textbook_instructions.md Step 0.4 and
convert_textbook_agent_instructions.md Step 0.3). Deliberately has no
torch/marker/pypdf/genai dependency, same constraint as index_card.py
and textbook/bib_info.py, so it stays testable and runnable with no GPU,
no VM, and no network.

Spec: docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md
"""
from __future__ import annotations

import difflib
import re

# A card only stores `title` (from generate_index_card()'s LLM/regex
# tiers) -- never author/year as their own fields. The candidate side of
# a fuzzy comparison instead parses author/year out of the candidate's
# own output folder name, which textbook.bib_info.derive_folder_name
# always writes as "<AuthorLastName>_<SanitizedTitle>_<Year>" (spec §3).
_TITLE_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")

# Below this combined score, a fuzzy candidate is never mentioned to the
# user at all -- deliberately loose (0.6, not a high-trust bar) because
# Tier 2 never auto-skips regardless of score (spec §3-4); this threshold
# only controls noise, never trust.
SURFACE_THRESHOLD = 0.6


def normalize_title(title: str) -> str:
    """Lowercase, punctuation-stripped, whitespace-collapsed -- comparison
    key for difflib title similarity, not a display value."""
    if not title:
        return ""
    cleaned = _TITLE_PUNCTUATION_RE.sub("", title).lower()
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def parse_author_year_from_folder_name(folder_name: str) -> tuple[str, str]:
    """Reverses textbook.bib_info.derive_folder_name's
    "<AuthorLastName>_<SanitizedTitle>_<Year>" convention -- author and
    year are always single tokens by construction (sanitize_filename
    never puts an underscore at either edge), unlike the sanitized title
    in between, which is not extracted here since the candidate's real
    `title` field (on its index card) is used instead of re-deriving one
    from this sanitized folder segment."""
    parts = folder_name.split("_")
    author = parts[0] if parts else ""
    year = parts[-1] if len(parts) > 1 else ""
    return author, year


def score_candidate(incoming: dict, candidate_title: str, candidate_author: str, candidate_year: str) -> dict:
    """Scores one candidate card against the incoming PDF's filename-derived
    bibliographic guess (spec §3). Never raises on empty/missing fields --
    every comparison degrades to a 0-bonus no-op rather than erroring, so a
    book with an unparseable filename still gets *some* score instead of
    crashing the whole batch (see Task 3's per-candidate error isolation,
    which is a second, independent safety net on top of this)."""
    title_score = difflib.SequenceMatcher(
        None, normalize_title(incoming.get("title", "")), normalize_title(candidate_title),
    ).ratio()

    author_bonus = 0.0
    incoming_author = (incoming.get("author") or "").strip()
    if incoming_author and candidate_author:
        incoming_last = incoming_author.split()[-1].lower()
        if incoming_last and incoming_last in candidate_author.lower():
            author_bonus = 0.15

    year_bonus = 0.0
    incoming_year = (incoming.get("year") or "").strip()
    if incoming_year and candidate_year:
        try:
            diff = abs(int(incoming_year) - int(candidate_year))
            if diff == 0:
                year_bonus = 0.1
            elif diff == 1:
                year_bonus = 0.05
        except ValueError:
            pass

    combined = min(1.0, title_score + author_bonus + year_bonus)
    return {"title_score": title_score, "author_bonus": author_bonus, "year_bonus": year_bonus, "combined": combined}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: PASS (all `TestNormalizeTitle`, `TestParseAuthorYearFromFolderName`, `TestScoreCandidate` cases)

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add title normalization and fuzzy duplicate-match scoring

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Exact-tier (byte-hash) duplicate lookup

**Files:**
- Modify: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Consumes: `indexer.index_card.compute_file_id(pdf_path: str) -> str`, `indexer.index_card.find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None`, `indexer.index_card.save_shard`, `indexer.index_card.list_courses`.
- Produces: `find_exact_duplicate(academic_hub_root: str, pdf_path: str, current_course: str) -> tuple[str, dict] | None` (returns `(course, card)` of a match in a *different* course, or `None`).

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_duplicate_check.py

import os
import tempfile

from indexer.index_card import save_shard
from indexer.duplicate_check import find_exact_duplicate


class TestFindExactDuplicate(unittest.TestCase):
    def _write_pdf(self, path: str, content: bytes = b"%PDF-1.4 fake content") -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_finds_match_in_a_different_course(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            from indexer.index_card import compute_file_id

            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "Ok.pdf")
            self._write_pdf(pdf_path)
            file_id = compute_file_id(pdf_path)

            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id, "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNotNone(result)
            course, card = result
            self.assertEqual(course, "econometrics")
            self.assertEqual(card["file_id"], file_id)

    def test_match_in_the_same_course_is_not_a_cross_course_duplicate(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            from indexer.index_card import compute_file_id

            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "Ok.pdf")
            self._write_pdf(pdf_path)
            file_id = compute_file_id(pdf_path)

            save_shard(academic_hub_root, "microecon", [{
                "file_id": file_id, "path": "microecon/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/microecon/textbooks/Ok.pdf", "course": "microecon",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNone(result)

    def test_no_match_anywhere(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            pdf_path = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "New.pdf")
            self._write_pdf(pdf_path, content=b"%PDF-1.4 never seen before")
            result = find_exact_duplicate(academic_hub_root, pdf_path, current_course="microecon")
            self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestFindExactDuplicate -v`
Expected: FAIL with `ImportError: cannot import name 'find_exact_duplicate'`

- [ ] **Step 3: Implement**

Add to `indexer/duplicate_check.py`:

```python
from indexer.index_card import compute_file_id, find_card_by_file_id


def find_exact_duplicate(academic_hub_root: str, pdf_path: str, current_course: str) -> tuple[str, dict] | None:
    """Tier 1 (spec §3): byte-identical duplicate in a *different* course.
    find_card_by_file_id() already searches every course unconditionally
    (indexer/index_card.py), so no change is needed there -- this just
    excludes a match that happens to already be in the current course,
    which is convert_textbook.py's own existing same-run skip check's
    job, not this module's."""
    file_id = compute_file_id(pdf_path)
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return None
    course, card = found
    if course == current_course:
        return None
    return course, card
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestFindExactDuplicate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add Tier 1 exact byte-hash cross-course duplicate lookup

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Fuzzy-tier candidate search across all courses

**Files:**
- Modify: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Consumes: `score_candidate` (Task 1), `parse_author_year_from_folder_name` (Task 1), `SURFACE_THRESHOLD` (Task 1), `indexer.index_card.list_courses(academic_hub_root: str) -> list[str]`, `indexer.index_card.load_shard(academic_hub_root: str, course: str) -> list[dict]`.
- Produces: `find_fuzzy_candidates(academic_hub_root: str, incoming: dict, current_course: str) -> list[dict]` — each result dict is `{"course": str, "card": dict, "title_score": float, "author_bonus": float, "year_bonus": float, "combined": float}`, sorted by `combined` descending. Only cards with `doc_type == "textbook"` in courses other than `current_course` are considered; only results with `combined >= SURFACE_THRESHOLD` are returned. A card whose scoring raises (missing/malformed `path`) is skipped with a `stderr` warning, never crashes the batch.

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_duplicate_check.py

import sys
from io import StringIO

from indexer.duplicate_check import find_fuzzy_candidates


class TestFindFuzzyCandidates(unittest.TestCase):
    def _card(self, folder_name, title, doc_type="textbook", course="econometrics"):
        return {
            "file_id": f"fid-{folder_name}", "path": f"{course}/textbooks/processed_outputs/{folder_name}/{folder_name}.md",
            "source_pdf_path": f"academic_resources/{course}/textbooks/x.pdf", "course": course,
            "doc_type": doc_type, "title": title,
        }

    def test_finds_and_ranks_candidates_above_threshold(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications"),
                self._card("Garcia_SpanishGrammar_2015", "Introduction to Spanish Grammar"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}

            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["course"], "econometrics")
            self.assertEqual(results[0]["card"]["title"], "Real Analysis with Economic Applications")

    def test_excludes_non_textbook_doc_types(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", doc_type="problem_set"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(results, [])

    def test_excludes_current_course(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "microecon", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", course="microecon"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(results, [])

    def test_similar_titled_different_book_surfaces_for_confirmation(self):
        # The Mas-Colell/Rubinstein worked example from the spec's Testing
        # section -- must surface (so a human gets asked), which this test
        # confirms; Task 6's orchestration is what ensures it's never
        # auto-skipped.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "math-methods", [
                self._card("Rubinstein_LectureNotesInMicroeconomicTheory_2012", "Lecture Notes in Microeconomic Theory", course="math-methods"),
            ])
            incoming = {"title": "Microeconomic Theory", "author": "Mas-Colell", "year": "1995"}
            results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            self.assertEqual(len(results), 1)

    def test_corrupt_shard_logs_warning_and_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            index_dir = os.path.join(academic_hub_root, ".index")
            os.makedirs(index_dir, exist_ok=True)
            with open(os.path.join(index_dir, "econometrics.json"), "w", encoding="utf-8") as f:
                f.write("not valid json{{{")
            save_shard(academic_hub_root, "math-methods", [
                self._card("Ok_RealAnalysisWithEconomicApplications_2007", "Real Analysis with Economic Applications", course="math-methods"),
            ])
            incoming = {"title": "Real Analysis with Economic Applications", "author": "Ok", "year": "2007"}

            captured_stderr = StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured_stderr
            try:
                results = find_fuzzy_candidates(academic_hub_root, incoming, current_course="microecon")
            finally:
                sys.stderr = old_stderr

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["course"], "math-methods")
            self.assertIn("WARNING", captured_stderr.getvalue())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestFindFuzzyCandidates -v`
Expected: FAIL with `ImportError: cannot import name 'find_fuzzy_candidates'`

- [ ] **Step 3: Implement**

Add to `indexer/duplicate_check.py`:

```python
import os
import sys

from indexer.index_card import list_courses, load_shard


def find_fuzzy_candidates(academic_hub_root: str, incoming: dict, current_course: str) -> list[dict]:
    """Tier 2 (spec §3): scores `incoming` (a bib_info-shaped
    {"title","author","year"} dict) against every textbook card in every
    *other* course. A card that can't be scored (malformed `path`, missing
    `title`) is skipped with a warning rather than aborting the whole scan
    (spec §6's error-isolation rule) -- same for a course whose shard file
    itself fails to load."""
    results = []
    for course in list_courses(academic_hub_root):
        if course == current_course:
            continue
        try:
            cards = load_shard(academic_hub_root, course)
        except Exception as err:
            print(f"WARNING: could not load shard for course {course!r} ({err}); skipping its candidates.", file=sys.stderr)
            continue

        for card in cards:
            if card.get("doc_type") != "textbook":
                continue
            try:
                folder_name = os.path.basename(os.path.dirname(card["path"]))
                author, year = parse_author_year_from_folder_name(folder_name)
                scores = score_candidate(incoming, card.get("title", ""), author, year)
            except Exception as err:
                print(f"WARNING: could not score candidate {card.get('path')!r} in course {course!r} ({err}); skipping.", file=sys.stderr)
                continue

            if scores["combined"] >= SURFACE_THRESHOLD:
                results.append({"course": course, "card": card, **scores})

    results.sort(key=lambda r: r["combined"], reverse=True)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestFindFuzzyCandidates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add Tier 2 fuzzy cross-course duplicate candidate search

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Dismissal persistence

**Files:**
- Modify: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Consumes: `indexer.index_card.now_iso() -> str`.
- Produces: `load_dismissals(academic_hub_root: str) -> list[dict]`, `save_dismissals(academic_hub_root: str, dismissals: list[dict]) -> None`, `is_dismissed(dismissals: list[dict], file_id_a: str, file_id_b: str) -> bool`, `record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None`. Storage file: `<academic_hub_root>/.index/duplicate_dismissals.json`.

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_duplicate_check.py

from indexer.duplicate_check import load_dismissals, save_dismissals, is_dismissed, record_dismissal


class TestDismissals(unittest.TestCase):
    def test_load_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self.assertEqual(load_dismissals(academic_hub_root), [])

    def test_record_then_is_dismissed_regardless_of_argument_order(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            dismissals = load_dismissals(academic_hub_root)
            self.assertTrue(is_dismissed(dismissals, "id-a", "id-b"))
            self.assertTrue(is_dismissed(dismissals, "id-b", "id-a"))

    def test_unrelated_pair_is_not_dismissed(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            dismissals = load_dismissals(academic_hub_root)
            self.assertFalse(is_dismissed(dismissals, "id-a", "id-c"))

    def test_recording_the_same_pair_twice_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            record_dismissal(academic_hub_root, "id-a", "id-b")
            self.assertEqual(len(load_dismissals(academic_hub_root)), 1)

    def test_persists_to_the_expected_path(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_dismissal(academic_hub_root, "id-a", "id-b")
            expected_path = os.path.join(academic_hub_root, ".index", "duplicate_dismissals.json")
            self.assertTrue(os.path.exists(expected_path))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestDismissals -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement**

Add to `indexer/duplicate_check.py`:

```python
import json

from indexer.index_card import now_iso


def _dismissals_path(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "duplicate_dismissals.json")


def load_dismissals(academic_hub_root: str) -> list[dict]:
    path = _dismissals_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dismissals(academic_hub_root: str, dismissals: list[dict]) -> None:
    path = _dismissals_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dismissals, f, indent=2, ensure_ascii=False)


def is_dismissed(dismissals: list[dict], file_id_a: str, file_id_b: str) -> bool:
    pair = tuple(sorted([file_id_a, file_id_b]))
    return any(tuple(sorted([d["file_id_a"], d["file_id_b"]])) == pair for d in dismissals)


def record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    """No-op (does not duplicate) if this exact pair is already recorded --
    safe to call every time a user says 'no' without checking first."""
    dismissals = load_dismissals(academic_hub_root)
    if is_dismissed(dismissals, file_id_a, file_id_b):
        return
    a, b = sorted([file_id_a, file_id_b])
    dismissals.append({"file_id_a": a, "file_id_b": b, "dismissed_at": now_iso()})
    save_dismissals(academic_hub_root, dismissals)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestDismissals -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add permanent dismissal persistence for rejected fuzzy matches

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Copy artifacts and clone the index card

**Files:**
- Modify: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Consumes: `indexer.index_card.compute_id_from_parts(parts: list[str]) -> str`, `indexer.index_card.load_shard`, `indexer.index_card.save_shard`, `indexer.index_card.recompute_course_entry(academic_hub_root: str, course: str) -> None`, `indexer.index_card.now_iso`.
- Produces: `copy_duplicate_artifacts(academic_hub_root: str, canonical_course: str, canonical_card: dict, new_course: str, new_folder_category: str, new_source_pdf_path: str) -> dict` — copies `processed_outputs/<BookDir>/` from the canonical course into the new course, appends a cloned card to the new course's shard, and returns that new card. `new_source_pdf_path` is the real relative path (from `academic_hub_root`) of the PDF that triggered this duplicate check — the caller already knows it (it's the file being iterated), so this function never derives it by string-editing the canonical card's own path (which could differ in folder-category naming, e.g. `textbooks` vs. `textbooks-and-papers`).

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_duplicate_check.py

import shutil

from indexer.index_card import compute_id_from_parts, load_courses
from indexer.duplicate_check import copy_duplicate_artifacts


class TestCopyDuplicateArtifacts(unittest.TestCase):
    def _make_canonical_book(self, academic_hub_root, course="econometrics", folder_category="textbooks", folder_name="Ok_RealAnalysisWithEconomicApplications_2007"):
        book_dir = os.path.join(academic_hub_root, course, folder_category, "processed_outputs", folder_name)
        os.makedirs(os.path.join(book_dir, "images"), exist_ok=True)
        with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
            f.write("# Real Analysis with Economic Applications\n\nBody text.")
        with open(os.path.join(book_dir, "images", "page_1.png"), "wb") as f:
            f.write(b"fake png bytes")
        with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
            f.write('{"title": "Real Analysis with Economic Applications"}')

        canonical_card = {
            "file_id": "canonical-fid", "path": f"{course}/{folder_category}/processed_outputs/{folder_name}/{folder_name}.md",
            "source_pdf_path": f"academic_resources/{course}/{folder_category}/Ok.pdf", "course": course,
            "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            "summary": "A real analysis textbook.", "tags": ["math"], "level": "advanced",
            "has_solutions": False, "page_count": 700, "embedding": [0.1, 0.2], "embedding_model": "gemini-embedding-001:768",
            "content_hash": "abc123", "needs_indexing": False,
        }
        save_shard(academic_hub_root, course, [canonical_card])
        return book_dir, folder_name, canonical_card

    def test_copies_all_artifact_files(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_book_dir = os.path.join(academic_hub_root, "microecon", "textbooks", "processed_outputs", folder_name)
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, f"{folder_name}.md")))
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "images", "page_1.png")))
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, f"{folder_name}_metadata.json")))

    def test_canonical_files_are_untouched(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            book_dir, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)
            before = open(os.path.join(book_dir, f"{folder_name}.md"), encoding="utf-8").read()

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            after = open(os.path.join(book_dir, f"{folder_name}.md"), encoding="utf-8").read()
            self.assertEqual(before, after)

    def test_new_card_has_a_derived_non_colliding_file_id(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            expected_id = compute_id_from_parts([canonical_card["file_id"], "microecon"])
            self.assertEqual(new_card["file_id"], expected_id)
            self.assertNotEqual(new_card["file_id"], canonical_card["file_id"])
            self.assertEqual(new_card["duplicate_of_file_id"], canonical_card["file_id"])
            self.assertEqual(new_card["course"], "microecon")
            self.assertEqual(new_card["source_pdf_path"], "academic_resources/microecon/textbooks/Ok.pdf")
            self.assertEqual(new_card["title"], canonical_card["title"])

    def test_new_card_is_saved_in_the_new_course_shard(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_shard = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(new_shard), 1)
            self.assertEqual(new_shard[0]["course"], "microecon")

    def test_rerunning_is_idempotent(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )
            copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            new_shard = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(new_shard), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestCopyDuplicateArtifacts -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement**

Add to `indexer/duplicate_check.py`:

```python
import shutil

from indexer.index_card import compute_id_from_parts, recompute_course_entry, save_shard


def copy_duplicate_artifacts(
    academic_hub_root: str, canonical_course: str, canonical_card: dict,
    new_course: str, new_folder_category: str, new_source_pdf_path: str,
) -> dict:
    """Copies a confirmed duplicate's processed_outputs/<BookDir>/ tree
    into the new course and clones its index card (spec §5). The canonical
    card/files are never modified -- this only ever reads from the
    canonical location and writes to the new one."""
    canonical_book_dir = os.path.join(academic_hub_root, os.path.normpath(os.path.dirname(canonical_card["path"])))
    folder_name = os.path.basename(canonical_book_dir)

    new_processed_outputs_dir = os.path.join(academic_hub_root, new_course, new_folder_category, "processed_outputs")
    new_book_dir = os.path.join(new_processed_outputs_dir, folder_name)
    os.makedirs(new_processed_outputs_dir, exist_ok=True)
    if os.path.exists(new_book_dir):
        shutil.rmtree(new_book_dir)
    shutil.copytree(canonical_book_dir, new_book_dir)

    new_file_id = compute_id_from_parts([canonical_card["file_id"], new_course])
    new_card = dict(canonical_card)
    new_card["file_id"] = new_file_id
    new_card["course"] = new_course
    new_card["path"] = f"{new_course}/{new_folder_category}/processed_outputs/{folder_name}/{folder_name}.md"
    new_card["source_pdf_path"] = new_source_pdf_path
    new_card["duplicate_of_file_id"] = canonical_card["file_id"]
    new_card["source_updated_at"] = now_iso()

    cards = [c for c in load_shard(academic_hub_root, new_course) if c.get("file_id") != new_file_id]
    cards.append(new_card)
    save_shard(academic_hub_root, new_course, cards)
    recompute_course_entry(academic_hub_root, new_course)
    return new_card
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestCopyDuplicateArtifacts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): copy duplicate artifacts and clone the index card cross-course

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: CLI orchestration

**Files:**
- Modify: `indexer/duplicate_check.py`
- Test: `tests/test_duplicate_check.py`

**Interfaces:**
- Consumes: everything from Tasks 1-5 (`find_exact_duplicate`, `find_fuzzy_candidates`, `is_dismissed`, `record_dismissal`, `copy_duplicate_artifacts`, `compute_file_id`), plus `indexer.index_card.derive_course(relative_path: str) -> str` and `textbook.bib_info.extract_bibliographic_info_from_filename(raw_input: str) -> dict`.
- Produces: `build_arg_parser() -> argparse.ArgumentParser`, `run_duplicate_check(textbook_subdir: str, academic_hub_root: str, non_interactive: bool, resolutions: dict[str, str], prompt_fn=None) -> dict` (returns `{"to_convert": list[str], "skipped": list[tuple], "unresolved": list[dict]}`, all keyed by plain PDF filename — this is the function the CLI's `main()` wraps and what a future in-process caller, e.g. a test or another script, uses directly instead of shelling out), `main() -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_duplicate_check.py

from indexer.duplicate_check import run_duplicate_check


class TestRunDuplicateCheck(unittest.TestCase):
    def _write_pdf(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def test_no_candidates_converts_everything(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "New_Book_2020.pdf"), b"brand new content")

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["New_Book_2020.pdf"])
            self.assertEqual(result["skipped"], [])

    def test_exact_duplicate_is_skipped_and_copied_without_any_prompt(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok.pdf")
            self._write_pdf(pdf_path, b"%PDF-1.4 identical bytes")
            from indexer.index_card import compute_file_id
            file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysis_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysis_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": file_id, "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysis_2007/Ok_RealAnalysis_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(result["skipped"][0][0], "Ok.pdf")
            new_book_dir = os.path.join(academic_hub_root, "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysis_2007")
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "Ok_RealAnalysis_2007.md")))

    def test_non_interactive_fuzzy_match_is_left_unresolved_and_kept_in_to_convert(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf"), b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(len(result["unresolved"]), 1)

    def test_resolve_yes_skips_and_copies(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "yes"},
            )

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)

    def test_resolve_no_dismisses_and_keeps_in_to_convert_without_reprompting(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "no"},
            )
            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])

            # Second run: same pair, no resolution given -- must not be
            # surfaced as unresolved again (spec §4).
            result_2 = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})
            self.assertEqual(result_2["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(result_2["unresolved"], [])

    def test_interactive_mode_uses_prompt_fn(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=lambda pdf_filename, candidate: "yes",
            )
            self.assertEqual(len(result["skipped"]), 1)


class TestBuildArgParser(unittest.TestCase):
    def test_requires_textbook_subdir(self):
        parser = build_arg_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_resolve_can_repeat(self):
        parser = build_arg_parser()
        args = parser.parse_args([
            "--textbook-subdir", "academic_resources/microecon/textbooks",
            "--non-interactive", "--resolve", "aaa=yes", "--resolve", "bbb=no",
        ])
        self.assertEqual(args.resolve, ["aaa=yes", "bbb=no"])
```

Add the `build_arg_parser` import alongside the others at the top of the appended test block:
```python
from indexer.duplicate_check import build_arg_parser
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestRunDuplicateCheck tests/test_duplicate_check.py::TestBuildArgParser -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement**

Add to `indexer/duplicate_check.py`:

```python
import argparse
import glob
from pathlib import Path

from indexer.index_card import derive_course
from textbook.bib_info import extract_bibliographic_info_from_filename


def _default_academic_hub_root() -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "academic-hub")


def _prompt_yes_no(pdf_filename: str, candidate: dict) -> str:
    """Default interactive prompt -- only reached when non_interactive is
    False, i.e. a human is at a real terminal. An agent must always pass
    non_interactive=True (see convert_textbook_agent_instructions.md Step
    0.3) since this blocks on real stdin."""
    print(f"\nPossible duplicate: {pdf_filename}")
    print(f"  matches {candidate['course']}: {candidate['card']['title']} "
          f"(score {candidate['combined']:.2f}, file_id={candidate['card']['file_id']})")
    answer = input("  Same book? Skip conversion and copy artifacts? [y/N] ").strip().lower()
    return "yes" if answer == "y" else "no"


def run_duplicate_check(
    textbook_subdir: str, academic_hub_root: str, non_interactive: bool,
    resolutions: dict[str, str], prompt_fn=None,
) -> dict:
    """The orchestration Tasks 1-5 build up to (spec §1-6). Kept separate
    from main() so it's directly callable in-process (tests above; also
    lets a future caller skip the CLI/argparse layer entirely)."""
    prompt_fn = prompt_fn or _prompt_yes_no
    current_course = derive_course(textbook_subdir)
    new_folder_category = textbook_subdir.rstrip("/").split("/")[-1]

    pdf_dir = os.path.join(academic_hub_root, textbook_subdir)
    pdf_paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))

    dismissals = load_dismissals(academic_hub_root)
    to_convert: list[str] = []
    skipped: list[tuple] = []
    unresolved: list[dict] = []

    for pdf_path in pdf_paths:
        pdf_filename = os.path.basename(pdf_path)
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        try:
            exact = find_exact_duplicate(academic_hub_root, pdf_path, current_course)
        except Exception as err:
            print(f"WARNING: exact-match check failed for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            exact = None

        if exact is not None:
            canonical_course, canonical_card = exact
            copy_duplicate_artifacts(
                academic_hub_root, canonical_course, canonical_card,
                current_course, new_folder_category, rel_pdf_path,
            )
            skipped.append((pdf_filename, canonical_course, canonical_card["path"], "exact"))
            continue

        incoming_file_id = compute_file_id(pdf_path)
        try:
            incoming_bib = extract_bibliographic_info_from_filename(pdf_path)
            candidates = find_fuzzy_candidates(academic_hub_root, incoming_bib, current_course)
        except Exception as err:
            print(f"WARNING: fuzzy-match check failed for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            candidates = []

        candidates = [c for c in candidates if not is_dismissed(dismissals, incoming_file_id, c["card"]["file_id"])]

        if not candidates:
            to_convert.append(pdf_filename)
            continue

        best = candidates[0]
        decision = resolutions.get(incoming_file_id)
        if decision is None and not non_interactive:
            decision = prompt_fn(pdf_filename, best)

        if decision == "yes":
            copy_duplicate_artifacts(
                academic_hub_root, best["course"], best["card"],
                current_course, new_folder_category, rel_pdf_path,
            )
            skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
        elif decision == "no":
            record_dismissal(academic_hub_root, incoming_file_id, best["card"]["file_id"])
            dismissals = load_dismissals(academic_hub_root)
            to_convert.append(pdf_filename)
        else:
            to_convert.append(pdf_filename)
            unresolved.append({"pdf_filename": pdf_filename, "incoming_file_id": incoming_file_id, "candidates": candidates})

    return {"to_convert": to_convert, "skipped": skipped, "unresolved": unresolved}


def _print_report(result: dict) -> None:
    print("\n[Duplicate check]")
    print(f"  To convert ({len(result['to_convert'])}):")
    for name in result["to_convert"]:
        print(f"    - {name}")
    print(f"  Skipped -- duplicate found, artifacts copied ({len(result['skipped'])}):")
    for pdf_filename, course, path, tier in result["skipped"]:
        print(f"    - {pdf_filename}\n      -> {course}: {path} (tier: {tier})")
    if result["unresolved"]:
        print(f"  Needs confirmation -- rerun with --resolve ({len(result['unresolved'])}):")
        for item in result["unresolved"]:
            print(f"    - {item['pdf_filename']} (incoming file_id={item['incoming_file_id']})")
            for c in item["candidates"]:
                print(f"        -> {c['course']}: {c['card']['title']} (score {c['combined']:.2f}, file_id={c['card']['file_id']})")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-course duplicate textbook detection -- run before uploading PDFs "
                     "for conversion. See docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md",
    )
    parser.add_argument(
        "--textbook-subdir", required=True,
        help="Path relative to academic-hub/, e.g. academic_resources/microecon/textbooks (same value as the conversion instructions' Step 0.2).",
    )
    parser.add_argument("--academic-hub-root", default=None, help="Defaults to the academic-hub/ folder next to this project.")
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Never block on input(); Tier 2 candidates are reported under 'Needs confirmation' and left unresolved unless --resolve is given for them.",
    )
    parser.add_argument(
        "--resolve", action="append", default=[], metavar="FILE_ID=yes|no",
        help="Apply a decision for one Tier 2 candidate's incoming file_id (repeatable).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    resolutions: dict[str, str] = {}
    for entry in args.resolve:
        file_id, sep, decision = entry.partition("=")
        if not sep or decision not in ("yes", "no"):
            parser.error(f"--resolve {entry!r} must be FILE_ID=yes or FILE_ID=no")
        resolutions[file_id] = decision

    academic_hub_root = args.academic_hub_root or _default_academic_hub_root()
    result = run_duplicate_check(args.textbook_subdir, academic_hub_root, args.non_interactive, resolutions)
    _print_report(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: PASS (every test in the file, all six task's worth)

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): wire up duplicate_check CLI (non-interactive + resolve flow)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Finalize and commit the two instructions documents

**Files:**
- Modify: `convert_textbook_instructions.md` (already edited in-session -- Step 0.4 inserted; this task verifies and commits it)
- Modify: `convert_textbook_agent_instructions.md` (already drafted in-session as a new file; this task verifies its CLI usage matches Task 6's real flags and commits it)

Both files already exist with their intended content from earlier in this session. This task is verification + commit, not first-draft writing.

**Interfaces:**
- Consumes: `indexer/duplicate_check.py`'s actual CLI surface from Task 6 (`--textbook-subdir`, `--academic-hub-root`, `--non-interactive`, `--resolve FILE_ID=yes|no`).

- [ ] **Step 1: Verify `convert_textbook_instructions.md`'s new Step 0.4 matches the real CLI**

Open `convert_textbook_instructions.md` and confirm its "Step 0.4: Check
for cross-course duplicates" section invokes exactly
`python -m indexer.duplicate_check --textbook-subdir "$TEXTBOOK_SUBDIR"`
(no `--non-interactive` here -- this file is the human-interactive
version, so the default blocking-prompt mode is correct for it). If it
doesn't match Task 6's actual flag names, fix it now.

- [ ] **Step 2: Verify `convert_textbook_agent_instructions.md` matches the real CLI**

Open `convert_textbook_agent_instructions.md` and confirm every
`indexer.duplicate_check` invocation in its "Step 0.3" section uses
`--non-interactive` and the `--resolve <file_id>=yes|no` syntax exactly
as Task 6 implemented it (not `--interactive`/`--report-only`, which do
not exist as flags -- if any stale reference to those remains, fix it).
Confirm every other gcloud command in the file (Steps -1, 0-5) is a
verbatim, syntactically valid match to the corresponding command already
present in `convert_textbook_instructions.md` -- these must never drift
apart on the substance (project/zone/bucket variable names, VM creation
flags, scp paths), only on interactivity framing.

- [ ] **Step 3: Run the full test suite once more**

Run: `pytest tests/ -v`
Expected: PASS (no regressions from the documentation-only changes in this task; this also re-confirms Tasks 1-6 are still green before this plan is considered done)

- [ ] **Step 4: Commit both documents together**

```bash
git add convert_textbook_instructions.md convert_textbook_agent_instructions.md
git commit -m "docs(textbook): add agent-facing conversion instructions, wire up Step 0.4

convert_textbook_instructions.md gains a Step 0.4 that runs the new
indexer/duplicate_check.py pre-flight check before any PDF is uploaded.

convert_textbook_agent_instructions.md is a new, autonomous-agent-facing
rewrite of the same pipeline: no interactive Docker shell (commands run
directly on the host via already-authenticated local gcloud), a Step -1
read-only preflight verification, explicit stop-and-ask points (nested
subfolder inclusion, a size/cost sanity check before VM creation, every
Tier 2 duplicate candidate, VM deletion), and condensed debugging
guidance drawn from the human doc's existing troubleshooting notes.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** §2 (where it runs) -> Task 6's `run_duplicate_check`/CLI; §3 (tiers) -> Tasks 1-3; §4 (confirmation/dismissal) -> Tasks 4 & 6; §5 (copy + card clone) -> Task 5; §6 (reporting/error handling) -> Task 6's `_print_report` and the per-candidate `try/except` blocks in Tasks 2, 3, 6; §7 (files touched) -> matches this plan's file list exactly; §8 (testing) -> every bullet has a corresponding test in Tasks 1-6.
- **Placeholder scan:** no TBD/TODO; every step shows real, complete code.
- **Type/signature consistency:** `find_exact_duplicate`, `find_fuzzy_candidates`, `copy_duplicate_artifacts`, and `run_duplicate_check`'s signatures are identical between their "Interfaces" declaration and their implementation across Tasks 2-6 -- checked by hand while writing this plan (in particular, `new_source_pdf_path` is threaded through consistently rather than re-derived).
- **Scope:** single cohesive plan -- the two documentation files depend on the CLI's final flag names, so they're sequenced last (Task 7) rather than split into their own plan.
