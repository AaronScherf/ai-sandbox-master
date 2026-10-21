# Sprint 02 Planning Document: Geospatial Evaluation Matcher Pilot

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Target Horizon:** Weeks 4–6 (Late November – Mid December 2026)
- **Status:** Ready for Execution Following Sprint 01
- **Deliverable Milestone:** Methodological Working Note + Curated Geocoded Evaluation Feature Store
- **Target Faculty Alignment:** Daniel Björkegren (AI & Development) & Jack Willis (Economics / Risk & Insurance)

---

## 1. Objectives & Empirical Scope

This sprint empirically tests the core methodological assumption of **RQ 3 (Empirical Transportability & Covariate-Matching)**: 
> *Can objective, cross-border Earth observation rasters (satellite rainfall anomalies, vegetation health, nightlights) and conflict metrics replace fragmented household survey covariates to predict out-of-sample program transferability?*

Rather than starting with an unmanageable database of thousands of studies, this sprint builds an **empirical pilot on 15–20 benchmark evaluations** of emergency cash transfers and agricultural index insurance across East Africa and the Sahel.

---

## 2. Sample Selection: Benchmark Impact Evaluations

Select 15–20 rigorously evaluated randomized controlled trials (RCTs) or high-credibility quasi-experiments from the **3ie Development Evidence Portal** and **J-PAL Evaluation Database**, filtering for:
- **Intervention Class:** Unconditional Cash Transfers (UCT), Mobile Money Safety Nets, or Parametric Weather Index Insurance.
- **Geographic Focus:** Arid and semi-arid regions with varying conflict and climate stress (e.g., Kenya, Somalia, Ethiopia, Mali, Niger, Yemen).
- **Core Outcome:** Standardized normalized effect sizes on household consumption, food security, or agricultural asset preservation.

### Initial Seed Study Candidates:
1. *Kenya (GiveDirectly / Haushofer & Shapiro, 2016; Egger et al., 2022):* Unconditional cash transfers in rural Siaya / western Kenya (high data density, low conflict baseline).
2. *Somalia (World Bank / WFP Baxnaano Safety Net, 2020–2023):* Emergency shock-responsive mobile cash in drought/conflict-affected districts.
3. *Ethiopia (Tigray Emergency Cash / PSNP evaluations):* Productive Safety Net Programme cash-for-work during drought and regional instability.
4. *Mali (Tranchant et al., 2019 / Emergency Cash in Insecure Settings):* Unconditional cash transfers in conflict-affected northern/central Mali.
5. *Yemen (Schwab, 2020 / Emergency Cash):* Social Fund for Development (SFD) cash response during active conflict and blockade conditions.

---

## 3. Spatial Geocoding & Satellite Feature Extraction Pipeline

For each selected evaluation in the pilot corpus:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ TRIAL FEATURE EXTRACTION PIPELINE                                                               │
│                                                                                                 │
│  [Evaluation Record] ──► Extract Implementation Bounds (Polygons / District Centroids)          │
│                                      │                                                          │
│                                      ▼                                                          │
│  [Temporal Window]   ──► Match Evaluation Baseline & Endline Dates (e.g., May 2021 – Oct 2022)   │
│                                      │                                                          │
│                                      ▼                                                          │
│  [Earth Observation Extraction (5km/10km Zonal Means)]:                                         │
│   • CHIRPS Precipitation: Cumulative rainfall z-score & SPI-3 during trial period.              │
│   • MODIS / Landsat NDVI: Mean vegetation health anomaly relative to long-term baseline.        │
│   • VIIRS Nighttime Lights: Mean baseline radiance (proxy for electrification & wealth).        │
│   • ACLED Conflict Density: Total battle fatalities within a 25km buffer during trial window.   │
│   • OpenStreetMap Road Distance: Euclidean & road network distance to primary trading hub.      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Methodological Proof of Concept & Analyses

1. **Common Support & Overlap Diagnostic:**
   - Construct a standardized feature matrix $X_{s}$ for each study site $s \in \{1, \dots, 20\}$.
   - Compute pairwise **Mahalanobis distances** and **Propensity Overlap scores** between all pairs of study contexts.
   - *Diagnostic Question:* Does a crisis trial in Somalia or Mali share sufficient common support with a rural trial in Kenya or Ethiopia to make matching meaningful, or are the distributions completely disjoint?
2. **Satellite-Informed Meta-Regression:**
   - Estimate whether satellite-derived environmental stress and conflict exposure explain cross-study variation in reported effect sizes ($\hat{\tau}_s$):
     $$\hat{\tau}_s = \beta_0 + \beta_1 \text{RainfallAnomaly}_s + \beta_2 \text{ConflictDensity}_s + \beta_3 \text{NightLights}_s + \varepsilon_s$$
   - *Success Benchmark:* Check whether environmental and security covariates account for a meaningful fraction of cross-study heterogeneity ($R^2 > 0.15$).
3. **Leave-One-Trial-Out Cross-Validation (Proof of Concept):**
   - For each study $k$, fit a transportability predictor on the remaining $N-1$ studies and predict the directional sign and standardized magnitude of $\hat{\tau}_k$.
   - Evaluate whether spatial similarity weighting outperforms a simple unweighted historical average.

---

## 5. Deliverable & Faculty Alignment Pitch

- **Deliverable:** A tidy, open-source dataset (`evaluation_satellite_features.parquet`) + a 10-page methodological memo detailing the feature store and out-of-sample validation findings.
- **Faculty Pitch Hook:**
  - **Daniel Björkegren (SIPA / AI & Development):** *"I have constructed an Earth-observation feature store for 20 benchmark crisis RCTs to test distribution shift and evaluate whether causal effects can be transported out-of-sample across unstable environments."*
  - **Jack Willis (Economics):** *"I'm exploring how satellite-derived rainfall and drought indices can be coupled directly with evaluation databases to test index insurance and cash safety net transferability."*
