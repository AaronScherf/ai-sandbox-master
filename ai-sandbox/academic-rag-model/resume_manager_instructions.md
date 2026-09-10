# Resume Manager

Companion to `journal_articles_instructions.md`/`notes_instructions.md`,
but for a single, personal, hand-curated document rather than a corpus:
the user's resume. Two independent runs — a one-time bootstrap, and a
per-application tailoring pipeline. **Revision 2**: the master resume is a
structured YAML file, not freeform Markdown. **Revision 3**: the bootstrap
parses that structure deterministically — no LLM call at all. See "How it
works" below for why on both.

## Step 1: One-time bootstrap

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

## Step 2: Per-application tailoring

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

## How it works

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
