# Resume Manager — Design Spec

Date: 2026-09-09 (Revision 4 added 2026-09-10; Revisions 5-7 added
2026-09-26)
Status: **Revision 7** (two-way Markdown editing, §14 — implemented) on
top of **Revision 6** (page-fit-aware Work Experience selection + clean
section breaks, §13 — implemented, with a bullet-granularity correction
after real feedback, see §13b) on top of **Revision 5** (multi-source
resume merge, §12 — implemented, real-run-validated across two full runs)
on top of **Revision 4** (interactive clarifying-question flow, §11 —
implemented) on top of **Revision 3** (deterministic extraction,
implemented and validated against the real resume); see
`docs/status/2026-09-09-resume-manager-status.md` for the full narrative
and evidence. History: v1 (freeform-Markdown master) surfaced a real
data-fidelity bug on its first real run (§1 item 4). Revision 2
(structured-data master format) fixed that, but its own first real run
took over 90 minutes of CPU-only Ollama calls, needed five separate
formatting/normalization fixes to even parse the model's YAML output, and
*still* produced two further real content bugs (a role miscategorized
into the wrong section with its bullets dropped, and a thesis present in
the raw text written as "Not specified") that traced to the same root
cause: the LLM had to freely decide section membership and entry
boundaries, not just fill in named fields. Revision 3 replaces that
extraction step entirely with deterministic, section-aware parsing (§3)
— no LLM call, no network, no sampling variance, sub-2-second runtime.
Revision 4 adds an opt-in interactive Q&A step (§11) ahead of tailoring,
requested during review of the first real tailoring run, so the user can
steer entry selection and bullet emphasis for a specific application
before the LLM call, without changing today's non-interactive default
behavior at all. **Revision 5** (§12) adds an ongoing multi-source-resume
merge step, `merge_resumes.py`, requested after the user started
maintaining several purpose-variant resumes (academic, USAID bidding,
World Bank, MEL) in a `source_resumes/` intake folder and wanted their
content folded into the one master automatically rather than by hand.
**Revision 6** (§13) replaces `tailor.py`'s binary included/excluded
Work Experience selection with a ranked candidate list plus a
render-measure-retry loop in `tailor_resume.py`, so a tailored resume's
first page fills with as much relevant experience as fits before a
section break, and adds a Typst-level non-split rule to `render.py` so no
section's heading is ever stranded alone at the bottom of a page —
requested after reviewing the first real Typst-rendered PDF, where
Education started on page 1 and continued onto page 2. Also switched the
rendering backend from Markdown+xhtml2pdf to Typst (`render.py`,
2026-09-26, same-day but not its own numbered revision since it doesn't
change §6's data flow, only its implementation — xhtml2pdf rendered
`<ul>/<li>` bullets with no visible marker at all on a real run and had
weak default typography; see `render.py`'s own module docstring for the
full rationale and the "standing style rules" it now encodes: single
grouped list blocks per section, right-aligned dates, page-fit density
tiers). Section numbers are unchanged since v1 so existing code
(already-shipped `resume_manager/*.py` docstrings cite `spec §N`) doesn't
go stale across revisions; §3 is rewritten in place again, §2/§8/§9/§10
touched where the LLM-vs-deterministic split matters, §11 is new under
Revision 4, §12-13 are new under Revisions 5-6.
Tailoring (§4), validation (§5), and rendering (§6) are unaffected by
Revision 3 — rewriting bullets to match a job description is inherently a
language task, unlike bootstrap extraction, and still uses the local LLM;
§4 gains one new optional parameter under Revision 4 (see §11) and its
response shape changes under Revision 6 (see §13).

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
   awareness until Revision 6 (§13).
   **(2026-09-26, small additive change, same shape as §11's `guidance`
   parameter)** The response gains one more field, `include_github: true
   or false` — the model's judgment on whether this JD has significant
   coding responsibility, per real, confirmed preference: the GitHub
   profile link (not the personal website) is only worth showing then.
   `apply_tailoring()` blanks `contact.github_url` when it's `false`;
   missing/non-bool defaults to `true` (unchanged behavior). The LLM is
   still never asked to return the URL itself, only a boolean — the same
   "never emits a metadata value" guarantee this section opens with.
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
to a renderer. It templates the structured tailored resume (§4's output
shape) into markup itself — deterministic string formatting, one function
per category — so formatting can't drift per application (missed bold,
inconsistent heading levels, etc.): every application's PDF shares the
same structure, differing only in which Work Experience entries and
bullets were selected/rewritten (and, from Revision 6 §13 on, how many).

**Rendering backend (originally Markdown+xhtml2pdf, replaced by Typst,
2026-09-26).** Revision 2 originally targeted `## Work Experience` /
`### <org> — <role> (<dates>)`-style Markdown, converted to HTML via the
`markdown` library and to PDF via `xhtml2pdf` (chosen over `weasyprint`
at the time — `weasyprint` failed to import on this machine, `OSError:
cannot load library 'libgobject-2.0-0'`, needing Pango/GTK native
libraries with no plain Windows `pip install` path). That pipeline was
replaced outright after reviewing the first real application's rendered
PDF: `xhtml2pdf` rendered every `<ul>/<li>` bullet with **no visible
marker at all** — a real, confirmed defect, not a style preference — and
its default typography was plain. `build_typst()` now templates directly
into Typst markup (`= Name`, `== Section`, `=== `/`job-heading(...)`
entries, `- ` bullets), compiled to PDF via the `typst` Python package
(`typst.compile()`) — a self-contained prebuilt wheel with no native
library dependency (same precedent `resvg-py` already set for Excalidraw
notes, §2), confirmed to install and compile cleanly on this machine.
`xhtml2pdf` and the module-local `markdown` import are removed from this
subproject (the `markdown` *package* itself stays in `requirements.txt`
for `audio_generator`, unrelated to this change).

`build_typst()`'s content escaping (`_escape_typst()`) guards against
resume content containing Typst's own syntax characters (`$ # * _ < > @
[ ] backtick`) — real, not hypothetical: the user's actual bullets contain
`$1.5M`/`$450M`, and contact emails contain `@`.

**Standing style rules, confirmed real feedback (2026-09-26) after
reviewing the first real Typst-rendered PDF** — encoded directly as code
in `render.py` (constants and template logic), not as a doc someone has
to remember to consult:
- Every list of bullets belonging to one entry/section is built as a
  single Typst list block (lines joined by one newline, never a blank
  line) — a blank line between two `- ` lines makes Typst treat them as
  *separate* one-item lists, each carrying its own block spacing, which
  is what caused visibly uneven gaps between bullets versus between a
  heading and its first bullet.
- The contact line under the name is centered, matching the name.
- A Work Experience entry's heading (`job-heading`, defined once in the
  Typst preamble) puts the org and its right-aligned date range on one
  line, with the role on its own line below in italics — confirmed real
  feedback that combining org + role on one line still wrapped for the
  longest titles even after moving the date aside; the role alone, with
  the full line width to itself, fits one line for every real title in
  the actual resume.
- A sub-role sharing its employer's date range (e.g. multiple USAID roles
  under one shared range) displays that carried-forward range on its own
  heading too, rather than showing no date at all — a display-only
  carry-forward (`_work_experience_display_dates()`); the underlying
  `resume_master.yaml` keeps storing the honest `"Not specified"`
  untouched.
- `_DENSITY_TIERS` (an ordered list of spacing/font-size constants, most
  spacious first) is a page-fit mechanism: `render_resume_pdf()` compiles
  at the most spacious tier, counts the resulting PDF's pages via `pypdf`
  (already a project dependency), and steps to the next tighter tier and
  recompiles only if the content overflows `target_pages` (default `2`,
  confirmed real preference) — never shrinking past the last tier's floor
  (9.5pt body text), so a resume adapts to however much content a given
  application's tailoring produced instead of needing per-application
  manual tuning. Revision 6 (§13) adds a *second*, independent lever for
  page-fitting (how many Work Experience entries are selected) — the two
  are deliberately not conflated (§13b).

`render_resume_pdf()` writes the built Typst source alongside the PDF as
`Tailored_Resume.typ` (a debuggable intermediate artifact, the same role
`resume_raw.md` plays for extraction, §3) before compiling it. Output:
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
boundary (no real Ollama, Gemini, or `typst`-library calls beyond the one
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
  non-empty PDF via `typst.compile()` (real library call — the one exception
  to "mock every external boundary," since there's no meaningful mock for
  PDF byte output and the library itself needs no network/model) — plus
  deterministic-templating tests (same input structure and density tier
  always produce the same Typst source, independent of any LLM).
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

- **Page-limit-aware selection** — addressed by Revision 6 (§13): a
  render-measure-retry loop (the hybrid candidate this item originally
  named) now fills available page space with ranked Work Experience
  entries, and section headings never get stranded across a page break.
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
  Still open even after Revision 5 (§12) added several more real source
  resumes to draw from — deliberately so: §12's merge step reads those
  other formats via one LLM comparison call per source rather than
  extending this deterministic per-format parser, since it only needs to
  spot *new* content, not fully re-parse a whole document's structure.
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
- **Replacing local Ollama inference with a subscription-based backend**
  (raised 2026-09-27) — every LLM call in this pipeline (`merge_resumes.py`,
  `tailor.py`) goes through `common/ollama_utils.call_ollama()`, a
  synchronous local call that can take 5-30+ minutes per invocation
  (§4's timing evidence). The user has a paid Gemini subscription used
  through a dedicated Antigravity IDE window and wants to know whether
  that subscription — not a metered `GEMINI_API_KEY`/`PAID_GEMINI_KEY`
  call — could replace some or all of these Ollama calls, for speed,
  without incurring per-token API charges. Antigravity itself is an
  interactive agent environment, not something a script can call as a
  subroutine for a single text-in/text-out response, so it can't be
  substituted for `call_ollama()` directly. The more promising angle,
  not yet verified: `gemini-cli` supports OAuth login against a Google
  account/subscription (as opposed to a metered API key) and has a
  non-interactive/headless mode (`gemini -p "..."`), which would match
  `call_ollama()`'s existing call shape closely enough to drop in.
  Whether that specific auth mode actually avoids per-call billing under
  the user's subscription tier is unconfirmed. The user is checking this
  directly via Antigravity and plans a more thorough review later —
  nothing about the current Ollama-based design should change until that
  review happens.

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

## 12. Multi-source resume merge (Revision 5)

**Problem.** The user started keeping several purpose-variant resumes
(an academic CV, a USAID bidding CV, a World Bank resume, an MEL-focused
CV, plus older `.docx` drafts) in a new intake folder,
`resume-manager/source_resumes/` (alongside the original bootstrapped
`resume.pdf`, moved there too). Each variant phrases and organizes
experience differently and may contain content — a bullet, an entire
role, a credential — that never made it into `resume_master.yaml`. The
user wants that content folded into the one master automatically as new
source files are added, without hand-transcribing each variant.

**Why this isn't `convert_resume.py`'s deterministic parser extended to
more formats.** §3's parser recognizes *one* resume's fixed line-shapes
per category and fully reconstructs its structure — appropriate for a
one-time bootstrap from a single canonical source, but not for this
job: `merge_resumes.py` only needs to spot content the master doesn't
already have, across documents whose structure it doesn't need to fully
parse. Confirmed as a deliberate scope decision (design discussion,
2026-09-26): this is an LLM comparison task (does the master already say
this?), not a section/line-shape extraction task, so it reuses `extract.py`
for raw text only and never routes through `normalize.py`.

**New module: `resume_manager/merge_resumes.py`.**

1. **Discovery.** Lists every `.pdf` and `.docx` file directly under
   `source_resumes/` (ignoring `desktop.ini` and any dotfile). A small
   JSON manifest, `source_resumes/.processed_manifest.json` (mapping
   filename → the mtime it was last processed at), is checked so a
   re-run only processes files that are new or have changed since —
   avoiding repeat ~5-30-minute Ollama calls (§4's timing evidence) on
   unchanged files every time the merge is re-run after adding one more.
2. **Raw text extraction**, format-dependent:
   - `.pdf`: `extract_resume_text()`, the same primitive `convert_resume.py`
     already uses (§3) — reused directly, no `process_pdf()` tier routing
     here either, for the same reasons §3 gives.
   - `.docx`: `mammoth.extract_raw_text()` — `mammoth` is already an
     explicit project dependency (used by a different subproject); this
     is its first use in `resume_manager`, following the same "already a
     project dependency, first use in a new context" precedent §2 already
     set for `rapidfuzz`.
   A source file that fails extraction (corrupt, password-protected) is
   skipped with a warning printed and logged in the merge report (step 7
   below) — never aborts the whole run over one bad file.
3. **One LLM comparison call per unprocessed source file.** Prompt
   contains: every current `work_experience`/`education`/`awards`/
   `publications` entry from `resume_master.yaml` (id, org/institution,
   role/degree, and existing bullets — enough for the model to know what's
   already captured) plus this one source's full raw extracted text. Asks
   for **additions only** (confirmed design decision: never asked to
   rewrite or replace existing bullet wording, even when the source phrases
   the same fact better — keeps any wording the user already hand-tuned in
   `resume_master.yaml` stable across merge re-runs). Response, parsed via
   the existing `parse_llm_yaml()`:
   ```yaml
   new_bullets_by_id:
     <existing-work-experience-or-education-id>: [new bullet text, ...]
   new_work_experience: [{org, role, location, start_date, end_date, bullets: [str]}]
   new_education: [{institution, degree, gpa, location, start_date, end_date, thesis}]
   new_awards: [{name, description, date}]
   new_publications: [{title, date, venue, link}]
   ```
   A missing/malformed response is treated as "nothing new found in this
   source" (logged, not a fatal error) — mirrors `tailor_resume()`'s and
   `generate_clarifying_questions()`'s existing never-crash-on-a-bad-LLM-
   response contract (§8, §11).
4. **Traceability verification (defense in depth, even with LLM judgment
   in the loop).** Every returned bullet and every new entry's required
   fields must pass `schema.py`'s existing `verify_entry_fields()` against
   *that source file's own* raw extracted text (not the master's) before
   being merged — the same substring-traceability check `convert_resume.py`
   already runs at bootstrap (§3 step 4), reused here as the safety net
   against outright fabrication that choosing "auto-merge with LLM
   judgment" over a review-gated flag (confirmed design decision,
   2026-09-26) would otherwise leave uncovered. A field/bullet that fails
   is dropped and named in the merge report, not merged and not raised as
   an error — consistent with this project's established "flag, never
   silently trust or crash" convention (§3 step 4, §5, §8).
5. **Fuzzy-match duplicate detection (added after the first real run,
   2026-09-26) — the LLM's own novelty judgment is not, on its own,
   reliable enough.** Confirmed by that real run: it duplicated 3 USAID
   work_experience entries, 2 education entries, and 2 publications, each
   time because a different source resume phrased the same role,
   institution, or title slightly differently and the LLM didn't
   recognize it as already present in the master — exactly the risk
   choosing "auto-merge with LLM judgment" over a review-gated flag
   (step 4 above) had left uncovered for *novelty* judgment specifically
   (traceability was already covered). `_find_duplicate()` adds a
   deterministic check in front of every proposed addition: a bullet
   compared (via `rapidfuzz.fuzz.ratio`, already a project dependency,
   same primitive `match_section_header()` uses in §3) against the target
   entry's existing bullets; a new work_experience entry's `"{org} {role}"`
   against every existing entry's own `"{org} {role}"`; new education by
   `"{institution} {degree}"`; new awards by `name`; new publications by
   `title`. Threshold 85, calibrated directly against that real run's
   duplicate pairs (93.8-100 similarity) versus a genuinely different
   entry (38.9) — comfortably inside the gap between them. A match is
   flagged and dropped, not merged, the same "flag, never silently trust"
   posture as step 4.

   **Education gets a second, targeted signal** (added after a real
   second run surfaced a slip-through, same day): "Mercer University
   Bachelor in Finance and Economics" vs "Mercer University B.B.A. with
   Honors, Summa Cum Laude, GPA: 3.91" is the same real degree (same
   institution, same 3.91 GPA), but scored only 48.7 combined
   institution+degree similarity — actually *lower* than some genuinely
   different institution pairs in the real master that happen to both say
   "Master of Science in ..." (52-56), so lowering the combined-text
   threshold to catch 48.7 would have created false positives instead of
   fixing this. `_find_duplicate_education()` compares the institution
   name alone first (a far more specific signal — 100 for the real
   duplicate pair vs 32.7-36.4 for genuinely different institutions in the
   real master) at a high bar (90), paired with an exact GPA match when
   both are real values — catching this case without that risk, and
   without wrongly merging two genuinely different real degrees from the
   same school (a real, legitimate case) since those don't share a GPA.
6. **Applying the additions.** Bullets in `new_bullets_by_id` are appended
   to the matching existing entry's `bullets` list (by id). Each object in
   `new_work_experience`/`new_education` becomes a new entry, assigned a
   stable id via the same `assign_ids()`/`slugify()` machinery
   `convert_resume.py` already uses (§3) — extended with an optional
   `existing_ids` parameter (backward compatible; `convert_resume.py`'s
   own call is unaffected) so a new entry's id is disambiguated against
   every id already present in the master, not just within this one
   source's own new entries, so a re-run never collides.
   `new_awards`/`new_publications` entries are simply appended (no id
   scheme for those categories, matching §3's schema).
7. **Merge report.** `resume_master.merge_report.txt` (written alongside
   `resume_master.yaml`) lists, per source file processed this run: how
   many bullets/entries were added, and how many were flagged and dropped
   for failing traceability or looking like a duplicate (with the specific
   field/value and reason) — an audit trail the user can check after the
   fact, the same role `validation_report.txt` plays for tailoring output
   (§5), even though nothing here blocks on it.
8. **Persistence is per-file, not once at the end of the whole run**
   (corrected after a real run was killed by the host machine's own
   memory-pressure protection mid-run, 2026-09-26 — unrelated to a bug in
   this module, but exposing a real gap in it): `resume_master.yaml`, the
   merge report, and the manifest (step 1) are all rewritten after *every*
   source file finishes processing, not batched until every file in the
   run completes. Each file can cost a real, slow (~5-30-minute) Ollama
   call, so without this, a crash or kill partway through a multi-file run
   would have discarded every already-applied result too, forcing a full
   re-run from scratch instead of resuming via the manifest from where it
   left off.

**CLI.** `python -m resume_manager.merge_resumes` (no arguments — always
operates on `resume-manager/source_resumes/` and
`resume-manager/resume_master.yaml`, matching `convert_resume.py`'s own
no-argument-by-default convention, §3).

**Model & config.** Reuses `RESUMEMANAGER_OLLAMA_MODEL` and
`RESUMEMANAGER_OLLAMA_TIMEOUT` unchanged — no new environment variables.

**Non-goals of this revision.** Rewriting or improving existing bullet
wording from a better-phrased source (confirmed: additions only, see
step 3); a review/approval gate before merging (confirmed: auto-merge,
with the merge report as an after-the-fact audit trail instead, see step
7) — step 5's fuzzy-match duplicate guard narrows the real risk this
traded away (novelty misjudgment), but doesn't reintroduce a gate;
resolving genuine conflicts between sources (e.g. two source resumes
giving different dates for the same role) — not observed in the user's
actual source files during design and deferred until it's a real problem
to solve, per this project's own consistent "don't solve it speculatively"
practice (§10's parser-broadening item takes the same stance).

## 13. Page-fit-aware Work Experience selection & clean section breaks (Revision 6)

**Problem.** Reviewing the first real Typst-rendered PDF (2026-09-26,
after the render.py rewrite this same day — see the revision-history note
at the top of this spec), two layout issues surfaced: (1) `tailor.py`'s
binary `included_ids` selection (§4) has no page-budget awareness, so
page 1 can end with unused space while a section (Education) starts on
page 1 and spills onto page 2; (2) nothing prevents a section heading
from being stranded at the bottom of a page with none of its own content
following it on the same page. The user wants Education (or any section)
to always start cleanly on its own page boundary when it doesn't fully
fit where it naturally falls, and wants any leftover space on an earlier
page filled with more relevant Work Experience first, rather than left
blank.

**Design decision: two independent mechanisms, not one.** Confirmed
during design discussion — these don't need to be solved by the same
piece of code:

**13a. Clean section breaks — `render.py` only, no LLM/tailor.py
involvement.** **Corrected during planning (2026-09-26) from this
section's first draft**, which wrapped only "the heading plus its first
entry" — verified empirically, against the real Education content (all 6
institutions), that this does *not* actually prevent the section from
splitting: entries after the first can still spill to the next page
independently, which is exactly the defect being fixed. The validated
design instead wraps each section's **entire** content — heading through
its last entry — in a single Typst `#block(breakable: false)[...]`.
Confirmed empirically: Typst refuses to split a non-breakable block
across a page boundary, so if the whole section doesn't fit in the space
remaining on the current page, the *entire* block moves to the next page
instead — verified this produces exactly the wanted behavior (all 6
Education institutions move together) where the original "first entry
only" approach didn't.

Applied to **Education, Awards & Scholarships, Research Presentations &
Publications, and Skills only — never Work Experience**, which must stay
breakable/flowing: it's the one section whose length §13b deliberately
grows to fill available space, and forcing it non-breakable would defeat
that entirely. This scoping also contains the one real risk a
non-breakable block introduces, confirmed empirically: if a wrapped
section's content is ever taller than one full page, Typst silently
clips the overflow at the page boundary instead of raising an error or
flowing to a new page — verified with a 120-item stress list, which
"compiled successfully" while quietly losing content past the bottom
margin. Not a concern for the real data (Education/Awards/Publications/
Skills are each a handful of entries, nowhere near a full page), and a
defensive pre-measurement pass was confirmed out of scope for this
revision (Typst has no built-in "measure before laying out" primitive;
would need a two-pass render) — accepted as a known limitation of this
approach, to revisit only if one of these four sections ever grows large
enough in practice for it to matter.

This is a template-only change: no page-counting, no new subsystem, and
it composes automatically with 13b below since both ultimately just look
at the real compiled page count.

**13b. Ranked selection + render-measure-retry fill loop —
`tailor.py` + `tailor_resume.py`.**
- `tailor.py`'s response shape changes from `included_ids`/`bullets_by_id`
  to `ranked_ids`/`bullets_by_id`: **every** Work Experience entry (or,
  to bound response size/latency, the top N most relevant — a plan-time
  decision) ranked most-to-least relevant to the job description, each
  with rewritten bullets already prepared. Still exactly one Ollama call
  — the "hybrid: LLM ranks by relevance, code trims by budget" candidate
  §10 already named for this problem, now the actual design. `_SYSTEM_PROMPT`
  and the response-shape check in `tailor_resume()` update accordingly;
  this is a genuine schema change (like Revision 2 fully replacing v1's
  approach), not an additive/backward-compatible one like §11's `guidance`
  parameter — there is no reason for a caller to want the old binary
  shape once ranking exists.
- `apply_tailoring()` gains a parameter — **`bullet_budget: dict[str, int]`,
  not the coarser `include_count: int` this started as** (corrected after
  real feedback, 2026-09-26 — see below) — mapping an entry id to how many
  of its bullets to include; an id absent from the map is excluded
  entirely.
- **Granularity correction, confirmed by real feedback after shipping the
  entry-level version:** an `include_count`-only fill loop (add one whole
  entry at a time) left a large, visibly wrong blank gap at the bottom of
  page 1 — the *next* whole entry didn't fit even though there was
  clearly room for more of it, because entries vary in size and the
  search could only move in whole-entry increments. `tailor_resume.py`'s
  `_select_work_experience_bullets()` instead walks `ranked_ids` in order
  and, for each entry, tries adding its bullets **one at a time** (in
  their given order); after each single addition it re-renders via
  `render_resume_pdf()` and checks the real page count, growing the
  budget for as long as each successive addition still fits
  `target_pages`. The search stops entirely — across all remaining
  entries and bullets, not just the current one — at the first addition
  that doesn't fit, since page count only ever grows as more content is
  added. An entry whose very first bullet doesn't fit is left out of the
  budget entirely (can't show an entry with zero bullets); the one
  exception is when the budget would otherwise be completely empty (not
  even the top-ranked entry's first bullet fit) — that first bullet is
  included anyway, the same "accept overflow at the readable floor"
  philosophy §6's density-tier loop already follows, rather than
  producing a resume with zero Work Experience.
- This runs **at the default (most spacious) density tier's own fitting
  behavior only** (confirmed design decision: filling space by adding
  content is a different lever from §6/render.py's existing density-tier
  shrinking, and the two should not be conflated — tier-shrinking stays
  reserved for "this content genuinely doesn't fit even at the readable
  floor," never used as a trick to cram in more bullets than naturally
  relevant at normal formatting); render_resume_pdf()'s own tier-shrink
  loop is still free to kick in per candidate, but the fill loop only ever
  asks "does this candidate fit," using whatever page count
  render_resume_pdf() actually reports.
- **Selection is by rank; display order is not** (a second real bug this
  same feedback round surfaced): reordering Work Experience into rank
  order broke render.py's shared-employer date carry-forward (§6) — a
  later-dated sub-role could rank ahead of the earlier one that actually
  carries their shared dates, landing first with no preceding same-org
  entry to inherit from. `apply_tailoring()` selects *which* entries by
  rank but builds the result by walking `master`'s own work_experience
  order and keeping only the selected ids, so the tailored resume stays
  in normal (reverse-)chronological order like any real resume,
  regardless of relevance ranking — incidentally also just correct
  resume convention independent of the bug it fixes.
- Compiles are sub-second (confirmed empirically during the Typst
  rendering work, 2026-09-26), so a search loop of this size — one render
  per bullet tried, not per entry — costs negligible wall-clock time
  relative to the one Ollama call.

**Testing implications** (extends §9's existing conventions): `render.py`
gets tests confirming a forced page-boundary case moves an entire wrapped
section (all of its entries, not just its heading) together onto the next
page (via `pypdf`'s per-page text extraction, not just a total page-count
check) for each of Education/Awards/Publications/Skills, plus a control
case confirming Work Experience is *not* wrapped this way (individual
entries may legitimately land on different pages); `tailor.py`'s tests
move from asserting `included_ids` shape to `ranked_ids` shape, plus a
display-order test confirming rank order never overrides master
(chronological) order; `tailor_resume.py` gets tests of the bullet-level
search loop against a mocked `render_resume_pdf` that reports a
controlled page count per candidate, confirming it stops at the right
bullet, moves to the next entry once the current one is exhausted, and
never loops past the last entry's last bullet.

**Non-goals of this revision.** Precise per-heading vertical-position
tracking via Typst's `query()`/label system (confirmed design decision:
the simpler render-measure-retry loop against total page count is
sufficient for a 1-2 page resume; revisit only if it proves
insufficiently precise in practice); applying the render-measure-retry
fill mechanism to any category other than Work Experience (Education/
Awards/Publications/Skills still pass through untouched in full, per
§1's original non-goals — only *how many* Work Experience entries are
selected changes, not what gets selected from any other category);
defending against a wrapped section growing taller than one full page
(13a's known, accepted limitation — confirmed empirically during
planning that Typst silently clips a non-breakable block's overflow
past the page boundary rather than erroring or flowing; not a real risk
at today's real content sizes, and a defensive pre-measurement pass was
confirmed out of scope, requiring a two-pass render Typst has no
built-in primitive for); forcing every individual Work Experience entry
to stay non-breakable internally (13a's wrap deliberately excludes Work
Experience for exactly this reason — the bulk of a resume's content
lives there, and forcing every entry non-breakable would waste
significant page space for no benefit the user asked for).

## 14. Two-way Markdown editing (Revision 7)

**Problem.** `resume_master.yaml` and `tailored_resume.yaml` are the
pipeline's only editable representation of a resume's content, and hand-
editing raw YAML for word-by-word wording tweaks is awkward. The user
wants a Markdown file for each — an ongoing one mirroring
`resume_master.yaml`, and a per-application one mirroring
`tailored_resume.yaml` — that they can edit directly, with those edits
syncing back into the real data the pipeline actually uses.

**Design decision: YAML stays canonical; Markdown is a synced view, not a
second source of truth.** Confirmed during design discussion: the
alternative (Markdown becomes primary, YAML derived from it) would mean
redefining the master data format at this late stage, disruptive to
`merge_resumes.py`/`tailor.py`/`render.py`, all of which already operate
on the YAML dict shape. Two-way sync instead: export a Markdown file from
the current YAML; a human edits it; a sync step parses it back and
overwrites the YAML.

**The one real risk this design has to solve: `merge_resumes.py` can
write `resume_master.yaml` automatically while the user is mid-edit on
`resume_master.md`.** Blindly overwriting the YAML from a hand-edited
`.md` would silently discard whatever the auto-merge added in between,
with no indication anything was lost. `tailored_resume.md` has no
equivalent risk — nothing else writes to one application's own output
files after `tailor_resume.py` finishes, so `sync_tailored_md.py` needs
no guard.

**New module: `resume_manager/markdown_sync.py`** (pure formatting/
parsing, no I/O):
- `export_to_markdown(resume: dict, embed_hash: bool = False) -> str` —
  renders any resume-shaped dict (master or tailored; same schema) as
  Markdown. **Deliberately not** the same compact, prose-style Markdown
  `render.py` builds for the final PDF (§6) — that format drops missing/
  placeholder fields and is never parsed back, so it can freely omit
  anything not worth a reader seeing. This format's job is reliable
  round-tripping, so every field gets an explicit `"- Label: value"` line
  (e.g. `- Location: ...`, `- Start: ...`, `- GPA: ...`), including the
  literal `"Not specified"` placeholder where that's the real stored
  value — unambiguous to parse, and more useful to see than a
  cosmetically-cleaned view when the audience is editing data rather than
  reading a finished resume. Work Experience/Education entries carry
  their `id` as an invisible `<!-- id: ... -->` comment immediately after
  their heading, so a re-import can match an edited entry back to the
  right one; Awards/Publications/Skills have no id scheme in the schema
  (§3) and are simply rebuilt wholesale from whatever entries appear in
  the file, in order. `embed_hash=True` (master only) prepends
  `<!-- resume-master-yaml-hash: <hash> -->`, computed by
  `compute_yaml_hash()` (a SHA-256 of the resume dict's canonical YAML
  form).
- `extract_embedded_hash(markdown_text) -> str | None` — reads that
  marker back out, for `sync_master_md.py`'s staleness check.
- `import_from_markdown(markdown_text: str) -> dict` — parses Markdown
  produced by `export_to_markdown()` back into the same dict shape. A
  block it doesn't recognize is silently ignored rather than raising —
  this format is meant for direct hand-editing, where stray text (a
  comment-to-self, a blank scratch line) is normal, not an error.

**Automatic export (no new user action).** `convert_resume.py` and
`merge_resumes.py` both write `resume_master.md` (with
`embed_hash=True`) immediately after writing `resume_master.yaml` —
`merge_resumes.py` does this as part of its existing per-file `_persist()`
step (§12 step 8), so the embedded hash is always fresh relative to
whatever the most recent auto-merge run left behind. `tailor_resume.py`
writes `tailored_resume.md` (no hash) alongside `tailored_resume.yaml`
every run.

**Explicit sync-back (the one new user action per edit).**
- `resume_manager/sync_master_md.py` (`python -m resume_manager.sync_master_md`,
  no arguments, same convention as `convert_resume.py`/`merge_resumes.py`):
  reads `resume_master.md`, compares its embedded hash against
  `compute_yaml_hash()` of the *current* `resume_master.yaml`. Mismatch →
  raises `RuntimeError` with a message naming the likely cause (a
  `merge_resumes.py` run) and telling the user to re-export and redo their
  edit — refuses to overwrite rather than silently losing the auto-merged
  change. Match → parses the Markdown, overwrites `resume_master.yaml`,
  and re-exports `resume_master.md` so its hash reflects the new state,
  ready for the next edit cycle.
- `resume_manager/sync_tailored_md.py --application-dir <path>`: reads
  that application's `tailored_resume.md`, overwrites
  `tailored_resume.yaml`, re-exports the `.md` (for consistency after
  whatever normalization the parse applied), and re-renders
  `Tailored_Resume.pdf` from the edited content via the existing
  `render_resume_pdf()` (§6) — no LLM call, no re-tailoring, just a fresh
  render of the hand-edited structure.

**Non-goals of this revision.** Automatic 3-way reconciliation of a
concurrent human edit and an auto-merge (confirmed design decision: the
hash-guard's all-or-nothing refusal — re-export and redo the edit — is
simpler and sufficiently safe given how infrequently a human edit and an
auto-merge run would actually overlap in practice; a real 3-way merge is
a candidate upgrade if that assumption stops holding); syncing
`tailored_resume.md` edits back through `validate_tailored()`'s fact-diff
checks (§5) — a hand-edited wording change is the user's own deliberate
choice, not an LLM rewrite to fact-check; per-field (rather than
whole-file) conflict resolution for `resume_master.md` (the hash-guard is
whole-file, matching this revision's simpler scope).

## 15. Tailoring from a rough opportunity description (Revision 8)

**Problem.** Every tailoring path so far (§4, §11) starts from a
complete job description already saved to a text file, plus a
human-chosen `--application-name`. The user wants to start from much
less: a free-text, possibly one-sentence description of an opportunity
("a senior data analyst role at a mid-size fintech, focused on fraud
detection"), with the pipeline itself producing a proper job description,
picking an application name, and — the genuinely new capability —
brainstorming which parts of the (potentially large, multi-page) master
resume are actually relevant to that opportunity before tailoring runs,
rather than relying solely on the existing single tailoring call's own
in-the-moment judgment.

**Design decision: a three-stage pipeline, local model on both ends,
Gemini in the middle.** Considered and rejected: (a) having the current
session's own agent (Claude, with real reasoning/tool use) do the
brainstorming directly — rejected because it would make this feature
require an active Claude Code session to run at all, a real departure
from this subproject's "fully local, no paid API, runnable without
Claude" design (§1, README) that the user confirmed during design
discussion they still want preserved; (b) doing the whole thing as one
large Gemini call (interpret the rough prompt, brainstorm relevance, and
draft the tailored bullets) — rejected because it hands Gemini
responsibility beyond what it's actually needed for (matching a large
document's content against a job description, where its larger context
window and speed genuinely help) and would duplicate `tailor_resume()`'s
already-built, already-tested rewriting/validation contract. The chosen
design keeps each stage doing only the one thing it's suited for:
1. **Stage 1 (local Ollama, new `interpret_opportunity_prompt()`):**
   turns the rough free-text description into a clean job-description-
   style text block and a short `application_name` string (e.g. "Acme
   Corp Senior Data Analyst"). A narrow rephrase/expand task — not a
   structured-extraction task across many categories like §12's merge
   comparison — so it's a much safer single local call than anything
   Revision 5-7 had to fix. Returns `None` (never raises) on an
   unreachable/timed-out/malformed response, matching every other local
   call's contract in this subproject (§8).
2. **Stage 2 (Gemini, new `brainstorm_relevant_content()`, via the
   existing `common/gemini_utils.py`):** sends `resume_master.yaml`'s
   *raw YAML text, in full* (not `merge_resumes.py`'s trimmed
   `_build_master_context()` view built for a smaller local context
   window — the whole point of using Gemini here is that its larger
   context window doesn't need that trimming) plus Stage 1's job
   description text to a flash-tier Gemini model (this is a
   relevance-matching task, not one needing pro-tier reasoning), asking
   it to identify which Work Experience entries, skills, and other
   master-resume content are most relevant to this opportunity and why.
   Output is free text in the same
   shape `guidance` already accepts (see below) — not structured
   YAML/JSON — since nothing downstream parses it further, and free text
   has far fewer failure modes than requiring an exact schema from a
   different model than the rest of this subproject uses. On failure
   (missing key, network error, quota), warns and returns `None`,
   exactly like `_collect_guidance()`'s existing graceful-degradation
   contract (§11) — a Gemini outage never blocks tailoring, it only
   means tailoring proceeds without the extra brainstormed context.
3. **Stage 3 (local Ollama — no new code):** Stage 1's job description
   text is written to a temp file, and the already-existing, completely
   unmodified `run_tailoring(master_resume_path, jd_path,
   application_name, resume_manager_dir, guidance=stage_2_text)`
   (`tailor_resume.py`) is called directly. `guidance` (§11) was already
   "optional free text inserted as a `### USER GUIDANCE` block" with no
   coupling to its originally-Q&A-shaped caller — Stage 2's brainstorm
   slots into that exact same parameter with zero changes to `tailor.py`
   or `run_tailoring()`.

**New module: `resume_manager/apply_from_prompt.py`.** Kept as its own
script rather than a new flag on `tailor_resume.py` — same "one script
per user-facing action" precedent as `convert_resume.py`/
`tailor_resume.py`/`merge_resumes.py`, and it's the only script in this
subproject that needs a Gemini API key at all, so isolating it keeps
every other entry point's zero-paid-dependency guarantee intact.
- `interpret_opportunity_prompt(prompt: str, model: str = RESUMEMANAGER_OLLAMA_MODEL) -> dict | None`
  — returns `{"job_description": str, "application_name": str}`.
- `brainstorm_relevant_content(master: dict, job_description: str, model: str = _GEMINI_MODEL) -> str | None`
  — `_GEMINI_MODEL` defaults to `"gemini-3.1-flash-lite"`, the same
  flash-tier model `notes/transcribe_notes.py` already uses for its
  cheapest per-call tasks (measured there at ~$0.0007/page) — a
  relevance-matching task over one resume plus one job description is
  well within that tier, with no need for a pro-tier model's cost or
  latency.
- `create_application_from_prompt(prompt: str, resume_manager_dir: str, ollama_model: str = RESUMEMANAGER_OLLAMA_MODEL, gemini_model: str = _GEMINI_MODEL, target_pages: int = 2) -> str`
  — the orchestration function: runs Stage 1, aborts with a clear error
  if it fails (there is no job description to proceed with, the same
  upfront-failure posture `run_tailoring()` already has for a missing
  file), runs Stage 2 (best-effort), writes Stage 1's job description to
  a temp file, and calls `run_tailoring()`. Returns the same one-line
  status string `run_tailoring()` already returns.
- CLI (`python -m resume_manager.apply_from_prompt`): `--prompt "text"`
  or `--prompt-file path.txt` (support both — an inline flag for a short
  description, a file for a longer, multi-paragraph one), plus the same
  `--resume-manager-dir` flag `tailor_resume.py` already exposes (its
  default mirrors `tailor_resume.py`'s own
  `_DEFAULT_RESUME_MANAGER_DIR`). `tailor_resume.py` has no
  `--target-pages` flag today — it isn't exposed there either, so this
  script doesn't invent one; `run_tailoring()`'s own default
  (`target_pages=2`) applies unchanged.

**New dependency, scoped to this one script.** `GEMINI_API_KEY` (or
`PAID_GEMINI_KEY`, same override this codebase's other Gemini callers
already support) is required only to run `apply_from_prompt.py`.
`convert_resume.py`, `tailor_resume.py`, and `merge_resumes.py` are
completely unaffected and remain fully local.

**Routing: which of the three tailoring entry points to use is agent
judgment, documented as a decision procedure, not new classification
code.** The user's real request is often conversational ("tailor my
resume for this opportunity"), and what they hand over varies: a path to
a JD file they already have, a complete job posting pasted inline, or
just a rough description. Distinguishing "this text is already a
complete job description" from "this text is a rough description" is an
open-ended natural-language judgment call — precisely the kind of task
this whole revision already established belongs to an agent's judgment,
not a deterministic heuristic (word-count and keyword-matching
heuristics are both easy to fool in either direction). Rather than write
classification code that would need its own real-world tuning the way
§12's duplicate-detection threshold did, this decision is documented as
guidance for whichever agent is handling the request, in
`resume_manager/README.md`:
1. **An existing job description file is already known or found**
   (the user names a path, or the agent finds a matching
   `applications/*/job_description.txt` by listing/reading the
   `applications/` directory — ordinary tool use, not new pipeline code)
   → run `tailor_resume.py --jd-file <path> --application-name <name>`
   directly.
2. **The user pastes what reads as a complete job posting** (has the
   shape of a real listing — responsibilities, qualifications, etc., not
   just a one-line gist) → the agent saves it verbatim to a new
   application folder's `job_description.txt`, derives `--application-name`
   itself from the posting's own company/role text (the same judgment
   call Stage 1 would otherwise make with an Ollama call — skipped here
   since the agent is already reading the full text), and runs
   `tailor_resume.py --jd-file <path> --application-name <name>`
   directly — bypassing `apply_from_prompt.py` and its Gemini dependency
   entirely, since there's nothing left to interpret or brainstorm that
   the existing tailoring call doesn't already do from a real job
   description.
3. **Only a rough, general description of the opportunity is given** →
   the agent runs `apply_from_prompt.py --prompt "..."`, invoking the
   full three-stage pipeline above.

This keeps `apply_from_prompt.py` itself simple and fully testable (it
always receives a rough description, never has to decide what kind of
input it was handed), and keeps the fuzzy, evolving part of this
decision in documentation an agent reads and reasons from, rather than
in code that would need the same kind of real-run calibration §12's
duplicate detection needed.

**Error handling.** Stage 1 failure aborts before creating any
application folder or writing any file — there is no job description to
proceed with. Stage 2 failure degrades to `guidance=None` and continues.
Stage 3 is `run_tailoring()`, unchanged, with its own existing error
handling (§8).

**Testing.** `interpret_opportunity_prompt()` and
`brainstorm_relevant_content()` each get unit tests mocking `call_ollama`
and the Gemini client respectively (the latter following
`test_transcribe_notes.py`'s existing pattern for mocking
`common/gemini_utils.py` callers), covering: a well-formed response, a
malformed/unparseable response, and an unreachable/erroring backend.
`create_application_from_prompt()` gets an orchestration-level test
(both calls mocked) verifying it calls `run_tailoring()` with the
derived job description, application name, and Stage 2's guidance text,
and a second test verifying a Stage 2 failure still calls
`run_tailoring()`, with `guidance=None`, rather than aborting.

**Non-goals of this revision.** A code-level "does a matching
application already exist" search utility — deliberately left to
ordinary agent tool use (Glob/Grep/Read over `applications/`) rather
than new fuzzy-matching code, since it's the same kind of fuzzy
real-world judgment call this revision already routes to agent
reasoning rather than code (see Routing, above); re-running this
pipeline's Stage 1/Stage 2 to *revise* an already-tailored application
(out of scope — re-running `tailor_resume.py` directly, or hand-editing
via §14's Markdown sync, already cover that case); any change to
`tailor.py`, `render.py`, or `validate.py` (none needed — Stage 3 reuses
`run_tailoring()` exactly as it exists today).
