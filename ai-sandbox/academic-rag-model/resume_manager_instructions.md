# Resume Manager

Companion to `journal_articles_instructions.md`/`notes_instructions.md`,
but for a single, personal, hand-curated document rather than a corpus:
the user's resume. Two independent runs — a one-time bootstrap, and a
per-application tailoring pipeline.

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
* The raw extraction is reformatted into the master convention (`##`
  section headings, `### <Org> — <Role> (<dates>)` entries, bullets) via
  one local Ollama call, then checked against the raw extraction before
  being trusted — a clean check writes `resume_master.md` directly; a
  flagged mismatch writes `resume_master.review.md` instead so you only
  reconcile the flagged content by hand.
* Re-running this bootstrap never overwrites an existing `resume_master.md`
  — only run it again if the *source PDF* changes; ongoing edits to your
  master resume are yours to make directly in `resume_master.md`.

**Required structure for `resume_master.md`:** each Experience/Education
entry must be an `### ` heading of the form `### <Org> — <Role> (<Start> –
<End or "Present">)`, followed by bullet points. Other sections (Skills,
Projects, Awards, ...) are freeform. This convention is what
`fact_diff.py` parses to catch fabricated entries during tailoring —
keeping it consistent as you expand the master resume by hand is what
keeps that check useful.

## Step 2: Per-application tailoring

```powershell
python -m resume_manager.tailor_resume --jd-file "job_description.txt" --application-name "acme-corp"
```

* `--jd-file` is a local text file with the job description pasted in —
  no URL scraping in this version.
* `--application-name` becomes part of the output folder name
  (`applications/<YYYY-MM-DD>-<slugified-name>/`).
* Tailoring runs one local Ollama call (same model as the bootstrap's
  normalization step, `qwen2.5:7b-instruct` by default) with a strict
  no-fabrication prompt, then `validate.py` flags anything in the result
  that doesn't trace back to `resume_master.md` — written to
  `validation_report.txt` alongside the tailored Markdown and the
  rendered PDF. Flags are warnings, not blockers: the PDF is rendered
  regardless, and you decide whether a flag is a real problem.

## How it works

* **Reuses `notes/transcribe_notes.py`'s extraction primitives, not its
  `process_pdf()` wrapper.** That wrapper's tier-routing decision
  (`has_reliable_pagination()`) sniffs `/Creator`/`/Producer` metadata
  for LaTeX/Word/LibreOffice/Apache FOP/XEP and fails safe to the
  handwriting/messy-export fallback for anything else. Confirmed against
  the user's real `resume.pdf`: its `/Producer` is `Skia/PDF m124`
  (headless-Chrome print-to-PDF), unrecognized by that check, even though
  the extracted text is clean. A resume is also a single, manually
  verified file, unlike a batch notes corpus — there's no need for a
  generic per-file heuristic at all here.
* **No paid API call anywhere in this subproject** — extraction is local
  PyMuPDF, reformatting and tailoring are local Ollama. `GEMINI_API_KEY`
  is never read.
* **Rendering uses `xhtml2pdf`, not `weasyprint`.** `weasyprint` depends
  on the Pango/GTK native libraries, which aren't a plain `pip install` on
  Windows and were confirmed (during this subproject's own planning) not
  to import on this machine. `xhtml2pdf` is pure Python.
