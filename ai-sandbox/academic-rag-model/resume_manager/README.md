# Resume Manager

Converts the user's resume PDF into a hand-maintained master Markdown
resume, then tailors it per job application via a local Ollama model and
renders a styled PDF — fully local except for reading the source PDF
itself: no paid API call anywhere in this subproject.

## One-time bootstrap

```powershell
.\.venv\Scripts\python.exe -m resume_manager.convert_resume
```

Copies the source resume PDF, extracts its text locally (0 API calls),
reformats it into the master convention via a local Ollama call, and
verifies that reformat against the raw extraction before writing
`resume_master.md`. A verification mismatch writes
`resume_master.review.md` instead, for manual reconciliation of just the
flagged content.

`resume_master.md` is then yours to keep expanding by hand over time —
never overwritten by a re-run of this bootstrap.

## Per application

```powershell
.\.venv\Scripts\python.exe -m resume_manager.tailor_resume --jd-file "path\to\job_description.txt" --application-name "acme-corp"
```

Writes `job_description.txt`, `tailored_resume.md`, `validation_report.txt`,
and `Tailored_Resume.pdf` into
`research/independent-research/projects/resume-manager/applications/<date>-<application-name>/`.

## Requirements

- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled
  (`ollama pull qwen2.5:7b-instruct`) — overridable via
  `RESUMEMANAGER_OLLAMA_MODEL`.
- No `GEMINI_API_KEY` needed anywhere in this subproject.

## Key files

- `extract.py` — local, zero-API-call PDF text extraction, reusing
  `notes/transcribe_notes.py`'s Tier-1 primitives directly (never its
  tier-routing wrapper — see the design spec's §3 for why).
- `normalize.py` — local-LLM reformat of the raw extraction into the
  master convention, verified via `fact_diff.py` before being trusted.
- `fact_diff.py` — shared entry/metric extraction and fact-preservation
  checks, used by both `normalize.py` and `validate.py`.
- `convert_resume.py` — the one-time bootstrap CLI.
- `tailor.py` — local-LLM job-description tailoring.
- `validate.py` — fact-diff report for a tailored resume against the
  master.
- `render.py` — Markdown → styled PDF via `xhtml2pdf`.
- `tailor_resume.py` — the per-application CLI, orchestrating
  tailor → validate → render.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-09-resume-manager-design.md`.
