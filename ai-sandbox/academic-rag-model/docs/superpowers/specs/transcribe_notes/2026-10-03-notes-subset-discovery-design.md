# Prior-Offering Subset Discovery: Design

## Motivation and history

The user has a full previous iteration of their econometrics course
(`academic_resources/econometrics/class_2024/`: hand-written lecture scans,
slides, problem sets with solutions, recitations, old exams) they want
converted into `academic_notes/` and folded into the RAG corpus, nested
under the existing `econometrics` course rather than as a separate
top-level course. Two pre-existing restrictions in `route_notes_transcribe.py`
block this as-is:

- `discover_pdf_files()` (`transcribe_notes.py`) is a flat `os.listdir`,
  not recursive. The user's source tree is several levels deep per content
  type (e.g. `class_2024/Class Notes/Hand-Written Notes/`,
  `class_2024/Problem Sets with Solutions/`).
- `_discover_migrated_pdf_sources()` (`route_notes_transcribe.py`), which
  sweeps PDFs already staged under `academic_resources/<course>/`, only
  descends into a category whose name *already exists* as a directory
  under `academic_notes/<course>/` (plus an unconditional exclusion of
  `TEXTBOOK_FOLDER_NAMES`). A brand-new category name like `class_2024` or
  `2024` has no such counterpart, so it's silently skipped.

Confirmed during design that neither restriction is load-bearing
elsewhere: `resolve_output_dir`/`to_notes_root`/`to_resources_root`
(`core/env/academic_hub_paths.py`) already mirror a path of any depth
correctly, `derive_course` (`core/indexer/index_card.py`) only ever reads
path segment 1, and `folder_category` (`derive_folder_category` in
`transcribe_notes.py`, `_folder_category_from_path` in
`core/indexer/chunk_index.py`) only ever reads the immediate parent
directory name, independent of how deep the tree above it goes. So the
fix is confined to discovery; nothing downstream (indexing, chunking,
duplicate detection, output paths) needs to change.

This is intentionally scoped as a general mechanism (any course may later
want a prior-offering or alternate-source subset, not just econometrics),
and deliberately conservative about auto-discovery scope, matching this
module's existing docstring promise: "no LLM makes the routing decision
... safe to run unattended." See also
`2026-09-21-source-asset-relocation-design.md` for the mirrored-path
convention this builds on.

A second, larger phase — using embedding similarity to link a prior
offering's content to its current-year corollary (e.g. a reused slide
deck, or a problem set covering the same material) — is **explicitly out
of scope for this spec** and will get its own design once there is real
prior-offering content indexed to test against.

## Scope

**In scope:**
- A marker file, `.notes_subset.json`, that opts a directory under
  `academic_resources/<course>/` into **arbitrary-depth recursive**
  PDF/Excalidraw discovery, for any course.
- Updates to `route_notes_transcribe.py`'s discovery functions to find
  and sweep marked subset roots alongside the two existing discovery
  paths (both left unchanged).
- Tests covering discovery at depth, the opt-in boundary (unmarked
  directories are never swept), and the textbook-folder exclusion.

**Out of scope:**
- Any new indexer/chunking/metadata behavior (none needed — see above).
- Cross-offering similarity linkage (Phase 2, separate spec).
- Reorganizing the user's actual `class_2024` folder beyond adding the
  marker file — no flattening, no renaming required.
- A CLI flag to list/validate marker files (nice-to-have, deferred; the
  existing `--dry-run` already lists every file that would be processed,
  which is sufficient for the user to sanity-check a newly marked subset).

## Design

### Marker file

`.notes_subset.json`, placed at the root of the directory to be swept,
e.g. `academic_resources/econometrics/class_2024/.notes_subset.json`:

```json
{"label": "2024"}
```

`label` is a free-text, human-readable identifier (not required to match
the directory name) stored for Phase 2's benefit, so cross-offering
linkage can read "this card's subtree is offering 2024" directly instead
of re-deriving it from a folder name later. Not used by Phase 1's
discovery logic itself beyond confirming the file exists and is valid
JSON.

A malformed or unreadable marker file is treated as **absent** (directory
not swept), with a warning printed — never a hard failure, preserving
unattended-safe behavior for the rest of the run.

### Discovery changes (`route_notes_transcribe.py`)

```python
_SUBSET_MARKER_FILENAME = ".notes_subset.json"

def find_subset_roots(resources_course_dir: str) -> list[str]:
    """Recursively finds every directory under resources_course_dir that
    contains _SUBSET_MARKER_FILENAME at its own root. Does not look for
    further nested markers once a root is found -- one marker claims its
    whole subtree, no stacking. A malformed marker is logged and treated
    as not-present (directory excluded, walk continues)."""

def _walk_marked_subset(subset_root: str):
    """Yields every directory under subset_root, pruning processed_outputs/,
    hidden directories, and (new, moved here from the old category-match
    gate) any directory named in TEXTBOOK_FOLDER_NAMES at any depth --
    same safety invariant _discover_migrated_pdf_sources already
    enforced, now needed here since the category-match gate it relied on
    is gone for this path."""

def discover_marked_subset_pdf_sources(resources_course_dir: str) -> list[str]:
    """find_subset_roots() + discover_pdf_files() over each dir yielded
    by _walk_marked_subset() per root -- the same
    recursive-walk-then-flat-list-per-dir pattern discover_pdf_sources()
    already uses for the academic_notes/ side, just pointed at a marked
    resources-side subtree instead."""

def discover_marked_subset_excalidraw_sources(resources_course_dir: str) -> list[tuple[str, str]]:
    """Same, via discover_excalidraw_files() -- kept symmetric with PDF
    discovery so a prior offering's handwritten Excalidraw scenes (if
    any) aren't a silent gap."""
```

`discover_pdf_sources()` and `discover_excalidraw_sources()` each gain a
call to their new marked-subset counterpart, appended to their existing
results list, resolving `resources_course_dir` the same way
`_discover_migrated_pdf_sources` already does today (via
`to_resources_root(course_dir)`, returning early if it doesn't exist).

`_discover_migrated_pdf_sources` (the existing flat, category-match-gated
sweep) is **unchanged** — it keeps serving its original case: a file
individually moved into an already-registered category via
`migrate_sources_to_resources.py`. The new marked-subset path is purely
additive for the "whole prior-offering subtree" case.

If a marker is ever placed somewhere that overlaps an already-matching
flat category (e.g. nested inside a directory `_discover_migrated_pdf_sources`
would also sweep), the same PDF path could otherwise appear twice in the
combined list and get processed twice in one run. `discover_pdf_sources()`
dedupes its combined result (existing categories + marked subsets) before
returning, so this is a no-op rather than a double-processing bug.

### Data flow (unchanged downstream)

A PDF at
`academic_resources/econometrics/class_2024/Class Notes/Hand-Written Notes/090424.pdf`
resolves exactly as today's code already handles it:
- `course` = `"econometrics"` (path segment 1)
- `folder_category` = `"Hand-Written Notes"` (immediate parent)
- output at `academic_notes/econometrics/class_2024/Class Notes/Hand-Written Notes/processed_outputs/090424.md`
  (`resolve_output_dir` + `os.makedirs(..., exist_ok=True)`, both already
  depth-agnostic)

`folder_category` values like `"Hand-Written Notes"` or `"Problem Sets
with Solutions"` won't match the canonical category vocabulary
`chunk_index.py`'s `_PROBLEM_TIER_FOLDER_CATEGORIES` checks for, so those
files fall back to generic paragraph/page chunking rather than the
problem-boundary-aware tier. This is a pre-existing, graceful fallback
(not a crash), not something this spec needs to fix — the user can rename
leaf folders to canonical names later if better chunking matters enough
to be worth it, but it's optional.

### Error handling

- Malformed `.notes_subset.json` → warn, treat as not-marked, continue.
- A marked subset root with zero PDFs/Excalidraw pairs underneath → no
  error, just contributes nothing (matches existing empty-directory
  behavior elsewhere in this module).
- Everything downstream of discovery (per-file try/except in `run_plan`,
  the output-landed-on-disk re-check) is already in place and untouched.

### Testing

New tests in `tests/pipelines/transcribe_notes/test_route_notes_transcribe.py`:
- A marker at a subset root makes PDFs at 3+ levels of nesting discoverable.
- A sibling directory with no marker is never swept, even if it contains PDFs.
- A `textbooks/`-named directory nested inside a marked subset is excluded.
- A malformed marker file (invalid JSON) is skipped with a warning, not a crash.
- Existing `_discover_migrated_pdf_sources` behavior (flat, category-match
  gated) is unchanged when no marker is present — regression coverage for
  the discovery path this spec doesn't touch.
- An already-processed PDF under a marked subset is correctly excluded by
  `filter_unprocessed_pdfs` on a second run (confirms `resolve_output_dir`
  depth-agnostic behavior holds through the new path too).

## Migration for the user's existing content

No reorganization needed. Add
`academic_resources/econometrics/class_2024/.notes_subset.json` containing
`{"label": "2024"}`, then run:

```powershell
python -m pipelines.transcribe_notes.route_notes_transcribe --course econometrics --dry-run
```

to confirm the full file list before spending any API calls, then without
`--dry-run` to actually transcribe.
