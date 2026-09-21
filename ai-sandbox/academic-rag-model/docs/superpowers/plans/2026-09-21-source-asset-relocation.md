# Source Asset Relocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let heavy note sources (PDFs, Excalidraw `.svg`/`.png` exports) move from `academic_notes/` to `academic_resources/` while `.md` files (scene files, `processed_outputs/`) stay put -- with both the transcription pipelines and the JSON source index still able to find, write to, and resolve everything correctly, in either location, during and after a partial migration.

**Architecture:** A new pure-path-math module (`common/academic_hub_paths.py`) centralizes the "same relative path, different root" mirroring rule; both transcribe pipelines and the router consume it instead of assuming source-and-output are always siblings. The JSON index gains a `source_asset_path` field, distinct from the existing `source_pdf_path` identity anchor, so a reader can always find the true heavy source regardless of doc type. `index_search.py`'s `rebuild()` gains an Excalidraw walker -- fixing a real, currently-live bug (verified empirically, not assumed) where Excalidraw cards get silently orphaned by every `rebuild()` run today. A new migration script does the actual file moves, reusing `rebuild()`'s existing cheap "file moved, content unchanged" reconciliation rather than inventing a second mechanism.

**Tech Stack:** Python, `unittest.TestCase` + `unittest.mock.MagicMock` (matches `tests/test_index_card.py`/`tests/test_index_search.py`'s existing style), pytest for the newer plain-function-style test files (`tests/test_route_notes_transcribe.py`, etc.).

**Spec:** `docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md` (see also its 2026-09-21 addendum section, folding in a concurrent session's brainstorm -- three decisions incorporated as Task 8 and amendments to Tasks 9-10 below, three items left open for the user)

**Status (2026-09-21):** Tasks 1-7 complete, tested, and committed. Task 8 (vocabulary rename) is new, added after Tasks 1-7 landed -- confirmed zero rework needed on completed code, since the path-mirroring helpers never touch course/category names. Tasks 9-10 amended in place, not yet implemented.

## Global Constraints

- Mirrored-path convention: a heavy source's new home is the exact same `<course>/<category>/<filename>` relative path, rooted at `academic_resources/` instead of `academic_notes/`. `processed_outputs/` never moves -- it always anchors to whichever lightweight file stays in `academic_notes/` (the PDF's own would-be location for a PDF note; the `.excalidraw.md` scene file's actual location for an Excalidraw note, since that file never moves).
- Every discovery/resolution path must work correctly whether a given file has already migrated or not -- migration happens one course/category at a time in practice, never atomically.
- `source_pdf_path` keeps its existing meaning (the `compute_file_id()` identity anchor) unchanged. The new `source_asset_path` field is additive, not a rename or a breaking change to any existing reader.
- New-card creation defaults `source_asset_path` to `source_pdf_path` when the caller doesn't pass one explicitly (existing textbook/video-notes callers need zero changes). Reconciling an *existing* card only overwrites `source_asset_path` when the caller passes a non-`None` value -- `None` means "this caller can't currently determine it," not "clear it."
- Never run the migration script against the real corpus as part of this plan -- building and testing it (against synthetic fixtures) is in scope; physically moving the user's real files is a separate, explicit go/no-go after every task below is verified.
- Match this project's existing testing conventions per file: `tests/test_index_card.py`/`tests/test_index_search.py` use `unittest.TestCase` + a `_fake_client()`-style `MagicMock` helper; `tests/test_transcribe_notes.py`/`tests/test_transcribe_excalidraw.py`/`tests/test_route_notes_transcribe.py` use plain pytest functions + `unittest.mock.patch`. New test files should pick whichever convention the module they're testing already uses.

---

## File Structure

- `common/academic_hub_paths.py` (new) -- pure path-mirroring helpers (`to_resources_root`, `to_notes_root`, `resolve_output_dir`). No filesystem I/O, no network.
- `indexer/index_card.py` (modified) -- `source_asset_path` threaded through `generate_index_card`, `make_failure_card`, `reconcile_and_write`, `move_card`.
- `indexer/index_search.py` (modified) -- new `_excalidraw_note_paths()` walker, wired into `rebuild()`; `_reconcile_one()` gains a `source_asset_path` parameter.
- `notes/transcribe_notes.py` (modified) -- `process_pdf()` uses `resolve_output_dir()` instead of a hardcoded sibling; `source_pdf` frontmatter upgrades from a bare filename to a full relative path; `_write_markdown_and_index()` passes `source_asset_path`.
- `notes/transcribe_excalidraw.py` (modified) -- `discover_excalidraw_files()` falls back to the mirrored `academic_resources/` location when no local image sibling exists; `write_outputs()` uses `resolve_output_dir()`, upgrades `source_image` frontmatter to a full relative path, and passes `source_asset_path`.
- `notes/route_notes_transcribe.py` (modified) -- `discover_pdf_sources()` also walks `academic_resources/<course>/<category>/` for any category that has a same-named counterpart under `academic_notes/<course>/`.
- `notes/migrate_sources_to_resources.py` (new) -- one-shot migration script: moves heavy files, then calls `rebuild()` to resync the index.
- New/modified tests: `tests/test_academic_hub_paths.py` (new), `tests/test_index_card.py` (modified), `tests/test_index_search.py` (modified), `tests/test_transcribe_notes.py` (modified), `tests/test_transcribe_excalidraw.py` (modified), `tests/test_route_notes_transcribe.py` (modified), `tests/test_migrate_sources_to_resources.py` (new).

---

### Task 1: Path-mirroring helpers

**Files:**
- Create: `common/academic_hub_paths.py`
- Test: `tests/test_academic_hub_paths.py`

**Interfaces:**
- Produces: `to_resources_root(path: str) -> str`, `to_notes_root(path: str) -> str`, `resolve_output_dir(source_path: str) -> str`.

- [x] **Step 1: Write the failing test**

```python
# tests/test_academic_hub_paths.py
import os

import pytest

from common.academic_hub_paths import resolve_output_dir, to_notes_root, to_resources_root


def test_to_resources_root_swaps_the_segment_in_an_os_native_path():
    path = os.path.join("C:" + os.sep, "hub", "academic_notes", "econometrics", "ta_notes", "foo.pdf")
    result = to_resources_root(path)
    assert "academic_resources" in result
    assert "academic_notes" not in result
    assert result.endswith(os.path.join("econometrics", "ta_notes", "foo.pdf"))


def test_to_resources_root_preserves_forward_slash_relative_paths():
    assert (
        to_resources_root("academic_notes/econometrics/ta_notes/foo.pdf")
        == "academic_resources/econometrics/ta_notes/foo.pdf"
    )


def test_to_notes_root_is_the_inverse():
    assert (
        to_notes_root("academic_resources/econometrics/ta_notes/foo.pdf")
        == "academic_notes/econometrics/ta_notes/foo.pdf"
    )


def test_to_resources_root_raises_when_no_academic_notes_segment():
    with pytest.raises(ValueError):
        to_resources_root("some/other/path/foo.pdf")


def test_to_notes_root_raises_when_no_academic_resources_segment():
    with pytest.raises(ValueError):
        to_notes_root("academic_notes/econometrics/ta_notes/foo.pdf")


def test_resolve_output_dir_mirrors_when_source_under_resources():
    source = os.path.join("academic_resources", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "ta_notes", "processed_outputs")


def test_resolve_output_dir_stays_a_sibling_when_source_still_under_notes():
    source = os.path.join("academic_notes", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "ta_notes", "processed_outputs")


def test_resolve_output_dir_stays_a_sibling_for_an_excalidraw_scene_file():
    # The .excalidraw.md anchor never moves -- always sibling behavior,
    # identical to today, regardless of where its image sibling lives.
    source = os.path.join("academic_notes", "econometrics", "lecture_notes", "Drawing.excalidraw.md")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "lecture_notes", "processed_outputs")


def test_resolve_output_dir_works_with_a_full_absolute_windows_style_path():
    source = os.path.join("C:" + os.sep, "hub", "academic_resources", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    expected = os.path.join("C:" + os.sep, "hub", "academic_notes", "econometrics", "ta_notes", "processed_outputs")
    assert result == expected
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_academic_hub_paths.py -v` (from `academic-rag-model/`)
Expected: FAIL with `ModuleNotFoundError: No module named 'common.academic_hub_paths'`

- [x] **Step 3: Write minimal implementation**

```python
# common/academic_hub_paths.py
"""
academic_hub_paths.py
Path-mirroring helpers between academic_notes/ (lightweight: .md scene
files, processed_outputs/) and academic_resources/ (heavy: PDFs,
Excalidraw .svg/.png exports). See
docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md.
Pure string/path manipulation -- no filesystem I/O, no network -- safe to
import at module scope anywhere.
"""
from __future__ import annotations

import os

_NOTES_ROOT_NAME = "academic_notes"
_RESOURCES_ROOT_NAME = "academic_resources"


def _swap_root(path: str, old_root: str, new_root: str) -> str:
    had_backslashes = "\\" in path
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    try:
        idx = parts.index(old_root)
    except ValueError:
        raise ValueError(f"path has no {old_root!r} segment: {path!r}")
    parts[idx] = new_root
    result = "/".join(parts)
    return result.replace("/", os.sep) if had_backslashes else result


def to_resources_root(path: str) -> str:
    """Rewrites a path's academic_notes/ segment to academic_resources/,
    preserving everything else (course/category/filename)."""
    return _swap_root(path, _NOTES_ROOT_NAME, _RESOURCES_ROOT_NAME)


def to_notes_root(path: str) -> str:
    """The inverse of to_resources_root."""
    return _swap_root(path, _RESOURCES_ROOT_NAME, _NOTES_ROOT_NAME)


def resolve_output_dir(source_path: str) -> str:
    """Given a source file's path (a PDF, or an Excalidraw scene/image
    file), returns the directory its processed_outputs/ should live
    under: mirrored into academic_notes/ if the source currently lives
    under academic_resources/ (the post-migration case for a PDF), or the
    source's own sibling processed_outputs/ otherwise -- covers both "not
    yet migrated" and "never moves at all" (an Excalidraw .excalidraw.md
    scene file), which is this project's convention from before this
    module existed."""
    normalized = source_path.replace("\\", "/")
    parts = normalized.split("/")
    if _RESOURCES_ROOT_NAME in parts:
        mirrored = to_notes_root(source_path)
        return os.path.join(os.path.dirname(mirrored), "processed_outputs")
    return os.path.join(os.path.dirname(source_path), "processed_outputs")
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_academic_hub_paths.py -v`
Expected: PASS (9 tests)

- [x] **Step 5: Commit**

```bash
git add common/academic_hub_paths.py tests/test_academic_hub_paths.py
git commit -m "feat(paths): add academic_notes/academic_resources path-mirroring helpers"
```

---

### Task 2: `source_asset_path` on the index card schema

**Files:**
- Modify: `indexer/index_card.py`
- Test: `tests/test_index_card.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `generate_index_card(..., source_asset_path: str | None = None)`, `make_failure_card(..., source_asset_path: str | None = None)`, `reconcile_and_write(..., source_asset_path: str | None = None)` -- all three now write/preserve a `source_asset_path` key on the card dict. `move_card()` rewrites it the same way it already rewrites `source_pdf_path`.

- [x] **Step 1: Write the failing test**

```python
# tests/test_index_card.py -- add to TestGenerateIndexCard
    def test_source_asset_path_defaults_to_source_pdf_path_when_not_given(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["source_asset_path"], "p.pdf")

    def test_source_asset_path_uses_explicit_value_when_given(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.excalidraw.md", course="math-camp",
            folder_category="excalidraw_notes", content_sample="text", page_count=3, client=client,
            source_asset_path="p.excalidraw.svg",
        )
        self.assertEqual(card["source_asset_path"], "p.excalidraw.svg")


# tests/test_index_card.py -- add to TestMakeFailureCard
    def test_source_asset_path_defaults_to_source_pdf_path(self):
        card = make_failure_card(
            file_id="abc123", path="p.md", source_pdf_path="p.pdf",
            course="math-camp", folder_category="ta_notes",
        )
        self.assertEqual(card["source_asset_path"], "p.pdf")


# tests/test_index_card.py -- add to TestReconcileAndWrite
    def test_new_card_source_asset_path_defaults_to_source_pdf_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = reconcile_and_write(tmp, **self._card_kwargs())
            self.assertEqual(card["source_asset_path"], "a.pdf")

    def test_existing_card_source_asset_path_updates_when_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client, source_asset_path="a.svg"))
            reconcile_and_write(tmp, **self._card_kwargs(client=client, source_asset_path="a-renamed.svg"))
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            self.assertEqual(load_shard(tmp, "math-camp")[0]["source_asset_path"], "a-renamed.svg")

    def test_existing_card_source_asset_path_preserved_when_not_given(self):
        # A caller that can't currently determine the asset location
        # (e.g. rebuild's Excalidraw walker, mid-migration) must not
        # blow away a previously-known-good value. Changing `path` (not
        # source_asset_path) on the second call is deliberate: it forces
        # `changed=True` so reconcile_and_write's "found" branch actually
        # runs and rewrites the shard, rather than the whole call being a
        # same-everything no-op that would pass this assertion vacuously
        # (the "unchanged path" no-op branch never touches the shard, so
        # it can't tell "correctly preserved" apart from "never ran").
        with tempfile.TemporaryDirectory() as tmp:
            client = _fake_client()
            reconcile_and_write(tmp, **self._card_kwargs(client=client, source_asset_path="a.svg"))
            reconcile_and_write(tmp, **self._card_kwargs(client=client, path="moved/a.md"))  # no source_asset_path this time
            self.assertEqual(client.models.generate_content.call_count, 1)  # still no regen
            updated = load_shard(tmp, "math-camp")[0]
            self.assertEqual(updated["path"], "moved/a.md")  # the actual change took effect
            self.assertEqual(updated["source_asset_path"], "a.svg")  # untouched field preserved


# tests/test_index_card.py -- add to TestMoveCard
    def test_move_card_rewrites_source_asset_path_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "misc", [
                {"file_id": "x", "path": "misc/processed_outputs/a.md",
                 "source_pdf_path": "misc/a.excalidraw.md", "source_asset_path": "misc/a.svg",
                 "course": "misc", "embedding": [1.0, 0.0], "tags": []},
            ])
            move_card(tmp, "x", "business")
            moved = load_shard(tmp, "business")
            self.assertEqual(moved[0]["source_asset_path"], "business/a.svg")
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_index_card.py -v -k source_asset_path`
Expected: FAIL -- `KeyError: 'source_asset_path'` on every new test.

- [x] **Step 3: Write minimal implementation**

In `indexer/index_card.py`, modify `generate_index_card`:

```python
def generate_index_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str, page_count: int, client, content_hash: str | None = None,
    known_doc_types: frozenset[str] = KNOWN_DOC_TYPES, source_asset_path: str | None = None,
) -> dict:
    """... (existing docstring unchanged) ..."""
```

and in its return dict, add (right after `"source_pdf_path": source_pdf_path,` -- note `generate_index_card`'s return dict doesn't currently include `source_pdf_path` itself; it's added by the caller's card assembly in the returned dict below):

```python
    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "source_asset_path": source_asset_path if source_asset_path is not None else source_pdf_path,
        "course": course,
        ... # rest unchanged
    }
```

Modify `make_failure_card` the same way:

```python
def make_failure_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_hash: str | None = None, source_asset_path: str | None = None,
) -> dict:
    """... (existing docstring unchanged) ..."""
    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "source_asset_path": source_asset_path if source_asset_path is not None else source_pdf_path,
        "course": course,
        ... # rest unchanged
    }
```

Modify `reconcile_and_write`:

```python
def reconcile_and_write(
    academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str,
    folder_category: str, content_sample: str, page_count: int, client,
    content_hash: str | None = None, known_doc_types: frozenset[str] = KNOWN_DOC_TYPES,
    source_asset_path: str | None = None,
) -> dict:
    """... (existing docstring unchanged, add one line:) source_asset_path
    is additive: a new card defaults it to source_pdf_path when not given;
    reconciling an existing card only overwrites it when a non-None value
    is passed, so a caller that can't currently determine the asset
    location doesn't blow away a previously-known-good one."""
    found = find_card_by_file_id(academic_hub_root, file_id)

    if found is not None:
        old_course, old_card = found
        resolved_asset_path = (
            source_asset_path if source_asset_path is not None else old_card.get("source_asset_path")
        )
        changed = (
            old_card.get("path") != path
            or old_card.get("source_pdf_path") != source_pdf_path
            or old_card.get("source_asset_path") != resolved_asset_path
            or old_card.get("orphaned")
        )
        updated = dict(old_card)
        updated["path"] = path
        updated["source_pdf_path"] = source_pdf_path
        updated["source_asset_path"] = resolved_asset_path
        updated["course"] = course
        updated["content_hash"] = content_hash
        updated.pop("orphaned", None)
        if changed:
            updated["source_updated_at"] = now_iso()

        if old_course == course:
            if changed:
                save_shard(academic_hub_root, course, _replace_card(
                    load_shard(academic_hub_root, course), file_id, updated,
                ))
                recompute_course_entry(academic_hub_root, course)
            return updated

        # Moved to a different course.
        remaining = [c for c in load_shard(academic_hub_root, old_course) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, old_course, remaining)
        new_course_cards = load_shard(academic_hub_root, course)
        new_course_cards.append(updated)
        save_shard(academic_hub_root, course, new_course_cards)
        recompute_course_entry(academic_hub_root, old_course)
        recompute_course_entry(academic_hub_root, course)
        return updated

    # No match anywhere -- genuinely new content (spec §4.3).
    try:
        card = generate_index_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path, course=course,
            folder_category=folder_category, content_sample=content_sample,
            page_count=page_count, client=client, content_hash=content_hash,
            known_doc_types=known_doc_types, source_asset_path=source_asset_path,
        )
    except Exception as err:
        print(f"WARNING: index card generation failed for {path} ({err}); writing needs_indexing card.")
        card = make_failure_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path,
            course=course, folder_category=folder_category, content_hash=content_hash,
            source_asset_path=source_asset_path,
        )

    cards = load_shard(academic_hub_root, course)
    cards.append(card)
    save_shard(academic_hub_root, course, cards)
    recompute_course_entry(academic_hub_root, course)
    return card
```

Modify `move_card` (add one line after the existing `source_pdf_path` rewrite):

```python
    card = dict(card)
    card["course"] = new_course
    if card.get("path"):
        card["path"] = card["path"].replace(f"{old_course}/", f"{new_course}/", 1)
    if card.get("source_pdf_path"):
        card["source_pdf_path"] = card["source_pdf_path"].replace(f"{old_course}/", f"{new_course}/", 1)
    if card.get("source_asset_path"):
        card["source_asset_path"] = card["source_asset_path"].replace(f"{old_course}/", f"{new_course}/", 1)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_index_card.py -v`
Expected: PASS (full file, including every pre-existing test -- none of their assertions touch `source_asset_path`, so the new default-fill behavior doesn't break them)

- [x] **Step 5: Commit**

```bash
git add indexer/index_card.py tests/test_index_card.py
git commit -m "feat(index): add source_asset_path field, distinct from the identity-anchor source_pdf_path"
```

---

### Task 3: Fix the live Excalidraw/rebuild orphaning bug

**Files:**
- Modify: `indexer/index_search.py`
- Test: `tests/test_index_search.py`

**Interfaces:**
- Consumes: `EXCALIDRAW_DOC_TYPES` (from `indexer.index_card`, already exists), `reconcile_and_write(..., source_asset_path=...)` (Task 2).
- Produces: `_excalidraw_note_paths(academic_hub_root: str, course_filter: str | None) -> Iterator[tuple[str, str, str]]` -- yields `(course_name, category, excalidraw_md_path)`, mirroring `_notes_pdf_paths`'s shape. `_reconcile_one(..., source_asset_path: str | None = None)`.

- [x] **Step 1: Write the failing test**

```python
# tests/test_index_search.py -- add near the top, alongside _make_notes_pdf/_make_video_lecture_note
def _make_excalidraw_note(academic_hub_root, course, category, basename, write_rag_md=True):
    note_dir = os.path.join(academic_hub_root, "academic_notes", course, category)
    os.makedirs(note_dir, exist_ok=True)
    md_path = os.path.join(note_dir, f"{basename}.excalidraw.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n---\n\nfake compressed-json scene data")
    svg_path = os.path.join(note_dir, f"{basename}.excalidraw.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("<svg></svg>")
    if write_rag_md:
        out_dir = os.path.join(note_dir, "processed_outputs")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{basename}.excalidraw.rag.md"), "w", encoding="utf-8") as f:
            f.write("---\nchunks: 2\n---\n\nExpanded prose content.")
    return md_path, svg_path


# tests/test_index_search.py -- new test class, near TestRebuildVideoLectureNotes
class TestRebuildExcalidrawNotes(unittest.TestCase):
    def test_rebuild_generates_a_card_for_a_real_excalidraw_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            stats = rebuild(tmp, client)
            self.assertEqual(stats["generated"], 1)
            cards = load_shard(tmp, "econometrics")
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["doc_type"], "ta_notes")  # _fake_client's canned doc_type

    def test_rebuild_skips_a_note_with_no_rag_md_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing", write_rag_md=False)
            client = _fake_client()
            stats = rebuild(tmp, client)
            self.assertEqual(stats["generated"], 0)
            self.assertEqual(load_shard(tmp, "econometrics"), [])

    def test_rebuild_does_not_orphan_an_existing_excalidraw_card(self):
        # This is the real, live bug this task fixes: before this task,
        # rebuild() has no walker for Excalidraw notes at all, so its
        # orphan pass flags every Excalidraw card as orphaned on every
        # run. Verified against a real isolated copy of the production
        # index before this task existed -- see the design spec.
        with tempfile.TemporaryDirectory() as tmp:
            _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            rebuild(tmp, client)  # first run: generates the card
            stats = rebuild(tmp, client)  # second run: must not orphan it
            self.assertEqual(stats["orphaned"], 0)
            cards = load_shard(tmp, "econometrics")
            self.assertNotIn("orphaned", cards[0])

    def test_rebuild_sets_source_asset_path_to_the_image_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path, svg_path = _make_excalidraw_note(tmp, "econometrics", "lecture_notes", "Drawing")
            client = _fake_client()
            rebuild(tmp, client)
            card = load_shard(tmp, "econometrics")[0]
            expected = os.path.relpath(svg_path, tmp).replace(os.sep, "/")
            self.assertEqual(card["source_asset_path"], expected)

```

(The "preserve `source_asset_path` when a caller can't currently determine
it" behavior -- the actual case that matters mid-migration, when the image
has already moved somewhere `_find_excalidraw_image` doesn't yet check --
is unit-tested directly against `reconcile_and_write` in Task 2's
`test_existing_card_source_asset_path_preserved_when_not_given`, not
re-tested here. A `rebuild()`-level version of this scenario would need to
force a real rewrite without changing `path` or the `.rag.md`'s content --
neither of which the real "image went missing" case actually changes -- so
`_reconcile_one`'s existing `already_current` short-circuit would
correctly skip reconciliation entirely, which is the right real-world
outcome and doesn't need a bespoke integration test on top of Task 2's
unit-level one.)

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_index_search.py -v -k Excalidraw`
Expected: FAIL -- `test_rebuild_generates_a_card_for_a_real_excalidraw_note` and `test_rebuild_skips_a_note_with_no_rag_md_yet` fail because no card is ever generated (no walker sees the file yet); `test_rebuild_does_not_orphan_an_existing_excalidraw_card` fails because nothing generates the first card to orphan-check against. All fail for the same root reason: no Excalidraw walker exists yet.

- [x] **Step 3: Write minimal implementation**

In `indexer/index_search.py`, add the import:

```python
from indexer.index_card import (
    TEXTBOOK_CONTENT_SAMPLE_CHARS,
    EMBEDDING_DIMENSIONALITY,
    EMBEDDING_MODEL,
    EXCALIDRAW_DOC_TYPES,
    KNOWN_DOC_TYPES,
    KNOWN_LEVELS,
    LECTURE_NOTE_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    compute_id_from_parts,
    cosine_similarity,
    derive_course,
    find_card_by_file_id,
    load_courses,
    load_shard,
    recompute_course_entry,
    reconcile_and_write,
    save_shard,
    set_rag_md_path,
)
```

Add a new walker, right after `_notes_pdf_paths`:

```python
def _excalidraw_note_paths(academic_hub_root: str, course_filter: str | None):
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        if course_filter and course != course_filter:
            continue
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir):
            continue
        for category in sorted(os.listdir(course_dir)):
            category_dir = os.path.join(course_dir, category)
            if not os.path.isdir(category_dir):
                continue
            for name in sorted(os.listdir(category_dir)):
                if name.lower().endswith(".excalidraw.md"):
                    yield course, category, os.path.join(category_dir, name)
```

Add a helper to locate an Excalidraw note's image sibling, checking the local directory first and the mirrored `academic_resources/` location second. Logic mirrors `transcribe_excalidraw.discover_excalidraw_files`'s own fallback (Task 5) but is kept as a small local function here rather than imported from `notes/` -- `index_search.py` is part of `indexer/`, which `notes/` already depends on (`transcribe_notes.py`/`transcribe_excalidraw.py` both import from `indexer.index_card`); importing back from `notes/` here would introduce a cycle. Add the top-level import alongside this module's others:

```python
from common.academic_hub_paths import to_resources_root
```

```python
_EXCALIDRAW_IMAGE_EXTENSIONS = (".png", ".svg")


def _find_excalidraw_image(excalidraw_md_path: str, academic_hub_root: str) -> str | None:
    stem = excalidraw_md_path[: -len(".md")]
    for ext in _EXCALIDRAW_IMAGE_EXTENSIONS:
        local = stem + ext
        if os.path.exists(local):
            return local
    try:
        mirrored_stem = to_resources_root(stem)
    except ValueError:
        return None
    for ext in _EXCALIDRAW_IMAGE_EXTENSIONS:
        mirrored = mirrored_stem + ext
        if os.path.exists(mirrored):
            return mirrored
    return None
```

Thread `source_asset_path` through `_reconcile_one`:

```python
def _reconcile_one(academic_hub_root, course_name, folder_category, file_id, rel_path,
                    rel_pdf_path, content_sample, page_count, client, force, stats, source_mtime,
                    content_hash, known_doc_types=KNOWN_DOC_TYPES, source_asset_path=None):
    existing = None
    for c in load_shard(academic_hub_root, course_name):
        if c.get("file_id") == file_id:
            existing = c
            break

    stale = existing is not None and _is_stale(existing, source_mtime, content_hash)
    already_current = (
        existing is not None and not force and not stale
        and not existing.get("needs_indexing")
        and existing.get("path") == rel_path
    )
    if already_current:
        if existing.get("content_hash") is None:
            _backfill_content_hash(academic_hub_root, course_name, file_id, content_hash)
        stats["unchanged"] += 1
        return

    is_first_time = existing is None
    needs_retry = existing is not None and existing.get("needs_indexing")
    if (force or stale or needs_retry) and existing is not None:
        remaining = [c for c in load_shard(academic_hub_root, course_name) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, course_name, remaining)
        recompute_course_entry(academic_hub_root, course_name)

    reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_path, source_pdf_path=rel_pdf_path,
        course=course_name, folder_category=folder_category, content_sample=content_sample,
        page_count=page_count, client=client, content_hash=content_hash,
        known_doc_types=known_doc_types, source_asset_path=source_asset_path,
    )
    if is_first_time:
        stats["generated"] += 1
    elif existing is not None and existing.get("course") != course_name:
        stats["moved"] += 1
    else:
        stats["updated"] += 1
```

Add the new loop in `rebuild()`, right after the video-lecture-notes loop and before `_flag_or_prune_orphans`:

```python
    for course_name, category, md_path in _excalidraw_note_paths(academic_hub_root, course):
        base_name = os.path.basename(md_path)[: -len(".excalidraw.md")]
        rag_path = os.path.join(os.path.dirname(md_path), "processed_outputs", f"{base_name}.excalidraw.rag.md")
        if not os.path.exists(rag_path):
            continue  # not transcribed yet -- nothing to index
        if os.path.getsize(rag_path) == 0:
            print(f"WARNING: {rag_path} is empty (0 bytes) but its source .excalidraw.md exists -- "
                  f"skipping. It likely hasn't been transcribed yet.")
            stats["skipped_empty_md"] += 1
            continue

        file_id = compute_file_id(md_path)
        seen_file_ids.add(file_id)
        rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
        rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")

        with open(rag_path, "r", encoding="utf-8") as f:
            content_sample = f.read()

        image_path = _find_excalidraw_image(md_path, academic_hub_root)
        rel_image_path = (
            os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/") if image_path else None
        )

        _reconcile_one(academic_hub_root, course_name, category, file_id, rel_rag_path,
                       rel_md_path, content_sample, None, client, force, stats,
                       source_mtime=os.path.getmtime(rag_path),
                       content_hash=compute_content_hash(rag_path),
                       known_doc_types=EXCALIDRAW_DOC_TYPES, source_asset_path=rel_image_path)
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_index_search.py -v -k Excalidraw`
Expected: PASS (4 tests)

- [x] **Step 5: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (every test, including every other subproject's)

- [x] **Step 6: Commit**

```bash
git add indexer/index_search.py tests/test_index_search.py
git commit -m "fix(index): add rebuild() walker for Excalidraw notes, fixing a live orphaning bug"
```

---

### Task 4: `transcribe_notes.py` -- mirrored output dir and full source path

**Files:**
- Modify: `notes/transcribe_notes.py`
- Test: `tests/test_transcribe_notes.py`

**Interfaces:**
- Consumes: `resolve_output_dir` (Task 1), `reconcile_and_write(..., source_asset_path=...)` (Task 2).

**Note on scope:** `process_pdf()` itself has zero direct tests anywhere in this file today (confirmed: `grep -n "process_pdf" tests/test_transcribe_notes.py` returns nothing) -- it directly drives `pypdf`/PyMuPDF, and this project's own established convention (see `render_page_to_image_bytes`'s docstring) is to leave that class of function untested directly, verified instead via real-corpus runs. `_write_markdown_and_index()`, which `process_pdf()` calls at the end of every tier, *is* directly tested (`TestWriteMarkdownAndIndex`, by mocking `reconcile_and_write`) -- that's where this task's new `source_asset_path` behavior gets a real test. The `output_dir = resolve_output_dir(pdf_path)` line change inside `process_pdf()` itself gets no bespoke test here (consistent with the rest of that function); Task 7's real corpus dry-run and Task 9's real migration are its actual verification.

- [x] **Step 1: Write the failing test**

```python
# tests/test_transcribe_notes.py -- add to TestWriteMarkdownAndIndex
    def test_source_asset_path_is_forwarded_as_the_pdf_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = os.path.join(tmp, "out.md")
            pdf_path = os.path.join(tmp, "academic_notes", "math-camp", "ta_notes", "foo.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"fake pdf")

            with patch("notes.transcribe_notes.reconcile_and_write") as mock_reconcile:
                _write_markdown_and_index(
                    md_path=md_path, frontmatter="", final_md="content", pdf_path=pdf_path,
                    academic_hub_root=tmp, folder_category="ta_notes", total_pages=3, client=MagicMock(),
                )
            rel_pdf_path = os.path.relpath(pdf_path, tmp).replace(os.sep, "/")
            self.assertEqual(mock_reconcile.call_args.kwargs["source_asset_path"], rel_pdf_path)
            self.assertEqual(mock_reconcile.call_args.kwargs["source_pdf_path"], rel_pdf_path)
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_notes.py -v -k source_asset_path`
Expected: FAIL -- `KeyError: 'source_asset_path'` (the kwarg doesn't exist on the call yet).

- [x] **Step 3: Write minimal implementation**

Add the import:

```python
from common.academic_hub_paths import resolve_output_dir
```

In `process_pdf`, replace:

```python
    output_dir = os.path.join(os.path.dirname(pdf_path), "processed_outputs")
```

with:

```python
    output_dir = resolve_output_dir(pdf_path)
```

In the same function, replace the `base_metadata` construction:

```python
    base_metadata = {
        "source_pdf": os.path.basename(pdf_path),
        "folder_category": folder_category,
        "total_pages": total_pages,
    }
```

with:

```python
    base_metadata = {
        "source_pdf": os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/"),
        "folder_category": folder_category,
        "total_pages": total_pages,
    }
```

In `_write_markdown_and_index`, thread `source_asset_path` through to `reconcile_and_write` (it's always the same value as `source_pdf_path` for a PDF-sourced card -- explicit, not implicit, per the design spec):

```python
def _write_markdown_and_index(md_path, frontmatter, final_md, pdf_path, academic_hub_root,
                               folder_category, total_pages, client, known_doc_types=KNOWN_DOC_TYPES):
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
        )
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {md_path} ({err}); "
              f"rerun `python index_search.py rebuild` later to catch it up.")
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_notes.py -v`
Expected: PASS (full file, no regressions -- every existing test still puts its fixture PDF under `academic_notes/` or a bare tmp dir with no `academic_resources` segment, so `resolve_output_dir` falls through to the unchanged sibling behavior for all of them)

- [x] **Step 5: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add notes/transcribe_notes.py tests/test_transcribe_notes.py
git commit -m "feat(notes): resolve PDF output dir via the mirroring convention, not a hardcoded sibling"
```

---

### Task 5: `transcribe_excalidraw.py` -- image fallback lookup and full source paths

**Files:**
- Modify: `notes/transcribe_excalidraw.py`
- Test: `tests/test_transcribe_excalidraw.py`

**Interfaces:**
- Consumes: `to_resources_root`, `resolve_output_dir` (Task 1), `reconcile_and_write(..., source_asset_path=...)` (Task 2).

- [x] **Step 1: Write the failing test**

```python
# tests/test_transcribe_excalidraw.py -- add near existing discover_excalidraw_files tests
def test_discover_excalidraw_files_falls_back_to_the_mirrored_resources_directory(tmp_path):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    # no local image sibling -- it's already been migrated

    resources_dir = tmp_path / "academic_resources" / "econometrics" / "lecture_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert len(pairs) == 1
    assert pairs[0][1] == str(resources_dir / "Drawing.excalidraw.svg")


def test_discover_excalidraw_files_prefers_local_image_over_mirrored_one(tmp_path):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    (notes_dir / "Drawing.excalidraw.svg").write_text("<svg>local</svg>")

    resources_dir = tmp_path / "academic_resources" / "econometrics" / "lecture_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "Drawing.excalidraw.svg").write_text("<svg>mirrored</svg>")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert pairs[0][1] == str(notes_dir / "Drawing.excalidraw.svg")


def test_discover_excalidraw_files_still_skips_when_no_image_anywhere(tmp_path, capsys):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert pairs == []
    assert "no matching .png/.svg" in capsys.readouterr().out.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v -k mirrored`
Expected: FAIL -- the first two tests get `pairs == []` (no fallback lookup exists yet).

- [x] **Step 3: Write minimal implementation**

Add the import:

```python
from common.academic_hub_paths import resolve_output_dir, to_resources_root
```

Replace `discover_excalidraw_files`:

```python
def discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]:
    """Finds every `.excalidraw.md` directly under notes_dir with a
    matching `.excalidraw.png` or `.excalidraw.svg` sibling (the plugin's
    auto-export) -- checked locally first, then in the mirrored
    academic_resources/ location (the post-migration case; see
    docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md).
    Skips (with a warning, not an error) any .md with no image found in
    either location."""
    if not os.path.isdir(notes_dir):
        return []
    pairs = []
    for name in sorted(os.listdir(notes_dir)):
        if not name.lower().endswith(".excalidraw.md"):
            continue
        if file_filter is not None and name != file_filter:
            continue
        md_path = os.path.join(notes_dir, name)
        stem = md_path[: -len(".md")]
        image_path = next((stem + ext for ext in _EXPORT_EXTENSIONS if os.path.exists(stem + ext)), None)
        if image_path is None:
            try:
                mirrored_stem = to_resources_root(stem)
            except ValueError:
                mirrored_stem = None
            if mirrored_stem is not None:
                image_path = next(
                    (mirrored_stem + ext for ext in _EXPORT_EXTENSIONS if os.path.exists(mirrored_stem + ext)),
                    None,
                )
        if image_path is None:
            print(f"WARNING: {name} has no matching .png/.svg (auto-export may not have run yet) -- skipping.")
            continue
        pairs.append((md_path, image_path))
    return pairs
```

In `write_outputs`, replace the output-dir line:

```python
    output_dir = os.path.join(os.path.dirname(excalidraw_md_path), "processed_outputs")
```

with:

```python
    output_dir = resolve_output_dir(excalidraw_md_path)
```

(a no-op change in practice, since `excalidraw_md_path` never lives under `academic_resources/` -- included for consistency and so this function stops hand-rolling a convention that now lives in one place.)

Replace `common_meta`'s two source fields (bare filenames -> full relative paths) and add `source_asset_path` to the `reconcile_and_write` call:

```python
    common_meta = {
        "source_excalidraw": os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/"),
        "source_image": os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/"),
        "folder_category": "excalidraw_notes",
        "routing": "excalidraw_chunked",
        "chunks": num_chunks,
        "model": transcription_model,
        "tags": [],
    }
```

```python
    try:
        file_id = compute_file_id(excalidraw_md_path)
        rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
        rel_source_path = os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/")
        rel_image_path = os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_source_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_rag_path, source_pdf_path=rel_source_path,
            course=course, folder_category="excalidraw_notes", content_sample=expanded_markdown,
            page_count=num_chunks, client=client, content_hash=compute_content_hash(rag_path),
            known_doc_types=EXCALIDRAW_DOC_TYPES, source_asset_path=rel_image_path,
        )
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {rag_path} ({err}); "
              f"rerun `python -m indexer.index_search rebuild` later to catch it up.")
```

- [x] **Step 4: Update the two pre-existing tests that assert a bare-filename `source_image`**

`test_write_outputs_creates_both_files_with_frontmatter` (asserts
`"source_image: Drawing 2026-09-08.excalidraw.png" in raw_content`) and
`test_write_outputs_records_svg_source_filename` (asserts
`"source_image: Econometrics 2026-09-09.excalidraw.svg" in raw_content`)
both currently expect a bare filename -- `write_outputs` now writes the
path relative to `academic_hub_root` instead. In both tests, the fixture
already places the image under `course_dir` (itself under
`tmp_path / "academic-hub" / "academic_notes" / ...`), so the new expected
value is that same relative path. Update:

```python
# test_write_outputs_creates_both_files_with_frontmatter
    assert "source_image: academic_notes/math_methods/lecture_notes/Drawing 2026-09-08.excalidraw.png" in raw_content
```

```python
# test_write_outputs_records_svg_source_filename
    assert "source_image: academic_notes/econometrics/lecture_notes/Econometrics 2026-09-09.excalidraw.svg" in raw_content
```

- [x] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_transcribe_excalidraw.py -v`
Expected: PASS (full file)

- [x] **Step 6: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS

- [x] **Step 7: Commit**

```bash
git add notes/transcribe_excalidraw.py tests/test_transcribe_excalidraw.py
git commit -m "feat(excalidraw): fall back to the mirrored academic_resources/ location for the image sibling"
```

---

### Task 6: `route_notes_transcribe.py` -- discover PDFs under `academic_resources/` too

**Files:**
- Modify: `notes/route_notes_transcribe.py`
- Test: `tests/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `discover_pdf_files` (existing, from `notes.transcribe_notes`), `discover_excalidraw_files` (existing, now with Task 5's fallback baked in -- no changes needed here for the Excalidraw side).
- Produces: `discover_pdf_sources(course_dir: str) -> list[str]` now also finds PDFs under the mirrored `academic_resources/` category.

- [x] **Step 1: Write the failing test**

```python
# tests/test_route_notes_transcribe.py -- add near existing discover_pdf_sources tests
def test_discover_pdf_sources_also_finds_pdfs_migrated_to_academic_resources(tmp_path):
    # academic_notes/<course>/ta_notes/ exists (even if empty of PDFs) --
    # that's what makes academic_resources/<course>/ta_notes/ eligible.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_pdf_sources_ignores_academic_resources_categories_with_no_notes_counterpart(tmp_path):
    # academic_resources/<course>/textbooks/ has no academic_notes/<course>/textbooks/
    # counterpart -- must stay out of scope (that's convert_textbook.py's
    # pipeline, not transcribe_notes.py's).
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    textbooks_dir = tmp_path / "academic_resources" / "econometrics" / "textbooks"
    textbooks_dir.mkdir(parents=True)
    (textbooks_dir / "Hansen.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert paths == []


def test_discover_pdf_sources_combines_notes_and_resources_pdfs(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    (ta_dir / "not-yet-migrated.pdf").write_bytes(b"x")
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "already-migrated.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert sorted(os.path.basename(p) for p in paths) == ["already-migrated.pdf", "not-yet-migrated.pdf"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_route_notes_transcribe.py -v -k academic_resources`
Expected: FAIL -- `discover_pdf_sources` currently only walks the `academic_notes/` tree it's given, so every `academic_resources/`-only PDF is invisible.

- [x] **Step 3: Write minimal implementation**

In `notes/route_notes_transcribe.py`, replace `discover_pdf_sources`:

```python
def discover_pdf_sources(course_dir: str) -> list[str]:
    paths = []
    for dirpath in _walk_content_dirs(course_dir):
        paths.extend(discover_pdf_files(dirpath))
    paths.extend(_discover_migrated_pdf_sources(course_dir))
    return paths


def _discover_migrated_pdf_sources(course_dir: str) -> list[str]:
    """PDFs already moved to academic_resources/<course>/<category>/ --
    only descends into a category that also exists directly under
    academic_notes/<course>/, so academic_resources/<course>/textbooks/
    (a completely different pipeline's home, with no academic_notes/
    counterpart) never gets swept in by accident."""
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        return []
    if not os.path.isdir(resources_course_dir):
        return []
    notes_categories = {
        name for name in os.listdir(course_dir) if os.path.isdir(os.path.join(course_dir, name))
    }
    paths = []
    for category in sorted(os.listdir(resources_course_dir)):
        if category not in notes_categories:
            continue
        category_dir = os.path.join(resources_course_dir, category)
        if not os.path.isdir(category_dir):
            continue
        paths.extend(discover_pdf_files(category_dir))
    return paths
```

Add the import:

```python
from common.academic_hub_paths import to_resources_root
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_route_notes_transcribe.py -v`
Expected: PASS (full file)

- [x] **Step 5: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add notes/route_notes_transcribe.py tests/test_route_notes_transcribe.py
git commit -m "feat(notes): route_notes_transcribe discovers PDFs already migrated to academic_resources/"
```

---

### Task 7: Real dry-run against the live corpus (no writes, no moves)

Verification-only task -- confirms Tasks 1-6 haven't broken anything real, using the exact same real corpus this session already validated the Excalidraw fix against. No code changes.

- [x] **Step 1: Run the router's dry-run against the full real corpus**

Run (from `academic-rag-model/`): `.venv/Scripts/python.exe -m notes.route_notes_transcribe --dry-run`
Expected: identical `PDF: 67 to process, 21 already done` / `Excalidraw: 1 to process, 8 already done` summary this session already produced and validated (nothing under `academic_resources/` has moved yet, so every discovery path should fall through to its pre-Task-6 behavior byte-for-byte).

- [x] **Step 2: Run rebuild in dry-adjacent mode against a scratch copy, confirm the orphan fix**

Reuse the NTFS-junction technique from the design spec's "Verified, not assumed" section (copy `.index/`, junction-link `academic_notes/`+`academic_resources/` to the real directories, never touch the real `.index/`). Run `rebuild(scratch_root, client=<a client whose every method raises AssertionError>, course="econometrics", force=False, prune=False)`. Expected: `stats["orphaned"] == 0` this time (compare against the `orphaned: 4` result recorded in the design spec, from before Task 3 existed).

- [x] **Step 3: Record results**

Add a short dated entry to `docs/status/2026-08-24-notes-transcription-status.md` (or a new tracker entry, matching this project's existing convention) noting: Tasks 1-6 verified against the real corpus with zero behavior change pre-migration, and the rebuild orphan bug confirmed fixed. No commit needed for this task beyond the doc update -- fold it into Task 8's commit if Task 8 follows immediately, or commit standalone otherwise.

---

### Task 8: Folder vocabulary unification -- underscores everywhere

**Added 2026-09-21, folded in from a concurrent session's brainstorm** --
see `docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md`'s
addendum section. Both trees currently mix hyphens and underscores for
what should be the same course/category. User's decision: underscores
everywhere, matching the majority already in `academic_notes/` (`ta_notes`,
`problem_sets`, `study_plan`, `cheat_sheet`, `handwritten_notes`,
`professor_notes`). This must land *before* Task 10's real migration --
not because any code in Tasks 1-7 assumes a specific category name (it
doesn't; `to_resources_root`/`to_notes_root` only ever match the literal
`academic_notes`/`academic_resources` root segment), but because a
mismatched *course* name between the two trees (`math-methods` vs.
`math_methods`) makes the mirrored-path convention resolve to a
nonexistent path for that course until the rename lands.

**This is a real-corpus survey + rename task, not a code task** -- no new
source files, no new tests. The known renames from the original brainstorm
(math-camp-focused, needs re-verification against every course):

- `academic_resources/math-methods/` -> `academic_resources/math_methods/`
- `academic_resources/<course>/lecture-slides/` -> `lecture_slides/`
  (wherever present)
- `academic_resources/<course>/lecture-recordings/` -> `lecture_recordings/`
  (wherever present)
- `academic_notes/math-camp/lecture-notes/` -> `lecture_notes/` (the one
  outlier vs. every other course's `lecture_notes`)

- [ ] **Step 1: Survey every course under both `academic_notes/` and
  `academic_resources/`** for hyphenated directory names (course-level and
  category-level), not just math-camp. A one-off script or manual
  `Get-ChildItem -Recurse -Directory | Where-Object Name -match '-'`
  against the real `academic-hub/` root is sufficient -- this doesn't need
  to be committed code, just a real inventory to confirm the rename list
  above is complete before executing it.

- [ ] **Step 2: Confirm the full rename list with the user** before
  touching any real directory -- same explicit-confirmation bar as Task 10,
  since renaming a course directory that any other tool (Obsidian, Direct
  Git Sync, the vault repo) references by its current name has its own
  blast radius independent of this plan's own code.

- [ ] **Step 3: Execute the renames for real** (`git mv` where the
  directory is git-tracked under `academic_resources/`'s parent repo;
  plain filesystem rename for anything inside the separately-repo'd
  `academic_notes` vault) once confirmed.

- [ ] **Step 4: Re-run the Task 7 verification** (`route_notes_transcribe
  --dry-run` equivalent, and the isolated-copy `rebuild()` check) against
  the real corpus post-rename, to confirm nothing broke and no course
  silently dropped out of discovery due to a missed rename.

---

### Task 9: Migration script

**Files:**
- Create: `notes/migrate_sources_to_resources.py`
- Test: `tests/test_migrate_sources_to_resources.py`

**Interfaces:**
- Consumes: `to_resources_root` (Task 1), `rebuild` (from `indexer.index_search`, Task 3's fixed version).
- Produces: `find_migration_candidates(academic_hub_root: str, course: str | None = None) -> list[tuple[str, str]]` -- list of `(current_path, target_path)` pairs (PDFs, `.docx`/`.pptx`, and Excalidraw images still under `academic_notes/`, the latter next to their `.md`). `migrate_one(current_path: str, target_path: str, dry_run: bool = False) -> None`. `main()`.

**Scope note (2026-09-21 addendum):** `.docx`/`.pptx` are in scope per the
user's decision -- purely mechanical, no code anywhere in `notes/`/
`indexer/` hardcodes a path to either extension, so this only needs to
extend the discovery filter below, not touch anything downstream (no
output-dir resolution, no indexing -- those only apply to PDF/Excalidraw
sources).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migrate_sources_to_resources.py
import os

from notes.migrate_sources_to_resources import find_migration_candidates, migrate_one


def test_find_migration_candidates_finds_an_unmigrated_pdf(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path))

    assert len(candidates) == 1
    current, target = candidates[0]
    assert current == str(pdf_path)
    assert target == str(tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf")


def test_find_migration_candidates_finds_an_unmigrated_excalidraw_image(tmp_path):
    lecture_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    svg_path = lecture_dir / "Drawing.excalidraw.svg"
    svg_path.write_text("<svg></svg>")

    candidates = find_migration_candidates(str(tmp_path))

    assert len(candidates) == 1
    current, target = candidates[0]
    assert current == str(svg_path)
    assert target == str(tmp_path / "academic_resources" / "econometrics" / "lecture_notes" / "Drawing.excalidraw.svg")


def test_find_migration_candidates_finds_docx_and_pptx(tmp_path):
    # 2026-09-21 addendum: docx/pptx are in scope too, purely mechanical --
    # no downstream code reads them, so this is the only thing that needs
    # to know about them.
    study_dir = tmp_path / "academic_notes" / "math-camp" / "study_plan"
    study_dir.mkdir(parents=True)
    (study_dir / "Prep Schedule.docx").write_bytes(b"x")
    (study_dir / "Overview.pptx").write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path))

    names = sorted(os.path.basename(c) for c, _t in candidates)
    assert names == ["Overview.pptx", "Prep Schedule.docx"]


def test_find_migration_candidates_skips_a_pdf_already_migrated(tmp_path):
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "foo.pdf").write_bytes(b"x")

    assert find_migration_candidates(str(tmp_path)) == []


def test_find_migration_candidates_respects_course_filter(tmp_path):
    for course in ("econometrics", "microecon"):
        d = tmp_path / "academic_notes" / course / "ta_notes"
        d.mkdir(parents=True)
        (d / "foo.pdf").write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path), course="econometrics")

    assert len(candidates) == 1
    assert "econometrics" in candidates[0][0]


def test_migrate_one_moves_the_file_and_creates_target_dirs(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"real bytes")
    target = tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf"

    migrate_one(str(pdf_path), str(target))

    assert not pdf_path.exists()
    assert target.read_bytes() == b"real bytes"


def test_migrate_one_dry_run_does_not_touch_the_filesystem(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"real bytes")
    target = tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf"

    migrate_one(str(pdf_path), str(target), dry_run=True)

    assert pdf_path.exists()
    assert not target.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_migrate_sources_to_resources.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'notes.migrate_sources_to_resources'`

- [ ] **Step 3: Write minimal implementation**

```python
# notes/migrate_sources_to_resources.py
"""
migrate_sources_to_resources.py
One-shot migration: moves heavy note sources (PDFs, Excalidraw
.svg/.png exports) from academic_notes/ to academic_resources/, mirroring
each file's <course>/<category>/<filename> relative path. Never moves a
.excalidraw.md scene file or anything under processed_outputs/ -- those
stay in academic_notes/ by design (see
docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md).
After moving files, calls index_search.rebuild() so every affected card's
source_pdf_path/source_asset_path gets refreshed via its existing cheap
"file moved, content unchanged" reconciliation -- no LLM call in the
common case.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from common.academic_hub_paths import to_resources_root

_EXCALIDRAW_IMAGE_EXTENSIONS = (".png", ".svg")
# 2026-09-21 addendum: docx/pptx are in scope too (user decision) -- purely
# mechanical, no downstream code reads them from their new location, so
# they only need to be included in this filter, nothing else.
_MECHANICAL_EXTENSIONS = (".docx", ".pptx")


def find_migration_candidates(academic_hub_root: str, course: str | None = None) -> list[tuple[str, str]]:
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return []
    candidates: list[tuple[str, str]] = []
    for course_name in sorted(os.listdir(notes_root)):
        if course and course_name != course:
            continue
        course_dir = os.path.join(notes_root, course_name)
        if not os.path.isdir(course_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir):
            dirnames[:] = [d for d in dirnames if d != "processed_outputs" and not d.startswith(".")]
            for name in sorted(filenames):
                lower = name.lower()
                is_pdf = lower.endswith(".pdf")
                is_excalidraw_image = any(lower.endswith(f".excalidraw{ext}") for ext in _EXCALIDRAW_IMAGE_EXTENSIONS)
                is_mechanical = lower.endswith(_MECHANICAL_EXTENSIONS)
                if not (is_pdf or is_excalidraw_image or is_mechanical):
                    continue
                current_path = os.path.join(dirpath, name)
                target_path = to_resources_root(current_path)
                candidates.append((current_path, target_path))
    return candidates


def migrate_one(current_path: str, target_path: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  would move: {current_path} -> {target_path}")
        return
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.move(current_path, target_path)
    print(f"  moved: {current_path} -> {target_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Move heavy note sources (PDFs, Excalidraw .svg/.png exports) from "
                    "academic_notes/ to academic_resources/, then resync the source index."
    )
    parser.add_argument("--course", default=None, help="Limit to this course. Default: every course.")
    parser.add_argument("--dry-run", action="store_true", help="List what would move without touching anything.")
    parser.add_argument("--no-reindex", action="store_true", help="Skip the rebuild() call after moving files.")
    args = parser.parse_args()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    candidates = find_migration_candidates(str(academic_hub_dir), course=args.course)
    if not candidates:
        print("Nothing to migrate.")
        return

    print(f"{len(candidates)} file(s) to migrate.")
    for current_path, target_path in candidates:
        migrate_one(current_path, target_path, dry_run=args.dry_run)

    if args.dry_run:
        return

    if args.no_reindex:
        print("Skipping reindex (--no-reindex). Run `python -m indexer.index_search rebuild` when ready.")
        return

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    from indexer.index_search import rebuild
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        print("WARNING: could not get a Gemini client; skipping reindex. "
              "Run `python -m indexer.index_search rebuild` by hand.")
        sys.exit(1)
    stats = rebuild(str(academic_hub_dir), client, course=args.course)
    print(f"Reindex complete: {stats}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_migrate_sources_to_resources.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (every test, this plan's full scope)

- [ ] **Step 6: Commit**

```bash
git add notes/migrate_sources_to_resources.py tests/test_migrate_sources_to_resources.py
git commit -m "feat(notes): add migration script for relocating heavy sources to academic_resources/"
```

---

### Task 10: Real migration -- explicit go/no-go checkpoint

**Not a code task.** Everything above is built and verified against synthetic fixtures plus a real, read-only dry-run (Task 7). This task is the actual physical move against the user's real corpus, and must not proceed without the user explicitly confirming at this exact point -- both because it touches ~90 real files across every course, and because the `academic_notes` vault repo had its git history rewritten this same week (per `docs/status/2026-09-21-obsidian-git-sync-status.md`).

**Prerequisite order (2026-09-21 addendum):** Task 8 (vocabulary rename)
must land first -- a mismatched course/category name between the two
trees would make this task's `to_resources_root` resolution silently miss
files. The math-camp duplicate-PDF cleanup (delete
`academic_resources/math-camp/lecture-slides/`'s byte-identical copies
after the rename lands `ta_notes` as the canonical category) is a small
data-cleanup step that fits naturally as Step 0 below, before the general
migration runs.

- [ ] **Step 0: Math-camp duplicate cleanup** (only after Task 8's rename
  lands `ta_notes`/`lecture_slides` as the unified names): confirm with the
  user, then delete the 6 byte-identical PDFs under
  `academic_resources/math-camp/lecture_slides/` (verify each is still
  byte-identical to its `academic_notes/math-camp/ta_notes/2025/`
  counterpart immediately before deleting, in case anything changed since
  the original brainstorm's hash check) -- the `academic_notes/` originals
  migrate normally through Step 3 below, no special-casing needed there.
- [ ] **Step 1: Confirm with the user** which courses to migrate first (all at once, or one course as a trial -- econometrics is a reasonable first candidate, being the smallest and most recently validated).
- [ ] **Step 2: Dry run for real**: `python -m notes.migrate_sources_to_resources --course econometrics --dry-run`, review the full candidate list with the user before proceeding.
- [ ] **Step 3: Run for real**: `python -m notes.migrate_sources_to_resources --course econometrics`, then verify with `python -m notes.route_notes_transcribe --dry-run` that nothing looks newly "to process" that shouldn't be, and spot-check that `source_asset_path` on a few real cards now points at the new `academic_resources/` location.
- [ ] **Step 4: Commit** the moved files in whichever repo(s) they now live in (the main sandbox repo for `academic_resources/`, the vault repo for whatever `academic_notes/` changes result) -- following this session's established pattern of explicit per-repo confirmation before any push.
