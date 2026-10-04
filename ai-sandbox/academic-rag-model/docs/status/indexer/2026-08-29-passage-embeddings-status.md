# Passage-Level Embeddings: Status Summary

Start here for "what happened and where do we stand" on passage-level chunking and embeddings — `core/indexer/chunk_index.py` and `core/indexer/embed_index.py`, which segment indexed documents into fine-grained passages, embed them with `text-embedding-004` (768-d), and support passage-level search queries across academic hub courses.

Design reference: `docs/superpowers/specs/indexer/2026-08-29-passage-embeddings-design.md`;
implementation plan: `docs/superpowers/plans/indexer/2026-08-29-passage-embeddings.md`.

## What shipped

1. **Tiered Chunking Algorithm (`core/indexer/chunk_index.py`)**:
   - Primary tier: Markdown header splits (`#`, `##`, `###`) respecting logical section boundaries.
   - Secondary tier: Double-newline paragraph splitting for long sections exceeding max token/character thresholds.
   - Chunk metadata: captures `file_id`, `chunk_id` (`<file_id>#chunk-<n>`), `heading`, `start_line`, `end_line`, and character offsets.
   - Clean page-marker handling: strips raw `<!-- PAGE: n -->` markers to prevent artificial boundary splits while preserving page attribution.

2. **Embedding & Storage (`core/indexer/embed_index.py`, `core/indexer/chunk_index.py`)**:
   - Embedding via `google-genai` SDK using `text-embedding-004` (768 dimensions), matching file-level cards.
   - Sharded on disk at `<root>/.index/chunks/<course>.json` alongside file cards.
   - Brute-force NumPy cosine similarity for search without requiring an external vector DB.

3. **Passage Search Funnel (`core/indexer/search.py`, `core/indexer/index_search.py`)**:
   - Three-stage search funnel: (1) broad file-level candidate retrieval, (2) passage-level vector similarity scoring, (3) citation extraction.
   - CLI support: `index_search.py query <term> --passages` and `index_search.py chunk --course <course>`.

## Real-corpus validation

- **Full test suite**: All unit tests in `tests/test_chunk_index.py` passing cleanly (63 tests).
- **Course validation**:
  - `math-camp`: All documents chunked into passages and embedded. Verified against real tutor questions in `rag_agent.py`.
  - `microecon`: Successfully chunked notes and homework index cards.
- **Subsequent bug fixes recorded**:
  - 2026-09-27: Fixed `chunk_index.py` page-marker leak where page marker comments were improperly indexed as text.
  - 2026-09-30: Refactored during repo restructure from flat modules to `core/indexer/chunk_index.py` and `core/indexer/embed_index.py`.

## Remaining open items

- Dynamic chunk size tuning based on content density (e.g. dense proofs vs. narrative summaries).
- Local Ollama embedding fallback for offline operation when API keys are unset.
