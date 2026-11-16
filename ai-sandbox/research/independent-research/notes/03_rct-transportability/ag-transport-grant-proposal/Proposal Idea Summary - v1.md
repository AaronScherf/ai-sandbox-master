# Proposal idea summary (draft v1, for the environmental science final paper)

*2026-11-16. A one-page statement of the idea, not the proposal. Numbers come from the pilot checks in [Reference Log v2](Reference%20Log%20-%20Four%20Searches%20-%20v2.md); every figure is a first pass, not a result. Funder framing is an assumption: I did not confirm a current NSF DISES or NASA solicitation.*

## Working title
**How far can environmental covariates carry crop-yield and fertilizer-response predictions into conflict-affected, data-poor regions? A held-out test in the Horn of Africa and a design for the data that would settle it.**

## The question
Planners in Sudan and South Sudan cannot observe most of the land they decide about. The best current work (CIMMYT's 2024/25 sorghum assessment for Sudan) already relies on satellite NDVI calibrated to crop cuts and extended to unobserved pixels. The open question is when that kind of prediction is good enough to act on: **is the information in shared environmental covariates (rainfall, vegetation, soil, plus conflict exposure) sufficient to predict yields and, more importantly, the effect of an agronomic intervention, in a place with no training data?**

## Hypotheses (falsifiable; decision threshold fixed in advance)
- **H1 (sufficiency).** Out-of-country prediction from environmental covariates alone does not meet a pre-specified decision criterion (a prediction interval narrow enough to say whether fertilizer pays at a stated profitability threshold). A null result, that prediction is adequate, would be equally informative.
- **H2 (distance).** Prediction error grows with distance from the nearest training sites in covariate space, and adding ACLED conflict exposure adds little once environment is controlled (as in the South Sudan sorghum precedent, Karongo et al. 2025).
- **H3 (design).** Placing new sites to cover the empty parts of covariate space (k-median or active selection) lowers transfer error more than the same number of randomly or conveniently placed sites.
- **Causal-distance gradient (framing hypothesis).** The share of heterogeneity explained by environmental covariates falls as the causal chain lengthens: yield level, then fertilizer response, then household outcomes such as consumption.

## Aims
1. **Retrospective hold-out (no new data).** Train on HarvestStat Africa subnational yields (and OFRA point-trial response functions) from countries other than the target; predict held-out Somalia as a country-level hold-out, with a second stage using Somalia's most recent years as a temporal hold-out. Compare covariate sets and spatial units (district, state, grid).
2. **Proxy assessment.** Test whether conflict-affected regions elsewhere (for example northeast Nigeria, the Sahel) behave like the target, by environmental similarity as well as by conflict exposure.
3. **Prospective trials (the funded part).** Run fertilizer-response trials with crop-cut yields in Sudan and South Sudan at sites chosen under Aim 3's design, and test the Aim 1 predictions there.

## Why it needs a grant
Open data cannot answer it. OFRA has no sites in Somalia, Sudan or South Sudan, and the nearest OFRA sites to Sudan's events are in western Ethiopia (Assosa, about 32 km). HarvestStat has no crop-specific South Sudan yields after 2012, and Sudan's state-level units average about 57,000 km2. The CIMMYT assessment has no yield estimate for Kassala. Plot-level yield and treatment data in conflict zones exist only privately (the ICRC-linked South Sudan survey of 2,100 farmers, available on request).

## What the pilot checks show so far
- **Data is there to start.** Somalia alone has enough exposed and non-exposed yield unit-years (sorghum 190 / 322, maize 226 / 337) to serve as a country-level hold-out. Sudan sorghum has 65 exposed / 188 non-exposed; South Sudan has essentially none, which is the gap the grant fills.
- **Rainfall data is available for the analysis.** CHIRPS seasonal rainfall could be matched to 9,866 of 10,259 unit-crop-years (96%).
- **A naive model does not transfer.** Within-unit rainfall anomalies explain some yield variation in Somalia (R2 0.19 sorghum, 0.12 maize) and less in Sudan (0.08 sorghum). A slope fitted on all other countries has **no out-of-country skill** (out-of-sample R2 about 0 for Somalia and Sudan sorghum, 0.05 for Somalia maize). This is a crude baseline, using one covariate and unit-anomalies, not a conclusion about what better models can do.
- **Proxies are not obvious.** Somalia's nearest rainfall-regime neighbours are units in Niger, South Africa, Ethiopia and Chad, and only 14% of them are conflict-exposed; they are about three times farther in climate space than Somalia's own nearest units (0.33 vs 0.12).
- **Scale matters.** Somali districts median about 5,700 km2; Sudanese states about 57,000 km2. Training at one scale and predicting at another is part of the question, not a nuisance.

## Honest limits
- Yield-level data tests yield transfer; fertilizer-response transfer rests on OFRA, whose sites overlap HarvestStat units in only 24 country-crop groups, mostly outside the Horn.
- Exposure is a raw ACLED event count; selective missingness inside insecure units is not ruled out.
- I have not shown that predictions in Sudan and South Sudan would be used: number of smallholders reached, or actors able to act on a prediction. This should be checked before the proposal claims it.
- Whether the USAID-funded CIMMYT programme continues is unconfirmed.
- Delivering fertilizer at scale to conflict zones is a separate logistics question the trials do not answer.

## Next
1. Check use: smallholder counts and decision-makers in Sudan and South Sudan; programme continuity for the CIMMYT assessment.
2. Read the CIMMYT PDF for its validation design.
3. Add covariates beyond rainfall (NDVI, soil, temperature) and repeat the hold-out with a proper model.
4. Decide funder framing (DISES versus a NASA food-security call) after reading a current solicitation.
