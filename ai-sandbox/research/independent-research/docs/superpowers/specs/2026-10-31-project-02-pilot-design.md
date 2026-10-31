# Project 02 pilot: architecture design (plan 2 input)

Status: draft for owner review, 2026-10-31. Covers spec phase 5 of the
[framework design](2026-10-31-reproducible-research-framework-design.md). Depends on
reprokit v0.1 ([plan 1](../plans/2026-10-31-reprokit-core-plan.md)). Choices marked
**[Claude's call]** were not decided by the owner.

## 1. What the pilot proves

One study repo that reproduces the Somalia result from acquired data, then re-runs
unchanged on Sudan with only a new instance config, new downloaded files, and (where a
provider changes) a harmonization record. It exercises the framework's hard parts: role-based
inputs, cosmetic vs structural harmonization, restricted-data fetching, fixtures, manifests,
and the `reproduce` command.

## 2. Scope [Claude's call, needs owner decision]

The Somalia case-study note has three layers. **The pilot covers Layer 1 only**: the
district-month fused panel (prices, rainfall, conflict, displacement) and the descriptive
price decomposition, with district-level or coarser maps. Layers 2 and 3 (narrative collection, LLM
claim coding, claim lineage) are excluded: they are subscription-heavy, depend on a
different set of sources, and are not what the portability test needs. They become a later
module (the note already suggests folding claim-lineage into the Project 04 toolkit).
Cash-transfer data is also excluded: it is request-only and the protocol warns that
transfer presence is endogenous. No causal claims; the analysis is descriptive, matching
the case-study note ("causal identification deferred to the full Project 02 panel").

## 3. Repo shape

- Name **[Claude's call]**: `compound-shocks-panel` (country-neutral). Generated from the
  reprokit copier template, kind `study`, confidentiality `public`.
- One fixed study design; each country is an **instance**: `instances/somalia/` and
  `instances/sudan/`, each with `config.yaml` (geography, period, sources by role, parameter
  overrides), `data/raw/`, `data/descriptors/`, `harmonization/` and `outputs/`. Code under
  `src/compound_shocks/` is identical for both.
- Existing Codex intake files (`source_register.csv`, `inventory.py`, `protocol.md`) migrate
  in: the register becomes per-role descriptors, `inventory.py` is superseded by the
  manifest hashing in reprokit, and the protocol's verification gates carry over verbatim.

## 4. Roles and canonical schemas

A role is what the pipeline asks for. Each has a canonical table; an adapter produces it.
Fields below come from the data-sources note and are **unverified against real files**
(the protocol forbids assuming them); the first acquisition task confirms or corrects them.

| Role | Canonical columns | Notes |
| --- | --- | --- |
| `conflict_events` | `event_id, date, lat, lon, event_type, sub_event_type, actor1, fatalities, geo_precision` | Source may give `lat_long` or separate columns: a cosmetic mapping |
| `displacement` | `month, origin_admin2, dest_admin2, individuals, reason` | `reason` categories differ by provider: structural |
| `prices` | `date, market, admin2, commodity, unit, currency, price` | Same commodity/unit/currency checks as the protocol |
| `rainfall` | gridded raster in, `admin2, month, precip_mm, coverage_frac` out | Zonal statistics; records missing cells per district-month |
| `admin_boundaries` | `admin2_id, name, geometry` plus boundary vintage | Needed by rainfall and every spatial join; vintage recorded |

## 5. Adapter interface

Per role and per provider, a small module in `src/compound_shocks/adapters/` implements:

```python
class Adapter(Protocol):
    role: str
    provider: str
    def find(self, raw_dir: Path) -> list[Path]: ...
    def read(self, paths: list[Path], instance: dict) -> pd.DataFrame: ...  # canonical columns
```

- `find` locates files by role/provider pattern in the instance's `data/raw/`, never by a
  hard-coded filename.
- Column renames live in a YAML mapping next to the adapter (`mappings/acled.yaml`), so
  a changed header is a data edit and not a code edit. These are the logged cosmetic changes.
- A new provider for an existing role means a new adapter *and* a harmonization record. The
  gate from reprokit (`check_gate`) runs before the pipeline and blocks otherwise.
- Canonical-schema checks run on every adapter output (column set, dtypes, no silent zeros for
  missing). Library choice (pandera or a few hand-written checks) is left to the builder.

## 6. Step graph [Claude's call, needs a short spike]

Pipeline: `fetch` per role, then `read` (adapter), then `harmonize/aggregate` to district-month,
then `fuse` into the panel, then `analyze`, then `figures`, then `report`. Steps declare
inputs/outputs and skip when unchanged.

| Option | For | Against |
| --- | --- | --- |
| **doit** (Python-native) | Cross-platform, plain Python task definitions, skips unchanged work, light | Smaller community; dynamic dependencies need `calc_dep` |
| Make | Universal | Windows is the weak point; non-technical Windows users will struggle |
| Snakemake | Strong for large/cluster pipelines | Heavier; its native Windows behavior is unconfirmed |
| DVC | Data versioning alongside Git | Adds a second tool; solves data tracking more than step ordering |

Recommendation: **doit**, wrapped behind a single `python -m compound_shocks reproduce`
command so the choice is invisible to users. Evidence is thin (a web search found anecdotes,
no head-to-head), so Task 1 of plan 2 is a one-day spike confirming doit runs the pipeline skeleton
on Windows and Linux. If it fails, fall back to a small own runner (steps as functions with
declared inputs/outputs and hash-based skipping). The pilot has **no data-dependent fetch**
(rainfall uses district polygons, not conflict coordinates), so dynamic graphs are not needed
now; the adapter interface leaves room for them (conflict-coordinate-driven satellite
queries) when a later project needs it.

## 7. Fetching restricted and open data

- `fetch` is separate from `read` and never runs implicitly. Open sources (HDX CKAN API for
  PRMN and WFP prices; CHIRPS monthly rasters over HTTPS) can be fetched by script with
  pinned dataset IDs. ACLED is account-gated: the fetch step reads credentials from
  environment variables (named in the README, never in files), and a user without an
  account is told how to register and which export to download manually.
- Every fetch writes a data descriptor and the file hash, and fails if the hash differs
  from the expected one unless the user passes an explicit refresh flag (providers revise data).
- Google Earth Engine is an alternative rainfall backend selected through `compute.yaml`,
  not the default (it needs an account).

## 8. Fixtures and tests

- `tests/fixtures/` is generated by a seeded script: roughly 3 districts and 12 months per role,
  with a deliberately missing market-month, a zero-displacement district-month, and a point on a
  district boundary. Schemas match the canonical tables.
- Tests: adapters map renamed columns; month assignment of events; point-in-polygon on a
  boundary point; zonal aggregation and `coverage_frac`; zeros vs missing preserved through
  the join; fused panel keys unique; the harmonization gate blocks a provider swap; the whole
  pipeline runs on fixtures in under a minute with no network.

## 9. Deliverables [Claude's call]

Price decomposition charts, district-level maps, a fused panel (CSV, regenerable), a short LaTeX
report built by `reproduce`. Slides and any web app are out of the pilot. Maps stay at district level
or coarser (case-study ethics). Derived outputs from ACLED are not published until its terms
are checked (open item).

## 10. Sudan portability test

Changes only `instances/sudan/config.yaml` and downloads. Expected structural change:
displacement provider (PRMN is Somalia-specific; IOM's tracking matrix is the candidate, **to
verify**), which forces a harmonization record comparing definitions, reason categories and
geography. Price coverage may be thin after the 2023 war began, so the study window and
missingness handling are decisions documented in the record and instance config. The result is
judged by whether the two manifests show the same method and by the harmonization record, not by
matching coefficients.

## 11. Open items for the owner

1. Confirm pilot scope: Layer 1 only (section 2).
2. ACLED terms: may district-month aggregates derived from ACLED be published in the repo?
3. Boundary source and vintage (OCHA common operational boundaries is the usual choice;
   not verified here).
4. Sudan displacement and price sources actually obtainable, and the window.
5. Repo name and whether the Somalia data account setup (ACLED registration) is done.
