# Journal Articles: Metadata & Folder Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `audit_metadata.py`, a script that re-checks each converted journal article's folder, tags, title, authors, and DOI against its real full text and fresh OpenAlex data — auto-correcting folder placement and tag-frontmatter sync (both have a mechanically well-defined right answer), and flagging title/author/DOI mismatches for human review — then chain it onto `reconcile_needs_manual.py`'s own run so it happens automatically, not as a separate step to remember.

**Architecture:** A new root-level module `audit_metadata.py` (same location as `reconcile_needs_manual.py`, in `academic-rag-model/`) exposes a set of small, independently-testable functions culminating in one orchestrator, `audit()`, plus a thin `main()` CLI. `reconcile_needs_manual.py`'s `main()` calls `audit()` as its last step. A new shared module `journal_discovery/text_match.py` breaks an import cycle that chaining introduces. A new `indexer/index_card.move_card()` function handles moving an index card between course shards when a folder gets corrected.

**Tech Stack:** Python 3, `unittest` (stdlib) for tests, `pathlib`, existing `journal_discovery`/`indexer` packages. No new dependencies — no LLM/Gemini calls anywhere in this feature.

**Spec:** `docs/superpowers/specs/2026-09-02-metadata-folder-audit-design.md`

## Global Constraints

- No LLM/Gemini calls anywhere in `audit_metadata.py` — the only network call is `discovery.resolve_work_by_doi()` (free, keyless OpenAlex).
- Auto-correct only folder placement and tag-frontmatter sync (both have a mechanically well-defined right answer); title, authors, and DOI mismatches are always flag-only, never auto-edited.
- A paper is only re-audited if `entry.get("audited_at")` is unset, unless `recheck_all=True` is passed.
- `audited_at` is set on an entry only after every check for that paper has completed without an unrecoverable error (a folder-move failure specifically must leave `audited_at` unset so the paper is retried on the next run).
- `audit_flags` is omitted entirely from an entry with no mismatches (not stored as an empty list) — worklist filtering relies on plain truthiness.
- Tag rendering when syncing frontmatter matches `retag.py`'s own format exactly: `"[" + ", ".join(tags) + "]"`.
- `reconcile_needs_manual.py`'s importable `reconcile()` function stays audit-free; only its `main()` CLI wrapper chains to `audit_metadata.audit()`. Missing `OPENALEX_CONTACT_EMAIL` must not make `reconcile_needs_manual.py`'s command fail — it prints a warning and skips just the audit step, exiting successfully. The standalone `python -m audit_metadata` CLI, by contrast, still hard-fails without `OPENALEX_CONTACT_EMAIL` (matching `discover.py`/`snowball.py`'s existing convention).
- All new/modified test files use `unittest.TestCase` with `tempfile.TemporaryDirectory()`, matching every existing test in `tests/` (see `test_reconcile_needs_manual.py`, `test_discovery.py`, `test_index_card.py`, `test_worklist.py`) — no new test framework.

---

## Task 1: Promote `normalize()` into `journal_discovery/text_match.py`

**Files:**
- Create: `journal_discovery/text_match.py`
- Modify: `reconcile_needs_manual.py` (replace private `_normalize()`/`_NON_ALNUM_RE` with an import)
- Test: `tests/test_text_match.py` (new)

**Interfaces:**
- Produces: `journal_discovery.text_match.normalize(text: str) -> str` — lowercases and strips every non-alphanumeric character. Used by Task 4 (`audit_metadata.py`'s text-only checks) without ever importing from `reconcile_needs_manual.py`, which is what avoids the import cycle Task 9 introduces (`reconcile_needs_manual.py` importing `audit_metadata`).

This is pulled out first, on its own, so every later task that needs text normalization (Task 4) has a stable import target from the start.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_text_match.py
import unittest

from journal_discovery.text_match import normalize


class TestNormalize(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(normalize("Causal Inference"), "causalinference")

    def test_strips_punctuation_and_whitespace(self):
        self.assertEqual(normalize("Causal Inference, from Hypothetical-Evaluations!!"),
                          "causalinferencefromhypotheticalevaluations")

    def test_empty_string(self):
        self.assertEqual(normalize(""), "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_text_match.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'journal_discovery.text_match'`

- [ ] **Step 3: Create `journal_discovery/text_match.py` and update `reconcile_needs_manual.py`**

```python
# journal_discovery/text_match.py
"""
text_match.py
Plain-text normalization shared by reconcile_needs_manual.py and
audit_metadata.py -- promoted out to a small standalone module (rather
than one importing it from the other) specifically because
reconcile_needs_manual.py's own main() now calls into audit_metadata.py
(spec S2), which would otherwise create an import cycle.
"""
from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    return _NON_ALNUM_RE.sub("", text.lower())
```

In `reconcile_needs_manual.py`:
1. Remove the module-level `_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")` (line 29) and the `_normalize()` function (lines 34-35).
2. Add `from journal_discovery.text_match import normalize` to the imports (alongside the existing `journal_discovery.manifest`/`journal_discovery.worklist` imports).
3. In `is_confirmed_downloaded()`, replace both calls to `_normalize(...)` with `normalize(...)`.

The resulting `is_confirmed_downloaded()` body is unchanged in behavior — only the import source of the normalization function changes:

```python
def is_confirmed_downloaded(doi: str | None, title: str, md_files: list[Path]) -> Path | None:
    """Returns the matching .md path if this paper's real content is
    found among the converted files -- a DOI substring match first
    (unambiguous when present), a normalized-title substring match as
    fallback for papers that don't print their DOI in the visible text.
    None means still needs a manual download."""
    normalized_title = normalize(title) if title else None
    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8", errors="ignore")
        if doi and doi.lower() in content.lower():
            return md_path
        if normalized_title and normalized_title in normalize(content):
            return md_path
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_text_match.py tests/test_reconcile_needs_manual.py -v`
Expected: PASS (all of `test_text_match.py`'s 3 tests, and every existing `test_reconcile_needs_manual.py` test unchanged in behavior)

- [ ] **Step 5: Commit**

```bash
git add journal_discovery/text_match.py reconcile_needs_manual.py tests/test_text_match.py
git commit -m "refactor(journal_discovery): promote normalize() into text_match.py

Breaks an import cycle Task 9 will otherwise introduce, once
reconcile_needs_manual.py's main() starts calling into audit_metadata.py."
```

---

## Task 2: `index_card.move_card()` — move a card between course shards

**Files:**
- Modify: `indexer/index_card.py`
- Test: `tests/test_index_card.py` (extend)

**Interfaces:**
- Consumes: `load_shard(academic_hub_root, course)`, `save_shard(academic_hub_root, course, cards)`, `find_card_by_file_id(academic_hub_root, file_id)`, `recompute_course_entry(academic_hub_root, course)` — all existing, unchanged.
- Produces: `move_card(academic_hub_root: str, file_id: str, new_course: str) -> bool` — returns `True` if a card was found and moved, `False` if no card with that `file_id` exists anywhere. A no-op (still returns `True`) when `new_course` already equals the card's current course. Used by Task 5's `apply_folder_correction()`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_index_card.py, alongside the existing imports and TestFindCardByFileId class
```

Add `move_card` to the existing `from indexer.index_card import (...)` block at the top of the file, then add:

```python
class TestMoveCard(unittest.TestCase):
    def test_moves_card_between_shards_and_updates_course_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [
                {"file_id": "x", "path": "misc/processed_outputs/a.md",
                 "source_pdf_path": "misc/a.pdf", "course": "misc",
                 "embedding": [1.0, 0.0], "tags": ["some-tag"]},
            ])
            result = move_card(tmp, "x", "business")

            self.assertTrue(result)
            self.assertEqual(load_shard(tmp, "misc"), [])
            moved = load_shard(tmp, "business")
            self.assertEqual(len(moved), 1)
            self.assertEqual(moved[0]["course"], "business")
            self.assertEqual(moved[0]["path"], "business/processed_outputs/a.md")
            self.assertEqual(moved[0]["source_pdf_path"], "business/a.pdf")

    def test_recomputes_course_entry_for_both_old_and_new_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [
                {"file_id": "x", "path": "misc/processed_outputs/a.md",
                 "source_pdf_path": "misc/a.pdf", "course": "misc",
                 "embedding": [1.0, 0.0], "tags": []},
                {"file_id": "y", "path": "misc/processed_outputs/b.md",
                 "source_pdf_path": "misc/b.pdf", "course": "misc",
                 "embedding": [0.0, 1.0], "tags": []},
            ])
            move_card(tmp, "x", "business")

            self.assertEqual(load_courses(tmp)["misc"]["file_count"], 1)
            self.assertEqual(load_courses(tmp)["business"]["file_count"], 1)

    def test_returns_false_when_card_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [{"file_id": "x", "path": "a.md", "course": "misc",
                                       "embedding": [1.0], "tags": []}])
            self.assertFalse(move_card(tmp, "nonexistent", "business"))

    def test_no_op_when_already_in_target_course(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [{"file_id": "x", "path": "misc/a.md", "source_pdf_path": "misc/a.pdf",
                                       "course": "misc", "embedding": [1.0], "tags": []}])
            result = move_card(tmp, "x", "misc")
            self.assertTrue(result)
            self.assertEqual(len(load_shard(tmp, "misc")), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_index_card.py -v -k MoveCard`
Expected: FAIL with `ImportError: cannot import name 'move_card'`

- [ ] **Step 3: Implement `move_card()`**

Add to `indexer/index_card.py`, after `find_card_by_file_id()` (after line 328's `_replace_card` helper, before `reconcile_and_write`):

```python
def move_card(academic_hub_root: str, file_id: str, new_course: str) -> bool:
    """Moves a card between course shards when a paper's folder gets
    corrected (audit_metadata.py's folder check). Updates the card's own
    course/path/source_pdf_path fields to match its new location, and
    recomputes both the old and new course's rollup entry in
    courses.json so centroid/predominant_tags stay correct on both
    sides. A no-op (still True) when the card is already in new_course."""
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    old_course, card = found
    if old_course == new_course:
        return True

    old_cards = [c for c in load_shard(academic_hub_root, old_course) if c["file_id"] != file_id]
    save_shard(academic_hub_root, old_course, old_cards)
    recompute_course_entry(academic_hub_root, old_course)

    card = dict(card)
    card["course"] = new_course
    if card.get("path"):
        card["path"] = card["path"].replace(f"{old_course}/", f"{new_course}/", 1)
    if card.get("source_pdf_path"):
        card["source_pdf_path"] = card["source_pdf_path"].replace(f"{old_course}/", f"{new_course}/", 1)

    new_cards = load_shard(academic_hub_root, new_course)
    new_cards.append(card)
    save_shard(academic_hub_root, new_course, new_cards)
    recompute_course_entry(academic_hub_root, new_course)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_index_card.py -v`
Expected: PASS (all `TestMoveCard` tests, and every pre-existing test in the file unchanged)

- [ ] **Step 5: Commit**

```bash
git add indexer/index_card.py tests/test_index_card.py
git commit -m "feat(indexer): add index_card.move_card() to relocate a card between course shards

Needed by audit_metadata.py's folder correction -- no prior committed
tool did this (the earlier grasp/competition-biology folder cleanup used
a one-off script that was never committed)."
```

---

## Task 3: `audit_metadata.py` — target selection and path resolution

**Files:**
- Create: `audit_metadata.py`
- Test: `tests/test_audit_metadata.py` (new)

**Interfaces:**
- Consumes: nothing new yet (pure functions over plain dicts/paths).
- Produces: `select_audit_targets(manifest: dict, recheck_all: bool) -> list[tuple[str, dict]]`; `resolve_paper_paths(articles_dir, key: str, entry: dict) -> tuple[Path | None, Path | None]` — both used by every later task in this file, and by `audit()` in Task 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_audit_metadata.py
import tempfile
import unittest
from pathlib import Path

from audit_metadata import resolve_paper_paths, select_audit_targets


class TestSelectAuditTargets(unittest.TestCase):
    def test_includes_fetched_and_downloaded_without_audited_at(self):
        manifest = {
            "10.1/a": {"status": "fetched"},
            "10.1/b": {"status": "downloaded"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual({k for k, _ in targets}, {"10.1/a", "10.1/b"})

    def test_excludes_needs_manual_and_proposed(self):
        manifest = {
            "10.1/a": {"status": "needs_manual"},
            "10.1/b": {"status": "proposed"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual(targets, [])

    def test_skips_already_audited_by_default(self):
        manifest = {
            "10.1/a": {"status": "fetched", "audited_at": "2026-09-01T00:00:00+00:00"},
            "10.1/b": {"status": "fetched"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual([k for k, _ in targets], ["10.1/b"])

    def test_recheck_all_includes_already_audited(self):
        manifest = {"10.1/a": {"status": "fetched", "audited_at": "2026-09-01T00:00:00+00:00"}}
        targets = select_audit_targets(manifest, recheck_all=True)
        self.assertEqual([k for k, _ in targets], ["10.1/a"])


class TestResolvePaperPaths(unittest.TestCase):
    def test_fetched_entry_derives_deterministic_paths(self):
        entry = {"status": "fetched", "folder": "business"}
        pdf_path, md_path = resolve_paper_paths("/articles", "10.1/some-paper", entry)
        self.assertEqual(pdf_path, Path("/articles/business/10-1-some-paper.pdf"))
        self.assertEqual(md_path, Path("/articles/business/processed_outputs/10-1-some-paper.md"))

    def test_fetched_entry_without_folder_returns_none_none(self):
        entry = {"status": "fetched"}
        self.assertEqual(resolve_paper_paths("/articles", "10.1/x", entry), (None, None))

    def test_downloaded_entry_uses_matched_md_path(self):
        entry = {"status": "downloaded", "matched_md_path": "/articles/physics/processed_outputs/weird-name.md"}
        pdf_path, md_path = resolve_paper_paths("/articles", "10.1/x", entry)
        self.assertEqual(md_path, Path("/articles/physics/processed_outputs/weird-name.md"))
        self.assertEqual(pdf_path, Path("/articles/physics/weird-name.pdf"))

    def test_downloaded_entry_without_matched_md_path_returns_none_none(self):
        entry = {"status": "downloaded"}
        self.assertEqual(resolve_paper_paths("/articles", "10.1/x", entry), (None, None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'audit_metadata'`

- [ ] **Step 3: Create `audit_metadata.py` with these two functions**

```python
#!/usr/bin/env python3
"""
audit_metadata.py
Re-checks each converted journal article's folder, tags, title, authors,
and DOI against its real full text and fresh OpenAlex data -- the gap
flagged in docs/2026-09-01-journal-discovery-status.md point 6:
.meta.json sidecars are written once at discovery time and never
revisited, and reconcile_needs_manual.py's folder/content preview was
read-only. Design: docs/superpowers/specs/2026-09-02-metadata-folder-audit-design.md.

Two ways to run this: automatically, chained onto the end of
reconcile_needs_manual.py's own run (the normal way this runs day to
day); or standalone for a forced full re-audit:
    python -m audit_metadata --recheck-all
"""
from __future__ import annotations

from pathlib import Path

from journal_discovery.topic_routing import sanitize_topic_name


def select_audit_targets(manifest: dict, recheck_all: bool) -> list[tuple[str, dict]]:
    targets = []
    for key, entry in manifest.items():
        if entry.get("status") not in ("fetched", "downloaded"):
            continue
        if not recheck_all and entry.get("audited_at"):
            continue
        targets.append((key, entry))
    return targets


def resolve_paper_paths(articles_dir, key: str, entry: dict) -> tuple[Path | None, Path | None]:
    """Returns (pdf_path, md_path) for a paper already known to be
    fetched/downloaded. A fetched entry's paths are deterministic from
    its manifest key (mirrors topic_routing.pdf_filename()'s own
    derivation, since the manifest key is already
    `work.doi or work.openalex_id`, the same precedence pdf_filename()
    uses). A downloaded (manually-placed) entry's PDF filename is
    arbitrary, so its path is derived from matched_md_path, which
    reconcile_needs_manual.py's content-matching already recorded --
    process_pdf() names a manually-downloaded file's .md after that
    PDF's own (arbitrary) stem, so the relationship is recoverable."""
    if entry.get("status") == "downloaded":
        matched = entry.get("matched_md_path")
        if not matched:
            return None, None
        md_path = Path(matched)
        pdf_path = md_path.parent.parent / f"{md_path.stem}.pdf"
        return pdf_path, md_path

    folder = entry.get("folder")
    if not folder:
        return None, None
    stem = sanitize_topic_name(key)[:80] or "paper"
    pdf_path = Path(articles_dir) / folder / f"{stem}.pdf"
    md_path = Path(articles_dir) / folder / "processed_outputs" / f"{stem}.md"
    return pdf_path, md_path


if __name__ == "__main__":
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: PASS (all 8 tests)

- [ ] **Step 5: Commit**

```bash
git add audit_metadata.py tests/test_audit_metadata.py
git commit -m "feat(journal_discovery): add audit_metadata target selection and path resolution"
```

---

## Task 4: `audit_metadata.py` — title, author, and DOI checks

**Files:**
- Modify: `audit_metadata.py`
- Test: `tests/test_audit_metadata.py` (extend)

**Interfaces:**
- Consumes: `journal_discovery.text_match.normalize()` (Task 1).
- Produces: `check_title(entry: dict, text: str) -> dict | None`, `check_authors(entry: dict, text: str) -> dict | None`, `check_doi(key: str, entry: dict, text: str) -> dict | None` — each returns `None` when no mismatch (or nothing stored to check against), or a flag dict `{"type": ..., "detail": ...}` otherwise. Used by `audit()` in Task 8, and the flag dicts are exactly what lands in a manifest entry's `audit_flags` list (spec S6).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_audit_metadata.py`:

```python
from audit_metadata import check_authors, check_doi, check_title


class TestCheckTitle(unittest.TestCase):
    def test_none_when_title_found_in_text(self):
        entry = {"title": "Causal Inference from Hypothetical Evaluations"}
        text = "CAUSAL INFERENCE, FROM Hypothetical-Evaluations!! An abstract follows."
        self.assertIsNone(check_title(entry, text))

    def test_flags_when_title_not_found(self):
        entry = {"title": "A Title That Was Never Printed"}
        text = "This paper is actually about something completely different."
        flag = check_title(entry, text)
        self.assertEqual(flag["type"], "title_mismatch")
        self.assertIn("A Title That Was Never Printed", flag["detail"])

    def test_none_when_no_title_stored(self):
        self.assertIsNone(check_title({}, "any text"))


class TestCheckAuthors(unittest.TestCase):
    def test_none_when_an_author_surname_found(self):
        entry = {"authors": ["Daniel Bjorkegren", "Jane Smith"]}
        text = "This paper, by Bjorkegren and coauthors, studies mobile money."
        self.assertIsNone(check_authors(entry, text))

    def test_flags_when_no_author_found_at_all(self):
        entry = {"authors": ["A. Nobody", "B. Nobody"]}
        text = "This paper was actually written by someone else entirely."
        flag = check_authors(entry, text)
        self.assertEqual(flag["type"], "author_mismatch")

    def test_none_when_no_authors_stored(self):
        self.assertIsNone(check_authors({}, "any text"))


class TestCheckDoi(unittest.TestCase):
    def test_none_when_doi_found(self):
        self.assertIsNone(check_doi("10.1/abc", {}, "Some paper. DOI: 10.1/abc. More text."))

    def test_flags_when_doi_missing(self):
        flag = check_doi("10.1/abc", {}, "Completely unrelated text with no DOI mentioned.")
        self.assertEqual(flag["type"], "doi_mismatch")

    def test_none_for_non_doi_key(self):
        self.assertIsNone(check_doi("https://openalex.org/W1", {}, "any text"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_metadata.py -v -k "CheckTitle or CheckAuthors or CheckDoi"`
Expected: FAIL with `ImportError: cannot import name 'check_title'`

- [ ] **Step 3: Implement the three checks**

Add to `audit_metadata.py` (after the imports, add `from journal_discovery.text_match import normalize`; place these functions after `resolve_paper_paths()`):

```python
def check_title(entry: dict, text: str) -> dict | None:
    title = entry.get("title")
    if not title:
        return None
    if normalize(title) in normalize(text):
        return None
    excerpt = " ".join(text.split())[:200]
    return {"type": "title_mismatch",
            "detail": f'stored title "{title}" not found in text (excerpt: "{excerpt}")'}


def check_authors(entry: dict, text: str) -> dict | None:
    authors = entry.get("authors") or []
    if not authors:
        return None
    normalized_text = normalize(text)
    for author in authors:
        surname = author.strip().split()[-1] if author.strip() else ""
        if surname and normalize(surname) in normalized_text:
            return None
    return {"type": "author_mismatch", "detail": f"none of {authors} found in text"}


def check_doi(key: str, entry: dict, text: str) -> dict | None:
    if key.startswith("http"):
        return None
    if key.lower() in text.lower():
        return None
    return {"type": "doi_mismatch", "detail": f"stored DOI ({key}) not found in text"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add audit_metadata.py tests/test_audit_metadata.py
git commit -m "feat(journal_discovery): add audit_metadata title/author/DOI text checks

Flag-only, per spec: no mechanically safe auto-correction target exists
for a title, author list, or DOI, unlike folder/tag-sync."
```

---

## Task 5: `audit_metadata.py` — folder check and correction

**Files:**
- Modify: `audit_metadata.py`
- Test: `tests/test_audit_metadata.py` (extend)

**Interfaces:**
- Consumes: `journal_discovery.discovery.resolve_work_by_doi(doi, mailto) -> Work | None` (existing), `journal_discovery.topic_routing.sanitize_topic_name()` (existing), `indexer.index_card.compute_file_id()`/`move_card()` (Task 2).
- Produces: `check_folder(key: str, entry: dict, mailto: str) -> dict` (`{"mismatch": bool, "new_folder": str | None, "error": str | None}`); `apply_folder_correction(articles_dir, index_root, entry: dict, pdf_path: Path, md_path: Path, new_folder: str) -> tuple[Path, Path]` (returns the new `(pdf_path, md_path)`, mutates `entry["folder"]` in place, and may raise on a filesystem error — the caller in Task 8 is responsible for catching that and leaving `audited_at` unset). Used by `audit()` in Task 8.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_audit_metadata.py`:

```python
from unittest.mock import patch

from indexer.index_card import compute_file_id, load_courses, load_shard, save_shard
from audit_metadata import apply_folder_correction, check_folder


def _fake_work(concepts):
    from journal_discovery.discovery import Work
    return Work(openalex_id="https://openalex.org/W1", doi="10.1/abc", title="T",
                authors=[], year=2024, abstract=None, concepts=concepts)


class TestCheckFolder(unittest.TestCase):
    @patch("audit_metadata.resolve_work_by_doi")
    def test_no_mismatch_when_folder_already_matches(self, mock_resolve):
        mock_resolve.return_value = _fake_work(["Business"])
        result = check_folder("10.1/abc", {"folder": "business"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertEqual(result["new_folder"], "business")

    @patch("audit_metadata.resolve_work_by_doi")
    def test_mismatch_when_concept_now_differs(self, mock_resolve):
        mock_resolve.return_value = _fake_work(["Sociology"])
        result = check_folder("10.1/abc", {"folder": "grasp"}, "me@example.com")
        self.assertTrue(result["mismatch"])
        self.assertEqual(result["new_folder"], "sociology")

    def test_skipped_for_non_doi_key(self):
        result = check_folder("https://openalex.org/W1", {"folder": "misc"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertIsNotNone(result["error"])

    @patch("audit_metadata.resolve_work_by_doi")
    def test_error_when_lookup_fails(self, mock_resolve):
        mock_resolve.return_value = None
        result = check_folder("10.1/abc", {"folder": "misc"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertIsNotNone(result["error"])


class TestApplyFolderCorrection(unittest.TestCase):
    def test_moves_files_and_updates_index_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "misc" / "paper.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            meta_path = pdf_path.with_suffix(".meta.json")
            meta_path.write_text("{}", encoding="utf-8")
            md_path = tmp / "misc" / "processed_outputs" / "paper.md"
            md_path.parent.mkdir(parents=True)
            md_path.write_text("content", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "path": "misc/processed_outputs/paper.md",
                                            "source_pdf_path": "misc/paper.pdf", "course": "misc",
                                            "embedding": [1.0], "tags": []}])

            entry = {"folder": "misc"}
            new_pdf, new_md = apply_folder_correction(tmp, str(tmp), entry, pdf_path, md_path, "business")

            self.assertTrue(new_pdf.exists())
            self.assertTrue(new_md.exists())
            self.assertFalse(pdf_path.exists())
            self.assertTrue((tmp / "business" / "paper.meta.json").exists())
            self.assertEqual(entry["folder"], "business")
            self.assertEqual(load_shard(str(tmp), "business")[0]["course"], "business")
            self.assertEqual(load_courses(str(tmp))["business"]["file_count"], 1)

    def test_moves_without_meta_json_for_manually_downloaded_papers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "misc" / "weird-name.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "misc" / "processed_outputs" / "weird-name.md"
            md_path.parent.mkdir(parents=True)
            md_path.write_text("content", encoding="utf-8")

            entry = {"folder": "misc"}
            new_pdf, new_md = apply_folder_correction(tmp, str(tmp), entry, pdf_path, md_path, "sociology")

            self.assertTrue(new_pdf.exists())
            self.assertTrue(new_md.exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_metadata.py -v -k "CheckFolder or ApplyFolderCorrection"`
Expected: FAIL with `ImportError: cannot import name 'check_folder'`

- [ ] **Step 3: Implement `check_folder()` and `apply_folder_correction()`**

Add to `audit_metadata.py`. Update the imports at the top to add:

```python
from journal_discovery.discovery import resolve_work_by_doi
from indexer.index_card import compute_file_id, move_card
```

Then:

```python
def check_folder(key: str, entry: dict, mailto: str) -> dict:
    if key.startswith("http"):
        return {"mismatch": False, "new_folder": None, "error": "non-DOI key, folder check skipped"}
    work = resolve_work_by_doi(key, mailto)
    if work is None:
        return {"mismatch": False, "new_folder": None, "error": "resolve_work_by_doi failed"}
    top_concept = work.concepts[0] if work.concepts else None
    new_folder = sanitize_topic_name(top_concept)
    current_folder = entry.get("folder")
    return {"mismatch": new_folder != current_folder, "new_folder": new_folder, "error": None}


def apply_folder_correction(
    articles_dir, index_root, entry: dict, pdf_path: Path, md_path: Path, new_folder: str,
) -> tuple[Path, Path]:
    """Moves every file belonging to this paper into its corrected
    folder and relocates its index card to match. Lets any filesystem
    or index-update exception propagate -- audit()'s caller (Task 8) is
    responsible for catching it and leaving audited_at unset so the
    paper is retried on the next run, rather than silently left
    half-migrated."""
    dest_folder = Path(articles_dir) / new_folder
    dest_folder.mkdir(parents=True, exist_ok=True)

    file_id = compute_file_id(str(pdf_path))

    new_pdf_path = dest_folder / pdf_path.name
    pdf_path.rename(new_pdf_path)

    meta_path = pdf_path.with_suffix(".meta.json")
    if meta_path.exists():
        meta_path.rename(dest_folder / meta_path.name)

    new_processed_dir = dest_folder / "processed_outputs"
    new_processed_dir.mkdir(exist_ok=True)
    new_md_path = new_processed_dir / md_path.name
    md_path.rename(new_md_path)

    cache_path = md_path.parent / f"{md_path.stem}_pages_cache.json"
    if cache_path.exists():
        cache_path.rename(new_processed_dir / cache_path.name)

    move_card(index_root, file_id, new_folder)
    entry["folder"] = new_folder
    return new_pdf_path, new_md_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add audit_metadata.py tests/test_audit_metadata.py
git commit -m "feat(journal_discovery): add audit_metadata folder check and auto-correction

Auto-corrects because the right value is mechanically derivable (a
fresh OpenAlex lookup, same level-0-preferring logic as the existing
folder-naming fix) -- unlike title/author/DOI, which stay flag-only."
```

---

## Task 6: `audit_metadata.py` — tag sync check and correction

**Files:**
- Modify: `audit_metadata.py`
- Test: `tests/test_audit_metadata.py` (extend)

**Interfaces:**
- Consumes: `indexer.index_card.compute_file_id()`/`find_card_by_file_id()` (existing).
- Produces: `check_tag_sync(index_root, pdf_path: Path, md_path: Path) -> dict` (`{"mismatch": bool, "index_tags": list[str] | None, "found_card": bool}`); `apply_tag_sync(md_path: Path, tags: list[str]) -> None`. Used by `audit()` in Task 8.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_audit_metadata.py`:

```python
from indexer.index_card import save_shard as _save_shard_for_tags  # already imported above if reusing save_shard
from audit_metadata import apply_tag_sync, check_tag_sync


class TestCheckTagSync(unittest.TestCase):
    def test_no_mismatch_when_frontmatter_already_matches_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: [economics, mobile-money]\n---\n\nBody text.", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["economics", "mobile-money"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["mismatch"])
            self.assertTrue(result["found_card"])

    def test_mismatch_when_frontmatter_out_of_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: []\n---\n\nBody text.", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["real-tag"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertTrue(result["mismatch"])
            self.assertEqual(result["index_tags"], ["real-tag"])

    def test_no_card_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: []\n---\n\nBody text.", encoding="utf-8")

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["found_card"])
            self.assertFalse(result["mismatch"])

    def test_no_frontmatter_tags_line_skips_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("no frontmatter at all here", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["real-tag"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["mismatch"])


class TestApplyTagSync(unittest.TestCase):
    def test_rewrites_frontmatter_tags_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            md_path.write_text("---\nsource_pdf: a.pdf\ntags: []\n---\n\nBody text.", encoding="utf-8")
            apply_tag_sync(md_path, ["economics", "mobile-money"])
            content = md_path.read_text(encoding="utf-8")
            self.assertIn("tags: [economics, mobile-money]", content)
            self.assertIn("Body text.", content)
            self.assertIn("source_pdf: a.pdf", content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_metadata.py -v -k "CheckTagSync or ApplyTagSync"`
Expected: FAIL with `ImportError: cannot import name 'check_tag_sync'`

- [ ] **Step 3: Implement `check_tag_sync()` and `apply_tag_sync()`**

Add to `audit_metadata.py`. Add to the imports:

```python
import re

from indexer.index_card import find_card_by_file_id
```

Then, near the top-level constants (mirrors `indexer/retag.py`'s own `_FRONTMATTER_RE`/`_TAGS_LINE_RE` exactly — a deliberate small duplication rather than importing private names from `retag.py`, matching the pattern this module already follows in `reconcile_needs_manual.py`):

```python
_FRONTMATTER_RE = re.compile(r"\A(---\n.*?\n---\n)", re.DOTALL)
_TAGS_LINE_RE = re.compile(r"(?m)^tags:.*$")
```

Then the two functions:

```python
def _current_frontmatter_tags(content: str) -> list[str] | None:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None
    tags_match = _TAGS_LINE_RE.search(match.group(1))
    if not tags_match:
        return None
    bracket_match = re.search(r"\[(.*)\]", tags_match.group(0))
    if not bracket_match:
        return []
    inner = bracket_match.group(1).strip()
    if not inner:
        return []
    return [t.strip() for t in inner.split(",")]


def check_tag_sync(index_root, pdf_path: Path, md_path: Path) -> dict:
    file_id = compute_file_id(str(pdf_path))
    found = find_card_by_file_id(index_root, file_id)
    if found is None:
        return {"mismatch": False, "index_tags": None, "found_card": False}
    _, card = found
    index_tags = card.get("tags") or []

    content = md_path.read_text(encoding="utf-8")
    current_tags = _current_frontmatter_tags(content)
    if current_tags is None:
        return {"mismatch": False, "index_tags": index_tags, "found_card": True}

    return {"mismatch": sorted(current_tags) != sorted(index_tags), "index_tags": index_tags, "found_card": True}


def apply_tag_sync(md_path: Path, tags: list[str]) -> None:
    content = md_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return
    rendered = "[" + ", ".join(tags) + "]"
    new_frontmatter = _TAGS_LINE_RE.sub(f"tags: {rendered}", match.group(1), count=1)
    md_path.write_text(new_frontmatter + content[match.end():], encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: PASS (all tests so far)

- [ ] **Step 5: Commit**

```bash
git add audit_metadata.py tests/test_audit_metadata.py
git commit -m "feat(journal_discovery): add audit_metadata tag-frontmatter sync check and correction

Auto-corrects (the index card is the source of truth -- retag.py writes
both, this just closes a sync gap, never invents a new tag)."
```

---

## Task 7: `write_metadata_audit_flags_worklist()`

**Files:**
- Modify: `journal_discovery/worklist.py`
- Test: `tests/test_worklist.py` (extend)

**Interfaces:**
- Consumes: `_link_for()`, `_read_checked_links()` (both existing, already generic).
- Produces: `write_metadata_audit_flags_worklist(manifest: dict, articles_dir) -> Path`. Used by `audit()` in Task 8.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_worklist.py` (add `write_metadata_audit_flags_worklist` to the existing import line):

```python
class TestWriteMetadataAuditFlagsWorklist(unittest.TestCase):
    def test_only_entries_with_flags_appear(self):
        manifest = {
            "10.1/flagged": {
                "status": "fetched", "title": "Flagged Paper", "doi_url": "https://doi.org/10.1/flagged",
                "audit_flags": [{"type": "title_mismatch", "detail": "stored title not found in text"}],
            },
            "10.1/clean": {"status": "fetched", "title": "Clean Paper", "audited_at": "2026-09-03T00:00:00+00:00"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_metadata_audit_flags_worklist(manifest, tmp)
            self.assertEqual(path, Path(tmp) / "metadata_audit_flags.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("Flagged Paper", content)
            self.assertNotIn("Clean Paper", content)

    def test_shows_flag_detail(self):
        manifest = {
            "10.1/flagged": {
                "status": "fetched", "title": "Flagged Paper", "doi_url": "https://doi.org/10.1/flagged",
                "audit_flags": [{"type": "author_mismatch", "detail": "none of ['A. Nobody'] found in text"}],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_metadata_audit_flags_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("author_mismatch", content)
            self.assertIn("none of ['A. Nobody'] found in text", content)

    def test_preserves_checked_state_across_regeneration(self):
        manifest = {
            "10.1/flagged": {
                "status": "fetched", "title": "Flagged Paper", "doi_url": "https://doi.org/10.1/flagged",
                "audit_flags": [{"type": "doi_mismatch", "detail": "..."}],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_metadata_audit_flags_worklist(manifest, tmp)
            path.write_text(
                path.read_text(encoding="utf-8").replace("- [ ] [Flagged Paper]", "- [x] [Flagged Paper]"),
                encoding="utf-8",
            )
            write_metadata_audit_flags_worklist(manifest, tmp)
            self.assertIn("- [x] [Flagged Paper]", path.read_text(encoding="utf-8"))

    def test_empty_manifest_still_writes_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_metadata_audit_flags_worklist({}, tmp)
            self.assertTrue(path.exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_worklist.py -v -k MetadataAuditFlags`
Expected: FAIL with `ImportError: cannot import name 'write_metadata_audit_flags_worklist'`

- [ ] **Step 3: Implement `write_metadata_audit_flags_worklist()`**

Add to `journal_discovery/worklist.py`, after `write_snowball_candidates_worklist()`. This one doesn't go through `_write_checkbox_worklist()` (that helper filters by `status`, but a flagged paper keeps its original `status` — the trigger here is a non-empty `audit_flags` list instead):

```python
def write_metadata_audit_flags_worklist(manifest: dict, articles_dir) -> Path:
    entries = [(key, entry) for key, entry in manifest.items() if entry.get("audit_flags")]
    entries.sort(key=lambda kv: kv[1].get("title") or kv[0])

    path = Path(articles_dir) / "metadata_audit_flags.md"
    previously_checked = _read_checked_links(path)

    lines = [
        "# Papers flagged by the metadata/folder audit",
        "",
        "audit_metadata.py found a mismatch it can't safely auto-correct --",
        "each needs a human look. Resolve by hand (fix the sidecar, re-file,",
        "whatever's right), then run `python -m audit_metadata --recheck-all`",
        "to clear the flag once it no longer reproduces. Checking a box here",
        "only tracks your own review progress; it does not clear the flag.",
        "",
    ]
    for key, entry in entries:
        title = entry.get("title") or key
        link = _link_for(key, entry)
        checkbox = "x" if link in previously_checked else " "
        lines.append(f"- [{checkbox}] [{title}]({link})")
        for flag in entry["audit_flags"]:
            lines.append(f"  - **{flag['type']}**: {flag['detail']}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_worklist.py -v`
Expected: PASS (all tests, including every pre-existing one)

- [ ] **Step 5: Commit**

```bash
git add journal_discovery/worklist.py tests/test_worklist.py
git commit -m "feat(journal_discovery): add write_metadata_audit_flags_worklist()"
```

---

## Task 8: `audit_metadata.py` — orchestrator and CLI

**Files:**
- Modify: `audit_metadata.py`
- Test: `tests/test_audit_metadata.py` (extend)

**Interfaces:**
- Consumes: every function from Tasks 3-7 (`select_audit_targets`, `resolve_paper_paths`, `check_title`, `check_authors`, `check_doi`, `check_folder`, `apply_folder_correction`, `check_tag_sync`, `apply_tag_sync`), plus `journal_discovery.manifest.{manifest_path, load_manifest, save_manifest}` (existing) and `journal_discovery.worklist.write_metadata_audit_flags_worklist` (Task 7).
- Produces: `audit(articles_dir, index_root, mailto, recheck_all=False) -> dict` (counts: `audited`, `folder_corrections`, `tag_syncs`, `flagged`, `skipped`) — this is what `reconcile_needs_manual.py`'s `main()` calls in Task 9. Also `main()`, the standalone CLI entry point.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_audit_metadata.py`:

```python
from unittest.mock import patch

from journal_discovery.manifest import load_manifest, manifest_path, record_outcome, save_manifest
from audit_metadata import audit


def _write_pdf_and_md(folder: Path, stem: str, md_text: str) -> tuple[Path, Path]:
    pdf_path = folder / f"{stem}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    md_path = folder / "processed_outputs" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_text, encoding="utf-8")
    return pdf_path, md_path


class TestAudit(unittest.TestCase):
    @patch("audit_metadata.resolve_work_by_doi")
    def test_clean_paper_gets_audited_with_no_flags(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(
                tmp / "business", stem,
                "---\ntags: []\n---\n\nA Real Paper. DOI: 10.1/abc. By Jane Doe.",
            )
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "A Real Paper", "authors": ["Jane Doe"]})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Real Paper", authors=[], year=2024, abstract=None,
                                              concepts=["Business"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["audited"], 1)
            self.assertEqual(result["flagged"], 0)
            updated = load_manifest(manifest_file)
            self.assertIn("audited_at", updated["10.1/abc"])
            self.assertNotIn("audit_flags", updated["10.1/abc"])

    @patch("audit_metadata.resolve_work_by_doi")
    def test_title_mismatch_gets_flagged_and_written_to_worklist(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(
                tmp / "business", stem,
                "---\ntags: []\n---\n\nCompletely different content. DOI: 10.1/abc.",
            )
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "A Title Never Printed", "doi_url": "https://doi.org/10.1/abc"})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Title Never Printed", authors=[], year=2024,
                                              abstract=None, concepts=["Business"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["flagged"], 1)
            updated = load_manifest(manifest_file)
            self.assertEqual(updated["10.1/abc"]["audit_flags"][0]["type"], "title_mismatch")
            worklist = (tmp / "metadata_audit_flags.md").read_text(encoding="utf-8")
            self.assertIn("A Title Never Printed", worklist)

    def test_already_audited_paper_skipped_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "X", "audited_at": "2026-09-01T00:00:00+00:00"})
            save_manifest(manifest_file, manifest)

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)
            self.assertEqual(result["audited"], 0)

    @patch("audit_metadata.resolve_work_by_doi")
    def test_folder_mismatch_moves_files_and_counts_correction(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(tmp / "grasp", stem, "---\ntags: []\n---\n\nA Real Paper. DOI: 10.1/abc.")
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="grasp", metadata={"title": "A Real Paper"})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Real Paper", authors=[], year=2024, abstract=None,
                                              concepts=["Sociology"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["folder_corrections"], 1)
            self.assertTrue((tmp / "sociology" / f"{stem}.pdf").exists())
            updated = load_manifest(manifest_file)
            self.assertEqual(updated["10.1/abc"]["folder"], "sociology")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_audit_metadata.py -v -k TestAudit`
Expected: FAIL with `ImportError: cannot import name 'audit'`

- [ ] **Step 3: Implement `audit()` and `main()`**

Add to `audit_metadata.py`. Add to the imports:

```python
import argparse
import os
from datetime import datetime, timezone

from journal_discovery.manifest import load_manifest, manifest_path, save_manifest
from journal_discovery.worklist import write_metadata_audit_flags_worklist
```

Then:

```python
def audit(articles_dir, index_root, mailto: str, recheck_all: bool = False) -> dict:
    manifest_file = manifest_path(articles_dir)
    manifest = load_manifest(manifest_file)
    targets = select_audit_targets(manifest, recheck_all)

    counts = {"audited": 0, "folder_corrections": 0, "tag_syncs": 0, "flagged": 0, "skipped": 0}

    for key, entry in targets:
        pdf_path, md_path = resolve_paper_paths(articles_dir, key, entry)
        label = entry.get("title") or key
        if pdf_path is None or md_path is None or not md_path.exists():
            print(f"  [skip] {label}: converted .md not found")
            counts["skipped"] += 1
            continue

        try:
            folder_result = check_folder(key, entry, mailto)
            if folder_result["error"]:
                print(f"  [warn] {label}: folder check skipped ({folder_result['error']})")
            elif folder_result["mismatch"]:
                old_folder = entry.get("folder")
                pdf_path, md_path = apply_folder_correction(
                    articles_dir, index_root, entry, pdf_path, md_path, folder_result["new_folder"],
                )
                print(f"  [folder] {label}: {old_folder} -> {folder_result['new_folder']}")
                counts["folder_corrections"] += 1
        except Exception as exc:
            # Broad on purpose: a failure anywhere in apply_folder_correction
            # (a file-move permission error, or move_card() failing after
            # files already moved) must never crash the whole run or leave
            # audited_at set on a half-migrated paper -- it just gets
            # retried on the next run, whatever the exact exception type.
            print(f"  [error] {label}: folder correction failed ({exc}); will retry next run")
            counts["skipped"] += 1
            continue

        tag_result = check_tag_sync(index_root, pdf_path, md_path)
        if not tag_result["found_card"]:
            print(f"  [warn] {label}: no index card found, tag-sync check skipped")
        elif tag_result["mismatch"]:
            apply_tag_sync(md_path, tag_result["index_tags"])
            print(f"  [tags] {label}: synced to {tag_result['index_tags']}")
            counts["tag_syncs"] += 1

        text = md_path.read_text(encoding="utf-8", errors="ignore")
        flags = [f for f in (check_title(entry, text), check_authors(entry, text), check_doi(key, entry, text)) if f]

        entry["audited_at"] = datetime.now(timezone.utc).isoformat()
        if flags:
            entry["audit_flags"] = flags
            counts["flagged"] += 1
            print(f"  [flag] {label}: {', '.join(f['type'] for f in flags)}")
        elif "audit_flags" in entry:
            del entry["audit_flags"]
        counts["audited"] += 1

    save_manifest(manifest_file, manifest)
    write_metadata_audit_flags_worklist(manifest, articles_dir)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    default_index_root = Path(__file__).resolve().parent.parent / "research"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    parser.add_argument("--index-root", default=str(default_index_root))
    parser.add_argument("--recheck-all", action="store_true")
    args = parser.parse_args()

    mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex).")
        return

    result = audit(args.articles_dir, args.index_root, mailto, recheck_all=args.recheck_all)
    print(f"\nAudited {result['audited']} paper(s): "
          f"{result['folder_corrections']} folder correction(s), "
          f"{result['tag_syncs']} tag sync(s), {result['flagged']} flagged, "
          f"{result['skipped']} skipped.")
```

Remove the placeholder `if __name__ == "__main__": pass` from Task 3 and replace it with:

```python
if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_audit_metadata.py -v`
Expected: PASS (every test in the file, all tasks so far)

- [ ] **Step 5: Commit**

```bash
git add audit_metadata.py tests/test_audit_metadata.py
git commit -m "feat(journal_discovery): wire audit_metadata's checks into audit() orchestrator + CLI

python -m audit_metadata --recheck-all is now a complete, standalone
forced-re-audit command. Chaining it onto reconcile_needs_manual.py's
own run is Task 9."
```

---

## Task 9: Chain `audit_metadata.audit()` onto `reconcile_needs_manual.py`

**Files:**
- Modify: `reconcile_needs_manual.py`
- Test: `tests/test_reconcile_needs_manual.py` (extend)

**Interfaces:**
- Consumes: `audit_metadata.audit()` (Task 8).
- Produces: `reconcile_needs_manual.main()` now runs the audit automatically after reconciling. `reconcile()` itself is untouched.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_reconcile_needs_manual.py` (add `import subprocess, sys, os` and `from unittest.mock import patch` to the top):

```python
import os
import subprocess
import sys
from unittest.mock import patch


class TestMainChainsAudit(unittest.TestCase):
    def test_main_calls_audit_when_mailto_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["reconcile_needs_manual", "--articles-dir", tmp,
                                             "--index-root", tmp]), \
                 patch.dict(os.environ, {"OPENALEX_CONTACT_EMAIL": "me@example.com"}), \
                 patch("reconcile_needs_manual.audit_metadata.audit") as mock_audit:
                mock_audit.return_value = {
                    "audited": 0, "folder_corrections": 0, "tag_syncs": 0, "flagged": 0, "skipped": 0,
                }
                import reconcile_needs_manual
                reconcile_needs_manual.main()
                mock_audit.assert_called_once_with(tmp, tmp, "me@example.com", recheck_all=False)

    def test_main_skips_audit_and_still_succeeds_without_mailto(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_without_mailto = {k: v for k, v in os.environ.items() if k != "OPENALEX_CONTACT_EMAIL"}
            with patch.object(sys, "argv", ["reconcile_needs_manual", "--articles-dir", tmp]), \
                 patch.dict(os.environ, env_without_mailto, clear=True), \
                 patch("reconcile_needs_manual.audit_metadata.audit") as mock_audit:
                import reconcile_needs_manual
                reconcile_needs_manual.main()
                mock_audit.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reconcile_needs_manual.py -v -k MainChainsAudit`
Expected: FAIL — `AttributeError: module 'reconcile_needs_manual' has no attribute 'audit_metadata'` (or the mock never gets called, since `main()` doesn't call `audit()` yet)

- [ ] **Step 3: Update `reconcile_needs_manual.py`**

Two changes:

1. Remove the "Folder/content review" print loop (the last block of the current `main()`, lines 111-115: `print("\nFolder/content review...")` through the `for md_path in find_converted_md_files(args.articles_dir): ...` loop) and its mention in the module docstring ("Also prints a folder/content review so folder-appropriateness can be checked against what a paper actually says, not just its OpenAlex concept tags.").

2. Replace `main()` with:

```python
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    default_index_root = Path(__file__).resolve().parent.parent / "research"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    parser.add_argument("--index-root", default=str(default_index_root))
    args = parser.parse_args()

    result = reconcile(args.articles_dir)

    print(f"Scanned {result['md_files_scanned']} converted .md file(s).\n")
    print(f"Confirmed downloaded ({len(result['confirmed'])}):")
    for key, title, md_path in result["confirmed"]:
        print(f"  - {title or key} -> {md_path}")
    print(f"\nStill needs manual download ({len(result['still_pending'])}):")
    for key, title in result["still_pending"]:
        print(f"  - {title or key}")

    mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("\nAudit step skipped: set OPENALEX_CONTACT_EMAIL to enable it.")
        return

    audit_result = audit_metadata.audit(args.articles_dir, args.index_root, mailto, recheck_all=False)
    print(f"\nAudited {audit_result['audited']} paper(s): "
          f"{audit_result['folder_corrections']} folder correction(s), "
          f"{audit_result['tag_syncs']} tag sync(s), {audit_result['flagged']} flagged, "
          f"{audit_result['skipped']} skipped.")
```

Add `import os` and `import audit_metadata` to the top of `reconcile_needs_manual.py` (`audit_metadata` imported as a module, not `from audit_metadata import audit`, so `patch("reconcile_needs_manual.audit_metadata.audit")` in the test above resolves correctly).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reconcile_needs_manual.py -v`
Expected: PASS (both new tests, and every pre-existing test in the file — `reconcile()` itself is unchanged, so `TestReconcile`'s tests are unaffected; confirm `TestFindConvertedMdFiles`/`TestIsConfirmedDownloaded`/`TestExtractPreview` still pass too, since none of those functions were touched)

Also run the full existing suite once to confirm nothing else broke:

Run: `python -m pytest tests/ -v`
Expected: PASS (all tests across the whole `academic-rag-model` project)

- [ ] **Step 5: Commit**

```bash
git add reconcile_needs_manual.py tests/test_reconcile_needs_manual.py
git commit -m "feat(journal_discovery): chain audit_metadata.audit() onto reconcile_needs_manual.py

reconcile is the one point where every paper's manifest status and
on-disk path are guaranteed resolvable together (a manually-downloaded
paper only flips to downloaded, with matched_md_path recorded, once
reconcile's own content-matching runs) -- so this is where the audit
runs automatically now, not as a separate command to remember.
Also retires the read-only folder/content preview loop this supersedes.

Missing OPENALEX_CONTACT_EMAIL degrades gracefully (warns, skips just
the audit step) rather than breaking a command that never needed it
before."
```

---

## Task 10: Update `journal_discovery_instructions.md` and `journal_articles_instructions.md`

**Files:**
- Modify: `journal_discovery_instructions.md`
- Modify: `journal_articles_instructions.md` (only if it references the retired preview loop — check first)

**Interfaces:** None (documentation only).

- [ ] **Step 1: Update `journal_discovery_instructions.md`'s "Step 3: Reconcile manual downloads" section**

Replace this paragraph (currently the last paragraph of Step 3, right after the code block for `python -m reconcile_needs_manual`):

```
A manually-downloaded PDF's filename is arbitrary -- it never matches
anything this pipeline would have generated -- so this matches by real
content instead: a DOI substring match against the converted `.md`
first, a normalized-title match as fallback. Confirmed papers are
marked `status="downloaded"` in the manifest and drop out of
`needs_manual_downloads.md` automatically, so the list always reflects
what you actually still need. It also prints a folder/content review
(folder name next to a real content preview for every converted paper)
so you can sanity-check folder-appropriateness against what a paper is
actually about, not just its OpenAlex concept tags.
```

with:

```
A manually-downloaded PDF's filename is arbitrary -- it never matches
anything this pipeline would have generated -- so this matches by real
content instead: a DOI substring match against the converted `.md`
first, a normalized-title match as fallback. Confirmed papers are
marked `status="downloaded"` in the manifest and drop out of
`needs_manual_downloads.md` automatically, so the list always reflects
what you actually still need.

Right after reconciling, this also runs a metadata/folder audit
automatically (`audit_metadata.py`, requires `OPENALEX_CONTACT_EMAIL` --
skipped with a warning if that's not set) -- re-checking every newly
converted paper's folder placement and tag sync against fresh OpenAlex
data and the academic-hub index (both auto-corrected when there's a
well-defined right answer), and flagging title/author/DOI mismatches it
can't safely auto-fix into `metadata_audit_flags.md`. Already-audited
papers are skipped on later runs. For a full forced re-audit (e.g.
after fixing a flagged paper by hand):

```powershell
python -m audit_metadata --recheck-all
```
```

- [ ] **Step 2: Check `journal_articles_instructions.md` for any reference to the retired preview loop**

Run: `grep -n "folder.content review\|Folder/content" journal_articles_instructions.md`
Expected: no matches (this doc documents `convert_journal_articles.py`, not `reconcile_needs_manual.py` — the preview loop was never described there). If a match is found, remove that reference the same way as Step 1.

- [ ] **Step 3: Read both files back to confirm they render sensibly**

No automated test for documentation — read the edited section of `journal_discovery_instructions.md` back with the `Read` tool and confirm the Markdown renders as intended (code fences balanced, no leftover references to the removed preview loop).

- [ ] **Step 4: Commit**

```bash
git add journal_discovery_instructions.md journal_articles_instructions.md
git commit -m "docs(journal_discovery): document the automatic metadata/folder audit step"
```

---

## Final check

- [ ] Run the full test suite once more from the `academic-rag-model` root: `python -m pytest tests/ -v`. Expected: every test passes, including the pre-existing suite (616+ tests before this plan) plus all new tests added across Tasks 1-9.
- [ ] Confirm `git log --oneline -10` shows one commit per task, in order.
