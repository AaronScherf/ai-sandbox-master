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

`--file` also accepts one cardless Excalidraw output
(`processed_outputs/<name>.excalidraw.rag.md` or `.excalidraw.questions.md`)
whose `<name>.excalidraw.md` scene exists. It plans and creates that single
card (`reason: no_card`, one paid card) with the same identity and fields a full
`rebuild` would use, without the Markdown, orphan, or subset passes, so a few
transcribed scenes can be indexed without also carding every other cardless
file. It refuses an empty output, a missing scene, or a file whose identity
already has a card.

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

## Reconcile and review

> **Status (2026-11-06): frozen as built.** The first live runs (`hub_review export --no-raise`, `repair` dry run, `corpus_health scan`) found 0 moves, 0 ambiguous items and 0 orphans. The similarity thresholds are untuned (no data), the review page has not been validated in a browser, and the other pipelines are not wired to preflight. See `docs/status/indexer/2026-11-06-hub-path-resilience-p4-steps-3-7-handoff.md`.

When files are moved or renamed, cards point at dead paths. `reconcile.py` finds them (pure read, no model
calls) and `reconcile_apply.py` repairs or raises them for review. Spec:
`docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md`.

Commands (run from `academic-rag-model/`; flags go AFTER the subcommand):
- `python -m tools.write_hub_ids --hub-root HUB [--apply]` stamps a stable `hub_id` into note
  frontmatter (dry run by default). It edits files in `academic_notes/`, a separate git repo: run the
  dry run first, then `--apply`, then commit there yourself. Notes with an empty frontmatter block and
  plain `.excalidraw` JSON scenes are skipped (`--include-excalidraw-json` opts the latter in once
  Excalidraw is verified to keep the key). Derived outputs (anything under `processed_outputs/`,
  `*.rag.md`, `*.excalidraw.questions.md`, video notes with a `.meta.json` sidecar) are listed as
  skipped "derived output": their producers rewrite them and would drop the id.
- `python -m tools.hub_review repair --hub-root HUB [--apply]` is the only command that applies exact
  moves. Without `--apply` it lists each `moved` difference (dry run); with `--apply` it repairs them
  (takes the corpus write lock once) and prints each `repair_id`.
- `python -m tools.hub_review undo REPAIR_ID --hub-root HUB` reverts one repair (exit 1 if the id is
  unknown, already undone, or the card has moved since). An undone move is never auto-applied again;
  it shows up on the review page as a relink candidate instead. Undoing a relink chosen on the page
  reopens that item.
- `python -m tools.hub_review export|page --hub-root HUB [--out PATH] [--no-raise]` lists pending
  relink / orphan / offering-link / pairing items; `page` bakes them into one review HTML page. Without
  `--no-raise` it first raises relink items into the corpus-health ledger (takes the write lock, sets
  `link_state: unresolved` on cards). It never applies moves; when some are waiting it prints
  "N exact moves are waiting: run `repair`" to stderr.
- `python -m tools.hub_review apply decisions.json --hub-root HUB [--dry-run]` applies decisions.
- Decision flow: publish the page as an Artifact with a `db` capability; viewers write
  `{item_id, action: accept|decline|defer, chosen, ts}` into its `decisions` collection; dump that to
  `decisions.json`; run `apply`. Each decision goes through the owning module's `resolve`/`reject`.

Typical order after reorganizing folders: `write_hub_ids` (dry run, then `--apply`, commit in
`academic_notes/`) BEFORE moving anything, so moved notes and clones are matched by `hub_id`; move
files; `rebuild`; `hub_review repair` (dry run, then `--apply`); `hub_review page` for what is left.

Caveats:
- Stamping hub_ids rewrites the notes' raw bytes. The content hash ignores the `hub_id` line, but two
  consumers still key on a legacy raw-bytes hash: the concept-graph syllabus digest
  (`agent/concept_graph/stages/gaps.py`) and audio states that still hold a legacy hash re-run once
  after stamping. To avoid the audio re-run, run the audio pipeline once before stamping (it upgrades
  its states to the canonical hash); otherwise accept one local TTS regeneration (local, not paid).
- A repair clears the card's `orphaned` flag, and `rebuild` clears it on every card it sees again.

Repairs are logged to `.index/reconcile_log.jsonl` (pending then done, crash-recoverable).
`undo_repair(hub_root, repair_id)` restores the card's `path`/`rag_md_path` (and an `orphaned` flag
only if the log recorded it). Repairs touch card fields only; note frontmatter `source_*` hints are
not rewritten. A card keeps its `hub_id` and `link_state` when it is regenerated.

Matching tiers (strongest first): `hub_id` (notes), canonical content hash (derived `.md`), byte hash
(PDFs and other binaries), git rename of the card path, then filename/course/body similarity.
Similarity needs evidence, not just a high ratio: name and course alone top out below the threshold
(no rescaling when the old text is unavailable), and the body term counts shared 3-word shingles by
containment scaled by `min(1, shared / MIN_SHARED_SHINGLES)`, so a note that grew tenfold around its old
text is still offered while a short note cannot match on coincident words. Each similarity candidate
carries `evidence` (the shared passage plus the opening of the old and new file) and the review page
shows it under "Compare text".
Identical files (several exact candidates for one note): `resolve(..., chosen, copies=[...])` relinks the
card to `chosen` and gives each copy (a `.md` note whose canonical content hash equals the chosen file's)
its own card, cloned from the original with `copy_of_file_id` and a fresh `hub_id` (`replace_hub_id`). Whether
a copy is still identical is derived (`index_card.copy_status`: its `content_hash` equals the origin's), so an
edited copy simply becomes its own note and keeps the provenance; `carry_note_identity` keeps the field across
card rebuilds. Not for PDFs: their card id is the byte hash, so identical PDFs cannot hold separate cards.
Index numbers that disagree between two file names (`lecture_03` / `lecture_04`) give the name no weight.
Safety rules:
- Only exact evidence yields `moved`, and only `hub_review repair --apply` (or `apply_repairs` from
  Python) applies it. Git renames and similarity only ever produce ranked `ambiguous` candidates for
  a human.
- Two stamped notes that swapped places are two `ambiguous` items (each offered the other's path),
  never a move. Accepting one is refused while the other card still holds that path; swap the files
  back (or rename one aside), then reconcile again.
- Several exact candidates, or one target contested by two cards, is `ambiguous`: nothing is linked.
- No candidate is `orphan`: report only. Reconcile and apply never delete or modify a content file.
- A content-tier card whose path still exists is never hashed (an in-place edit is staleness, not a
  location problem).
- A target already held by another card is never used; an explicit choice must be a listed candidate.

Scan, preflight and vocabulary (P4):
- The corpus-health scan (`tools/corpus_health/cli.py`) raises relink and orphan items into the ledger
  (ledger only, never `link_state`; skipped with `--no-state`), reports duplicate `hub_id`s and new
  folder names (`vocab_name`) as findings, and prints "N exact moves waiting: run `hub_review repair`".
  Failures here are non-fatal `warnings` on the report.
- Preflight (`core/indexer/preflight.py`): `index_search chunk|rebuild|index-md --apply|retag`,
  `transcribe_notes`, `route_notes_transcribe`, `transcribe_excalidraw` and the audio pipeline refuse
  (exit 2, pointing at `python -m tools.hub_review page
  --hub-root HUB`, or `repair` for waiting moves) when an open relink item or a waiting exact move is
  in their way. Orphans only warn. Read-only modes (`chunk`/`retag --dry-run`, `index-md` without
  `--apply`, `rebuild --plan`, `query`/`ask`) warn instead of refusing; `transcribe_notes`,
  `route_notes_transcribe`, `transcribe_excalidraw` and audio refuse except for `--dry-run` (transcribe
  and route: `--dry-run` without `--submit`/`--collect`). `--ignore-unresolved` bypasses.
  The tree fingerprint (notes, resources and the hub's `.index/`) and remembered waiting moves live in
  `<state_dir>/preflight.json` (local, not `.index/`: mtimes are per machine). When another writer holds
  the write lock, preflight reconciles read-only and writes nothing. Not yet wired: postprocess_notes,
  textbook conversion, video notes, migrate_sources_to_resources and the agent CLIs (tracker).
- `python -m tools.write_hub_ids --hub-root HUB --fix-duplicates [--apply]` repairs two live notes that
  carry the same `hub_id` (dry run by default).
- Vocabulary: folder names not yet in `hub_config.json` become `vocab_name` items on the review page;
  accepting one goes through `tools.hub_vocabulary.confirm`. A declined name is asked once.

Not yet: `ACADEMIC_HUB_ROOT` discovery (P5). Status:
`docs/status/indexer/2026-11-05-hub-path-resilience-p4-status.md` (P4),
`docs/status/indexer/2026-11-03-hub-path-resilience-p3-status.md` (P3).

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
3. `python -m tools.hub_vocabulary impact --hub-root <hub>` lists the files and cards whose category or groups would parse differently from the pre-vocabulary rules. Run it after confirming names and before the next transcription or index run: a newly confirmed category can make PDFs eligible for transcription that were skipped before, and `newly_eligible_pdfs` in its output lists exactly those (a paid run). The pipelines read `academic-hub/hub_config.json` (or `ACADEMIC_HUB_CONFIG`); pass `--config` if `<hub-root>/hub_config.json` is not that file, and note other worktrees see a confirmation only once it is merged.
