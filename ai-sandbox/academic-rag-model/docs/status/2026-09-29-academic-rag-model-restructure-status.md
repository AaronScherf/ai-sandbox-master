# academic-rag-model Directory Restructure: Status Summary

Start here for "what happened and where do we stand" on the structural reorganization of `ai-sandbox/academic-rag-model` from ~15 flat sibling directories into a categorized, role-based tree (`pipelines/`, `discovery/`, `agent/`, `core/`, and standalone tools), completed with zero behavior changes.

Design reference: `docs/superpowers/specs/2026-09-29-academic-rag-model-restructure-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-29-academic-rag-model-restructure.md`.

## What shipped

1. **Role-Based Package Hierarchy**:
   - `core/`:
     - `core/env/` (was `common/`): shared environment setup, LLM API client wrappers, and vault path resolution.
     - `core/indexer/` (was `indexer/`): card schemas, chunk indexing, embedding generation, search algorithms, and cross-offering linkage.
   - `pipelines/`: Ingestion and content conversion pipelines:
     - `pipelines/convert_textbook/` (was `textbook/`)
     - `pipelines/transcribe_notes/` (was `notes/`)
     - `pipelines/convert_journal_articles/` (was `journal_articles/`)
     - `pipelines/convert_essays/` (was `essays/`)
     - `pipelines/generate_video_notes/` (was `video_notes/`)
     - `pipelines/postprocess_notes/` (was `postprocessing/`)
   - `discovery/`:
     - `discovery/discover_journal_articles/` (was `journal_discovery/`)
   - `agent/`:
     - `agent/rag/` (was `rag/`)
     - `agent/viz/` (was `viz/`)
     - `agent/problem_gen/` (was `problem_gen/`)
     - `agent/problem_corpus/` (was `problem_corpus/`)
     - `agent/summary_enhance/` (newly added)
   - Standalone packages preserved at top level: `resume_manager/`, `audio_generator/`, `tools/`.

2. **Test Suite Reorganization (`tests/`)**:
   - Flat `tests/test_*.py` files mirrored into matching package subdirectories: `tests/core/`, `tests/pipelines/`, `tests/agent/`, `tests/discovery/`, and `tests/resume_manager/`.
   - All tests execute cleanly via `pytest tests/`.

3. **Documentation Partitioning (`docs/`)**:
   - `docs/status/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`, and `docs/brainstorms/` subfolder-partitioned by package namespace.

4. **Import Path Rewriting & Depth Adjustments**:
   - Script-driven regex rewriting of all `from <old> import ...` and `import <old>` statements.
   - Fixed relative path depth calculations (`os.path.join(dirname(__file__), "..", ...)`) for moved scripts.

## Validation & Verification

- **Full Test Suite**: All tests passed across all subpackages upon completion of mechanical moves.
- **Verification of Tooling**: VM deployment paths in `start_conversion.sh` and documentation runbooks updated to use the new module paths (`python -m pipelines.convert_textbook...`).
