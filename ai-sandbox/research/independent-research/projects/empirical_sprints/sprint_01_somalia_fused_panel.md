# Sprint 01 Planning Document: Somalia Fused Multi-Shock Panel & EDA

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Target Horizon:** Weeks 1–3 (Late October – Mid November 2026)
- **Status:** Detailed Empirical Specification
- **Deliverable Milestone:** Informal 30-Minute PhD Brownbag Presentation (Mid-November 2026) + 15-Page EDA Memo
- **Associated Codebase:** `ai-sandbox/research/independent-research/projects/04_data_fusion_toolkit/`

---

## 1. Objectives & Empirical Scope

This sprint builds the foundational multi-modal data pipeline for **Project 02 (Fused Subnational Multi-Shock Studies)** and the open-source **Project 04 (Analytics Toolkit)**. It grounds the abstract concept of "compounded crises" in a data-dense, highly volatile real-world setting: Somalia from 2018 to 2024.

### The Research Question for this Sprint:
> *Did the 2022 global grain price shock and 2021–2023 multi-season drought translate into forced displacement uniformly across Somalia, or did local armed conflict and market blockades act as severe non-linear multipliers?*

---

## 2. Data Resource Verification & Live Download Endpoints

Every required dataset exists as an accessible public or academic resource:

| Stream | Custodian | Live Endpoint / Access URL | Format & Temporal Scope | Key Extracted Variables |
| :--- | :--- | :--- | :--- | :--- |
| **Forced Displacement** | UNHCR / NRC PRMN | [HDX Somalia IDPs](https://data.humdata.org/dataset/somalia-internally-displaced-persons-idps) | CSV / XLSX; monthly, 2016–2024 (Continuous) | Number of individuals, reported reason (*drought, conflict, flood*), District of Origin $\to$ Destination. |
| **Market Commodity Prices** | WFP VAM & FAO FSNAU | [HDX WFP Food Prices Somalia](https://data.humdata.org/dataset/wfp-food-prices-for-somalia) | CSV; monthly, 1995–2024 (Continuous) | Retail prices (SOS/USD) of red sorghum, imported wheat, vegetable oil; Terms of Trade (TOT: goat/sorghum, labor/sorghum). |
| **Conflict Point Events** | ACLED | [acleddata.com](https://acleddata.com/data-export-tool/) (API / Direct Download via `.edu` license) | Daily event points; 1997–2024 (Weekly updates) | Exact coordinates, event type (*battles, violence against civilians*), actor identities (*Al-Shabaab, SNA*), fatalities. |
| **Continuous Rainfall Rasters** | UCSB CHIRPS | [CHIRPS Daily/Monthly FTP](https://data.chc.ucsb.edu/products/CHIRPS-2.0/) & [GEE `UCSB-CHG/CHIRPS/DAILY`](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY) | GeoTIFF / NetCDF; 0.05° (~5.3 km), 1981–present | Monthly precipitation depth (mm), long-term climatology, rainfall anomaly z-scores, SPI-3. |
| **Subnational Boundaries** | OCHA Somalia | [HDX COD-AB Somalia](https://data.humdata.org/dataset/ec140a63-5330-4376-a3df-c7ebf73cfc3c) | GeoJSON / Shapefile / Geodatabase | Admin 1 (18 regions) and Admin 2 boundaries with standardized P-codes. |

---

## 3. Academic Model Benchmark: Comparison to Existing Literature

### The Benchmark Model: Thalheimer, Schwarz, & Pretis (2023)
The gold-standard empirical model combining PRMN, ACLED, and climate data is **Lisa Thalheimer, Moritz P. Schwarz, and Felix Pretis (2023), *"Large weather and conflict effects on internal displacement in Somalia with little evidence of feedback onto conflict"*, published in *Global Environmental Change*** (Vol. 79, 102641).

* **What Thalheimer et al. (2023) Did:**
  - Evaluated subnational internal displacement flows in Somalia from 2016 to 2018 using PRMN and ACLED.
  - Estimated panel distributed-lag models, finding that a 1°C monthly local temperature increase led to an eventual ~10-fold increase in displacement, while rainfall declines doubled IDP outflows.
  - Demonstrated that while weather and violence drive displacement, displacement did not trigger new conflict outbreaks.
* **The Four Major Gaps Our Sprint 01 Addresses:**
  1. *Expanded Temporal Horizon:* Thalheimer et al.'s analysis ended in 2018. We expand the series from **2018 through 2024**, covering the historic 2021–2023 five-season failed rains, the 2022 Ukraine grain blockade, and the major SNA/clan offensive against al-Shabaab.
  2. *The Missing Economic Mediator (Commodity Prices):* Thalheimer et al. modeled direct weather-to-migration elasticities, completely omitting food commodity prices, import reliance, and Terms of Trade. We introduce WFP market prices to test the *economic transmission mechanism*.
  3. *Adversarial Non-Linear Interactions:* Thalheimer et al. treated weather and conflict primarily as additive linear controls. We explicitly model **interaction effects** ($\text{Drought} \times \text{Conflict}$) to evaluate how military sieges amplify climate shocks.
  4. *Social Protection Mitigation:* We incorporate WFP/World Bank *Baxnaano* cash transfer rollout data to test whether emergency liquidity dampens distress displacement.

---

## 4. Methodological Pitfalls & Mitigation Strategies

### Pitfall 1: Administrative Boundary Drift (74 vs. 91 Districts)
- **The Issue:** Historical PRMN records, ACLED point geocoding, and WFP market listings often adhere to Somalia’s historical 74-district layout, whereas recent OCHA Common Operational Datasets (COD-AB) adopt a 91-district structure.
- **Mitigation:** Create an explicit, auditable crosswalk dictionary (`somalia_district_crosswalk.csv`) mapping the 91 modern polygons into the 74 stable historical district cores. All zonal raster statistics will be computed on these standardized 74 base units.

### Pitfall 2: Strategic Self-Reporting Bias in PRMN
- **The Issue:** PRMN enumerators record a primary "reason" for displacement (*drought, conflict, flood*). When emergency aid appeals are funded specifically for drought relief, fleeing households or local monitoring partners have a strong incentive to report "drought" rather than "conflict," and vice versa.
- **Mitigation:** Use **Total Net Displacement Outflows** as the primary, objective dependent variable. Treat the self-reported sub-categories strictly as secondary diagnostic checks, rather than assuming pure causal orthogonality between "drought" and "conflict" IDPs.

### Pitfall 3: Non-Random Market Price Missingness Under Al-Shabaab Control
- **The Issue:** WFP and FSNAU price monitors cannot safely enter rural territories under active al-Shabaab control (e.g., Middle Juba, rural Bay/Bakool), creating non-random missing price cells in the most insecure districts.
- **Mitigation:**
  - Audit missingness explicitly: code a binary indicator $MissingPrice_{it}$.
  - For primary regressions, impute rural market prices using **Inverse Distance Weighting (IDW)** along connected road corridors from the nearest monitored hub.
  - Substitute continuous satellite proxies (**VIIRS nighttime lights** and **MODIS NDVI vegetation anomalies**) that observe all districts equally regardless of ground security.

### Pitfall 4: Currency Fragmentation & Nominal Distortion
- **The Issue:** Somalia operates under multiple currency regimes: Somali Shilling (SOS) in Mogadishu and south-central, Somaliland Shilling (SLS) in the north, and USD-denominated mobile money (EVC Plus, Sahal). Inflation rates vary wildly across these currency zones.
- **Mitigation:** Avoid using raw nominal Somali Shillings. Instead, analyze:
  1. USD-converted prices using verified regional exchange rates from FSNAU.
  2. **Terms of Trade (TOT):** Ratio of local cereal price to daily unskilled casual labor wages, or ratio of local cereal price to the sale of one export-quality goat. Terms of Trade are unit-free, real purchasing-power measures that bypass currency distortions.

### Pitfall 5: Spatial Autocorrelation & Destination Contamination
- **The Issue:** When District A experiences drought and clashes, people flee to District B (e.g., Baidoa or Mogadishu). If District B receives massive aid and records high arrivals, a naive model might falsely associate aid with displacement.
- **Mitigation:** Exploit the dyadic structure of PRMN by isolating **District of Origin Outflows** ($Y_{it}^{\text{origin}}$) from **District of Destination Inflows** ($Y_{jt}^{\text{dest}}$). The regression models origin distress push factors, controlling for baseline origin population.

### Pitfall 6: Temporal Lag Structure Mismatch
- **The Issue:** Agricultural drought is a slow-onset cumulative process (building over months), whereas armed clashes and drone strikes trigger immediate flight within 48–72 hours.
- **Mitigation:** Specify distinct temporal lag structures:
  - *Climate Stress:* 3-month rolling Standardized Precipitation Index (SPI-3) and seasonal rainfall anomalies.
  - *Conflict Violence:* Contemporaneous and 1-month lagged ACLED event counts and battle fatalities.

---

## 5. Baseline Econometric Benchmark Specification

$$\ln(\text{DisplacementOutflows}_{it}) = \alpha_i + \gamma_t + \beta_1 \text{RainAnomaly}_{it} + \beta_2 \ln(\text{FoodPrice}_{it}) + \beta_3 \text{ConflictFatalities}_{it} + \beta_4 (\text{RainAnomaly}_{it} \times \text{ConflictFatalities}_{it}) + \varepsilon_{it}$$

- $\alpha_i$: District fixed effects (controlling for baseline geography, clan boundaries, distance to major transport corridors).
- $\gamma_t$: Year-month fixed effects (absorbing macroeconomic price shocks and national political milestones).
- $\beta_4$: The non-linear compound shock coefficient—testing whether local armed conflict exacerbates the displacement elasticity of drought.
- Standard errors clustered at the region (Admin 1) level to account for spatial autocorrelation across contiguous districts.

---

## 6. Execution Roadmap (Weeks 1–3)

- **Week 1 (Oct 21 – Oct 27): Data Ingestion & Boundary Crosswalk**
  - Download OCHA COD-AB boundaries, ACLED Somalia extract, WFP food price CSV, and PRMN IDP dataset.
  - Construct `somalia_district_crosswalk.csv` harmonizing P-codes.
  - Ingest CHIRPS monthly rasters for the Horn of Africa bounding box ($1.5^\circ\text{S} - 12.0^\circ\text{N}$, $40.5^\circ\text{E} - 51.5^\circ\text{E}$).
- **Week 2 (Oct 28 – Nov 03): Spatial Aggregation & Missingness Audit**
  - Execute zonal statistics on CHIRPS rasters per district.
  - Aggregate ACLED points to district-month counts.
  - Join WFP market price series and compute goat-to-sorghum Terms of Trade.
  - Generate missingness audit heatmap.
- **Week 3 (Nov 04 – Nov 12): Analysis, Regression & Presentation Deck**
  - Plot triple-shock timeline and displacement origin-destination vector maps.
  - Estimate baseline TWFE regressions with interaction terms.
  - Assemble the 15-slide presentation deck for the PhD student brownbag.
