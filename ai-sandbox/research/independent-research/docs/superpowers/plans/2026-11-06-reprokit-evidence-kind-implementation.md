# Reprokit `evidence` kind Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `evidence` project kind to reprokit (v0.4.0): typed-source manifest, extraction cache, claim checking, add/remove sensitivity runs, and a Copier template variant, with study output unchanged.

**Architecture:** New kind-specific modules (`evidence_*.py`, each near 150 lines or fewer) hang off the existing validator and CLI through one dispatch point keyed on `project.yaml` `kind`. The shared core (charter, compute, agents, CI) is untouched. The template stays a single `template/` with `kind` conditionals.

**Tech Stack:** Python 3.11+, jsonschema, PyYAML, Copier, pytest, uv lockfile.

**Spec:** `docs/superpowers/specs/2026-11-06-reprokit-evidence-kind-design.md` (monorepo, `ai-sandbox/research/independent-research/`). Also read `2026-11-06-reprokit-evidence-kind-handoff.md` in `../plans/`.

**Repo and branch:** code goes in `ai-sandbox/research/independent-research/projects/reprokit` (separate git repo), branch `evidence-kind`. Do not tag, push, or release without owner approval. Run Python via `C:\Users\theaa\AppData\Roaming\Python\Python313\Scripts\uv.exe run pytest -q` (uv is not on PATH).

## Global Constraints

- Tests under 30 s total; modules near 150 lines or fewer (`cli.py` is already 186: put new commands in `evidence_cli.py`, do not grow `cli.py` beyond a registration call).
- No secrets; no PDFs, full text or transcriptions committed; no raw ACLED rows; stage explicit paths only.
- A study repo generated before and after the change is byte-identical.
- Charter stays at `0.2.0`; `0.1.0` and `0.2.0` files keep validating.
- Existing verification-states vocabulary is reused (`proposed`, `source-verified`, `fixture-tested`, `run on acquired data`, `independently reproduced`); see `_VERIFIED_STATES` in `src/reprokit/validate.py`.
- Errors are `Problem(path, location, message)` (`src/reprokit/problems.py`) with plain-language messages that say what to do.
- Abstracts are never stored. Fetch/transcribe adapters, OpenAlex search, Zotero sync and the `library` kind are out of scope.
- Do not generate repos into `research/independent-research/projects/`; tests and the end-to-end check use `tmp_path` / a scratch directory.

## Review Focus

Tests pinning each of these are in the task named in brackets.
1. Two manifest entries with the same `id` must be a problem, not silently merged. [Task 1]
2. `[@a; @b]` multi-citation markers and markers inside CRLF files must resolve. [Task 3]
3. A marker citing an `excluded` or `proposed` entry must be reported, with the entry id in the message. [Task 3]
4. `evidence-run --exclude nope` (unknown id) must fail with a clear message, not run on everything. [Task 5]
5. A PDF in a nested directory (`notes/deep/x.pdf`) or under a different case (`X.PDF`) must be rejected. [Task 6]

---

### Task 1: Evidence manifest schema and rules

**Files:**
- Create: `src/reprokit/schemas/evidence_manifest.json`, `src/reprokit/evidence_manifest.py`, `tests/test_evidence_manifest.py`, `tests/fixtures/evidence/manifest_ok.yaml`
- Modify: `src/reprokit/validate.py` (accept schema name `evidence_manifest`; no version dispatch needed beyond `0.1.0`)

**Interfaces:**
- Produces: `load_manifest(path: Path) -> tuple[dict | None, list[Problem]]` (schema + rules), `check_manifest_rules(doc: dict, path: str, confidentiality: str) -> list[Problem]`, constants `SOURCE_TYPES`, `ACCESS_CLASSES`, `SCREENING_STATUSES`.
- Consumes: `load_yaml`, `validate_document`, `Problem`.

Schema (spec section 4): top level `schema_version` (const `0.1.0`), `sources` (array). Entry required: `id` (pattern `^[a-z0-9][a-z0-9_-]*$`), `type` (article, report, dataset, webpage, project_package, other), `identifier` (`{scheme: doi|openalex|dataset_doi|url|file_hash, value}`), `title`, `access_class` (open, paywalled, restricted, confidential, unknown), `screening_status` (candidate, included, excluded), `verification_status` (the existing vocabulary). Optional: `also` (list of identifiers), `year`, `retrieved_on`, `screening_reason`, `content_hash`, `converter`, `snapshot` (`{url, date}`), `rights_note`, `extraction`, `descriptor`. No additional properties; no `abstract` property.

- [ ] **Step 1: Write failing tests** in `tests/test_evidence_manifest.py`: `test_fixture_manifest_is_valid`; `test_duplicate_id_is_a_problem` (Review Focus 1; message names the id); `test_abstract_field_is_rejected`; `test_webpage_without_snapshot_cannot_be_source_verified`; `test_dataset_requires_descriptor_link`; `test_project_package_rejected_in_public_repo` (parametrize `confidentiality`: public rejects unless `access_class` is `confidential`/`restricted` pointer-only, private_until_release/confidential accept); `test_empty_sources_list_is_valid` (minimal tier).
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_manifest.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the schema and `check_manifest_rules` as above in `evidence_manifest.py`; extend `validate_document` to load `evidence_manifest.json`.
- [ ] **Step 4: Run** the same tests. Expected: PASS. Then run the full suite: `uv run pytest -q` still PASS.
- [ ] **Step 5: Commit** (`git add` the five paths; message `feat: evidence manifest schema and rules`).

### Task 2: Charter `evidence:` block

**Files:**
- Modify: `src/reprokit/schemas/charter_0_2.json`, `src/reprokit/charter_rules.py`
- Test: `tests/test_charter_rules.py`

**Interfaces:**
- Produces: optional charter property `evidence: {manifest: str, inclusion_criteria: list[str], search_protocol: str, zotero_group: str}` (all optional inside, no additional properties). `check_charter_consistency` adds a problem when `evidence` is present and `kind != "evidence"`.

- [ ] **Step 1: Write failing tests**: `test_evidence_block_valid_for_evidence_kind`; `test_evidence_block_rejected_for_study_kind` (message tells the user to set `kind: evidence` or remove the block); `test_existing_0_1_and_0_2_charters_still_validate` (reuse existing fixtures).
- [ ] **Step 2: Run** `uv run pytest tests/test_charter_rules.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the schema property and rule. Do not bump `schema_version`.
- [ ] **Step 4: Run** full suite. Expected: PASS.
- [ ] **Step 5: Commit** the three paths (`feat: optional evidence block in charter 0.2.0`).

### Task 3: Claim checking

**Files:**
- Create: `src/reprokit/evidence_claims.py`, `tests/test_evidence_claims.py`

**Interfaces:**
- Consumes: manifest dict from Task 1.
- Produces: `check_claims(text: str, manifest: dict, path: str) -> list[Problem]`; `extract_markers(text: str) -> list[tuple[int, str]]` (line number, id).

Marker grammar: `[@id]` and `[@id1; @id2]`. Rules: unknown id; cited entry not `included`; cited entry `verification_status` not source-verified or later; `included` entries never cited are not a problem.

- [ ] **Step 1: Write failing tests**: `test_unknown_marker_reported_with_line`; `test_multi_citation_marker_resolves_both` and `test_crlf_text_resolves` (Review Focus 2); `test_excluded_and_proposed_entries_reported_with_id` (Review Focus 3); `test_text_without_markers_has_no_problems`.
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_claims.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** with one compiled regex; normalise line endings before scanning.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: check synthesis claims against the manifest`).

### Task 4: Extraction schema, records and staleness

**Files:**
- Create: `src/reprokit/evidence_extraction.py`, `src/reprokit/schemas/extraction_record.json`, `src/reprokit/schemas/extraction_schema.json`, `tests/test_evidence_extraction.py`, fixtures under `tests/fixtures/evidence/`

**Interfaces:**
- Produces: `load_extraction_schema(path: Path) -> tuple[dict | None, list[Problem]]`; `load_records(folder: Path, manifest: dict, schema: dict) -> tuple[dict[str, dict], list[Problem]]` (keyed by source id); `stale_records(records: dict, manifest: dict) -> list[str]` (ids where `source_content_hash` and the entry's `content_hash` are both set and differ).

Formats: `evidence/extraction_schema.yaml` = `{schema_version: 0.1.0, fields: {<name>: {type: string|number|boolean|list, aggregate: count|sum|none}}}`. Record `evidence/extractions/<id>.yaml` = `{source_id, extractor, prompt_version, source_content_hash, cost: {usd: number}, fields: {...}, locators: {<field>: str}}`; `fields` keys must exist in the schema; filename must equal `source_id`; no free-text field longer than 500 characters (guards against bulk quotation).

- [ ] **Step 1: Write failing tests**: `test_valid_record_loads`; `test_unknown_field_rejected`; `test_filename_must_match_source_id`; `test_overlong_text_rejected`; `test_stale_record_detected_when_hash_differs`; `test_included_source_without_record_is_a_problem` (excluded/candidate sources need none).
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_extraction.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** both schemas and functions.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: extraction schema, records and staleness`).

### Task 5: Aggregation and `evidence-run`

**Files:**
- Create: `src/reprokit/evidence_run.py`, `src/reprokit/evidence_cli.py`, `tests/test_evidence_run.py`
- Modify: `src/reprokit/cli.py` (register the subcommand only: one import and one `add_parser` call)

**Interfaces:**
- Consumes: Tasks 1 and 4.
- Produces: `aggregate(manifest: dict, records: dict, schema: dict, *, only: set[str] | None = None, exclude: set[str] = frozenset()) -> dict` returning `{"sources": [ids used], "fields": {name: value}, "cost_usd": float}` (`count` = number of used records with a non-empty value; `sum` = numeric total; `list` fields merge into a sorted unique list); `delta(full: dict, subset: dict) -> dict` (per-field difference plus ids removed); CLI `reprokit evidence-run [repo] [--only IDS] [--exclude IDS]` (comma-separated), which prints the aggregate (and the delta when a subset was requested) and writes `outputs/evidence_aggregate.yaml`. It never calls an AI service.

- [ ] **Step 1: Write failing tests**: `test_aggregate_counts_sums_and_merges_lists`; `test_exclude_removes_a_source_and_delta_shows_it`; `test_only_restricts_to_listed_ids`; `test_unknown_id_in_exclude_fails_with_clear_message` (Review Focus 4, exit code 1, no output file written); `test_adding_a_source_needs_only_its_record` (aggregate over a manifest with a new included source and one new record equals old aggregate plus that record); `test_cli_writes_output_file`.
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_run.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `aggregate` and `delta` as pure functions; the CLI function loads files and calls them.
- [ ] **Step 4: Run** the tests, then the full suite. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: evidence-run aggregation and sensitivity`).

### Task 6: `validate` dispatch by kind and stray-file guard

**Files:**
- Create: `src/reprokit/evidence_rules.py`, `tests/test_evidence_validate.py`
- Modify: `src/reprokit/cli.py` (in `_validate`, after the charter loads: call `validate_evidence(repo_dir, charter_doc)` when `charter_doc["kind"] == "evidence"`)

**Interfaces:**
- Consumes: Tasks 1 to 4.
- Produces: `validate_evidence(repo_dir: Path, charter: dict) -> list[Problem]`. It runs, in order: manifest schema and rules (path from `charter["evidence"]["manifest"]`, default `evidence/manifest.yaml`); `synthesis.md` claim check when the file exists; extraction schema, records and missing-record check when `evidence/extraction_schema.yaml` exists (screening tier); stale records as warnings, not problems; the stray-file guard. Stray-file guard: any file matching `*.pdf`, `*.epub`, `*.docx` (case-insensitive, any depth) outside `cache/`, or any file under `cache/` that git would not ignore, is a problem. The study validation path must not import or call any of this for other kinds.

- [ ] **Step 1: Write failing tests**: `test_minimal_evidence_repo_validates` (charter + empty manifest + synthesis only); `test_missing_manifest_reported`; `test_pdf_in_nested_directory_rejected` and `test_uppercase_pdf_rejected` (Review Focus 5); `test_cache_directory_must_be_gitignored`; `test_study_kind_repo_unaffected` (run `main(["validate", ...])` on an existing study fixture; same output as before).
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_validate.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `validate_evidence` and the dispatch call.
- [ ] **Step 4: Run** the full suite. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: validate dispatches on evidence kind`).

### Task 7: `verify-sources`

**Files:**
- Create: `src/reprokit/evidence_verify.py`, `tests/test_evidence_verify.py`
- Modify: `src/reprokit/evidence_cli.py` (add the subcommand)

**Interfaces:**
- Produces: `verify_sources(manifest: dict, resolve: Callable[[dict], bool]) -> list[Problem]` (one problem per `included` entry whose identifier does not resolve); `default_resolver(identifier: dict) -> bool` using stdlib `urllib` with a 10 s timeout against `https://doi.org/<doi>` and `https://api.openalex.org/works/<id>` (HEAD request; schemes `url`, `file_hash`, `dataset_doi` are skipped, not failed). CLI `reprokit verify-sources [repo]`. It makes no paid calls and reads no credentials.

- [ ] **Step 1: Write failing tests** (injected fake resolver, no network): `test_unresolvable_included_entry_reported`; `test_excluded_entries_not_checked`; `test_non_doi_schemes_skipped`; `test_cli_exits_nonzero_on_unresolved` (monkeypatch `default_resolver`).
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_verify.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests. Expected: PASS (no test touches the network).
- [ ] **Step 5: Commit** (`feat: verify-sources command`).

### Task 8: Template variant

**Files:**
- Modify: `template/copier.yml` (add `screening_pipeline` bool, default false, asked only when `kind == evidence`; `_exclude` list gated on `kind`), `template/project.yaml.jinja` (emit the `evidence:` block when `kind == evidence`), `template/README.md.jinja`, `template/AGENTS.md.jinja`, `template/quick_check.py.jinja`, `template/protocol.md.jinja`
- Create: `template/evidence/manifest.yaml.jinja`, `template/synthesis.md.jinja`, `template/evidence/extraction_schema.yaml.jinja`, `template/evidence/extractions/.gitkeep`
- Test: `tests/test_template.py` (extend), `tests/fixtures/study_baseline/` (generated tree snapshot, if not already present, taken BEFORE changing the template)

**Interfaces:**
- Produces: for `kind: evidence`: `project.yaml` with `evidence:`, `evidence/manifest.yaml` (empty `sources: []`), `synthesis.md`, a protocol focused on search/screen/extract, `.gitignore` entries `/cache/`; study-only paths (`data/descriptors`, `data/raw`, `data/derived`, `config`-related) excluded. With `screening_pipeline: true` also `evidence/extraction_schema.yaml`, `compute.yaml`, `agents.yaml`. The evidence `quick_check.py` writes a 3-entry fixture manifest and one extraction record to a temp dir, runs validate, claims, aggregate through the real functions, and reports through `verify_smoke_result`. Study output stays identical (the `kind` default is `study`).

- [ ] **Step 1: Before touching the template**, generate a study repo with the existing `generate()` helper (fixed answers) and commit a file-hash listing of it as `tests/fixtures/study_baseline.json` (path -> sha256).
- [ ] **Step 2: Write failing tests** in `tests/test_template.py`: `test_study_output_is_byte_identical_to_baseline`; `test_minimal_evidence_repo_passes_validate_and_quick_check` (`generate(tmp_path, kind="evidence")`, then `main(["validate", ...]) == 0` and `quick-check` exits 0); `test_screening_pipeline_adds_extraction_and_compute_files`; `test_evidence_repo_has_no_study_scaffolding` (no `data/descriptors`, no `config.yaml`); `test_evidence_gitignore_excludes_cache`.
- [ ] **Step 3: Run** `uv run pytest tests/test_template.py -q`. Expected: new tests FAIL, baseline test PASSES.
- [ ] **Step 4: Implement** the conditionals with `_exclude` and `{% if kind == 'evidence' %}`; keep study branches textually unchanged.
- [ ] **Step 5: Run** the full suite including the baseline test. Expected: PASS. Confirm total runtime under 30 s.
- [ ] **Step 6: Commit** (`feat: evidence template variant`).

### Task 9: Review migration

**Files:**
- Create: `src/reprokit/evidence_migrate.py`, `tests/test_evidence_migrate.py`, `tests/fixtures/evidence/literature_review_sample.md` (two papers, synthetic text, no copied abstracts)
- Modify: `src/reprokit/evidence_cli.py` (subcommand `migrate-review REVIEW.md [--out PATH]`)

**Interfaces:**
- Produces: `parse_review(text: str) -> list[dict]` reading the `### <a id="paper-N"></a>N. Title` blocks (`Authors`, `Publication Year`, `Journal / Venue`, `DOI / Link`); `review_to_manifest(text: str, retrieved_on: str) -> dict` giving each paper `type: article`, `identifier: {scheme: doi, value}` (DOI extracted from the `doi.org` URL; `openalex` or `url` scheme when no DOI), slug `id` from first author surname + year (with `-b`, `-c` suffix on collision), `access_class: unknown`, `screening_status: included`, `verification_status: proposed`. Abstracts and citation counts are dropped.

- [ ] **Step 1: Write failing tests**: `test_parse_two_papers`; `test_doi_extracted_from_link`; `test_collision_gets_suffix`; `test_abstract_not_in_output`; `test_output_validates_against_manifest_schema`.
- [ ] **Step 2: Run** `uv run pytest tests/test_evidence_migrate.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** (`feat: migrate literature_review.md to a manifest`).

### Task 10: Docs, version and end-to-end check

**Files:**
- Modify: `CHANGELOG.md`, `README.md`, `pyproject.toml` (version `0.4.0`), `src/reprokit/__init__.py` if it carries the version, `template/copier.yml` default `reprokit_requirement` only if it is meant to track the release (leave at `v0.3.2` until the tag exists; note this in the CHANGELOG)
- Create: `docs/evidence-kind.md` (how to use: tiers, manifest, `[@id]` markers, `evidence-run`, `verify-sources`, rights rules, Zotero optional)

- [ ] **Step 1:** Write the doc and CHANGELOG entry; README gets a short "Project kinds" note including the `copier copy` from a local clone reminder.
- [ ] **Step 2: End-to-end check in a scratch directory outside `projects/`:** generate an evidence repo from the local clone, run `migrate-review` on `01_evidence_map/literature_review.md` into it, then `validate`, `quick-check`, `evidence-run`. Expected: validate exits 0 (migrated entries are `proposed`, so no synthesis citations yet), quick-check passes.
- [ ] **Step 3:** Confirm CI on Linux and Windows in a scratch GitHub repo ONLY after owner approval (it requires a push to a new repo).
- [ ] **Step 4:** Run `uv run pytest -q` and `uv lock --check`. Expected: all pass, lockfile unchanged.
- [ ] **Step 5: Commit** (`docs: evidence kind guide and v0.4.0 changelog`). Do not tag or push; report to the owner for release approval.

---

## Execution notes
- Tasks 1 to 4 are independent of the template and can run in order or in parallel worktrees; Task 5 needs 1 and 4; Task 6 needs 1 to 4; Task 8 needs 6; Task 9 needs 1.
- Codex handles implementation under the routing convention; Claude reviews the finished branch for design fidelity and security (stray-file guard, credentials never logged).
- Cost: nothing in this plan calls a paid service.
