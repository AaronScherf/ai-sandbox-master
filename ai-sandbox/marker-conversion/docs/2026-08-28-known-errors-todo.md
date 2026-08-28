# Known Errors / TODO

Tracker for concrete bugs found during real-corpus testing that need
fixing, separate from the status docs (which describe what was built and
why). Add new entries at the top. Each entry should have enough evidence
that whoever picks it up doesn't have to re-derive it from scratch.

---

## OPEN — `transcribe_notes.py`: 6 real PDFs produced 0-byte `.md` output, no error, no cache

**Found:** 2026-08-28, while running the source indexer's `retag` (see
`docs/superpowers/plans/2026-08-28-source-indexer-retag.md`) against the
real `academic-hub` corpus — the indexer itself worked correctly and is
not the bug; it just surfaced this.

**What's broken:** these 6 files in
`academic_notes/math-camp/ta_notes/processed_outputs/` are exactly 0
bytes, with **no matching `_pages_cache.json`** in the same directory:

- `Part I Linear Algebra 08.10.md`
- `Part I Linear Algebra 08.11 (1).md`
- `Part I Linear Algebra 08.12 (1).md`
- `Part I Linear Algebra 08.13 (1).md`
- `Part II Analysis in Euclidean Spaces 08.13 (1).md`
- `Part II Analysis in Euclidean Spaces 08.14.md`

Their source PDFs exist and are substantial (10-14MB each) — this is not
a case of an empty/missing source file.

**Evidence gathered so far:**
- No `_pages_cache.json` for any of the 6 exists at all. Tiers 2-4 of
  `process_pdf()` save this cache incrementally as each page/batch
  completes, so its total absence means either those tiers never ran, or
  Tier 1 (pure local extraction, which writes no cache) is what fired.
- Checked `Part I Linear Algebra 08.10.pdf` directly with `pypdf`:
  `/Creator: 'Nebo'` — this is a **Nebo (MyScript ink) export**. Its
  embedded "text" layer is just page-header boilerplate (`"Linear
  Algebra Page 2"`, etc.), not the actual handwritten math content,
  which exists only as ink strokes/images. `has_reliable_pagination()`'s
  own docstring says Nebo/MyScript/OneNote exports are specifically
  meant to be routed away from Tier 1/2's local-text path into Tier 3's
  per-page vision transcription, "regardless of what any single page's
  text happens to look like."
- Given that guard should apply here, a 0-byte, cache-less result is
  unexplained by the code as currently understood — needs an actual run
  against one of these 6 files (with logging/breakpoints) to see which
  branch of `process_pdf()` it actually takes.

**Leading hypothesis (unconfirmed):** these `.md` files may simply
predate ever running `transcribe_notes.py` on these particular PDFs at
all — e.g. an empty stub created by another process (editor autosave,
directory scaffolding, manual `touch`) rather than a pipeline defect.
The PDFs' `CreationDate` (2026-08-11) and the `.pdf`/`.md` file mtimes
(2026-08-17) are recent relative to this project, consistent with "newly
added, not yet transcribed." This would mean there's no transcription
bug at all — just leftover empty placeholders next to real, unconverted
source PDFs.

**Alternative hypothesis:** the Nebo/MyScript detection guard in
`has_reliable_pagination()` failed to fire for these specific files
(different metadata shape than expected?), letting Tier 1 run against a
PDF with no real extractable text, and Tier 1 produced technically-valid
but empty output because `page_looks_defective()` doesn't treat
"zero-length extracted text" as its own defect signal.

**To do:** run `transcribe_notes.py` directly against these 6 PDFs with
verbose output to see which tier actually fires and why the result is
empty; confirm or rule out the Nebo-guard hypothesis; if it's a real
guard failure, fix `has_reliable_pagination()`/`page_looks_defective()`;
if it's just "never run," there's no code bug, just a backlog item to
run the pipeline on them.

**Not blocking:** the source indexer already treats this gracefully on
its own end (see companion fix in the same session: `rebuild` now skips
0-byte `.md` files entirely rather than generating a vacuous card for
them) — this entry is about the transcription pipeline itself, not the
indexer.
