# Cross-Offering Content Linkage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find and surface likely corollaries between a course's marked prior offerings (e.g. `class_2024`) and its other content -- a reused slide deck, a problem set covering the same material a different year -- using each card's existing embedding, writing the result into both the index and each matched note's own Obsidian-visible `.md` file.

**Architecture:** A new standalone module, `core/indexer/offering_links.py`, with its own CLI, mirroring `retag.py`'s (threshold-based pairwise comparison over existing card embeddings) and `duplicate_check.py`'s (confidence-tiered, dismissals-ledger) patterns. One supporting piece of shared infrastructure moves first: `.notes_subset.json` marker-reading is promoted from `route_notes_transcribe.py` into `core/env/academic_hub_paths.py` (needed there to avoid a circular import once `transcribe_notes.py` also needs it), alongside a new `find_containing_offering_label()`.

**Tech Stack:** Python 3.13, stdlib only for the new plumbing (`os`, `json`, `re`) -- no new dependencies. Reuses `numpy`-backed `cosine_similarity()` and `gemini-embedding-001` embeddings already present on every card.

**Spec:** `ai-sandbox/academic-rag-model/docs/superpowers/specs/indexer/2026-10-03-cross-offering-linkage-design.md`

## Global Constraints

- No new embedding or LLM calls anywhere in this feature -- every comparison reuses a card's existing `embedding` field.
- `core/env/academic_hub_paths.py` stays importable at module scope with no side effects (unchanged from today); the functions it gains do file I/O only when called, never at import time.
- Every existing test in `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py` and `tests/core/indexer/test_index_card.py` must still pass unchanged after Tasks 1-2 -- both are pure refactors/additive fields, not behavior changes.
- New `.index/offering_links/{review,dismissals}.json` ledgers live one level down inside `.index/`, not as direct children of it -- `list_courses()` treats every direct-child `*.json` (other than `courses.json`/`tags.json`) as a course shard, same reasoning `duplicate_check.py`'s own `.index/duplicates/` already documents.
- A malformed ledger file (hand-edited, truncated) is treated as empty with a warning, never a hard failure.

## Review Focus

- A card with no embedding (a `needs_indexing` failure card) crashes the comparison instead of being cleanly excluded.
- Two cards in the *same* offering (both primary, or both in `class_2024`) get compared and linked against each other -- this tool's whole point is cross-offering only.
- A match already recorded in `dismissals.json` gets re-surfaced into `review.json` or auto-written on every rerun instead of staying suppressed.
- Rerunning the tool after a match already exists duplicates the `## Related notes` block or the `related_offerings` entry instead of replacing it in place.
- A card's `.md` file is missing or unreadable on disk and the whole run aborts, instead of skipping just that card's markdown-side write (index-side write must still succeed independently, same failure-isolation rule the rest of this indexer already follows).

---

### Task 1: Promote marker-reading into `academic_hub_paths.py`, add `find_containing_offering_label`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/core/env/academic_hub_paths.py`
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/env/test_academic_hub_paths.py`

**Interfaces:**
- Consumes: nothing new (stdlib `os`, `json`).
- Produces: `read_subset_marker(dir_path: str) -> dict | None` and `find_containing_offering_label(path: str) -> str | None`, both in `core/env/academic_hub_paths.py`, used by Task 2 and Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/env/test_academic_hub_paths.py`:

```python
import json

from core.env.academic_hub_paths import (
    find_containing_offering_label,
    read_subset_marker,
    resolve_output_dir,
    textbook_rag_md_path,
    to_notes_root,
    to_resources_root,
)


def test_read_subset_marker_returns_parsed_dict(tmp_path):
    (tmp_path / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    assert read_subset_marker(str(tmp_path)) == {"label": "2024"}


def test_read_subset_marker_returns_none_when_missing(tmp_path):
    assert read_subset_marker(str(tmp_path)) is None


def test_read_subset_marker_warns_and_ignores_malformed_json(tmp_path, capsys):
    (tmp_path / ".notes_subset.json").write_text("{not valid json")
    assert read_subset_marker(str(tmp_path)) is None
    assert "WARNING" in capsys.readouterr().out


def test_find_containing_offering_label_returns_none_for_a_notes_rooted_path():
    path = os.path.join("academic_notes", "econometrics", "ta_notes", "foo.pdf")
    assert find_containing_offering_label(path) is None


def test_find_containing_offering_label_finds_a_marker_on_the_course_dir_itself(tmp_path):
    course_dir = tmp_path / "academic_resources" / "econometrics"
    course_dir.mkdir(parents=True)
    (course_dir / ".notes_subset.json").write_text(json.dumps({"label": "whole-course"}))
    pdf_path = course_dir / "class_2024" / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "whole-course"


def test_find_containing_offering_label_finds_a_marker_several_levels_up(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    pdf_path = deep / "090424.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "2024"


def test_find_containing_offering_label_returns_none_when_no_ancestor_is_marked(tmp_path):
    category_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    category_dir.mkdir(parents=True)
    pdf_path = category_dir / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) is None


def test_find_containing_offering_label_prefers_the_outermost_marker(tmp_path):
    # Mirrors find_subset_roots()'s own "one marker claims its whole
    # subtree, no stacking" rule -- the outer marker is the one that
    # actually governs this file, since find_subset_roots() would never
    # have looked for the inner one.
    outer = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    inner = outer / "Class Notes"
    inner.mkdir(parents=True)
    (outer / ".notes_subset.json").write_text(json.dumps({"label": "outer"}))
    (inner / ".notes_subset.json").write_text(json.dumps({"label": "inner"}))
    pdf_path = inner / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "outer"
```

Add `import os` at the top of that test file if not already present (it already is, per the existing `os.path.join` calls there).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/env/test_academic_hub_paths.py -k "subset_marker or offering_label" -v`
Expected: FAIL (`read_subset_marker`/`find_containing_offering_label` not defined)

- [ ] **Step 3: Implement**

In `core/env/academic_hub_paths.py`, change the import block:

```python
from __future__ import annotations

import json
import os
```

Add after `TEXTBOOK_FOLDER_NAMES`:

```python
_SUBSET_MARKER_FILENAME = ".notes_subset.json"
```

Add at the end of the file:

```python
def read_subset_marker(dir_path: str) -> dict | None:
    """Reads this directory's prior-offering subset marker, if any.
    Returns None for a missing file (not marked) or a malformed one
    (logged, treated as not marked) -- never raises, so one bad marker
    can't take down a caller scanning many directories."""
    marker_path = os.path.join(dir_path, _SUBSET_MARKER_FILENAME)
    if not os.path.isfile(marker_path):
        return None
    try:
        with open(marker_path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as err:
        print(f"WARNING: malformed subset marker, ignoring: {marker_path} ({err})")
        return None
    if not isinstance(data, dict):
        print(
            f"WARNING: malformed subset marker, ignoring: {marker_path} "
            f"(expected a JSON object, got {type(data).__name__})"
        )
        return None
    return data


def find_containing_offering_label(path: str) -> str | None:
    """The label of the subset marker governing `path`, or None if path
    isn't under academic_resources/ at all, or no ancestor up to its
    course directory carries a valid marker. Checks ancestors from the
    course directory downward to path's own parent (top-down,
    first-match-wins) -- the same order find_subset_roots() walks in
    (route_notes_transcribe.py), so this always agrees with which
    directory that function would have returned as the subset root
    governing this exact file."""
    had_backslashes = "\\" in path
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    try:
        idx = parts.index(_RESOURCES_ROOT_NAME)
    except ValueError:
        return None
    course_depth = idx + 2
    if len(parts) <= course_depth:
        return None
    for depth in range(course_depth, len(parts)):
        candidate = "/".join(parts[:depth])
        if had_backslashes:
            candidate = candidate.replace("/", os.sep)
        marker = read_subset_marker(candidate)
        if marker is not None:
            label = marker.get("label")
            return str(label) if label is not None else None
    return None
```

Now update `route_notes_transcribe.py` to use the promoted names instead of its own copies. Change the import line:

```python
from core.env.academic_hub_paths import (
    TEXTBOOK_FOLDER_NAMES,
    read_subset_marker,
    resolve_output_dir,
    to_resources_root,
)
```

Remove `import json` (no longer used in this file), remove the `_SUBSET_MARKER_FILENAME = ".notes_subset.json"` line, and remove the whole `_read_subset_marker()` function definition. In `find_subset_roots()`, change:

```python
        if _read_subset_marker(dirpath) is not None:
```

to:

```python
        if read_subset_marker(dirpath) is not None:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/env/test_academic_hub_paths.py -v`
Expected: all PASS, including the 7 new tests

- [ ] **Step 5: Run the full regression suite for the refactored module**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: all PASS unchanged (pure refactor -- `find_subset_roots()`'s observable behavior is identical)

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/env/academic_hub_paths.py ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py ai-sandbox/academic-rag-model/tests/core/env/test_academic_hub_paths.py
git commit -m "refactor(indexer): promote subset-marker reading into academic_hub_paths, add find_containing_offering_label"
```

---

### Task 2: `offering_label` on index cards

**Files:**
- Modify: `ai-sandbox/academic-rag-model/core/indexer/index_card.py`
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_notes.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/indexer/test_index_card.py`

**Interfaces:**
- Consumes: `find_containing_offering_label(path: str) -> str | None` (Task 1).
- Produces: `generate_index_card()`, `make_failure_card()`, `reconcile_and_write()` each gain `offering_label: str | None = None`; every card dict gains an `"offering_label"` key. `link_duplicate_note()` and `process_pdf()` in `transcribe_notes.py` compute and forward it. Used by Task 3's `derive_offering_for_card()` only indirectly (that function re-derives from `path`, not from this stored field -- see spec) but this is what makes the field available to other consumers (RAG agent, `problem_gen`, `audio_generator`) without filesystem access.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/indexer/test_index_card.py`, inside `TestGenerateIndexCard`:

```python
    def test_offering_label_defaults_to_none(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertIsNone(card["offering_label"])

    def test_offering_label_is_stored_when_given(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
            offering_label="2024",
        )
        self.assertEqual(card["offering_label"], "2024")
```

Add a new test method to the `TestReconcileAndWrite`-equivalent class (the one using `_card_kwargs`, around line 452):

```python
    def test_offering_label_is_stored_on_a_new_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = reconcile_and_write(tmp, **self._card_kwargs(offering_label="2024"))
            self.assertEqual(card["offering_label"], "2024")
            self.assertEqual(load_shard(tmp, "math-camp")[0]["offering_label"], "2024")

    def test_offering_label_updates_on_reconciliation_like_course_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client, offering_label="2023"))
            reconcile_and_write(tmp, **self._card_kwargs(
                client=client, path="moved/a.md", source_pdf_path="moved/a.pdf", offering_label="2024",
            ))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            self.assertEqual(load_shard(tmp, "math-camp")[0]["offering_label"], "2024")
```

Also add a test to `make_failure_card`'s existing test class (find it by searching `class TestMakeFailureCard` in the same file) following the same pattern:

```python
    def test_offering_label_is_stored_on_a_failure_card(self):
        card = make_failure_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", offering_label="2024",
        )
        self.assertEqual(card["offering_label"], "2024")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_index_card.py -k offering_label -v`
Expected: FAIL (`generate_index_card()`/`make_failure_card()`/`reconcile_and_write()` reject the unexpected `offering_label` keyword, or the returned dict has no such key)

- [ ] **Step 3: Implement**

In `core/indexer/index_card.py`:

`generate_index_card()` -- add the parameter and the returned field:

```python
def generate_index_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str, page_count: int, client, content_hash: str | None = None,
    known_doc_types: frozenset[str] = KNOWN_DOC_TYPES, source_asset_path: str | None = None,
    offering_label: str | None = None,
) -> dict:
```

and in the returned dict, add:

```python
        "offering_label": offering_label,
```

`make_failure_card()`:

```python
def make_failure_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_hash: str | None = None, source_asset_path: str | None = None,
    offering_label: str | None = None,
) -> dict:
```

and in its returned dict:

```python
        "offering_label": offering_label,
```

`reconcile_and_write()`:

```python
def reconcile_and_write(
    academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str,
    folder_category: str, content_sample: str, page_count: int, client,
    content_hash: str | None = None, known_doc_types: frozenset[str] = KNOWN_DOC_TYPES,
    source_asset_path: str | None = None, offering_label: str | None = None,
) -> dict:
```

In the `found is not None` branch, alongside the existing `updated["course"] = course` line, add:

```python
        updated["offering_label"] = offering_label
```

In the "genuinely new content" branch, forward it to both calls:

```python
        card = generate_index_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path, course=course,
            folder_category=folder_category, content_sample=content_sample,
            page_count=page_count, client=client, content_hash=content_hash,
            known_doc_types=known_doc_types, source_asset_path=source_asset_path,
            offering_label=offering_label,
        )
    except Exception as err:
        print(f"WARNING: index card generation failed for {path} ({err}); writing needs_indexing card.")
        card = make_failure_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path,
            course=course, folder_category=folder_category, content_hash=content_hash,
            source_asset_path=source_asset_path, offering_label=offering_label,
        )
```

In `pipelines/transcribe_notes/transcribe_notes.py`, add the import:

```python
from core.env.academic_hub_paths import find_containing_offering_label, resolve_output_dir, to_resources_root
```

(adjust the existing import line for `resolve_output_dir`/`to_resources_root` if they're already imported separately -- merge into one `from core.env.academic_hub_paths import (...)` block.)

Update `_write_markdown_and_index()`:

```python
def _write_markdown_and_index(md_path, frontmatter, final_md, pdf_path, academic_hub_root,
                               folder_category, total_pages, client, known_doc_types=KNOWN_DOC_TYPES,
                               offering_label=None):
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + final_md)

    try:
        file_id = compute_file_id(pdf_path)
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_pdf_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_pdf_path,
            course=course, folder_category=folder_category, content_sample=final_md,
            page_count=total_pages, client=client, content_hash=compute_content_hash(md_path),
            known_doc_types=known_doc_types, source_asset_path=rel_pdf_path,
            offering_label=offering_label,
        )
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {md_path} ({err}); "
              f"rerun `python index_search.py rebuild` later to catch it up.")
```

Update `link_duplicate_note()` to take and use its own offering (the new location's offering, never inherited from the canonical card):

```python
def link_duplicate_note(academic_hub_root: str, canonical_course: str, canonical_card: dict,
                         pdf_path: str, folder_category: str, offering_label: str | None = None) -> dict:
```

and, alongside the existing `new_card["source_asset_path"] = rel_pdf_path` line:

```python
    new_card["offering_label"] = offering_label
```

In `process_pdf()`, compute the label once near each existing `folder_category = derive_folder_category(pdf_path)` call and thread it through. The helper itself handles both path shapes (returns `None` immediately for a not-yet-migrated `academic_notes/`-side path), so no extra branching is needed at the call site:

```python
        folder_category = derive_folder_category(pdf_path)
        offering_label = find_containing_offering_label(pdf_path)
```

(this appears twice in `process_pdf()` -- once in the `find_existing_transcription` duplicate-link branch, once in the main new-content path; add the `offering_label = ...` line right after each existing `folder_category = derive_folder_category(pdf_path)` line). Update the duplicate-link call:

```python
        link_duplicate_note(academic_hub_root, canonical_course, canonical_card, pdf_path, folder_category, offering_label)
```

and all four `_write_markdown_and_index(...)` call sites in the main path, adding the new keyword:

```python
        _write_markdown_and_index(
            md_path, frontmatter, final_md, pdf_path, academic_hub_root,
            folder_category, total_pages, client, known_doc_types=known_doc_types,
            offering_label=offering_label,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_index_card.py -k offering_label -v`
Expected: all PASS

- [ ] **Step 5: Run the full regression suites**

Run: `python -m pytest tests/core/indexer/test_index_card.py tests/pipelines/transcribe_notes/test_transcribe_notes.py -v`
Expected: all PASS unchanged (every new parameter defaults to `None`, so every existing call site and every existing test keeps working)

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/index_card.py ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_notes.py ai-sandbox/academic-rag-model/tests/core/indexer/test_index_card.py
git commit -m "feat(indexer): add offering_label field to index cards, computed at indexing time"
```

---

### Task 3: Ledger primitives and offering derivation

**Files:**
- Create: `ai-sandbox/academic-rag-model/core/indexer/offering_links.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py`

**Interfaces:**
- Consumes: `find_containing_offering_label(path: str) -> str | None`, `to_resources_root(path: str) -> str` (Task 1); `now_iso() -> str` (already in `core/indexer/index_card.py`).
- Produces: `load_review`, `save_review`, `load_dismissals`, `save_dismissals`, `is_dismissed(dismissals, file_id_a, file_id_b) -> bool`, `record_dismissal(academic_hub_root, file_id_a, file_id_b) -> None`, `derive_offering_for_card(card: dict, academic_hub_root: str) -> str | None` -- all used by Task 4 and Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/core/indexer/test_offering_links.py`:

```python
import json
import os
import tempfile

from core.indexer.offering_links import (
    derive_offering_for_card,
    is_dismissed,
    load_dismissals,
    load_review,
    record_dismissal,
    save_dismissals,
    save_review,
)


def test_load_dismissals_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_dismissals(tmp) == []


def test_record_dismissal_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        dismissals = load_dismissals(tmp)
        assert is_dismissed(dismissals, "fid1", "fid2")
        assert is_dismissed(dismissals, "fid2", "fid1")  # order-independent


def test_record_dismissal_is_a_no_op_if_already_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        record_dismissal(tmp, "fid2", "fid1")  # same pair, swapped order
        assert len(load_dismissals(tmp)) == 1


def test_is_dismissed_false_for_an_unrecorded_pair():
    assert is_dismissed([], "fid1", "fid2") is False


def test_dismissals_file_lives_one_level_inside_index_not_as_a_direct_child():
    with tempfile.TemporaryDirectory() as tmp:
        record_dismissal(tmp, "fid1", "fid2")
        assert os.path.isfile(os.path.join(tmp, ".index", "offering_links", "dismissals.json"))
        assert not os.path.isfile(os.path.join(tmp, ".index", "offering_links.json"))


def test_review_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        save_review(tmp, [{"file_id_a": "a", "file_id_b": "b", "similarity": 0.85, "course": "econometrics"}])
        assert load_review(tmp) == [{"file_id_a": "a", "file_id_b": "b", "similarity": 0.85, "course": "econometrics"}]


def test_load_review_returns_empty_list_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        assert load_review(tmp) == []


def test_load_dismissals_warns_and_treats_malformed_file_as_empty(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, ".index", "offering_links", "dismissals.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w") as f:
            f.write("{not valid json")
        assert load_dismissals(tmp) == []
        assert "WARNING" in capsys.readouterr().out


def test_derive_offering_for_card_returns_none_for_a_primary_card():
    with tempfile.TemporaryDirectory() as tmp:
        notes_dir = os.path.join(tmp, "academic_notes", "econometrics", "ta_notes")
        os.makedirs(notes_dir)
        card = {"path": "academic_notes/econometrics/ta_notes/foo.md"}
        assert derive_offering_for_card(card, tmp) is None


def test_derive_offering_for_card_finds_the_label_from_a_marked_subset():
    with tempfile.TemporaryDirectory() as tmp:
        subset = os.path.join(tmp, "academic_resources", "econometrics", "class_2024")
        deep = os.path.join(subset, "Class Notes", "Hand-Written Notes")
        os.makedirs(deep)
        with open(os.path.join(subset, ".notes_subset.json"), "w") as f:
            json.dump({"label": "2024"}, f)
        card = {
            "path": "academic_notes/econometrics/class_2024/Class Notes/Hand-Written Notes/"
                    "processed_outputs/090424.md",
        }
        assert derive_offering_for_card(card, tmp) == "2024"


def test_derive_offering_for_card_works_without_a_stored_offering_label_field():
    # The real class_2024 cards from Phase 1's first run predate the
    # offering_label field entirely -- this must still work from path alone.
    with tempfile.TemporaryDirectory() as tmp:
        subset = os.path.join(tmp, "academic_resources", "econometrics", "class_2024")
        os.makedirs(subset)
        with open(os.path.join(subset, ".notes_subset.json"), "w") as f:
            json.dump({"label": "2024"}, f)
        card = {"path": "academic_notes/econometrics/class_2024/processed_outputs/2023exam1.md"}
        assert "offering_label" not in card
        assert derive_offering_for_card(card, tmp) == "2024"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -v`
Expected: FAIL (`core.indexer.offering_links` doesn't exist yet)

- [ ] **Step 3: Implement**

Create `core/indexer/offering_links.py`:

```python
"""
offering_links.py
Finds likely corollaries between a course's marked prior offerings (Phase 1's
.notes_subset.json subsets -- see pipelines/transcribe_notes/README.md) and
its other content -- a reused slide deck, a problem set covering the same
material a different year -- using each card's existing title+summary
embedding, the same cosine-similarity-against-a-threshold shape
core/indexer/retag.py already uses for tag clustering, and the same
confidence-tiered dismissals-ledger pattern core/indexer/duplicate_check.py
already uses for fuzzy textbook matches. Deliberately separate from
index_card.py/transcribe_notes.py -- this is a corpus-wide, course-at-a-time
pass on its own explicit schedule, never per-file.

Spec: docs/superpowers/specs/indexer/2026-10-03-cross-offering-linkage-design.md
"""
from __future__ import annotations

import json
import os

from core.env.academic_hub_paths import find_containing_offering_label, to_resources_root
from core.indexer.index_card import now_iso

OFFERING_LINK_AUTO_THRESHOLD = 0.90  # starting guess -- calibrate against real data (Task 4)
OFFERING_LINK_REVIEW_THRESHOLD = 0.80  # starting guess -- calibrate against real data (Task 4)


def _links_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "offering_links")


def _review_path(academic_hub_root: str) -> str:
    return os.path.join(_links_dir(academic_hub_root), "review.json")


def _dismissals_path(academic_hub_root: str) -> str:
    return os.path.join(_links_dir(academic_hub_root), "dismissals.json")


def _load_json_list(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"expected a list, got {type(data).__name__}")
        return data
    except (OSError, ValueError) as err:
        print(f"WARNING: could not load {path} ({err}); treating as empty.")
        return []


def _save_json_list(path: str, entries: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def load_review(academic_hub_root: str) -> list[dict]:
    return _load_json_list(_review_path(academic_hub_root))


def save_review(academic_hub_root: str, entries: list[dict]) -> None:
    _save_json_list(_review_path(academic_hub_root), entries)


def load_dismissals(academic_hub_root: str) -> list[dict]:
    return _load_json_list(_dismissals_path(academic_hub_root))


def save_dismissals(academic_hub_root: str, dismissals: list[dict]) -> None:
    _save_json_list(_dismissals_path(academic_hub_root), dismissals)


def is_dismissed(dismissals: list[dict], file_id_a: str, file_id_b: str) -> bool:
    """Tolerates a hand-edited entry that isn't a well-formed
    {"file_id_a","file_id_b"} dict -- it simply doesn't match anything,
    rather than raising (same degrade-don't-crash rule as duplicate_check.py's
    own is_dismissed, which this mirrors)."""
    pair = tuple(sorted([file_id_a, file_id_b]))
    for d in dismissals:
        if not isinstance(d, dict):
            continue
        if tuple(sorted([d.get("file_id_a"), d.get("file_id_b")])) == pair:
            return True
    return False


def record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    """No-op (does not duplicate) if this exact pair is already recorded --
    safe to call every time a user says 'no' without checking first."""
    dismissals = load_dismissals(academic_hub_root)
    if is_dismissed(dismissals, file_id_a, file_id_b):
        return
    a, b = sorted([file_id_a, file_id_b])
    dismissals.append({"file_id_a": a, "file_id_b": b, "dismissed_at": now_iso()})
    save_dismissals(academic_hub_root, dismissals)


def derive_offering_for_card(card: dict, academic_hub_root: str) -> str | None:
    """Re-derives this card's offering straight from its own path on
    disk, independent of whether the stored offering_label field is
    present -- what makes this correct for cards indexed before that
    field existed (e.g. the real class_2024 cards from Phase 1's first
    real run, which predate it entirely)."""
    abs_notes_path = os.path.join(academic_hub_root, card["path"])
    try:
        abs_resources_path = to_resources_root(abs_notes_path)
    except ValueError:
        return None
    return find_containing_offering_label(abs_resources_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/offering_links.py ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py
git commit -m "feat(indexer): add offering_links ledger primitives and offering derivation"
```

---

### Task 4: Cross-offering match comparison

**Files:**
- Modify: `ai-sandbox/academic-rag-model/core/indexer/offering_links.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py`

**Interfaces:**
- Consumes: `cosine_similarity(a, b) -> float` (already in `core/indexer/index_card.py`).
- Produces: `find_cross_offering_matches(cards_with_offerings, auto_threshold=OFFERING_LINK_AUTO_THRESHOLD, review_threshold=OFFERING_LINK_REVIEW_THRESHOLD) -> tuple[list[tuple[dict, dict, float]], list[tuple[dict, dict, float]]]`, used by Task 6.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/indexer/test_offering_links.py`:

```python
from core.indexer.offering_links import find_cross_offering_matches

# Unit vectors at chosen angles so cosine_similarity's dot product gives an
# exact, easy-to-reason-about similarity: a=[1,0] vs [cos(t), sin(t)] -> cos(t).
_A = [1.0, 0.0]
_HIGH = [0.95, 0.3122498999199199]   # cosine 0.95 vs _A -- above auto (0.90)
_MID = [0.85, 0.5266403851195171]    # cosine 0.85 vs _A -- in review band (0.80-0.90)
_LOW = [0.5, 0.8660254037844387]     # cosine 0.5 vs _A -- below review band


def _card(file_id, embedding, path="academic_notes/econometrics/x.md"):
    return {"file_id": file_id, "path": path, "embedding": embedding, "title": file_id}


def test_same_offering_pairs_are_never_compared():
    cards = [(_card("a", _A), "2024"), (_card("b", _HIGH), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert review == []


def test_cross_offering_high_similarity_is_an_auto_match():
    cards = [(_card("a", _A), None), (_card("b", _HIGH), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert len(auto) == 1
    assert review == []
    card_a, card_b, similarity = auto[0]
    assert {card_a["file_id"], card_b["file_id"]} == {"a", "b"}
    assert similarity > 0.90

def test_cross_offering_mid_similarity_is_a_review_match():
    cards = [(_card("a", _A), None), (_card("b", _MID), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert len(review) == 1


def test_cross_offering_low_similarity_is_ignored():
    cards = [(_card("a", _A), None), (_card("b", _LOW), "2024")]
    auto, review = find_cross_offering_matches(cards)
    assert auto == []
    assert review == []


def test_three_offerings_compares_every_cross_pair():
    # 2023 vs 2024 counts too, not just subset-vs-primary (brainstorming
    # decision: "every pair in the course").
    cards = [(_card("a", _A), "2023"), (_card("b", _HIGH), "2024"), (_card("c", _LOW), None)]
    auto, review = find_cross_offering_matches(cards)
    assert len(auto) == 1  # a-b only; a-c and b-c are both low similarity
    matched_ids = {auto[0][0]["file_id"], auto[0][1]["file_id"]}
    assert matched_ids == {"a", "b"}


def test_custom_thresholds_are_respected():
    cards = [(_card("a", _A), None), (_card("b", _MID), "2024")]
    auto, review = find_cross_offering_matches(cards, auto_threshold=0.80, review_threshold=0.70)
    assert len(auto) == 1  # 0.85 now clears the lowered auto bar
    assert review == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -k cross_offering -v`
Expected: FAIL (`find_cross_offering_matches` not defined)

- [ ] **Step 3: Implement**

Add to `core/indexer/offering_links.py` (add `cosine_similarity` to the existing `from core.indexer.index_card import now_iso` line, making it `from core.indexer.index_card import cosine_similarity, now_iso`):

```python
def find_cross_offering_matches(
    cards_with_offerings: list[tuple[dict, str | None]],
    auto_threshold: float = OFFERING_LINK_AUTO_THRESHOLD,
    review_threshold: float = OFFERING_LINK_REVIEW_THRESHOLD,
) -> tuple[list[tuple[dict, dict, float]], list[tuple[dict, dict, float]]]:
    """Pure function -- no file I/O. Compares every pair of cards whose
    offerings differ (two primary cards, both None, are therefore never
    compared here at all -- that's retag.py's subject-clustering job, not
    this one's). Returns (auto_matches, review_matches), each a list of
    (card_a, card_b, similarity) above its respective threshold."""
    auto_matches = []
    review_matches = []
    n = len(cards_with_offerings)
    for i in range(n):
        card_a, offering_a = cards_with_offerings[i]
        for j in range(i + 1, n):
            card_b, offering_b = cards_with_offerings[j]
            if offering_a == offering_b:
                continue
            similarity = cosine_similarity(card_a.get("embedding") or [], card_b.get("embedding") or [])
            if similarity >= auto_threshold:
                auto_matches.append((card_a, card_b, similarity))
            elif similarity >= review_threshold:
                review_matches.append((card_a, card_b, similarity))
    return auto_matches, review_matches
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/offering_links.py ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py
git commit -m "feat(indexer): add threshold-based cross-offering match comparison"
```

---

### Task 5: Writing a match (index + Obsidian-visible markdown)

**Files:**
- Modify: `ai-sandbox/academic-rag-model/core/indexer/offering_links.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py`

**Interfaces:**
- Consumes: `load_shard`, `save_shard`, `recompute_course_entry` (already in `core/indexer/index_card.py`); the `(card_a, card_b, similarity)` tuples `find_cross_offering_matches()` produces (Task 4).
- Produces: `link_target_display(card, offering_label) -> tuple[str, str]`, `append_related_section(academic_hub_root, card, related) -> bool`, `write_matches(academic_hub_root, matches, confidence) -> dict` -- used by Task 6.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/indexer/test_offering_links.py`:

```python
from core.indexer.offering_links import append_related_section, link_target_display, write_matches


def test_link_target_display_strips_notes_prefix_and_md_suffix():
    card = {"path": "academic_notes/econometrics/class_2024/Class Notes/Slides/processed_outputs/slides1.md",
            "title": "Slides 1"}
    link_path, alias = link_target_display(card, "2024")
    assert link_path == "econometrics/class_2024/Class Notes/Slides/processed_outputs/slides1"
    assert alias == "2024: Slides 1"


def test_link_target_display_labels_a_primary_card_as_current():
    card = {"path": "academic_notes/econometrics/professor_notes/processed_outputs/slides1.md", "title": "Slides 1"}
    _, alias = link_target_display(card, None)
    assert alias == "current: Slides 1"


def test_append_related_section_writes_a_new_block(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("---\ntitle: foo\n---\n\nBody text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])

    content = note_path.read_text()
    assert written is True
    assert content.startswith("---\ntitle: foo\n---\n\nBody text.\n")
    assert "## Related notes" in content
    assert "[[econometrics/class_2024/processed_outputs/x|2024: X]]" in content


def test_append_related_section_is_idempotent(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("---\ntitle: foo\n---\n\nBody text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written_1 = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    content_1 = note_path.read_text()
    written_2 = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    content_2 = note_path.read_text()

    assert written_1 is True
    assert written_2 is True
    assert content_1 == content_2  # rerun replaces in place, doesn't duplicate
    assert content_1.count("## Related notes") == 1
    assert "[[econometrics/class_2024/processed_outputs/x|2024: X]]" in content_1


def test_append_related_section_reflects_a_changed_match_list(tmp_path):
    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    note_path = note_dir / "y.md"
    note_path.write_text("Body text.\n")
    card = {"path": "academic_notes/econometrics/y.md"}
    target_a = {"path": "academic_notes/econometrics/class_2024/processed_outputs/a.md", "title": "A"}
    target_b = {"path": "academic_notes/econometrics/class_2023/processed_outputs/b.md", "title": "B"}

    append_related_section(academic_hub_root, card, [(target_a, "2024", 0.92)])
    append_related_section(academic_hub_root, card, [(target_a, "2024", 0.92), (target_b, "2023", 0.88)])
    content = note_path.read_text()

    assert content.count("## Related notes") == 1
    assert "2024: A" in content
    assert "2023: B" in content


def test_append_related_section_skips_a_missing_file_without_raising(tmp_path):
    academic_hub_root = str(tmp_path)
    card = {"path": "academic_notes/econometrics/does-not-exist.md"}
    target = {"path": "academic_notes/econometrics/class_2024/processed_outputs/x.md", "title": "X"}

    written = append_related_section(academic_hub_root, card, [(target, "2024", 0.92)])
    assert written is False


def test_write_matches_updates_related_offerings_on_both_cards(tmp_path):
    from core.indexer.index_card import load_shard, save_shard

    academic_hub_root = str(tmp_path)
    note_dir_a = tmp_path / "academic_notes" / "econometrics"
    note_dir_a.mkdir(parents=True)
    (note_dir_a / "a.md").write_text("Body A.\n")
    (note_dir_a / "b.md").write_text("Body B.\n")

    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b])

    stats = write_matches(academic_hub_root, [(card_a, card_b, 0.92)], confidence="high", offerings={"fa": None, "fb": "2024"})

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    assert cards["fa"]["related_offerings"] == [{"file_id": "fb", "path": card_b["path"], "similarity": 0.92, "confidence": "high"}]
    assert cards["fb"]["related_offerings"] == [{"file_id": "fa", "path": card_a["path"], "similarity": 0.92, "confidence": "high"}]
    assert stats["links_written"] == 1


def test_write_matches_replaces_a_stale_entry_for_the_same_pair_on_rerun(tmp_path):
    from core.indexer.index_card import load_shard, save_shard

    academic_hub_root = str(tmp_path)
    note_dir = tmp_path / "academic_notes" / "econometrics"
    note_dir.mkdir(parents=True)
    (note_dir / "a.md").write_text("Body A.\n")
    (note_dir / "b.md").write_text("Body B.\n")
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/a.md", "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/b.md", "title": "B", "embedding": [0.95, 0.31]}
    save_shard(academic_hub_root, "econometrics", [card_a, card_b])

    write_matches(academic_hub_root, [(card_a, card_b, 0.80)], confidence="review", offerings={"fa": None, "fb": "2024"})
    write_matches(academic_hub_root, [(card_a, card_b, 0.95)], confidence="high", offerings={"fa": None, "fb": "2024"})

    cards = {c["file_id"]: c for c in load_shard(academic_hub_root, "econometrics")}
    assert cards["fa"]["related_offerings"] == [{"file_id": "fb", "path": card_b["path"], "similarity": 0.95, "confidence": "high"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -k "link_target_display or append_related_section or write_matches" -v`
Expected: FAIL (none of these three functions exist yet)

- [ ] **Step 3: Implement**

Add to `core/indexer/offering_links.py` (add `load_shard, recompute_course_entry, save_shard` to the existing `core.indexer.index_card` import):

```python
_SECTION_START = "<!-- offering-links:start -->"
_SECTION_END = "<!-- offering-links:end -->"
_NOTES_PREFIX = "academic_notes/"


def link_target_display(card: dict, offering_label: str | None) -> tuple[str, str]:
    """(wikilink target path, alias text) for card. The target is
    card["path"] relative to the academic_notes/ vault root (Obsidian's
    actual sync root is that directory's own standalone git repo, not
    academic-hub/ itself) with the .md suffix stripped -- a bare filename
    link would be ambiguous given real collisions already in this corpus
    (e.g. slides1.md exists under both professor_notes/ and
    class_2024/Class Notes/Slides/)."""
    path = card["path"]
    if path.startswith(_NOTES_PREFIX):
        path = path[len(_NOTES_PREFIX):]
    if path.endswith(".md"):
        path = path[: -len(".md")]
    offering_text = offering_label if offering_label is not None else "current"
    alias = f"{offering_text}: {card.get('title') or os.path.basename(path)}"
    return path, alias


def _build_related_section(related: list[tuple[dict, str | None, float]]) -> str:
    lines = [_SECTION_START, "## Related notes"]
    for target_card, offering_label, similarity in related:
        link_path, alias = link_target_display(target_card, offering_label)
        lines.append(f"- [[{link_path}|{alias}]] (similarity: {similarity:.2f})")
    lines.append(_SECTION_END)
    return "\n".join(lines) + "\n"


def append_related_section(academic_hub_root: str, card: dict, related: list[tuple[dict, str | None, float]]) -> bool:
    """Appends (or replaces, if already present) an idempotent, delimited
    '## Related notes' block at the end of card's own .md file. Returns
    False (logged, not raised) if the file doesn't exist on disk --
    an indexing side-effect must never block on a missing file."""
    md_path = os.path.join(academic_hub_root, card["path"])
    if not os.path.isfile(md_path):
        print(f"WARNING: cannot write related-notes section, file not found: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_section = _build_related_section(related)
    start = content.find(_SECTION_START)
    if start == -1:
        separator = "" if content.endswith("\n") else "\n"
        new_content = content + separator + "\n" + new_section
    else:
        end = content.find(_SECTION_END)
        end = end + len(_SECTION_END) if end != -1 else len(content)
        new_content = content[:start] + new_section + content[end:].lstrip("\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def write_matches(
    academic_hub_root: str, matches: list[tuple[dict, dict, float]], confidence: str,
    offerings: dict[str, str | None],
) -> dict:
    """Writes both directions of every match: each card's related_offerings
    index field (replacing any prior entry for that same pair, so a rerun
    is idempotent) and both cards' Obsidian-visible markdown section.
    `offerings` maps file_id -> offering_label, precomputed by the caller
    (Task 6) via derive_offering_for_card() for every card involved."""
    stats = {"links_written": 0, "markdown_writes_skipped": 0}
    by_file_id_related: dict[str, list[tuple[dict, str | None, float]]] = {}

    for card_a, card_b, similarity in matches:
        by_file_id_related.setdefault(card_a["file_id"], []).append((card_b, offerings.get(card_b["file_id"]), similarity))
        by_file_id_related.setdefault(card_b["file_id"], []).append((card_a, offerings.get(card_a["file_id"]), similarity))
        stats["links_written"] += 1

    # Group touched cards by the course each one's own path implies, so
    # each shard is loaded and saved exactly once regardless of how many
    # matches touch cards in it.
    touched_paths: dict[str, str] = {}
    for card_a, card_b, _ in matches:
        touched_paths[card_a["file_id"]] = card_a["path"]
        touched_paths[card_b["file_id"]] = card_b["path"]
    courses = {path.replace("\\", "/").split("/")[1] for path in touched_paths.values()}

    for course in courses:
        shard = load_shard(academic_hub_root, course)
        changed = False
        for card in shard:
            fid = card.get("file_id")
            if fid not in by_file_id_related:
                continue
            card["related_offerings"] = [
                {"file_id": other["file_id"], "path": other["path"], "similarity": sim, "confidence": confidence}
                for other, _label, sim in by_file_id_related[fid]
            ]
            changed = True
        if changed:
            save_shard(academic_hub_root, course, shard)
            recompute_course_entry(academic_hub_root, course)

    for card_a, card_b, _ in matches:
        for card in (card_a, card_b):
            related = by_file_id_related[card["file_id"]]
            if not append_related_section(academic_hub_root, card, related):
                stats["markdown_writes_skipped"] += 1

    return stats
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/offering_links.py ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py
git commit -m "feat(indexer): write cross-offering matches to the index and as Obsidian-visible links"
```

---

### Task 6: CLI and end-to-end wiring

**Files:**
- Modify: `ai-sandbox/academic-rag-model/core/indexer/offering_links.py`
- Test: `ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py`

**Interfaces:**
- Consumes: everything from Tasks 3-5, plus `list_courses`, `load_shard` (`core/indexer/index_card.py`).
- Produces: `run_for_course(academic_hub_root, course, dry_run=False) -> dict`, `resolve_pending(academic_hub_root, file_id_a, file_id_b) -> bool`, `reject_pending(academic_hub_root, file_id_a, file_id_b) -> bool`, `main()`. This is the plan's final public surface -- nothing downstream consumes these within this plan's scope.

- [ ] **Step 1: Write the failing tests**

Add to `tests/core/indexer/test_offering_links.py`:

```python
from core.indexer.offering_links import reject_pending, resolve_pending, run_for_course


def _seed_course(tmp_path, course, cards):
    from core.indexer.index_card import save_shard
    note_dir = tmp_path / "academic_notes" / course
    note_dir.mkdir(parents=True, exist_ok=True)
    for card in cards:
        rel = card["path"][len("academic_notes/"):]
        full = tmp_path / "academic_notes" / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"Body for {card['file_id']}.\n")
    save_shard(str(tmp_path), course, cards)


def test_run_for_course_writes_an_auto_match_end_to_end(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))

    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["fa"]["related_offerings"][0]["file_id"] == "fb"
    assert cards["fb"]["related_offerings"][0]["file_id"] == "fa"
    assert stats["auto_matches"] == 1


def test_run_for_course_excludes_a_card_with_no_embedding(tmp_path):
    # A needs_indexing failure card has embedding=[] -- must be cleanly
    # excluded from comparison, not crash cosine_similarity() or get
    # spuriously matched against everything via an empty-vector score.
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [], "needs_indexing": True}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    assert stats["auto_matches"] == 0
    assert stats["review_matches"] == 0


def test_run_for_course_dry_run_writes_nothing(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics", dry_run=True)

    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]
    assert stats["auto_matches"] == 1


def test_run_for_course_logs_a_review_match_instead_of_writing_it(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])

    stats = run_for_course(str(tmp_path), "econometrics")

    from core.indexer.offering_links import load_review
    from core.indexer.index_card import load_shard
    assert stats["review_matches"] == 1
    assert len(load_review(str(tmp_path))) == 1
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]


def test_run_for_course_skips_a_dismissed_pair(tmp_path):
    from core.indexer.offering_links import record_dismissal
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.95, 0.3122498999199199]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    record_dismissal(str(tmp_path), "fa", "fb")

    stats = run_for_course(str(tmp_path), "econometrics")

    assert stats["auto_matches"] == 0
    from core.indexer.index_card import load_shard
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert "related_offerings" not in cards["fa"]


def test_resolve_pending_promotes_a_review_match_to_a_written_link(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")  # produces one pending review entry

    resolved = resolve_pending(str(tmp_path), "fa", "fb")

    from core.indexer.offering_links import load_review
    from core.indexer.index_card import load_shard
    assert resolved is True
    assert load_review(str(tmp_path)) == []
    cards = {c["file_id"]: c for c in load_shard(str(tmp_path), "econometrics")}
    assert cards["fa"]["related_offerings"][0]["confidence"] == "high"


def test_resolve_pending_returns_false_when_pair_not_in_review(tmp_path):
    assert resolve_pending(str(tmp_path), "nope", "nothing") is False


def test_reject_pending_dismisses_and_clears_the_pending_entry(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    subset.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    card_a = {"file_id": "fa", "path": "academic_notes/econometrics/professor_notes/a.md",
              "title": "A", "embedding": [1.0, 0.0]}
    card_b = {"file_id": "fb", "path": "academic_notes/econometrics/class_2024/b.md",
              "title": "B", "embedding": [0.85, 0.5266403851195171]}
    _seed_course(tmp_path, "econometrics", [card_a, card_b])
    run_for_course(str(tmp_path), "econometrics")

    rejected = reject_pending(str(tmp_path), "fa", "fb")

    from core.indexer.offering_links import is_dismissed, load_dismissals, load_review
    assert rejected is True
    assert load_review(str(tmp_path)) == []
    assert is_dismissed(load_dismissals(str(tmp_path)), "fa", "fb")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -k "run_for_course or resolve_pending or reject_pending" -v`
Expected: FAIL (none of these three functions exist yet)

- [ ] **Step 3: Implement**

Add to `core/indexer/offering_links.py` (add `list_courses, find_card_by_file_id` to the existing `core.indexer.index_card` import):

```python
def run_for_course(academic_hub_root: str, course: str, dry_run: bool = False) -> dict:
    notes_course_dir = os.path.join(academic_hub_root, "academic_notes", course)
    all_cards = [
        c for c in load_shard(academic_hub_root, course)
        if c.get("embedding") and not c.get("orphaned") and not c.get("needs_indexing")
    ]
    offerings = {c["file_id"]: derive_offering_for_card(c, academic_hub_root) for c in all_cards}
    cards_with_offerings = [(c, offerings[c["file_id"]]) for c in all_cards]

    auto_matches, review_matches = find_cross_offering_matches(cards_with_offerings)

    dismissals = load_dismissals(academic_hub_root)
    auto_matches = [
        m for m in auto_matches if not is_dismissed(dismissals, m[0]["file_id"], m[1]["file_id"])
    ]
    review_matches = [
        m for m in review_matches if not is_dismissed(dismissals, m[0]["file_id"], m[1]["file_id"])
    ]

    if not dry_run and auto_matches:
        write_matches(academic_hub_root, auto_matches, confidence="high", offerings=offerings)

    if not dry_run and review_matches:
        existing_review = load_review(academic_hub_root)
        existing_pairs = {tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) for e in existing_review}
        for card_a, card_b, similarity in review_matches:
            pair = tuple(sorted([card_a["file_id"], card_b["file_id"]]))
            if pair in existing_pairs:
                continue
            existing_review.append({
                "file_id_a": pair[0], "file_id_b": pair[1], "similarity": similarity, "course": course,
            })
        save_review(academic_hub_root, existing_review)

    return {"auto_matches": len(auto_matches), "review_matches": len(review_matches)}


def resolve_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Confirms a pending review match: writes it as a high-confidence
    link (same as an auto-match) and removes it from review.json."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    entry = next((e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) == pair), None)
    if entry is None:
        return False

    found_a = find_card_by_file_id(academic_hub_root, file_id_a)
    found_b = find_card_by_file_id(academic_hub_root, file_id_b)
    if found_a is None or found_b is None:
        return False
    _, card_a = found_a
    _, card_b = found_b
    offerings = {
        file_id_a: derive_offering_for_card(card_a, academic_hub_root),
        file_id_b: derive_offering_for_card(card_b, academic_hub_root),
    }
    write_matches(academic_hub_root, [(card_a, card_b, entry["similarity"])], confidence="high", offerings=offerings)

    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    save_review(academic_hub_root, remaining)
    return True


def reject_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Permanently dismisses a pending review match and clears it from
    review.json. Returns True even if the pair was already dismissed but
    present in review.json (clearing the stale entry is still useful)."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    was_pending = len(remaining) != len(review)
    record_dismissal(academic_hub_root, file_id_a, file_id_b)
    if was_pending:
        save_review(academic_hub_root, remaining)
    return was_pending


def main() -> None:
    import argparse

    from core.env.gemini_utils import load_dotenv_override

    load_dotenv_override()
    parser = argparse.ArgumentParser(
        description="Find and link likely corollaries between a course's marked prior "
                    "offerings and its other content, using each card's existing embedding."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course.")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing anything.")
    parser.add_argument("--resolve", metavar="FILE_ID_A:FILE_ID_B",
                         help="Confirm one pending review match, writing it as a high-confidence link.")
    parser.add_argument("--reject", metavar="FILE_ID_A:FILE_ID_B",
                         help="Permanently dismiss one pending review match.")
    args = parser.parse_args()

    academic_hub_dir = str(_academic_hub_dir())

    if args.resolve:
        a, b = args.resolve.split(":", 1)
        print("resolved" if resolve_pending(academic_hub_dir, a, b) else "no such pending match")
        return
    if args.reject:
        a, b = args.reject.split(":", 1)
        print("dismissed" if reject_pending(academic_hub_dir, a, b) else "no such pending match")
        return

    courses = args.course if args.course is not None else list_courses(academic_hub_dir)
    for course in courses:
        stats = run_for_course(academic_hub_dir, course, dry_run=args.dry_run)
        print(f"{course}: {stats['auto_matches']} linked, {stats['review_matches']} pending review")


def _academic_hub_dir():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent / "academic-hub"


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/core/indexer/test_offering_links.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full package test suite**

Run: `python -m pytest tests/ -q`
Expected: all PASS -- confirms Tasks 1-2's refactors/additive fields caused no regressions anywhere else in the package (`index_search.py`, `retag.py`, `duplicate_check.py`, `generate_video_notes`, `convert_essays`, etc. all read cards from the same shards).

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/core/indexer/offering_links.py ai-sandbox/academic-rag-model/tests/core/indexer/test_offering_links.py
git commit -m "feat(indexer): add offering_links CLI (--course, --dry-run, --resolve, --reject)"
```

---

## After implementation

The two threshold constants (`OFFERING_LINK_AUTO_THRESHOLD = 0.90`, `OFFERING_LINK_REVIEW_THRESHOLD = 0.80`) are starting guesses. Before relying on real output, run `python -m core.indexer.offering_links --course econometrics --dry-run` against the real corpus (`class_2024` alongside current econometrics content) and inspect the actual similarity distribution it reports, adjusting the two constants if the real numbers suggest the bar is in the wrong place -- same empirical-calibration step `retag.py`'s own `TAG_ASSIGNMENT_THRESHOLD` went through. This is a manual follow-up outside this plan's test scope, since it needs the real embeddings, not fixtures.
