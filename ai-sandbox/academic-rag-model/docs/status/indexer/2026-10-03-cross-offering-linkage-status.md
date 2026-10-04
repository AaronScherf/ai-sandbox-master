# Cross-Offering Content Linkage: Status Summary

Start here for "what happened and where do we stand" on cross-offering content linkage — `core/indexer/offering_links.py`, which identifies corollaries between a course's marked prior offerings (e.g. `class_2024`) and its primary content (slides, problem sets, lecture notes) using card embedding similarity, writing links into `.index/` cards and notes markdown files.

Design reference: `docs/superpowers/specs/indexer/2026-10-03-cross-offering-linkage-design.md`;
implementation plan: `docs/superpowers/plans/indexer/2026-10-03-cross-offering-linkage.md`.

## What shipped

1. **Shared Offering Primitives (`core/env/academic_hub_paths.py`)**:
   - Promoted `.notes_subset.json` marker-reading into `academic_hub_paths.py` (`read_subset_marker`).
   - Added `find_containing_offering_label(path)` to automatically detect prior offering contexts from directory trees.
   - Added `offering_label` field to index cards computed at indexing time.

2. **Matching & Thresholding Engine (`core/indexer/offering_links.py`)**:
   - Zero new LLM/embedding API cost: reuses pre-computed card embeddings (`cosine_similarity`).
   - Partitioning by offering: strictly compares cross-offering cards (excludes intra-offering comparisons).
   - Confidence thresholding:
     - High confidence (≥0.88): auto-linked or proposed for direct resolution.
     - Review tier (0.80–0.88): recorded in `.index/offering_links/review.json`.
     - Dismissals tracked in `.index/offering_links/dismissals.json`.

3. **Dual Persistence (Index Cards & Markdown Notes)**:
   - Index side: writes `related_offerings` list into course shard index cards.
   - Note side: deterministically appends or updates an Obsidian-compatible `## Related notes` block with wikilinks.

4. **CLI Management Interface**:
   - `python -m core.indexer.offering_links --course <course> [--dry-run] [--resolve <pair_id>] [--reject <pair_id>]`.

## Real-corpus validation & bug fixes

- **TestSuite**: All tests passing across `tests/core/indexer/test_offering_links.py`.
- **Directory Depth Fix (`a1c7e41`)**: Fixed academic-hub path resolution depth in the CLI where the relative root was off by one directory level when invoked from the repository root.
- **Review Hardening (`3471c35`)**: Addressed review findings #1–#6 and #8: handling cards lacking embeddings, isolating markdown write failures from index card updates, and handling malformed ledger files.
