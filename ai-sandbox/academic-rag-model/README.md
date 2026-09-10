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
- [`journal_discovery/`](journal_discovery/) — resolves a faculty name or topic query (OpenAlex, locally-scored relevance, paced Unpaywall/arXiv/EZProxy access) into full-text PDFs under `research/journal-articles/<topic>/`, ready for `journal_articles/` to pick up. See [`journal_discovery_instructions.md`](journal_discovery_instructions.md).
- [`postprocessing/`](postprocessing/) — `postprocess_notes.py`: a downstream correction pass over `notes/`'s output. Depends on `notes/`.
- [`rag/`](rag/README.md) — the multi-turn tutoring agent grounded in passage retrieval. Depends on `indexer/`.
- [`viz/`](viz/README.md) — interactive Plotly HTML visualizations for concepts: a keyword-matched template library first, an LLM fallback (Gemini `gemini-3.1-flash-lite` by default) for concepts with no template. Local Ollama (`qwen2.5-coder:7b`) is available as an opt-in fallback backend. Wired into `rag/` as an opt-in `--visualize` flag.
- [`problem_gen/`](problem_gen/README.md) — the problem-generation sub-agent: retrieves the student's own real problems and textbook content for a topic, then generates a new, self-verified practice problem via a local Ollama model (`qwen2-math:7b`). No paid API call for generation itself. Wired into `rag/` via automatic intent detection on the question text — no flag needed.
- [`problem_corpus/`](problem_corpus/README.md) — extracts a structured problem corpus (topic tag, problem text, solution if present, provenance) from math-camp's problem sets, textbooks, and recitation slides. Standalone batch tool, run on demand — not wired into `rag/` or `problem_gen/` yet (that's a later, separate idea). See `docs/status/2026-09-05-problem-generation-status.md`'s "Future development ideas" section.
- [`video_notes/`](video_notes/README.md) — turns a batch of YouTube lecture videos into synthesized Markdown notes under `academic_notes/<course>/lecture-notes/`: local audio download + transcription (`yt-dlp`, `faster-whisper`), fully automatic grouping into logical lecture series, and synthesis via a local Ollama model (`qwen2.5:7b-instruct`). No paid API call except the existing indexer's own per-note classification step.
- [`resume_manager/`](resume_manager/README.md) — deterministically parses the user's resume PDF into a hand-maintained structured master resume (`resume_master.yaml`, no LLM call), then tailors it per job application via a local Ollama model and renders a styled PDF (`xhtml2pdf`). No paid API call anywhere in this subproject. See [`resume_manager_instructions.md`](resume_manager_instructions.md).
- `tests/` — flat (not mirrored by subproject); imports are package-qualified to match the layout above.
- `old_attempts/` — superseded, unmaintained prototypes; not part of the active pipeline.
- `docs/` — narrative status docs and specs for each subproject's real design history (bugs found and fixed, generalizations made, evidence behind the numbers) — start with the most recently dated file per subproject if you want the "why," not just the "what."

## Requirements

- **Python 3.13+** (pinned in `.python-version`). `requirements.txt`'s
  `audioop-lts` entry exists specifically because Python 3.13's stdlib
  dropped the `audioop` module `pydub` needs (PEP 594) — on an older
  interpreter it either won't install cleanly or will fail at import time
  instead, not a graceful degradation. One-time setup per machine:
  ```bash
  python -m venv .venv
  source .venv/bin/activate   # .venv\Scripts\activate on Windows
  pip install -r requirements.txt
  ```
- **Baseline** (`notes/`, `essays/`, `journal_articles/`, `indexer/`, `rag/`): a `GEMINI_API_KEY` in `../.env` (copy from `../.env.example`). `essays/`'s own conversion needs no API key at all — only its optional indexing hook does.
- **Textbook pipeline only** (`textbook/`): a GCP project with billing enabled and GPU quota approved (`PREEMPTIBLE_NVIDIA_L4_GPUS`), plus `gcloud` and Docker installed and running locally. See [`gcp_instructions.md`](gcp_instructions.md) for full setup.
- **Visualization sub-agent only** (`viz/`, reached via `rag/`'s opt-in `--visualize` flag): `plotly` installed in the venv. Its LLM fallback tier (only reached when no template matches) defaults to Gemini (`gemini-3.1-flash-lite`), using the same `GEMINI_API_KEY` as the Baseline row above — no extra setup. Set `VIZ_BACKEND=ollama` to opt into fully local, free generation instead — a local Ollama install (`ollama serve`) with `qwen2.5-coder:7b` pulled (`ollama pull qwen2.5-coder:7b`); real testing found it unreliable (timeouts and broken scripts) on the same request Gemini handled cleanly. Either backend degrades to returning `None` with a printed warning if unavailable — see `docs/status/2026-09-02-visualization-agent-status.md` for the full comparison.
- **Problem generation sub-agent only** (`problem_gen/`, reached via `rag/`'s automatic intent detection on the question text): generation defaults to Gemini (`gemini-3.1-flash-lite`), using the same `GEMINI_API_KEY` as the Baseline row above — no extra setup, and real spike testing measured well under a cent per problem with responses in seconds. Set `PROBLEMGEN_BACKEND=ollama` to opt into fully local, free generation instead — a local Ollama install (`ollama serve`) with `qwen2-math:7b` pulled (`ollama pull qwen2-math:7b`); on CPU-only Ollama, a single request can then take several minutes to up to ~30 minutes in the worst case, and real testing found it unreliable at honoring an explicit technique constraint. Either backend degrades to falling back to normal Q&A if unavailable — see `docs/status/2026-09-05-problem-generation-status.md` for the full real-corpus comparison.
- **Problem corpus extraction only** (`problem_corpus/`, run directly — not reached via `rag/`): uses the same `GEMINI_API_KEY` as the Baseline row above, no extra setup. No local-Ollama option (this only runs as an occasional offline batch tool, not a live per-request path, so there's no equivalent reliability-vs-latency tradeoff to weigh).
- **Video lecture notes only** (`video_notes/`): `ffmpeg` on `PATH`, plus `pip install yt-dlp faster-whisper`. A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled for synthesis and `nomic-embed-text` pulled for its grouping fallback — no `GEMINI_API_KEY` needed for those steps, though a key is still needed for the existing indexer's own per-note classification call once notes are written. See [`video_notes/README.md`](video_notes/README.md).
- **Resume manager only** (`resume_manager/`): a local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled, overridable via `RESUMEMANAGER_OLLAMA_MODEL` — needed for tailoring only; the bootstrap (PDF → master resume) has no Ollama dependency at all. No `GEMINI_API_KEY` needed anywhere in this subproject. See [`resume_manager/README.md`](resume_manager/README.md).
- A sibling `academic-hub/<TEXTBOOK_SUBDIR>/` folder (matching `.env`'s `TEXTBOOK_SUBDIR`) for the textbook/notes corpus, and/or a sibling `research/` folder for the essays/journal-articles corpus — the indexer's multi-root search (`--root`, repeatable) can query across both in one call. Either is optional; use whichever corpus you're actually populating.
