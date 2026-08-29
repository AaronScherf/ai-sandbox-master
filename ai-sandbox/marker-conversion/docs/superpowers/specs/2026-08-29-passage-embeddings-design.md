# Passage-Level Embeddings Design

Brainstormed and approved with the user 2026-08-29, as a direct follow-on
to the source indexer (`docs/superpowers/specs/2026-08-27-source-indexer-design.md`)
and per the recommendation recorded in that spec's §9 and
`docs/2026-08-29-source-indexer-status.md`'s "What's next".

## 1. Problem & goals

The source indexer answers "which *file* is relevant to this query" —
useful for source selection, but not what an interactive tutoring model
needs to ground and cite a specific answer. That needs "which *passage*
(a few paragraphs -- one theorem, one problem) answers this question."

Goal: chunk every already-indexed file into citable passages, embed each
one, and add a passage-level search on top of the existing file-level
search — reusing the file-level ranking as a coarse pre-filter rather
than building a new flat search over every chunk in the corpus.

Not a goal here: the RAG model itself (generation, citation formatting,
conversational tutoring logic). This spec is retrieval infrastructure
only, same scoping boundary the original indexer spec drew for itself.

**Real-corpus scale, confirmed live (2026-08-29):** 8.8MB of `.md`/
`.rag.md` content across the current 30 files, 85% of it from the 5
textbooks. At a ~2000-3000 char chunk target this is roughly
**4,000-8,000 chunks** — meaning batched embedding calls are a real
requirement here, not an optimization, and this will keep scaling with
textbook count specifically as the corpus grows.

## 2. Architecture

A new module, `chunk_index.py`, deliberately separate from
`index_card.py` (per-file cards, hook-driven) for the same reason
`retag.py` is separate: chunk generation runs on its own explicit
schedule (`index_search.py chunk`), not automatically inside
`transcribe_notes.py`/`convert_textbook.py`'s existing hooks. Two
reasons to keep it a separate pass rather than wiring into 3 existing
hook points immediately: this is a first-time capability, lower risk
built and proven standalone first; and hook-time chunking would mean a
single textbook conversion run also pays for potentially hundreds of
chunk-embedding calls inline, with no separate control over when that
cost is paid.

```
chunk_index.py          # chunk_file(), generate_chunks_for_file(), chunk() orchestration, storage I/O
index_search.py         # + search_passages(), + CLI wiring only (`chunk` subcommand, `query --passages`)
.index/chunks/<course>.json   # new, parallel to <course>.json (file cards)
```

Same division of responsibility as `retag.py`/`index_search.py` today:
the orchestration function (`chunk()`, analogous to `retag()`) lives in
the dedicated module, not in `index_search.py` -- its CLI parser just
imports and calls it, the same way it already does for `retag()`.

## 3. Data model

`.index/chunks/<course>.json`: a flat list, one entry per chunk,
parallel to how `<course>.json` holds file cards.

```python
{
    "chunk_id": "40bdcffc053227ac-014",   # f"{file_id}-{chunk_index:03d}"
    "file_id": "40bdcffc053227ac",        # links back to the file's own card
    "chunk_index": 14,                     # 0-based position within the file, reading order
    "tier": "heading",                     # "heading" | "problem_number" | "page"
    "heading_path": ["3", "3.7"],          # set when tier == "heading", else None
    "problem_label": "Problem 4",          # set when tier == "problem_number", else None
    "page_range": [44, 45],                # always set, every tier -- confirmed live: both
                                            # notes and textbook .rag.md carry <!-- page N -->
    "text": "### 3.7 Optimization over a Convex Set\n\n...",
    "embedding": [0.0123, -0.0456, ...],
    "embedding_model": "gemini-embedding-001:768",  # same model/dim as file-level cards
    "content_hash": "91bfb2d2b836421a",    # the PARENT FILE's content_hash at generation
                                            # time (index_card.compute_content_hash's output
                                            # for that file), not a hash of the chunk's own text
}
```

`text` is stored directly, not re-derived from the source file at query
time -- mirrors how a card stores `summary` as a derived-but-stored
value. Keeps a chunk servable/citable without re-parsing the source
file on every read, at the cost of roughly duplicating the corpus's own
byte size in `.index/chunks/` (a few MB of JSON at current scale --
acceptable; embedding vectors themselves, 768 floats per chunk, are the
actual dominant storage cost, not chunk text).

**Staleness** reuses the file-level signal directly, no new mechanism:
at generation time, compare the file's *current* `content_hash`
(already on its card, per spec §4.3's revised staleness design) against
what's stored on its existing chunks. A mismatch means the whole file's
chunks are stale -- regenerate all of them for that file. One file, one
all-or-nothing regeneration event, same mental model file cards already
use, not an incremental per-chunk diff.

## 4. Chunking algorithm

Three tiers, tried in order, each empirically validated before being
trusted -- the same "don't trust an inferred structure on its own
say-so" philosophy `retag.py`'s discovery phase already uses for tag
candidates.

```python
def chunk_file(text: str, doc_type: str, folder_category: str) -> list[RawChunk]:
    ...
```

**Tier 1 -- headings.** Split on markdown `#`/`##`/`###` lines. For
`doc_type == "textbook"` only, skip everything before
`describe_images.py`'s existing `load_front_matter_end()` boundary
first -- confirmed live that a textbook's front matter (title page,
author, table of contents) gets marked with `#` by Marker's conversion,
which would otherwise produce garbage chunks (`Axler_...rag.md`: "#
Sheldon Axler", a bare author name, is literally one of its headings).
Notes files don't have this problem -- confirmed live, `LN_Optimization.md`'s
table of contents is plain text, never marked with `#` at all, so no
front-matter skip is applied there. Used as-is if the file has enough
headings to produce reasonably-sized sections (see the size cap below,
which every tier is subject to regardless of which one fires).

**Tier 2 -- numbered-problem detection**, attempted only when
`folder_category` is `problem_sets` or `recitation_slides`, and only
when tier 1 didn't already produce enough real structure. Real
numbering conventions were confirmed to vary file to file within this
one corpus -- `old_exam_2021.md` uses `1. **(40 points)**...`,
`old_problem_set.md` uses plain `1. For each of...`, `Practice
Sheet.md` uses `**Practice Problem 1. Involutions**` (bold-wrapped, not
a real heading, and matched zero of the first two patterns). A small
pattern set covers the confirmed-real cases:

```python
_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),                       # "1. ..."
    re.compile(r"(?m)^\*\*Practice Problem \d+"),        # "**Practice Problem 1. ...**"
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same reasoning as retag.py's MIN_TAG_CLUSTER_SIZE:
# a weak/sparse match count (e.g. 1 accidental hit) isn't trusted as real
# document structure -- falls through to tier 3 instead.
```

If the total match count across all four patterns is below
`_MIN_PROBLEM_MATCHES`, tier 2 is abandoned for this file and tier 3
runs instead -- exactly what happens for `Practice Sheet.md`, correctly,
since its real numbering (`**Practice Problem N. Title**`) is the one
pattern that *would* match it, but a file where none of the patterns
clear the threshold falls through safely rather than trusting a
false-positive single match.

**Tier 3 -- page-based fallback**, universal, using the `<!-- page N
-->` markers every file already has (both pipelines). One chunk per
page, further subject to the same size cap as every other tier.

**Uniform size cap, every tier.** Confirmed live against real section
lengths in `LN_Optimization.md` (112 real sections): median 678 chars,
p90 1,937, but a real max of 34,054 -- a long tail that would otherwise
produce a useless giant "chunk." `_CHUNK_MAX_CHARS = 3000` sits above
the real p90 (rarely fires on well-structured content) while firmly
bounding the outlier tail. A chunk over the cap is subdivided further
at the next available boundary inside it (a lettered sub-part, a
blank-line paragraph break) rather than needing tier-specific
sub-splitting logic -- one rule applied uniformly regardless of which
tier produced the oversized chunk.

**Minimum length filter.** A chunk under `_CHUNK_MIN_CHARS = 80` (e.g.
a heading immediately followed by another heading, no real content
between them) is dropped, not embedded -- noise filtering, not
retrievable content.

## 5. Generation pass

```python
def generate_chunks_for_file(academic_hub_root: str, file_id: str, client) -> dict:
    """Chunk + embed one file's content, atomically: parses structure
    locally first (no API cost), then batch-embeds every resulting
    chunk. Only writes to .index/chunks/<course>.json once the whole
    batch succeeds -- a partial failure leaves the file's existing
    chunks untouched (not a half-updated, inconsistent set) and the
    file stays eligible for retry on the next `chunk` run, the same
    needs_indexing-style pattern file cards already use."""

def chunk(academic_hub_root: str, client, course: str | None = None,
          file: str | None = None, dry_run: bool = False) -> dict:
    """Iterates every non-orphaned card (spec §4.3's reconciliation is
    already the source of truth for which files exist), skips a file
    whose content_hash matches what's already on its chunks, generates
    for everything else. dry_run reports which files would be
    (re-)chunked and the resulting chunk-count estimate, without
    calling the API -- same pattern as every other real-spend operation
    in this project (retag --dry-run, transcribe_notes.py --dry-run)."""
```

Failure isolation matches every other pass in this indexer: one file's
chunking/embedding failure is logged and skipped, never aborts the
whole corpus pass. Batch embedding calls go through the existing
`gemini_utils.call_with_retries` -- no new retry mechanism needed, same
one every other Gemini call in this codebase already uses.

## 6. Passage search

```python
def search_passages(
    query: str, course: str | None = None, top_k: int = 5,
    file_top_k: int = 5, client,
) -> list[PassageResult]:
    # top_k/file_top_k default to the same 5 search() and
    # DEFAULT_COURSE_CANDIDATES already use elsewhere in index_search.py --
    # not independently re-derived, kept consistent with the existing
    # file-level search's own defaults.
    """Three-stage funnel: search() finds the top file_top_k *files*
    first (reusing 100% of the existing course-then-file filtering, not
    duplicating it), then ranks that shortlist's chunks by cosine
    similarity to the query, returning the top_k best passages
    corpus-wide across that shortlist. A file with no chunks yet
    (chunk hasn't been run against it) is silently skipped at this
    stage rather than erroring -- degrades gracefully during the
    transition period before `chunk` has been run corpus-wide."""
```

`PassageResult` carries `chunk_id`, `file_id`, `path`, `score`, `text`,
and a rendered citation string built from whichever locator fields the
chunk has (`"§3.7, p. 44"` / `"Problem 4, p. 12"` / `"p. 8"`).

## 7. CLI

Two additions to `index_search.py`'s existing argument parser, matching
`retag`'s own pattern:

- `index_search.py chunk [--course X] [--file Y] [--dry-run]`
- `index_search.py query "..." --passages [--top-k N]` -- a flag on the
  existing `query` command (same query, different result granularity),
  not a new subcommand.

## 8. Testing

`chunk_file()` is pure logic, no network calls -- fully unit-tested per
tier (heading-splitting incl. the textbook-only front-matter skip, the
problem-number pattern set incl. its validate-before-trusting
threshold, page-based fallback, the uniform size cap and minimum-length
filter). `generate_chunks_for_file()`/`chunk()` tested with a mocked
client the same way `rebuild()`/`retag()` already are -- atomicity
(partial-failure leaves existing chunks untouched), staleness
(content_hash mismatch triggers regeneration, match skips it), failure
isolation (one bad file doesn't abort the pass). `search_passages()`
tested the same way `search()` already is -- synthetic small
embeddings, no real API calls.

Real-corpus validation follows this session's established pattern:
`chunk --dry-run` first to see the real chunk-count/tier breakdown per
file, spot-check a handful of real chunks by hand before trusting the
algorithm, *then* a real run against the full corpus.

## 9. Explicitly not built here

- **ANN indexing.** Brute-force NumPy cosine similarity stays the
  approach, same YAGNI reasoning as the original indexer spec -- even
  at an estimated 4,000-8,000 chunks, a linear scan over 768-dim
  vectors is not a real bottleneck. Revisit only if the corpus grows
  enough that it demonstrably becomes one.
- **Cross-chunk deduplication** (e.g. a theorem restated near-verbatim
  in both a textbook and a lecture-note file producing two
  near-identical, redundant top results). Not investigated against real
  data yet -- unknown whether it's a real problem at current corpus
  composition or a hypothetical one.
- **Hook-time (automatic) chunk generation.** Deliberately deferred per
  §2 -- revisit once `chunk` as a standalone pass has been validated
  against the real corpus and its real cost is known.
- **Tag reuse at chunk level.** Chunks don't carry `tags` -- the
  existing file-level tags remain the only tag signal. Whether a
  chunk-level tag/topic signal would be useful is unexplored.
