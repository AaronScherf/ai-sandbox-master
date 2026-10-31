# Gap analysis recall probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `gap run --probe` asks OpenAlex for the top 25 works on the question's wording and reports how many are already in the corpus, with a Wilson 95% interval.

**Architecture:** One new module `agent/literature/gap/probe.py` (pure helpers plus `run_probe` with an injectable fetch), a small change to `report.py` (fills the existing `external` slot and renders one section) and `cli.py` (three flags). The verdict, classification and the default offline run are untouched.

**Tech Stack:** Python 3.13, unittest/pytest, the existing `discovery.discover_journal_articles.discovery.iter_topic_works` and `Work`.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-31-literature-gap-recall-probe-design.md`

## Global Constraints

- No network in tests: fetch is injected or `agent.literature.gap.probe.iter_topic_works` is patched; works are invented.
- No LLM, no paid API. `--probe` is opt-in; without it the run is byte-for-byte the slice 1 behaviour (report gains `external: null` as before).
- The verdict and `counts` never depend on the probe. Misses are stored as a count only, never titles.
- Interval is Wilson 95% (z = 1.96). Never a percent complete.
- Run tests from `ai-sandbox/academic-rag-model/` with the main checkout's venv; new test file `tests/agent/literature/test_lit_gap_probe.py` on invented data only.

## Review Focus

- `--probe` without a contact email must refuse before any search or file write (spec 7), using `--mailto` or `$OPENALEX_CONTACT_EMAIL` (the `backfill-years` convention; spec amended: env fallback allowed, git config never read).
- A question with no intervention, outcome or country constraint has an empty query: report an error, make no request.
- OpenAlex ids come as `https://openalex.org/W123` and DOIs as `https://doi.org/10.x`: matching must normalize both sides and be case-insensitive.
- A work with no DOI/id/title (None) must not match a corpus paper whose field is also None.
- Network failure must still write the offline report and keep the exit code.

---

### Task 1: Pure helpers (`wilson`, `build_query`, `match_work`)

**Files:**
- Modify: `agent/literature/gap/corpus.py` (add `openalex_id: str | None = None` to `PaperRow`; select it in `load_corpus`)
- Create: `agent/literature/gap/probe.py`
- Test: `tests/agent/literature/test_lit_gap_probe.py`

**Interfaces:**
- Produces: `wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None` (None when n == 0);
  `build_query(constraints: list[Constraint], vocabs: dict, subregions: Subregions) -> str`;
  `match_work(work, corpus: Corpus) -> tuple[str, str] | None` returning `(file_id, "openalex_id" | "doi" | "title")`.
- Consumes: `Constraint`, `vocab_for`, `Corpus`, `Subregions.names` (code -> name), `Work` (`openalex_id`, `doi`, `title`).

- [ ] **Step 1: Write failing tests** in `test_lit_gap_probe.py`:
  - `test_wilson_known_values`: `wilson(0, 25)` lower is 0.0 and upper within 0.001 of 0.1332; `wilson(25, 25)` upper 1.0; `wilson(5, 10)` within 0.001 of (0.2366, 0.7634); `wilson(0, 0) is None`.
  - `test_query_uses_intervention_outcome_and_country_names_only`: constraints intervention `i.cash`, outcome `o.food`, countries `SO`, study_design `d.rct` with toy subregions (`write_toy_tables`) gives `"Cash transfers Food security Somalia"`; a label group contributes its label once; duplicate labels collapse; no relevant constraint gives `""`.
  - `test_match_by_id_then_doi_then_title`: corpus papers built with `make_corpus` plus `openalex_id` set via a helper below; a work with id `https://openalex.org/W1` matches paper with `W1` (`by == "openalex_id"`); DOI `https://doi.org/10.1/ABC` matches stored `10.1/abc` (`"doi"`); title `Cash, Transfers!` matches `cash transfers` (`"title"`); a work matching nothing returns None; a work whose id/doi/title are None never matches a paper with None fields.
  - `gap_helpers.make_conn` gets an optional per-paper `"openalex_id"` key written to `papers.openalex_id` (the column exists; currently inserted as None).
- [ ] **Step 2: Run** `python -m pytest tests/agent/literature/test_lit_gap_probe.py -q`. Expected: FAIL (module/attribute missing).
- [ ] **Step 3: Implement** the helpers. Normalization: ids strip the `https://openalex.org/` prefix and lowercase; DOIs strip `https://doi.org/` and lowercase; titles lowercase, non-alphanumerics to single spaces (same rule as `backfill_years._normalize_title`; import it). Wilson: standard score interval, clamp to [0, 1].
- [ ] **Step 4: Run** the file plus `tests/agent/literature -q -k gap`. Expected: PASS.
- [ ] **Step 5: Commit** `git add` the four paths; `feat(literature): gap probe helpers`.

### Task 2: `run_probe`

**Files:**
- Modify: `agent/literature/gap/probe.py`
- Test: `tests/agent/literature/test_lit_gap_probe.py`

**Interfaces:**
- Consumes: Task 1 helpers; `discovery.discover_journal_articles.discovery.iter_topic_works(keywords, mailto, batch_size)`.
- Produces: `run_probe(corpus, constraints, vocabs, subregions, mailto: str, n: int = 25, fetch=None, today: str | None = None) -> dict`.
  Success: `{"query", "requested": n, "retrieved", "in_corpus", "interval": [lo, hi] | None, "matched": [{"file_id", "by"}], "not_in_corpus", "fetched": today or date.today().isoformat()}`.
  Failure: `{"query", "requested": n, "error": str}`. `fetch` defaults to the module-level imported `iter_topic_works`.

- [ ] **Step 1: Write failing tests** with a fake `fetch(keywords, mailto, batch_size)` returning invented `Work`s (and recording its arguments):
  - `test_probe_counts_matches_and_intervals`: 4 works, 2 matching corpus papers, `n=25` gives retrieved 4, in_corpus 2, `not_in_corpus` 2, interval equals `wilson(2, 4)`, `matched` lists file ids with `by`; fake saw `batch_size == 25` and the built query.
  - `test_probe_takes_at_most_n_works`: fake yields 10, `n=3` gives retrieved 3.
  - `test_empty_result_has_no_interval`: retrieved 0, in_corpus 0, `interval is None`.
  - `test_empty_query_errors_without_calling_fetch`: only a study_design constraint; result has `error`, fetch not called.
  - `test_fetch_exception_becomes_error`: fake raises `RuntimeError("boom")`; result `error` contains "boom".
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** `run_probe`: build query; empty gives error dict; `itertools.islice(fetch(query, mailto, n), n)`; catch `Exception` around iteration only (network errors vary), match each work, count. A work matching a paper counts once; two works matching the same paper both count (k counts works).
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(literature): gap recall probe`.

### Task 3: Report section

**Files:**
- Modify: `agent/literature/gap/report.py` (`build_report(..., probe: dict | None = None)`: `"external": {"probe": probe} if probe else None`; `render_markdown` adds "## Recall probe" after Coverage when `report["external"]`)
- Test: `tests/agent/literature/test_lit_gap_report.py` (new tests) 

**Interfaces:**
- Consumes: the `run_probe` dict. Produces: `report["external"]["probe"]`; Markdown lines exactly:
  success: `Top {retrieved} OpenAlex results by relevance for "{query}"; {in_corpus} are in the corpus ({lo:.0%} to {hi:.0%} interval). This measures the corpus against OpenAlex's ranking for this wording, not against all the literature.`;
  zero retrieved: `OpenAlex returned no results for "{query}".`; error: `Probe not run: {error}`.

- [ ] **Step 1: Write failing tests**: `external` stays None without a probe (existing test already asserts this); with a success dict the JSON round-trips and Markdown contains the exact success sentence for `in_corpus=2, retrieved=25` using `wilson(2, 25)`; error dict renders `Probe not run: boom`; the verdict and counts are identical with and without a probe.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** as above.
- [ ] **Step 4: Run** `-k gap`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(literature): gap report recall probe section`.

### Task 4: CLI and docs

**Files:**
- Modify: `agent/literature/cli.py` (`gap` parser: `--probe` store_true, `--probe-n` int default 25, `--mailto` default None; `cmd_gap`), `agent/literature/README.md`, `docs/status/literature/2026-10-29-stage5-gap-analysis-slice1.md` (a "Slice 2: recall probe" paragraph)
- Test: `tests/agent/literature/test_lit_gap_cli.py` (new class, patching `agent.literature.gap.probe.iter_topic_works`)

**Interfaces:**
- Consumes: `probe.run_probe`, `greport.build_report(..., probe=...)`. In `cmd_gap` for `action == "run"`: `mailto = args.mailto or os.environ.get("OPENALEX_CONTACT_EMAIL")`; with `--probe` and no mailto print `gap: --probe needs --mailto or OPENALEX_CONTACT_EMAIL` and return 2 before reading the db; after classification call `run_probe(...)` and pass it to `build_report`; print `probe: {k} of {n} in the corpus` or `probe: not run ({error})` (warning, exit code unchanged).

- [ ] **Step 1: Write failing tests**: `--probe` without mailto (env cleared with `mock.patch.dict(os.environ, clear=True)`) returns 2 and writes no report; with `--mailto a@b.c` and a patched fetch of 3 invented works (one matching a fixture paper by title) exit 0, `report["external"]["probe"]["in_corpus"] == 1` and stdout contains `probe: 1 of 3`; patched fetch that raises gives exit 0, `external.probe.error` set and `report.md` written; a run without `--probe` has `external is None` and never calls the patched fetch.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** the flags and wiring; update the README command list and "Not built" (probe built; live search, classification, discovery queue and `found_externally` still not built).
- [ ] **Step 4: Run** `python -m pytest tests/agent/literature -q`. Expected: all pass. Then smoke on the real db with `--report-root` set to the scratchpad and the user's go-ahead for one OpenAlex request (free, no key): one `gap run --probe` for the cash-transfer question, counts only.
- [ ] **Step 5: Commit** `feat(literature): gap run --probe`; then `python -m tools.land_branch check --full` from `ai-sandbox/academic-rag-model/` and ask the owner to approve the change id.
