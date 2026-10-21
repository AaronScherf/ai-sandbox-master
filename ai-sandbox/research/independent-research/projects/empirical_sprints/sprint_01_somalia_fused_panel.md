# Sprint 01 Planning Document: Somalia Fused Multi-Shock Panel & EDA

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Target Horizon:** Weeks 1–3 (Late October – Mid November 2026)
- **Status:** Ready for Execution
- **Deliverable Milestone:** Informal 30-Minute PhD Brownbag Presentation (Mid-November 2026) + 15-Page EDA Memo
- **Associated Codebase:** `ai-sandbox/research/independent-research/projects/04_data_fusion_toolkit/`

---

## 1. Objectives & Empirical Scope

This sprint builds the foundational multi-modal data pipeline for **Project 02 (Fused Subnational Multi-Shock Studies)** and the open-source **Project 04 (Analytics Toolkit)**. It grounds the abstract concept of "compounded crises" in a data-dense, highly volatile real-world setting: Somalia from 2018 to 2024.

### The Research Question for this Sprint:
> *Did the 2022 global grain price shock and 2021–2023 multi-season drought translate into forced displacement uniformly across Somalia, or did local armed conflict and market blockades act as severe non-linear multipliers?*

---

## 2. Data Ingestion Architecture & Sources

| Stream | Custodian | Format & Frequency | Spatial Resolution | Key Variables Extracted |
| :--- | :--- | :--- | :--- | :--- |
| **Conflict Point Events** | ACLED | Point events, daily (API / CSV) | Lat / Lon coordinates | Event type (*battles, violence against civilians*), fatalities, actor types (*Al-Shabaab, SNA*). |
| **Continuous Climate Rasters** | UCSB CHIRPS | Gridded raster (`.tif`), monthly | 0.05° (~5.3 km) | Monthly precipitation depth (mm), long-term climatology, rainfall anomaly z-scores, SPI-3. |
| **Market Commodity Prices** | WFP VAM & FAO FSNAU | Tabular time series, monthly (HDX) | 40+ market towns | Retail prices (SOS/USD) of imported wheat, red sorghum, vegetable oil, goat-to-cereal Terms of Trade (TOT). |
| **Forced Displacement** | UNHCR & NRC PRMN | Tabular event aggregates, monthly | Origin Admin 2 $\to$ Destination Admin 2 | Displaced individuals, self-reported reason (*drought, conflict, flooding*), IDP flow vectors. |
| **Boundary Polygons** | OCHA Somalia | GeoJSON / Shapefile | 74 Admin-2 Districts | Standardized administrative boundaries and district centroids. |

---

## 3. Data Engineering & Harmonization Steps

1. **Geometry Alignment & Master Spatial Spine:**
   - Define master panel index: 74 districts $\times$ 84 months (Jan 2018 – Dec 2024) = 6,216 district-month observations.
   - Clean and harmonize district naming conventions across datasets (resolving discrepancies between OCHA P-codes, ACLED district names, and PRMN spellings).
2. **Spatial Aggregation:**
   - *ACLED:* Perform spatial point-in-polygon overlay against district boundaries to aggregate total monthly conflict events, battle counts, and reported fatalities.
   - *CHIRPS:* Execute zonal statistics (`rasterio` / `exactextract`) to compute mean monthly rainfall and standardized precipitation anomalies for each district polygon.
   - *WFP/FSNAU:* Assign market price points to their parent district; for districts lacking a monitored market, construct inverse-distance-weighted (IDW) spatial price interpolations along primary road corridors.
   - *PRMN:* Aggregate origin-district displacement outflows ($Y_{it}^{\text{out}}$) and destination-district IDP inflows ($Y_{it}^{\text{in}}$).
3. **Missingness & Conflict Bias Audit:**
   - Map missing market price series across time and space.
   - Quantify whether missingness systematically clusters in al-Shabaab-controlled districts (e.g., Middle Juba, parts of Bay/Bakool).
   - Flag districts requiring satellite proxy substitution (e.g., VIIRS nightlights or NDVI).

---

## 4. Exploratory Data Analysis (EDA) Targets & Visualizations

The sprint deliverable will feature four core visual and analytical components:
1. **The Triple-Shock Timeline (2018–2024):**
   - High-frequency time-series overlaying the national timeline of:
     - (a) Rainfall deficit (failed Gu/Deyr rains),
     - (b) Global wheat/oil price spikes (Ukraine invasion onset, Feb 2022),
     - (c) Escalation of military offensive against al-Shabaab (August 2022).
2. **Spatial Displacement Choropleths:**
   - Subnational heatmaps comparing districts of origin for drought-reported displacement versus conflict-reported displacement.
3. **Market Price Disconnection Maps:**
   - Spatial visualization showing the divergence in food prices between coastal port markets (Mogadishu, Berbera) and besieged inland markets (Baidoa, Qansax Dheere).
4. **Correlation & Scatter Matrices:**
   - Bivariate relationships between local conflict intensity, rainfall deficits, and net displacement outflows.

---

## 5. Baseline Econometric Benchmark (Proof of Concept)

Before attempting Double Machine Learning or Bayesian transportability, estimate a transparent **Two-Way Fixed Effects (TWFE)** panel regression:

$$\text{Displacement}_{it} = \alpha_i + \gamma_t + \beta_1 \text{RainAnomaly}_{it} + \beta_2 \text{FoodPrice}_{it} + \beta_3 \text{Conflict}_{it} + \beta_4 (\text{RainAnomaly}_{it} \times \text{Conflict}_{it}) + \varepsilon_{it}$$

- $\alpha_i$: District fixed effects (controlling for baseline geography, clan composition, distance to coast).
- $\gamma_t$: Year-month fixed effects (controlling for macroeconomic inflation and national political cycles).
- $\beta_4$: Tests whether local armed conflict magnifies the displacement effect of an environmental shock.

---

## 6. Brownbag Presentation Deliverable

- **Format:** 30-minute slide deck (15 slides) + Jupyter Notebook replication artifact.
- **Audience:** First-year Sustainable Development PhD cohort and faculty mentors.
- **Narrative Arc:**
  1. *The Puzzle:* Famine was averted in Somalia in 2022, but 1.4 million people fled. Why?
  2. *The Data Fusion Innovation:* How combining ACLED, CHIRPS, and WFP prices produces subnational visibility where surveys fail.
  3. *Empirical Findings:* Initial TWFE interaction results and spatial price wedges.
  4. *The Pitch:* How this empirical engine scales into the broader 3R dissertation agenda.
