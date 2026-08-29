# Known Errors / TODO

Tracker for concrete bugs found during real-corpus testing that need
fixing, separate from the status docs (which describe what was built and
why). Add new entries at the top. Each entry should have enough evidence
that whoever picks it up doesn't have to re-derive it from scratch.

---

## RESOLVED — `transcribe_notes.py`: 6 real PDFs produced 0-byte `.md` output, no error, no cache

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

**Resolution (2026-08-28), confirmed not assumed:** neither hypothesis
above was quite right. Both the `.pdf` and `.md` mtimes (2026-08-17)
predate commit `44bcfe2` (2026-08-24 — "Add local-extraction bypass and
conditional accumulation/DPI/model"), which is the commit that actually
added `_MESSY_EXPORT_MARKERS = ("nebo", "myscript", "onenote")` — the
Nebo-guard this entry's investigation was reasoning about didn't exist yet
when these 6 files were produced. Verified directly: all 6 PDFs' metadata
confirms Nebo/OneNote export, and running the *current* `transcribe_notes.py`
against all 6 for real (not a dry-run) produced full, correct transcriptions
via Tier 3 — no code change was needed, since the guard responsible had
already shipped 4 days earlier. These were pre-fix stale artifacts sitting
next to the real source PDFs, not a live bug. Full narrative and
cross-reference: `docs/2026-08-24-notes-transcription-status.md`, "2026-08-28:
six 0-byte `.md` files were pre-fix stale artifacts, now re-transcribed".

**Not blocking (unchanged):** the source indexer already treats this
gracefully on its own end (see companion fix in the same session: `rebuild`
now skips 0-byte `.md` files entirely rather than generating a vacuous card
for them) — this entry was about the transcription pipeline itself, not the
indexer.

**Companion bugs found and fixed while exercising this recovery path for
the first time** (all in the source indexer, not `transcribe_notes.py` —
none were previously exercised end-to-end against real re-transcription):
- `rebuild` never noticed a `.md`'s content had changed when its `file_id`
  and `path` both stayed the same (re-transcription is exactly this case) —
  fixed with an mtime-based staleness check (`830e802`).
- A card previously marked `needs_indexing: true` (from an earlier failed
  attempt) was never actually retried by a plain, non-`--force` `rebuild` —
  the old/new-card swap was gated on `force or stale` only, not on
  `needs_indexing` (`4979df5`).
- `generate_index_card()` crashed with `'list' object has no attribute
  'get'` when `gemini-3.1-flash-lite` wrapped an otherwise well-formed JSON
  response in a one-element array, despite `response_mime_type` and explicit
  prompt instructions asking for a bare object — fixed by unwrapping
  (`7d57d3f`).

---

## RESOLVED — `retag.py`: a single-document fallback tag leaked onto unrelated files on reuse

**Found:** 2026-08-28, reviewing the `retag --dry-run` preview against the
now-fully-real corpus (all 6 files above re-transcribed) before persisting
it for real — `math-camp-syllabus` (a fallback tag minted for the one
syllabus file, spec §5.4) appeared on `LN_Linear Algebra.md`, and
`probability-lecture-notes` (fallback-minted for the one probability
lecture) appeared on the syllabus itself.

**Root cause, confirmed directly:** `assign_tags()` (spec §5.3) checks
every tag in the vocabulary against every card with the same
`TAG_ASSIGNMENT_THRESHOLD = 0.65`, with no distinction between a tag that
cleared `discover_tags`' corpus-wide validation (>= 3 real matches) and a
fallback tag whose anchor is just a generic paraphrase of one document's
title+summary. Measured live: `math-camp-syllabus` scored 0.7264 cosine
similarity against `LN_Linear Algebra.md` — comfortably above threshold,
in a corpus small and topically homogeneous enough that a generic anchor
drifts close to everything.

**Fix:** fallback tags are now marked `origin: "fallback"` when minted;
`assign_tags()` skips any tag with that origin entirely, so a fallback tag
only ever describes the single document `ensure_minimum_coverage` made it
for (`6848575`). The two pre-existing fallback tags in the real corpus's
`tags.json` were backfilled with `origin: "fallback"` by hand, since they
predated the field. Verified after the fix: those two documents correctly
fell back to fresh, more specific single-document tags
(`probability-foundations`, `probability-theory-notes`) instead of
inheriting the old, now-excluded ones.
