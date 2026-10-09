# Source Indexer

The layer that turns a growing pile of converted textbooks, notes, essays, and
journal articles into a searchable corpus. Given a query like "teach me about
linear algebra," this is what ranks the most relevant files — the
source-selection layer underneath the [RAG tutoring agent](../../agent/rag/), not the
tutor itself. Every other conversion pipeline in this repo (`convert_textbook/`,
`transcribe_notes/`, `convert_essays/`, `convert_journal_articles/`) hooks into this module so a newly
converted document gets indexed as a normal side effect of that pipeline
running, not a separate step someone has to remember.

Run any script here as a module from the `academic-rag-model/` root, e.g.
`python -m core.indexer.index_search query "..."` — see the root
[`README.md`](../../README.md) for why (package-qualified imports need
`academic-rag-model/` on `sys.path`).

## Key files

- `index_card.py` — per-file index cards keyed by `file_id` (a hash of the
  source file's own bytes, so a card survives being moved or renamed), plus
  free course-level rollups computed from existing card data. `known_doc_types`
  is a parameter here, not a hardcoded constant, so a non-academic-hub corpus
  (e.g. `convert_essays/`, `convert_journal_articles/`) can classify into its own vocabulary
  instead of being force-fit into `textbook`/`problem_set`/`ta_notes`/
  `handwritten_notes`. `source_pdf_path` is the identity anchor
  (`compute_file_id()` hashes its bytes); `source_asset_path` (2026-09-21)
  is a separate, additive field tracking the true heavy-asset location for
  academic-hub's `academic_notes`/`academic_resources` split — defaults to
  `source_pdf_path` for a new card, and reconciling an existing card only
  overwrites it when the caller passes a non-`None` value, so a caller that
  can't currently determine it doesn't blow away a previously-known-good one.
- `index_search.py` — the `rebuild`/`query`/`ask` CLI, and the two-stage
  (course-then-file) cosine-similarity search. Query-side functions
  (`search`, `search_passages`) take a **list** of corpus roots, not one, so a
  single query can span multiple corpora (e.g. `academic-hub` and `research/`)
  at once — candidates are tracked as `(root, course)` pairs so two corpora
  with a same-named course never collide. `rebuild`/`retag`/`chunk` stay
  single-root (`--root`, given exactly once) since those write into one
  corpus's own `.index/`. `rebuild()` flags a card `orphaned: true` when its
  source can't be found on that run (moved, renamed in a way the walker
  couldn't follow, or genuinely deleted) — a provenance note, not a verdict
  on the card's own content: `search()` still surfaces an orphaned card as
  long as it has a real embedding, since the underlying `.md` may still be
  perfectly good even once its original source is gone (real finding,
  2026-09-23 — see the source-asset-relocation plan's cleanup notes).
- `related.py` (2026-10-03) — links a handwriting-only Excalidraw note to its
  "with slides" superset: `subset_of`/`subset_link_score` on the subset's card.
  Candidates share course, folder, and a `YYYY-MM-DD` in the filename (the superset's
  raw transcript has `embedded_slides: true`); confirmed by word-3-gram
  containment >= 0.3 of the subset's handwriting in the superset's `[Handwritten]`
  blocks (whole-card embeddings can't separate same-topic lectures). `search()`
  hides a subset whenever its superset is also a surviving candidate
  (`--include-subsets` / `include_subsets=True` shows both); an unindexed, missing,
  or filtered-out superset never hides the subset. Runs from
  `transcribe_excalidraw.write_outputs` and `rebuild`; manual:
  `python -m core.indexer.related [--course X] [--dry-run]`. Manual corrections:
  `.index/links/overrides.json` with
  `{"force": [{"subset": id, "superset": id}], "block": [id]}`.
- `questions.py` (2026-10-03) — pure logic for the `[Question]` resolver (`agent/rag/resolve_questions.py`):
  tag discovery and stable ids (`q<ordinal>-<hash>`, from the raw transcript so regeneration can't change them),
  the per-note sidecar (`<name>.excalidraw.questions.md`) with atomic I/O, and `apply_markers`, the deterministic
  step that rewrites `.rag.md` tags into resolved markers (by position when tag counts match, by text similarity
  otherwise; unmatched entries are flagged stale). `rebuild` indexes each sidecar as its own `excalidraw_questions`
  card under `compute_id_from_parts(["excalidraw_questions", <note file_id>])` so rewrites update one card.
- `chunk_index.py` — passage-level chunking and embedding for citable,
  paragraph/heading/page-accurate retrieval (not just "which file," but
  "which paragraph"). Tiered: headings first, numbered-problem detection for
  problem sets, page-based fallback for paginated PDFs, and a paragraph-based
  fallback (`¶4`, `¶6-8`) for content with no page markers at all (e.g.
  `.docx`-derived essays).
- `retag.py` — corpus-wide tag mining: a holistic LLM proposal followed by
  per-candidate empirical validation against real cosine similarity, plus a
  minimum-coverage safety net so no file goes untagged. A real (non-dry-run)
  run also patches each file's own `tags:` frontmatter line in place.

The `index_search chunk` CLI holds the shared corpus write lock for a real run;
`--dry-run` remains read-only. Other index writers have not adopted this lock
yet, so this does not enable corpus-health apply actions or guarantee exclusion
against those writers.

## Design docs

`docs/superpowers/specs/indexer/2026-08-27-source-indexer-design.md` for the schema;
`docs/status/indexer/2026-08-29-source-indexer-status.md` for narrative history — real bugs
found and fixed, and the generalizations that let a second and third corpus
(essays, journal articles) reuse this unchanged.
