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

Pass optional tailoring priorities or user-confirmed facts with `--guidance`
or `--guidance-file path\to\instructions.txt`. The same text is sent to the
Gemini relevance brainstorm and local tailoring model, and saved in the
application's `guidance.txt`. User-supplied facts can supplement the master
resume for the entry they describe; the models must not infer additional
claims from them. Free-text inclusion or exclusion preferences guide model
selection but are not hard filters, so review which roles made the final
resume. For example:

```powershell
.\.venv\Scripts\python.exe -m resume_manager.apply_from_prompt `
  --prompt-file "ukraine_opportunity.txt" `
  --guidance-file "ukraine_resume_guidance.txt"
```

For important facts that must be tied to a specific work-experience entry,
pass `--facts-file path\to\facts.yaml`. Each fact names the master entry ID,
states the user-confirmed fact, and lists required concept groups. Every
group must be represented in the final entry; alternatives within a group
allow common paraphrases. A fact that misses a concept is reported for human
review, never used to block PDF rendering.

```yaml
- entry_id: u-s-agency-for-international-development-1
  fact: Managed inventories and asset databases for electrical infrastructure and humanitarian equipment across more than 16 projects.
  required_concepts:
    - [inventory, inventories]
    - [asset database, asset databases, asset tracking]
    - [electrical infrastructure]
    - [humanitarian equipment]
    - [16+ projects, more than 16 projects, over 16 projects]
```

The same option is available on `tailor_resume.py` for a saved job
description. Applications save the normalized facts in `user_facts.yaml`.
Their `validation_report.txt` separates numeric traceability, fact coverage,
possible duplicate bullets, responsibility wording, and repeated openings,
and records whether the Gemini relevance brainstorm succeeded, failed, or
was skipped. These checks are advisory and should be reviewed with the
resume.

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

## Revising an already-tailored application

To make a small, deterministic edit to an application you've already
generated -- without re-running Ollama or Gemini -- use
`revise_application.py`. Today it supports one operation: dropping a whole
`work_experience` entry (e.g. the user decides mid-review that one role
shouldn't be on this particular application after all):

```powershell
.\.venv\Scripts\python.exe -m resume_manager.revise_application `
  --app-dir "applications\2026-09-28-ukraine-energy-resilience-monitoring-consultant" `
  --remove-entry-id "bloomfield-community-empowerment-center-1"
```

It edits only that one application's saved `tailored_resume.yaml`, then
regenerates `tailored_resume.md`, the PDF, and `validation_report.txt` from
it -- re-running the same fact-diff and user-fact-coverage checks
`tailor_resume.py` uses, using the application's own saved
`user_facts.yaml` if it has one. `resume_master.yaml` is only ever read
(never written), and `job_description.txt`/`guidance.txt` are left exactly
as they were, since they record what was actually asked for. The
application's previously recorded Gemini brainstorm status (succeeded /
failed / skipped) is carried forward into the refreshed report unchanged.
Entry ids come from `tailored_resume.md`'s `<!-- id: ... -->` comments or
`tailored_resume.yaml`'s `id` fields. An unknown `--app-dir` or
`--remove-entry-id` fails before anything is written.

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
- `render.py` — deterministic Typst templating of a structured resume,
  then → styled PDF via the `typst` package.
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

## Full usage guide

Companion to `journal_articles_instructions.md`/`notes_instructions.md`,
but for a single, personal, hand-curated document rather than a corpus:
the user's resume. Two independent runs — a one-time bootstrap, and a
per-application tailoring pipeline. **Revision 2**: the master resume is a
structured YAML file, not freeform Markdown. **Revision 3**: the bootstrap
parses that structure deterministically — no LLM call at all. See "How it
works" below for why on both.

### Step 1: One-time bootstrap

```powershell
cd academic-rag-model
python -m resume_manager.convert_resume
```

* Defaults to `personal-website/AaronScherf.github.io/static/uploads/resume.pdf`
  as the source and
  `research/independent-research/projects/resume-manager/` as the
  destination — both overridable via `--source-pdf`/`--resume-manager-dir`.
* Extraction is purely local (PyMuPDF-based, 0 API calls) — never routes
  through the handwriting/messy-export Gemini fallback other conversion
  pipelines in this repo have, because a resume PDF's `/Producer`/`/Creator`
  metadata (often a resume-builder tool, not LaTeX/Word/LibreOffice) isn't a
  reliable signal for a document that's already known to be typeset. A page
  that fails the local "does this look defective" check stops the run for
  your direct attention instead of silently escalating to a vision model.
* The raw extraction is parsed into the structured schema (below)
  deterministically — no LLM call, no network (~1-2 seconds total):
  section headers are fuzzy-matched against known synonyms, and each
  section's entries are extracted by explicit line-shape rules (see "How
  it works"). A defense-in-depth check then confirms every required
  field is traceable to the raw extraction before trusting it — a clean
  check writes `resume_master.yaml` directly; a flagged mismatch (in
  practice, a parser bug) writes `resume_master.review.yaml` instead so
  you only reconcile the flagged field(s) by hand. A document the parser
  can't make sense of at all fails loudly, naming exactly which
  section/line didn't match, rather than guessing.
* Re-running this bootstrap never overwrites an existing
  `resume_master.yaml` — only run it again if the *source PDF* changes;
  ongoing edits to your master resume are yours to make directly in
  `resume_master.yaml`.

**Schema for `resume_master.yaml`:**

```yaml
contact:
  name: str
  location: str
  email: str
  linkedin_url: str
  github_url: str
  website_url: str
work_experience:
  - id: str              # auto-assigned, e.g. "usaid-1" -- don't hand-edit
    org: str
    role: str
    location: str
    start_date: str
    end_date: str         # or "Present"
    bullets: [str]
education:
  - id: str
    institution: str
    degree: str
    gpa: str              # optional
    location: str
    start_date: str
    end_date: str
    thesis: str            # optional
awards:
  - name: str
    description: str
    date: str
publications:
  - title: str
    date: str
    venue: str
    link: str              # optional
skills:
  - category: str
    items: [str]
```

`id` fields are assigned once by the bootstrap and referenced by
`tailor.py` to key rewritten bullets back to the correct entry — leave
them as-is when hand-editing (add new entries freely; each gets its own
id automatically only via a fresh bootstrap run, so a hand-added entry
needs its own manually-chosen, unique `id` in the meantime, e.g.
`"my-new-role-1"`).

### Step 2: Per-application tailoring

```powershell
python -m resume_manager.tailor_resume --jd-file "job_description.txt" --application-name "acme-corp"
```

* `--jd-file` is a local text file with the job description pasted in —
  no URL scraping in this version.
* `--application-name` becomes part of the output folder name
  (`applications/<YYYY-MM-DD>-<slugified-name>/`).
* Tailoring sends the LLM only each Work Experience entry's `id`/`org`/
  `role`/`bullets` and the job description — it returns only which ids to
  include and rewritten bullets per id. Every other field, and every
  other resume section (Education, Awards, Publications, Skills, Contact),
  is copied through unchanged by code — the LLM never sees or re-emits a
  date, an org name, a location, a GPA, or anything outside Work
  Experience bullets. `validate.py` then flags any rewritten bullet whose
  numbers/`$`/`%` don't trace back to that *same entry's* original
  bullets — written to `validation_report.txt` alongside the tailored
  YAML and the rendered PDF. Flags are warnings, not blockers.
* `--interactive` (optional) runs a short Q&A first: 2-4 open-ended
  questions generated from your master resume and the job description by
  the same local Ollama model tailoring already uses, answered by typing
  free text at the terminal. The combined Q&A transcript is saved as
  `guidance.txt` in the application folder and passed to tailoring as one
  extra prompt section the model is told to prioritize — it can steer
  which entries get selected and how bullets are framed, but can't
  override any of tailoring's other rules (no fabrication, every metric
  preserved, no repeated bullet openings). If question generation fails
  (Ollama unreachable, timed out, or an unexpected response), tailoring
  prints a warning and proceeds without guidance rather than aborting.
  Without `--interactive`, none of this runs — tailoring behaves exactly
  as it did before this flag existed.

### How it works

* **Structured schema, not freeform Markdown (Revision 2).** v1 asked the
  LLM to author a Markdown heading per entry; against the real resume, two
  roles shared one printed date range with their employer, and the LLM
  silently substituted each role's location into the heading's date slot
  instead — an ambiguity a single freeform text slot had no way to avoid.
  Named fields remove the ambiguity entirely, and verification becomes a
  direct field check instead of a heuristic.
* **Deterministic bootstrap parsing, not an LLM call (Revision 3).**
  Revision 2's own first real run took over 90 minutes of CPU-only Ollama
  calls, needed five separate fixes just to get valid YAML back, and
  *still* miscategorized a role into the wrong section (dropping its
  bullets) and dropped a thesis that was right there in the raw text. The
  common cause: the LLM had to freely decide section membership and entry
  boundaries. A machine-generated resume doesn't need that decided
  freshly each time — section headers are fuzzy-matched (`rapidfuzz`)
  against known synonyms (not hardcoded to this one resume's exact
  wording, so a differently-worded export can still be recognized), and
  each section's entries follow a small, fixed number of line-shapes,
  matched by explicit rules. See
  `../docs/status/2026-09-09-resume-manager-status.md` for the full
  evidence and every bug found along the way.
* **Tailoring never lets the LLM touch metadata**, for the same reason:
  not "the LLM was told not to change it," but "the LLM's response has no
  field to put it in even if it wanted to." Tailoring still uses a local
  Ollama call (rewriting bullets to match a job description is a language
  task, unlike bootstrap extraction).
* **Reuses `notes/transcribe_notes.py`'s extraction primitives, not its
  `process_pdf()` wrapper.** That wrapper's tier-routing decision sniffs
  `/Creator`/`/Producer` metadata for LaTeX/Word/LibreOffice/Apache
  FOP/XEP and fails safe to the handwriting/messy-export fallback for
  anything else. Confirmed against the user's real `resume.pdf`: its
  `/Producer` is `Skia/PDF m124` (headless-Chrome print-to-PDF),
  unrecognized by that check, even though the extracted text is clean.
* **No paid API call anywhere in this subproject** — extraction and schema
  parsing are local PyMuPDF/Python (no LLM at all), tailoring is local
  Ollama. `GEMINI_API_KEY` is never read.
* **Rendering uses `xhtml2pdf`, not `weasyprint`.** `weasyprint` depends
  on the Pango/GTK native libraries, which aren't a plain `pip install` on
  Windows and were confirmed not to import on this machine. `xhtml2pdf` is
  pure Python, and rendering is now deterministic templating over
  structured data rather than converting LLM-authored Markdown.
