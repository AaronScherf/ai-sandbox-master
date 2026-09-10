# Resume Manager — Design Spec

Date: 2026-09-09
Status: **Revision 2** (structured-data master format) — approved in
brainstorming, revision in progress. v1 was implemented, and its bootstrap
was run once against the real resume; that run's *content* succeeded (no
API cost, clean extraction) but surfaced a real, silent data-fidelity bug
in v1's design (see §3), motivating this revision before the master resume
or tailoring pipeline is trusted further. Section numbers are unchanged
from v1 so existing code (already-shipped `resume_manager/*.py` docstrings
cite `spec §N`) doesn't go stale across this revision; §3-§7 are rewritten
in place.

## 1. Problem & goals

Today the user's resume exists only as a single PDF
(`personal-website/AaronScherf.github.io/static/uploads/resume.pdf`) —
there's no editable source, no way to keep a longer "everything I've ever
done" version, and tailoring it to a specific job description means manual
rewriting from scratch each time. This spec designs **`resume_manager`**: a
new subproject that converts the existing resume PDF into a **structured**
master resume, and adds a local-LLM pipeline that tailors it to a specific
job description and renders the result to a polished PDF — adapted from the
user's own brainstorm (`docs/brainstorms/resume_manager_brainstorm.md`),
with changes driven by this project's existing conventions and by real
properties of the user's actual resume, confirmed by inspection and by a
real run (§3):

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
4. **(Revision 2, confirmed by a real run)** v1's master format asked the
   LLM to freely author a Markdown heading per entry (`### <Org> — <Role>
   (<dates>)`). Against the real resume, two of three USAID roles share one
   printed date range with the employer line rather than a per-role one —
   an ambiguity the freeform heading format had no way to represent, so the
   LLM silently substituted each role's *location* into the heading's
   `(<dates>)` slot instead, and v1's fact-diff verification (built to catch
   fabricated/dropped *entries and metrics*, not malformed *fields within* an
   entry) didn't catch it. The fix is structural, not a tighter regex: give
   every field its own named slot so there's nothing left for the LLM to
   guess about.

**Goals**
- Bootstrap-convert `resume.pdf` into a **structured master resume**
  (`resume_master.yaml`, schema in §3) once, purely locally (no paid API
  calls in the normal case — §3), via local-LLM field extraction verified
  against the raw extraction so no field is silently dropped, invented, or
  filled with the wrong value.
- Store that master resume under
  `research/independent-research/projects/resume-manager/` that the user
  keeps expanding into a long, comprehensive record of everything they've
  done — never overwritten by tooling once it exists.
- Given the master resume and a job-description text file, use a local
  Ollama model to select which Work Experience entries to highlight and
  rewrite their bullets to mirror the JD's vocabulary — with every other
  field (org, role, location, dates, and every other category entirely)
  passed through **verbatim by code, never re-emitted by the LLM** — so
  metadata fabrication during tailoring is structurally impossible, not
  merely checked for afterward (§4).
- Automatically flag (not silently block) anything in a rewritten bullet
  that doesn't trace back to that same entry's original bullets, so the
  user can review before submitting (§5).
- Render the tailored, structured result to a styled, submission-ready PDF
  via deterministic templating — never by handing LLM-authored prose
  straight to a Markdown renderer (§6).
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
- **(Revision 2)** No selection/rewriting of Education, Awards, Publications,
  or Skills during tailoring in this version — every category except Work
  Experience passes through the tailoring step unchanged, in full. Extending
  selection to those categories is a documented follow-on (§10).
- **(Revision 2)** No page-limit-aware selection in this version — entry
  selection during tailoring is relevance-only; fitting the result within a
  page budget is a documented follow-on (§10), not solved here.

## 2. Architecture

A new sibling package, `resume_manager/`, alongside `video_notes/`,
`problem_gen/`, `journal_articles/`, `notes/` in `academic-rag-model/`.
Depends on `notes/transcribe_notes.py`'s local-extraction primitives
(`extract_all_page_texts`, `page_looks_defective`, `build_final_markdown`,
`build_frontmatter` — reused unchanged; its `process_pdf()` tier-routing
wrapper is deliberately *not* used, see §3), `common/ollama_utils.py:call_ollama`
(reused unchanged for both normalization and tailoring), and `pyyaml` for
reading/writing the structured master resume (**Revision 2**: already an
installed, transitively-available package in this project — used
optionally by `postprocessing/postprocess_discovery.py` — but not yet an
explicit `requirements.txt` entry; resume_manager makes it one, since here
it's load-bearing, not optional). Unlike `journal_articles`/`notes`,
conversion has no dependency on `common/gemini_utils.py` or a paid API at
all in the normal case — see §3. Run as modules from the
`academic-rag-model/` root, matching every other subproject:

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
well-ordered. Routing it through `process_pdf()` as-is would send a
perfectly typeset resume through the handwriting-transcription fallback
purely on an unrecognized metadata string. A resume is also a single,
manually-verified file — unlike a batch notes corpus, there's no need for a
generic per-file heuristic at all.

**(Revision 2, confirmed by the first real run)** `page_looks_defective()`'s
own "unexpected character" allowlist, tuned for LaTeX math lecture notes,
didn't recognize the resume's ordinary bullet character (U+2022) or a
stray zero-width space (U+200B) — both legitimate, neither corrupted —
which flagged both real pages as defective on the first run. Fixed
upstream, additively, in `notes/transcribe_notes.py`'s shared
`_ALLOWED_EXTRA_CHARS` (same precedent as the earlier Apache FOP/XEP fix
for journal articles) — not part of this spec's own scope, but recorded
here since it was a real blocker for this pipeline's first real run.

### Master resume schema

The structured master resume, `resume_master.yaml`:

```yaml
contact:
  name: str
  location: str
  email: str
  linkedin_url: str
  github_url: str
  website_url: str

work_experience:
  - id: str              # stable slug (e.g. "usaid-1"), assigned once by
                          # convert_resume.py after parsing -- never
                          # LLM-authored (see below) -- referenced by
                          # tailor.py (§4) to key rewritten bullets back to
                          # the correct entry regardless of list order.
    org: str
    role: str
    location: str
    start_date: str
    end_date: str         # or the literal "Present"
    bullets: [str]

education:
  - id: str
    institution: str
    degree: str
    gpa: str | null        # optional
    location: str
    start_date: str
    end_date: str
    thesis: str | null     # optional

awards:
  - name: str
    description: str
    date: str

publications:
  - title: str
    date: str
    venue: str
    link: str | null       # optional

skills:
  - category: str
    items: [str]
```

`id` fields are assigned by `convert_resume.py`'s own code immediately
after parsing the LLM's extraction (`slugify(org) + "-" + ordinal`, e.g.
three USAID roles become `usaid-1`, `usaid-2`, `usaid-3` in resume order) —
deliberately not left to the LLM to invent, so ids are stable, human-legible
in the hand-edited file, and never a source of the ambiguity §1 goal 4
described. Only `work_experience` and `education` entries get ids (only
`work_experience` is referenced by id today, in tailoring — `education`
gets one too since it shares the same org/role-shaped ambiguity and may
need one for a future follow-on, per §10).

### Steps

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
3. **Extract into schema via local LLM.** `resume_raw.md`'s content is sent
   to `common.ollama_utils.call_ollama` with a strict, schema-driven prompt:
   the prompt includes the exact YAML schema above (minus `id`, which the
   LLM never produces) and instructs the model to fill it in from the raw
   text — preserving every word, number, and date exactly; no summarizing,
   no paraphrasing, no inventing a value for a field the raw text doesn't
   contain (use `null`/omit optional fields instead of guessing); output
   ONLY valid YAML, no commentary, no code-fence wrapper (stripped if
   present anyway, defensively). Same `RESUMEMANAGER_OLLAMA_MODEL`
   model/timeout conventions as tailoring (§4). The response is parsed with
   `yaml.safe_load`; a parse failure is treated the same as an Ollama
   failure (§8) — normalization didn't produce usable output, nothing is
   written to `resume_master.yaml`.
4. **Assign ids, then verify before trusting the extraction.** `id` fields
   are assigned (see schema above) to every `work_experience`/`education`
   entry. Then, for every entry in every category: every **required**
   field (everything except `gpa`, `thesis`, `link`) must be non-empty, and
   its string value must appear as a substring of `resume_raw.md` — this
   is what directly catches §1 goal 4's bug (an empty or wrong `end_date`
   fails immediately, a field-shaped check, not a heuristic) as well as
   invented values. `bullets`/`items` list entries get the same
   substring-traceability check, individually. A clean pass writes the
   parsed structure straight to `resume_master.yaml`. Any flagged mismatch
   writes it to `resume_master.review.yaml` instead, alongside a report of
   exactly which field(s) on which entry didn't validate, and the user
   reconciles only that flagged content by hand — manual work is the
   exception path triggered by a real discrepancy, not the default
   expectation.

`resume_master.yaml` (once written, by whichever path) is the file the user
keeps expanding over time into the long, comprehensive master record, never
overwritten by a re-run of this bootstrap; `resume_raw.md` is left as-is as
a permanent reference of the original extraction and the extraction step's
own verification input.

## 4. Tailoring

`tailor.py`, invoked per application via `tailor_resume.py`. **Revision 2**
replaces v1's whole-document LLM rewrite with a narrower, structurally
safer mechanism: the LLM never emits a metadata field at all, for any
category.

1. Reads `resume_master.yaml` (parsed) and the JD file (`--jd-file`).
2. Builds a prompt containing, for each `work_experience` entry: its `id`,
   `org`, `role`, and existing `bullets` (read-only context) — no other
   field. The JD text is included in full. The prompt instructs the model
   to return **only**:
   ```yaml
   included_ids: [str]              # which work_experience ids to keep
   bullets_by_id:
     <id>: [str]                    # rewritten bullets for each included id
   ```
   mirroring the JD's vocabulary in the rewritten bullets, without
   inventing experience or metrics not present in that entry's original
   bullets. Selection is relevance-only in this version — no page-limit
   awareness (§1 non-goals, §10).
3. Calls `common.ollama_utils.call_ollama(prompt, model, request_timeout)` —
   `num_ctx` auto-sized to the prompt by `call_ollama`'s existing estimate,
   so this pipeline can't hit the same silent-truncation bug
   `video_notes`/`viz`/`problem_gen` already hit and fixed. Response parsed
   with `yaml.safe_load`; a parse failure is treated as a tailoring failure
   (§8).
4. **Python code, not the LLM, reconstructs the tailored resume**: for each
   id in `included_ids`, copies that entry's `org`/`role`/`location`/
   `start_date`/`end_date` verbatim from `resume_master.yaml` and splices in
   `bullets_by_id[id]` as its bullets. `contact`, `education`, `awards`,
   `publications`, and `skills` are copied through in full, completely
   unchanged (§1 non-goals) — none of it is ever sent to the LLM as
   something to reproduce. The result is a structured, in-memory tailored
   resume (same shape as the schema in §3, minus any excluded
   `work_experience` entries) — nothing about the LLM's response can alter
   a date, an org name, a location, or any non-Work-Experience content,
   because the LLM's response never contains those fields.
5. Writes the tailored structure to
   `resume-manager/applications/<YYYY-MM-DD>-<application-name>/
   tailored_resume.yaml`.

**Model & config**: default `qwen2.5:7b-instruct` — matches
`video_notes`'s and `notes/transcribe_excalidraw.py`'s general-purpose
instruct model choice, not `problem_gen`'s math-only `qwen2-math:7b`.
Overridable via `RESUMEMANAGER_OLLAMA_MODEL`, same override pattern as
`VIDEONOTES_OLLAMA_MODEL` / `PROBLEMGEN_OLLAMA_MODEL`. `request_timeout`
defaults to `300` seconds structurally, but real CPU-only inference on this
model took over 300s and under 1800s for the v1 whole-document prompt in
practice (confirmed by the first real bootstrap run) — the *effective*
default going forward should follow that evidence rather than the
originally-assumed `transcribe_excalidraw.py` figure; resolved during
planning (§10 carries this forward if the plan doesn't pin an exact value).
`temperature: 0.2` per the brainstorm draft, to favor strict adherence to
the master's facts over creative rewriting.

Note: `call_ollama` itself takes no `temperature` parameter today (only
`prompt`, `model`, `request_timeout`, `url`, `num_ctx`) — the plan should
either extend it with an `options` passthrough or fold `temperature` into
the request another way; resolved during planning, not decided here.

## 5. Validation (automated fact-diff)

**Revision 2**: shrinks substantially, since metadata fabrication during
tailoring is now structurally impossible (§4) rather than something to
detect after the fact. `validate.py` compares the tailored structure
against the master and prints a warning report — it never blocks rendering
(§1 non-goals):

- **Bullet metrics, scoped per entry**: for each included `work_experience`
  entry, extracts standalone numeric tokens with a `%`, `$`, or `x`
  suffix/prefix (e.g. `30%`, `$2M`, `10x`) from its *rewritten* bullets;
  any such token not found in that **same entry's original bullets** (not
  the whole master document — a tighter check than v1's whole-document
  scope, made possible by knowing exactly which original entry a rewritten
  bullet came from) is flagged as a possible invented metric.
- **Selection sanity**: any id in `included_ids` that doesn't exist in the
  master is flagged (should be structurally impossible given §4's
  mechanism, but checked defensively — a `None`/`assert`-free reused
  primitive matters less here than an honest report if it ever happens).
- Report is printed to the console and saved alongside the tailored output
  as `validation_report.txt` in the application's folder, for a record of
  what was flagged even after the console output scrolls away.

## 6. Rendering

**Revision 2**: `render.py` no longer hands LLM-authored Markdown straight
to the `markdown` library. It now templates the structured tailored resume
(§4's output shape) into Markdown itself — deterministic string formatting,
one function per category (`## Work Experience` / `### <org> — <role>
(<dates>)` / bullets; `## Education`; `## Awards & Scholarships`; `## Research
Presentations & Publications`; `## Skills`) — then converts that Markdown to
HTML via the `markdown` library and to a styled PDF via `xhtml2pdf`, using
the letter-size/margin/heading CSS block adapted from
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

Templating instead of LLM-authored Markdown also means formatting can no
longer drift per application (missed bold, inconsistent heading levels,
etc.) — every application's PDF shares byte-identical structure, differing
only in which Work Experience entries and bullets were selected/rewritten.

## 7. Orchestration & output layout

`tailor_resume.py` is the CLI entry point, running tailor → validate →
render in sequence for one application, mirroring how `tailor_resume.py`
in the original brainstorm draft combined all three steps, but now backed
by the three separably-testable modules above rather than one script.

```
research/independent-research/projects/resume-manager/
  resume.pdf                        # copied source (bootstrap)
  processed_outputs/resume_raw.md   # raw local extraction (reference + verification input)
  resume_master.yaml                # structured master, expanded by hand over time
  resume_master.review.yaml         # only present if extraction verification flagged something
  applications/
    2026-09-09-acme-corp/
      job_description.txt           # user-provided input
      tailored_resume.yaml          # structured tailored result
      validation_report.txt
      Tailored_Resume.pdf
```

## 8. Error handling

- `common.ollama_utils.call_ollama` already distinguishes "server
  unreachable" (`None`) from "request timed out" (`OLLAMA_TIMEOUT`) — reused
  unchanged; `tailor.py` prints a clear error and exits non-zero on either,
  rather than proceeding with empty/partial output.
- A YAML parse failure on the LLM's response (extraction or tailoring) is
  treated the same as an unreachable/timed-out Ollama call — no output is
  trusted or written, a clear error is surfaced.
- A JD file that doesn't exist, or a missing `resume_master.yaml` (bootstrap
  not yet run), fails fast with a clear message before any Ollama call.
- `validate.py` never raises on its own — an id present in `included_ids`
  but absent from the master is reported, not crashed on; rendering
  proceeds regardless (§5).
- Conversion (§3) stops with a clear, actionable error if any page fails
  `page_looks_defective()` — never falls back to a Gemini call the user
  didn't ask for.
- Extraction's verification check (§3 step 4) never blocks — a flagged
  mismatch produces `resume_master.review.yaml` plus a report instead of
  either silently trusting the LLM output or crashing the bootstrap run.

## 9. Testing

Mirrors the existing flat `tests/` convention, mocking every external
boundary (no real Ollama, Gemini, or xhtml2pdf-library calls beyond the one
documented exception below):

- `tailor.py`: mocked `call_ollama`, testing prompt construction (only
  `id`/`org`/`role`/`bullets` per entry appear in the prompt — no other
  metadata field), the reconstruction logic (included ids get master
  metadata + rewritten bullets spliced in; excluded ids are dropped;
  non-work-experience categories pass through byte-identical), and a
  malformed-YAML response being treated as a failure.
- `validate.py`: the highest-value test target — synthetic master/tailored
  structure fixtures exercising: a matching bullet metric (no flag), an
  invented bullet metric (flagged), and an `included_ids` entry not present
  in the master (flagged).
- `render.py`: a smoke test that a small known structured resume produces a
  non-empty PDF via `xhtml2pdf` (real library call — the one exception to
  "mock every external boundary," since there's no meaningful mock for PDF
  byte output and the library itself needs no network/model) — plus
  deterministic-templating tests (same input structure always produces
  the same Markdown/HTML, independent of any LLM).
- `convert_resume.py`: verifies the extraction step calls
  `extract_all_page_texts()`/`page_looks_defective()` directly (never
  `process_pdf()`, never `common/gemini_utils.py`) and stops with an error
  when a page is flagged defective, using a synthetic "defective page"
  fixture. The schema-verification logic is the highest-value target here:
  a clean match (writes `resume_master.yaml`), a missing required field
  (flagged), a field value not traceable to raw text (flagged), and `id`
  assignment being stable/collision-free across duplicate `org` values (the
  real three-USAID-roles case), all against mocked `call_ollama` output.
- Real end-to-end run against the user's actual resume and one real job
  description as manual validation before trusting the pipeline, the same
  way other subprojects' status docs record a first real-corpus pass before
  being trusted at scale. (The first such run, under v1's design, is what
  surfaced §1 goal 4's bug — this revision's own real-run validation is
  still outstanding.)

## 10. Open questions / follow-on (not decided by this spec)

- **Page-limit-aware selection.** Confirmed as wanted during this revision's
  own design discussion: eventually, `included_ids` selection (§4) should
  account for a page-length budget, not just relevance — choosing enough
  Work Experience entries to fill (but not overflow) a target page count.
  Not solved here; candidate approaches for the follow-on to evaluate:
  an empirically-calibrated word/bullet budget passed to the LLM as a
  constraint, a render-then-measure-then-retry loop using `xhtml2pdf`'s own
  page count, or a hybrid (LLM ranks by relevance, code trims by budget).
- **Selection/rewriting for Education, Awards, Publications, and Skills.**
  Deferred in this version (§1 non-goals) — every category but Work
  Experience passes through tailoring unchanged. Worth revisiting once the
  Work-Experience-only mechanism is validated against real applications.
  `education` entries already carry an `id` (§3) in anticipation of this.
- **Metric-extraction regex coverage** (§5) is necessarily heuristic — real
  resumes phrase numbers in more ways than `%`/`$`/`x` (e.g. "reduced
  latency by half", "team of 12"), and the user's own bullets already show
  cases like `$1.5M`, `$450M`, `20 program evaluations`, `12 context
  assessments` that mix the two. The plan should validate the pattern set
  directly against the real extracted text (§3) before trusting it, rather
  than guessing patterns without real examples.
- **`RESUMEMANAGER_OLLAMA_TIMEOUT`'s real default.** §4 flags that 300s
  was too short for a real CPU-only run; the plan should pin a concrete
  default based on the timings actually observed (the first real bootstrap
  run needed `RESUMEMANAGER_OLLAMA_TIMEOUT=1800` to succeed) rather than
  carrying forward the original, now-falsified assumption.
- **Cover-letter generation** and **JD URL scraping** are both explicitly
  deferred (§1) — worth revisiting once the core tailor/validate/render
  loop is proven on real applications.
- **Multiple resume "flavors"** (e.g. a separate master for
  research-track vs. industry-track roles) aren't addressed — out of scope
  until the single-master version proves insufficient in practice.
