# reprokit core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `reprokit`, a standalone repo holding the framework's schemas, validators, a small CLI, and a copier template that generates a kind-agnostic research repo.

**Architecture:** One Python package (`src/reprokit`) of small single-purpose modules. Each framework file (charter, descriptor, config, compute profile, agent profile, harmonization record, manifest) has a JSON Schema in `src/reprokit/schemas/`, a shared `validate_document`, and, where rules go beyond schema, a rule module. Every check returns `list[Problem]` that names file, field and expected value, so humans and agents get the same readable errors. A copier template in `template/` generates a repo whose CI runs `reprokit validate`.

**Tech Stack:** Python >=3.11, uv (lockfile), pytest, ruff, jsonschema, PyYAML, copier, GitHub Actions.

**Spec:** `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-reproducible-research-framework-design.md` (sections 4, 5.2, 7). This is plan 1 of 3: plan 2 is the Project 02 pilot (spec phases 5-7, 13), plan 3 is communication, derivative rules and the future-kind check (phases 14-16). Phases 0 (gitlinks), 1 (standards verification) and 12 (taxonomy hooks) are not code and are out of scope here.

## Global Constraints

- The repo is standalone and lives **outside the monorepo** at `C:\Users\theaa\reprokit`; it must clone, install and pass tests with no monorepo present.
- Python `>=3.11`; dependencies locked with uv (`uv.lock` committed); CI builds with `uv sync --locked`.
- No GPU or large machine assumed; the test suite runs in under 30 seconds on a laptop.
- No secrets, credentials, raw data or copyrighted material in the repo; fixtures are synthetic.
- Spend rule: warn and require go-ahead for any estimated cost **over $1** (exactly $1.00 does not trigger).
- Confidentiality classes: `public`, `private_until_release`, `confidential`. Verification states: `proposed`, `source-verified`, `fixture-tested`, `run on acquired data`, `independently reproduced`.
- Every schema document carries `schema_version` (SemVer string, initial `"0.1.0"`).
- Code license MIT (**plan author's call**, owner may change before first release). Package name `reprokit` and copier (not cookiecutter) are also plan-author calls.
- Stage explicit paths only; never `git add -A` / `git add .`. Creating the GitHub remote or pushing needs the owner's go-ahead and is not part of this plan.
- Concise modules: if a module passes ~150 lines, split it by responsibility.

## Review Focus

1. A typo'd key in a document (`confidentialty:`) must fail naming the key, not pass silently (schemas use `additionalProperties: false`).
2. Windows-authored files (CRLF line endings, UTF-8 BOM) must validate exactly like LF files.
3. A `confidential` charter that declares a `public`-audience deliverable must fail unless that deliverable sets `requires_redaction: true`.
4. Provider names differing only by case or whitespace (`"ACLED "` vs `"acled"`) are not a structural change; a different provider is, and blocks without a harmonization record.
5. Spend exactly at the warn threshold is `ok`; just above is `confirm`; above the ceiling is `refuse`.
6. Invalid YAML syntax, an empty file, and a missing file each produce one readable `Problem`, not a traceback.

## File Structure

```
reprokit/
  pyproject.toml, uv.lock, README.md, AGENTS.md, LICENSE, .gitignore
  .github/workflows/ci.yml
  src/reprokit/
    __init__.py            version only
    problems.py            Problem dataclass
    loader.py              YAML loading with readable errors
    validate.py            validate_document(path, schema_name)
    schemas/*.json         one schema per document type
    charter_rules.py       cross-field charter rules
    harmonization.py       structural-change detection and gate
    manifest.py            hashing and run manifest
    profiles.py            backend choice and spend check
    cli.py                 `reprokit validate`, `reprokit manifest`
  template/                copier template (kind-agnostic core + study kind)
  tests/                   one test module per source module, plus test_template.py
```

### Task 1: Repo bootstrap and Problem type

**Files:**
- Create: `pyproject.toml`, `README.md`, `AGENTS.md`, `LICENSE`, `.gitignore`, `.github/workflows/ci.yml`, `src/reprokit/__init__.py`, `src/reprokit/problems.py`, `tests/test_problems.py`

**Interfaces:**
- Produces: `reprokit.problems.Problem(path: str, location: str, message: str)` frozen dataclass with `__str__` returning `"{path}: {location}: {message}"`.

- [ ] **Step 1:** In `C:\Users\theaa\reprokit` run `git init -b main`, then write `pyproject.toml` (hatchling build, `requires-python = ">=3.11"`, dependencies `jsonschema`, `pyyaml`; dev group `pytest`, `ruff`, `copier`; script `reprokit = "reprokit.cli:main"`). Run `uv sync` to create `uv.lock`.
- [ ] **Step 2: Write the failing test** `test_problem_str_names_file_field_and_message`: `str(Problem("a.yaml", "deliverables[0].audience", "required"))` equals `"a.yaml: deliverables[0].audience: required"`.
- [ ] **Step 3:** Run `uv run pytest tests/test_problems.py -v`; expect FAIL (module missing).
- [ ] **Step 4:** Implement `Problem` as above.
- [ ] **Step 5:** Write `AGENTS.md` (commands: `uv sync --locked`, `uv run pytest`, `uv run ruff check`; boundaries: schemas are versioned, change them only with a version bump and a test), `README.md` (purpose, install, `reprokit validate`), `LICENSE` (MIT, owner name from `git config user.name`), `.gitignore` (`.venv/`, `__pycache__/`, `.pytest_cache/`, `dist/`).
- [ ] **Step 6:** Write `.github/workflows/ci.yml`: on push/PR, `astral-sh/setup-uv`, `uv sync --locked`, `uv run ruff check`, `uv run pytest`.
- [ ] **Step 7:** Run `uv run pytest -v` and `uv run ruff check`; expect PASS.
- [ ] **Step 8: Commit** with explicit paths: `git add pyproject.toml uv.lock README.md AGENTS.md LICENSE .gitignore .github src tests && git commit -m "chore: bootstrap reprokit"`.

### Task 2: Loader and schema validation core

**Files:**
- Create: `src/reprokit/loader.py`, `src/reprokit/validate.py`, `src/reprokit/schemas/charter.json`, `tests/test_loader.py`, `tests/test_validate.py`, `tests/fixtures/charter_valid.yaml`

**Interfaces:**
- Consumes: `Problem`.
- Produces: `load_yaml(path: Path) -> tuple[dict | None, list[Problem]]`; `validate_document(path: Path, schema_name: str) -> list[Problem]` (`schema_name` is the schema file stem, e.g. `"charter"`).

- [ ] **Step 1: Write failing tests** in `test_loader.py`: `test_missing_file_gives_one_problem` (one Problem, message contains "not found"); `test_empty_file_gives_one_problem` (message contains "empty"); `test_invalid_yaml_reports_line` (message contains "line"); `test_crlf_and_bom_file_loads` (file written with `\r\n` and a UTF-8 BOM loads to the same dict as the LF version).
- [ ] **Step 2:** In `test_validate.py`: `test_valid_charter_has_no_problems`; `test_unknown_key_names_the_key` (add `confidentialty: public`; one Problem whose message contains `confidentialty`); `test_missing_required_field_names_location` (drop `purpose`; Problem location is `purpose` or empty-root and message contains "purpose"); `test_bad_enum_lists_allowed_values` (`confidentiality: secret`; message contains `private_until_release`).
- [ ] **Step 3:** Run `uv run pytest tests/test_loader.py tests/test_validate.py -v`; expect FAIL.
- [ ] **Step 4:** Implement `load_yaml` (read with `utf-8-sig`, `yaml.safe_load`, convert `YAMLError` marks to line numbers). Implement `validate_document` (load schema from `reprokit.schemas` via `importlib.resources`, use `jsonschema.Draft202012Validator`, map each error to a `Problem` with a readable location such as `deliverables[0].audience`).
- [ ] **Step 5:** Write `schemas/charter.json`: required `schema_version`, `name`, `kind` (string, pattern `^[a-z][a-z0-9_-]*$` so new kinds need no core change), `purpose` (enum `academic_publication`, `dissertation`, `consulting`, `open_source_tool`, `side_project`), `confidentiality` (enum per Global Constraints), `audiences` (array of `{name, needs, technical_level` enum `non_technical|practitioner|expert`, `channel}`), `publication` (`{venues: [string], preregistration: string}`), `deliverables` (array of `{id, audience, format, build, requires_redaction?: bool}`), `taxonomy` (`{tags: [string]}`), `sources` (array of string), `siblings` (array of `{name, url, tag}`). `additionalProperties: false` at every level.
- [ ] **Step 6:** Run the tests; expect PASS.
- [ ] **Step 7: Commit** `src/reprokit/loader.py src/reprokit/validate.py src/reprokit/schemas/charter.json tests` with message `feat: yaml loader and charter schema validation`.

### Task 3: Charter cross-field rules

**Files:**
- Create: `src/reprokit/charter_rules.py`, `tests/test_charter_rules.py`

**Interfaces:**
- Consumes: `Problem`.
- Produces: `check_charter_consistency(doc: dict, path: str) -> list[Problem]`. Rules: (a) a `confidential` charter whose deliverable targets an audience with `channel: "public"` needs that deliverable to set `requires_redaction: true`; (b) every deliverable `audience` names an entry in `audiences`; (c) `academic_publication`/`dissertation` purpose requires at least one `publication.venues` entry or `preregistration` set.

- [ ] **Step 1: Write failing tests:** `test_confidential_with_public_deliverable_fails_without_redaction`; `test_redaction_flag_clears_it`; `test_unknown_deliverable_audience_names_it`; `test_academic_without_venue_or_preregistration_fails`; `test_side_project_needs_no_venue`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement `check_charter_consistency`, treating an audience as public when its `channel` is `"public"`.
- [ ] **Step 4:** Run; expect PASS. (The CLI in Task 8 calls this after schema validation; `validate_document` itself stays schema-only.)
- [ ] **Step 5: Commit** `src/reprokit/charter_rules.py tests/test_charter_rules.py`.

### Task 4: Data descriptor and run-config schemas

**Files:**
- Create: `src/reprokit/schemas/descriptor.json`, `src/reprokit/schemas/config.json`, `tests/test_descriptor_config.py`, `tests/fixtures/descriptor_valid.yaml`, `tests/fixtures/config_valid.yaml`

**Interfaces:**
- Consumes: `validate_document`.
- Produces: schema names `"descriptor"` and `"config"`.

- [ ] **Step 1: Write failing tests:** `test_valid_descriptor_passes`; `test_descriptor_requires_find_in_other_geography` (the field the spec requires so a user knows what to look for elsewhere); `test_descriptor_variables_need_meaning_and_unit`; `test_valid_config_passes`; `test_config_unknown_parameter_key_fails`; `test_config_source_needs_role_and_provider`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Write `descriptor.json`: required `schema_version`, `role`, `provider`, `title`, `query`, `coverage_space`, `coverage_time`, `variables` (array of `{name, meaning, unit}`), `access_class` (enum `open`, `account_required`, `request_required`, `unverified`), `reuse_terms`, `verification_status` (enum of the five states), `find_in_other_geography`. Write `config.json`: required `schema_version`, `geography`, `period` (`{start, end}` ISO dates), `sources` (object keyed by role, each `{provider, dataset}`), `parameters` (free-form object, since parameters vary by study).
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5: Commit** schemas, tests and fixtures.

### Task 5: Harmonization gate

**Files:**
- Create: `src/reprokit/schemas/harmonization.json`, `src/reprokit/harmonization.py`, `tests/test_harmonization.py`

**Interfaces:**
- Consumes: `Problem`, `validate_document`.
- Produces: `structural_changes(baseline: dict, current: dict) -> list[str]` (roles whose normalized provider differs; normalization = `strip().casefold()`); `check_gate(baseline: dict, current: dict, records_dir: Path) -> list[Problem]` (one Problem per changed role lacking `records_dir/<role>.yaml` that validates against `harmonization`).

- [ ] **Step 1: Write failing tests:** `test_case_and_whitespace_difference_is_not_structural` (`"ACLED "` vs `"acled"` returns `[]`); `test_different_provider_is_structural` (`"UNHCR/NRC"` to `"IOM"` returns `["displacement"]`); `test_gate_blocks_without_record` (Problem message contains the role and the expected record path); `test_gate_passes_with_valid_record`; `test_gate_rejects_record_missing_rationale`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Write `harmonization.json` (required `schema_version`, `role`, `from_source`, `to_source`, `differences`, `decision`, `rationale`, `affected_outputs` array, `approved_by`, `date`). Implement both functions; `baseline` and `current` are `config` documents' `sources` mappings.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5: Commit.**

### Task 6: Run manifest

**Files:**
- Create: `src/reprokit/schemas/manifest.json`, `src/reprokit/manifest.py`, `tests/test_manifest.py`

**Interfaces:**
- Consumes: `validate_document`.
- Produces: `hash_file(path: Path) -> str` (SHA-256 hex, streamed in 1 MiB blocks); `build_manifest(config: dict, inputs: dict[str, Path], code_version: str, resolved_packages: dict[str, str]) -> dict`; `write_manifest(manifest: dict, out: Path) -> None` (stable key order, trailing newline). `inputs` is keyed by role.

- [ ] **Step 1: Write failing tests:** `test_hash_file_matches_hashlib` (known bytes); `test_hash_of_empty_file_is_sha256_of_empty` (`e3b0c442...b855`); `test_build_manifest_records_role_hash_and_params`; `test_missing_input_raises_filenotfounderror_naming_role`; `test_written_manifest_validates_against_schema`; `test_two_writes_of_same_manifest_are_byte_identical`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement as signatures state; manifest keys: `schema_version`, `code_version`, `parameters`, `inputs` (role to `{path, sha256}`), `packages`, `created_utc` (injectable through an optional `now` argument for the determinism test). Write `manifest.json`.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5: Commit.**

### Task 7: Compute and agent profiles

**Files:**
- Create: `src/reprokit/schemas/compute.json`, `src/reprokit/schemas/agents.json`, `src/reprokit/profiles.py`, `tests/test_profiles.py`

**Interfaces:**
- Consumes: none.
- Produces: `StepNeeds(ram_gb: float, gpu: bool)` frozen dataclass; `choose_backend(profile: dict, needs: StepNeeds) -> str | None` (walks `profile["preference_order"]`; `"local"` qualifies only if `profile["local"]["ram_gb"] >= needs.ram_gb` and not `needs.gpu` unless `local.gpu` is true; any other named backend qualifies; `None` when nothing does); `check_spend(estimated_usd: float, agents: dict) -> Literal["ok", "confirm", "refuse"]`.

- [ ] **Step 1: Write failing tests:** `test_local_chosen_when_it_fits`; `test_falls_through_to_next_backend_when_ram_too_small`; `test_gpu_need_skips_local_without_gpu`; `test_none_when_no_backend_qualifies`; `test_spend_at_warn_threshold_is_ok` (1.00 with `warn_above_usd: 1.0`); `test_spend_just_over_threshold_confirms` (1.01); `test_spend_over_ceiling_refuses`; `test_schemas_accept_minimal_valid_profiles`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Write `compute.json` (required `schema_version`, `local` `{ram_gb, cores, gpu}`, `preference_order` array of names, `backends` array of `{name, kind, access_note, cost_note}` with `kind` an open string such as `earth_engine`, `cluster`, `cloud_vm`) and `agents.json` (required `schema_version`, `subscriptions` array of `{provider, plan}` (may be empty), `ai_preference` enum `local|subscription|api`, `api_offload` `{allowed, providers, warn_above_usd, ceiling_usd}`). Implement `profiles.py`.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5: Commit.**

### Task 8: CLI

**Files:**
- Create: `src/reprokit/cli.py`, `tests/test_cli.py`, `tests/fixtures/repo_valid/` (a minimal generated-style repo: `project.yaml`, `compute.yaml`, `agents.yaml`, `config.yaml`, `data/descriptors/prices.yaml`)

**Interfaces:**
- Consumes: `validate_document`, `check_charter_consistency`, `build_manifest`, `write_manifest`.
- Produces: `main(argv: list[str] | None = None) -> int`. `reprokit validate [repo_dir=.]` validates each known file that exists (`project.yaml`→charter plus consistency rules, `compute.yaml`, `agents.yaml`, `config.yaml`, every `data/descriptors/*.yaml`), prints one `Problem` per line, returns 1 if any, else 0. `reprokit manifest --config config.yaml --out outputs/manifest.json` builds and writes a manifest from the config's input paths.

- [ ] **Step 1: Write failing tests** using `capsys` and `main([...])`: `test_validate_clean_repo_returns_0`; `test_validate_reports_every_problem_and_returns_1` (two broken files, both named in output); `test_validate_skips_absent_optional_files`; `test_validate_checks_every_descriptor`; `test_manifest_command_writes_valid_file`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement with `argparse`; no business logic in `cli.py`, only wiring.
- [ ] **Step 4:** Run `uv run pytest -q`; expect all PASS and under 30 seconds.
- [ ] **Step 5: Commit.**

### Task 9: Copier template (core + study kind)

**Files:**
- Create: `template/copier.yml`, `template/project.yaml.jinja`, `template/AGENTS.md.jinja`, `template/README.md.jinja`, `template/CITATION.cff.jinja`, `template/LICENSE.jinja`, `template/pyproject.toml.jinja`, `template/compute.yaml`, `template/agents.yaml`, `template/protocol.md`, `template/.gitignore`, `template/.github/workflows/ci.yml`, `template/comms/.gitkeep`, `template/data/raw/.gitkeep`, `template/data/derived/.gitkeep`, `template/data/descriptors/.gitkeep`, `template/outputs/.gitkeep`, `tests/test_template.py`

**Interfaces:**
- Consumes: `reprokit validate`.
- Produces: a generated repo that passes `reprokit validate` and whose `.gitignore` excludes raw data, derived data, outputs and credentials.

- [ ] **Step 1: Write failing tests** with `copier.run_copy("template", dst, data={...}, defaults=True, unsafe=False)`: `test_generated_repo_passes_reprokit_validate`; `test_generated_gitignore_excludes_raw_derived_outputs_and_env` (assert `/data/raw/*`, `/data/derived/*`, `/outputs/*`, `/.env` lines); `test_generated_agents_md_has_derivative_rules_section` (heading "Derivative rules" present); `test_generated_ci_runs_validate_and_secret_scan`; `test_confidentiality_question_is_required` (no default; `defaults=True` with it unset raises).
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Write the template. `copier.yml` questions: `project_name`, `kind` (default `study`), `purpose`, `confidentiality` (no default), `author`. The generated `AGENTS.md` carries: commands, forbidden zones (raw data, credentials, locked specs), the "adapt to a new country" runbook stub, and the **Derivative rules** section (may reuse public-class and aggregated results; must exclude restricted/confidential/unreleased/copyrighted material; must link back to source version; stop for owner review before publishing). `compute.yaml` defaults: `local` 8 GB, no GPU, `preference_order: [local]`. `agents.yaml` defaults: no subscriptions, `ai_preference: local`, `warn_above_usd: 1.0`. Generated CI: `uv sync --locked`, `uv run reprokit validate`, and a gitleaks step.
- [ ] **Step 4:** Run; expect PASS.
- [ ] **Step 5: Commit** `template tests/test_template.py`.

### Task 10: Clean-room check and release prep

**Files:**
- Modify: `README.md`, `AGENTS.md`
- Create: `CHANGELOG.md`, `CITATION.cff`

- [ ] **Step 1:** Clone the repo to a scratch directory outside the project (`git clone C:\Users\theaa\reprokit <scratch>\reprokit-clean`), run `uv sync --locked` and `uv run pytest -q` there; expect PASS with no network access to the monorepo.
- [ ] **Step 2:** Generate a repo from the template into a scratch directory, `cd` in, run `uv run reprokit validate`; expect exit code 0.
- [ ] **Step 3:** Write `CHANGELOG.md` (Keep a Changelog, `0.1.0`), `CITATION.cff`, and a README section documenting each schema file, the `Problem` output format, and "install the template" with `copier copy`.
- [ ] **Step 4: Commit** with message `docs: changelog, citation and schema docs`. Tag `v0.1.0` only after the owner approves.

## Self-review notes

- Spec coverage: charter and its consistency rules (T2, T3), descriptor and config (T4), harmonization two-tier gate (T5), manifest (T6), compute and agent profiles with the $1 rule (T7), validators/CLI (T8), copier template with `AGENTS.md` derivative rules, locked environment, CI, secret scanning, gitignore (T9), standalone cloneability and clean-room run (T10). Deliberately deferred to later plans: role adapters and step graph, `reproduce` build targets, comms generator, derivative test, future-kind check.
- Types are consistent: `Problem` fields, `validate_document(path, schema_name)`, and the `sources` mapping shape are used identically in T2, T5, T6, T8.
