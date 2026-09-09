# Resume Manager — Design Spec

Date: 2026-09-09
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

Today the user's resume exists only as a single PDF
(`personal-website/AaronScherf.github.io/static/uploads/resume.pdf`) —
there's no editable source, no way to keep a longer "everything I've ever
done" version, and tailoring it to a specific job description means manual
rewriting from scratch each time. This spec designs **`resume_manager`**: a
new subproject that converts the existing resume PDF into Markdown, builds a
**master resume** Markdown file the user keeps expanding over time, and adds
a local-LLM pipeline that tailors the master to a specific job description
and renders the result to a polished PDF — adapted from the user's own
brainstorm (`docs/brainstorms/resume_manager_brainstorm.md`), with changes
driven by this project's existing conventions and by two real properties of
the user's actual resume PDF, confirmed by inspection (§3):

1. Its extraction quality doesn't need `notes/transcribe_notes.py:process_pdf`'s
   full tiered pipeline (built for a heterogeneous, unknown-provenance notes
   corpus) — its own reliable-pagination check would actually misroute this
   specific file to the expensive handwriting/messy-export fallback (§3), so
   conversion reuses that module's local-extraction primitives directly
   instead of its tier-routing wrapper.
2. Its layout is regular enough that the raw-to-master reformatting step can
   itself be automated (a local LLM call + verification), rather than
   requiring the user to hand-transcribe it (§3).
3. Tailoring reuses `common/ollama_utils.py` for its LLM calls instead of the
   brainstorm draft's raw `ollama.generate()` (which lacks the `num_ctx`
   sizing fix that `common/ollama_utils.py` already carries — see
   `docs/status/2026-09-06-video-lecture-notes-status.md` for the bug this
   avoids repeating).

**Goals**
- Bootstrap-convert `resume.pdf` into Markdown once, purely locally (no paid
  API calls in the normal case — §3), then automatically reformat it into
  the master resume's structured convention, verified against the raw
  extraction so no content is silently dropped or invented.
- Store a **master resume** Markdown file under
  `research/independent-research/projects/resume-manager/` that the user
  keeps expanding into a long, comprehensive record of everything they've
  done — never overwritten by tooling once it exists.
- Given the master resume and a job-description text file, use a local
  Ollama model to produce a tailored Markdown resume that mirrors the JD's
  vocabulary without inventing experience, dates, or metrics.
- Automatically flag (not silently block) anything in the tailored output
  that doesn't trace back to the master resume, so the user can review
  before submitting.
- Render the tailored Markdown to a styled, submission-ready PDF.
- Keep the source PDF and every generated artifact for one application
  together and self-contained under `resume-manager/`, rather than scattered
  across the personal-website repo and ad hoc output locations.

**Non-goals**
- No cover-letter generation in this version — resume tailoring only
  (approved during brainstorming; a natural follow-on subproject once this
  loop is proven).
- No scraping a job description from a URL — the JD is a local text file the
  user saves themselves. URL scraping is a possible follow-on, not decided
  here.
- No indexing of the resume or its tailored variants into the shared
  academic-hub source-indexer (`research/.index/`) used for journal articles
  and notes — a personal resume has no place in that corpus's embedding
  space or doc-type vocabulary. Conversion deliberately bypasses
  `process_pdf()`'s tier-routing wrapper (see §3), which is also where its
  indexing side effect lives, so there's no indexing call to suppress in the
  first place.
- No hard-blocking validation — the automated fact-diff check (§5) flags
  discrepancies for manual review; it never refuses to render a PDF.

## 2. Architecture

A new sibling package, `resume_manager/`, alongside `video_notes/`,
`problem_gen/`, `journal_articles/`, `notes/` in `academic-rag-model/`.
Depends on `notes/transcribe_notes.py`'s local-extraction primitives
(`extract_all_page_texts`, `page_looks_defective`, `build_final_markdown`,
`build_frontmatter` — reused unchanged; its `process_pdf()` tier-routing
wrapper is deliberately *not* used, see §3) and
`common/ollama_utils.py:call_ollama` (reused unchanged for both
normalization and tailoring). Unlike `journal_articles`/`notes`, conversion
has no dependency on `common/gemini_utils.py` or a paid API at all in the
normal case — see §3. Run as modules from the `academic-rag-model/` root,
matching every other subproject:

```powershell
# One-time bootstrap (see §3)
python -m resume_manager.convert_resume

# Per application
python -m resume_manager.tailor_resume `
  --jd-file "path\to\job_description.txt" `
  --application-name "acme-corp"
```

## 3. Conversion (bootstrap step)

`convert_resume.py` is a one-off script, run once (or re-run if the source
PDF changes), not part of the per-application pipeline.

**Why this doesn't call `process_pdf()` wholesale.** `process_pdf()`'s tier
routing (`has_reliable_pagination()`) exists to handle a heterogeneous,
unknown-provenance notes corpus: it sniffs `/Creator`/`/Producer` metadata
for LaTeX/Word/LibreOffice/FOP/XEP markers and fails safe to "not reliably
paginated" for anything else, routing straight to Tier 3 — the branch
handling "handwritten, or a messy app export" via full per-page Gemini
vision at handwriting DPI/model. Confirmed against the real file: the
user's `resume.pdf` has `/Producer: Skia/PDF m124` (a headless-Chrome
print-to-PDF export, from whatever resume-builder tool generated it) — not
on that marker list — even though its extracted text is in fact clean and
well-ordered (verified by inspection: consistent ALL-CAPS section header
lines like `WORK EXPERIENCE`, `Org … dates` / `Role … Location` line pairs,
bullet lines). Routing it
through `process_pdf()` as-is would send a perfectly typeset resume through
the handwriting-transcription fallback purely on an unrecognized metadata
string. A resume is also a single, manually-verified file — unlike a batch
notes corpus, there's no need for a generic per-file heuristic at all.

**Steps:**
1. Copies `personal-website/AaronScherf.github.io/static/uploads/resume.pdf`
   into `research/independent-research/projects/resume-manager/resume.pdf`,
   so the source PDF and everything derived from it live together,
   independent of the personal-website repo's own layout.
2. Extracts text directly via `extract_all_page_texts()` (PyMuPDF
   layout-aware extraction — the same primitive Tier 1 itself uses) and
   checks each page with `page_looks_defective()`. If every page passes,
   builds the raw Markdown via `build_final_markdown()` /
   `build_frontmatter()` (same page-tagged formatting convention as the
   rest of the corpus) and writes it to
   `resume-manager/processed_outputs/resume_raw.md` — 0 API calls, no
   Gemini dependency at all. If any page *fails* `page_looks_defective()`,
   conversion stops with a clear error instead of silently escalating to
   Gemini vision — a 1-2 page resume is short enough that a defective page
   deserves the user's direct attention (re-export the source PDF, or
   transcribe just that page by hand), not the handwriting-fallback
   machinery built for a different problem.
3. **Normalize via local LLM.** `resume_raw.md`'s content is sent to
   `common.ollama_utils.call_ollama` with a strict, narrow prompt: reformat
   into the master convention below (`##` section headings, `### <Org> —
   <Role> (<Start> – <End>)` entry headings, bullet points) — preserving
   every word, number, and date exactly; no summarizing, no paraphrasing, no
   added or removed content. Same `RESUMEMANAGER_OLLAMA_MODEL` model/timeout
   conventions as tailoring (§4).
4. **Verify before trusting the reformat.** The same fact-diff technique as
   §5 (entry headings + numeric-metric tokens) runs in *both* directions
   between `resume_raw.md` and the normalized output — every entry/metric in
   the raw extraction must be traceable in the normalized output (catches
   dropped content) and every entry/metric in the normalized output must be
   traceable in the raw extraction (catches invented content). A clean pass
   writes the normalized output straight to `resume_master.md`. Any flagged
   mismatch writes it to `resume_master.review.md` instead, alongside a
   report of exactly what didn't match, and the user reconciles only that
   flagged content by hand — manual work is the exception path triggered by
   a real discrepancy, not the default expectation.

`resume_master.md` (once written, by whichever path) is the file the user
keeps expanding over time into the long, comprehensive master record, never
overwritten by a re-run of this bootstrap; `resume_raw.md` is left as-is as
a permanent reference of the original extraction and the normalization
step's own verification input.

**Required structure for `resume_master.md`** (so §5's fact-diff check has
something reliable to parse, and what step 3's prompt targets): each
Experience/Education entry is an `### ` heading of the form `### <Org> —
<Role> (<Start> – <End or "Present">)`, followed by bullet points. Other
sections (Skills, Projects, etc.) are freeform. This convention is
documented in the subproject's `README.md` and
`resume_manager_instructions.md`.

## 4. Tailoring

`tailor.py`, invoked per application via `tailor_resume.py`:

1. Reads `resume_master.md` and the JD file (`--jd-file`).
2. Builds a system/user prompt carrying over the brainstorm doc's rules
   unchanged: no fabrication of experience/skills/metrics, rewrite existing
   bullets to mirror the JD's vocabulary, preserve structure/dates/contact
   info exactly, output Markdown only (no conversational wrapper text).
3. Calls `common.ollama_utils.call_ollama(prompt, model, request_timeout)` —
   `num_ctx` auto-sized to the (likely long) master-resume-plus-JD prompt by
   `call_ollama`'s existing estimate, so this pipeline can't hit the same
   silent-truncation bug `video_notes`/`viz`/`problem_gen` already hit and
   fixed.
4. Writes the tailored Markdown to
   `resume-manager/applications/<YYYY-MM-DD>-<application-name>/
   tailored_resume.md`.

**Model & config**: default `qwen2.5:7b-instruct` — matches
`video_notes`'s and `notes/transcribe_excalidraw.py`'s general-purpose
instruct model choice, not `problem_gen`'s math-only `qwen2-math:7b`.
Overridable via `RESUMEMANAGER_OLLAMA_MODEL`, same override pattern as
`VIDEONOTES_OLLAMA_MODEL` / `PROBLEMGEN_OLLAMA_MODEL`. `request_timeout`
defaults to `300` seconds, matching `transcribe_excalidraw.py`'s
`expand_via_ollama` default. `temperature: 0.2` per the brainstorm draft, to
favor strict adherence to the master's facts over creative rewriting.

Note: `call_ollama` itself takes no `temperature` parameter today (only
`prompt`, `model`, `request_timeout`, `url`, `num_ctx`) — the plan should
either extend it with an `options` passthrough or fold `temperature` into
the request another way; resolved during planning, not decided here.

## 5. Validation (automated fact-diff)

`validate.py` compares `tailored_resume.md` against `resume_master.md` and
prints a warning report — it never blocks rendering (§1 non-goals):

- **Entries**: extracts every `### <Org> — <Role> (<dates>)` heading from
  both files. Any heading in the tailored output that doesn't match one in
  the master (org, role, and dates all matching) is flagged as a possible
  fabrication — a tailored file dropping a master entry entirely (e.g.
  omitting an old, less-relevant role) is expected behavior and not flagged.
- **Metrics**: extracts standalone numeric tokens with a `%`, `$`, or `x`
  suffix/prefix (e.g. `30%`, `$2M`, `10x`) from bullets under each tailored
  heading; any such token not found anywhere in the master resume text is
  flagged as a possible invented metric.
- Report is printed to the console and saved alongside the tailored output
  as `validation_report.txt` in the application's folder, for a record of
  what was flagged even after the console output scrolls away.

## 6. Rendering

`render.py`: Markdown → HTML via the `markdown` library → styled PDF via
`xhtml2pdf`, using the letter-size/margin/heading CSS block adapted from
`docs/brainstorms/resume_manager_brainstorm.md`. **Not** `weasyprint` as the
brainstorm draft suggested — confirmed during planning that `weasyprint`
fails to import on this machine (`OSError: cannot load library
'libgobject-2.0-0'`; it depends on the Pango/GTK native libraries, which
aren't installed and aren't a plain `pip install` on Windows — exactly the
risk the brainstorm draft's own note flagged). `xhtml2pdf` is pure Python
(reportlab-based), installs cleanly via `pip install xhtml2pdf`, and was
verified during planning to render the same HTML+CSS shape (headings,
borders, lists, `@page` size/margins) to a valid PDF. Output:
`resume-manager/applications/<YYYY-MM-DD>-<application-name>/
Tailored_Resume.pdf`.

## 7. Orchestration & output layout

`tailor_resume.py` is the CLI entry point, running tailor → validate →
render in sequence for one application, mirroring how `tailor_resume.py`
in the original brainstorm draft combined all three steps, but now backed
by the three separably-testable modules above rather than one script.

```
research/independent-research/projects/resume-manager/
  resume.pdf                        # copied source (bootstrap)
  processed_outputs/resume_raw.md   # raw local extraction (reference + verification input)
  resume_master.md                  # master resume, expanded by hand over time
  resume_master.review.md           # only present if normalization verification flagged something
  applications/
    2026-09-09-acme-corp/
      job_description.txt           # user-provided input
      tailored_resume.md
      validation_report.txt
      Tailored_Resume.pdf
```

## 8. Error handling

- `common.ollama_utils.call_ollama` already distinguishes "server
  unreachable" (`None`) from "request timed out" (`OLLAMA_TIMEOUT`) — reused
  unchanged; `tailor.py` prints a clear error and exits non-zero on either,
  rather than proceeding with empty/partial output.
- A JD file that doesn't exist, or a missing `resume_master.md` (bootstrap
  not yet run), fails fast with a clear message before any Ollama call.
- `validate.py` never raises on its own — a parse mismatch (e.g. a
  malformed `### ` heading) is reported as "could not parse" for that entry
  rather than crashing the pipeline; rendering proceeds regardless (§5).
- Conversion (§3) stops with a clear, actionable error if any page fails
  `page_looks_defective()` — never falls back to a Gemini call the user
  didn't ask for.
- Normalization's verification check (§3 step 4) never blocks — a flagged
  mismatch produces `resume_master.review.md` plus a report instead of
  either silently trusting the LLM output or crashing the bootstrap run.

## 9. Testing

Mirrors the existing flat `tests/` convention, mocking every external
boundary (no real Ollama, Gemini, or weasyprint calls in unit tests):

- `tailor.py`: mocked `call_ollama`, testing prompt construction (master +
  JD content both present, rules included) and the auto-`num_ctx` sizing
  path is exercised via `call_ollama` itself (already covered by
  `tests/test_ollama_utils.py`, not re-tested here).
- `validate.py`: the highest-value test target — synthetic master/tailored
  Markdown fixtures exercising: a matching entry (no flag), a tailored-only
  entry (flagged), a metric present in both (no flag), a metric only in
  tailored (flagged), and a master entry dropped from tailored (no flag,
  per §5).
- `render.py`: a smoke test that a small known Markdown input produces a
  non-empty PDF via `xhtml2pdf` (real library call — the one exception to
  "mock every external boundary," since there's no meaningful mock for PDF
  byte output and the library itself needs no network/model).
- `convert_resume.py`: verifies the extraction step calls
  `extract_all_page_texts()`/`page_looks_defective()` directly (never
  `process_pdf()`, never `common/gemini_utils.py`) and stops with an error
  when a page is flagged defective, using a synthetic "defective page"
  fixture. The normalize step's verification logic (bidirectional
  entry/metric matching between raw and normalized text) is the highest-
  value target here, parallel to `validate.py`'s own tests: a clean match
  (writes `resume_master.md`), a dropped entry (flagged), and a fabricated
  entry (flagged), all against mocked `call_ollama` output.
- Real end-to-end run against the user's actual resume and one real job
  description as manual validation before trusting the pipeline, the same
  way other subprojects' status docs record a first real-corpus pass before
  being trusted at scale.

## 10. Open questions / follow-on (not decided by this spec)

- **Metric-extraction regex coverage** (§5, and §3 step 4's identical
  technique applied to normalization) is necessarily heuristic — real
  resumes phrase numbers in more ways than `%`/`$`/`x` (e.g. "reduced
  latency by half", "team of 12"), and the user's own bullets above already
  show cases like `$1.5M`, `$450M`, `20 program evaluations`, `12 context
  assessments` that mix the two. The plan should validate the pattern set
  directly against the real extracted text (§3) before trusting either use
  of it, rather than guessing patterns without real examples.
- **Cover-letter generation** and **JD URL scraping** are both explicitly
  deferred (§1) — worth revisiting once the core tailor/validate/render
  loop is proven on real applications.
- **Multiple resume "flavors"** (e.g. a separate master for
  research-track vs. industry-track roles) aren't addressed — out of scope
  until the single-master version proves insufficient in practice.
