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

Copies the source resume PDF, extracts its text locally (0 API calls), and
deterministically parses it into the structured schema — no LLM call, no
network, no sampling variance (~1-2 seconds). A defense-in-depth check
verifies every required field's traceability against the raw extraction
before writing `resume_master.yaml`; a real mismatch here would mean a
parser bug, not a fabrication. If it fires, it writes
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

Add `--interactive` to answer 2-4 clarifying questions (generated from
your master resume and the job description by the same local Ollama
model) before tailoring — your typed answers steer which entries get
selected and how bullets are framed for that one application. The Q&A
transcript is saved as `guidance.txt` alongside the other application
files. Omitting `--interactive` (the default) skips this step entirely —
no extra Ollama call, tailoring behaves exactly as it always has.

## Tailoring from a rough opportunity description

```powershell
.\.venv\Scripts\python.exe -m resume_manager.apply_from_prompt --prompt "senior data analyst role at a mid-size fintech, focused on fraud detection"
```

or `--prompt-file path\to\notes.txt` for a longer, multi-paragraph description.
Turns a rough description into a job description and application name via
one local Ollama call, brainstorms which of your master resume's content
is most relevant via one Gemini call (needs `GEMINI_API_KEY` or
`PAID_GEMINI_KEY` in `../.env` — this is the only script in this
subproject that does), then runs the same tailor → validate → render
pipeline as `tailor_resume.py` above. If no Gemini key is configured, it
still completes, just without the extra relevance brainstorm.

**If you're an agent handling a "tailor my resume for this opportunity"
request:** which of the three tailoring entry points to use is a
judgment call based on what you were actually given, not something to
guess mechanically:
1. **You already have (or can find) a saved job description file** — the
   user names a path, or you find a matching
   `applications/*/job_description.txt` by listing the `applications/`
   directory — use `tailor_resume.py --jd-file <path> --application-name
   <name>` directly.
2. **The user pastes what reads as a complete job posting** (has the
   shape of a real listing — responsibilities, qualifications, etc., not
   just a one-line gist) — save it verbatim to a new application
   folder's `job_description.txt`, derive `--application-name` yourself
   from the posting's own company/role text, and use `tailor_resume.py
   --jd-file <path> --application-name <name>` directly. Do **not** use
   `apply_from_prompt.py` here — there's nothing left to interpret or
   brainstorm that the tailoring call doesn't already do from a real job
   description, and it would add an unneeded Gemini dependency.
3. **Only a rough, general description of the opportunity is given** —
   use `apply_from_prompt.py --prompt "..."` (above), which runs the
   full pipeline including the relevance brainstorm.

## Requirements

- A local Ollama install (`ollama serve`) with `qwen2.5:7b-instruct` pulled
  (`ollama pull qwen2.5:7b-instruct`) — overridable via
  `RESUMEMANAGER_OLLAMA_MODEL`. Needed for **tailoring only**; the
  bootstrap has no Ollama dependency at all. CPU-only inference on this
  model can take up to `RESUMEMANAGER_OLLAMA_TIMEOUT` seconds (default
  `1800`).
- No `GEMINI_API_KEY` needed for the bootstrap, `tailor_resume.py`, or
  `merge_resumes.py`. `apply_from_prompt.py`'s relevance-brainstorm step
  needs `GEMINI_API_KEY` (or `PAID_GEMINI_KEY`) in `../.env` — if it's
  missing, that one script still completes, just without the extra
  brainstormed guidance.

## Key files

- `extract.py` — local, zero-API-call PDF text extraction, reusing
  `notes/transcribe_notes.py`'s Tier-1 primitives directly (never its
  tier-routing wrapper — see the design spec's §3 for why).
- `schema.py` — the structured master-resume schema's field lists, stable
  id assignment, and generic required-field/traceability verification.
- `normalize.py` — deterministic, section-aware parsing of the raw text
  into that schema (fuzzy section-header matching + per-section line-shape
  rules; no LLM), verified via `schema.py` before being trusted.
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
- `apply_from_prompt.py` — turns a rough, free-text opportunity
  description into a job description and application name (local
  Ollama), brainstorms relevant master-resume content (Gemini), then
  calls `tailor_resume.py`'s `run_tailoring()` directly.

See the design spec (Revision 3 note at the top covers what changed and
why) and the status doc (full real-run narrative and evidence) for the
full reasoning:
`../docs/superpowers/specs/2026-09-09-resume-manager-design.md`,
`../docs/status/2026-09-09-resume-manager-status.md`.
