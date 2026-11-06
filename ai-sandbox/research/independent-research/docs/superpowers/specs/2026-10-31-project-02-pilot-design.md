# Project 02 pilot: architecture design (plan 2 input)

Status: draft for owner review, 2026-10-31. **Scope realigned 2026-10-31 to Phase A (data exploration); see section 12.** Covers spec phase 5 of the
[framework design](2026-10-31-reproducible-research-framework-design.md). Depends on
reprokit v0.1 ([plan 1](../plans/2026-10-31-reprokit-core-plan.md)). Choices marked
**[Claude's call]** were not decided by the owner.

## 1. What the pilot proves

**Phase A (this pilot): data exploration and portability.** One study repo that ingests, harmonizes and fuses
Somalia's prices, rainfall, conflict, displacement and boundaries into a district-month panel, reproducibly, and
whose same code then ingests Sudan with only a new instance config, new downloaded files, and (where a provider
changes) a harmonization record. It exercises the framework's hard parts: role-based inputs, cosmetic vs
structural harmonization, restricted-data fetching, fixtures, manifests, and the `reproduce` command. It answers
"what data are possible", not a research question. Formal modeling, causal inference, cross-country regressions and
paper drafting are **Phase B**, gated behind a data audit and a literature gap analysis (section 12; owner decision,
guidance in [the realignment note](../../../notes/01_compound-shocks-panel/review-gate/Pilot%20Scope%20Realignment%20-%20Exploratory%20Review%20Gate.md)).

## 2. Scope [Claude's call, needs owner decision]

The Somalia case-study note has three layers. **The pilot covers Layer 1 only**: the
district-month fused panel (prices, rainfall, conflict, displacement) and the descriptive
price decomposition, with district-level or coarser maps. Layers 2 and 3 (narrative collection, LLM
claim coding, claim lineage) are excluded: they are subscription-heavy, depend on a
different set of sources, and are not what the portability test needs. They become a later
module (the note already suggests folding claim-lineage into the Project 04 toolkit).
Cash-transfer data is also excluded: it is request-only and the protocol warns that
transfer presence is endogenous. No models, price decompositions, causal claims or cross-country regressions in Phase A; the work is
exploratory data analysis only, matching the case-study note ("causal identification deferred to the full Project 02
panel"). Phase B is gated (section 12).

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

### 4.1 Common core and country extensions (decided 2026-10-31)

The Sudan source check ([findings](../../../notes/01_compound-shocks-panel/data-sources/Sudan%20Data%20Sources%20-%20Portability%20Check.md), Gemini, unverified by Claude) showed the two countries cannot share every variable. So the
study design defines:

- **Common core panel**: variables available and defined the same way in both countries: conflict
  counts and fatalities (ACLED), monthly rainfall and anomalies (CHIRPS), staple cereal prices
  (sorghum, wheat/wheat flour; Sudan coverage is mostly 12 to 18 state capitals), all keyed by
  OCHA COD-AB Admin 2 p-codes and month.
- **Country extensions**: variables that exist in only one country or are defined differently.
  Displacement is the main one. Somalia (PRMN) is a monthly origin-destination **flow** with a
  reason; Sudan (IOM DTM) is mostly a **stock** with state-level origin, almost no reason variation
  after April 2023, and no continuous monthly series before it. Terms-of-trade measures need a casual
  wage and live-goat price that WFP Sudan does not publish, so they are Somalia-only.
- **Comparison rule** (Phase B, gated): any pooled or nested cross-country test uses the common core only, and
  displacement models run per country and are not pooled. Phase A builds both panels and marks columns `core` or
  `extension` but runs no cross-country tests. The displacement provider change is recorded in a harmonization
  record (flow vs stock, geography, reason categories, how any flow proxy such as first-differenced stock is built and
  its known biases: re-displacement, returnees).
- The panel schema marks each column `core` or `extension` so a run can state which columns the
  comparison used, and the manifest records it.

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

### 7.1 ACLED constraints (from the ACLED terms findings, Gemini reading of the 2025 EULA; not legal advice, not yet confirmed with ACLED)

- **Never commit** event-level rows or any subset. Raw files stay in the ignored `data/raw/`.
  Replicators register for their own account and fetch.
- **May commit**: district-month (or coarser) aggregates, figures and maps, synthetic fixtures with
  ACLED-style column names, and code that calls the API. Until ACLED answers the low-count question,
  committed aggregates use total counts and fatalities only, no per-event-type cells of 1 or 2.
- **Figures and maps** carry a visible caption: `Source: ACLED (acleddata.com), accessed <date>`.
- **Provenance**: the ACLED descriptor records access date, applied filters and the aggregation
  performed (now required fields on gated descriptors).
- **Rolling 12-month lag** on the Research Tier: Somalia 2021 to 2023 is fine; Sudan data ends about
  one year before today. A later replicator may receive a revised snapshot, so the expected-hash check
  is per access date, and a mismatch is reported as "provider revised data", not as an error.
- **Credentials** (account email and password) come from environment variables only, with an
  `.env.example`; secret scanning runs in CI.
- **AI services** (Claude's inference, to confirm with ACLED): raw ACLED rows must not be sent to
  external AI services or used to train or improve any model. The generated `AGENTS.md` and
  `agents.yaml` carry this rule for restricted-source data. Agents may work on aggregates and code.

## 8. Fixtures and tests

- `tests/fixtures/` is generated by a seeded script: roughly 3 districts and 12 months per role,
  with a deliberately missing market-month, a zero-displacement district-month, and a point on a
  district boundary. Schemas match the canonical tables.
- Tests: adapters map renamed columns; month assignment of events; point-in-polygon on a
  boundary point; zonal aggregation and `coverage_frac`; zeros vs missing preserved through
  the join; fused panel keys unique; the harmonization gate blocks a provider swap; the whole
  pipeline runs on fixtures in under a minute with no network.

## 9. Deliverables [Claude's call; revised by the Phase A realignment]

Fused district-month panels for Somalia and Sudan (CSV, regenerable), run manifests, EDA figures (missingness heatmaps,
raw market price series, conflict and rainfall trends, coarse district audit maps), and an **Exploratory Data Audit Memo**
per instance (provenance and access dates, hash checks, coverage and missingness findings, caveats for the research
design). No LaTeX paper, slides or web app in Phase A. Maps stay at district level or coarser (case-study ethics). Every
ACLED-derived figure carries `Source: ACLED (acleddata.com), accessed <date>`. Derived outputs from ACLED are not published
until its terms are checked (open item).

## 10. Sudan portability test (Phase A)

Changes `instances/sudan/config.yaml`, downloads and one structural harmonization record. The common core (4.1) is
portable: ACLED Sudan (from 1997, within the 12-month lag), CHIRPS (satellite-only after April 2023 because station feeds
collapsed), and OCHA COD-AB Sudan (19 Admin 1, 189 Admin 2 localities, p-codes `SD...`, CC BY 4.0, 2020 vintage per the
findings). WFP Sudan prices cover few markets and break down around May 2023, so the study window and missingness handling
are documented in the instance config and the record. Displacement (IOM DTM instead of PRMN) is the structural change and
needs the harmonization record described in 4.1; the Sudan displacement series is a country extension.

The portability test passes if the same code and manifest-recorded method produce a fused panel for Sudan, `reproduce
--instance sudan` succeeds, the harmonization record is complete, and the Sudan audit memo can be generated. **No regressions or
model comparisons** (deferred to Phase B). Findings about Sudan sources are Gemini's and unverified: the first Sudan task
re-checks the dataset IDs and fields against the actual downloaded files.

## 11. Open items for the owner

1. ~~Pilot scope~~ Decided 2026-10-31: Layer 1 only. Also decided: cross-country comparison uses the common core only (4.1).
2. ACLED terms: Gemini reads aggregates, figures, fixtures and API code as publishable and raw rows as not
   (section 7.1). Still open with ACLED: low-count cells, fixtures, and use with external AI services.
   The consultation email draft awaits the owner's decision to send.
3. ~~Boundary source and vintage~~ Decided by owner 2026-10-31: **OCHA COD-AB** per country,
   with **geoBoundaries** as fallback where COD-AB is missing or unusable. The vintage used is
   recorded in each instance's descriptor and manifest. License and Sudan COD-AB coverage still
   to be verified (Sudan sources prompt).
4. ~~Sudan sources~~ Gathered by Gemini (see 4.1 and 10); the Sudan window must end before the 12-month
   ACLED lag cutoff; exact window is a decision for the Sudan instance.
5. ~~Repo name / ACLED registration~~ `compound-shocks-panel` confirmed; ACLED registration done and a Somalia
   export (through 2025-10-31) is already in the ignored `data/raw/`.
6. Whether to send the ACLED consultation email (draft in the findings, section 3.3). On hold over the holiday weekend.
7. ~~Somalia window and CHIRPS version~~ Decided 2026-10-31: window 2021-01 to 2023-08 (the HDX PRMN dataset
   `somalia-internally-displaced-persons-idps` ends 2023-08; the dataset ID in the data-sources note is wrong),
   CHIRPS v2.0. Looking for a newer PRMN release (UNHCR portal or Microdata Library) is a non-blocking check.
8. Phase B (modeling and paper) is gated: it needs the data audit, a literature gap memo, and owner approval (section 12).

## 12. Phase B and the review gate (owner decision 2026-10-31)

Guidance: [Pilot Scope Realignment](../../../notes/01_compound-shocks-panel/review-gate/Pilot%20Scope%20Realignment%20-%20Exploratory%20Review%20Gate.md) (Gemini, reviewed by Claude). Phase A stops with the two audit memos. Before any
modeling the owner and agents run the **Review Gate**: (A) review the audit memos, including whether price gaps track
conflict intensity and whether Admin 2 aggregation hides or creates patterns; (B) a literature review and gap analysis (the
literature pipeline plus project notes) answering what is already published, what the contribution is, and which identification
strategy the observed data gaps allow; (C) owner approval of the research question, the modeling plan, and which deferred
components to reactivate.

**Deferred to Phase B, preserved in git history** (original text in `cbeb9ce6`; design in `29753f0a`, `b2bcb4a9`):
the imported-vs-local price basket decomposition (`price_index`, `price_decomposition`), the LaTeX paper build, pooled and
nested cross-country tests (`compare.nested_f_test`), and the framework design's deliverables, website communication hook and
audience derivatives (phases 13 to 16 of the framework design).
