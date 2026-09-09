# Resume Manager

Converts the user's resume PDF into a hand-maintained **structured** master
resume (`resume_master.yaml`), then tailors it per job application via a
local Ollama model and renders a styled PDF — fully local except for
reading the source PDF itself: no paid API call anywhere in this
subproject.

## One-time bootstrap

```powershell
.\.venv\Scripts\python.exe -m resume_manager.convert_resume
```

Copies the source resume PDF, extracts its text locally (0 API calls),
extracts it into the structured schema via a local Ollama call, and
verifies every required field's traceability against the raw extraction
before writing `resume_master.yaml`. A verification mismatch writes
`resume_master.review.yaml` instead, for manual reconciliation of just the
flagged field(s).

`resume_master.yaml` is then yours to keep expanding by hand over time —
never overwritten by a re-run of this bootstrap.

## Per application

```powershell
.\.venv\Scripts\python.exe -m resume_manager.tailor_resume --jd-file "path\to\job_description.txt" --application-name "acme-corp"
```

Selects which Work Experience entries to highlight and rewrites their
bullets to mirror the job description — every other field (org, role,
location, dates, and every other resume section) is copied through
unchanged by code, never re-emitted by the LLM. Writes
`job_description.txt`, `tailored_resume.yaml`, `validation_report.txt`, and
`Tailored_Resume.pdf` into
`research/independent-research/projects/resume-manager/applications/<date>-<application-name>/`.

## Requirements

- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled
  (`ollama pull qwen2.5:7b-instruct`) — overridable via
  `RESUMEMANAGER_OLLAMA_MODEL`. CPU-only inference on this model can take
  up to `RESUMEMANAGER_OLLAMA_TIMEOUT` seconds (default `1800`).
- No `GEMINI_API_KEY` needed anywhere in this subproject.

## Key files

- `extract.py` — local, zero-API-call PDF text extraction, reusing
  `notes/transcribe_notes.py`'s Tier-1 primitives directly (never its
  tier-routing wrapper — see the design spec's §3 for why).
- `schema.py` — the structured master-resume schema's field lists, stable
  id assignment, and generic required-field/traceability verification.
- `normalize.py` — local-LLM extraction of the raw text into that schema,
  verified via `schema.py` before being trusted.
- `fact_diff.py` — free-text numeric-metric extraction/traceability, used
  by `validate.py` to scope a check to one entry's own original bullets.
- `convert_resume.py` — the one-time bootstrap CLI.
- `tailor.py` — the bullets-only local-LLM call, plus code-side
  reconstruction of the full tailored resume (`apply_tailoring`).
- `validate.py` — per-entry bullet-metric fact-diff for a tailored resume.
- `render.py` — deterministic Markdown templating of a structured resume,
  then → styled PDF via `xhtml2pdf`.
- `tailor_resume.py` — the per-application CLI, orchestrating
  tailor → validate → render.

See the design spec for the full reasoning (Revision 2 note at the top
covers what changed and why):
`../docs/superpowers/specs/2026-09-09-resume-manager-design.md`.
