# Resume Manager — Design Spec

Date: 2026-09-09
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

Today the user's resume exists only as a single PDF
(`personal-website/AaronScherf.github.io/static/uploads/resume.pdf`) —
there's no editable source, no way to keep a longer "everything I've ever
done" version, and tailoring it to a specific job description means manual
rewriting from scratch each time. This spec designs **`resume_manager`**: a
new subproject that converts the existing resume PDF into Markdown using the
academic-rag-model's established journal-article/notes conversion pipeline,
establishes a hand-maintained "master resume" Markdown file the user keeps
expanding over time, and adds a local-LLM pipeline that tailors the master
to a specific job description and renders the result to a polished PDF —
adapted from the user's own brainstorm
(`docs/brainstorms/resume_manager_brainstorm.md`), with two changes driven
by this project's existing conventions: reuse `notes/transcribe_notes.py`'s
`process_pdf()` for conversion instead of a bespoke script, and reuse
`common/ollama_utils.py` for the tailoring LLM call instead of the brainstorm
draft's raw `ollama.generate()` (which lacks the `num_ctx` sizing fix that
`common/ollama_utils.py` already carries — see
`docs/status/2026-09-06-video-lecture-notes-status.md` for the bug this
avoids repeating).

**Goals**
- Bootstrap-convert `resume.pdf` into Markdown once, using the same tiered
  free-extraction/hybrid-repair/Gemini-vision pipeline already used for
  journal articles and notes (`notes/transcribe_notes.py:process_pdf`).
- Store a hand-maintained **master resume** Markdown file under
  `research/independent-research/projects/resume-manager/` that the user
  keeps expanding into a long, comprehensive record of everything they've
  done — never overwritten by tooling.
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
  space or doc-type vocabulary. `process_pdf()`'s own indexing side effect
  is deliberately pointed at an isolated location so it never touches
  `research/.index/` (see §3).
- No hard-blocking validation — the automated fact-diff check (§5) flags
  discrepancies for manual review; it never refuses to render a PDF.

## 2. Architecture

A new sibling package, `resume_manager/`, alongside `video_notes/`,
`problem_gen/`, `journal_articles/`, `notes/` in `academic-rag-model/`.
Depends on `notes/transcribe_notes.py:process_pdf` (conversion, reused
unchanged) and `common/ollama_utils.py:call_ollama` (tailoring, reused
unchanged). Run as modules from the `academic-rag-model/` root, matching
every other subproject:

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
PDF changes), not part of the per-application pipeline:

1. Copies `personal-website/AaronScherf.github.io/static/uploads/resume.pdf`
   into `research/independent-research/projects/resume-manager/resume.pdf`,
   so the source PDF and everything derived from it live together,
   independent of the personal-website repo's own layout.
2. Calls `process_pdf(pdf_path, client, model_override, academic_hub_root,
   known_doc_types={"resume"})` exactly as `journal_articles/
   convert_journal_articles.py` already does for its own corpus — same
   `get_gemini_client()` / `load_dotenv_override()` setup from
   `common/gemini_utils.py`. `academic_hub_root` is passed as the
   `resume-manager/` folder itself (not `research/`), so `process_pdf`'s
   indexing side effect writes an isolated `.index/` under `resume-manager/`
   rather than the shared one journal articles and notes use — a resume
   card has no business in that corpus, per §1's non-goals, and
   `_write_markdown_and_index`'s indexing failure path is already
   non-fatal (a warning, never blocks the Markdown output) if this ever
   errors.
3. `process_pdf` writes its usual output to
   `resume-manager/processed_outputs/resume.md` (its own
   `processed_outputs/` sibling-folder convention, unchanged).

The user then hand-copies/cleans that raw conversion into
`resume-manager/resume_master.md` — a resume's layout (columns, dense
bullets) converts messier than prose, so this step is deliberately manual,
not automated. `resume_master.md` is the file the user keeps expanding over
time into the long, comprehensive master record; `processed_outputs/
resume.md` is left as-is as a reference of the original bootstrap.

**Required structure for `resume_master.md`** (so §5's fact-diff check has
something reliable to parse): each Experience/Education entry is an `### `
heading of the form `### <Org> — <Role> (<Start> – <End or "Present">)`,
followed by bullet points. Other sections (Skills, Projects, etc.) are
freeform. This convention is documented in the subproject's `README.md` and
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

`render.py`, carried over from the brainstorm draft largely as-is:
Markdown → HTML via the `markdown` library → styled PDF via `weasyprint`,
using the letter-size/margin/heading CSS block already drafted in
`docs/brainstorms/resume_manager_brainstorm.md`. Output:
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
  processed_outputs/resume.md       # raw bootstrap conversion (reference only)
  resume_master.md                  # hand-maintained master, expanded over time
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
- `process_pdf`'s existing indexing-failure handling (catch + warn, never
  blocks the Markdown write) is reused unchanged for the bootstrap step.

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
  non-empty PDF via `weasyprint` (real library call — the one exception to
  "mock every external boundary," since there's no meaningful mock for PDF
  byte output and the library itself needs no network/model).
- `convert_resume.py`: thin — verifies it calls `process_pdf` with the
  expected `academic_hub_root` (the isolated `resume-manager/` path, not
  `research/`) and `known_doc_types={"resume"}`; `process_pdf`'s own
  conversion-tier logic is already covered by `notes/`'s and
  `journal_articles/`'s existing tests and isn't re-tested here.
- Real end-to-end run against the user's actual resume and one real job
  description as manual validation before trusting the pipeline, the same
  way other subprojects' status docs record a first real-corpus pass before
  being trusted at scale.

## 10. Open questions / follow-on (not decided by this spec)

- **Metric-extraction regex coverage** (§5) is necessarily heuristic —
  real resumes phrase numbers in more ways than `%`/`$`/`x` (e.g. "reduced
  latency by half", "team of 12"). The plan should collect a handful of
  real bullets from the user's own resume to validate the pattern set
  against, rather than guessing patterns without real examples.
- **Cover-letter generation** and **JD URL scraping** are both explicitly
  deferred (§1) — worth revisiting once the core tailor/validate/render
  loop is proven on real applications.
- **Multiple resume "flavors"** (e.g. a separate master for
  research-track vs. industry-track roles) aren't addressed — out of scope
  until the single-master version proves insufficient in practice.
