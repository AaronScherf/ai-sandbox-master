# compound-shocks-panel pilot Implementation Plan (Phase A: data exploration)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Project 02 pilot as a standalone study repo, `compound-shocks-panel`, that reproducibly ingests and fuses Somalia's data into a district-month panel, audits its quality, and shows the same code ports to Sudan. **Phase A only**: no modeling, causal inference, cross-country regressions or paper drafting; those are gated behind a review (see "Phase structure and review gate" and [the realignment note](../../../notes/Pilot%20Scope%20Realignment%20-%20Exploratory%20Review%20Gate.md)).

**Architecture:** A study repo generated from the reprokit template. Code under `src/compound_shocks/` is country-neutral; each country is an instance folder (`instances/<name>/`: config, raw data, descriptors, harmonization records). Per-role, per-provider adapters turn raw files into canonical tables; spatial functions assign events and rainfall to OCHA COD-AB Admin 2 districts; a fuse step builds a panel keyed by `(admin2_id, month)` whose columns are marked `core` or `extension`; `doit` runs the step graph behind one `reproduce` command; EDA figures and an audit memo summarize what the data support.

**Tech Stack:** Python >=3.11, uv, reprokit (installed from its git tag), pandas, geopandas, rasterio, shapely, matplotlib, doit, requests, pytest, ruff. (`statsmodels` is a Phase B dependency; Task 11 removes it from `pyproject.toml`, and Phase B re-adds it.)

**Spec:** `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-project-02-pilot-design.md` (sections 3 to 10; 4.1 and 7.1 are binding). Framework context: `.../specs/2026-10-31-reproducible-research-framework-design.md`. Builds on reprokit v0.1.0 (`https://github.com/AaronScherf/reprokit`, tag `v0.1.0`).

## Global Constraints

- Standalone repo at `C:\Users\theaa\compound-shocks-panel` (outside the monorepo), generated from the reprokit template (`kind: study`, `purpose: academic_publication`, `confidentiality: public`); MIT; Python `>=3.11`; `uv.lock` committed; CI uses `uv sync --locked`. The reprokit-side change (Task 1) is a separate repo and release.
- Layer 1 only: prices, rainfall, conflict, displacement, boundaries. No narrative/LLM layers, no cash-transfer data. **Phase A only: no regressions, price-basket decompositions, causal claims, hypothesis tests, cross-country comparisons, LaTeX papers or slides.** Exploratory data analysis and the audit memo are the only analysis.
- Inputs are located by role directory (`instances/<name>/data/raw/<role>/`), never by hard-coded filename. Cosmetic changes (renamed column or file) are logged; provider or definition changes require a harmonization record, enforced by `reprokit gate`.
- ACLED (Spec 7.1): never commit event-level rows or any subset; committed aggregates are totals only (events, fatalities) per district-month, no per-event-type cells, no coordinates or event IDs; every figure and map carries the caption `Source: ACLED (acleddata.com), accessed <date>`; credentials only from `ACLED_EMAIL` and `ACLED_PASSWORD` environment variables; raw rows are never sent to external AI services.
- Boundaries: OCHA COD-AB per country with geoBoundaries as fallback; record boundary vintage in the descriptor and manifest. Maps at district level or coarser.
- Tests run on synthetic seeded fixtures with no network and finish in under 60 seconds. Real-data tests are marked `real_data` and skipped when the raw files are absent.
- Month assignment: calendar month of the event date as `YYYY-MM`. Zero conflict events in a district-month is `0`; a missing price or unreported displacement is `NaN`, never `0`.
- Spend rule: warn and require go-ahead before any step estimated over $1 (none expected).
- Stage explicit paths only; never `git add -A` / `git add .`. Creating GitHub repos and pushing needs the owner's go-ahead (public-repo creation is blocked for agents; the owner runs it).

## Phase structure and review gate (owner decision 2026-10-31)

```
PHASE A (this plan): adapters, spatial joins, zonal stats, panel fusion, EDA + audit memo, Sudan portability
        |
   REVIEW GATE: (A) data audit  (B) literature gap analysis  (C) owner approves question and modeling plan
        |
PHASE B (separate plan, not started): modeling, decompositions, cross-country tests, paper
```

Phase A stops after Task 16. Nothing in Phase B starts until the gate clears. Deferred and preserved in git history (original
Tasks 11, 12, 15 in commit `cbeb9ce6`): `price_index` and `price_decomposition` baskets, the LaTeX `report/main.tex` build,
`compare.nested_f_test` and all cross-country regressions. Source of the realignment: [Pilot Scope Realignment](../../../notes/Pilot%20Scope%20Realignment%20-%20Exploratory%20Review%20Gate.md).

## Source facts checked 2026-10-31 (unauthenticated HTTP calls; files not yet downloaded or opened)

- **WFP prices:** HDX dataset `wfp-food-prices-for-somalia` (CC BY-IGO), coverage 1995-01 to 2026-08, updated monthly; resources "Somalia - Food Prices" (CSV) and "Somalia - Markets" (CSV). The global `wfp-food-prices` dataset on HDX is stale (ends 2021-08): do not use it. Columns, units, and market coverage are still unverified.
- **Boundaries:** HDX dataset `cod-ab-som` (CC BY-IGO), formats GDB, SHP, GeoJSON, XLSX; dataset dates 2025-01-08 to 2025-10-30. Boundary vintage ("valid on") is not yet read from the metadata.
- **Rainfall:** CHIRPS v2.0 monthly Africa GeoTIFFs, no login: `https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/chirps-v2.0.YYYY.MM.tif.gz` (about 4.4 MB each; 2021 and 2023 months present). The older `CHIRPS-2.0` path in the data-sources note returns 404 and must not be used. v3.0 also exists at `/products/CHIRPS/v3.0/`; decided by the owner: the plan uses v2.0 and records the version in the descriptor.
- **Displacement (problem):** the dataset ID in the data-sources note (`unhcr-somalia-prmn-displacement-and-return-events`) returns 404. The actual HDX dataset is `somalia-internally-displaced-persons-idps` (CC BY; CSV and XLSX), but its coverage is **2016-01 to 2023-08**. September to December 2023 are absent, so the 2021 to 2023 window cannot be fully covered from this dataset. Whether it has origin and destination districts and a reason field is unverified. A newer or by-request PRMN release (UNHCR Operational Data Portal or Microdata Library) is unchecked.
- **API access:** the HDX metadata API (`/api/3/action/package_show`) answers without a key or account. The fetch layer should use plain HTTP; no HDX credentials are needed. ACLED is the only source needing an account (OAuth with email and password).
- **FSNAU** market data (separate portal) has not been checked for an API.

## Review Focus

1. The real ACLED export starts with a UTF-8 BOM (`\ufeffevent_id_cnty`); the adapter must still find the first column.
2. A district-month with no events is `0`, a market-month with no price is `NaN`, and unreported displacement is `NaN`; the fused panel preserves all three distinctly.
3. An event whose coordinates fall exactly on a district boundary, or outside every polygon (offshore, low `geo_precision`), is assigned deterministically or logged as unassigned, never silently dropped or double-counted.
4. Events join to districts by point-in-polygon, never by ACLED's own `admin2` name; name-based joins (prices, displacement) go through an explicit crosswalk and report every unmatched name.
5. A second `reproduce` with unchanged inputs does no work and writes an identical panel; changing one input file's bytes reruns exactly the dependent steps.
6. A provider swap for any role stops the run before processing with a message naming the missing harmonization record.
7. Publishable aggregates contain no coordinates, event IDs, actor strings, or event-type columns.

## Execution routing (per `docs/AGENT_ROUTING.md`)

| Tasks | Owner | Notes |
| --- | --- | --- |
| 1 | Codex (Claude reviews) | reprokit v0.2.0 |
| 2 to 3 | Claude (architecture/spike), Codex for scaffold steps | Spike decides doit vs own runner |
| 4 to 12 | Codex in slices from this plan; Claude reviews each adapter and the fuse step | Escalate any schema change to Claude; Tasks 11 and 12 are EDA only |
| 13 | Codex | Mocked HTTP only |
| 14 | Owner downloads; Gemini operates documented runs; Claude judges findings | Real data; ACLED rows never go to Gemini or any external AI |
| 15 | Codex (code), Gemini (run), Claude (harmonization judgment) | No regressions |
| Gate | Owner, with Gemini (literature pipeline, large reads) and Claude (audit review) | After Task 16; no coding |
| 16 | Claude (review), owner (publish) | |

### Task 1: reprokit v0.2.0: instance discovery and gate command

**Repo:** `C:\Users\theaa\reprokit`. **Files:**
- Modify: `src/reprokit/cli.py`, `README.md`, `CHANGELOG.md`
- Test: `tests/test_cli.py`, `tests/fixtures/repo_instances/` (a study repo with `instances/a/` and `instances/b/`)

**Interfaces:**
- Produces: `reprokit validate` also checks, for every `instances/*/`: `config.yaml` (schema `config` + period rule), `data/descriptors/*.yaml`, `harmonization/*.yaml`; problems name the full path. New command `reprokit gate --baseline <config.yaml> --config <config.yaml> --records <dir>` prints `Problem` lines from `check_gate(baseline["sources"], config["sources"], records)` and exits 1 on any.

- [x] **Step 1: Write failing tests:** `test_validate_walks_every_instance` (a broken descriptor in `instances/b` is reported with its path, `instances/a` clean); `test_validate_instance_period_rule`; `test_gate_blocks_provider_swap_without_record` (message names the role and expected record path); `test_gate_passes_with_valid_record`; `test_gate_exit_0_when_providers_match_ignoring_case`. Run; expect FAIL.
- [x] **Step 2:** Implement in `cli.py` (extend `_validate`; add `_gate` using `harmonization.check_gate`). Run `uv run pytest -q`; expect PASS.
- [x] **Step 3:** Document in README and CHANGELOG (`0.2.0`), bump `pyproject.toml` version, commit, tag `v0.2.0`. Pushing is the owner's go-ahead.

### Task 2: Generate the study repo and migrate the intake scaffold

**Repo:** new `compound-shocks-panel`. **Files:**
- Create: everything from `copier copy` plus `instances/somalia/{config.yaml,data/raw/.gitkeep,data/descriptors/*.yaml,harmonization/.gitkeep}`, `instances/sudan/` (same, empty roles), `docs/decisions/`
- Modify: `pyproject.toml` (dependencies, `reprokit @ git+https://github.com/AaronScherf/reprokit@v0.2.0`), `protocol.md`, `.gitignore` (ignore `instances/*/data/raw/*`, `instances/*/data/derived/*`, `instances/*/outputs/*`, keep `.gitkeep`)

**Interfaces:**
- Produces: an instance config for Somalia with roles `conflict_events`, `displacement`, `prices`, `rainfall`, `admin_boundaries` (providers ACLED, UNHCR/NRC PRMN, WFP, UCSB CHC CHIRPS, OCHA COD-AB), period `2021-01-01` to `2023-08-31` (decided 2026-10-31: the HDX PRMN dataset ends 2023-08; extend later by config change if a newer release is found), geography `Somalia`, parameters from Task 11. One descriptor per role from the pilot design's table; every unverified field is the literal `unverified`, `access_class` set correctly (`conflict_events: account_required`, with `accessed`, `applied_filters`, `manipulation` filled from the existing export: accessed `2026-10-31`, filters `Somalia, event dates 1997-01-01 to 2025-10-31`).

- [x] **Step 1:** `uv run copier copy` the reprokit template into `C:\Users\theaa\compound-shocks-panel` (project_name `Compound Shocks Panel`). Add the dependencies listed in the stack to `pyproject.toml`, run `uv lock`, `uv sync`.
- [x] **Step 2: Write failing test** `tests/test_repo_layout.py::test_reprokit_validate_passes_on_repo` running `reprokit.cli.main(["validate", "."])` expects 0 and `test_somalia_and_sudan_instances_exist`. Fill the instances and descriptors until it passes.
- [x] **Step 3:** Copy `protocol.md` content from the monorepo's `projects/02_compound_shocks/protocol.md` (verification gates, decision log) into the new `protocol.md`; copy the existing ACLED export from `...projects/02_compound_shocks/data/raw/ACLED Data_2026-10-31_...csv` into `instances/somalia/data/raw/conflict_events/` (local only, ignored; confirm `git status` does not list it).
- [x] **Step 4:** Commit with explicit paths. Owner creates the GitHub repo and pushes.

### Task 3: Step-runner spike and decision

**Files:**
- Create: `src/compound_shocks/__init__.py`, `src/compound_shocks/cli.py`, `src/compound_shocks/pipeline.py`, `dodo.py`, `docs/decisions/001-step-runner.md`, `tests/test_reproduce_skeleton.py`, `.github/workflows/ci.yml` (matrix `ubuntu-latest`, `windows-latest`)

**Interfaces:**
- Produces: `compound_shocks.cli.main(argv: list[str] | None = None) -> int` with `reproduce --instance NAME`; `compound_shocks.pipeline.tasks(instance_dir: Path) -> list[dict]` (doit task dicts with `name`, `file_dep`, `targets`, `actions`). Skeleton steps: `read` then `aggregate` then `fuse`, each writing a small file under `instances/<name>/data/derived/`.

- [x] **Step 1: Write failing tests:** `test_reproduce_runs_skeleton_on_fixture_instance` (tmp instance with two tiny input files; exit 0; outputs exist); `test_second_run_does_no_work` (capture doit's up-to-date count, all tasks skipped); `test_changed_input_reruns_only_dependents` (touch one role's file bytes; only its chain reruns); `test_runs_with_no_make_installed` (the command never shells out to `make`).
- [x] **Step 2:** Implement with doit's Python API (`DoitMain` with a `ModuleTaskLoader`), no `dodo.py` logic beyond importing `pipeline.tasks`. Run tests; expect PASS on this Windows machine.
- [x] **Step 3:** Push the branch and read the CI matrix result for Linux. Write `docs/decisions/001-step-runner.md`: chosen runner, the evidence (test results on both OSes), and the fallback (own minimal runner with the same `tasks()` interface) if either OS fails. If the spike fails on either OS, stop and report to Claude before continuing.
- [x] **Step 4:** Commit.

### Task 4: Canonical schemas, adapter protocol, mapping loader

**Files:**
- Create: `src/compound_shocks/schema.py`, `src/compound_shocks/adapters/__init__.py`, `src/compound_shocks/adapters/base.py`, `src/compound_shocks/adapters/mapping.py`, `tests/test_schema.py`, `tests/test_adapters_base.py`

**Interfaces:**
- Produces: `ROLE_COLUMNS: dict[str, list[str]]` (the five canonical tables from Spec section 4); `PANEL_COLUMNS: dict[str, Literal["core", "extension"]]` (core: `events`, `fatalities`, `precip_mm`, `coverage_frac`, `price_sorghum`, `price_wheat`; extension: displacement columns, terms-of-trade columns); `check_frame(df, role: str) -> list[reprokit.problems.Problem]` (missing/extra columns, wrong dtype kinds, duplicate keys); `class Adapter(Protocol)` with `role: str`, `provider: str`, `find(raw_dir: Path) -> list[Path]`, `read(paths: list[Path], instance: dict) -> pd.DataFrame`; `register(adapter: Adapter) -> None`; `get_adapter(role: str, provider: str) -> Adapter` (provider compared with `strip().casefold()`; `KeyError` message lists registered providers for the role); `load_mapping(path: Path) -> dict[str, str]`; `apply_mapping(df, mapping) -> pd.DataFrame` (rename, then missing-source-column Problem naming the column).

- [x] **Step 1: Write failing tests:** `test_check_frame_names_missing_column`; `test_check_frame_flags_duplicate_keys`; `test_get_adapter_ignores_case_and_whitespace`; `test_get_adapter_unknown_provider_lists_registered`; `test_apply_mapping_renames_and_reports_missing_source_column`; `test_every_core_panel_column_is_documented` (every key in `PANEL_COLUMNS` appears in `README.md`).
- [x] **Step 2:** Implement; run; commit.

### Task 5: ACLED adapter and mapping

**Files:**
- Create: `src/compound_shocks/adapters/acled.py`, `src/compound_shocks/adapters/mappings/acled.yaml`, `tests/test_acled_adapter.py`, `tests/fixtures/make_fixtures.py` (seeded generator, ACLED part), `tests/fixtures/acled_fixture.csv`

**Interfaces:**
- Produces: `AcledAdapter` (`role="conflict_events"`, `provider="ACLED"`), `find` globs `*.csv` in the role dir; `read` returns canonical `event_id, date, lat, lon, event_type, sub_event_type, actor1, fatalities, geo_precision` (date as ISO string, `fatalities` int). Mapping file: `event_id_cnty -> event_id`, `event_date -> date`, `latitude -> lat`, `longitude -> lon`; a `lat_long` variant is handled by the same adapter via an optional split mapping key.

- [x] **Step 1: Write failing tests:** `test_reads_fixture_with_bom` (fixture written with a UTF-8 BOM, first column found); `test_lat_long_single_column_variant_is_split`; `test_output_passes_check_frame`; `test_find_ignores_non_csv_and_gitkeep`; `test_real_export_header_maps` (marked `real_data`: reads only the header of the real export, asserts all mapping source columns exist; never loads rows into any external service).
- [x] **Step 2:** Implement (`encoding="utf-8-sig"`); run; commit.

### Task 6: Boundaries adapter and point-in-polygon

**Files:**
- Create: `src/compound_shocks/adapters/boundaries.py`, `src/compound_shocks/spatial.py`, `tests/test_boundaries.py`, `tests/test_spatial.py`, fixture GeoJSON (3 tiny districts) from the generator

**Interfaces:**
- Produces: `CodAbAdapter` (`role="admin_boundaries"`, `provider="OCHA COD-AB"`) returning a GeoDataFrame with `admin2_id, name, geometry` and `gdf.attrs["vintage"]`; `GeoBoundariesAdapter` with the same output (fallback provider, so using it requires a harmonization record); `assign_admin2(points: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> pd.DataFrame` adds `admin2_id` (`<NA>` when none) and never changes row count; a point on a shared boundary goes to the district with the lowest `admin2_id`; returns unassigned count in `result.attrs["unassigned"]`.

- [x] **Step 1: Write failing tests:** `test_point_on_shared_boundary_is_assigned_to_lowest_id`; `test_point_outside_all_polygons_is_unassigned_and_counted`; `test_row_count_preserved`; `test_vintage_recorded`; `test_geoboundaries_output_matches_canonical_columns`.
- [x] **Step 2:** Implement with geopandas `sjoin` (`predicate="intersects"`, then drop duplicates by lowest id); run; commit.

### Task 7: Rainfall adapter and zonal statistics

**Files:**
- Create: `src/compound_shocks/adapters/chirps.py`, extend `src/compound_shocks/spatial.py`, `tests/test_chirps.py`; generator makes two tiny monthly GeoTIFFs with a nodata cell

**Interfaces:**
- Produces: `ChirpsAdapter` (`role="rainfall"`, `provider="UCSB CHC CHIRPS"`); `zonal_monthly(rasters: dict[str, Path], boundaries: gpd.GeoDataFrame) -> pd.DataFrame` with columns `admin2_id, month, precip_mm, coverage_frac` (`rasters` maps `YYYY-MM` to a file; area-weighted mean over valid cells; `coverage_frac` is the share of the district's area with valid cells).

- [x] **Step 1: Write failing tests:** `test_area_weighted_mean_on_known_grid`; `test_nodata_cells_lower_coverage_frac_not_precip`; `test_district_with_no_valid_cells_has_nan_precip_and_zero_coverage`; `test_month_taken_from_mapping_keys`.
- [x] **Step 2:** Implement with rasterio masks (no extra zonal library unless needed); run; commit.

### Task 8: Prices and displacement adapters

**Files:**
- Create: `src/compound_shocks/adapters/wfp_prices.py`, `src/compound_shocks/adapters/prmn.py`, `src/compound_shocks/adapters/mappings/{wfp_prices,prmn}.yaml`, `src/compound_shocks/crosswalk.py`, `tests/test_wfp_prices.py`, `tests/test_prmn.py`, `tests/test_crosswalk.py`

**Interfaces:**
- Produces: `WfpPricesAdapter` (`role="prices"`, `provider="WFP"`) canonical `date, market, admin2, commodity, unit, currency, price` (rows with a different unit or currency for the same commodity-market are flagged, not merged); `PrmnAdapter` (`role="displacement"`, `provider="UNHCR/NRC PRMN"`) canonical `month, origin_admin2, dest_admin2, individuals, reason` with `reason` mapped to `drought|conflict|flood|other`; `apply_crosswalk(df, column: str, crosswalk: dict[str, str], role: str) -> tuple[pd.DataFrame, list[Problem]]` replaces provider district names with COD-AB `admin2_id`s and returns a Problem per unmatched name.

- [x] **Step 1: Write failing tests:** `test_prices_mixed_units_are_flagged`; `test_prmn_unreported_month_is_nan_not_zero`; `test_prmn_reason_categories_mapped_and_unknown_reported`; `test_crosswalk_reports_every_unmatched_name`; `test_adapters_output_passes_check_frame`.
- [x] **Step 2:** Implement; run; commit. Real column names are unverified; Task 14 confirms them against actual downloads.

### Task 9: Panel fusion

**Files:**
- Create: `src/compound_shocks/panel.py`, `tests/test_panel.py`

**Interfaces:**
- Consumes: canonical tables from Tasks 5 to 8, `assign_admin2`, `zonal_monthly`, `PANEL_COLUMNS`.
- Produces: `month_of(date: str) -> str` (`"2021-02-28"` to `"2021-02"`); `aggregate_conflict(events: pd.DataFrame) -> pd.DataFrame` (columns `admin2_id, month, events, fatalities`); `fuse_panel(conflict, rainfall, prices, displacement, admin2_ids: list[str], months: list[str]) -> pd.DataFrame` with one row per `(admin2_id, month)` over the full cross product; conflict missing means `0`, price and displacement missing mean `NaN`; `panel.attrs["column_kinds"]` copies `PANEL_COLUMNS`; `publishable_aggregates(panel) -> pd.DataFrame` returns only `admin2_id, month, events, fatalities`.

- [x] **Step 1: Write failing tests:** `test_month_boundaries` (Jan 31, Feb 28, Dec 31); `test_district_month_without_events_is_zero`; `test_missing_price_is_nan_not_zero`; `test_panel_keys_unique_and_complete`; `test_unassigned_events_are_not_in_panel_but_counted`; `test_publishable_aggregates_has_no_coordinates_ids_actors_or_event_types`.
- [x] **Step 2:** Implement; run; commit.

### Task 10: Pipeline wiring, gate and manifest

**Files:**
- Modify: `src/compound_shocks/pipeline.py`, `src/compound_shocks/cli.py`
- Create: `tests/test_pipeline_end_to_end.py`, instance fixtures under `tests/fixtures/instance_somalia/`

**Interfaces:**
- Consumes: Tasks 3 to 9, `reprokit.manifest`, `reprokit gate`.
- Produces: `reproduce --instance NAME` runs `gate` (against `instances/somalia/config.yaml` as the baseline), then `read` per role through `get_adapter`, `spatial`, `aggregate`, `fuse`, `manifest`; outputs `data/derived/panel.csv`, `outputs/manifest.json`, `outputs/publishable_aggregates.csv`. Stops with exit 1 before processing if the gate fails or `check_frame` finds problems.

- **Carry-over from review of Task 8:** adapters put their problem lists in `df.attrs["problems"]`, which pandas can drop on `concat`/`copy`; collect them immediately after each `read` and add `test_adapter_problems_reach_the_run_report`.

- [x] **Step 1: Write failing tests:** `test_end_to_end_on_fixture_instance`; `test_provider_swap_without_record_stops_before_processing` (no derived file written); `test_provider_swap_with_record_proceeds`; `test_manifest_lists_core_and_extension_columns`; `test_rerun_is_idempotent` (panel bytes identical; manifest identical except `created_utc`).
- [x] **Step 2:** Implement; run; commit.

### Task 11: Exploratory data analysis and diagnostics

**Files:**
- Create: `src/compound_shocks/eda.py`, `src/compound_shocks/figures.py`, `tests/test_eda.py`, `tests/test_figures.py`
- Modify: `pyproject.toml` (remove `statsmodels`; Phase B re-adds it), `uv.lock`

**Interfaces:**
- Produces: `data_profile(panel: pd.DataFrame) -> dict` (per column: non-null count, zero count, min and max month, number of distinct districts with any non-null value; per source group the same); `missingness_matrix(panel, out: Path) -> None` (heatmap, districts by month, one panel per source column, saved as PNG); `plot_commodity_series(prices: pd.DataFrame, out: Path) -> None` (raw market-level price lines by commodity, no index, no basket weighting); `plot_conflict_rainfall_trends(panel, out: Path, accessed: str) -> None` (monthly national totals of events and fatalities with mean precipitation); `make_district_audit_map(panel, boundaries: gpd.GeoDataFrame, column: str, out: Path, accessed: str) -> None` (coarse choropleth). Every figure with ACLED-derived content has the caption `Source: ACLED (acleddata.com), accessed <accessed>`.

- [x] **Step 1: Write failing tests:** `test_profile_counts_zeros_and_nans_separately` (a conflict zero is counted as a zero, a missing price as null); `test_profile_reports_district_coverage_per_source`; `test_missingness_matrix_writes_png_with_one_panel_per_column`; `test_price_series_uses_raw_prices_not_an_index` (plotted y-values equal the input prices); `test_conflict_figures_have_acled_caption` (inspect saved figure text objects); `test_price_figure_has_no_acled_caption`; `test_no_modeling_imports` (importing the package imports neither `statsmodels` nor `sklearn`).
- [x] **Step 2:** Implement with matplotlib (Agg backend); run; remove `statsmodels` from `pyproject.toml`, run `uv lock`; commit.

### Task 12: Exploratory data audit memo (done 2026-11-02, `01af18c`; 162 tests; `audit` step runs in `reproduce`, memo reads descriptors for access dates and ACLED answers)

**Files:**
- Create: `src/compound_shocks/audit_memo.py`, `tests/test_audit_memo.py`; add an `audit` step to `pipeline.py`
- Modify: `project.yaml` (deliverable `data-audit-memo`, format `markdown`, build `python -m compound_shocks reproduce --instance NAME`)

**Interfaces:**
- Produces: `build_audit_memo(instance_dir: Path) -> Path` writes `outputs/audit_memo.md` (and a copy as HTML) from the instance's manifest, descriptors, panel profile and EDA figures. Sections: dataset provenance (provider, dataset ID, access dates, hashes, boundary vintage); coverage and missingness findings (districts with no market, months with no displacement report, unassigned-event count, share of district-months with any price); the figures; the three ACLED answers (access date, applied filters, manipulation); observations and caveats to inform the literature review and research design. It states no causal or hypothesis claim.

- [x] **Step 1: Write failing tests:** `test_memo_contains_provenance_hashes_and_access_dates`; `test_memo_reports_districts_with_no_price_observations`; `test_memo_contains_acled_citation_block_and_three_answers`; `test_memo_makes_no_causal_claims` (the memo template contains none of the words "effect of", "causes", "impact of", "significant"); `test_audit_step_is_part_of_reproduce`.
- [x] **Step 2:** Implement (plain string templates, no LaTeX); run; commit.

### Task 13: Fetch layer (mocked HTTP only)

**Files:**
- Create: `src/compound_shocks/fetch/{__init__.py,hdx.py,acled.py,chirps.py,codab.py}`, `tests/test_fetch.py`, `.env.example` (entries `ACLED_EMAIL`, `ACLED_PASSWORD`)

**Interfaces:**
- Pinned sources (from "Source facts checked"): `fetch_hdx` takes the dataset IDs `wfp-food-prices-for-somalia`, `cod-ab-som` (GeoJSON resource) and `somalia-internally-displaced-persons-idps`; `fetch_chirps(months: list[str], out_dir: Path)` builds the v2.0 Africa monthly URL for each `YYYY-MM`, downloads, and gunzips. Add a test that a 404 on any pinned URL raises an error naming the source and URL (providers move files, as CHIRPS already did once).
- Produces: `fetch_file(url: str, out_dir: Path, expected_sha256: str | None, refresh: bool = False) -> Path` (writes the file; with `expected_sha256` set, a mismatch raises `ProviderRevisedData` naming both hashes and the access date unless `refresh=True`); `fetch_hdx(dataset_id: str, resource_name: str, out_dir: Path, ...) -> Path` using the HDX CKAN API with pinned IDs from the descriptor; `fetch_acled(params: dict, out_dir: Path) -> Path` reads credentials from `ACLED_EMAIL` and `ACLED_PASSWORD`, raises a plain-language error with registration instructions if unset, and never logs them; all fetchers write the descriptor's `accessed` and `sha256`.

- [x] **Step 1: Write failing tests with `requests` mocked:** `test_hash_mismatch_raises_provider_revised_data_unless_refresh`; `test_acled_missing_credentials_explains_how_to_register`; `test_credentials_never_appear_in_logs_or_exceptions`; `test_fetch_writes_into_role_directory`.
- [x] **Step 2:** Implement; run; commit. No test touches the network.

### Task 14: Somalia real run (owner and Gemini operate; Claude reviews)

**Files:** `instances/somalia/data/raw/*` (ignored), `instances/somalia/data/descriptors/*.yaml`, `docs/verification/somalia-2026-XX-XX.md`

- [x] **Step 0 (decided by owner 2026-10-31):** Somalia window is 2021-01 through 2023-08 because the HDX PRMN dataset ends 2023-08; CHIRPS v2.0. A newer PRMN release (UNHCR portal or Microdata Library request) is a parallel, non-blocking check; record the outcome in the verification note.
- [x] **Step 1 (done 2026-11-02, via the Task 13 fetchers):** Owner downloads PRMN, WFP prices, CHIRPS (months in the chosen window), COD-AB Somalia into the role directories (or runs the Task 13 fetchers). The ACLED export already exists.
- [x] **Step 2 (done 2026-11-02; descriptors filled in `01af18c`):** For each role, replace every `unverified` field in the descriptor from the provider's page and the actual file; set `verification_status: source-verified`. Confirm or correct the canonical columns and mapping files against real headers; any mismatch is a Task 5 or 8 fix with a test.
- [x] **Step 2b (all four fixed with tests; review findings on Tasks 6 to 8, 2026-10-31; each fix needs a test):** (1) the real WFP CSV has an HXL tag row (`#date`, `#adm2+name`, ...) under the header; `WfpPricesAdapter` must skip it. (2) `pricetype` (retail/wholesale) is dropped by the canonical `prices` table; filter to retail or flag mixed price types per market and commodity. (3) `CodAbAdapter.find` only globs `*.geojson`; handle the HDX shapefile/GDB download too. (4) Time `zonal_monthly` on the real window (about 74 districts x 32 months); if it takes minutes, switch the per-cell loop to `rasterio.mask`, keeping the area-weighted tests green.
- [x] **Step 3 (done 2026-11-02; note at `docs/verification/somalia-2026-11-02.md` in the compound-shocks-panel repo, fresh-clone hashes match):** Run `uv run python -m compound_shocks reproduce --instance somalia`. Record in `docs/verification/` the commands, row counts per role, unassigned-event count, price-gap pattern, and any harmonization or boundary-vintage finding. Set `verification_status: run on acquired data` only after a clean run.
- [x] **Step 4 (done 2026-11-02; the notes are counts only, no ACLED rows):** Claude reviews the verification note before anything is committed to the public repo. Raw ACLED rows are never pasted into any external AI tool; only counts and column names are shared.

**Findings from the real run (2026-11-02), all fixed with tests and recorded in the repo's `protocol.md` decision log:**
- COD-AB v03 zip holds two admin2 files (`_em` edge-matched copy dropped); properties are lowercase `adm2_pcode`, `adm2_name`.
- The HDX PRMN CSV is a 3 KB per-district summary; the real data is the XLSX (sheet `OutputsArrivals`, weekly rows, day-first dates).
- CHIRPS GeoTIFFs have no nodata tag and mark sea cells -9999; unmasked, they corrupted district means.
- The ACLED export repeats each event once per actor row (101,144 rows, 52,925 events); collapsed to one row per `event_id`.
- PRMN and WFP report Mogadishu only as "Banadir", so the 17 Mogadishu districts and "Unspecified" are merged into one unit (74 units). Owner decision.
- Three provider spellings are aliased; Badhan and Dhahar are absent from COD-AB v03 and stay unassigned; 204 WFP rows with a blank district are assigned by market.
- Reproducibility: code fingerprint invalidates stale steps, CSVs use LF, text hashes ignore line endings; a fresh clone reproduces `panel.csv` and `publishable_aggregates.csv` byte for byte.
- Panel: 2,368 rows; prices in 21% of district-months (37 of 74 districts); displacement in 90%.
- Update 2026-11-02: the owner extended the Somalia window to 2021-01 through 2025-10 (latest month ACLED and WFP prices both cover). PRMN still ends 2023-08, so `displaced_individuals` is missing from 2023-09 on. The panel is now 74 x 58 = 4,292 rows with prices in 33% of district-months (35% of market-district months in 2021, 94% in 2024) and a `population` context column (OCHA COD-PS, 2014 UNFPA estimate, one fixed figure per district). The clean-room hashes above predate this and must be redone (Task 16).
- Open for the review gate: nominal local-currency prices versus USD; venue and purpose.

### Task 15: Sudan portability (data pipeline only) (done 2026-11-02)

**Files:**
- Create: `instances/sudan/config.yaml`, `instances/sudan/crosswalks/district_names.yaml`, `instances/sudan/data/descriptors/*.yaml`, `instances/sudan/harmonization/displacement.yaml`, `src/compound_shocks/adapters/iom_dtm.py` (plus its mapping), `tests/test_iom_dtm.py`, `docs/verification/sudan-2026-11-02.md`
- Also built in this task: the `displacement_stock` canonical schema and the `displaced_stock` / `displaced_stock_change` panel columns; the `fetch/hdx.py` `SOURCES` registry keyed by instance; the missingness-versus-conflict section of the audit memo; and a new `population` role (OCHA COD-PS: `adapters/population.py`, `units.merge_populations`, a `population` source in both configs and descriptors, events per 100,000 residents and a market-district coverage table in the memo).

**Interfaces:**
- Produces: `IomDtmAdapter` (`role="displacement"`, `provider="IOM DTM"`) canonical `month, dest_admin2, origin_admin1, stock` (stock, not flow); `stock_change(df: pd.DataFrame) -> pd.DataFrame` (first difference per `dest_admin2`, NaN where a month is missing, documented caveat on re-displacement and returnees). Only the "Armed Clashes in Sudan (Overview)" operation is read; other DTM operations are dropped, not filled in, because they run 2.4 to 3 times higher where they overlap and a first version that mixed them switched series in 184 of 185 localities.

- [x] **Step 1: Write failing tests:** `test_stock_change_nan_when_month_missing`; `test_iom_dtm_output_passes_check_frame`; `test_sudan_reproduce_blocked_without_displacement_record`; `test_sudan_reproduce_with_record_produces_panel_and_manifest` (fixture instance); and `test_only_the_overview_series_is_used_and_others_are_not_mixed_in`.
- [x] **Step 2:** Implement; run; commit (`81f9bc7`, population `2450f7d`, Overview-only and period `c1c545b`).
- [x] **Step 3 (done 2026-11-02; Gemini state codes were wrong, COD-AB v03 uses SD01 Khartoum):** Sudan data downloaded and the Gemini findings re-checked against the real files (DTM P-codes match COD-AB v03 exactly; WFP covers 18 markets in 18 of 189 localities). `harmonization/displacement.yaml` approved by the owner (`e303780`). The owner set the Sudan period to 2021-01 through 2025-10. `reproduce --instance sudan` ran clean and the audit memo was generated; note at `docs/verification/sudan-2026-11-02.md`. **No regressions or model comparisons.**

**Findings (2026-11-02, recorded in the repo's `protocol.md`):**
- Sudan panel: 189 localities x 58 months = 10,962 rows. Sorghum or wheat prices in 7% of locality-months (18 of 189 localities, 17% of the population); displacement stock in 32% (none before 2023-08); ACLED 23,418 events in the panel, 344 unassigned.
- Price gaps and conflict (descriptive, no test): localities that ever have a price have more events (6.39 vs 1.69 per month; 2.33 vs 0.96 per 100,000 residents). Within market localities, months without a price have more events in 2023 (12.19 vs 5.57) and 2024 (10.72 vs 6.24), about equal in 2025, and fewer in 2021. Somalia shows the same direction between districts; within its market districts months without a price have more events from 2024 (7.52 vs 4.30) while 2021 to 2022 show the reverse (3.24 vs 6.43 in 2021). These are descriptive and cannot separate where markets are placed from collection lapsing where fighting is heavier; that question goes to the Review Gate.
- Somalia's thin map is mostly market placement: 37 of 74 districts have a price, holding 68% of the population, but only 13 have one in 75% of months.
- Sudan displacement is a stock; Somalia's is a flow. A Gemini review (2026-11-02) concluded they are not comparable, must stay distinct columns, and must not share a cross-country statistic.
- Open for the review gate: wholesale rows (318 in Sudan); mixed millet units (3.5 KG vs 90 KG); SDG nominal prices; the Somalia population is a 2014 estimate.

### Task 16: Clean-room check and release

**Files:** `README.md` (replication guide for a non-technical reader), `CHANGELOG.md`, `CITATION.cff`

- [x] **Step 1 (done 2026-11-02, fresh clone at `fb279f2`):** Fresh clone into a scratch directory; `uv sync --locked` (26s); `uv run pytest` (182 passed, 1 skipped; about 3 minutes, because the end-to-end tests run the real pipeline on fixtures); `uv run reprokit validate .` (pass). There is no CLI fixture instance, so `reproduce --instance somalia` needs the real raw data; the fixture pipeline run is covered by `tests/test_pipeline_end_to_end.py`. The original expectation of PASS in under 60 seconds was wrong and is dropped. The earlier real-data clean-room hashes cover the old 2021-01 to 2023-08 window and are void: repeat the real-data check for Somalia (74 x 58, 2021-01 to 2025-10; `panel.csv` 785f6c1d…, `publishable_aggregates.csv` d7ff4f77…; **both matched exactly, 13m13s**) and Sudan (189 x 58; ff16c5bc…, d3030e1b…; **both matched exactly, 17m23s**, memory-heavy, run alone). Raw files were copied from the working copy, not re-downloaded.
- [x] **Step 2 (done 2026-11-02, `fb279f2`, timings corrected in `d2ce302`):** README: what the project is, quick start, how to get each data source (with the account steps and costs; no paid AI needed), how to run another country (the Sudan walkthrough), the core/extension column marking, ACLED terms and the capture-date caveat, how to cite. State that the Somalia flow (`displaced_individuals`) and the Sudan stock (`displaced_stock`, `displaced_stock_change`) are not comparable and never share a cross-country statistic; remove the "planned portability test" wording and the old 2023-08 window.
- [x] **Step 3 (review done 2026-11-02: no credentials in tree or history, no raw rows, aggregates are totals only; owner approved the tag; `v0.1.0` tagged at `d2ce302`):** Claude reviews security and licensing (no raw data, no credentials, ACLED aggregates only, boundaries and data licenses stated). Tag `v0.1.0` (the Phase A data pipeline) after the owner approves; the repo already exists. Then stop: the Review Gate follows.

## Review Gate (after Task 16; no coding)

1. **Data audit:** review both audit memos; ask whether price gaps track conflict intensity (survival or selection bias in who reports), whether Admin 2 aggregation hides or creates patterns, and what is too sparse to use.
2. **Literature gap memo:** use the literature pipeline and `notes/lit_review.md` to answer what is already published on Somalia 2021 to 2023 and on import-price and climate interactions in East Africa, what the contribution would be, and which identification strategy the observed gaps allow.
3. **Owner decision:** approve the research question, the modeling plan, and which deferred components to reactivate (price decompositions, nested tests, report build). Only then write the Phase B plan.

## Self-review notes

- Spec coverage (Phase A): scope and repo shape (T2), roles and canonical schemas (T4 to T8), core/extension marking (T4, T9), adapters and mappings (T4 to T8), step graph decision and spike (T3), fetching with hash and revised-data semantics and ACLED credentials (T13), fixtures and tests (T5 to T9 and generator), EDA figures with ACLED caption and audit memo (T11, T12), Sudan portability with harmonization record (T10, T15), ACLED constraints in 7.1 (Global Constraints, T9, T11, T13), open items left to the owner (ACLED email, low-count policy: totals only until answered).
- Interfaces are consistent: `check_frame`, `get_adapter`, `assign_admin2`, `zonal_monthly`, `fuse_panel`, `publishable_aggregates`, `data_profile` carry the same signatures wherever used.
- Not in this plan: narrative layers, cash data, econometric modeling, price decompositions, cross-country regressions, LaTeX paper, slides or web app (all Phase B or later), and the communication hook (plan 3).
