# Data Sources for Climate, Forced Displacement, Cash Transfers, and Conflict Research

**Author:** Antigravity (Gemini Operator)  
**Date:** October 2026  
**Focus Projects:** Project 01 (Evidence Map), Project 02 (Fused Panel Study & Somalia Case Study), Project 03 (Chatbot Survey Pilot), Project 04 (Data Fusion Toolkit), and Project 06 (Math Thesis Residual Validation)  
**Associated Documents:**  
- `ai-sandbox/research/independent-research/projects/research_projects_plan_fall26.md`  
- `ai-sandbox/research/independent-research/notes/Ground Truth - PhD Research Plan.md`  
- `ai-sandbox/research/independent-research/notes/Somalia Three-Shock Case Study.md`

---

## Executive Summary & Research Agenda Alignment

Across the research planning memos (`research_projects_plan_fall26.md`, `Ground Truth - PhD Research Plan.md`, and `Somalia Three-Shock Case Study.md`), your PhD research program centers on an overarching empirical and theoretical throughline:

> **The Flagship Question:** *Does investment in climate-adaptive resilience (specifically cash transfers, social protection, and digital risk infrastructure) reduce the probability that a climate shock becomes a forced displacement event, and does that relationship change—or break down—once conditioned on active, violent conflict?*

This question bridges four traditionally siloed literatures:
1. **Climate Shocks:** Slow-onset (multi-season droughts, soil moisture deficits, evaporative stress) and rapid-onset (flash floods, extreme heat).
2. **Forced Displacement:** Distinguishing distress migration, internal displacement (IDP stocks/flows), and refugee movements from routine labor mobility.
3. **Cash Transfers & Social Protection:** Evaluating how unconditional cash, cash-for-work, mobile money safety nets, and index insurance alter household coping strategies in fragile states.
4. **Conflict & Insecurity:** Accounting for armed actor contestation, violence against civilians, infrastructure disruption, and access blockades.

### Project-by-Project Data Requirements

| Project | Core Empirical Focus | Primary Data Requirements | Key Output / Deliverable |
|---|---|---|---|
| **Project 01: Evidence Map** | Systematic catalogue of existing RCTs and quasi-experiments at the climate × cash × conflict intersection | Evaluation registries (3ie, J-PAL, CEGA, Campbell), publication metadata, effect sizes, risk-of-bias scores | Public interactive catalogue / dashboard + literature gap memo (Nov 2026) |
| **Project 02: Fused Subnational Panel Study** | Econometric panel testing how climate shocks translate into displacement conditional on conflict intensity and cash transfer presence | Harmonized district-month panel fusing conflict events, displacement flows, gridded drought indices, and cash program locations | First draft (Nov 2026), full paper and SusDev seminar presentation (April 2027) |
| **Somalia Three-Shock Case Study (Project 02 Anchor)** | Proof-of-concept separating Ukraine war grain-import price shock, Horn of Africa drought, and al-Shabaab insurgency (2021–2023) | Market price series (imported vs domestic), PRMN displacement by cause, CHIRPS/SPEI rainfall, ACLED events, trade shipments | Case study report, price decomposition charts, narrative verification lineage map |
| **Project 03: Chatbot Survey Pilot** | High-frequency survey methods pilot (n ≈ 50–150) in access-constrained settings comparing LLM-administered vs structured surveys | Micro-level household survey baselines, sampling frames from humanitarian partners, validation against administrative data | Methods paper and IRB protocol (submitted Jan 2027, pilot Feb 2027) |
| **Project 04: Data-Fusion Toolkit** | Reusable open-source Python library for spatiotemporal aggregation and harmonization | Standardized schemas for raster climate grids, point conflict coordinates, and polygon administrative units | Documented Python package on GitHub (Jan 2027) |
| **Project 06: Math Thesis Revision** | Asymmetric-aware omnibus normality test applied to high-dimensional predictive residuals | Residual series from Project 02/04 panel and causal-ML models (heavy-tailed, skewed distributions) | Revised thesis manuscript + empirical validation memo (Jan–Feb 2027) |

---

## Methodological & Data-Fusion Challenges in Fragile Settings

Operating at the intersection of climate, conflict, and displacement presents unique empirical pitfalls that the data pipeline must address:

1. **Spatiotemporal Granularity Misalignment:**
   - Climate data are continuous spatial rasters (e.g., CHIRPS 0.05° grid, ~5.3 km) at daily, dekadal, or monthly scales.
   - Conflict events (ACLED) are discrete point occurrences (lat/lon coordinates, exact timestamp).
   - Displacement data (IDMC, PRMN) are aggregate polygon figures, typically reported at administrative unit levels (Admin 1 / Region or Admin 2 / District) on a monthly or event-driven basis.
   - Humanitarian cash programming is often recorded at distribution sites or settlement clusters with irregular reporting intervals.
   - *Requirement:* Standardized zonal statistics and spatial buffer methods implemented in the Project 04 pipeline to prevent spatial aggregation bias (the Modifiable Areal Unit Problem, MAUP).

2. **Reporting Bias and Missingness Under Armed Contestation:**
   - In insurgent-controlled zones (e.g., al-Shabaab strongholds in south-central Somalia), market price enumerators and displacement monitors cannot operate safely.
   - Cell phone towers may be sabotaged or monitored, compromising mobile phone records and remote survey reach.
   - *Requirement:* Explicit missingness modeling, sensitivity tests against remote sensing proxies (e.g., VIIRS nighttime lights, NDVI), and bounding analyses.

3. **Causal Endogeneity and Triangulation:**
   - Conflict affects local rainfall reporting (stations go offline), and drought can exacerbate local resource conflict over grazing rights and wells.
   - In displacement tracking, enumerators often categorize a movement under a single "primary reason" (e.g., "drought" vs "conflict"), masking the reality that drought depleted assets while conflict cut off aid, together forcing departure.
   - *Requirement:* Exploiting exogenous temporal shocks (e.g., international Black Sea shipping blockades) and spatial variations in rainfall anomalies to instrument for local food prices and agricultural stress.

---

## In-Depth Analysis of Promising Datasets

Below are seven in-depth dataset evaluations meeting your research requirements, all accessible either publicly or via standard academic data request protocols.

---

### 1. UNHCR / NRC Protection & Return Monitoring Network (PRMN) Somalia

* **Custodian / Host:** United Nations High Commissioner for Refugees (UNHCR) & Norwegian Refugee Council (NRC).
* **Access Modality:**
  - *Public:* Aggregated monthly and weekly district-level displacement and return datasets are publicly downloadable on the [Humanitarian Data Exchange (HDX)](https://data.humdata.org/dataset/unhcr-somalia-prmn-displacement-and-return-events) and the UNHCR Operational Data Portal.
  - *By Request:* Detailed event-level microdata and anonymized household protection profiling are available for research through the [UNHCR Microdata Library](https://microdata.unhcr.org/).
* **Spatial & Temporal Resolution:**
  - *Spatial:* District of departure (Origin Admin 2) to District of arrival (Destination Admin 2), georeferenced settlements/camps.
  - *Temporal:* Monthly, weekly, and event-level aggregates; continuous coverage from 2006 to present.
* **Key Variables:**
  - `Number of Individuals` displaced / returning.
  - `Reason for Displacement` (categorized into: *Drought*, *Conflict/Insecurity*, *Flooding*, *Other/Eviction*).
  - `District of Origin` vs `District of Destination`.
  - `Vulnerability Indicators` (unaccompanied minors, female-headed households, elderly).
* **Methodological Strengths:**
  - Uniquely allows empirical disentanglement of *conflict-induced* vs *climate-induced* displacement flows between the exact same origin-destination pairs over time.
  - Granular enough to observe directional flight (e.g., rural Bay/Bakool districts into urban Baidoa or Mogadishu peripheral camps).
* **Known Limitations & Biases:**
  - Self-reported reason: Respondents entering an aid distribution hub may report "drought" if food aid is currently being distributed for drought relief, or "conflict" if physical safety is the immediate priority.
  - Does not capture self-settled IDPs who blend into host community relatives without approaching formal monitoring transit nodes.
* **Alignment with Projects:**
  - **Somalia Three-Shock Case Study:** Serves as the dependent variable series for Sub-question 2 (Attribution).
  - **Project 02:** Forms the primary subnational outcome metric ($Y_{it}$ = net displaced outflows/inflows per district-month).

---

### 2. Armed Conflict Location & Event Data Project (ACLED)

* **Custodian / Host:** ACLED (acleddata.com).
* **Access Modality:**
  - *Public / Academic License:* Free academic API access and direct web downloads upon registering with an institutional email (Columbia University `.edu`).
  - *Python Client:* Easily queried via python libraries (`requests` or `acled` wrapper).
* **Spatial & Temporal Resolution:**
  - *Spatial:* Exact geographic point coordinates (latitude / longitude) and Admin 1/Admin 2/Admin 3 assignments.
  - *Temporal:* Daily event level; coverage from 1997 to present with weekly real-time updates.
* **Key Variables:**
  - `event_type`: *Battles*, *Explosions/Remote violence*, *Violence against civilians*, *Protests*, *Riots*, *Strategic developments*.
  - `sub_event_type`: *Armed clash*, *Air/drone strike*, *Abduction/forced disappearance*, *Attack*, *Looting/property destruction*.
  - `actor1`, `actor2`: Specific armed groups (e.g., Al-Shabaab, Somali National Army, ATMIS/AMISOM, Clan Militias).
  - `fatalities`: Reported casualty counts per event.
  - `geo_precision`: Quality flag (1 = exact town/point, 2 = district centroid, 3 = regional centroid).
* **Methodological Strengths:**
  - High spatial precision enables buffer analysis around market towns, transit corridors, and IDP camp perimeters.
  - Categorization allows isolating *violence against civilians* (direct displacement push) from *remote territorial clashes* or *inter-clan disputes*.
* **Known Limitations & Biases:**
  - Media reporting bias: Events in urban centers or government-controlled zones are more readily reported than events deep in contested rural territory.
  - Fatality estimates vary significantly across sources; best used as binary/count exposure or intensity indices rather than exact casualty figures.
* **Alignment with Projects:**
  - **Project 02 & Somalia Case Study:** Provides the conditioning/moderating variable ($Conflict_{it}$) measuring the local security environment.
  - **Project 04:** Standard conflict ingestion component in the data-fusion toolkit.

---

### 3. CHIRPS & ERA5-Land (UCSB Climate Hazards Center & ECMWF Copernicus)

* **Custodian / Host:**
  - CHIRPS: Climate Hazards Center, University of California, Santa Barbara (UCSB).
  - ERA5-Land: European Centre for Medium-Range Weather Forecasts (ECMWF) Copernicus Climate Change Service.
* **Access Modality:**
  - *Public Open Access:* Fully open data.
  - *Access Methods:* Google Earth Engine (`UCSB-CHG/CHIRPS/DAILY`, `ECMWF/ERA5_LAND/HOURLY`), Climate Engine API, direct HTTP/FTP raster download (`.tif`, `.nc`), and Python `xarray` / `rasterio`.
* **Spatial & Temporal Resolution:**
  - *CHIRPS:* 0.05° (~5.3 km) spatial resolution; daily, pentad (5-day), dekad (10-day), and monthly; 1981 to present (near-real time updates).
  - *ERA5-Land:* 0.1° (~9 km) spatial resolution; hourly and monthly; 1950 to present.
* **Key Variables:**
  - *CHIRPS:* Precipitation depth (mm), long-term climatology, rainfall anomalies.
  - *ERA5-Land:* 2m air temperature, potential evaporation, total evaporation, volumetric soil water (layers 1 to 4: 0–7 cm, 7–28 cm, 28–100 cm, 100–289 cm), skin reservoir content.
  - *Derived Indices:* Standardized Precipitation Index (SPI-3, SPI-6), Standardized Precipitation-Evapotranspiration Index (SPEI), Consecutive Dry Days (CDD), rainy season onset delay (Gu and Deyr seasons in Somalia).
* **Methodological Strengths:**
  - CHIRPS blends satellite infrared estimates of cold cloud duration with sparse local meteorological stations, making it the most reliable rainfall product for East Africa and the Horn.
  - ERA5-Land adds the critical thermal/evapotranspiration dimension needed to differentiate agricultural drought (soil moisture deficit) from meteorological drought (rainfall failure).
* **Known Limitations & Biases:**
  - Complex terrain or coastal microclimates can introduce minor satellite retrieval artifacts.
  - Station blending depends on station density, which is inherently lower in conflict zones.
* **Alignment with Projects:**
  - **Project 02:** Generates the exogenous weather shock indicators ($ClimateShock_{it}$).
  - **Somalia Case Study:** Quantifies the 2021–2023 multi-season failed Gu and Deyr rains.
  - **Project 04:** Forms the core raster extraction and zonal statistics pipeline (aggregating grid cells into district-level time series).

---

### 4. WFP Global Food Prices Database & FAO/FSNAU Somalia Market Data

* **Custodian / Host:** World Food Programme (WFP) Vulnerability Analysis and Mapping (VAM) & Food and Agriculture Organization (FAO) Food Security and Nutrition Analysis Unit (FSNAU) Somalia.
* **Access Modality:**
  - *Public Open Access:* Downloadable via [HDX WFP Global Food Prices](https://data.humdata.org/dataset/wfp-food-prices) and the [FSNAU Data Portal](https://www.fsnau.org/sectors/markets).
  - *API:* WFP Dataviz / VAM API and HDX CKAN API.
* **Spatial & Temporal Resolution:**
  - *Spatial:* Market / town level (40+ monitored markets in Somalia, hundreds across East Africa/Sahel).
  - *Temporal:* Monthly and weekly; continuous series from 1998 to present.
* **Key Variables:**
  - Commodity prices (retail and wholesale) in local currency (SOS) and USD:
    - *Imported Staples:* Wheat flour, cooking/vegetable oil, imported rice, diesel fuel.
    - *Domestic Agro-pastoral Staples:* Red sorghum, white maize, cowpeas.
    - *Livestock:* Local quality goat, export goat, camel, cattle.
    - *Labor Rates:* Daily unskilled casual labor wage rate.
  - *Terms of Trade (TOT):*
    - Daily wage to cereal (kg of red sorghum purchased by one day's labor).
    - Local goat to cereal (kg of cereal purchased by the sale of one goat).
* **Methodological Strengths:**
  - **The Crucial Empirical Wedge:** Enables clean econometric identification between the *global import price shock* (Black Sea disruption spiking wheat flour and oil) and the *local agro-climatic drought shock* (depressing livestock prices, raising local cereal prices, collapsing terms of trade).
  - Terms of trade provides a direct proxy for the purchasing power and food access of vulnerable pastoral and agro-pastoral households before displacement occurs.
* **Known Limitations & Biases:**
  - Market access disruptions: During heavy fighting or al-Shabaab roadblocks, market enumerators cannot collect prices, creating non-random missingness.
  - Dual currency regimes (e.g., Somali Shilling vs Somaliland Shilling vs USD mobile money) require careful deflation and currency standardization.
* **Alignment with Projects:**
  - **Somalia Three-Shock Case Study:** Primary empirical data for Layer 1 price decomposition.
  - **Project 02:** Instrument/mediator showing how macro shocks translate into household economic stress.

---

### 5. WFP & OCHA Cash-Based Transfers (CBT) & Somalia Cash Working Group (CWG) Datasets

* **Custodian / Host:** WFP, OCHA, and the Inter-Agency Standing Committee (IASC) Somalia Cash Working Group (CWG).
* **Access Modality:**
  - *Public:* Monthly 3W/4W ("Who does What, Where, and When") datasets and Cash Transfer dashboards on [HDX Somalia Cash Working Group](https://data.humdata.org/organization/somalia-cash-working-group) and OCHA FTS.
  - *By Request:* Project-level transfer microdata (transfer size, mobile money disbursement logs, target criteria) available through academic data agreements with the WFP Research Assessment and Monitoring (RAM) unit or CWG coordinators.
* **Spatial & Temporal Resolution:**
  - *Spatial:* Admin 2 (district) and settlement/camp level.
  - *Temporal:* Monthly and quarterly; detailed reporting from 2017 to present (covering the massive scale-up of the World Bank/WFP *Baxnaano* safety net and emergency drought cash responses).
* **Key Variables:**
  - `Disbursement Modality`: *Unconditional Cash Transfers (UCT)*, *Cash-for-Work (CFW)*, *Mobile Money Transfers*, *Vouchers*.
  - `Transfer Value`: Transfer amount per household (USD/SOS).
  - `Beneficiary Counts`: Reached households and individuals, broken down by host community vs IDP status.
  - `Targeting Mechanism`: Shock-responsive social safety net vs emergency humanitarian response.
* **Methodological Strengths:**
  - Provides the essential moderating variable to evaluate whether social protection dampens the shock-to-displacement transmission channel.
  - Captures the exact delivery modality (e.g., mobile money via Hormuud EVC Plus vs physical vouchers), allowing analysis of delivery mechanisms in insecure settings.
* **Known Limitations & Biases:**
  - Program placement endogeneity: Cash transfers are intentionally routed to districts experiencing severe distress, requiring careful identification (e.g., rollout timing, eligibility cutoffs, or shift-share instruments).
  - 3W data reflects planned/reported distributions, which may differ from actual realized transfers if security blockades prevent disbursement.
* **Alignment with Projects:**
  - **Project 02:** Direct empirical measure of social protection presence ($CashTransfers_{it}$).
  - **Project 01:** Anchors the cash transfer classification taxonomy for the Evidence Map.

---

### 6. World Bank Microdata Library: Somalia High Frequency Survey (SHFS) & LSMS-ISA

* **Custodian / Host:** The World Bank Development Data Group & UNHCR-World Bank Joint Data Center (JDC) on Forced Displacement.
* **Access Modality:**
  - *Public / Direct Academic Request:* Public-use files and licensed microdata available via the [World Bank Microdata Catalog](https://microdata.worldbank.org/) and [Somalia Integrated Household Budget Survey (SIHBS 2022)](https://microdata.worldbank.org/index.php/catalog/5607).
  - *Approval Timeline:* Typically 2–5 business days for academic researchers.
* **Spatial & Temporal Resolution:**
  - *Spatial:* Georeferenced household clusters (with standard GPS jittering for privacy), Admin 1/Admin 2 stratification (urban, rural, IDP settlements).
  - *Temporal:* Wave 1 (2016), Wave 2 (2017–2018), SIHBS (2022), and ongoing high-frequency monitoring rounds.
* **Key Variables:**
  - Household consumption, food expenditure share, and poverty headcount.
  - Receipt of cash transfers, humanitarian assistance, and diaspora remittances (including mobile money usage).
  - Self-reported exposure to drought, flood, conflict, and economic shocks over preceding 12 months.
  - Coping strategies (asset sales, skipping meals, migration of family members).
  - Displacement status: Non-displaced host vs IDP living inside camp vs IDP living in host community.
* **Methodological Strengths:**
  - Supplies the household-level microeconomic mechanisms that macro district panels cannot directly observe.
  - Provides empirical distributions of household vulnerability, consumption, and financial access to ground the synthetic counterfactuals in Project 03.
* **Known Limitations & Biases:**
  - Insecure rural districts under armed group control were omitted or sampled via remote/phone protocols, creating sample truncation.
  - Cross-sectional rounds with limited true panel household tracking.
* **Alignment with Projects:**
  - **Project 03 (Chatbot Survey Pilot):** Ground truth for question design, testing whether chatbot-elicited qualitative answers match household survey indicators.
  - **Direction I & II:** Provides micro-evidence on digital credit/insurance feasibility in fragile contexts.

---

### 7. 3ie Development Evidence Portal (DEP) & J-PAL / CEGA Registries

* **Custodian / Host:** International Initiative for Impact Evaluation (3ie), Abdul Latif Jameel Poverty Action Lab (J-PAL), and Center for Effective Global Action (CEGA).
* **Access Modality:**
  - *Public Open Access:* Free API and web repository at [developmentevidence.3ieimpact.org](https://developmentevidence.3ieimpact.org) and J-PAL Evaluation Database.
* **Spatial & Temporal Resolution:**
  - *Spatial:* Global coverage (focused on low- and middle-income countries), geocoded to country and subnational implementation region.
  - *Temporal:* Over 11,000 impact evaluations and systematic reviews published from 1990 to present.
* **Key Variables:**
  - `Intervention Sector`: *Social Protection / Cash Transfers*, *Agriculture / Climate Adaptation*, *Peacebuilding / Conflict*.
  - `Methodology`: RCT, Difference-in-Differences, Regression Discontinuity, Instrumental Variables, Synthetic Controls.
  - `Outcome Measures`: Agricultural yield, food security, income, migration/displacement, social cohesion.
  - `Effect Sizes & Standard Errors`: Standardized normalized effect sizes for meta-analysis.
  - `Confidence / Risk of Bias Ratings`: Low, medium, or high risk of bias assessments.
* **Methodological Strengths:**
  - Structured, standardized metadata eliminates manual bibliographic scraping.
  - Enables immediate filtering of studies that evaluate cash transfers specifically within conflict-affected or drought-prone regions.
* **Known Limitations & Biases:**
  - Publication bias toward statistically significant results in peer-reviewed literature.
  - Fragile/conflict contexts are historically underrepresented compared to stable development environments (e.g., Kenya, Uganda, Mexico).
* **Alignment with Projects:**
  - **Project 01 (Evidence Map):** The primary data foundation for cataloguing existing trials and drafting the "what's missing" memo in October–November 2026.
  - **Direction III:** Supplies the study pool and variance estimates for the hierarchical meta-analysis pipeline.

---

## Supplementary & Specialized Datasets

Beyond the seven core datasets above, three specialized sources directly support the multi-shock case study and narrative verification layer:

### A. UN Black Sea Grain Initiative (BSGI) Vessel Database & UN Comtrade
* **Host:** United Nations Joint Coordination Centre (JCC) & UN Statistics Division.
* **Details:** Contains vessel-by-vessel manifest records (departure date, port of origin in Ukraine, metric tons of wheat/corn/oil, destination country) from July 2022 through July 2023.
* **Research Utility:** Quantifies the exact timing and volume of grain shipments reaching East African ports (Mogadishu, Berbera, Djibouti), providing the macro import supply shock instrument for the Somalia Case Study.

### B. Integrated Food Security Phase Classification (IPC) Archives
* **Host:** IPC Global Support Unit (FAO/WFP/FEWS NET partnership).
* **Details:** Subnational acute food insecurity classifications (Phases 1 to 5: Minimal, Stressed, Crisis, Emergency, Famine) at Admin 1/Admin 2 level, published multiple times per year with historical data back to 2007.
* **Research Utility:** Crucial intermediate welfare outcome between climate/price shocks and displacement. Directly resolves the verification question in the Somalia case study: confirming that while Phase 5 Famine thresholds were projected in late 2022 for Baidoa and Burhakaba, formal famine declaration was averted through humanitarian cash scale-ups.

### C. GDELT Project & Media Cloud Narrative Archives
* **Host:** GDELT Project (GDELT 2.0 Global Knowledge Graph) & Media Cloud Consortium.
* **Details:** Monitors broadcast, print, and online news in over 100 languages, with automated entity extraction, sentiment scoring, and topic coding.
* **Research Utility:** Powers Layer 2 (Narratives) and Layer 3 (Verification) of the Somalia Case Study. Enables tracking Russian state media (RT/Sputnik Africa) vs Western press vs local Somali reporting (Hiiraan Online, Garowe Online) regarding the blamed cause of the food crisis (sanctions vs war blockade vs climate change).

---

## Cross-Dataset Synthesis & Architecture Matrix

| Dataset Name | Host / Custodian | Thematic Pillar | Access Protocol | Spatial Unit | Temporal Freq. | Primary Project Alignment |
|---|---|---|---|---|---|---|
| **UNHCR PRMN Somalia** | UNHCR & NRC | Displacement / Climate / Conflict | Open (HDX) / Request (Microdata) | Admin 2 (District) | Monthly / Weekly | Project 02 & Somalia Case Study |
| **ACLED** | ACLED | Conflict / Political Violence | Open Academic API / Portal | Point (Lat/Lon) | Daily | Project 02, 04 & Somalia Case Study |
| **CHIRPS & ERA5-Land** | UCSB CHC & ECMWF | Climate / Drought / Soil Moisture | Open Access (GEE, FTP, API) | 0.05° / 0.1° Raster | Daily / Dekadal / Monthly | Project 02, 04 & Somalia Case Study |
| **WFP / FSNAU Food Prices** | WFP VAM & FAO FSNAU | Market Prices / Import Shocks | Open Access (HDX, Portal) | Market / Settlement | Weekly / Monthly | Project 02 & Somalia Case Study |
| **WFP / OCHA Cash (CWG)** | WFP & OCHA | Cash Transfers / Social Safety Nets | Open (HDX) / Request (Microdata) | Admin 2 / Settlement | Monthly / Quarterly | Project 01, 02 & Direction I |
| **World Bank SHFS / LSMS** | World Bank & JDC | Household Welfare / Micro Resilience | Request (Microdata Library) | Household / Cluster | Multi-wave Panel | Project 03 & Direction I/II |
| **3ie Evidence Portal** | 3ie / J-PAL | Systematic Evaluations / Meta-Data | Open Access (API / Portal) | Study / Subnational | Continuous | Project 01 & Direction III |
| **UN BSGI & Comtrade** | UN JCC / UN Comtrade | International Trade Flows | Open Access (HDX / UN API) | Port / Country | Shipment / Monthly | Somalia Case Study (Shock 1) |
| **IPC Acute Food Insecurity** | IPC / FEWS NET | Food Insecurity / Welfare | Open Access (IPC Portal) | Admin 1 / Admin 2 | Triannual / Seasonal | Project 02 & Somalia Case Study |
| **GDELT / Media Cloud** | GDELT / Media Cloud | Narrative Claims / Media Discourse | Open Access (API / BigQuery) | Article / Sentence | Real-time / Daily | Somalia Case Study (Layers 2 & 3) |

---

## Recommended Data-Fusion Pipeline Architecture (Project 04)

```
[ Climate Rasters: CHIRPS / ERA5-Land ]
                  │
                  ▼ (Zonal Statistics: Area-Weighted Mean / SPI Calculation)
       ┌──────────────────────┐
       │ Admin 2 (District)   │ ◄── [ UNHCR PRMN Displacement Flows ]
       │ Month Panel: (i, t)  │ ◄── [ WFP / FSNAU Market Prices & TOT ]
       └──────────────────────┘ ◄── [ WFP / OCHA Cash Transfers (3W/4W) ]
                  ▲
                  │ (Spatial Aggregation / Point-in-Polygon & Buffers)
[ Point Events: ACLED Conflict Data ]
                  │
                  ▼
       ┌──────────────────────┐
       │ Fused Master Panel   │ ──► Project 02 Econometric Estimation:
       │ (Balanced / Unbalanced)    Y_it = β1(Climate_it) + β2(Conflict_it) +
       └──────────────────────┘            β3(Cash_it) + β4(Climate × Conflict) +
                  │                        β5(Climate × Cash) + α_i + γ_t + ε_it
                  ▼
       ┌──────────────────────┐
       │ Residual Vector      │ ──► Project 06 Math Thesis Revision:
       │ e_it = Y_it - Ŷ_it   │     Asymmetric-Aware Omnibus Normality Testing
       └──────────────────────┘
```

---

## Actionable Next Steps (October – December 2026)

1. **Immediate Data Ingestion (October 2026):**
   - Register for an ACLED Academic Account using Columbia credentials to obtain an API key.
   - Pull the complete UNHCR PRMN Somalia displacement dataset (2016–2024) from HDX to establish baseline district-level monthly inflows and outflows.
   - Download the FSNAU/WFP market price tables for Somalia (imported wheat flour, cooking oil, red sorghum, goat, labor wage) from HDX.
   - Query CHIRPS monthly rainfall rasters via Google Earth Engine for Somalia Admin 2 boundaries and compute SPI-3 / SPI-6 deviations.

2. **Case Study Proof-of-Concept (November 2026):**
   - Execute the 3-shock price decomposition (imported wheat flour vs local red sorghum vs goat-to-cereal terms of trade) across Bay, Bakool, Hiraan, and Mogadishu.
   - Align the BSGI shipment departure dates with local wheat flour price stabilization in late 2022 to verify the import price transmission lag.
   - Run the preliminary regression model for Project 02's first draft.

3. **Institutional Data Requests (November – December 2026):**
   - Submit a data access request to the World Bank Microdata Catalog for the Somalia High Frequency Survey (Waves 1 & 2) and SIHBS 2022 for household-level baseline parameters.
   - Request project-level cash disbursement microdata from the Somalia Cash Working Group / WFP RAM team to refine transfer values beyond aggregate 3W counts.

4. **Handoff to Residual Analysis (January 2027):**
   - Export regression residuals $\hat{\varepsilon}_{it}$ from the Project 02 panel models directly into the Project 06 repository (`math_thesis/rewrite/`) to validate the asymmetry-aware penalized-GLS normality test against empirical climate-conflict distributions.
