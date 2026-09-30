# CLAUDE.md — academic-rag-model

Python 3.13 packages that convert academic PDFs/docs into Markdown, index them, and power a tutoring agent. `README.md` has the subproject map; each package has its own README. Read only the README for the package you're working in.

## Commands (run from this directory, venv at `.venv/`)
- Run scripts as modules: `python -m pipelines.transcribe_notes.transcribe_notes ...`, `python -m core.indexer.index_search query "..."` (never as bare file paths).
- Tests: `python -m pytest tests/` — prefer a single file or `-k` filter over the full suite. `tests/` mirrors the package tree (`tests/pipelines/...`, `tests/agent/...`, `tests/core/...`, etc.).
- To look something up in the corpus, use `python -m core.indexer.index_search query "..."` rather than grepping `academic-hub/`.

## Scope
- `core/env/` and `core/indexer/` are shared by everything; changes there need tests for the callers too.
- Ignore `archive/old_attempts/` (superseded), `.venv/`, `__pycache__/`, `audio_generator/models/`.
- Design history lives in `docs/status/<package>/<date>-*.md` (subfoldered by package; latest date wins within a package's subfolder) and `docs/superpowers/{specs,plans}/`. Grep these for the relevant section; don't read them whole.
- API keys come from `../.env` (`GEMINI_API_KEY`, `PAID_GEMINI_KEY`). Never print or commit them. Don't trigger paid Gemini runs over large batches without asking.

## Multi-agent routing

See [the shared routing convention](../../docs/AGENT_ROUTING.md).
Gemini defaults to using existing pipelines, documentation review, and
large-context synthesis. Codex handles code maintenance, tests, and Git;
Claude handles architecture and technical design decisions.
