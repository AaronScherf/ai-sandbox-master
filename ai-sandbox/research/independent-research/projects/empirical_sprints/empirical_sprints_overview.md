# Empirical Sprints Overview: De-Risking the PhD Research Pipeline

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Date:** October 2026
- **Status:** Planning Baseline — Fall 2026 First-Year Sprints
- **Associated Core Documents:**
  - `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/01_ground-truth-and-research-plan/Ground Truth - PhD Research Plan - 3R Revision.md`
  - `ai-sandbox/research/independent-research/projects/research_projects_plan_fall26 - 3R Revision.md`
  - `ai-sandbox/research/independent-research/notes/03_rct-transportability/Brainstorming Transcript - Transferability of Crisis Interventions.md`

---

## 1. Executive Summary & Purpose

This overview coordinates three tightly scoped, **2-to-4 week empirical sprint projects** designed for the first year of doctoral study. Rather than prematurely committing to high-dimensional Bayesian transportability architectures or complex causal-ML estimations, these sprints serve as **empirical proofs-of-concept**. 

Their primary objective is to de-risk the research pipeline by physically testing data availability, spatial resolution alignment, reporting missingness, and baseline econometric feasibility on real crisis data. The empirical findings from these sprints will determine which methodological branches to advance, how to structure dissertation working papers, and which faculty advisors to engage with concrete evidence.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ THE THREE-SPRINT INTEGRATION ARCHITECTURE                                                       │
│                                                                                                 │
│   [Sprint 01: Somalia Fused Multi-Shock Panel]                                                  │
│   • Multi-modal data fusion spine: ACLED + CHIRPS + WFP Prices + PRMN Displacement.             │
│   • Establishes district-month harmonization and missingness bounds.                            │
│   • Direct Deliverable: November PhD Brownbag presentation & 15-page EDA memo.                  │
│                             │                                                                   │
│             ┌───────────────┴────────────────┐                                                  │
│             ▼                                ▼                                                  │
│   [Sprint 02: Geospatial Matcher Pilot]    [Sprint 03: Market Price Transmission]               │
│   • Geocodes 15–20 benchmark RCTs.         • Tests spatial price wedges across 40 markets.      │
│   • Builds satellite feature store.        • Measures corridor conflict & checkpoint friction.  │
│   • Evaluates cross-border overlap.        • Verifies the core market supply failure mode.      │
│   • Informs: Daniel Björkegren &           • Informs: Eric Verhoogen &                          │
│     Jack Willis (Transportability/ML).       Suresh Naidu (Industrial/Market Econ).             │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Sprint Descriptions & Interlocking Logic

### Sprint 01: Somalia Fused Multi-Shock Data & EDA Sprint (Weeks 1–3)
- **Focus:** Build the foundational spatiotemporal data engine using Somalia (2018–2024) as the primary testbed.
- **Role in Pipeline:** Serves as the technical testbed for the **Project 04 (Data Fusion Toolkit)** codebase and the empirical backbone for **Project 02 (Somalia Three-Shock Study)**. It resolves geometry alignment, raster extraction, and missingness audits in a single data-dense geography.
- **Detailed Plan:** [`sprint_01_somalia_fused_panel.md`](file:///C:/Users/theaa/ai-sandbox-master/.worktrees/gemini-transferability-brainstorm/ai-sandbox/research/independent-research/projects/empirical_sprints/sprint_01_somalia_fused_panel.md)

### Sprint 02: Geospatial Evaluation Matcher Pilot (Weeks 4–6)
- **Focus:** Geocode 15–20 benchmark cash transfer and index insurance evaluations from 3ie and J-PAL across East Africa/Sahel, extracting objective satellite rasters and conflict buffers.
- **Role in Pipeline:** Empirically tests the central assumption of **RQ 3 (Empirical Transportability)**: whether Earth observation covariates exhibit sufficient common support across borders to predict out-of-sample program performance. Directly shapes **Project 01 (Evidence Map)** and **Project 03 (Transferability Working Paper)**.
- **Detailed Plan:** [`sprint_02_geospatial_evaluation_matcher.md`](file:///C:/Users/theaa/ai-sandbox-master/.worktrees/gemini-transferability-brainstorm/ai-sandbox/research/independent-research/projects/empirical_sprints/sprint_02_geospatial_evaluation_matcher.md)

### Sprint 03: Spatial Price Transmission & Checkpoint Blockade Pilot (Weeks 7–9)
- **Focus:** Analyze pairwise price differentials for imported wheat and local sorghum across 40+ market towns in Somalia or Yemen relative to road-network conflict events.
- **Role in Pipeline:** Econometrically tests the core assumption of **RQ 1**: that armed blockades render local supply inelastic, turning cash injections into local inflation rather than consumption smoothing. Provides micro-foundations for market modeling in Project 02 and Project 03.
- **Detailed Plan:** [`sprint_03_market_price_transmission.md`](file:///C:/Users/theaa/ai-sandbox-master/.worktrees/gemini-transferability-brainstorm/ai-sandbox/research/independent-research/projects/empirical_sprints/sprint_03_market_price_transmission.md)

---

## 3. Decision Signals & Contingency Trees

Each sprint is designed with explicit diagnostic thresholds. What we learn from the data directly guides the subsequent research design:

```
                                  [DATA INTEGRATION SIGNALS]
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      ▼                       ▼                       ▼
                [GREEN SIGNAL]          [YELLOW SIGNAL]          [RED SIGNAL]
             Clean spatial overlap   Localized missingness;    Total data severance
             and robust support.     high noise in conflict.   or severe bias.
                      │                       │                       │
                      ▼                       ▼                       ▼
             Scale to Double-ML      Deploy satellite proxies  Pivot to qualitative
             & Bayesian Transport.   & sensitivity bounds.     or macro-level models.
```

### Sprint 01 Diagnostic Signals (Somalia Fused Panel)
* **Green Signal:** District-month panel yields $>70\%$ complete records across key variables (WFP sorghum prices, ACLED clashes, CHIRPS rainfall, PRMN displacement). Standard panel fixed-effects produce statistically identifiable coefficients on interaction terms.
  - *Action:* Proceed directly to Double Machine Learning (`EconML`) for heterogeneous treatment effects and prepare the draft for the SusDev Spring Seminar.
* **Yellow Signal:** Severe missingness ($>50\%$) in market price feeds in al-Shabaab-controlled southern rural districts (e.g., Middle Juba), but satellite rasters (CHIRPS, VIIRS nightlights) and PRMN displacement are complete.
  - *Action:* Model missingness explicitly as an endogenous conflict outcome. Use VIIRS nightlights and agricultural vegetation anomalies (NDVI) as continuous proxies for economic collapse where price enumerators cannot travel.
* **Red Signal:** PRMN displacement reasons ("drought" vs. "conflict") exhibit heavy reporting contamination (respondents strategically misreporting causes to access specific aid pipelines), invalidating causal attribution.
  - *Action:* Abandon single-reason displacement attribution. Shift the dependent variable to total net displacement outflows, using exogenous international commodity shocks (Ukraine export bans) and rainfall anomalies to identify shock transmission.

### Sprint 02 Diagnostic Signals (Geospatial Evaluation Matcher)
* **Green Signal:** 3ie/J-PAL trial boundaries can be geocoded to subnational polygons or district clusters. Satellite raster features (precipitation z-scores, night lights, NDVI) show strong overlap across countries and explain $>20\%$ of the cross-study variance in cash transfer effect sizes.
  - *Action:* Scale to a full 100-study corpus. Formulate the flagship **Project 03** paper around the "Geospatial Evaluation Matcher" and approach Daniel Björkegren and Jack Willis.
* **Yellow Signal:** Study coordinates are only reported at coarse province (Admin 1) or national levels, blurring localized environmental signals.
  - *Action:* Restrict the matching pilot to a curated tier of 20 evaluations with published household GPS clusters or known district centroids; use spatial buffer sensitivity tests (10km vs. 25km vs. 50km).
* **Red Signal:** Cross-border covariate distributions show near-zero common support (e.g., conflict exposure in Somalia/Yemen is so extreme that it has zero overlap with peaceful evaluation sites in Kenya/Uganda).
  - *Action:* Reject naive out-of-sample matching. Pivot RQ 3 from direct covariate matching to **non-exchangeable Bayesian hierarchical modeling with explicit variance penalization**, bounding uncertainty rather than claiming point-estimate transferability.

### Sprint 03 Diagnostic Signals (Market Price Transmission)
* **Green Signal:** Pairwise spatial price gaps correlate significantly with corridor conflict events; the spatial Law of One Price breaks down in contested corridors.
  - *Action:* Formalize the market friction paper as a standalone applied economics contribution. Present to Eric Verhoogen and Suresh Naidu.
* **Yellow Signal:** Price dispersion is dominated by exchange rate volatility (dual currency regimes: SOS vs. Somaliland Shilling vs. USD mobile money) rather than physical roadblocks.
  - *Action:* Re-denominate all commodity prices in USD or grams of gold; introduce regional currency fixed effects into the spatial dyadic regression.
* **Red Signal:** Conflict events have no observable impact on price transmission because traders rely on informal negotiations, clan protection, or maritime bypass routes.
  - *Action:* Revise RQ 1: cash transfers fail not because goods are physically blocked, but because of monopolistic markups or liquidity capture by local merchant cartels.

---

## 4. Timeline & Milestone Calendar (Fall 2026)

| Week | Window | Focus & Milestones | Primary Deliverable |
| :---: | :--- | :--- | :--- |
| **W1–W2** | Oct 21 – Nov 04 | **Sprint 01:** Ingest ACLED, CHIRPS, WFP, PRMN into Python. Run spatial joins and missingness audit. | Harmonized district-month dataset (`.parquet`). |
| **W3** | Nov 05 – Nov 18 | **Sprint 01:** Plot shock timelines, map displacement corridors, estimate baseline TWFE models. | **PhD Brownbag Presentation Slides & 15-page EDA Memo.** |
| **W4–W5** | Nov 19 – Dec 02 | **Sprint 02:** Screen and geocode 20 3ie/J-PAL RCTs; extract satellite raster buffers. | Geocoded evaluation feature store. |
| **W6** | Dec 03 – Dec 15 | **Sprint 02:** Test covariate overlap, run meta-regression, evaluate transferability signal. | Methodological pilot note for Björkegren/Willis. |
| **Recess** | Dec 15 – Jan 10 | **Winter Break Sprint:** Consolidate findings into first draft of Project 03 working paper. | Project 03 Working Paper Draft. |
| **W7–W8** | Jan 11 – Jan 25 | **Sprint 03:** Construct road network graph, calculate price wedges, estimate conflict friction models. | Market transmission working note for Verhoogen/Naidu. |
