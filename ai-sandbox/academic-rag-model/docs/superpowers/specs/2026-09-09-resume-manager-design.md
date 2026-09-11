# Resume Manager — Design Spec

Date: 2026-09-09 (Revision 4 added 2026-09-10)
Status: **Revision 4** (interactive clarifying-question flow, §11,
design-approved — not yet implemented) on top of **Revision 3**
(deterministic extraction, implemented and validated against the real
resume); see `docs/status/2026-09-09-resume-manager-status.md` for the
full narrative and evidence. History: v1 (freeform-Markdown master)
surfaced a real data-fidelity bug on its first real run (§1 item 4).
Revision 2 (structured-data master format) fixed that, but its own first
real run took over 90 minutes of CPU-only Ollama calls, needed five
separate formatting/normalization fixes to even parse the model's YAML
output, and *still* produced two further real content bugs (a role
miscategorized into the wrong section with its bullets dropped, and a
thesis present in the raw text written as "Not specified") that traced to
the same root cause: the LLM had to freely decide section membership and
entry boundaries, not just fill in named fields. Revision 3 replaces that
extraction step entirely with deterministic, section-aware parsing (§3)
— no LLM call, no network, no sampling variance, sub-2-second runtime.
Revision 4 adds an opt-in interactive Q&A step (§11) ahead of tailoring,
requested during review of the first real tailoring run, so the user can
steer entry selection and bullet emphasis for a specific application
before the LLM call, without changing today's non-interactive default
behavior at all. Section numbers are unchanged since v1 so existing code
(already-shipped `resume_manager/*.py` docstrings cite `spec §N`) doesn't
go stale across revisions; §3 is rewritten in place again, §2/§8/§9/§10
touched where the LLM-vs-deterministic split matters, §11 is new.
Tailoring (§4), validation (§5), and rendering (§6) are unaffected by
Revision 3 — rewriting bullets to match a job description is inherently a
language task, unlike bootstrap extraction, and still uses the local LLM;
§4 gains one new optional parameter under Revision 4 (see §11).

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
   itself be automated, rather than requiring the user to hand-transcribe
   it (§3) — **(Revision 3)** and regular enough that automation doesn't
   need an LLM at all: a machine-generated resume has clear section
   headers and a small number of fixed per-entry line-shapes, which a
   deterministic parser matches directly, with none of an LLM's
   section-boundary/categorization guesswork.
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
  (`resume_master.yaml`, schema in §3) once, purely locally and
  deterministically (§3 Revision 3: no LLM call, no network, no sampling
  variance) — a value is either extracted from a recognized section/line
  shape or the parser fails loudly naming exactly what didn't match,
  never silently dropped, invented, or misplaced.
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
- **(Revision 4)** Optionally let the user answer a handful of
  JD-grounded clarifying questions before tailoring, so their own stated
  priorities can steer which entries get selected and how bullets are
  framed for that one application — opt-in only, so today's fully
  automated run stays available unchanged (§11).

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
wrapper is deliberately *not* used, see §3), `pyyaml` for reading/writing
the structured master resume (already an installed, transitively-available
package in this project — used optionally by
`postprocessing/postprocess_discovery.py` — but not yet an explicit
`requirements.txt` entry; resume_manager makes it one, since here it's
load-bearing, not optional), and `rapidfuzz` for fuzzy section-header
matching (§3 Revision 3 — already an explicit project dependency, used
here for the first time outside its original context). **(Revision 3)**
`common/ollama_utils.py:call_ollama` is used **only by `tailor.py`** now —
bootstrap extraction (`normalize.py`, `convert_resume.py`) has no LLM, no
network, and no `common/gemini_utils.py` dependency at all; the whole
bootstrap is local, deterministic Python. Run as modules from the
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
after parsing (`slugify(org) + "-" + ordinal`, e.g.
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
3. **Extract into schema deterministically — no LLM (Revision 3).**
   `resume_raw.md`'s content (frontmatter and `<!-- page N -->` tags
   stripped first) is parsed by explicit rules, in two layers:
   - **Section splitting.** Each line is checked against
     `match_section_header()`: a fuzzy match (via `rapidfuzz.fuzz.ratio`,
     threshold 80) against a small synonym list per category (e.g.
     `work_experience` matches "work experience", "professional
     experience", "employment history", "job experience", "experience";
     similarly for `education`, `awards`, `publications`, `skills`) —
     deliberately not hardcoded to this one resume's exact header text,
     so a differently-worded resume export can still be recognized, per
     the explicit design goal of "some flexibility, but fuzzy matching,
     not a full LLM call." A candidate line must also be short (≤60
     chars) and not a bullet, to avoid a long sentence that happens to
     mention "experience" being mistaken for a header. Everything
     between one matched header and the next belongs to that section;
     the resume's name (first non-header line of the document) is
     handled separately from section content.
   - **Per-section line-shape parsing.** Each section has its own small
     number of fixed shapes, determined empirically against the real
     resume (documented in full, with real-line examples, in
     `docs/status/2026-09-09-resume-manager-status.md`):
     - `work_experience`: a blank-line-delimited chunk of exactly 4 lines
       whose 2nd line matches a `MM/YYYY - MM/YYYY`-or-`Present` pattern
       is `(org, dates, role, location)` and starts a new employer; a
       2-line chunk `(role, location)` is an *additional* role under the
       most recently seen employer (the USAID case: 3 roles, 1 shared
       date range) — its own `start_date`/`end_date` become the literal
       string `"Not specified"` rather than guessing (never a different
       field's value, the exact mistake Revision 2's LLM made once). A
       chunk whose first line starts with `• ` is that entry's bullets;
       an unprefixed line is a wrapped continuation of the previous
       bullet, joined with a space.
     - `education`: fixed 3-line entries (`institution`, `degree[ • GPA:
       X]`, `location • MM/YYYY - MM/YYYY`), consumed greedily regardless
       of blank-line boundaries (two institutions can appear back-to-back
       with no blank line between them); a `Thesis: ...` line is
       reattached to the entry immediately before it, whenever it
       appears.
     - `awards`: 2-line pairs (`Name (description)`, `date`).
     - `publications`: 3-line groups (`title`, `date`, `venue`); a
       `Published at: <url>` line reattaches to the entry immediately
       before it.
     - `skills`: a non-bullet chunk is a category header (joined if
       wrapped across lines); its following bullet chunk's items are
       comma-split (so `"Python, R, JavaScript"` becomes three items,
       while a single-item bullet is unaffected) — this section also
       needs zero-width-space stripping (§3 already fixed this once for
       `page_looks_defective()`; the same character appears *within*
       these bullets' text too, not just in the count check, so
       extraction itself strips it).
   - A shape the parser doesn't recognize — or zero section headers
     matched at all — raises `ResumeParseError` naming exactly what
     didn't match; `extract_resume_schema()` catches it, prints the
     reason, and returns `None`, the same failure contract the old
     LLM-based version had (so `convert_resume.py` needed zero changes).
4. **Assign ids, then verify (defense in depth).** `id` fields are
   assigned (see schema above) to every `work_experience`/`education`
   entry. Then, for every entry in every category, `verify_extraction()`
   (unchanged since Revision 2) checks every **required** field
   (everything except `gpa`, `thesis`, `link`) is non-empty and traceable
   as a substring of `resume_raw.md`, and exempts the literal placeholder
   `"Not specified"` (and `"Present"` for `end_date`) from that
   traceability check — an honest "the source doesn't say" is not a
   fabrication to flag. **(Revision 3)** With deterministic extraction,
   every value is a substring of `resume_raw.md` *by construction*, so
   this check should now always report clean; it's kept as a defense-in-
   depth regression test on the parser's own regexes, not because
   fabrication is possible anymore. A clean pass writes the parsed
   structure straight to `resume_master.yaml`. Any flagged mismatch (in
   practice: a parser bug) writes it to `resume_master.review.yaml`
   instead, alongside a report of exactly which field(s) on which entry
   didn't validate.

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
      guidance.txt                  # only present if run with --interactive (§11)
      tailored_resume.yaml          # structured tailored result
      validation_report.txt
      Tailored_Resume.pdf
```

## 8. Error handling

- `common.ollama_utils.call_ollama` already distinguishes "server
  unreachable" (`None`) from "request timed out" (`OLLAMA_TIMEOUT`) — reused
  unchanged; `tailor.py` prints a clear error and exits non-zero on either,
  rather than proceeding with empty/partial output. This applies to
  **tailoring only** (Revision 3) — bootstrap extraction has no Ollama
  call to fail.
- A YAML parse failure on `tailor.py`'s LLM response is treated the same
  as an unreachable/timed-out Ollama call — no output is trusted or
  written, a clear error is surfaced.
- **(Revision 3)** `normalize.py`'s deterministic parser raises
  `ResumeParseError` (caught by `extract_resume_schema()`, which prints
  the reason and returns `None`) when a section/entry doesn't match any
  recognized shape — replaces the old "Ollama call failed or returned
  invalid YAML" failure mode for bootstrap extraction. The error message
  names the exact chunk/line that didn't match, so fixing it means either
  adjusting the source PDF's formatting or extending
  `resume_manager/normalize.py`'s parsing rules — not guessing.
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
- **(Revision 4)** `generate_clarifying_questions()` failing — Ollama
  unreachable/timed out, or a malformed/wrong-shape YAML response — never
  aborts a `--interactive` run: `tailor_resume.py` prints a warning and
  proceeds exactly as a non-interactive run would (`guidance=None`),
  matching the existing pattern of an auxiliary check never blocking the
  core pipeline (§5, §3 step 4). Only a failure in the tailoring call
  itself (§4/§8, unchanged) stops the run.

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
  fixture. `id` assignment being stable/collision-free across duplicate
  `org` values (the real three-USAID-roles case) is also covered.
- **(Revision 3)** `normalize.py`: no mocking at all — every test calls
  `extract_resume_schema()` directly against a representative excerpt of
  the *actual* real resume's raw extraction (used verbatim as a test
  fixture, not a synthesized approximation), covering every line-shape
  §3 documents plus both real bugs Revision 2 hit (multiple roles under
  one employer with an honest `"Not specified"` instead of a guessed
  date; a `Thesis:` line reattaching correctly across a
  no-blank-line institution boundary) and the `match_section_header()`
  fuzzy-matching behavior (exact headers, worded-differently synonyms,
  and confirming a bullet/long-sentence line never matches). A document
  with zero recognized section headers is confirmed to return `None`
  (via `ResumeParseError`), not a silently near-empty result.
- Real end-to-end run against the user's actual resume and one real job
  description as manual validation before trusting the pipeline, the same
  way other subprojects' status docs record a first real-corpus pass before
  being trusted at scale — see
  `docs/status/2026-09-09-resume-manager-status.md` for the full record
  (bugs found under both v1 and Revision 2, each fixed, leading to
  Revision 3).
- **(Revision 4)** `tailor.py`: `generate_clarifying_questions()` tested
  the same way `tailor_resume()` already is (mocked `call_ollama`) —
  prompt contains the entry context and JD, a `questions: [...]` YAML
  response parses into a list, and an unreachable Ollama call / malformed
  YAML / wrong-shape response all return `None`. Separately, a regression
  test confirms `tailor_resume(master, jd)` (no `guidance` argument) sends
  the byte-identical prompt it does today, and
  `tailor_resume(master, jd, guidance="...")` appends a new prompt section
  containing that text — guarding the backward-compatibility requirement
  that a non-interactive run is unaffected by this revision.
- **(Revision 4)** `tailor_resume.py`: `build_guidance_text()` tested
  directly on synthetic questions/answers (no mocking needed — pure
  formatting); `collect_answers_interactively()` tested with a mocked
  `input()`.

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
- **`RESUMEMANAGER_OLLAMA_TIMEOUT`'s real default** — resolved for
  bootstrap extraction by Revision 3 (no longer applicable there at
  all — no Ollama call). Still applies to `tailor.py`, pinned to `1800`
  seconds per the same real timing evidence (§4).
- **Broadening the deterministic parser to other resume formats
  (Revision 3).** `match_section_header()`'s synonym list and each
  section's line-shape rules were built against this one real resume.
  Confirmed as an explicit, deliberate scope decision during design: "try
  to broaden it later if we get some other resume examples" — not solved
  speculatively here. When a second real resume with a different layout
  is available, extend the synonym lists and add whatever new line-shapes
  it needs (e.g. a different date format, a single-line entry style)
  rather than guessing formats without real examples to test against.
- **Cover-letter generation** and **JD URL scraping** are both explicitly
  deferred (§1) — worth revisiting once the core tailor/validate/render
  loop is proven on real applications.
- **Multiple resume "flavors"** (e.g. a separate master for
  research-track vs. industry-track roles) aren't addressed — out of scope
  until the single-master version proves insufficient in practice.
- **Interactive clarifying-question flow** — addressed by Revision 4
  (§11): the user can now optionally answer a few JD-grounded questions
  before tailoring. Still open within that design: broadening beyond
  free-text answers (e.g. multiple-choice) if free-text guidance proves
  too unconstrained in practice, and whether guidance should ever apply
  to categories other than Work Experience once §10's other
  "selection/rewriting beyond Work Experience" item is picked up.

## 11. Interactive clarifying-question flow (Revision 4)

**Problem.** The first real tailoring run (2026-09-09) showed the LLM
choosing entries and framing bullets from relevance signals in the JD
text alone. Reviewing that output, the user asked for "a back-and-forth
sort of model... that lets the user answer a few questions based on the
job description to help guide the LLM what to focus on" — their own
stated priorities (which experience to emphasize, which angle to frame
it from) aren't derivable from the JD text alone and shouldn't require
editing the master resume or the prompt by hand to express.

**Design constraints, confirmed during brainstorming:**
- Must be usable by someone without Claude Code — a standalone CLI flag
  on `tailor_resume.py`, not a Claude-orchestrated conversation.
- Question generation uses the same local Ollama model already used for
  tailoring, not Claude — keeps the whole pipeline local-only, as it
  already is.
- Fully opt-in via a new `--interactive` flag: omitting it reproduces
  today's fully automated, non-interactive run byte-for-byte. This
  matters concretely, not just in principle — this session has been
  invoking `tailor_resume.py` non-interactively via Bash throughout
  development, and that path must keep working unchanged.
- 2-4 open-ended (free-text) questions, not multiple-choice — the answer
  space (what to emphasize, which framing to use) doesn't reduce cleanly
  to a fixed option set the way earlier design questions in this session
  did.

**Question generation (`tailor.py`).** A new function,
`generate_clarifying_questions(master, job_description, model=RESUMEMANAGER_OLLAMA_MODEL) -> list[str] | None`,
alongside `tailor_resume()` in the same module (both are LLM-calling
entry points; `tailor_resume.py` stays the orchestration/CLI layer, per
this project's existing module split). Reuses `_build_entry_context()` —
the same id/org/role/bullets context already sent to tailoring — plus
the job description, in a new prompt asking the model for 2-4 open-ended
questions that would help a person choose which of *these* entries to
emphasize and how to frame them for *this* JD. Response parsed via the
existing `parse_llm_yaml()` in a `questions: [str, str, ...]` shape,
mirroring `tailor_resume()`'s own `included_ids`/`bullets_by_id` shape
check. Returns `None` — never raises — on an unreachable/timed-out Ollama
call or a malformed/wrong-shape response, exactly like `tailor_resume()`
already does; the caller decides what `None` means (§8).

**Interactive collection (`tailor_resume.py`).** Two new small,
independently testable functions:
- `collect_answers_interactively(questions: list[str]) -> list[str]` —
  prints each question and reads one free-text line via `input()`.
- `build_guidance_text(questions: list[str], answers: list[str]) -> str` —
  pairs each question with its answer into a single guidance block (e.g.
  `"Q: ...\nA: ...\n\n"` per pair, joined) — pure formatting, no I/O, so
  it's testable without mocking `input()`.

`main()` gains a new `--interactive` flag (`argparse`, `store_true`,
default `False`). When set: after loading the master resume and JD text
(before calling `tailor_resume()`), call
`generate_clarifying_questions()`. If it returns a non-empty list, call
`collect_answers_interactively()` then `build_guidance_text()`, and pass
the result as `tailor_resume()`'s new `guidance` argument. If it returns
`None` or an empty list, print a warning and proceed with `guidance=None`
— the run is never aborted by a failure in this auxiliary step (§8).
When `--interactive` is omitted entirely, none of this runs at all:
`generate_clarifying_questions()` is never called, and `tailor_resume()`
is called exactly as it is today.

**Threading guidance into tailoring (`tailor.py`).**
`tailor_resume(master, job_description, model=..., guidance: str | None = None) -> dict | None`
gains one new, defaulted-to-`None` parameter. When `guidance` is not
`None`, the prompt gains one new section, `### USER GUIDANCE (prioritize
this when selecting entries and framing bullets):`, inserted between the
entry context and the job description. This section only ever tells the
model what to prioritize among facts already present in the master
entries — it does not relax, override, or get exempted from any existing
`_SYSTEM_PROMPT` rule (no fabrication, preserve every metric, vary
sentence openings across all bullets, return only ids and bullets). When
`guidance is None` — the default, and the case for every non-interactive
run including every run this session has made so far — the prompt is
byte-for-byte unchanged from today; this is a hard backward-compatibility
requirement (§9), not just an intended default.

**Persistence.** When `--interactive` produced guidance, `tailor_resume.py`
also writes the full Q&A transcript (the generated questions and the
user's literal free-text answers, not just the combined prompt string) to
`guidance.txt` in that application's folder (§7), alongside
`job_description.txt` — so reviewing an application later shows exactly
what steered it, the same reasoning `validation_report.txt` already
follows for tailoring's own output.

**Non-goals of this revision.** Multiple-choice questions (open-ended
only, per the design constraints above); persisting or reusing guidance
across applications (each `--interactive` run's guidance applies to that
one application only — the master resume itself is the only thing meant
to persist across applications); extending guidance to categories other
than Work Experience (guidance flows into the same Work-Experience-only
tailoring call as today; broadening tailoring itself to other categories
is still the separate, already-deferred §10 item).
