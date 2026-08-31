# Source Indexer

The layer that turns a growing pile of converted textbooks, notes, essays, and
journal articles into a searchable corpus. Given a query like "teach me about
linear algebra," this is what ranks the most relevant files — the
source-selection layer underneath the [RAG tutoring agent](../rag/), not the
tutor itself. Every other conversion pipeline in this repo (`textbook/`,
`notes/`, `essays/`, `journal_articles/`) hooks into this module so a newly
converted document gets indexed as a normal side effect of that pipeline
running, not a separate step someone has to remember.

Run any script here as a module from the `marker-conversion/` root, e.g.
`python -m indexer.index_search query "..."` — see the root
[`README.md`](../README.md) for why (package-qualified imports need
`marker-conversion/` on `sys.path`).

## Key files

- `index_card.py` — per-file index cards keyed by `file_id` (a hash of the
  source file's own bytes, so a card survives being moved or renamed), plus
  free course-level rollups computed from existing card data. `known_doc_types`
  is a parameter here, not a hardcoded constant, so a non-academic-hub corpus
  (e.g. `essays/`, `journal_articles/`) can classify into its own vocabulary
  instead of being force-fit into `textbook`/`problem_set`/`ta_notes`/
  `handwritten_notes`.
- `index_search.py` — the `rebuild`/`query`/`ask` CLI, and the two-stage
  (course-then-file) cosine-similarity search. Query-side functions
  (`search`, `search_passages`) take a **list** of corpus roots, not one, so a
  single query can span multiple corpora (e.g. `academic-hub` and `research/`)
  at once — candidates are tracked as `(root, course)` pairs so two corpora
  with a same-named course never collide. `rebuild`/`retag`/`chunk` stay
  single-root (`--root`, given exactly once) since those write into one
  corpus's own `.index/`.
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

## Design docs

`docs/superpowers/specs/2026-08-27-source-indexer-design.md` for the schema;
`docs/2026-08-29-source-indexer-status.md` for narrative history — real bugs
found and fixed, and the generalizations that let a second and third corpus
(essays, journal articles) reuse this unchanged.
