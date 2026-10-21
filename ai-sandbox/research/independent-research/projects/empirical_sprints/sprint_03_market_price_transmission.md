# Sprint 03 Planning Document: Spatial Price Transmission & Checkpoint Blockade Pilot

- **Author:** Aaron Scherf (with Antigravity / Gemini Operator)
- **Target Horizon:** Weeks 7–9 (January 2027 / Winter Break Sprint)
- **Status:** Ready for Execution Following Sprints 01 & 02
- **Deliverable Milestone:** Empirical Working Note on Market Segmentation Under Armed Conflict
- **Target Faculty Alignment:** Eric Verhoogen (Firm & Market Disruption) & Suresh Naidu (Political Economy & Labor)

---

## 1. Objectives & Empirical Scope

This sprint empirically tests the core economic mechanism underlying **RQ 1 (The Welfare, Market & Survival Frontier)**:
> *Under what conflict conditions does the spatial Law of One Price break down, and do armed checkpoints create severe local supply inelasticity that undermines cash transfers?*

While standard development economics assumes transport costs are passive and symmetric (e.g., road surface friction), armed conflict introduces **strategic, adversarial trade frictions**—military roadblocks, extortion tolls, insurgent ambushes, and siege tactics. This pilot evaluates whether conflict along trade corridors segments markets, driving localized food price spikes that turn cash aid into inflation.

---

## 2. Data Sources & Spatial Network Construction

| Data Stream | Source | Format | Variables & Purpose |
| :--- | :--- | :--- | :--- |
| **Commodity Prices** | WFP VAM & FAO FSNAU | Monthly tabular series (40+ markets) | Retail prices of imported wheat flour, local red sorghum, vegetable oil, and diesel fuel (SOS & USD). |
| **Road Network Graph** | OpenStreetMap (OSM) / HDX | Spatial vector lines (Shapefile / GeoJSON) | Primary and secondary transport corridors connecting regional port hubs to inland markets. |
| **Corridor Conflict Events** | ACLED | Point events (lat/lon, date) | Armed clashes, checkpoints, looting of goods, and ambushes along transit corridors. |

---

## 3. Spatial Network Construction & Dyadic Modeling

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ CORRIDOR CONFLICT & SPATIAL PRICE TRANSMISSION                                                  │
│                                                                                                 │
│  [Port / Central Hub] ───────────── Road Transit Corridor ────────────► [Inland Market]         │
│  Price: P_it (Imported Wheat)        ▲ Checkpoints / ACLED Clashes       Price: P_jt            │
│                                      │                                                          │
│  Pairwise Price Gap: |ln(P_it) - ln(P_jt)| = f(Distance_ij, Fuel_t, CorridorConflict_ijt)      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Constructing the Market Dyads:**
   - Define all pairwise combinations of monitored markets $(i, j)$ across Somalia (e.g., 40 markets $\implies \approx 780$ unique dyads per month).
   - Identify key import source hubs (e.g., Mogadishu, Berbera, Bossaso) and interior destination markets (e.g., Baidoa, Beletweyne, Qansax Dheere).
2. **Shortest-Path Corridor Routing:**
   - Using `networkx` or `osmnx`, compute the shortest road path along the OpenStreetMap highway network between market $i$ and market $j$.
   - Calculate road network distance ($Distance_{ij}$) versus straight-line Euclidean distance.
3. **Corridor Conflict Exposure Extraction:**
   - Generate a 5km buffer polygon around each shortest-path road corridor.
   - Count the number of ACLED conflict events ($ConflictEvents_{ijt}$) and reported fatalities occurring within that corridor buffer during month $t$.

---

## 4. Econometric Specification: Dyadic Price Wedge Regressions

Estimate the spatial price gap between market $i$ and market $j$ at month $t$:

$$\left| \ln(P_{it}) - \ln(P_{jt}) \right| = \alpha_{ij} + \gamma_t + \beta_1 \ln(\text{Distance}_{ij}) + \beta_2 \text{FuelPrice}_t + \beta_3 \text{CorridorConflict}_{ijt} + \varepsilon_{ijt}$$

- $| \ln(P_{it}) - \ln(P_{jt}) |$: Absolute percentage price wedge for staple food (imported wheat or domestic sorghum).
- $\alpha_{ij}$: Dyad fixed effects (controlling for permanent geographic friction, terrain, clan boundaries).
- $\gamma_t$: Year-month fixed effects (controlling for macroeconomic exchange rate shocks and national inflation).
- $\text{CorridorConflict}_{ijt}$: Conflict events along the connecting transit corridor.
- $\beta_3$: The key parameter of interest—measures the extent to which armed conflict along trade corridors increases spatial price dispersion and segments markets.

---

## 5. Deliverable & Faculty Alignment Pitch

- **Deliverable:** An 8–10 page empirical note with spatial network maps showing severed trade corridors, regression tables of spatial price wedges, and an analysis of where cash transfers risk triggering inflation versus where markets absorb liquidity smoothly.
- **Faculty Pitch Hook:**
  - **Eric Verhoogen (Economics / Firm & Market Disruption):** *"I am measuring spatial market integration and trade corridor frictions under armed conflict, showing how checkpoint extortion breaks spatial price transmission in fragile states."*
  - **Suresh Naidu (Economics / Political Economy):** *"I am testing how non-state armed actors extract rents along trade networks and how that alters the general equilibrium impacts of humanitarian cash injections."*
