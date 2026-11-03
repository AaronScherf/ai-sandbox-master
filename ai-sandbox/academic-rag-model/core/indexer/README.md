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
  `handwritten_notes`. The Markdown content hash (`compute_content_hash`) ignores location-only frontmatter fields (`LOCATION_FIELDS`), so moving a note does not make its card stale; cards that stored the old raw-bytes hash still compare via `content_hash_matches`. One-time migration of stored hashes: `python -m tools.rehash_content_hashes --hub-root <hub>` (dry run; review the `stale` list), then `--apply`. It rewrites a card's hash and its chunk records' hash together, only when the file is unchanged since the card was written; no API calls, safe to rerun. `source_pdf_path` is the identity anchor
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

The `index_search rebuild` CLI, real `chunk` and `retag` runs, and standalone
`related` subset-linking runs hold the shared corpus write lock. `retag` also
locks an available nested `academic_notes` repository because it rewrites
Markdown frontmatter. Dry runs remain read-only. Other index writers have not
adopted this lock yet, so this does not enable corpus-health apply actions or
guarantee exclusion against those writers.

## Part-layout discovery and safe rebuilds

For `academic_{notes,resources}/<course>/part_N/<category>/...`, discovery
matches resources to notes by `(part_N, category)`. A valid
`.notes_subset.json` marker also admits resources in an otherwise unmatched
offering. Textbook folders are excluded from notes-PDF discovery at any depth
and found by the separate book walker. Files directly under a course or
`part_N` have no category and are reported without indexing. Legacy courses
retain their prior discovery behavior. In part-layout courses, an authored
same-stem Markdown source supersedes its PDF export in both route and rebuild
discovery.

Preview all producer and Markdown work without constructing an API client:

```powershell
python -m core.indexer.index_search --root <academic-hub> rebuild --course econometrics --plan --json
```

The plan reports each target's action and estimated paid cards, and whether
the default `--max-paid 25` cap would refuse a run. The cap covers producer
and Markdown card work before any index write. `--max-markdown-paid` remains
a separate Markdown cap. A failed producer card can be retried in isolation:

```powershell
python -m core.indexer.index_search --root <academic-hub> rebuild --course econometrics --file academic_notes/econometrics/part_1/problem_sets/processed_outputs/pset3.md --plan --json
```

The exact retry requires `needs_indexing`, a matching source PDF, and a
single card in that course. It keeps the existing identity and source fields,
generates before replacing the failure card, and skips the Markdown, orphan,
and subset passes. Run the corresponding command without `--plan` only after
coordinating the index writer and approving its paid call.

`python -m tools.relocate_index_paths --root <academic-hub> --course <course> --baseline ca3b286`
previews the one-shot path migration without API calls or
writes. Its opt-in `--apply --writer-coordinated` verifies moved content and
frontmatter, remaps matching chunk hashes and catalog paths, and backs up the
changed index files outside the repository. Catalog roles and owner decisions
are preserved. Catalog regeneration is deferred until the course-materials
part-layout fixes land; new files remain uncatalogued until then.

## Markdown-only notes and companions

`rebuild` recursively discovers useful Markdown under `academic_notes/<course>/`,
including `processed_outputs/`, after reserving paths owned by the PDF, video,
textbook, and Excalidraw producers. A Markdown file with no verified upstream
producer gets `source_kind: "markdown_only"` and null `source_pdf_path` /
`source_asset_path`. This means its origin is unknown; it does not assert that
the file is derivative. Producer-confirmed generated children, such as distinct
textbook chapters and Excalidraw question sidecars, get
`source_kind: "generated_companion"` and, when known, `companion_of_file_id`,
`companion_role`, and `relationship_basis`. An authored hint can have a verified
parent link while retaining unknown origin. Existing specialized sidecar IDs
are preserved. A `.rag.md` already attached through a parent card's
`rag_md_path` is one alternate rendering of that card, not a duplicate card.
Machine manifests and raw Excalidraw canvas files are excluded; ambiguous
producer ownership is reported for review. New and changed Markdown cards
are capped at 25 per `rebuild` invocation unless `--max-markdown-paid N` is
raised after a preview. Each paid card normally uses one generation and one
embedding call; passage chunking is a separate API step.

Read-only preview (no API client or index write):

```powershell
python -m core.indexer.index_search --root <academic-hub> index-md --course econometrics --json
python -m core.indexer.index_search --root <academic-hub> index-md --course econometrics --file academic_notes/econometrics/part_1/problem_sets/processed_outputs/problem_set_1.md --json
```

Exact-file application requires the corpus writer to be coordinated with all
other `.index/` writers. It holds the shared corpus lock, writes cards and
course rollups atomically, and returns a JSON result with a post-write audit:

```powershell
python -m core.indexer.index_search --root <academic-hub> index-md --course econometrics --file academic_notes/econometrics/part_1/problem_sets/processed_outputs/problem_set_1.md --apply --writer-coordinated --max-markdown-paid 1 --json
```

`index-md --apply` requires `--file`; use `rebuild --course` for a bounded
course batch. The `index-md` JSON result gives path, classification, origin,
parent relationship, action, content hash, estimated paid calls, and status.
Run `chunk --course <course> --file-id <id> --json` after indexing when
passage-level search is needed. The scanner does not edit the nested
`academic_notes/` repository.

## Design docs

`docs/superpowers/specs/indexer/2026-08-27-source-indexer-design.md` for the schema;
`docs/status/indexer/2026-08-29-source-indexer-status.md` for narrative history — real bugs
found and fixed, and the generalizations that let a second and third corpus
(essays, journal articles) reuse this unchanged.

## Hub folder vocabulary

Which folder names are categories, group layers or plain sub-structure lives in `academic-hub/hub_config.json` (loaded by `core/env/hub_vocabulary.py`), not in code. `parse_hub_path` takes the nearest ancestor folder the vocabulary knows as a category; folders between the course and it are group layers (any depth). A path with no known category parses exactly as before, so an unconfirmed folder name changes nothing. A missing or invalid config falls back to the old rules with a warning.

Maintaining it (no API calls):

1. `python -m tools.hub_vocabulary propose --hub-root <hub>` prints candidate names learned from the tree (category = content in two or more courses; group = numbered/year/`part_N` or above a known category; ignore = infrastructure-looking names). Read-only.
2. `python -m tools.hub_vocabulary confirm NAME {category,group,ignore} --hub-root <hub> [--alias-of CANONICAL]` stores one answer (`source: owner`). A different later answer needs `--replace`.
3. `python -m tools.hub_vocabulary impact --hub-root <hub>` lists the files and cards whose category or groups would parse differently from the pre-vocabulary rules. Run it after confirming names and before the next transcription or index run: a newly confirmed category can make PDFs eligible for transcription that were skipped before.
