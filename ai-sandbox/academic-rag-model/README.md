# Academic Hub Conversion & Indexing Pipelines

A growing set of subprojects that convert academic PDFs and documents — textbooks, TA notes,
problem sets, exams, application essays, journal articles — into clean,
LLM-ready Markdown, feed them into a shared, searchable index, and ground a
tutoring agent's answers in the result. Most of it runs entirely locally with
just a Gemini API key; only the textbook pipeline needs a GPU VM, and only
when a document actually warrants Marker's layout-aware OCR.

Run any script as a module from this directory, e.g.
`python -m pipelines.transcribe_notes.transcribe_notes --notes-subdir ...` or
`python -m core.indexer.index_search query "..."` — not as a bare file path, since
the package-qualified imports below need this directory on `sys.path`
(`python -m` does that automatically; `pytest`/`python -m unittest` work too
via the root `conftest.py`).

## Repository layout

Each subproject is a Python package (`__init__.py`) with its own `README.md`
— start there for detail. Packages are grouped by role: `core/` (shared
infrastructure), `pipelines/` (conversion pipelines), `discovery/` (corpus
acquisition), `agent/` (the tutoring agent and its sub-agents), plus two
standalone apps and a `tools/` folder of small bridge scripts.

- [`core/env/`](core/env/) — `gemini_utils.py`: Gemini client setup, retry/backoff, `.env` loading. Used by every subproject.
- [`core/indexer/`](core/indexer/README.md) — the source indexer: per-file cards, corpus-wide tag mining, passage-level chunking, and multi-root search. Depended on by every conversion pipeline below for its indexing hooks.
- [`pipelines/convert_textbook/`](pipelines/convert_textbook/README.md) — Marker/GPU conversion for large, math-heavy textbooks. See the README's GCP setup section. The only files deployed to the GCP VM (with `core/env/`/`core/indexer/`, which they import).
- [`pipelines/transcribe_notes/`](pipelines/transcribe_notes/README.md) — local, cost-routed transcription for TA notes, problem sets, exams, and handwritten scans.
- [`pipelines/convert_essays/`](pipelines/convert_essays/README.md) — local, `.docx`-to-Markdown conversion for application essays and loose research notes.
- [`pipelines/convert_journal_articles/`](pipelines/convert_journal_articles/README.md) — local, reuses `pipelines/transcribe_notes/`'s tiered pipeline unchanged for academic journal-article PDFs.
- [`pipelines/postprocess_notes/`](pipelines/postprocess_notes/) — `postprocess_notes.py`: a downstream correction pass over `pipelines/transcribe_notes/`'s output. Depends on `pipelines/transcribe_notes/`.
- [`pipelines/generate_video_notes/`](pipelines/generate_video_notes/README.md) — turns a batch of YouTube lecture videos into synthesized Markdown notes under `academic_notes/<course>/lecture_notes/`: local audio download + transcription (`yt-dlp`, `faster-whisper`), fully automatic grouping into logical lecture series, and synthesis via a local Ollama model (`qwen2.5:7b-instruct`). No paid API call except the existing indexer's own per-note classification step.
- [`discovery/discover_journal_articles/`](discovery/discover_journal_articles/README.md) — resolves a faculty name or topic query (OpenAlex, locally-scored relevance, paced Unpaywall/arXiv/EZProxy access) into full-text PDFs under `research/journal-articles/<topic>/`, ready for `pipelines/convert_journal_articles/` to pick up.
- [`agent/rag/`](agent/rag/README.md) — the multi-turn tutoring agent grounded in passage retrieval. Depends on `core/indexer/`.
- [`agent/tutor/`](agent/tutor/README.md) — the Socratic tutoring session gate: a local CLI that an IDE agent (Antigravity) calls every turn to enforce a tutoring state machine, lint tutor messages, cap ratings by evidence, and persist sessions and a learner-gap profile into the vault. Reuses `agent/rag/` only for prep-time retrieval. Distinct from `agent/rag/`'s Q&A REPL.
- [`agent/viz/`](agent/viz/README.md) — interactive Plotly HTML visualizations for concepts: a keyword-matched template library first, an LLM fallback (Gemini `gemini-3.1-flash-lite` by default) for concepts with no template. Local Ollama (`qwen2.5-coder:7b`) is available as an opt-in fallback backend. Wired into `agent/rag/` as an opt-in `--visualize` flag.
- [`agent/problem_gen/`](agent/problem_gen/README.md) — the problem-generation sub-agent: retrieves the student's own real problems and textbook content for a topic, then generates a new, self-verified practice problem via a local Ollama model (`qwen2-math:7b`). No paid API call for generation itself. Wired into `agent/rag/` via automatic intent detection on the question text — no flag needed.
- [`agent/problem_corpus/`](agent/problem_corpus/README.md) — extracts a structured problem corpus (topic tag, problem text, solution if present, provenance) from math-camp's problem sets, textbooks, and recitation slides. Standalone batch tool, run on demand — not wired into `agent/rag/` or `agent/problem_gen/` yet (that's a later, separate idea). See `docs/status/agent/problem_gen/2026-09-05-problem-generation-status.md`'s "Future development ideas" section.
- [`resume_manager/`](resume_manager/README.md) — deterministically parses the user's resume PDF into a hand-maintained structured master resume (`resume_master.yaml`, no LLM call), then tailors it per job application via a local Ollama model and renders a styled PDF (`xhtml2pdf`). No paid API call anywhere in this subproject.
- [`audio_generator/`](audio_generator/README.md) — converts a course's Markdown notes and converted textbooks into local MP3 narration (Piper/Kokoro TTS) for passive/commute listening, no GPU. Discovery, cleaning, and TTS synthesis are fully offline; only its optional LaTeX-narration step calls a cloud API (Gemini).
- `tools/` — small standalone bridge scripts that don't belong to any one pipeline: `audit_metadata.py`, `reconcile_needs_manual.py`, and `corpus_health/` (read-only scan, local decision review, and a separately invoked exact-card chunk repair; other repairs remain gated).
- `tests/` — mirrors the package tree above (`tests/pipelines/...`, `tests/agent/...`, `tests/core/...`, etc.); imports are package-qualified to match the layout above.
- `archive/old_attempts/` — superseded, unmaintained prototypes; not part of the active pipeline.
- `docs/` — narrative status docs and specs for each subproject's real design history (bugs found and fixed, generalizations made, evidence behind the numbers), subfoldered by package within each doc-type folder (e.g. `docs/status/<package>/`) — start with the most recently dated file in a subproject's subfolder if you want the "why," not just the "what."

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
- **Baseline** (`pipelines/transcribe_notes/`, `pipelines/convert_essays/`, `pipelines/convert_journal_articles/`, `core/indexer/`, `agent/rag/`): a `GEMINI_API_KEY` in `../.env` (copy from `../.env.example`). `pipelines/convert_essays/`'s own conversion needs no API key at all — only its optional indexing hook does.
- **Textbook pipeline only** (`pipelines/convert_textbook/`): a GCP project with billing enabled and GPU quota approved (`PREEMPTIBLE_NVIDIA_L4_GPUS`), plus `gcloud` and Docker installed and running locally. See [`pipelines/convert_textbook/README.md`](pipelines/convert_textbook/README.md) for full setup.
- **Visualization sub-agent only** (`agent/viz/`, reached via `agent/rag/`'s opt-in `--visualize` flag): `plotly` installed in the venv. Its LLM fallback tier (only reached when no template matches) defaults to Gemini (`gemini-3.1-flash-lite`), using the same `GEMINI_API_KEY` as the Baseline row above — no extra setup. Set `VIZ_BACKEND=ollama` to opt into fully local, free generation instead — a local Ollama install (`ollama serve`) with `qwen2.5-coder:7b` pulled (`ollama pull qwen2.5-coder:7b`); real testing found it unreliable (timeouts and broken scripts) on the same request Gemini handled cleanly. Either backend degrades to returning `None` with a printed warning if unavailable — see `docs/status/agent/viz/2026-09-02-visualization-agent-status.md` for the full comparison.
- **Problem generation sub-agent only** (`agent/problem_gen/`, reached via `agent/rag/`'s automatic intent detection on the question text): generation defaults to Gemini (`gemini-3.1-flash-lite`), using the same `GEMINI_API_KEY` as the Baseline row above — no extra setup, and real spike testing measured well under a cent per problem with responses in seconds. Set `PROBLEMGEN_BACKEND=ollama` to opt into fully local, free generation instead — a local Ollama install (`ollama serve`) with `qwen2-math:7b` pulled (`ollama pull qwen2-math:7b`); on CPU-only Ollama, a single request can then take several minutes to up to ~30 minutes in the worst case, and real testing found it unreliable at honoring an explicit technique constraint. Either backend degrades to falling back to normal Q&A if unavailable — see `docs/status/agent/problem_gen/2026-09-05-problem-generation-status.md` for the full real-corpus comparison.
- **Problem corpus extraction only** (`agent/problem_corpus/`, run directly — not reached via `agent/rag/`): uses the same `GEMINI_API_KEY` as the Baseline row above, no extra setup. No local-Ollama option (this only runs as an occasional offline batch tool, not a live per-request path, so there's no equivalent reliability-vs-latency tradeoff to weigh).
- **Video lecture notes only** (`pipelines/generate_video_notes/`): `ffmpeg` on `PATH`, plus `pip install yt-dlp faster-whisper`. A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled for synthesis and `nomic-embed-text` pulled for its grouping fallback — no `GEMINI_API_KEY` needed for those steps, though a key is still needed for the existing indexer's own per-note classification call once notes are written. See [`pipelines/generate_video_notes/README.md`](pipelines/generate_video_notes/README.md).
- **Resume manager only** (`resume_manager/`): a local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled, overridable via `RESUMEMANAGER_OLLAMA_MODEL` — needed for tailoring only; the bootstrap (PDF → master resume) has no Ollama dependency at all. No `GEMINI_API_KEY` needed anywhere in this subproject. See [`resume_manager/README.md`](resume_manager/README.md).
- A sibling `academic-hub/<TEXTBOOK_SUBDIR>/` folder (matching `.env`'s `TEXTBOOK_SUBDIR`) for the textbook/notes corpus, and/or a sibling `research/` folder for the essays/journal-articles corpus — the indexer's multi-root search (`--root`, repeatable) can query across both in one call. Either is optional; use whichever corpus you're actually populating.
