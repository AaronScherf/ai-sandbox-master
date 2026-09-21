# Relocating Heavy Note Sources to `academic_resources/`: Design

## Motivation

The user wants `academic_notes/` (git+Obsidian-synced to a tablet) to stay
lightweight -- text only -- so sync stays fast and the repo stays small
(already rewritten once this month, 217MB->35MB, per
`docs/status/2026-09-21-obsidian-git-sync-status.md`'s history-rewrite
note). Plan, from the user directly: move the *heavy* files -- PDFs and
Excalidraw `.svg`/`.png` exports -- into `academic_resources/` (already
the home for textbook PDFs, per `indexer/duplicate_check.py` and
`index_search.py`'s `_textbook_book_dirs`), while keeping every `.md` file
-- the `.excalidraw.md` scene files, and every `processed_outputs/`
artifact (raw + expanded transcriptions, `_pages_cache.json`) -- in
`academic_notes/` exactly where it is today.

Hard requirement from the user: "I want to ensure the files still refer to
each other via their indices so an analysis can compare them or
re-transcribe as needed from source truth." Two distinct things must keep
working after the move:
1. **The JSON source index** (`indexer/index_card.py`/`index_search.py`)
   must still resolve, for any card, exactly where its true (heavy) source
   lives -- not just whether it was "PDF-derived" or "Excalidraw-derived."
2. **The transcription pipelines themselves** must still be able to find a
   source file to (re-)transcribe, and still write output to the same
   `academic_notes/.../processed_outputs/` location as today, even though
   the source no longer lives next to it.

## Current state (why this isn't a small patch)

Three places hardcode "source and its `processed_outputs/` are siblings
in the same directory":
- `notes/transcribe_notes.py`'s `process_pdf()`: `output_dir =
  os.path.join(os.path.dirname(pdf_path), "processed_outputs")`.
- `notes/transcribe_excalidraw.py`'s `discover_excalidraw_files()` (image
  must be in the same directory as the `.md`) and `write_outputs()` (same
  sibling-output-dir pattern).
- `notes/route_notes_transcribe.py`'s `pdf_output_path`/
  `excalidraw_output_path`/`_walk_content_dirs` (added this session,
  inherits the same assumption from the two pipelines above).

And the JSON index has its own separate, real gap, found and verified
empirically while investigating this (not a consequence of the planned
move, but directly relevant to it -- see "Verified, not assumed" below):
`indexer/index_search.py`'s `rebuild()` -- the command that's supposed to
resync the index after files move -- has walkers for PDF notes
(`_notes_pdf_paths`), textbooks (`_textbook_book_dirs`), and video lecture
notes (`_video_lecture_note_paths`), but **none for Excalidraw notes**.
`rebuild()`'s orphan pass treats "not found by any walker" as orphaned.

**Verified, not assumed:** ran `rebuild()` against an isolated copy of the
real index (NTFS-junction-linked to the real `academic_notes`/
`academic_resources` so real content resolves, `.index/` copied so nothing
real could be touched), scoped to `course="econometrics"`. Result:
`{'unchanged': 4, 'orphaned': 4, ...}` -- the 4 real textbook cards
correctly left alone, all 4 real Excalidraw cards registered this session
flagged `orphaned: true`. With `--prune` (a real CLI flag on this
command), that's deletion. This is a live, pre-existing bug, not something
this session's Excalidraw work introduced, but it directly threatens the
"still refer to each other via indices" requirement, so fixing it is part
of this plan, not a separate follow-up.

## Design

### 1. Mirrored-path convention

A source file's new home is the **same relative path, rooted at
`academic_resources/` instead of `academic_notes/`**, keeping the same
`<course>/<category>/<filename>` shape both pipelines and the indexer
already use everywhere else:

```
academic_notes/econometrics/ta_notes/01-defining-terms.pdf   (today)
academic_resources/econometrics/ta_notes/01-defining-terms.pdf   (after)

academic_notes/econometrics/lecture_notes/Econometrics ....excalidraw.md    (stays)
academic_notes/econometrics/lecture_notes/Econometrics ....excalidraw.svg   (today)
academic_resources/econometrics/lecture_notes/Econometrics ....excalidraw.svg  (after)
```

`processed_outputs/` never moves -- it stays wherever the *lightweight*
anchor file lives: next to the PDF's own `academic_notes/` category
directory for a PDF note (there's no `.md` scene file, so the PDF's own
category directory becomes a virtual anchor -- output writes to
`academic_notes/<course>/<category>/processed_outputs/`, not
`academic_resources/.../processed_outputs/`), or next to the
`.excalidraw.md` (unchanged, since that never moves).

New shared module `common/academic_hub_paths.py` (no network, no heavy
imports -- matches this project's other `common/` modules) implements this
once, so `transcribe_notes.py`, `transcribe_excalidraw.py`, and
`route_notes_transcribe.py` don't each reimplement it slightly
differently:

```python
def to_resources_root(rel_path: str) -> str
def to_notes_root(rel_path: str) -> str
def notes_category_output_dir(academic_hub_root: str, course: str, category: str) -> str
```

### 2. Backward compatibility during a partial migration

Files migrate one course/category at a time in practice, not atomically.
Every discovery path checks **both** roots rather than assuming migration
is complete:
- `transcribe_notes.py`'s PDF output-dir logic: if `pdf_path` is under
  `academic_resources/`, output goes to the mirrored `academic_notes/`
  category dir; if it's still under `academic_notes/` (not yet migrated),
  output stays a sibling, exactly as today. Either way the file itself is
  found wherever the caller points it -- this is a resolution rule, not a
  discovery rule.
- `transcribe_excalidraw.py`'s image lookup: check the same directory as
  the `.md` first (today's behavior, for not-yet-migrated files), then
  fall back to the mirrored `academic_resources/` directory.
- `route_notes_transcribe.py`'s PDF discovery walks **both**
  `academic_notes/<course>/` and `academic_resources/<course>/`, but only
  descends into an `academic_resources/<course>/<category>/` directory
  when a **same-named** category directory also exists directly under
  `academic_notes/<course>/` -- this is what keeps `academic_resources/
  <course>/textbooks/` (which has no `academic_notes/<course>/textbooks/`
  counterpart) out of scope without a hardcoded, easily-stale category
  name list.

### 3. Index card schema: a new `source_asset_path` field

`source_pdf_path` keeps its existing meaning unchanged: the
content-identity anchor (`compute_file_id()` is computed from this exact
file) -- the PDF itself, or the `.excalidraw.md` scene file. It does not
move for Excalidraw cards, so nothing about identity/file_id changes.

New field, `source_asset_path`: the actual heavy file a human (or a
re-transcription/comparison script) needs to open to see the real
source content. For a PDF card this equals `source_pdf_path` (set
explicitly, not left implicit, so a reader never needs to know a card's
`doc_type` to find its source). For an Excalidraw card, this is the
`.svg`/`.png` that was actually rasterized and sent to Gemini -- distinct
from `source_pdf_path` for the first time. `None` only for doc types with
no single-file heavy asset (there are none today, but the field stays
optional for forward compatibility rather than becoming a silent new
required contract on every caller).

Both `notes/transcribe_notes.py` and `notes/transcribe_excalidraw.py`'s
own frontmatter (`source_pdf`/`source_image` respectively) upgrade from a
bare filename to the file's path relative to `academic_hub_root` -- once
the heavy file no longer lives next to the output, a bare filename is no
longer enough to relocate it by hand from the `.md` alone.

### 4. Migration script

`notes/migrate_sources_to_resources.py`: finds every PDF/Excalidraw-image
still living under `academic_notes/` whose category directory has content
already indexed (or not -- migration doesn't require prior indexing),
moves each to its mirrored `academic_resources/` location (plain
`shutil.move`, same filesystem, atomic), prints a summary, and -- unless
`--no-reindex` is passed -- calls `index_search.rebuild()` afterward so
every affected card's `source_pdf_path`/`source_asset_path` gets patched
to the new location via `reconcile_and_write()`'s existing cheap
"file moved, content unchanged" path (no LLM call in the common case --
only a genuinely new/stale/`needs_indexing` card would trigger one, none
of which a pure move produces).

**Never run against the real corpus without a final explicit
confirmation** -- building and testing this script (against synthetic
fixtures) is in scope for this plan; physically moving the user's real
~90 files is a separate, explicit go/no-go after the code is verified.

## Non-goals

- Not touching `convert_textbook.py`'s own PDF handling (textbooks already
  live in `academic_resources/`; unaffected).
- Not touching `video_notes/` (its "source" is a set of YouTube video IDs,
  not a local file at all -- `compute_id_from_parts`, no `source_pdf_path`
  concept applies).
- Not renaming `source_pdf_path` itself, despite the name being a slight
  misnomer for an Excalidraw card (it holds the `.excalidraw.md` path) --
  it's already load-bearing across `index_card.py`/`index_search.py`/both
  transcribe scripts; renaming it is a bigger, separable blast radius than
  this plan needs, and every caller already treats it as "the identity
  anchor," which remains accurate.
