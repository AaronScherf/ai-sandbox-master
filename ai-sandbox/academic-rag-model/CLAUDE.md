# CLAUDE.md — academic-rag-model

Python 3.13 packages that convert academic PDFs/docs into Markdown, index them, and power a tutoring agent. `README.md` has the subproject map; each package has its own README. Read only the README for the package you're working in.

## Commands (run from this directory, venv at `.venv/`)
- Run scripts as modules: `python -m notes.transcribe_notes ...`, `python -m indexer.index_search query "..."` (never as bare file paths).
- Tests: `python -m pytest tests/` — prefer a single file or `-k` filter over the full suite. `tests/` is flat, not mirrored by package.
- To look something up in the corpus, use `python -m indexer.index_search query "..."` rather than grepping `academic-hub/`.

## Scope
- `common/` and `indexer/` are shared by everything; changes there need tests for the callers too.
- Ignore `old_attempts/` (superseded), `.venv/`, `__pycache__/`, `audio_generator/models/`.
- Design history lives in `docs/status/<date>-<subproject>-status.md` (latest date wins) and `docs/superpowers/{specs,plans}/`. Grep these for the relevant section; don't read them whole.
- API keys come from `../.env` (`GEMINI_API_KEY`, `PAID_GEMINI_KEY`). Never print or commit them. Don't trigger paid Gemini runs over large batches without asking.

## Multi-agent routing
Gemini (Antigravity) and Codex also work this repo. See `../../docs/AGENT_ROUTING.md` for which agent handles what — large-context reads (full-corpus sweeps, long status-doc synthesis) route to Gemini, routine/mechanical work (test runs, git mechanics) routes to Codex, judgment calls stay with Claude.
