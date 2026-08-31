# Academic Hub Conversion & Indexing Pipelines

Seven subprojects that convert academic PDFs and documents — textbooks, TA notes,
problem sets, exams, application essays, journal articles — into clean,
LLM-ready Markdown, feed them into a shared, searchable index, and ground a
tutoring agent's answers in the result. Most of it runs entirely locally with
just a Gemini API key; only the textbook pipeline needs a GPU VM, and only
when a document actually warrants Marker's layout-aware OCR.

Run any script as a module from this directory, e.g.
`python -m notes.transcribe_notes --notes-subdir ...` or
`python -m indexer.index_search query "..."` — not as a bare file path, since
the package-qualified imports below need this directory on `sys.path`
(`python -m` does that automatically; `pytest`/`python -m unittest` work too
via the root `conftest.py`).

## Repository layout

Each subproject is a Python package (`__init__.py`) with its own `README.md`
— start there for detail. `common/` and `indexer/` are the two shared modules
almost everything else depends on.

- [`common/`](common/) — `gemini_utils.py`: Gemini client setup, retry/backoff, `.env` loading. Used by every subproject.
- [`indexer/`](indexer/README.md) — the source indexer: per-file cards, corpus-wide tag mining, passage-level chunking, and multi-root search. Depended on by every conversion pipeline below for its indexing hooks.
- [`textbook/`](textbook/README.md) — Marker/GPU conversion for large, math-heavy textbooks. See [`gcp_instructions.md`](gcp_instructions.md). The only files deployed to the GCP VM (with `common/`/`indexer/`, which they import).
- [`notes/`](notes/README.md) — local, cost-routed transcription for TA notes, problem sets, exams, and handwritten scans. See [`notes_instructions.md`](notes_instructions.md).
- [`essays/`](essays/README.md) — local, `.docx`-to-Markdown conversion for application essays and loose research notes. See [`essays_instructions.md`](essays_instructions.md).
- [`journal_articles/`](journal_articles/README.md) — local, reuses `notes/`'s tiered pipeline unchanged for academic journal-article PDFs. See [`journal_articles_instructions.md`](journal_articles_instructions.md).
- [`postprocessing/`](postprocessing/) — `postprocess_notes.py`: a downstream correction pass over `notes/`'s output. Depends on `notes/`.
- [`rag/`](rag/README.md) — the multi-turn tutoring agent grounded in passage retrieval. Depends on `indexer/`.
- `tests/` — flat (not mirrored by subproject); imports are package-qualified to match the layout above.
- `old_attempts/` — superseded, unmaintained prototypes; not part of the active pipeline.
- `docs/` — narrative status docs and specs for each subproject's real design history (bugs found and fixed, generalizations made, evidence behind the numbers) — start with the most recently dated file per subproject if you want the "why," not just the "what."

## Requirements

- **Baseline** (`notes/`, `essays/`, `journal_articles/`, `indexer/`, `rag/`): a `GEMINI_API_KEY` in `../.env` (copy from `../.env.example`). `essays/`'s own conversion needs no API key at all — only its optional indexing hook does.
- **Textbook pipeline only** (`textbook/`): a GCP project with billing enabled and GPU quota approved (`PREEMPTIBLE_NVIDIA_L4_GPUS`), plus `gcloud` and Docker installed and running locally. See [`gcp_instructions.md`](gcp_instructions.md) for full setup.
- A sibling `academic-hub/<TEXTBOOK_SUBDIR>/` folder (matching `.env`'s `TEXTBOOK_SUBDIR`) for the textbook/notes corpus, and/or a sibling `research/` folder for the essays/journal-articles corpus — the indexer's multi-root search (`--root`, repeatable) can query across both in one call. Either is optional; use whichever corpus you're actually populating.
