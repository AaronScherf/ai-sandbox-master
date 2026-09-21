# Duplicate Auto-Resolution Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-resolve high-confidence Tier 2 duplicate matches immediately (skip + copy + clone) instead of always blocking on a human decision, with a lightweight post-hoc confirmation queue and a safe recovery path for a wrong auto-skip.

**Architecture:** A new `AUTO_SKIP_THRESHOLD` constant splits Tier 2 matches into two bands inside `run_duplicate_check`: at or above it, auto-resolve immediately (unless an explicit `--resolve` decision was already given, which always wins); below it, unchanged existing behavior. A new pending-confirmation store (mirroring the existing dismissals store exactly) records every auto-skip for later review via new `--review-pending`/`--confirm-pending`/`--reject-pending` CLI modes.

**Tech Stack:** Python 3 stdlib only, `unittest` (matches `tests/test_duplicate_check.py`'s existing conventions).

**Spec:** `docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`, Component 1.

## Global Constraints

- No change to Tier 1 (exact byte-hash) handling, `find_fuzzy_candidates`'s scoring, or `SURFACE_THRESHOLD` — this plan only changes what happens *after* a Tier 2 candidate is found.
- An explicit `--resolve FILE_ID=yes|no` decision always takes precedence over the auto-skip threshold — a human/agent's explicit decision must never be silently overridden by a heuristic.
- The pending-confirmation store lives at `.index/duplicates/pending_confirmation.json` — the same nested directory `dismissals.json` already uses, for the same reason (a flat `.index/`-level file would be misread as a phantom course by `list_courses()`). It is git-tracked, not gitignored.
- **Real-code finding from this plan's own research:** two existing tests (`test_non_interactive_fuzzy_match_is_left_unresolved_and_kept_in_to_convert`, `test_interactive_mode_uses_prompt_fn`) use a near-identical-title fixture that will score at or near 1.0 under the real scoring function — well above the proposed `AUTO_SKIP_THRESHOLD` of 0.85. Both tests must have their fixtures changed to the Mas-Colell/Rubinstein ambiguous-band pairing (title similarity ~0.71, already the canonical worked example elsewhere in this test suite) so they keep testing what they were written to test. This is done in Task 3, not left as a surprise regression.

---

### Task 1: Pending-confirmation store

**Files:**
- Modify: `indexer/duplicate_check.py` (add new functions near the existing `_dismissals_path`/`load_dismissals`/`save_dismissals` block, currently lines 170-195)
- Test: `tests/test_duplicate_check.py` (new `TestPendingConfirmations` class, placed after the existing `TestDismissalsStorageLocation` class)

**Interfaces:**
- Produces: `_pending_confirmation_path(academic_hub_root: str) -> str`, `load_pending_confirmations(academic_hub_root: str) -> list[dict]`, `save_pending_confirmations(academic_hub_root: str, entries: list[dict]) -> None`, `record_pending_confirmation(academic_hub_root: str, entry: dict) -> None`.

- [ ] **Step 1: Write the failing tests**

Add this class to `tests/test_duplicate_check.py`, right after `TestDismissalsStorageLocation` (before the final `if __name__ == "__main__":` line):

```python
class TestPendingConfirmations(unittest.TestCase):
    """Mirrors TestDismissals/TestDismissalsStorageLocation exactly -- same
    store shape, same nested-path reasoning (pipeline-autonomy-policies
    spec, Component 1b)."""

    def test_load_missing_file_returns_empty_list(self):
        from indexer.duplicate_check import load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self.assertEqual(load_pending_confirmations(academic_hub_root), [])

    def test_record_then_load_round_trips(self):
        from indexer.duplicate_check import record_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            entry = {
                "incoming_file_id": "incoming-fid", "pdf_filename": "Ok.pdf", "course": "microecon",
                "matched_course": "econometrics", "matched_file_id": "canonical-fid",
                "matched_title": "Real Analysis with Economic Applications", "score": 0.91,
                "new_card_file_id": "clone-fid", "queued_at": "2026-09-20T00:00:00+00:00",
            }
            record_pending_confirmation(academic_hub_root, entry)
            entries = load_pending_confirmations(academic_hub_root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0], entry)

    def test_recording_multiple_entries_appends_not_overwrites(self):
        from indexer.duplicate_check import record_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "b", "pdf_filename": "B.pdf"})
            entries = load_pending_confirmations(academic_hub_root)
            self.assertEqual([e["incoming_file_id"] for e in entries], ["a", "b"])

    def test_persists_to_the_expected_nested_path(self):
        from indexer.duplicate_check import record_pending_confirmation, _pending_confirmation_path
        with tempfile.TemporaryDirectory() as academic_hub_root:
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            expected_path = os.path.join(academic_hub_root, ".index", "duplicates", "pending_confirmation.json")
            self.assertEqual(_pending_confirmation_path(academic_hub_root), expected_path)
            self.assertTrue(os.path.exists(expected_path))

    def test_pending_confirmation_file_is_not_visible_to_list_courses(self):
        # Same regression class as TestDismissalsStorageLocation -- a flat
        # .index/-level file would be misread as a phantom course by
        # list_courses(), and a future rebuild --prune would delete it.
        from indexer.duplicate_check import record_pending_confirmation
        from indexer.index_card import list_courses, save_shard
        with tempfile.TemporaryDirectory() as academic_hub_root:
            save_shard(academic_hub_root, "econometrics", [])
            record_pending_confirmation(academic_hub_root, {"incoming_file_id": "a", "pdf_filename": "A.pdf"})
            self.assertEqual(list_courses(academic_hub_root), ["econometrics"])
            self.assertNotIn("pending_confirmation", list_courses(academic_hub_root))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestPendingConfirmations -v`
Expected: FAIL with `ImportError: cannot import name 'load_pending_confirmations'`

- [ ] **Step 3: Implement**

In `indexer/duplicate_check.py`, find the existing block:

```python
def _dismissals_path(academic_hub_root: str) -> str:
    """Deliberately one level DOWN inside .index/, not directly in it:
    indexer.index_card.list_courses() treats every `*.json` file that is a
    direct child of `.index/` (except courses.json/tags.json) as a course
    shard, so a `.index/duplicate_dismissals.json` would surface as a
    phantom course named "duplicate_dismissals" -- and index_search.py's
    `rebuild --prune` would then walk that "shard", find none of its
    entries backed by a real file, and delete every recorded dismissal.
    list_courses() only ever scans direct children, never subdirectories,
    so `.index/duplicates/` is structurally outside its namespace."""
    return os.path.join(academic_hub_root, ".index", "duplicates", "dismissals.json")
```

Immediately after that function (and before `def load_dismissals`), insert:

```python
def _pending_confirmation_path(academic_hub_root: str) -> str:
    """Same nested-path reasoning as _dismissals_path above -- a flat
    .index/-level file would be misread as a phantom course by
    list_courses() and eventually deleted by `rebuild --prune`. Lives in
    the same .index/duplicates/ directory as dismissals.json, git-tracked
    the same way (durable index state, not run-local scratch output)."""
    return os.path.join(academic_hub_root, ".index", "duplicates", "pending_confirmation.json")


def load_pending_confirmations(academic_hub_root: str) -> list[dict]:
    path = _pending_confirmation_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pending_confirmations(academic_hub_root: str, entries: list[dict]) -> None:
    path = _pending_confirmation_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def record_pending_confirmation(academic_hub_root: str, entry: dict) -> None:
    entries = load_pending_confirmations(academic_hub_root)
    entries.append(entry)
    save_pending_confirmations(academic_hub_root, entries)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestPendingConfirmations -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add pending-confirmation store for auto-resolved duplicates

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Extend `copy_duplicate_artifacts` with a `pending_confirmation` flag

**Files:**
- Modify: `indexer/duplicate_check.py` (function `copy_duplicate_artifacts`)
- Test: `tests/test_duplicate_check.py` (add to the existing `TestCopyDuplicateArtifacts` class)

**Interfaces:**
- Consumes: nothing new.
- Produces: `copy_duplicate_artifacts(..., pending_confirmation: bool = False) -> dict` — when `True`, the returned (and saved) card gains `duplicate_pending_confirmation: True`; when omitted/`False` (every existing caller), behavior is identical to today — the key is simply absent, not `False`.

- [ ] **Step 1: Write the failing test**

Add this method to `TestCopyDuplicateArtifacts` in `tests/test_duplicate_check.py`, right after `test_new_card_has_a_derived_non_colliding_file_id`:

```python
    def test_pending_confirmation_flag_marks_the_new_card(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
                pending_confirmation=True,
            )

            self.assertTrue(new_card["duplicate_pending_confirmation"])
            saved_card = load_shard(academic_hub_root, "microecon")[0]
            self.assertTrue(saved_card["duplicate_pending_confirmation"])

    def test_pending_confirmation_flag_defaults_to_absent_not_false(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            _, folder_name, canonical_card = self._make_canonical_book(academic_hub_root)

            new_card = copy_duplicate_artifacts(
                academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
                "academic_resources/microecon/textbooks/Ok.pdf",
            )

            self.assertNotIn("duplicate_pending_confirmation", new_card)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest "tests/test_duplicate_check.py::TestCopyDuplicateArtifacts::test_pending_confirmation_flag_marks_the_new_card" "tests/test_duplicate_check.py::TestCopyDuplicateArtifacts::test_pending_confirmation_flag_defaults_to_absent_not_false" -v`
Expected: the first FAILs with `KeyError: 'duplicate_pending_confirmation'`; the second PASSes already (nothing sets the key yet) — confirm it passes for the right reason (the key genuinely doesn't exist), not by accident.

- [ ] **Step 3: Implement**

In `indexer/duplicate_check.py`, find the function signature:

```python
def copy_duplicate_artifacts(
    academic_hub_root: str, canonical_course: str, canonical_card: dict,
    new_course: str, new_folder_category: str, new_source_pdf_path: str,
) -> dict:
```

Change to:

```python
def copy_duplicate_artifacts(
    academic_hub_root: str, canonical_course: str, canonical_card: dict,
    new_course: str, new_folder_category: str, new_source_pdf_path: str,
    pending_confirmation: bool = False,
) -> dict:
```

Then find:

```python
    new_card = dict(canonical_card)
    new_card["file_id"] = new_file_id
    new_card["course"] = new_course
    new_card["path"] = f"{rel_new_book_dir}/{folder_name}.md"
    new_card["source_pdf_path"] = new_source_pdf_path
    new_card["duplicate_of_file_id"] = canonical_card["file_id"]
    new_card["source_updated_at"] = now_iso()
```

Change to:

```python
    new_card = dict(canonical_card)
    new_card["file_id"] = new_file_id
    new_card["course"] = new_course
    new_card["path"] = f"{rel_new_book_dir}/{folder_name}.md"
    new_card["source_pdf_path"] = new_source_pdf_path
    new_card["duplicate_of_file_id"] = canonical_card["file_id"]
    new_card["source_updated_at"] = now_iso()
    if pending_confirmation:
        # High-confidence auto-skip (pipeline-autonomy-policies spec,
        # Component 1a) -- distinguishes this clone from a Tier 1 exact
        # match or a human-confirmed Tier 2 "yes", neither of which needs
        # post-hoc review. Absent (not False) on every other call, so
        # existing/older cards never gain a meaningless extra key.
        new_card["duplicate_pending_confirmation"] = True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py::TestCopyDuplicateArtifacts -v`
Expected: PASS (both new tests, and every pre-existing test in the class).

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add pending_confirmation flag to copy_duplicate_artifacts

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Two-tier auto-skip policy inside `run_duplicate_check`

**Files:**
- Modify: `indexer/duplicate_check.py` (the `SURFACE_THRESHOLD` constant area, and `run_duplicate_check`'s Tier 2 decision block, currently lines 415-442)
- Test: `tests/test_duplicate_check.py` — new tests in `TestRunDuplicateCheck`, plus fixture fixes to two existing tests in the same class (see Global Constraints)

**Interfaces:**
- Consumes: `record_pending_confirmation` (Task 1), `copy_duplicate_artifacts(..., pending_confirmation=True)` (Task 2).
- Produces: a new module-level constant `AUTO_SKIP_THRESHOLD = 0.85`. `run_duplicate_check`'s returned dict gains a new key, `"auto_skipped_pending_confirmation": list[dict]` (always present, possibly empty) — every other key's meaning is unchanged.

- [ ] **Step 1: Fix the two existing tests whose fixtures now land in the wrong confidence band**

This step comes first, before writing new tests, so the failure it produces in Step 2 is attributable only to the missing feature, not to a fixture that (once the feature exists) would silently start testing the wrong thing.

In `tests/test_duplicate_check.py`, find:

```python
    def test_non_interactive_fuzzy_match_is_left_unresolved_and_kept_in_to_convert(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf"), b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(len(result["unresolved"]), 1)
```

Replace it with (the Mas-Colell/Rubinstein pairing scores ~0.71 via the real filename-parsing pipeline -- above `SURFACE_THRESHOLD` but below the new `AUTO_SKIP_THRESHOLD`, exactly the band this test needs to exercise):

```python
    def test_non_interactive_fuzzy_match_is_left_unresolved_and_kept_in_to_convert(self):
        # Uses the Mas-Colell/Rubinstein ambiguous band (score >= SURFACE_
        # THRESHOLD but below AUTO_SKIP_THRESHOLD) deliberately -- this
        # test's whole point is the "surfaced but not auto-resolved" path,
        # which the two-tier policy (pipeline-autonomy-policies spec,
        # Component 1a) now reserves for exactly this confidence band. A
        # near-identical title (like the old "Ok_RealAnalysis..." fixture)
        # would now score high enough to auto-skip before ever reaching
        # here -- see Task 3's Global Constraints note.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            self._write_pdf(os.path.join(academic_hub_root, subdir, "Microeconomic Theory -- Mas-Colell.pdf"), b"a different but similarly-titled book")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "math-methods", "textbooks", "processed_outputs", "Rubinstein_LectureNotesInMicroeconomicTheory_2012")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Rubinstein_LectureNotesInMicroeconomicTheory_2012.md"), "w", encoding="utf-8") as f:
                f.write("# Lecture Notes in Microeconomic Theory")
            save_shard(academic_hub_root, "math-methods", [{
                "file_id": "rubinstein-fid", "path": "academic_resources/math-methods/textbooks/processed_outputs/Rubinstein_LectureNotesInMicroeconomicTheory_2012/Rubinstein_LectureNotesInMicroeconomicTheory_2012.md",
                "source_pdf_path": "academic_resources/math-methods/textbooks/x.pdf", "course": "math-methods",
                "doc_type": "textbook", "title": "Lecture Notes in Microeconomic Theory",
            }])

            result = run_duplicate_check(subdir, academic_hub_root, non_interactive=True, resolutions={})

            self.assertEqual(result["to_convert"], ["Microeconomic Theory -- Mas-Colell.pdf"])
            self.assertEqual(len(result["unresolved"]), 1)
            self.assertEqual(result["auto_skipped_pending_confirmation"], [])
```

Now find:

```python
    def test_interactive_mode_uses_prompt_fn(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=lambda pdf_filename, candidate: "yes",
            )
            self.assertEqual(len(result["skipped"]), 1)
```

Replace it with:

```python
    def test_interactive_mode_uses_prompt_fn(self):
        # Same ambiguous-band fixture as the test above -- a near-perfect
        # match would now be auto-skipped before ever calling prompt_fn.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Microeconomic Theory -- Mas-Colell.pdf")
            self._write_pdf(pdf_path, b"a different but similarly-titled book")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "math-methods", "textbooks", "processed_outputs", "Rubinstein_LectureNotesInMicroeconomicTheory_2012")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Rubinstein_LectureNotesInMicroeconomicTheory_2012.md"), "w", encoding="utf-8") as f:
                f.write("# Lecture Notes in Microeconomic Theory")
            save_shard(academic_hub_root, "math-methods", [{
                "file_id": "rubinstein-fid", "path": "academic_resources/math-methods/textbooks/processed_outputs/Rubinstein_LectureNotesInMicroeconomicTheory_2012/Rubinstein_LectureNotesInMicroeconomicTheory_2012.md",
                "source_pdf_path": "academic_resources/math-methods/textbooks/x.pdf", "course": "math-methods",
                "doc_type": "textbook", "title": "Lecture Notes in Microeconomic Theory",
            }])

            prompt_calls = []

            def _record_and_confirm(pdf_filename, candidate):
                prompt_calls.append(pdf_filename)
                return "yes"

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=_record_and_confirm,
            )
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(prompt_calls, ["Microeconomic Theory -- Mas-Colell.pdf"])
```

- [ ] **Step 2: Write the new failing tests**

Add these two methods to `TestRunDuplicateCheck`, right after the (now-fixed) `test_interactive_mode_uses_prompt_fn`:

```python
    def test_high_confidence_match_is_auto_skipped_without_any_prompt_or_resolution(self):
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            # This exact fixture already scores 1.0 via the real filename-
            # parsing pipeline (title/author/year all match) -- see Task
            # 3's Global Constraints note.
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            def _fail_if_called(pdf_filename, candidate):
                self.fail("prompt_fn must not be called for a high-confidence auto-skip")

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=False, resolutions={},
                prompt_fn=_fail_if_called,
            )

            self.assertEqual(result["to_convert"], [])
            self.assertEqual(len(result["skipped"]), 1)
            self.assertEqual(len(result["auto_skipped_pending_confirmation"]), 1)
            pending = result["auto_skipped_pending_confirmation"][0]
            self.assertEqual(pending["pdf_filename"], "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self.assertEqual(pending["matched_course"], "econometrics")
            self.assertGreaterEqual(pending["score"], 0.85)

            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(os.path.join(new_book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md")))

            new_card = load_shard(academic_hub_root, "microecon")[0]
            self.assertTrue(new_card["duplicate_pending_confirmation"])

    def test_explicit_resolve_decision_wins_over_the_auto_skip_threshold(self):
        # An explicit --resolve decision is a real human/agent decision --
        # it must never be silently overridden by the heuristic, even for
        # a candidate that would otherwise auto-skip. Passing "no" here
        # must dismiss and convert, not auto-skip, despite the score.
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            self._write_pdf(pdf_path, b"a re-scanned copy, different bytes")
            from indexer.index_card import compute_file_id
            incoming_file_id = compute_file_id(pdf_path)

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            result = run_duplicate_check(
                subdir, academic_hub_root, non_interactive=True,
                resolutions={incoming_file_id: "no"},
            )

            self.assertEqual(result["to_convert"], ["Ok_RealAnalysisWithEconomicApplications_2007.pdf"])
            self.assertEqual(result["skipped"], [])
            self.assertEqual(result["auto_skipped_pending_confirmation"], [])
```

- [ ] **Step 3: Run all four tests to verify they fail for the right reason**

Run: `pytest tests/test_duplicate_check.py::TestRunDuplicateCheck -v`
Expected: the two fixture-fixed tests now FAIL differently than before this step -- confirm the failure is `KeyError: 'auto_skipped_pending_confirmation'` (the key doesn't exist yet) or an assertion mismatch, not an import error. The two new tests FAIL the same way.

- [ ] **Step 4: Implement**

In `indexer/duplicate_check.py`, find the `SURFACE_THRESHOLD` constant:

```python
# Below this combined score, a fuzzy candidate is never mentioned to the
# user at all -- deliberately loose (0.6, not a high-trust bar) because
# Tier 2 never auto-skips regardless of score (spec §3-4); this threshold
# only controls noise, never trust.
SURFACE_THRESHOLD = 0.6
```

Add immediately after it:

```python
# At or above this score, a Tier 2 match auto-resolves immediately
# instead of blocking on a human decision (pipeline-autonomy-policies
# spec, Component 1a) -- an initial judgment call, not derived from data;
# revisit once real runs provide a score distribution to tune against.
# Below it (but still >= SURFACE_THRESHOLD above), behavior is unchanged
# from before this policy existed: always surfaced, never auto-resolved --
# this is deliberately where the Mas-Colell/Rubinstein-style false-
# positive risk concentrates (see tests/test_duplicate_check.py's
# TestScoreCandidate.test_similar_but_different_books_surface_above_threshold).
AUTO_SKIP_THRESHOLD = 0.85
```

Then find the Tier 2 decision block inside `run_duplicate_check`:

```python
        best = candidates[0]
        decision = resolutions.get(incoming_file_id)
        if decision is None and not non_interactive:
            decision = prompt_fn(pdf_filename, best)

        if decision == "yes":
            try:
                copy_duplicate_artifacts(
                    academic_hub_root, best["course"], best["card"],
                    current_course, new_folder_category, rel_pdf_path,
                )
                skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
            except Exception as err:
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
        elif decision == "no":
```

Change to:

```python
        best = candidates[0]
        decision = resolutions.get(incoming_file_id)

        if decision is None and best["combined"] >= AUTO_SKIP_THRESHOLD:
            # High-confidence auto-skip (spec Component 1a) -- only when
            # no explicit --resolve decision was already given for this
            # exact incoming_file_id; an explicit decision always wins.
            try:
                new_card = copy_duplicate_artifacts(
                    academic_hub_root, best["course"], best["card"],
                    current_course, new_folder_category, rel_pdf_path,
                    pending_confirmation=True,
                )
                skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
                pending_entry = {
                    "incoming_file_id": incoming_file_id, "pdf_filename": pdf_filename,
                    "course": current_course, "matched_course": best["course"],
                    "matched_file_id": best["card"]["file_id"],
                    "matched_title": best["card"].get("title", ""),
                    "score": best["combined"], "new_card_file_id": new_card["file_id"],
                    "queued_at": now_iso(),
                }
                try:
                    record_pending_confirmation(academic_hub_root, pending_entry)
                except Exception as err:
                    # The copy already succeeded -- losing this record
                    # would hide a clone that still needs review, not lose
                    # the clone itself. Still surface it in THIS run's own
                    # report even if it couldn't be persisted for later.
                    print(f"WARNING: could not persist pending-confirmation record for {pdf_filename} ({err}); "
                          f"it will not appear in a later --review-pending until this is retried.", file=sys.stderr)
                auto_skipped_pending_confirmation.append(pending_entry)
            except Exception as err:
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
            continue

        if decision is None and not non_interactive:
            decision = prompt_fn(pdf_filename, best)

        if decision == "yes":
            try:
                copy_duplicate_artifacts(
                    academic_hub_root, best["course"], best["card"],
                    current_course, new_folder_category, rel_pdf_path,
                )
                skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
            except Exception as err:
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
        elif decision == "no":
```

Then find the initialization of the result-tracking lists, near the top of `run_duplicate_check`:

```python
    to_convert: list[str] = []
    skipped: list[tuple] = []
    unresolved: list[dict] = []
```

Change to:

```python
    to_convert: list[str] = []
    skipped: list[tuple] = []
    unresolved: list[dict] = []
    auto_skipped_pending_confirmation: list[dict] = []
```

Finally, find the return statement:

```python
    return {"to_convert": to_convert, "skipped": skipped, "unresolved": unresolved}
```

Change to:

```python
    return {
        "to_convert": to_convert, "skipped": skipped, "unresolved": unresolved,
        "auto_skipped_pending_confirmation": auto_skipped_pending_confirmation,
    }
```

- [ ] **Step 5: Run the full `TestRunDuplicateCheck` class and the whole file**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: PASS — every test in the file, including `TestRunDuplicateCheckErrorIsolation` and `TestEmitToConvert` (both use Tier 1 exact-match or no-candidate fixtures, unaffected by this change) and `TestCorruptDismissalsFile`/`TestDismissalsStorageLocation` (untouched by this task).

- [ ] **Step 6: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): auto-resolve high-confidence Tier 2 duplicate matches

Explicit --resolve decisions still always win over the threshold.
Fixes two existing tests whose near-identical-title fixtures would
otherwise have started silently testing the wrong confidence band.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Reporting — `_print_report` section and `--review-pending` CLI mode

**Files:**
- Modify: `indexer/duplicate_check.py` (`_print_report`, `build_arg_parser`, `main`)
- Test: `tests/test_duplicate_check.py` (new tests near `TestEmitToConvert`)

**Interfaces:**
- Consumes: `result["auto_skipped_pending_confirmation"]` (Task 3), `load_pending_confirmations` (Task 1).
- Produces: `_print_pending_confirmations(entries: list[dict]) -> None` (new). `build_arg_parser()` gains a `--review-pending` flag and makes `--textbook-subdir` optional at the parser level (the "required unless --review-pending" check moves into `main()`).

- [ ] **Step 1: Write the failing tests**

Add these to `tests/test_duplicate_check.py`, right after the `TestEmitToConvert` class:

```python
class TestReviewPending(unittest.TestCase):
    def test_review_pending_lists_entries_across_all_courses(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            dc.record_pending_confirmation(academic_hub_root, {
                "incoming_file_id": "a", "pdf_filename": "Ok.pdf", "course": "microecon",
                "matched_course": "econometrics", "matched_file_id": "canonical-fid",
                "matched_title": "Real Analysis with Economic Applications", "score": 0.91,
                "new_card_file_id": "clone-fid", "queued_at": "2026-09-20T00:00:00+00:00",
            })
            argv = ["duplicate_check", "--review-pending", "--academic-hub-root", academic_hub_root]
            captured = StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=captured):
                dc.main()
            output = captured.getvalue()
            self.assertIn("Ok.pdf", output)
            self.assertIn("econometrics", output)
            self.assertIn("Real Analysis with Economic Applications", output)

    def test_review_pending_does_not_require_textbook_subdir(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            argv = ["duplicate_check", "--review-pending", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()  # must not raise SystemExit

    def test_normal_run_still_requires_textbook_subdir(self):
        # Replaces the old parser-level test (build_arg_parser() no longer
        # marks --textbook-subdir required=True at the argparse layer,
        # since --review-pending must be usable without it) -- the
        # requirement now lives in main() instead.
        import indexer.duplicate_check as dc
        with mock.patch.object(sys, "argv", ["duplicate_check"]):
            with self.assertRaises(SystemExit):
                dc.main()


class TestAutoSkipReportSection(unittest.TestCase):
    def test_report_includes_auto_skipped_section_with_review_command(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            subdir = "academic_resources/microecon/textbooks"
            pdf_path = os.path.join(academic_hub_root, subdir, "Ok_RealAnalysisWithEconomicApplications_2007.pdf")
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(b"a re-scanned copy, different bytes")

            book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            os.makedirs(book_dir, exist_ok=True)
            with open(os.path.join(book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
                f.write("# Real Analysis")
            save_shard(academic_hub_root, "econometrics", [{
                "file_id": "some-other-fid", "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
                "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
                "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
            }])

            argv = ["duplicate_check", "--textbook-subdir", subdir, "--academic-hub-root", academic_hub_root, "--non-interactive"]
            captured = StringIO()
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=captured):
                dc.main()
            output = captured.getvalue()
            self.assertIn("Auto-skipped as likely duplicate", output)
            self.assertIn("--review-pending", output)
```

Also delete the now-superseded test in `TestBuildArgParser`:

```python
    def test_requires_textbook_subdir(self):
        parser = build_arg_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])
```

(This assumption — that `--textbook-subdir` is required at the *parser* level — is no longer true; `test_normal_run_still_requires_textbook_subdir` above covers the same guarantee at the `main()` level instead, where the check now actually lives.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestReviewPending tests/test_duplicate_check.py::TestAutoSkipReportSection -v`
Expected: FAIL — `--review-pending` is not yet a recognized argument (argparse error), and the auto-skip report section doesn't exist yet.

- [ ] **Step 3: Implement**

In `indexer/duplicate_check.py`, find `_print_report`:

```python
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
```

Change to:

```python
def _print_report(result: dict) -> None:
    print("\n[Duplicate check]")
    print(f"  To convert ({len(result['to_convert'])}):")
    for name in result["to_convert"]:
        print(f"    - {name}")
    print(f"  Skipped -- duplicate found, artifacts copied ({len(result['skipped'])}):")
    for pdf_filename, course, path, tier in result["skipped"]:
        print(f"    - {pdf_filename}\n      -> {course}: {path} (tier: {tier})")
    if result["auto_skipped_pending_confirmation"]:
        print(f"  Auto-skipped as likely duplicate -- please confirm ({len(result['auto_skipped_pending_confirmation'])}):")
        for entry in result["auto_skipped_pending_confirmation"]:
            print(f"    - {entry['pdf_filename']}\n      -> {entry['matched_course']}: {entry['matched_title']} "
                  f"(score {entry['score']:.2f}, incoming file_id={entry['incoming_file_id']})")
        print("    Review with: python -m indexer.duplicate_check --review-pending")
    if result["unresolved"]:
        print(f"  Needs confirmation -- rerun with --resolve ({len(result['unresolved'])}):")
        for item in result["unresolved"]:
            print(f"    - {item['pdf_filename']} (incoming file_id={item['incoming_file_id']})")
            for c in item["candidates"]:
                print(f"        -> {c['course']}: {c['card']['title']} (score {c['combined']:.2f}, file_id={c['card']['file_id']})")


def _print_pending_confirmations(entries: list[dict]) -> None:
    print(f"\n[Pending duplicate confirmations] ({len(entries)}):")
    for entry in entries:
        print(f"  - {entry['pdf_filename']} (course={entry.get('course', '?')})")
        print(f"      -> {entry.get('matched_course', '?')}: {entry.get('matched_title', '?')} "
              f"(score {entry.get('score', 0):.2f}, incoming file_id={entry.get('incoming_file_id', '?')})")
    if entries:
        print("  Confirm with: python -m indexer.duplicate_check --confirm-pending FILE_ID")
        print("  Reject with:  python -m indexer.duplicate_check --reject-pending FILE_ID")
```

Then find `build_arg_parser`'s `--textbook-subdir` definition:

```python
    parser.add_argument(
        "--textbook-subdir", required=True,
        help="Path relative to academic-hub/, e.g. academic_resources/microecon/textbooks (same value as the conversion instructions' Step 0.2).",
    )
```

Change to:

```python
    parser.add_argument(
        "--textbook-subdir", default=None,
        help="Path relative to academic-hub/, e.g. academic_resources/microecon/textbooks (same value as the conversion instructions' Step 0.2). "
             "Required unless --review-pending, --confirm-pending, or --reject-pending is given.",
    )
```

Then find the end of `build_arg_parser`, right before its `return parser`:

```python
    parser.add_argument(
        "--emit-to-convert", default=None, metavar="PATH",
        help="Also write the final 'to convert' PDF filenames (one per line) to PATH, in addition to the "
             "human-readable report on stdout. Read it back with `mapfile -t PDF_FILENAMES < PATH`: a confirmed "
             "duplicate's source PDF is deliberately never deleted, so re-globbing the folder would re-include it.",
    )
    return parser
```

Change to:

```python
    parser.add_argument(
        "--emit-to-convert", default=None, metavar="PATH",
        help="Also write the final 'to convert' PDF filenames (one per line) to PATH, in addition to the "
             "human-readable report on stdout. Read it back with `mapfile -t PDF_FILENAMES < PATH`: a confirmed "
             "duplicate's source PDF is deliberately never deleted, so re-globbing the folder would re-include it.",
    )
    parser.add_argument(
        "--review-pending", action="store_true",
        help="List every pending duplicate-confirmation entry across all courses, instead of running a normal "
             "check against --textbook-subdir.",
    )
    return parser
```

Finally, find `main()`:

```python
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
    if args.emit_to_convert:
        write_to_convert_file(args.emit_to_convert, result["to_convert"])
        print(f"\n  Wrote {len(result['to_convert'])} filename(s) to {args.emit_to_convert}")
```

Change to:

```python
def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    academic_hub_root = args.academic_hub_root or _default_academic_hub_root()

    if args.review_pending:
        _print_pending_confirmations(load_pending_confirmations(academic_hub_root))
        return

    if not args.textbook_subdir:
        parser.error("--textbook-subdir is required unless --review-pending is given")

    resolutions: dict[str, str] = {}
    for entry in args.resolve:
        file_id, sep, decision = entry.partition("=")
        if not sep or decision not in ("yes", "no"):
            parser.error(f"--resolve {entry!r} must be FILE_ID=yes or FILE_ID=no")
        resolutions[file_id] = decision

    result = run_duplicate_check(args.textbook_subdir, academic_hub_root, args.non_interactive, resolutions)
    _print_report(result)
    if args.emit_to_convert:
        write_to_convert_file(args.emit_to_convert, result["to_convert"])
        print(f"\n  Wrote {len(result['to_convert'])} filename(s) to {args.emit_to_convert}")
```

- [ ] **Step 4: Delete the superseded parser-level test**

Remove this method from `TestBuildArgParser` in `tests/test_duplicate_check.py` (its guarantee is now covered by `TestReviewPending.test_normal_run_still_requires_textbook_subdir`, at the `main()` level where the check now lives):

```python
    def test_requires_textbook_subdir(self):
        parser = build_arg_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: PASS — every test in the file.

- [ ] **Step 6: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add --review-pending CLI mode and auto-skip report section

--textbook-subdir's required-ness moves from the argparse layer into
main(), since --review-pending must be usable without it.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Recovery — `--confirm-pending`/`--reject-pending` and the reject flow

**Files:**
- Modify: `indexer/duplicate_check.py` (`build_arg_parser`, `main`, plus two new functions)
- Test: `tests/test_duplicate_check.py` (new `TestConfirmAndRejectPending` class)

**Interfaces:**
- Consumes: `load_pending_confirmations`/`save_pending_confirmations` (Task 1), `load_shard`/`save_shard`/`recompute_course_entry` (already imported), `record_dismissal` (already in this module).
- Produces: `confirm_pending_confirmation(academic_hub_root: str, incoming_file_id: str) -> None`, `reject_pending_confirmation(academic_hub_root: str, incoming_file_id: str) -> None`. Both raise `ValueError` if no matching pending entry exists.

- [ ] **Step 1: Write the failing tests**

Add this class to `tests/test_duplicate_check.py`, right after `TestAutoSkipReportSection`:

```python
class TestConfirmAndRejectPending(unittest.TestCase):
    def _make_auto_skipped_clone(self, academic_hub_root):
        """Sets up exactly what Task 3's auto-skip path leaves behind:
        a real copied book directory, a clone card flagged
        duplicate_pending_confirmation, and a matching pending-confirmation
        entry -- built via the real production functions, not
        hand-fabricated, so this test exercises the actual recovery path
        against real state."""
        canonical_book_dir = os.path.join(
            academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs",
            "Ok_RealAnalysisWithEconomicApplications_2007",
        )
        os.makedirs(canonical_book_dir, exist_ok=True)
        with open(os.path.join(canonical_book_dir, "Ok_RealAnalysisWithEconomicApplications_2007.md"), "w", encoding="utf-8") as f:
            f.write("# Real Analysis")
        canonical_card = {
            "file_id": "canonical-fid",
            "path": "academic_resources/econometrics/textbooks/processed_outputs/Ok_RealAnalysisWithEconomicApplications_2007/Ok_RealAnalysisWithEconomicApplications_2007.md",
            "source_pdf_path": "academic_resources/econometrics/textbooks/Ok.pdf", "course": "econometrics",
            "doc_type": "textbook", "title": "Real Analysis with Economic Applications",
        }
        save_shard(academic_hub_root, "econometrics", [canonical_card])

        new_card = copy_duplicate_artifacts(
            academic_hub_root, "econometrics", canonical_card, "microecon", "textbooks",
            "academic_resources/microecon/textbooks/Ok.pdf", pending_confirmation=True,
        )
        from indexer.duplicate_check import record_pending_confirmation, now_iso
        pending_entry = {
            "incoming_file_id": "incoming-fid", "pdf_filename": "Ok.pdf", "course": "microecon",
            "matched_course": "econometrics", "matched_file_id": "canonical-fid",
            "matched_title": "Real Analysis with Economic Applications", "score": 0.99,
            "new_card_file_id": new_card["file_id"], "queued_at": now_iso(),
        }
        record_pending_confirmation(academic_hub_root, pending_entry)
        return new_card

    def test_confirm_removes_the_pending_entry_and_leaves_the_clone_in_place(self):
        from indexer.duplicate_check import confirm_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            confirm_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertEqual(load_pending_confirmations(academic_hub_root), [])
            clone_cards = load_shard(academic_hub_root, "microecon")
            self.assertEqual(len(clone_cards), 1)
            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(new_book_dir))

    def test_confirm_raises_for_an_unknown_incoming_file_id(self):
        from indexer.duplicate_check import confirm_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            with self.assertRaises(ValueError):
                confirm_pending_confirmation(academic_hub_root, "no-such-id")

    def test_reject_removes_the_clone_card_and_folder(self):
        from indexer.duplicate_check import reject_pending_confirmation, load_pending_confirmations
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertEqual(load_pending_confirmations(academic_hub_root), [])
            self.assertEqual(load_shard(academic_hub_root, "microecon"), [])
            new_book_dir = os.path.join(academic_hub_root, "academic_resources", "microecon", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertFalse(os.path.exists(new_book_dir))

    def test_reject_records_a_permanent_dismissal(self):
        from indexer.duplicate_check import reject_pending_confirmation, is_dismissed, load_dismissals
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            self.assertTrue(is_dismissed(load_dismissals(academic_hub_root), "incoming-fid", "canonical-fid"))

    def test_reject_leaves_the_canonical_book_untouched(self):
        from indexer.duplicate_check import reject_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)

            reject_pending_confirmation(academic_hub_root, "incoming-fid")

            canonical_cards = load_shard(academic_hub_root, "econometrics")
            self.assertEqual(len(canonical_cards), 1)
            self.assertEqual(canonical_cards[0]["file_id"], "canonical-fid")
            canonical_book_dir = os.path.join(academic_hub_root, "academic_resources", "econometrics", "textbooks", "processed_outputs", "Ok_RealAnalysisWithEconomicApplications_2007")
            self.assertTrue(os.path.exists(canonical_book_dir))

    def test_reject_raises_for_an_unknown_incoming_file_id(self):
        from indexer.duplicate_check import reject_pending_confirmation
        with tempfile.TemporaryDirectory() as academic_hub_root:
            with self.assertRaises(ValueError):
                reject_pending_confirmation(academic_hub_root, "no-such-id")

    def test_cli_confirm_pending_flag(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)
            argv = ["duplicate_check", "--confirm-pending", "incoming-fid", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()
            self.assertEqual(dc.load_pending_confirmations(academic_hub_root), [])

    def test_cli_reject_pending_flag(self):
        import indexer.duplicate_check as dc
        with tempfile.TemporaryDirectory() as academic_hub_root:
            self._make_auto_skipped_clone(academic_hub_root)
            argv = ["duplicate_check", "--reject-pending", "incoming-fid", "--academic-hub-root", academic_hub_root]
            with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout", new=StringIO()):
                dc.main()
            self.assertEqual(load_shard(academic_hub_root, "microecon"), [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_duplicate_check.py::TestConfirmAndRejectPending -v`
Expected: FAIL with `ImportError: cannot import name 'confirm_pending_confirmation'`

- [ ] **Step 3: Implement**

In `indexer/duplicate_check.py`, add these two functions right after `record_pending_confirmation` (from Task 1):

```python
def confirm_pending_confirmation(academic_hub_root: str, incoming_file_id: str) -> None:
    """The clone stands as correct -- just removes it from the pending
    queue, no further action (pipeline-autonomy-policies spec, Component 1c)."""
    entries = load_pending_confirmations(academic_hub_root)
    if not any(e.get("incoming_file_id") == incoming_file_id for e in entries):
        raise ValueError(f"no pending confirmation found for incoming_file_id={incoming_file_id!r}")
    remaining = [e for e in entries if e.get("incoming_file_id") != incoming_file_id]
    save_pending_confirmations(academic_hub_root, remaining)


def reject_pending_confirmation(academic_hub_root: str, incoming_file_id: str) -> None:
    """Recovery path for a post-hoc 'no, that wasn't actually a
    duplicate' decision (spec Component 1d): removes the wrongly-created
    clone (card + copied folder), records a permanent dismissal so the
    pair is never proposed again, and removes the pending entry. The
    original PDF is never touched -- it was never moved by
    copy_duplicate_artifacts in the first place -- so it naturally
    reappears in 'to convert' the next time duplicate_check runs against
    that course."""
    entries = load_pending_confirmations(academic_hub_root)
    entry = next((e for e in entries if e.get("incoming_file_id") == incoming_file_id), None)
    if entry is None:
        raise ValueError(f"no pending confirmation found for incoming_file_id={incoming_file_id!r}")

    new_course = entry["course"]
    new_card_file_id = entry["new_card_file_id"]
    cards = load_shard(academic_hub_root, new_course)
    clone_card = next((c for c in cards if c.get("file_id") == new_card_file_id), None)
    if clone_card is not None:
        book_dir = os.path.join(academic_hub_root, os.path.normpath(os.path.dirname(clone_card["path"])))
        if os.path.isdir(book_dir):
            shutil.rmtree(book_dir)
        remaining_cards = [c for c in cards if c.get("file_id") != new_card_file_id]
        save_shard(academic_hub_root, new_course, remaining_cards)
        recompute_course_entry(academic_hub_root, new_course)

    record_dismissal(academic_hub_root, entry["incoming_file_id"], entry["matched_file_id"])

    remaining_entries = [e for e in entries if e.get("incoming_file_id") != incoming_file_id]
    save_pending_confirmations(academic_hub_root, remaining_entries)
```

Then find `build_arg_parser`'s `--review-pending` addition from Task 4:

```python
    parser.add_argument(
        "--review-pending", action="store_true",
        help="List every pending duplicate-confirmation entry across all courses, instead of running a normal "
             "check against --textbook-subdir.",
    )
    return parser
```

Change to:

```python
    parser.add_argument(
        "--review-pending", action="store_true",
        help="List every pending duplicate-confirmation entry across all courses, instead of running a normal "
             "check against --textbook-subdir.",
    )
    parser.add_argument(
        "--confirm-pending", default=None, metavar="FILE_ID",
        help="Confirm one auto-skipped clone (by its incoming file_id) is a correct duplicate -- removes it "
             "from the pending-confirmation queue, no other action.",
    )
    parser.add_argument(
        "--reject-pending", default=None, metavar="FILE_ID",
        help="Reject one auto-skipped clone (by its incoming file_id) -- removes the clone card and copied "
             "folder, records a permanent dismissal, and clears the pending-confirmation entry.",
    )
    return parser
```

Finally, find `main()`'s `--review-pending` handling from Task 4:

```python
    if args.review_pending:
        _print_pending_confirmations(load_pending_confirmations(academic_hub_root))
        return

    if not args.textbook_subdir:
```

Change to:

```python
    if args.confirm_pending:
        confirm_pending_confirmation(academic_hub_root, args.confirm_pending)
        print(f"Confirmed -- {args.confirm_pending} removed from the pending-confirmation queue.")
        return

    if args.reject_pending:
        reject_pending_confirmation(academic_hub_root, args.reject_pending)
        print(f"Rejected -- clone removed, dismissal recorded for {args.reject_pending}.")
        return

    if args.review_pending:
        _print_pending_confirmations(load_pending_confirmations(academic_hub_root))
        return

    if not args.textbook_subdir:
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_duplicate_check.py -v`
Expected: PASS — every test in the file.

- [ ] **Step 5: Commit**

```bash
git add indexer/duplicate_check.py tests/test_duplicate_check.py
git commit -m "feat(indexer): add --confirm-pending/--reject-pending recovery flow

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full project test suite: `pytest tests/ -q` — expect all green.
- [ ] `python -m indexer.duplicate_check --review-pending --academic-hub-root <path>` runs without error against a fresh (empty) academic-hub root.
- [ ] `grep -n "AUTO_SKIP_THRESHOLD" indexer/duplicate_check.py` shows both the constant definition and its use in `run_duplicate_check`.

## Self-Review Notes

- **Spec coverage:** 1a (two-tier policy) -> Task 3; 1b (pending-confirmation store) -> Task 1; 1c (reporting + CLI) -> Tasks 4-5; 1d (reject recovery) -> Task 5; 1e (invocation-time surfacing) -> satisfied by `--review-pending` existing (Task 4) for a future caller (the sibling skill spec) to invoke, not additional code in this plan.
- **Placeholder scan:** no TBD/TODO; every step shows complete code verified against the actual current file content (read in full before writing this plan).
- **Type/signature consistency:** `copy_duplicate_artifacts`'s new `pending_confirmation` parameter (Task 2) is consumed with the same name and position in Task 3's call. `run_duplicate_check`'s new `auto_skipped_pending_confirmation` return key (Task 3) is read identically in Task 4's `_print_report`. `reject_pending_confirmation`/`confirm_pending_confirmation` (Task 5) consume the exact entry-dict shape Task 3 produces (`incoming_file_id`, `course`, `matched_file_id`, `new_card_file_id`).
- **Real-fixture verification:** this plan's Task 3 fixture changes were derived by tracing the actual `extract_bibliographic_info_from_filename`/`score_candidate` logic by hand against real filenames, not assumed — confirmed the "Ok_RealAnalysis..." fixture scores 1.0 (author+title+year all match) and the Mas-Colell/Rubinstein fixture scores ~0.71 (title overlap only), placing each correctly on either side of the proposed 0.85 threshold.
- **Scope:** five tasks, all confined to `indexer/duplicate_check.py` and its test file — no change to `indexer/index_search.py` (that's the sibling rebuild-safety-fix plan) or the OOM/cost escalation ladder (a separate sibling plan).
