# Prior-Offering Subset Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `route_notes_transcribe.py` discover PDFs (and Excalidraw scenes) nested at any depth under a marker-tagged subdirectory of `academic_resources/<course>/`, so a whole prior course offering can be transcribed into the existing course without flattening its folder structure or pre-registering category names.

**Architecture:** Add a new, purely additive discovery path alongside the two that already exist in `route_notes_transcribe.py` (the recursive `academic_notes/`-side walk, and the flat category-match-gated `academic_resources/`-side sweep). The new path recognizes a `.notes_subset.json` marker file as an opt-in signal, then recursively walks everything beneath it (pruning `processed_outputs/`, hidden dirs, and textbook folders), reusing the existing flat `discover_pdf_files`/`discover_excalidraw_files` primitives per directory. Nothing downstream of discovery changes — `resolve_output_dir`, `derive_course`, and `folder_category` are already depth-agnostic.

**Tech Stack:** Python 3.13, stdlib only (`os`, `json`), `pytest` with `tmp_path` fixtures — no new dependencies.

**Spec:** `ai-sandbox/academic-rag-model/docs/superpowers/specs/transcribe_notes/2026-10-03-notes-subset-discovery-design.md`

## Global Constraints

- All changes confined to `pipelines/transcribe_notes/route_notes_transcribe.py` and its test file — the spec confirms no other module needs changes.
- No new third-party dependencies; marker parsing uses stdlib `json`.
- A malformed or missing marker file must never raise — treat as "not marked," print a warning, continue the run (unattended-safe).
- Every new function gets a test in `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`, following that file's existing style (`_make_course` helper, `tmp_path`, plain assertions — no mocking of the filesystem).
- Run the full existing test file after each task, not just the new test, to catch regressions in the two untouched discovery paths early.

## Review Focus

- A malformed `.notes_subset.json` (invalid JSON) crashes the whole course's discovery instead of being skipped with a warning.
- A `textbooks`-named directory nested inside a marked subset leaks textbook PDFs into notes transcription (the category-match gate that used to prevent this doesn't apply to this new path).
- A marker placed somewhere that overlaps the existing flat migrated-category sweep causes the same PDF to appear twice in `pdf_todo` and get processed twice in one run.
- An already-transcribed PDF under a marked subset gets re-transcribed on a second run because `resolve_output_dir`/`filter_unprocessed_pdfs` don't actually hold up at depth in practice (confirms the spec's depth-agnostic claim with a real end-to-end test, not just code reading).
- A marker file placed on the wrong side (`academic_notes/` instead of `academic_resources/`) silently does nothing rather than raising a confusing error — must stay a quiet no-op, not a crash.

---

### Task 1: Marker file reading and `find_subset_roots`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py:19-35` (add `import json`, add `_SUBSET_MARKER_FILENAME` constant)
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py` (insert new functions after `_discover_migrated_pdf_sources`, currently ending at line 90)
- Test: `ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: nothing new (stdlib `os`, `json` only).
- Produces: `_read_subset_marker(dir_path: str) -> dict | None` and `find_subset_roots(resources_course_dir: str) -> list[str]`, both used by Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`:

```python
import json

from pipelines.transcribe_notes.route_notes_transcribe import (
    find_subset_roots,
)


def test_find_subset_roots_finds_a_marked_directory(tmp_path):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == [str(resources_dir)]


def test_find_subset_roots_ignores_unmarked_directories(tmp_path):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / "some.pdf").write_bytes(b"x")  # no marker file

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []


def test_find_subset_roots_does_not_search_for_nested_markers_inside_a_claimed_root(tmp_path):
    outer = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    inner = outer / "Class Notes"
    inner.mkdir(parents=True)
    (outer / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (inner / ".notes_subset.json").write_text(json.dumps({"label": "nested-should-be-ignored"}))

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == [str(outer)]


def test_find_subset_roots_skips_malformed_marker_with_a_warning(tmp_path, capsys):
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text("{not valid json")

    roots = find_subset_roots(str(tmp_path / "academic_resources" / "econometrics"))

    assert roots == []
    assert "WARNING" in capsys.readouterr().out


def test_find_subset_roots_returns_empty_for_missing_resources_dir(tmp_path):
    assert find_subset_roots(str(tmp_path / "academic_resources" / "nonexistent")) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k find_subset_roots -v`
Expected: FAIL (ImportError / `find_subset_roots` not defined)

- [ ] **Step 3: Implement**

In `route_notes_transcribe.py`, change the import block (lines 21-23) to:

```python
import argparse
import json
import os
import sys
```

Change the constant line (line 35) to:

```python
_SKIP_DIR_NAMES = frozenset({"processed_outputs"})
_SUBSET_MARKER_FILENAME = ".notes_subset.json"
```

Insert after `_discover_migrated_pdf_sources` (after its closing `return paths` at line 90):

```python
def _read_subset_marker(dir_path: str) -> dict | None:
    """Reads this directory's subset marker, if any. Returns None for a
    missing file (not marked) or a malformed one (logged, treated as not
    marked) -- never raises, so one bad marker can't take down discovery
    for the rest of the course."""
    marker_path = os.path.join(dir_path, _SUBSET_MARKER_FILENAME)
    if not os.path.isfile(marker_path):
        return None
    try:
        with open(marker_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as err:
        print(f"WARNING: malformed subset marker, ignoring: {marker_path} ({err})")
        return None


def find_subset_roots(resources_course_dir: str) -> list[str]:
    """Recursively finds every directory under resources_course_dir whose
    own root holds a valid _SUBSET_MARKER_FILENAME. Once a root is found,
    stops looking for further nested markers inside it -- one marker
    claims its whole subtree, no stacking."""
    if not os.path.isdir(resources_course_dir):
        return []
    roots = []
    for dirpath, dirnames, _filenames in os.walk(resources_course_dir):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES and not d.startswith(".")]
        if _read_subset_marker(dirpath) is not None:
            roots.append(dirpath)
            dirnames[:] = []  # claimed -- don't search inside for nested markers
    return sorted(roots)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k find_subset_roots -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full test file to check for regressions**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: all existing tests still PASS (no behavior changed yet in `discover_pdf_sources`/`discover_excalidraw_sources`)

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): add .notes_subset.json marker discovery"
```

---

### Task 2: `_walk_marked_subset` recursive walk with textbook exclusion

**Files:**
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py` (insert after `find_subset_roots`)
- Test: `ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `_SKIP_DIR_NAMES`, `TEXTBOOK_FOLDER_NAMES` (already imported at module top).
- Produces: `_walk_marked_subset(subset_root: str)` — a generator yielding every directory under `subset_root`, used by Task 3.

- [ ] **Step 1: Write the failing tests**

```python
from pipelines.transcribe_notes.route_notes_transcribe import _walk_marked_subset


def test_walk_marked_subset_yields_nested_directories(tmp_path):
    root = tmp_path / "class_2024"
    deep = root / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(deep) in dirs
    assert str(root / "Class Notes") in dirs
    assert str(root) in dirs


def test_walk_marked_subset_prunes_processed_outputs_and_hidden_dirs(tmp_path):
    root = tmp_path / "class_2024"
    (root / "processed_outputs").mkdir(parents=True)
    (root / ".obsidian").mkdir(parents=True)
    (root / "Slides").mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(root / "processed_outputs") not in dirs
    assert str(root / ".obsidian") not in dirs
    assert str(root / "Slides") in dirs


def test_walk_marked_subset_prunes_textbook_folders_at_any_depth(tmp_path):
    root = tmp_path / "class_2024"
    textbooks_dir = root / "Readings" / "textbooks"
    textbooks_dir.mkdir(parents=True)

    dirs = list(_walk_marked_subset(str(root)))

    assert str(textbooks_dir) not in dirs
    assert str(root / "Readings") in dirs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k walk_marked_subset -v`
Expected: FAIL (`_walk_marked_subset` not defined)

- [ ] **Step 3: Implement**

Insert after `find_subset_roots`:

```python
def _walk_marked_subset(subset_root: str):
    """Yields every directory under subset_root, pruning processed_outputs/,
    hidden directories, and any TEXTBOOK_FOLDER_NAMES-named directory at
    any depth -- the same invariant _discover_migrated_pdf_sources
    enforces via its category-match gate, needed here directly since that
    gate doesn't apply to this path."""
    for dirpath, dirnames, _filenames in os.walk(subset_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in _SKIP_DIR_NAMES and d not in TEXTBOOK_FOLDER_NAMES and not d.startswith(".")
        ]
        yield dirpath
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k walk_marked_subset -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full test file to check for regressions**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): add recursive walk for marked subset trees"
```

---

### Task 3: `discover_marked_subset_pdf_sources` and `discover_marked_subset_excalidraw_sources`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py` (insert after `_walk_marked_subset`)
- Test: `ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `find_subset_roots(resources_course_dir: str) -> list[str]` (Task 1), `_walk_marked_subset(subset_root: str)` (Task 2), `discover_pdf_files(notes_dir, file_filter=None) -> list[str]` and `discover_excalidraw_files(notes_dir, file_filter=None) -> list[tuple[str, str]]` (both already imported at module top).
- Produces: `discover_marked_subset_pdf_sources(resources_course_dir: str) -> list[str]` and `discover_marked_subset_excalidraw_sources(resources_course_dir: str) -> list[tuple[str, str]]`, both used by Task 4.

- [ ] **Step 1: Write the failing tests**

```python
from pipelines.transcribe_notes.route_notes_transcribe import (
    discover_marked_subset_excalidraw_sources,
    discover_marked_subset_pdf_sources,
)


def test_discover_marked_subset_pdf_sources_finds_pdfs_at_arbitrary_depth(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    subset = resources_econ / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")
    (subset / "2023exam1.pdf").write_bytes(b"x")  # loose file directly under the marked root

    paths = discover_marked_subset_pdf_sources(str(resources_econ))

    names = sorted(os.path.basename(p) for p in paths)
    assert names == ["090424.pdf", "2023exam1.pdf"]


def test_discover_marked_subset_pdf_sources_ignores_unmarked_siblings(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    unmarked = resources_econ / "class_2023"
    unmarked.mkdir(parents=True)
    (unmarked / "old.pdf").write_bytes(b"x")

    paths = discover_marked_subset_pdf_sources(str(resources_econ))

    assert paths == []


def test_discover_marked_subset_excalidraw_sources_finds_pairs_at_depth(tmp_path):
    resources_econ = tmp_path / "academic_resources" / "econometrics"
    subset = resources_econ / "class_2024"
    deep = subset / "Scanned Canvases"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "Drawing.excalidraw.md").write_text("---\n---\n")
    (deep / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_marked_subset_excalidraw_sources(str(resources_econ))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k discover_marked_subset -v`
Expected: FAIL (names not defined)

- [ ] **Step 3: Implement**

Insert after `_walk_marked_subset`:

```python
def discover_marked_subset_pdf_sources(resources_course_dir: str) -> list[str]:
    paths = []
    for subset_root in find_subset_roots(resources_course_dir):
        for dirpath in _walk_marked_subset(subset_root):
            paths.extend(discover_pdf_files(dirpath))
    return paths


def discover_marked_subset_excalidraw_sources(resources_course_dir: str) -> list[tuple[str, str]]:
    pairs = []
    for subset_root in find_subset_roots(resources_course_dir):
        for dirpath in _walk_marked_subset(subset_root):
            pairs.extend(discover_excalidraw_files(dirpath))
    return pairs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k discover_marked_subset -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full test file to check for regressions**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): discover PDFs and Excalidraw pairs in marked subsets"
```

---

### Task 4: Wire into `discover_pdf_sources`/`discover_excalidraw_sources`, with dedup

**Files:**
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py:58-63` (`discover_pdf_sources`)
- Modify: `ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py:93-97` (`discover_excalidraw_sources`)
- Test: `ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`

**Interfaces:**
- Consumes: `discover_marked_subset_pdf_sources`, `discover_marked_subset_excalidraw_sources` (Task 3), `to_resources_root` (already imported at module top).
- Produces: updated `discover_pdf_sources(course_dir: str) -> list[str]` and `discover_excalidraw_sources(course_dir: str) -> list[tuple[str, str]]` — same signatures as today, now including marked-subset results, deduplicated. This is the public surface `build_plan` (and therefore `main()`) already calls, so no caller changes needed anywhere.

- [ ] **Step 1: Write the failing tests**

```python
def test_discover_pdf_sources_includes_marked_subset_at_depth(tmp_path):
    # academic_notes/econometrics/ta_notes/ already exists from normal use;
    # the marked subset sits alongside it in academic_resources/, under a
    # brand-new "class_2024" name with no academic_notes/ counterpart --
    # exactly the case _discover_migrated_pdf_sources can't handle.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["090424.pdf"]


def test_discover_pdf_sources_does_not_duplicate_pdfs_seen_by_both_paths(tmp_path):
    # Pathological but guarded-against case: a marker placed directly
    # inside a category that's also eligible for the existing flat
    # migrated-category sweep must not cause double processing.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / ".notes_subset.json").write_text(json.dumps({"label": "overlap"}))
    (resources_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_pdf_sources_ignores_marker_placed_on_the_notes_side(tmp_path):
    # The marker is only ever read from the academic_resources/ side --
    # placing it under academic_notes/ by mistake must be a quiet no-op,
    # not an error, and must not accidentally re-trigger the normal
    # recursive academic_notes/ walk differently.
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (notes_dir / "01-terms.pdf").write_bytes(b"x")

    paths = discover_pdf_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert [os.path.basename(p) for p in paths] == ["01-terms.pdf"]


def test_discover_excalidraw_sources_includes_marked_subset(tmp_path):
    (tmp_path / "academic_notes" / "econometrics" / "lecture_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Scanned Canvases"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "Drawing.excalidraw.md").write_text("---\n---\n")
    (deep / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_sources(str(tmp_path / "academic_notes" / "econometrics"))

    assert len(pairs) == 1
    assert os.path.basename(pairs[0][0]) == "Drawing.excalidraw.md"


def test_marked_subset_pdf_is_skipped_on_second_run_once_transcribed(tmp_path):
    # End-to-end check of the spec's "nothing downstream needs to change"
    # claim: resolve_output_dir/filter_unprocessed_pdfs must correctly
    # recognize a marked-subset PDF as already done, through build_plan.
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    (deep / "090424.pdf").write_bytes(b"x")
    mirrored_out = (
        tmp_path / "academic_notes" / "econometrics" / "class_2024"
        / "Class Notes" / "Hand-Written Notes" / "processed_outputs"
    )
    mirrored_out.mkdir(parents=True)
    (mirrored_out / "090424.md").write_text("already transcribed")

    plan = build_plan(str(tmp_path), courses=["econometrics"])

    assert plan.pdf_todo == []
    assert [os.path.basename(p) for p in plan.pdf_skipped] == ["090424.pdf"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k "includes_marked_subset or does_not_duplicate or ignores_marker_placed or skipped_on_second_run" -v`
Expected: FAIL (marked-subset results not yet wired in)

- [ ] **Step 3: Implement**

Replace `discover_pdf_sources` (current lines 58-63):

```python
def discover_pdf_sources(course_dir: str) -> list[str]:
    paths = []
    for dirpath in _walk_content_dirs(course_dir):
        paths.extend(discover_pdf_files(dirpath))
    paths.extend(_discover_migrated_pdf_sources(course_dir))
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        resources_course_dir = None
    if resources_course_dir is not None:
        paths.extend(discover_marked_subset_pdf_sources(resources_course_dir))
    seen = set()
    deduped = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped
```

Replace `discover_excalidraw_sources` (current lines 93-97):

```python
def discover_excalidraw_sources(course_dir: str) -> list[tuple[str, str]]:
    pairs = []
    for dirpath in _walk_content_dirs(course_dir):
        pairs.extend(discover_excalidraw_files(dirpath))
    try:
        resources_course_dir = to_resources_root(course_dir)
    except ValueError:
        resources_course_dir = None
    if resources_course_dir is not None:
        pairs.extend(discover_marked_subset_excalidraw_sources(resources_course_dir))
    seen = set()
    deduped = []
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            deduped.append(pair)
    return deduped
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -k "includes_marked_subset or does_not_duplicate or ignores_marker_placed or skipped_on_second_run" -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full test file**

Run: `python -m pytest tests/pipelines/transcribe_notes/test_route_notes_transcribe.py -v`
Expected: all tests PASS (every pre-existing test plus every test added in Tasks 1-4)

- [ ] **Step 6: Run the whole package's test suite as a final regression check**

Run: `python -m pytest tests/ -k transcribe_notes -v`
Expected: all PASS — confirms `transcribe_excalidraw.py`, `excalidraw_chunking.py`, and `migrate_sources_to_resources.py` tests (which import from or exercise shared helpers in this package) are unaffected.

- [ ] **Step 7: Commit**

```bash
git add ai-sandbox/academic-rag-model/pipelines/transcribe_notes/route_notes_transcribe.py ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git commit -m "feat(transcribe_notes): wire marked-subset discovery into the main discovery paths"
```

---

## After implementation

Add `academic_resources/econometrics/class_2024/.notes_subset.json` (containing `{"label": "2024"}`) to the real vault and run:

```powershell
python -m pipelines.transcribe_notes.route_notes_transcribe --course econometrics --dry-run
```

to confirm the full real file list before spending any API calls. This is a separate, manual follow-up step outside this plan's test scope — it touches real `academic-hub/` content, not fixtures.
