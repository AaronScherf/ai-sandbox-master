# Academic Hub

Per-course academic content: your own notes/coursework plus the source
material it's derived from. See the root [`README.md`](../../README.md) for
the whole-repo architecture and [`academic-rag-model/`](../academic-rag-model/README.md)
for the pipelines that populate and index this folder.

- [`academic_notes/<course>/`](academic_notes/) — **its own separate git
  repo** (nested here but gitignored from this outer repo), synced to a
  tablet via Obsidian's Direct Git Sync plugin. Kept deliberately
  lightweight: your own TA notes, problem sets, exams, and handwritten-note
  transcriptions as `.md` (both plain notes and `processed_outputs/`, the
  pipeline-generated conversions) plus each source's own `.excalidraw.md`
  scene file, which never moves. This is the complete, self-contained
  corpus meant to be readable on the tablet without anything else present.
- `academic_resources/<course>/{textbooks,ta_notes,problem_sets,...}/` —
  heavy source material: third-party copyrighted content (textbook PDFs and
  their full-text Markdown conversions, `lecture_slides/`,
  `lecture_recordings/`) *and*, as of the 2026-09 source-asset relocation,
  your own heavy sources (PDFs, Excalidraw `.svg`/`.png` exports, `.docx`/
  `.pptx`) that used to live under `academic_notes/` — moved out to keep
  that tree lightweight, since none of it needs to travel to the tablet.
  Each file's location mirrors its `academic_notes/`-side category exactly
  (`common/academic_hub_paths.py`'s `to_resources_root()`/`to_notes_root()`
  — swap only the root segment, same `<course>/<category>/<filename>`).
  Not wholesale-gitignored — only the third-party/copyrighted patterns and
  `.docx`/`.pptx`/`.mp3` are (see the root `.gitignore`'s own comments for
  the full, evolving list); your own migrated PDFs and Excalidraw images
  are tracked normally. Run `workspace_generator.sh` (repo root) to
  scaffold these empty per course.
- `.index/` — the source-indexer's per-file cards and corpus-wide tags
  (derivative metadata, tracked); `.index/chunks/` (verbatim passage
  excerpts, gitignored). Each card's `source_pdf_path` is its identity
  anchor (a `compute_file_id()` content hash, so it survives a move or
  rename); `source_asset_path` separately tracks the true heavy-asset
  location, which needs the mirroring convention above once a source has
  migrated. `orphaned: true` means a card's source couldn't be found on
  the last `rebuild()` — a provenance note, not a reason the card gets
  hidden from search (its `.md` content may still be perfectly real and
  useful even when its original source is gone).

Course folders are driven entirely by what you create under
`academic_notes/` — there's no fixed course list.

See `academic-rag-model/docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md`
for the full design behind the notes/resources split, and
`academic-rag-model/docs/superpowers/plans/2026-09-21-source-asset-relocation.md`
for the real-corpus migration history (per-course status, bugs found and
fixed along the way).
