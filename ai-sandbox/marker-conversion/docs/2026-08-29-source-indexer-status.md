# Source Indexer: Status Summary

Start here for "what happened and where do we stand" on the source-indexer
subproject -- `index_card.py` (per-file card generation), `index_search.py`
(rebuild/backfill + two-stage search), and `retag.py` (corpus-wide tag
mining). Design/schema reference: `docs/superpowers/specs/2026-08-27-source-indexer-design.md`
(kept current with revision notes inline; this doc is the narrative
history and current state, not a duplicate of the design).

Given a query like "teach me about linear algebra," this subsystem ranks
the most relevant files in `academic-hub`. It is explicitly the
source-selection layer for an eventual interactive RAG tutoring model,
not the RAG model itself (see "What's next" below).

## What shipped

Two implementation plans, both merged into `marker-conversion`:

- **Core indexer** (`docs/superpowers/plans/2026-08-28-source-indexer-core.md`):
  per-file index cards keyed by `file_id` (SHA-256 of the source PDF's own
  bytes, independent of where the file lives), course-level rollups
  (free centroid/tag-frequency, no extra LLM call), two-stage
  course-then-file cosine-similarity search, hooks into all three
  conversion pipelines (`transcribe_notes.py`, `convert_textbook.py`,
  `describe_images.py`).
- **`retag`** (`docs/superpowers/plans/2026-08-28-source-indexer-retag.md`):
  corpus-wide, two-phase tag mining -- holistic LLM proposal +
  per-candidate empirical validation for discovery, many-to-many
  cosine-similarity assignment (a file can carry several tags), a
  minimum-coverage safety net so no file goes untagged, and (added
  2026-08-29) writing real tags back into each file's own frontmatter.

## Real-corpus state as of 2026-08-29

30 cards (`math-camp` course), all healthy: **0 orphaned, 0
`needs_indexing`, 0 untagged, 30/30 have `content_hash`, 5/5 textbooks
have `rag_md_path` linked to their `.rag.md`.** 14 tags in the
vocabulary (10 corpus-validated, 4 single-document fallback tags).
`doc_type` spans `handwritten_notes`, `problem_set`, `ta_notes`,
`textbook`.

## Bugs found and fixed, in order

All confirmed live against the real corpus, not synthetic fixtures --
each has a regression test.

1. **Tag discovery redesigned** (2026-08-28): the original design (graph
   clustering — connected components over a file-embedding similarity
   graph) was tried against real data and rejected: transitive
   clustering merges unrelated subjects, and no threshold swept
   (0.78-0.90) produced a clean subject split. Replaced with one-shot
   holistic LLM proposal + per-candidate empirical validation (spec
   §5.2's "Revised 2026-08-28" note has the full evidence).
2. **Minimum-coverage safety net added** (2026-08-28): 2 of 24 real
   cards had zero tags after the redesign above — genuinely unique
   documents (the one syllabus) can never clear the corpus-wide minting
   bar. Fixed with a per-file fallback tag proposal (spec §5.4).
3. **Fallback tags were leaking onto unrelated documents** (2026-08-28):
   a `math-camp-syllabus` fallback tag (minted for one document) scored
   0.73 similarity against an unrelated Linear Algebra file — well above
   the assignment threshold — because a fallback anchor is never
   corpus-validated the way a real tag is. Fixed by marking fallback
   tags `origin: "fallback"` and excluding that origin from reuse (spec
   §5.3/§5.4).
4. **`rebuild` was silently corrupting `tags.json`** (2026-08-28): a
   stale pre-rename filename (`topics.json` instead of `tags.json`) in
   `_flag_or_prune_orphans`'s exclusion list meant every `rebuild`
   treated the tag vocabulary as a course shard of file-cards, stamping
   a meaningless `orphaned: True` onto every tag. Harmless by itself,
   but `rebuild --prune` would have silently deleted the entire tag
   vocabulary. Fixed; regression test populates `tags.json` before
   calling `rebuild` and asserts it's untouched.
5. **Frontmatter write-back added** (2026-08-29, spec §5.5): per user
   request, a real (non-dry-run) `retag` now patches each file's own
   `tags:` frontmatter line with its current tags, so reading the raw
   `.md` shows real tags without consulting the index. Notes-only —
   textbook `.rag.md` output never had a frontmatter convention.
6. **Six 0-byte `.md` files, and a runaway-repetition transcription bug**
   (2026-08-28 and 2026-08-29): both are `transcribe_notes.py` pipeline
   bugs, not indexer bugs, but were both *discovered* while validating
   `retag`/`rebuild` against real content — full writeups live in
   `docs/2026-08-28-known-errors-todo.md` and
   `docs/2026-08-24-notes-transcription-status.md`. Mentioned here only
   because fixing them required re-transcribing and re-indexing most of
   the corpus, which is what followed in items 7-8.
7. **Staleness detection was mtime-only, and mtime is not a safe signal**
   (2026-08-29): `_is_stale()` compared a `.md`'s mtime against the
   card's `source_updated_at` — confirmed live that a real rebuild once
   reported 14 cards "updated" in one run even though nothing had
   actually changed, traced to something (a container/session remount)
   resetting every `.md`'s mtime to the same instant. Fixed with a
   `content_hash` field (SHA-256 of the file's own bytes) as the
   decisive signal, with mtime kept only as a one-time migration bridge
   for a card that predates the field (spec §4.3's "revised 2026-08-29"
   note).
8. **`.rag.md` linkage never reached the index card for any of the 5 real
   textbooks** (2026-08-29): `describe_images.py`'s `link_rag_md()`
   writes `rag_md_path` into `_metadata.json` unconditionally but only
   updates the card if one already existed at that exact moment —
   confirmed live that none of the 5 real textbook cards had it set,
   despite every `.rag.md` file existing on disk. `rebuild`'s textbook
   loop now reconciles `rag_md_path` from `_metadata.json` onto the
   card every time they differ (spec §4.4's "revised 2026-08-29" note).

## What's next

The spec's §9 lists everything explicitly deferred. Discussed with the
user 2026-08-29 which to tackle first:

- **Passage/chunk-level embeddings — recommended next.** Everything
  built so far is file-level ("which document is relevant"), not
  passage-level ("which paragraph answers this question") — the actual
  retrieval granularity an interactive tutor needs to ground and cite a
  specific answer. The embedding infrastructure here (client, cosine
  similarity, course/file two-stage filtering as a cheap coarse
  pre-filter) is directly reusable, not throwaway work.
- **Retrieval-conditioned scoring** (for the paused
  `project_notes_postprocessing_paused` precision problem) explicitly
  *depends on* passage-level embeddings existing first — its whole
  premise is scoring a transcription candidate against retrieved,
  validated-similar *passages*, and file-level granularity is too
  coarse to give useful neighbors for that comparison.
- **Tag-graph browsing** (persisting the co-occurrence structure
  `retag`'s discovery phase already computes and discards, for
  topic-relationship browsing/traversal) is cheap — no new embeddings,
  just a read layer over data that's basically already computed — but
  it's a navigation aid for a human exploring the corpus, not something
  that moves the interactive-tutor goal forward. Parked as a low-cost
  side quest, not prioritized.
- **Document-pairing detection** (e.g. linking a problem set to its own
  solutions file) confirmed still unbuilt and still a real gap (`Linear
  Algebra Problem Set.md` / `...AMS Solutions.md` have no link today) —
  the user flagged this as nice-to-keep-in-mind but not urgent.

Brainstorming for passage-level embeddings starts on a new branch,
forked from `marker-conversion` per this repo's usual branch topology.
