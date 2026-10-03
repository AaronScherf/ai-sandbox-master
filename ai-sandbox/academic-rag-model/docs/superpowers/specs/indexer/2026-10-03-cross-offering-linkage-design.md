# Cross-Offering Content Linkage: Design

## Motivation and history

Phase 1 (`2026-10-03-notes-subset-discovery-design.md`, same date, `transcribe_notes/` spec folder) made it possible to transcribe a whole prior course offering (e.g. a full previous year's lecture notes, problem sets, and recitations) into an existing course via a `.notes_subset.json` marker, without flattening its folder structure. That's now been run for real: `academic_resources/econometrics/class_2024/` is fully converted (29 PDFs) and indexed alongside the current econometrics content.

The gap Phase 1 deliberately left open: nothing connects a prior offering's content to its current-year corollary. The professor may reuse a slide deck across years, cover the same material in a differently-worded lecture note, or recycle a problem set -- none of that is visible today. This spec covers finding and surfacing those connections, for the RAG tutoring agent, for Obsidian browsing (native backlinks), and for other pipelines (`problem_gen`, `audio_generator`) that may want to query "what else is like this card" programmatically -- all three consumers were named explicitly when this was scoped during brainstorming.

A real, concrete constraint surfaced while designing this against the actual converted data: `slides1.md` now exists at two different paths --
`academic_notes/econometrics/professor_notes/processed_outputs/slides1.md` (current) and
`academic_notes/econometrics/class_2024/Class Notes/Slides/processed_outputs/slides1.md` (2024). Any Obsidian-visible link has to be written path-qualified, not as a bare filename, or it's ambiguous.

Confirmed during design: this project already has nearly everything this feature needs.
- Every index card already carries a `title+summary` embedding (`generate_index_card`, `core/indexer/index_card.py`) and a working, self-normalizing `cosine_similarity()` in the same module.
- `core/indexer/retag.py` already does exactly this shape of work -- corpus-wide, threshold-based pairwise comparison against real card embeddings, on its own explicit schedule, never per-file -- for tag clustering instead of cross-offering linking.
- `core/indexer/retag.py`'s `write_tags_to_frontmatter()` already establishes the "patch a card's own `.md` file in place, idempotently, degrade gracefully if the expected shape isn't there" pattern this needs for writing the Obsidian-visible link.
- `core/indexer/duplicate_check.py` already establishes a confidence-tiered, dismissals-ledger pattern (`.index/duplicates/dismissals.json`) for a fuzzy match that shouldn't be silently auto-resolved past a certain uncertainty, with a small CLI (`--resolve`, `--reject-pending`) for a human to act on a pending list.

So this spec is almost entirely glue across those three existing patterns, plus one genuinely new piece: knowing which "offering" a card belongs to.

## Scope

**In scope:**
- A new module, `core/indexer/offering_links.py`, with its own CLI, run on demand per course (same "separate tool, explicit schedule" philosophy as `retag.py`/`duplicate_check.py` -- not wired into every index write or into `route_notes_transcribe.py`'s own run).
- Promoting `.notes_subset.json` marker-reading from `route_notes_transcribe.py` into `core/env/academic_hub_paths.py`, plus a new `find_containing_offering_label()` there.
- One new optional index-card field, `offering_label: str | None`.
- Writing both a card-level, bidirectional `related_offerings` field and an idempotent, path-qualified Obsidian link in each matched card's own `.md` file.
- A confidence-tiered threshold (auto-write above a high bar, log to a review ledger in a middle band, ignore below it) with a dismissals ledger so a human "no, not related" decision sticks.

**Out of scope:**
- Chunk/passage-level comparison (document-level only, per brainstorming decision -- every card's existing title+summary embedding is reused as-is, zero new embedding calls).
- Any change to how Phase 1's discovery/transcription works.
- Automatic triggering (no cron integration, no hook into `route_notes_transcribe.py`'s own run) -- this is its own explicit step, run after a transcription batch.
- A UI for reviewing the pending list beyond the CLI (`--resolve`/`--reject`, mirroring `duplicate_check.py`'s exact flags).
- Backfilling `offering_label` onto cards indexed before this field existed (the comparison tool re-derives offering from each card's path directly, so it works correctly on today's data with no migration -- see Design).

## Design

### Determining a card's "offering"

A circular-import constraint shapes this: `transcribe_notes.py`'s indexing hook needs to read `.notes_subset.json` to tag a card at write time, but `route_notes_transcribe.py` (where that marker-reading currently lives) already imports *from* `transcribe_notes.py` -- so the marker logic has to live somewhere both can import without a cycle. `core/env/academic_hub_paths.py` is that place: zero internal dependencies, already imported by both.

Promote from `route_notes_transcribe.py` into `academic_hub_paths.py`, unchanged in behavior:
- `_SUBSET_MARKER_FILENAME = ".notes_subset.json"`
- `_read_subset_marker(dir_path) -> dict | None` (exact logic already hardened by the Phase 1 review fix pass: BOM-tolerant, rejects non-dict JSON with a warning, never raises)

Add:
```python
def find_containing_offering_label(path: str) -> str | None:
    """Walks path's ancestors (on the academic_resources/ side -- callers
    pass a resources-rooted path, or convert first) up to the course root,
    returning the nearest ancestor's marker label, or None if path isn't
    under any marked subset. Stops at the course root (parts[1]) rather
    than walking past it -- a marker can't claim a whole course."""
```

`route_notes_transcribe.py` imports the promoted names instead of defining them; its own tests move with them (pure refactor, no behavior change -- the full existing test suite for Phase 1 is the regression check).

### Card schema addition

`index_card.py`: `generate_index_card()`, `make_failure_card()`, and `reconcile_and_write()` each gain an `offering_label: str | None = None` parameter, stored as a new card field. `transcribe_notes.py`'s `_write_markdown_and_index()` computes it once per file:

```python
resources_pdf_path = pdf_path if "academic_resources" in pdf_path else to_resources_root(pdf_path)
offering_label = find_containing_offering_label(resources_pdf_path)
```

Every existing card simply lacks this key; every reader treats a missing key the same as `None` (primary/current, not any named offering). No migration required for the schema to be valid -- see below for why existing `class_2024` cards still compare correctly despite predating this field.

### The comparison engine

`core/indexer/offering_links.py`, mirroring `retag.py`'s shape:

```python
def derive_offering_for_card(academic_hub_root: str, card: dict) -> str | None:
    """Re-derives offering straight from card["path"] via
    find_containing_offering_label(), independent of whether the stored
    offering_label field is present -- this is what makes the tool work
    correctly on class_2024's cards today without a backfill: they
    predate the stored field, but their path alone is enough."""

def find_cross_offering_matches(
    cards: list[dict], auto_threshold: float, review_threshold: float,
) -> tuple[list[tuple[dict, dict, float]], list[tuple[dict, dict, float]]]:
    """Every pair of cards whose derive_offering_for_card() values differ,
    per the brainstorming decision: subset-vs-subset counts too, not just
    subset-vs-primary. Two primary cards (both None) are therefore never
    compared by this tool at all -- that's retag.py's subject-clustering
    job, not this one's. Returns (auto_matches, review_matches) by
    cosine_similarity() against each card's existing embedding."""
```

Starting threshold constants (to be empirically calibrated against the real `class_2024`-vs-current-econometrics embeddings during implementation, the same way `retag.py`'s `TAG_ASSIGNMENT_THRESHOLD = 0.65` was tuned against real data rather than guessed -- the implementation plan includes a dedicated calibration task that computes the real pairwise distribution before locking these in):

```python
OFFERING_LINK_AUTO_THRESHOLD = 0.90   # starting guess, calibrate against real data
OFFERING_LINK_REVIEW_THRESHOLD = 0.80  # starting guess, calibrate against real data
```

These need to sit meaningfully higher than `retag.py`'s 0.65 -- that threshold answers "is this card about the same general subject as this tag," a loose bar; this one answers "does this specific document likely correspond to that specific document," a much tighter claim.

### Writing a match

On an auto-match (and on a `--resolve`d review match), both directions get written:

1. **Index side** -- each card gets a `related_offerings` entry appended (replacing any prior entry for that same pair, so a rerun is idempotent):
   ```json
   {"file_id": "...", "path": "academic_notes/...", "similarity": 0.92, "confidence": "high"}
   ```
2. **Markdown side** -- an idempotent, delimited section appended to the bottom of each card's own `.md` file:
   ```markdown
   <!-- offering-links:start -->
   ## Related notes
   - [[class_2024/Class Notes/Slides/slides1|2024: Slides 1]] (similarity: 0.92)
   <!-- offering-links:end -->
   ```
   The link target is the *other* card's `path` with the `academic_notes/` prefix stripped and `.md` suffix removed -- `academic_notes/` is the actual Obsidian vault root (it's `academic-hub/academic_notes/`'s own standalone git repo, synced as the vault), not `academic-hub/` itself, so a path relative to `academic-hub/` would be wrong inside the vault. The alias (`2024: Slides 1`) is the other card's `offering_label` (or "current" if `None`) plus its title. Re-running replaces the block between the two HTML comments wholesale (same idempotent-replace philosophy as `write_tags_to_frontmatter`'s regex-replace), so matches never duplicate across reruns and a dismissed-then-reconfirmed pair doesn't leave a stale entry behind.

A card with no frontmatter block or a missing `.md` file on disk is skipped for the markdown-side write (logged, not fatal) but still gets its index-side `related_offerings` entry -- same failure-isolation philosophy as the rest of this corpus's indexer code (an indexing side-effect must never block the thing it's indexing).

### Review ledger and dismissals

Mirrors `duplicate_check.py`'s exact shape, new files under `.index/offering_links/`:
- `review.json` -- pending matches in the middle confidence band, `{file_id_a, file_id_b, similarity, course}`.
- `dismissals.json` -- confirmed non-matches. `duplicate_check.py`'s own `record_dismissal`/`is_dismissed` hardcode `.index/duplicates/dismissals.json` (not parameterized by path), so they can't be imported verbatim for a second ledger at a different path -- `offering_links.py` implements its own, structurally identical pair of functions against `.index/offering_links/dismissals.json` instead. Not worth refactoring `duplicate_check.py` to parameterize its path just to share four lines of dict-and-list bookkeeping.

CLI surface on `offering_links.py`, matching `duplicate_check.py`'s flag names so a user who's already used one tool recognizes the other:
```
python -m core.indexer.offering_links --course econometrics [--dry-run]
python -m core.indexer.offering_links --resolve FILE_ID_A:FILE_ID_B   # confirm a pending review match
python -m core.indexer.offering_links --reject FILE_ID_A:FILE_ID_B    # dismiss permanently
```

### Error handling

- A card with no embedding (a `needs_indexing` failure card) is excluded from comparison entirely -- there's nothing to compute a similarity against.
- A malformed `review.json`/`dismissals.json` is treated as empty with a warning, never a hard failure (same "a hand-edited/truncated ledger must not take down a whole run" philosophy `duplicate_check.py` already documents for its own dismissals file).
- The markdown-append step never blocks the index-side write; the two are independent best-effort steps, same ordering rationale as `_write_markdown_and_index`'s own indexing-must-never-block-transcription comment.

### Testing

- `find_containing_offering_label()`: unit tests at various path depths, marker present/absent/malformed, reusing Phase 1's existing fixture patterns.
- `derive_offering_for_card()`: works correctly from `card["path"]` alone, with and without a stored `offering_label` (covers the no-backfill claim directly).
- `find_cross_offering_matches()`: pure-function tests with synthetic embeddings -- same-offering pairs never compared, cross-offering pairs correctly bucketed into auto/review/ignored by threshold.
- Markdown-append idempotency: running twice produces one block, not two; a dismissed-then-later-reconfirmed pair's block reflects the current state, not a stale one.
- Dismissals/review ledger round-trip, mirroring `duplicate_check.py`'s own existing tests for the same functions.
- End-to-end against a small synthetic two-offering fixture course (not the real corpus) verifying a known near-duplicate pair gets linked on both sides, in both the index and both `.md` files.

## Migration / rollout

No backfill needed to run this correctly against today's data (`derive_offering_for_card()` reads path directly). `offering_label` starts appearing on cards going forward, as they're (re)indexed; a separate, optional backfill utility to populate it onto already-indexed cards can be written later if a consumer actually needs it from the index rather than re-deriving it, but nothing in this spec depends on that existing.
