# Pilot Scope Realignment: Exploratory Review Gate & Preserved Research Plans

**Status:** Owner Decision & Architecture Guidance, 2026-10-31  
**Author:** Gemini (Review & Synthesis)  
**Audience:** Claude, Codex, and Project Owner  
**Applies to:**
- `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-project-02-pilot-design.md`
- `ai-sandbox/research/independent-research/docs/superpowers/plans/2026-10-31-compound-shocks-pilot-plan.md`
- `ai-sandbox/research/independent-research/docs/superpowers/specs/2026-10-31-reproducible-research-framework-design.md`

---

## 1. Executive Summary & Purpose

On 2026-10-31, the owner reviewed the trajectory of the research reproducibility pilot. The current plans for the `compound-shocks-panel` pilot ([Plan 2](<C:/Users/theaa/ai-sandbox-master/ai-sandbox/research/independent-research/docs/superpowers/plans/2026-10-31-compound-shocks-pilot-plan.md>)) expanded beyond testing data infrastructure into a full-scale automated research pipeline for **Project 02** (Somalia Compounded Shocks), pre-specifying economic basket decompositions, cross-country econometric hypothesis tests (nested $F$-tests on Sudan), and automated LaTeX paper compilation.

### The Owner's Decision
1. **Decouple Data Engineering from Econometric Modeling:** The project will proceed with data intake, cleaning, spatial harmonization, raster aggregation, panel fusion, and descriptive visualization to explore data quality and feasibility ("what is possible").
2. **Hold on Analysis and Hypothesis Testing:** Formal econometric modeling, price decomposition mechanisms, causal inference, cross-country regressions, and academic paper drafting are placed on hold.
3. **Establish an Explicit Review Gate:** Before any formal analysis or hypothesis phase begins, the project must pass through a two-part review gate:
   - **Part A (Data Audit):** Evaluate the actual fused panel (sparsity, missingness, measurement noise, and structural validity).
   - **Part B (Literature Gap & Novelty Analysis):** Conduct a systematic literature review and gap analysis to verify whether the proposed research question is a genuine, citable empirical contribution or merely replicating existing Horn of Africa / Sahel compound-shock analyses.
4. **Preserve All Prior Plans:** None of Claude's design ideas are lost. All existing plans, econometric formulas, and LaTeX drafting structures are cataloged and preserved in Git history and in this document for reactivation after the Review Gate clears.

---

## 2. Preservation of Prior Analytical Designs

To ensure zero loss of ideas, the previous analytical designs drafted by Claude are recorded below, with their exact commit provenance:

| Plan / Spec Component | Original Location & Git Commit | Preserved Analytical Concepts |
| :--- | :--- | :--- |
| **Project 02 Pilot Design** | `specs/2026-10-31-project-02-pilot-design.md` (`29753f0a`, `b2bcb4a9`, `cbeb9ce6`) | - Layer 1 descriptive price decomposition separating imported baskets (wheat flour, cooking oil) from domestic staples (sorghum, maize).<br>- District choropleth maps.<br>- Cross-country pooled comparison rule on common-core variables (ACLED conflict, CHIRPS rainfall, cereal prices). |
| **Compound Shocks Implementation Plan** | `plans/2026-10-31-compound-shocks-pilot-plan.md` (`cbeb9ce6`) | - **Task 11:** `price_index(prices, basket, base_month)` and `price_decomposition(prices, imported, local, base_month)`.<br>- **Task 12:** `report/main.tex` template populated by Jinja from manifest and figures, compiled via `latexmk`.<br>- **Task 15:** `compare.nested_f_test(panels, formula)` fitting pooled OLS and country-specific models to test parameter stability between Somalia and Sudan. |
| **Framework Master Design** | `specs/2026-10-31-reproducible-research-framework-design.md` (`60e4e057`) | - Phases 13–16: Deliverables builder (paper PDF, slides), website communication hook (`comms/`), and audience derivative generator (academic to public). |

These designs remain intact in Git history and can be reintroduced as modular extensions during Phase B once the research question is validated.

---

## 3. The Two-Phase Architecture: Explicit Boundaries

The work is split into two sequential phases separated by a mandatory human-in-the-loop review gate:

```
[ PHASE A: Data Exploration & Fusion ]
  ├── 1. Role Adapters (ACLED, COD-AB, CHIRPS, WFP, PRMN)
  ├── 2. Spatial Joins & Raster Zonal Aggregation
  ├── 3. Multi-Source Panel Fusion (Admin 2 x Month)
  ├── 4. Sudan Data Portability Verification (Pipeline only)
  └── 5. Exploratory Data Analysis (EDA) Profile & Visuals
             │
             ▼
========================================================================
[ MANDATORY GATE: Data Audit & Literature Gap Review ]
  ├── Part A: Empirical Data Feasibility Audit (Missingness & Noise)
  ├── Part B: Literature Novelty & Gap Analysis (via Literature Pipeline)
  └── Part C: Owner Approval of Research Question & Econometric Plan
========================================================================
             │
             ▼
[ PHASE B (GATED): Econometric Analysis & Paper Drafting ]
  ├── 1. Formal Econometric Modeling & Causal Identification
  ├── 2. Price Basket Decompositions & Hypothesis Testing
  ├── 3. Cross-Country Econometric Regressions (Somalia vs Sudan)
  └── 4. Academic Paper / LaTeX Report Compilation
```

---

## 4. Work Authorized in Phase A (Exploration & Engineering)

The following components from Plan 1 (`reprokit`) and Plan 2 (`compound-shocks-panel`) are **authorized to proceed**:

1. **`reprokit` Framework Core (Plan 1, Tasks 1–10):**
   - Standard schemas (`charter`, `descriptor`, `config`, `compute`, `agents`, `harmonization`, `manifest`).
   - Structural harmonization gating (`check_gate`) and SHA-256 run manifest builder.
   - Copier template for reproducible study repositories.
2. **Data Ingestion & Adapters (Plan 2, Tasks 4–8, 13):**
   - Scripted downloaders/adapters for WFP prices, UNHCR/PRMN displacement, OCHA COD-AB boundaries, and CHIRPS GeoTIFFs.
   - ACLED conflict adapter adhering to the 2025 EULA terms (no raw rows committed, totals only).
   - Point-in-polygon spatial join (`geopandas`) assigning conflict events to OCHA COD-AB Admin 2 districts.
   - Raster zonal aggregation (`rasterio`) computing district-month area-weighted precipitation means and spatial coverage fractions (`coverage_frac`).
3. **Panel Fusion (Plan 2, Tasks 9–10):**
   - Assembling the Admin 2 $\times$ Month panel for Somalia (2021-01 to 2023-08).
   - Strict tracking of structural zeroes (zero conflict events) versus true missingness (`NaN` for prices and displacement).
   - Orchestration via `doit` under `python -m compound_shocks reproduce --instance somalia`.
4. **Sudan Data Portability Check (Plan 2, Task 15 — Modified Scope):**
   - Testing whether the exact same adapter, boundary, and fusion code can ingest Sudan sources (OCHA COD-AB Sudan, CHIRPS, WFP Sudan, IOM DTM).
   - Implementing the IOM DTM adapter and drafting the structural harmonization record documenting the shift from flow (PRMN) to stock (IOM).
   - Output: a clean Sudan fused panel dataset. **No regressions or model comparisons.**
5. **Phase A Deliverables:**
   - Reproducible fused panels (`data/derived/panel.csv`) for Somalia and Sudan.
   - Cryptographic run manifests (`outputs/manifest.json`).
   - **Exploratory Data Analysis (EDA) Profile & Audit Report** (see Section 5 below).

---

## 5. Modifications Required for Claude's Implementation Plan

Claude and Codex should apply the following direct edits to [C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\docs\superpowers\plans\2026-10-31-compound-shocks-pilot-plan.md](<C:/Users/theaa/ai-sandbox-master/ai-sandbox/research/independent-research/docs/superpowers/plans/2026-10-31-compound-shocks-pilot-plan.md>):

### Task 11: Shift from "Analysis Defaults & Figures" to "Exploratory Data Analysis (EDA) & Diagnostics"
- **Remove:** `price_index`, `price_decomposition` baskets (`imported` vs `local`), and mechanism assertions.
- **Implement:**
  - `data_profile(panel: pd.DataFrame) -> dict`: Summary tables of non-null counts, zero counts, min/max dates, and unique districts per source.
  - `missingness_matrix(panel: pd.DataFrame, out: Path) -> None`: Temporal and spatial heatmaps showing missing data patterns (especially price series gaps across conflict-heavy districts).
  - `plot_commodity_series(prices: pd.DataFrame, out: Path) -> None`: Raw market-level price trends over time without normalized basket weighting.
  - `plot_conflict_rainfall_trends(panel: pd.DataFrame, out: Path) -> None`: Descriptive time-series of total monthly conflict events/fatalities and mean precipitation.
  - `make_district_audit_map(panel: pd.DataFrame, boundaries: gpd.GeoDataFrame, column: str, out: Path) -> None`: Coarse choropleths displaying event densities and rainfall anomalies.
- **Caption Requirement:** Retain visible attribution on all ACLED-derived figures: `Source: ACLED (acleddata.com), accessed <date>`.

### Task 12: Replace "Report Build" with "Exploratory Data Audit Memo"
- **Remove:** `report/main.tex` academic working paper generation and `latexmk` build targets.
- **Implement:**
  - A Markdown/HTML report generator (`build_audit_memo(instance_dir: Path) -> Path`) that compiles:
    1. Dataset provenance, access dates, and hash verifications.
    2. Missingness and data coverage findings (districts with zero markets, months with no displacement reports).
    3. Descriptive charts and maps from Task 11.
    4. Key empirical observations and caveats to inform the subsequent literature review and research design.

### Task 15: Strip Regressions from "Sudan Instance & Common-Core Comparison"
- **Remove:** `compare.nested_f_test` and all pooled OLS regressions.
- **Retain:**
  - Ingestion of Sudan data sources into `instances/sudan/data/raw/`.
  - `IomDtmAdapter` and first-differenced stock-flow conversion.
  - Formal harmonization record (`instances/sudan/harmonization/displacement.yaml`) explaining the conceptual break between PRMN flows and IOM stocks.
  - Generating `instances/sudan/data/derived/panel.csv` and its EDA audit memo.
  - Verifying that `compound_shocks reproduce --instance sudan` succeeds identically.

---

## 6. The Review Gate Requirements (Before Phase B)

Once Phase A is complete, all autonomous coding stops. The owner and agents will execute the following review steps before any modeling begins:

### Step 1: Empirical Feasibility & Data Audit
- Review the EDA audit memos for Somalia and Sudan.
- Evaluate whether price gaps correlate with conflict intensity (e.g., whether markets in al-Shabaab-controlled areas stop reporting, introducing severe survival/selection bias).
- Assess whether Admin 2 spatial aggregation obscures local conflict-drought dynamics or creates aggregation artifacts.

### Step 2: Comprehensive Literature Review & Gap Analysis
- Utilize the literature pipeline (`ai-sandbox/academic-rag-model/agent/literature/`) and project notes in `ai-sandbox/research/independent-research/notes/02_literature-and-evidence-map/Literature Pipeline - Early Prototype.md`.
- Search recent academic literature (OpenAlex, Semantic Scholar, NBER, CEPR, 3ie) for:
  - Existing empirical papers on Somalia's 2021–2023 crisis (drought, Ukraine food price shocks, and al-Shabaab conflict).
  - Studies examining the interaction of food import prices and localized climate shocks in East Africa.
  - Methodological papers addressing compound conflict-climate displacement attribution.
- **Deliverable:** A formal Literature Gap Memo addressing:
  1. *What has already been published?* (Are we duplicating an existing paper?)
  2. *What is the specific theoretical contribution?* (Does this advance Direction I of the PhD plan?)
  3. *What identification strategy is actually credible given the data gaps observed in Phase A?*

### Step 3: Owner Decision on Phase B Plan
- The project owner reviews the Data Audit and Literature Gap Memo.
- The owner formally approves:
  - The precise research question and core hypotheses.
  - The econometrics and identification strategy (e.g., fixed-effects specifications, instrumental variables, or descriptive decomposition).
  - Reactivation of preserved Plan 2 components (Tasks 11, 12, 15) with any necessary revisions.
