# Literature gap analysis, slice 1 (offline) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `python -m agent.literature gap run|question` so a research question (explicit facet constraints or free text via an optional task card) yields a deterministic verdict, coverage report and evidence list from `literature.sqlite`, with no network and no LLM in the core.

**Architecture:** A new subpackage `agent/literature/gap/` of small pure modules (corpus loader, id-based matcher, term resolution with stop-and-pick, sibling/subregion widening, classifier, coverage, report) driven by a thin `cmd_gap` in `cli.py`. The free-text card is one more stage module (`gap/card.py`) registered in `cmd_submit` beside `contribute` and `synth`. Existing `db query` / `cluster define` are untouched.

**Tech Stack:** Python 3.13, stdlib `sqlite3`/`json`/`dataclasses`, PyYAML, `unittest`-style tests run with pytest, `core.agent_tasks` for the card.

**Spec:** `docs/superpowers/specs/literature_taxonomy/2026-10-29-literature-gap-analysis-design.md` (section numbers below refer to it). Run everything from `ai-sandbox/academic-rag-model/` inside the worktree `.worktrees/claude-literature-gap-analysis` (branch `claude/literature-gap-analysis`). Worktrees have no `.venv`; use the main checkout's interpreter.

## Global Constraints

- No network call and no LLM in slice 1's core; the card route needs no API (`--driver api` is not offered for this stage).
- Verdict names, fixed: `tried_directly`, `tried_adjacent`, `found_externally_not_in_corpus` (reserved, never produced in slice 1), `no_evidence_in_corpus`.
- Thresholds: 8 candidates per unresolved constraint, partial matches capped at 10, thin flag when fewer than 3 direct papers.
- Matching is by term id (descendants included); a label clause applies only to facts whose `shown` starts with `proposed:`. Tier A/B facts only; excluded papers and papers with no record never appear.
- Relaxable facets: `intervention`, `outcome`, `countries`. Exactly one constraint relaxed. Never widen sector, population, study design, data source.
- A term whose parent is a top-level grouping (parent has no parent) or that has no parent is not widened.
- Every report carries the fixed completeness line: `Corpus completeness: not measured (needs OpenAlex, slice 2). The corpus was assembled by discovery, not sampled; absence here is not absence in the literature.`
- Reports are local only, under `<report-root>/<run-id>/` (default `<index-root>/literature_gap/`), gitignored. No Artifact in slice 1.
- Tests use invented data only: ids like `paper-a`, titles "Study A", quotes like `quote a1`, a synthetic vocabulary, a toy subregion table. No 3ie text, no paper text, no network.
- `db query` and `cluster define` behaviour and tests unchanged.
- Stage explicit paths only; never `git add -A`. Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Only the owner lands on `main`.

## Review Focus

Failure modes the spec implies that no single task's happy path covers (each gets a pinning test in the owning task):

1. A phrase that matches no term at all: the run stops with a clear "no candidate" message and exit 2, not a crash or a silent empty constraint (Task 3).
2. A db with zero papers or zero facts: verdict `no_evidence_in_corpus`, counts zero, report still renders (Task 6).
3. Two constraints on the same facet: both must match; a paper with only one is partial (Task 5).
4. A paper that is direct is never also listed adjacent, even when a widening would also match it (Task 5).
5. Lower-case or mixed-case country input (`so`) resolves to `SO` and an unknown code or name stops with candidates or an error (Task 3).

## File Structure

| File | Responsibility |
| --- | --- |
| `agent/literature/gap/__init__.py` | package marker, `VERDICTS` tuple |
| `agent/literature/gap/corpus.py` | `Fact`, `PaperRow`, `Corpus`, `load_corpus(conn)` |
| `agent/literature/gap/match.py` | `Constraint`, `vocab_for`, `fact_matches`, `papers_matching` |
| `agent/literature/gap/subregions.py` | `Subregions`, `load_subregions`; data file `gap/country_subregions.yaml` |
| `agent/literature/gap/resolve.py` | `Candidate`, `Resolution`, `resolve` (stop-and-pick, lexical ranking) |
| `agent/literature/gap/adjacent.py` | `Widening`, `widen` |
| `agent/literature/gap/classify.py` | `GapResult`, `classify` (direct, adjacent, different method, partial, verdict) |
| `agent/literature/gap/coverage.py` | `Sidecar`, `read_sidecar`, `coverage` (counts, blind spots, stale db) |
| `agent/literature/gap/report.py` | `build_report`, `render_markdown`, `write_report`, `gap_dir` |
| `agent/literature/gap/card.py` | free-text constraint card: `STAGE`, `make_tasks`, `validate_result`, `apply_result` |
| `agent/literature/cli.py` | `gap` subcommand, `cmd_gap`, `cmd_submit` dispatch entry |
| `tests/agent/literature/gap_helpers.py` | synthetic vocabularies, toy subregions, in-memory corpus builder |
| `tests/agent/literature/test_lit_gap_*.py` | one test file per module |
| `.gitignore` | `ai-sandbox/research/literature_gap/` |

Deviations from the spec, deliberate: (a) the subregion table lives at `gap/country_subregions.yaml`, not `vocab_data/`, because `load_vocab_dir` loads every `*.yaml` there as a vocabulary and would reject it; it also carries country names so a name phrase can be resolved; (b) there is no `gap submit`: the existing `submit RUN_ID` dispatches by run stage, so the card is submitted with it and `gap run` then reads the `constraints.json` the card wrote; (c) test files follow the existing `test_lit_*` prefix, `test_lit_gap_*.py`; (d) `--report-root` is added so a smoke run against the main checkout's data does not write into it.

---

### Task 1: Corpus loader and id-based matcher

**Files:**
- Create: `agent/literature/gap/__init__.py`, `agent/literature/gap/corpus.py`, `agent/literature/gap/match.py`
- Create: `tests/agent/literature/gap_helpers.py`
- Test: `tests/agent/literature/test_lit_gap_match.py`

**Interfaces:**
- Produces:
  - `corpus.Fact(facet: str, shown: str, label: str, tier: str, quote: str | None, locator: str | None)` frozen dataclass.
  - `corpus.PaperRow(file_id: str, title: str | None, year: int | None, doi: str | None)`.
  - `corpus.Corpus(papers: dict[str, PaperRow], facts: dict[str, list[Fact]], results: dict[str, list[dict]])`; result dicts have keys `claim, direction, magnitude, quote`.
  - `corpus.load_corpus(conn: sqlite3.Connection) -> Corpus`.
  - `match.Constraint(facet: str, value: str, phrase: str = "", resolved_by: str = "exact")` frozen dataclass; `value` is a resolved term id for vocabulary facets and an upper-case ISO alpha-2 code for `countries`.
  - `match.vocab_for(facet: str, vocabs: dict) -> Vocabulary | None` (via `schema.FACETS`; `None` for `countries`).
  - `match.fact_matches(c: Constraint, fact: Fact, vocabs: dict) -> bool`.
  - `match.papers_matching(corpus: Corpus, constraints: list[Constraint], vocabs: dict) -> list[str]` (sorted file ids where every constraint matches some fact).
  - Test helper `gap_helpers.make_conn(papers: dict[str, dict]) -> sqlite3.Connection` building the real `db._TABLES` schema in memory from `{file_id: {"title", "year", "facts": [(facet, term_id, label, tier)], "results": [(claim, direction)]}}`, plus `gap_helpers.VOCABS` (synthetic intervention/outcome/sector/study_design/population/data_source vocabularies) with the tree below.
- Consumes: `agent.literature.compare._ancestors`, `agent.literature.vocab.Vocabulary`, `agent.literature.schema.FACETS`, `agent.literature.db._TABLES`, `agent.literature.transcript.normalize`.

Synthetic tree for `gap_helpers.VOCABS` (ids invented): intervention `i.social` (root) > `i.cash` > `i.cash_uncond`, `i.cash_cond`; `i.cash` siblings `i.voucher`, `i.food`; `i.social` also has `i.root_only` with no children; a second root `i.agri` > `i.seeds` (child of root, so not widenable). Outcome `o.welfare` (root) > `o.food` > `o.food_cons`, `o.food_div`; `o.food` sibling `o.health`. Two terms in different positions with the same label "training" (`i.agri.training` under `i.agri`, `i.social.training` under `i.social`). Sector flat: `s.social`, `s.agri`. Study design flat: `d.panel`, `d.rct`.

- [ ] **Step 1: Write the failing tests** in `test_lit_gap_match.py`:
  - `test_load_corpus_reads_papers_facts_results`: two papers, assert `corpus.facts["paper-a"][0].facet`, years, results grouped by file id.
  - `test_descendant_matches_parent_constraint`: constraint `Constraint("intervention", "i.cash")`; paper with fact `i.cash_uncond` is matched, paper with `i.voucher` is not.
  - `test_matching_is_by_id_so_same_label_terms_stay_distinct`: constraint on `i.agri.training` matches a paper with that id and not a paper with `i.social.training` although both have label "training".
  - `test_proposed_fact_matches_on_label_only`: fact `shown="proposed:cash grants"`, label `cash grants`, constraint on a term labelled "Cash Grants" matches; a proposed fact with another label does not.
  - `test_country_constraint_is_case_insensitive_on_the_fact`: `Constraint("countries", "SO")` matches fact shown `so` and `SO`.
  - `test_papers_matching_requires_every_constraint`: two constraints, only the paper with both is returned; two constraints on one facet both required.
- [ ] **Step 2: Run to verify failure**: `python -m pytest tests/agent/literature/test_lit_gap_match.py -v` → FAIL (`ModuleNotFoundError: agent.literature.gap`).
- [ ] **Step 3: Implement** `corpus.py`, `match.py`, `gap_helpers.py` per the Interfaces block. `load_corpus` runs three `SELECT`s over `papers`, `facts`, `results`. `fact_matches`: countries → `fact.facet == "countries" and fact.shown.upper() == c.value`; vocabulary facets → `fact.facet == c.facet` and (`fact.shown == c.value` or `c.value in _ancestors(fact.shown, vocab)`) or (`fact.shown.startswith("proposed:")` and `normalize(fact.label) == normalize(vocab.terms[c.value].label)`).
- [ ] **Step 4: Run to verify pass**: same command → PASS.
- [ ] **Step 5: Commit** `agent/literature/gap/__init__.py agent/literature/gap/corpus.py agent/literature/gap/match.py tests/agent/literature/gap_helpers.py tests/agent/literature/test_lit_gap_match.py` with message `feat(literature): gap analysis corpus loader and id-based matcher`.

---

### Task 2: Country subregion table

**Files:**
- Create: `agent/literature/gap/subregions.py`, `agent/literature/gap/country_subregions.yaml`
- Modify: `agent/literature/vocab_data/README.md` (one paragraph: the table's source and why it lives outside `vocab_data/`)
- Test: `tests/agent/literature/test_lit_gap_subregions.py`

**Interfaces:**
- Produces: `Subregions` dataclass with `by_code: dict[str, tuple[str, str]]` (code → (name, subregion)); methods `region_of(code: str) -> str | None`, `members(subregion: str) -> frozenset[str]`, `codes_for_name(text: str) -> list[str]` (normalized exact name match). `load_subregions(path=None) -> Subregions` (cached like `load_countries`).
- Consumes: `agent.literature.vocab.load_countries`.
- YAML shape: `countries: [{code: SO, name: Somalia, subregion: Eastern Africa}, ...]`.

- [ ] **Step 1: Write the failing tests**:
  - `test_every_code_in_countries_yaml_has_a_subregion`: for each code in `load_countries()`, `load_subregions().region_of(code)` is not None.
  - `test_every_subregion_code_is_a_valid_country`: each key passes `is_country`.
  - `test_somalia_neighbours`: `region_of("SO") == "Eastern Africa"` and `"KE" in members("Eastern Africa")`.
  - `test_name_lookup_is_case_and_space_insensitive`: `codes_for_name("  somalia ") == ["SO"]`.
  - `test_toy_table_loads_from_a_path`: write a four-row YAML in a temp dir and load it.
- [ ] **Step 2: Run to verify failure** (`-k subregions`).
- [ ] **Step 3: Implement** `subregions.py` and author `country_subregions.yaml` for every code in `vocab_data/countries.yaml`, using UN M49 subregion names (public UN statistical standard); note provenance in the README paragraph and as a header comment in the YAML. A code the standard does not place gets no row; the first test then names it, and the builder adds it or documents the exception in the README.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** the four paths above with message `feat(literature): committed country-to-subregion table for gap analysis`.

---

### Task 3: Term resolution with stop-and-pick

**Files:**
- Create: `agent/literature/gap/resolve.py`
- Test: `tests/agent/literature/test_lit_gap_resolve.py`

**Interfaces:**
- Produces:
  - `Candidate(term_id: str, label: str, level: int, children: int, papers: int)` frozen dataclass (`papers` = direct matches that term would give on its own, via `papers_matching`; for countries `term_id` is the code, `level` 0, `children` 0).
  - `Resolution(constraint: Constraint | None, candidates: list[Candidate], message: str)`; resolved iff `constraint is not None`.
  - `resolve(corpus: Corpus, vocabs: dict, facet: str, value: str, *, pick: str | None = None, resolved_by: str = "user", subregions: Subregions | None = None, limit: int = 8) -> Resolution`.
  - `level_of(term_id: str, vocab) -> int` (root = 0).
  - `shortlist(corpus: Corpus, vocabs: dict, facet: str, text: str, limit: int = 8) -> list[Candidate]`: the lexical ranking `resolve` uses, exposed so the Task 9 card can reuse it; add a test that it returns the same order `resolve` reports.
- Consumes: Task 1 (`Constraint`, `papers_matching`, `vocab_for`), Task 2 (`Subregions`), `vocab.is_country`, `vocab.Vocabulary.terms`, `transcript.normalize`.
- Behaviour (spec 4.2): with `pick`, the pick must be a term id of the facet's vocabulary (or valid country) else unresolved with message naming it; resolved constraint records `phrase=value`, `value=pick`. Without `pick`, scan **all** terms for exact normalized match on id/label/alias: exactly one → resolved with `resolved_by="exact"`; more than one → unresolved, candidates are those terms; none → lexical ranking (token overlap against label and aliases, definition at lower weight; score 0 excluded; ties by term id), top `limit`. Countries: value upper-cased; valid alpha-2 code resolves; otherwise `subregions.codes_for_name`; one hit resolves, several or none give candidates/message. An unknown facet is a `ValueError`.

- [ ] **Step 1: Write the failing tests** (synthetic vocabularies):
  - `test_exact_label_resolves_to_one_term`: "Cash" (case-insensitive) → `i.cash`, `resolved_by == "exact"`.
  - `test_duplicate_label_is_ambiguous_and_lists_both_positions`: "training" → unresolved, two candidates with different `term_id`.
  - `test_unresolved_phrase_gives_ranked_candidates_with_level_children_and_paper_counts`: "unconditional transfer" → first candidate `i.cash_uncond`, fields `level`, `children`, `papers` match the fixture.
  - `test_no_overlap_gives_no_candidates_and_a_message` (Review Focus 1): "zzz" → `constraint is None`, `candidates == []`, message mentions no candidate.
  - `test_candidate_list_is_capped_at_eight`.
  - `test_pick_resolves_and_records_the_phrase`: `pick="i.cash"` → constraint `value == "i.cash"`, `phrase` is the original value, `resolved_by == "user"`.
  - `test_pick_outside_the_facet_vocabulary_is_rejected`: a `o.food` pick on `intervention`.
  - `test_country_code_case_and_name` (Review Focus 5): "so" → `SO`; "Somalia" with the toy table → `SO`; "XX" → unresolved with a message.
  - `test_unknown_facet_raises_value_error`.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `resolve.py` per the Behaviour block.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** `agent/literature/gap/resolve.py tests/agent/literature/test_lit_gap_resolve.py` with message `feat(literature): gap constraint resolution with stop-and-pick candidates`.

---

### Task 4: Widening (adjacent context rules)

**Files:**
- Create: `agent/literature/gap/adjacent.py`
- Test: `tests/agent/literature/test_lit_gap_adjacent.py`

**Interfaces:**
- Produces: `Widening(constraint: Constraint, kind: str, term_ids: frozenset[str], countries: frozenset[str], label: str)` and `widen(c: Constraint, vocabs: dict, subregions: Subregions) -> Widening | None`; `Widening.matches(fact: Fact, vocabs: dict) -> bool`; `Widening.label_for(fact: Fact, vocabs: dict) -> str`.
- Consumes: Task 1 `Fact`/`Constraint`/`vocab_for`, `_ancestors`; Task 2 `Subregions`.
- Rules (spec 4.4): `intervention`/`outcome` term T with parent P where P itself has a parent: `term_ids` = the other children of P; a fact matches if its id is in `term_ids` or has an ancestor in it. T with no parent, or whose parent is a root, returns `None`. `countries`: same-subregion codes excluding the constraint's own; a code absent from the table returns `None`. Other facets return `None`. Labels: `different outcome (sibling: <sibling label> <- <T label>; <n> siblings)`, `different intervention (...)`, `different country (same subregion: <name>)`.

- [ ] **Step 1: Write the failing tests**:
  - `test_outcome_widens_to_siblings_with_descendants`: constraint `o.food_cons` → a paper fact `o.food_div` matches; `label_for` contains `different outcome`, the sibling label and the sibling count.
  - `test_own_subtree_is_not_in_the_widening`.
  - `test_term_under_a_root_is_not_widened`: `i.seeds` (parent `i.agri` is a root) → `None`; `i.root_only`'s parent is a root → `None`; a root term → `None`.
  - `test_grandparent_is_not_adjacent`: constraint `o.food_cons`; a fact `o.health` (a child of the grandparent's other branch) does not match.
  - `test_country_widens_to_same_subregion_only` with the toy table (SO → KE yes, NG no).
  - `test_country_missing_from_table_cannot_be_widened`.
  - `test_sector_population_design_and_data_source_are_never_widened`.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `adjacent.py`.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** `agent/literature/gap/adjacent.py tests/agent/literature/test_lit_gap_adjacent.py` with message `feat(literature): gap analysis sibling and subregion widening`.

---

### Task 5: Classification and verdict

**Files:**
- Create: `agent/literature/gap/classify.py`; modify `agent/literature/gap/__init__.py` (add `VERDICTS = ("tried_directly", "tried_adjacent", "found_externally_not_in_corpus", "no_evidence_in_corpus")`)
- Test: `tests/agent/literature/test_lit_gap_classify.py`

**Interfaces:**
- Produces:
  - `GapResult(direct: list[str], adjacent: dict[str, list[str]], different_method: list[str], partial: list[tuple[str, int]], unwidenable: list[str], verdict: str, rule: str)`; `adjacent` maps file id → labels (one per qualifying relaxation); `partial` is `(file_id, exact_matches)` already ordered and capped at 10; `unwidenable` names relaxable constraints that returned `None` from `widen` (value strings).
  - `classify(corpus: Corpus, constraints: list[Constraint], vocabs: dict, subregions: Subregions) -> GapResult`.
- Consumes: Tasks 1, 2, 4.
- Rules (spec 4.3 to 4.6): direct = `papers_matching` all. Adjacent: not direct, and for exactly one relaxable constraint `c` the paper matches every other constraint exactly and `widen(c).matches` some fact; a paper may carry labels from several such single relaxations. `different_method`: constraints include a `study_design` one, paper matches all others exactly and fails only the design constraint(s), not direct. Partial: not direct, not adjacent, not `different_method`, with at least one exact match, ordered by exact count desc then year desc then file id, first 10. Verdict: direct non-empty → `tried_directly`; else adjacent non-empty → `tried_adjacent`; else `no_evidence_in_corpus`. `rule` is a one-sentence string stating which condition fired with counts.

- [ ] **Step 1: Write the failing tests** (synthetic corpus via `make_conn`/`load_corpus`):
  - `test_leaf_under_parent_constraint_is_direct`.
  - `test_one_adjacent_case_each_for_intervention_outcome_country`.
  - `test_two_relaxations_needed_is_partial_not_adjacent`.
  - `test_direct_paper_is_never_listed_adjacent` (Review Focus 4): a paper matching directly whose facts also satisfy a widening appears only in `direct`.
  - `test_two_constraints_on_one_facet_both_required` (Review Focus 3): paper with one of two outcomes is partial with count 1.
  - `test_single_constraint_question_can_be_relaxed_and_has_no_partial_list`.
  - `test_different_method_is_separate_from_adjacent_and_partial`; and a paper adjacent on one constraint that also fails the design constraint is partial.
  - `test_unwidenable_constraints_are_reported` (a root intervention, a country missing from the table).
  - `test_partial_list_is_capped_at_ten_and_ordered`.
  - `test_each_verdict_and_rule_text`; `test_found_externally_is_never_produced`.
  - Property-style: over a small grid of constraint sets, `set(direct).isdisjoint(adjacent)` and the verdict is a function of `len(direct)` and `len(adjacent)` only.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `classify.py`.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** `agent/literature/gap/__init__.py agent/literature/gap/classify.py tests/agent/literature/test_lit_gap_classify.py` with message `feat(literature): gap analysis classification and corpus-only verdict`.

---

### Task 6: Coverage, blind spots and stale-db check

**Files:**
- Create: `agent/literature/gap/coverage.py`
- Test: `tests/agent/literature/test_lit_gap_coverage.py`

**Interfaces:**
- Produces:
  - `Sidecar(eligible: int, excluded: int, without_record: int, open_tier_c: int, db_stale: bool, db_path: str, db_mtime: float, db_papers: int, scales: dict[str, str | None])`.
  - `read_sidecar(target: stage.Target, index_root: str, db_file: Path) -> Sidecar`: `eligible`/`without_record` from `eligible_papers` and `target.records.all_ids()` as `cmd_status` computes them; `excluded` from `target.records.excluded()`; `open_tier_c` = tier `C` facts over non-excluded records via `tiers.tiered_facts`; `db_stale` = any `*.json` under `target.records.dir` newer than the db file; `scales` = `core.geography.scale` of each record in the db (`target.records.read(fid, "a")`).
  - `coverage(corpus: Corpus, result: GapResult, constraints: list[Constraint], sidecar: Sidecar) -> dict` JSON-able, keys: `eligible`, `excluded`, `without_record`, `open_tier_c`, `db` (path, mtime, papers, stale), `designs` and `countries` (label → papers over direct plus adjacent), `year_range`, `result_directions` (tally), `thin` (bool), `completeness` (the fixed line), `blind_spots` with `proposed` (`{facet: [file_ids]}` for papers having a `proposed:` fact in a constrained facet but not direct) and, only when a `countries` constraint exists, `no_country_fact` (file ids) and `broad_scale` (file ids whose scale is `multi_country` or `global`, never counted as direct).
- Consumes: Tasks 1, 5; `agent.literature.papers.eligible_papers`, `tiers.tiered_facts`, `stage.Target`.

- [ ] **Step 1: Write the failing tests**:
  - `test_counts_and_distributions_over_direct_plus_adjacent`.
  - `test_thin_flag_at_two_and_three_direct_papers`.
  - `test_completeness_line_is_always_present`.
  - `test_blind_spot_proposed_fact_listed_not_counted_in_verdict`.
  - `test_blind_spot_no_country_and_broad_scale_only_with_a_country_constraint`.
  - `test_empty_corpus_gives_zero_counts_and_no_evidence` (Review Focus 2).
  - `test_read_sidecar_counts_with_a_built_target`: use `synth_helpers.build` (three papers), exclude one, assert `excluded == 1`, `eligible`, and `scales` populated; `db_stale` false after a db build, true after touching a record file with a later mtime (`os.utime`).
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `coverage.py`.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** `agent/literature/gap/coverage.py tests/agent/literature/test_lit_gap_coverage.py` with message `feat(literature): gap analysis coverage, blind spots and stale-db warning`.

---

### Task 7: Report (JSON and Markdown)

**Files:**
- Create: `agent/literature/gap/report.py`
- Modify: `.gitignore` (add `ai-sandbox/research/literature_gap/` next to the `literature_db/` line)
- Test: `tests/agent/literature/test_lit_gap_report.py`

**Interfaces:**
- Produces:
  - `SCHEMA_VERSION = 1`; `gap_dir(report_root, run_id: str) -> Path` (validates `run_id` with the same pattern as `cluster.topic_dir`, raising `ValueError`).
  - `build_report(question: str, constraints: list[Constraint], vocabs: dict, result: GapResult, cov: dict, corpus: Corpus, *, unmapped: list[str] = (), include_quotes: bool = False) -> dict` with keys `schema_version, question, unmapped_phrases, constraints (phrase, facet, value, label, level, resolved_by), verdict, rule, counts, caveat, coverage, evidence (per paper: id, kind, labels, title, year, facts with tier, results with claim and direction; quote only if include_quotes), partial, different_method, external: None`.
  - `render_markdown(report: dict) -> str` deterministic, sections in spec 4.7 order; stale-db warning first when `coverage.db.stale`; `unmapped_phrases` printed at the top.
  - `write_report(report: dict, run_dir: Path) -> tuple[Path, Path]` writes `report.json` (sorted keys off, `ensure_ascii=False`, LF) and `report.md` atomically (temp file then `os.replace`).
- Consumes: Tasks 1, 5, 6.
- `caveat` text (fixed): `Facets are per paper: a direct hit means the paper has all the facts, not that it links them; check each paper's results.`

- [ ] **Step 1: Write the failing tests**:
  - `test_report_json_has_schema_version_and_null_external`.
  - `test_markdown_contains_verdict_rule_caveat_and_completeness_line`.
  - `test_quotes_absent_by_default_and_present_with_flag` (use placeholder `quote a1`).
  - `test_stale_db_warning_leads_the_markdown`.
  - `test_unmapped_phrases_are_printed_first`.
  - `test_rendering_is_deterministic`: render twice, equal.
  - `test_write_report_creates_both_files_and_gap_dir_rejects_bad_run_ids` (`../x`, uppercase).
  - `test_gitignore_lists_literature_gap`: read the repo-root `.gitignore` and assert the line exists.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `report.py` and the `.gitignore` line.
- [ ] **Step 4: Run to verify pass.**
- [ ] **Step 5: Commit** `agent/literature/gap/report.py tests/agent/literature/test_lit_gap_report.py .gitignore` with message `feat(literature): gap analysis report rendering`.

---

### Task 8: `gap run` command

**Files:**
- Modify: `agent/literature/cli.py` (add `cmd_gap`, a `gap` subparser, dispatch entry; import `from .gap import ...` lazily inside `cmd_gap` to keep startup unchanged)
- Test: `tests/agent/literature/test_lit_gap_cli.py`

**Interfaces:**
- Produces: `gap run --run-id ID [--where facet=value ...] [--pick facet=term_id ...] [--quotes] [--report-root PATH]`. `--report-root` default `<index-root>/literature_gap`. Exit codes: 0 report written; 2 stopped (unresolved constraints, no db, bad input).
- Consumes: Tasks 1 to 7; `cluster.parse_constraint` for `--where`/`--pick` parsing (a pick is `facet=term_id`); `litdb.db_path`; the existing `_target(args)`.
- Flow: no db → print `gap: no database yet; run \`db build\` first`, exit 2. Constraints from `--where` (each resolved with the matching `--pick`, if any), or, when none given, from `<run-dir>/constraints.json` (Task 9; each item resolved with `pick=value`, `resolved_by="card"`, and its `unmapped` list passed to the report). Any unresolved → write `candidates.json` in the run dir (per constraint: phrase, facet, message, candidates as dicts), print each with a `--pick facet=<term_id>` hint, exit 2, no report. Otherwise classify, coverage, build, write, print `verdict: <name>`, counts and both paths. Open the db read-only and close it in `finally`.

- [ ] **Step 1: Write the failing tests** (build a real db with `synth_helpers.build` + `db.build`; run `main([...])` with `contextlib.redirect_stdout`):
  - `test_run_writes_report_and_prints_verdict`: `--where intervention=cash transfer --where countries=SO` → exit 0, files exist, stdout has `verdict: tried_directly`.
  - `test_ambiguous_phrase_stops_with_candidates_json_and_exit_2`; then re-run with `--pick` completes (exit 0) and the report records `resolved_by` `user`.
  - `test_no_database_exits_2`.
  - `test_unknown_facet_in_where_exits_2_without_traceback`.
  - `test_report_root_flag_redirects_output`.
  - `test_existing_db_query_and_cluster_commands_unchanged`: run `test_lit_db.py` and `test_lit_cluster.py` as part of the verification step.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `cmd_gap` (action `run`; `question` is added in Task 9) and the parser entry.
- [ ] **Step 4: Run to verify pass**: `python -m pytest tests/agent/literature/test_lit_gap_cli.py tests/agent/literature/test_lit_db.py tests/agent/literature/test_lit_cluster.py -v` → PASS.
- [ ] **Step 5: Commit** `agent/literature/cli.py tests/agent/literature/test_lit_gap_cli.py` with message `feat(literature): gap run command`.

---

### Task 9: Free-text card (optional front door)

**Files:**
- Create: `agent/literature/gap/card.py`
- Modify: `agent/literature/cli.py` (`gap question TEXT --run-id ID`; register the module in `cmd_submit`'s stage map)
- Test: `tests/agent/literature/test_lit_gap_card.py`

**Interfaces:**
- Produces: `STAGE = "gap"`; `make_tasks(target: Target, question: str, run_id: str, report_root: str, corpus: Corpus, subregions) -> tuple[list[Task], dict]`; `validate_result(entry: dict, result, target: Target) -> list[str]`; `apply_result(target, entry, result, provenance) -> str | None` writing `<report_root>/<run_id>/constraints.json` (`{"question", "constraints": [{facet, value, phrase}], "unmapped": [...]}`).
- Consumes: Task 3 (`resolve.shortlist`), `stage._vocab_listing`, `core.agent_tasks.tasks.Task`, the pattern in `contribute.py`.
- Card: one `Task(id=f"gap-{run_id}", stage=STAGE, subject={"run_id", "question", "report_root"}, instructions=..., context=<per-facet lexical shortlist plus the vocabulary listing>)`; `passages` stays empty (the dataclass allows it). Expected answer YAML: `constraints: [{facet, term_id, phrase}]` (for `countries`, `term_id` is an ISO code) and `unmapped: [phrase, ...]`. Validation bounces: not a mapping; no constraints; facet not in `cluster.FACETS`; a `term_id` not in that facet's vocabulary; an invalid country code; a missing `phrase`; `unmapped` not a list of strings. The run proceeds with mapped constraints only; no quotes needed.
- CLI: `gap question` writes the card with `collect_run(card.STAGE, tasks, _work_root(args), gap_dir(report_root, run_id), run_id=run_id, repo_label="gap report folder")` and prints how to relay it (`bootstrap` text is reused). `submit RUN_ID` then applies it; the user runs `gap run --run-id ID` with no `--where`.

- [ ] **Step 1: Write the failing tests**:
  - `test_card_context_includes_a_shortlist_for_the_question_words`.
  - `test_valid_answer_writes_constraints_json_and_gap_run_uses_it`: end to end through `main(["gap","question",...])`, fill the card (`lit_helpers.fill_card`), `main(["submit", run])`, `main(["gap","run",...])`; report shows `resolved_by` `card` and the printed unmapped phrases appear in `report.md`.
  - Bounce tests: unknown term id, term from the wrong facet, invalid country code, empty constraint list, missing phrase.
  - `test_unmapped_phrases_do_not_stop_the_run`.
  - `test_question_with_no_database_still_writes_a_card` (the card needs the vocabularies and corpus only for the shortlist; with no db it prints a notice and builds an empty shortlist).
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `card.py` and the CLI additions.
- [ ] **Step 4: Run to verify pass**: `python -m pytest tests/agent/literature/test_lit_gap_card.py tests/agent/literature/test_lit_gap_cli.py -v`.
- [ ] **Step 5: Commit** `agent/literature/gap/card.py agent/literature/cli.py tests/agent/literature/test_lit_gap_card.py` with message `feat(literature): optional free-text constraint card for gap analysis`.

---

### Task 10: Documentation, full suite and smoke check

**Files:**
- Modify: `agent/literature/README.md` (command lines for `gap run` / `gap question`, a "Gap analysis (stage 5, slice 1)" section: verdicts, adjacency rules, blind spots, report location, no-network note)
- Create: `docs/status/literature/2026-10-29-stage5-gap-analysis-slice1.md` (what shipped, deviations a to d above, smoke-run counts, open items: slice 2)
- Test: whole suite

- [ ] **Step 1: Run the literature tests**: `python -m pytest tests/agent/literature -q` → all pass, including untouched `test_lit_db.py`, `test_lit_cluster.py`.
- [ ] **Step 2: Run the full suite**: `python tools/run_tests_chunked.py` → no new failures (compare with `main`'s result if anything fails).
- [ ] **Step 3: Read `docs/WORKTREE_DATA_AND_RETIRE.md`** before the smoke run, then run one question against the real db without writing into the main checkout: `python -m agent.literature --index-root C:\Users\theaa\ai-sandbox-master\ai-sandbox\research --vocab-dir C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\resources\3ie\vocab gap run --run-id smoke1 --where intervention="cash transfers" --where countries=SO --report-root <scratchpad>/gap`. It is read-only on the db and records. If a phrase stops, `--pick` from the printed candidates. Compare the direct count with `db query --where ... --where ...` for the same resolved terms; record any difference (spec 4.3).
- [ ] **Step 4: Write the status doc** with counts only (no quotes, no titles of real papers beyond counts) and the smoke-run comparison.
- [ ] **Step 5: Update the README** and commit `agent/literature/README.md docs/status/literature/2026-10-29-stage5-gap-analysis-slice1.md` with message `docs(literature): gap analysis slice 1 readme and status`.
- [ ] **Step 6: Hand to the owner**: run `land_branch check --full` and ask the owner to approve a specific change ID; do not merge or push to `main`. Retire the worktree from outside it afterwards.

---

## Self-review

- **Spec coverage:** 4.1 entry points (Tasks 8, 9; `gap submit` replaced by existing `submit`, deviation b); 4.2 resolution and country names (Tasks 2, 3); 4.3 direct and id matching (Task 1, smoke comparison in Task 10); 4.4 adjacency, partial, different method (Tasks 4, 5); 4.5 coverage, blind spots, stale db (Task 6); 4.6 verdicts (Task 5); 4.7 report and quotes opt-in, gitignore (Task 7); 4.8 card (Task 9); section 5 tests (every task, invented data); section 6 guardrails (Global Constraints, no Artifact, no network); section 8 slice 2 is out of scope here.
- **Type consistency:** `Constraint`, `Fact`, `Corpus`, `GapResult`, `Sidecar`, `Resolution`, `Widening` are defined once in the task that produces them and used with those names in later tasks. `Constraint.value` is a resolved term id or upper-case country code everywhere.
- **Proportion:** bodies are left to the implementer; tasks carry signatures, rules and the tests that pin them.
