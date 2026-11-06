# Cross-Group Connections: RCT Replication & Transportability

*Group D (new; closest to Direction III and Project 03). Files: `RCT_replication_gemini_brainstorm.md` and `Brainstorming Transcript - Transferability of Crisis Interventions.md`. Written 2026-11-05. "(inference)" marks my own reading. The brainstorm's citations are Gemini output and I did not verify them.*

## Precursor: the Transferability brainstorm transcript (Oct 14-20)
`Brainstorming Transcript - Transferability of Crisis Interventions.md` (from branch `gemini/transferability-brainstorm`) came three weeks before the RCT brainstorm and is where most of this group's thinking was first laid out. The RCT brainstorm reads as a more technical restatement of its Sprint 2 and RQ 3.

| Transcript | RCT brainstorm | Relationship |
|---|---|---|
| RQ 3 / Sprint 2: geocode 15-20 cash and insurance trials from 3ie and J-PAL, attach CHIRPS, NDVI, night lights and ACLED, check common support | Steps 2 and 4: add locality covariates and proxies, then match proxies and covariates in a new location | Same idea; Sprint 2 is the concrete data-collection plan |
| "Inverse matching": hold the intervention fixed, match on crisis context | Out-of-sample projection by matching on covariates and proxies | Same; the transcript frames the context as the unit of matching |
| Bayesian hierarchical model that relaxes exchangeability, with a variance penalty growing with context distance, and situational-proximity CAR priors | Bayesian hierarchical pooling of related RCTs with leave-one-site-out checks | The transcript adds the non-exchangeability argument and a penalty term; the brainstorm adds the leave-one-out validation |
| Your view that naive RCT extrapolation is already well studied and unobserved confounders are one question among many | The brainstorm's overlap and conditional-independence assumptions | Consistent; the transcript puts the novelty elsewhere (isomorphic mimicry, delivery rails, practitioner use) |
| Success = same sign and similar magnitude; practitioner usefulness over statistical elegance | Gemini's LIML, DML, JIVE and Bai-Ng detail | Tension: the transcript warns against models "too dense for anyone to actually use". The brainstorm's technical menu should be filtered through that |
| Sprint 1 (Somalia fused panel) and Sprint 3 (price transmission under checkpoints) | Compound shocks panel (group B) | Sprint 1 became the Project 02 pilot; Sprint 3 is closest to the Literature Gap Memo's Option 3 (inference) |

Other points from the transcript that bear on this group:
- Project 03's three chapters come straight from its three research questions (welfare and markets, delivery rails, empirical transportability). That is the policy sense of "transferability" the overview note separates from statistical transportability, and RQ 3 is the bridge between them.
- It argues that satellite covariates avoid the problem of non-harmonized household surveys. That is why the RCT brainstorm's proxy-outcome step matters, and also why its measurement-error caveats (spillovers, attenuation) matter.
- It warns against methodological lock-in before touching the data, and proposes green, yellow and red diagnostic signals in `projects/empirical_sprints/empirical_sprints_overview.md` (not read in full). The RCT brainstorm's Step 3 (can proxies detect the effect?) needs the same kind of go/no-go test before anything is built.
- Its faculty matrix pairs Sprint 2 with Björkegren and Willis.

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
