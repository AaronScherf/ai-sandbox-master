# Cross-Group Connections: RCT Replication & Transportability

*Group D (new; closest to Direction III and Project 03). File: `RCT_replication_gemini_brainstorm.md`. Written 2026-11-05. "(inference)" marks my own reading. The brainstorm's citations are Gemini output and I did not verify them.*

## What the brainstorm contains
A four-step design for taking a geocoded RCT (for example a cash-transfer trial) and extending it: (1) replicate; (2) add locality covariates and proxy outcomes such as night lights, NDVI and later displacement; (3) test whether proxies can detect the effect without panel survey data; (4) project impact to new locations by matching covariates and proxies. A companion idea pools several RCTs in a Bayesian hierarchical model with leave-one-site-out checks, and a separate note proposes ACLED/displacement as a forecast outcome. Gemini's reply maps these to DML, surrogate indices, LIML/Fuller, causal transportability, Meager-style shrinkage, JIVE, Bai-Ng factor models and FAVAR. The three questions Aaron then asked have not been answered.

## Where the same ideas already appear elsewhere

| Idea in the brainstorm | Where it already shows up | Note |
|---|---|---|
| DML / cross-fitting, hierarchical multi-trial pooling, Bayesian priors for out-of-sample prediction | Ground Truth original, Theme 04 and Direction III ("scaling pilots into national policy", modeled on CEGA's IDEAL); 3R Revision "Advanced Technical Identity" | The brainstorm is a concrete version of a stack the plans already commit to |
| Cash transfers as the intervention | Direction I (flagship), Project 01 evidence map, Project 03 | GiveDirectly and PROGRESA are named as the example trials |
| Satellite and night-light proxies for welfare | Data Sources (VIIRS, NDVI as sensitivity checks), Sudan Data Sources (NDVI and VIIRS in place of terms of trade) | Same data, different job: here as an outcome proxy for treatment effects |
| ACLED and displacement as a forecast target | Compound shocks panel (the panel contains these series) | The panel's dense columns are conflict and rainfall |
| Spillovers, measurement error, selection into observation | Data Audit Review (missing prices track programmes in Somalia, conflict in Sudan) | Same class of problem |
| Smooth global approximations missing sharp thresholds | `Research Ideas.docx` spectral-bias note | Relevant to DML nuisance models and to extrapolation under rare shocks |

## Connections by group

### Overview and strategy (A)
- Direction III in the original plan has no SIPA faculty anchor; the 3R plan names Björkegren (ML under distribution shift) for II and III. This brainstorm is the most direct candidate for a methods chapter he would care about (inference).
- Project 03 in the 3R plan is "disaster-to-conflict transferability" in the policy sense. The brainstorm's transportability is statistical (does an estimate move across sites?). A natural bridge: the policy paper's "failure modes" (reporting bias, targeting manipulation) are the violations of the brainstorm's unconfoundedness and overlap assumptions (inference).

### Compound shocks panel (B)
- Panel columns usable as covariates or proxies for Step 2: rainfall, conflict events, population (fixed vintage). Prices and displacement are too sparse for that role per the audit.
- The brainstorm's Step 3 asks whether proxies can stand in for missing survey outcomes. The panel's own problem, missing prices and displacement, is a test bed for the same idea, although not an RCT (inference).
- The fused panel does not contain geocoded RCT sites or cash-transfer programme locations, which Step 1 and Step 4 need.

### Literature pipeline and evidence map (C)
- The key empirical risk is whether enough geocoded RCTs with panel data exist, especially in conflict and disaster settings. The evidence map can answer that if it records data availability (see the group C connections note).
- The Gemini Brief's question 4 asks which additional data the closest papers use. The brainstorm's candidates (night lights, NDVI/kNDVI, building footprints, crop yields) are the same family and can be added to its list.

### Exploratory methods (E)
- Spectral bias and tipping points (Research Ideas) bear directly on Step 4: extrapolating to a new location where conditions fall outside the source support (the brainstorm's overlap condition) is where smooth models are most likely to be wrong.

## Open items
1. The unanswered critique: do the ideas hang together, is there enough panel data, how well does it map to transfer learning in conflict and disaster settings. A reply is needed before this group can be developed.
2. Decide the home: a standalone methods paper (Direction III), a section of Project 03, or a later dissertation chapter.
3. Verify every citation (Egger et al. 2022, Meager 2019, Athey et al. 2019, Bai and Ng 2008 and the rest) before relying on it.
4. Gemini's table calls LIML "essential" for many weak proxy instruments. This is a strong claim to check; it depends on whether proxies are really being used as instruments (inference).
