# Proposal idea summary (draft v2, for the environmental science final paper)

*2026-11-16. Supersedes [v1](Proposal%20Idea%20Summary%20-%20v1.md): the pilot numbers are corrected and the trial-versus-area idea is added. Source of every figure: [Reference Log v3](Reference%20Log%20-%20Four%20Searches%20-%20v3.md) and the [pilot code](../../projects/ag-transport-pilot/README.md). Funder framing is an assumption; no current NSF DISES or NASA solicitation was confirmed.*

## Working title
**How far can environmental covariates carry crop-yield and fertilizer-response predictions into conflict-affected, data-poor regions? A held-out test in the Horn of Africa and a design for the data that would settle it.**

## The question
Planners in Sudan and South Sudan cannot observe most of the land they decide about. The best current work, CIMMYT's 2024/25 sorghum assessment for Sudan, calibrates satellite NDVI to crop cuts and extends the curve to every sorghum pixel in four states. The open question is when such prediction is good enough to act on: **do shared environmental covariates (rainfall, vegetation, soil, plus conflict exposure) carry enough information to predict yields and, more importantly, the effect of an agronomic intervention, where there is no training data?**

## Hypotheses (falsifiable; decision threshold fixed in advance)
- **H1 (sufficiency).** Out-of-country prediction from environmental covariates alone does not meet a pre-specified decision criterion (an interval narrow enough to say whether fertilizer pays at a stated profitability threshold). A finding that it does would be equally informative.
- **H2 (distance).** Prediction error grows with distance from the nearest training sites in covariate space; adding conflict exposure adds little once environment is controlled (as in the South Sudan sorghum precedent, Karongo et al. 2025).
- **H3 (design).** Placing new sites to cover empty parts of covariate space lowers transfer error more than the same number of conveniently placed sites.
- **H4 (area information).** Area-level yield statistics (such as HarvestStat) improve trial-based response predictions beyond environmental covariates alone, because trials are not representative of the surrounding area.
- **Framing gradient.** The share of heterogeneity explained by environment falls as the causal chain lengthens: yield level, then fertilizer response, then household outcomes.

## Aims
1. **Retrospective hold-out (no new data).** Train on HarvestStat yields and OFRA trial response functions from countries other than the target; predict held-out Somalia, with a second stage using its most recent years. Baseline to beat: the OFRA Inference Tool (borrowing response functions from sites with similar soil and climate). Compare units (district, state, grid).
2. **Proxy assessment.** Test whether conflict-affected regions elsewhere (northeast Nigeria, the Sahel) behave like the target, by environmental similarity as well as exposure.
3. **Prospective trials (the funded part).** Fertilizer-response trials with crop cuts in Sudan and South Sudan at sites chosen to cover covariate space, testing the Aim 1 predictions there.

## Why it needs a grant
Open data cannot answer it. OFRA has no Horn of Africa sites and almost no conflict-exposed trials (17 of 517 site-years have 50 or more violent events within 50 km, 15 of them in Rwanda). HarvestStat has no crop-specific South Sudan yields after 2012, and Sudan's state units average about 57,000 km2. CIMMYT's assessment has no rainfed Kassala yield. Plot-level yield and treatment data in conflict zones exist only privately (an ICRC-affiliated South Sudan survey of 2,100 farmers, available on request).

## What the pilot checks show (exploratory; v3 corrects v1)
- **Somalia can be the holdout.** Sorghum 190 exposed / 322 non-exposed unit-years, maize 226 / 337. Sudan sorghum has 65 / 188. South Sudan has essentially none.
- **Rainfall data are available** for 96% of 12,899 unit-crop-years.
- **A naive rainfall model does not transfer.** Within-unit rainfall explains 0.19 (Somalia sorghum), 0.13 (Somalia maize) and 0.15 (Sudan sorghum) of yield variation; a slope fitted elsewhere has out-of-country R2 of about 0.02. One covariate; a baseline, not a limit on what better models can do.
- **Climate does not rule out proxies.** Somalia's nearest rainfall-regime neighbours (Niger, Kenya, Chad, Angola, Ethiopia, Senegal) are only slightly farther away than its own units (0.19 vs 0.14) but are only 3% conflict-exposed. The v1 claim of "three times farther" was an artifact of a flawed rainfall window and is withdrawn.
- **Trials are not typical of their surroundings.** Where an OFRA trial and a HarvestStat yield share a unit, crop and year (94 unit-years), the OFRA coefficient A is a median 1.9 times (maize) and 1.7 times (sorghum) the unit yield, assuming A is the no-nutrient yield (unverified). This motivates H4.
- **Scale matters.** Somali districts median about 5,700 km2; Sudanese states about 57,000 km2.

## Honest limits
- Yield data test yield transfer; response transfer rests on OFRA, which overlaps HarvestStat in few units, mostly outside the Horn.
- Exposure is a raw event count; selective missingness inside insecure units is not ruled out.
- Not shown: that predictions would be used in Sudan and South Sudan, or that the USAID-funded CIMMYT programme continues.
- Delivering fertilizer at scale to conflict zones is a separate problem the trials do not answer.

## Next
1. Read the OFRA equation source (Wortmann and Sones 2017) and redo the trial-versus-area check on response, not A.
2. Build the OFRA Inference Tool baseline and add area statistics.
3. Add NDVI, soil and temperature; replace the pooled slope with a hierarchical model.
4. Check use: smallholder counts and decision-makers; programme continuity.
5. Choose funder framing after reading a current solicitation.
