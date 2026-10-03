# Subset-Note Linking: Design

**Status:** approved in conversation 2026-10-03; written spec pending review.
**Package:** `core/indexer/` (shared by every pipeline; changes need caller tests).

## Motivation

Excalidraw lecture notes now exist in two versions per lecture: the original
handwriting-only canvas, and a "with slides" canvas where the lecture slides
are embedded beside the same handwriting. Both are kept on disk. The slides
version's content is a strict superset of the handwriting-only version (same
ink, plus the slides).

The indexer has no relationship between cards. `search()` returns one result
per card, and `search_passages()` ranks chunks across the shortlisted files, so
the two near-identical versions both occupy top-k slots and crowd out other
sources. This hurts the RAG tutor, the problem generator, and the optional
grounding step in `transcribe_excalidraw.py`.

**Goal:** keep both files and both cards, but have default search return only the
superset, with the subset reachable on request.

## Decisions (made in conversation)

1. Search default: **collapse the pair to the superset** (slides version). The
   subset stays indexed and is returned with `include_subsets=True` / `--include-subsets`.
2. Pairing: **detect automatically, then confirm by content**, with a manual
   override file for mistakes.
3. Storage: a **`subset_of` field on the subset's card** (not a separate links
   file, not query-time dedupe).

## Evidence for the confirmation rule

Measured on the real microecon index (2026-10-03), `microecon.json` excalidraw cards:

| Signal | True pairs | Non-pairs |
|---|---|---|
| Card embedding cosine | 0.879 to 0.920 | up to 0.897 |
| Handwriting word-3-gram containment (subset in superset's `[Handwritten]` blocks) | 0.59 to 0.83 | 0.00 to 0.02 (16 pairs) |

Card embeddings are useless here: all microeconomics lectures are topically
alike, and true and false pairs overlap. Handwriting containment separates
them cleanly because both versions transcribe the same ink. The threshold of
**0.3** sits far from both clusters. Caveat: calibrated on only 4 true pairs.

## Data model

- Subset card gains `subset_of: <superset file_id>` and `subset_link_score: <float>`.
- Superset card is unchanged.
- One level only: a subset points at a superset that is not itself a subset.
- Existing `reconcile_and_write` copies the old card dict, so unknown fields
  survive reconciliation; no schema migration is needed.

## Component: `core/indexer/related.py` (new)

- `handwriting_text(raw_md_path) -> str`: for a slides note, only the `**[Handwritten]**`
  blocks (chunk markers stripped); for a handwriting-only note, the whole body.
  Reuses `split_labeled_segments` logic (kept in `transcribe_excalidraw.py`;
  this module must not import the pipeline, so the small label-splitting
  helper is moved to a shared location or duplicated minimally; decide in the plan).
- `containment(subset_text, superset_text, n=3) -> float`: fraction of the
  subset's word n-grams (tokens: alphabetic words of 3+ chars and LaTeX
  commands, lowercased) that appear in the superset's.
- `find_candidates(cards)`: pairs of `excalidraw_notes` cards in the same
  course and the same folder whose filenames contain the same `YYYY-MM-DD`
  date, where the superset's raw transcript frontmatter has
  `embedded_slides: true` and the subset's does not. Filename with no date -> no candidate.
  Raw transcript path is derived from the card's `.rag.md` path (drop `.rag`).
  A missing raw file excludes the card.
- `link_subsets(academic_hub_root, course, dry_run=False) -> list[Link]`:
  1. load the shard and overrides;
  2. for each candidate subset, score every candidate superset; pick the highest
     score >= `CONTAINMENT_THRESHOLD` (0.3);
  3. apply overrides: `force` links regardless of score, `block` (subset
     file_id) prevents any link;
  4. write `subset_of`/`subset_link_score` on linked subsets; remove them from
     cards that no longer qualify (superset deleted, text changed, now blocked);
  5. save the shard only if something changed. Idempotent.
- Overrides file: `.index/links_overrides.json`:
  `{"force": [{"subset": "<id>", "superset": "<id>"}], "block": ["<id>"]}`.
  Missing file = no overrides. Not a course shard, so `list_courses` and
  `index_search.py`'s shard scan must ignore it (same treatment as `courses.json`/`tags.json`; see
  `duplicate_check.py`'s note on `.index/duplicates/` for why a top-level
  `.index/*.json` would otherwise surface as a phantom course).
- CLI: `python -m core.indexer.related [--root R] [--course C] [--dry-run]`
  prints each link with its score and applies unless `--dry-run`.

## Search integration (`index_search.py`)

- `search(..., include_subsets: bool = False)`. After the existing filters
  (needs_indexing/embedding, doc_type, has_solutions, max_level), and unless
  `include_subsets`, drop every candidate card whose `subset_of` is the
  `file_id` of another surviving candidate in the same root.
- Consequently a stale or dangling link never hides content: if the superset is
  missing, unindexed, lacks an embedding, or is excluded by the caller's own
  filters, the subset is returned normally.
- `search_passages` calls `search()` for its file-level pass, so it inherits the
  behavior; its signature gains a pass-through `include_subsets` for completeness.
- CLI `query`/`ask` gain `--include-subsets`. No existing caller changes
  behavior except by no longer receiving duplicates.

## Hooks

- `transcribe_excalidraw.write_outputs`: after `reconcile_and_write`, call
  `link_subsets(academic_hub_root, course)`. Wrapped in the existing try/except
  style: failure prints a warning, never fails the note.
- `index_search.rebuild`: after the per-course loop, call `link_subsets` for each
  course touched. Non-fatal.
- Because a new slides note is indexed after the handwriting-only note exists
  (or vice versa), linking happens on whichever write comes second.

## Testing

- Unit (`tests/core/indexer/test_related.py`): tokenization/containment; handwriting
  extraction for both note kinds; candidate rules (date match, slides flag
  direction, same folder, missing date, missing raw file); a same-day
  lecture-vs-recitation negative; threshold boundary; overrides (force, block);
  stale-link clearing; idempotence; dry-run writes nothing.
- Search (`tests/core/indexer/test_index_search.py`): subset hidden by default;
  returned with `include_subsets=True`; returned when superset missing /
  filtered out / lacks embedding; `search_passages` inherits.
- Hooks: `write_outputs` and `rebuild` call the linker and survive its failure.
- Regression: the full existing suite (1857+ tests at 2026-10-03) must pass.
- Real-data check on the microecon index via `--dry-run`: expect 4 links
  (`Microeconomics lecture 2026-09-07`, `... lecture 2026-09-10`, `Microeconomics 2026-09-15`,
  `Microeconomics 2026-09-17`, each to its "with slides" note), none for 09-22 (no
  handwriting-only version), and none for the orphaned `Drawing 2026-09-07` card
  (its raw transcript no longer exists, so it is excluded).

## Out of scope

- Removing the stale orphaned `Drawing 2026-09-07` card (no raw transcript, so it stays unlinked and still appears in default search until removed).
- Chunk-level partial-overlap dedupe.
- Non-Excalidraw pairs (PDF vs scan, etc.).
- Multi-hop chains.
- The `[Question]` resolving step (separate effort).

## Open questions for the implementation plan

- Where the `**[Slide]**`/`**[Handwritten]**` splitting helper lives so
  `related.py` does not import a pipeline module.
- Exact n-gram tokenization details (kept simple; must reproduce the measured 0.59 to 0.83 / <= 0.02 separation).
- Whether `link_subsets` should also record `subset_linked_at` for debugging (leaning no; YAGNI).
