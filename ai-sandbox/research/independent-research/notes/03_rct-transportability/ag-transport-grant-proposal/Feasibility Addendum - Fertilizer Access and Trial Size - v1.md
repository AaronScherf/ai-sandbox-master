# Is the project worth funding? Fertilizer access and trial-size model (Addendum v1)

*2026-11-17. Follows [Reference Log v4](Reference%20Log%20-%20Four%20Searches%20-%20v4.md) and [Proposal Draft v1](Proposal%20Draft%20-%20v1.md). Code: [`14_candidate_cells.py`](../../projects/ag-transport-pilot/scripts/14_candidate_cells.py), [`15_trial_design_model.py`](../../projects/ag-transport-pilot/scripts/15_trial_design_model.py); tables `outputs/design_*.csv`, `candidate_cells_summary.csv`. One analyst, run on acquired data, not independently reproduced. News items are not Crossref-checkable; they are cited by URL.*

## 1. Fertilizer access (quick literature, report and news check)

| | Finding | Source quality |
|---|---|---|
| **South Sudan** | Smallholders on field crops **do not use chemical fertilizer**, pesticide or herbicide; soil fertility is kept by shifting cultivation and fallow, manure in a few states. Small amounts of fertilizer are used on vegetables near the Ugandan border by better-off farmers. Herbicide on a few large mechanized farms in Upper Nile comes from Sudan. Private tractor hire rose 80% (SSP 150,000 to 270,000) and fuel 25% in a year. | FAO/WFP Crop and Food Security Assessment 2025 ([CliMIS PDF](https://climis-southsudan.org/uploads/publications/CFSAM_2025.pdf)); **read directly** |
| **Sudan, supply** | Inputs including fertilizer remained scarce at very high prices in the 2024 assessment; over half of fertilizer imports come from the Gulf, so the 2026 Hormuz disruption cut supply. Input supply is being rebuilt through agro-dealers (Sustain Sudan, with CIMMYT and Clingendael; a shipment reached Port Sudan in December 2025). | FAO CFSAM Sudan 2024 ([PDF](https://fscluster.org/sites/default/files/2025-06/Sudan%202024%20CFSAM%20Special%20Report%20-%20March%202025.pdf)) and [Clingendael](https://www.clingendael.org/sites/default/files/2025-01/Sudans_agricultural_input_supply_war_final.pdf): **not read** (server blocked download; claims via search summaries) |
| **Sudan, price** | A farmer in the irrigated Gezira scheme reports a 50 kg bag of urea at about **$50 in May 2026 against $11 a year earlier**; national surveys: fertilizer +67% year on year, irrigation diesel more than doubled; "two sacks of wheat buy one sack of urea"; one scheme planted 500 of 10,000 feddans. | AP and Reuters news (May 2026), e.g. [Reuters via The Citizen](https://thecitizen.co.tz/tanzania/news/africa/iran-war-poses-new-threat-to-harvests-in-hunger-stricken-sudan-5473606); one farmer's account plus survey figures, irrigated, **not** rainfed sorghum |
| **Not found** | Any South Sudan fertilizer price; any price for rainfed sorghum areas (Gedaref, Kordofan); whether Sudan's smallholder survey (IFPRI, 2024) reports input use by crop. | Gap; the IFPRI [survey page](https://sudan.ifpri.info/2026/05/14/farming-in-crisis-livelihood-challenges-and-resilience-in-conflict-affected-sudan-insights-from-the-sudan-2024-smallholder-farmers-survey/) is the next thing to read |

**Reading.** In South Sudan there is no fertilizer market to serve, so a trial there tests a technology with no supply chain, and its value depends on a supply or subsidy program that does not exist in the evidence found. In Sudan a market exists but is currently very expensive and import-dependent. The proposal should therefore state its decision problem as *conditional*: where fertilizer is, or becomes, available, at what response does it pay.

## 2. What price does to the required precision

Break-even gain at 50 kg N/ha is `BE = 50 x VCR x (price of N per kg / price of grain per kg)`, using a value-cost ratio (VCR) of 2 (a common extension rule of thumb; my choice). Urea is 46% N, so $11 a bag is $0.48 per kg N and $50 is $2.17. **The grain price ($0.40/kg) is my placeholder; I found no sourced price.**

| Scenario | Price ratio | Break-even gain at 50 kg N |
|---|---|---|
| Pre-spike urea ($11/bag) | 1.2 | **120 kg grain/ha** |
| 2026 spike ($50/bag) | 5.4 | **540 kg grain/ha** |

For comparison, OFRA's mean sorghum gain at 50 kg N is **476 kg/ha** (92 sites), maize 795. At spike prices the average OFRA sorghum response is below break-even; at pre-spike prices it clears it fourfold. Whether fertilizer pays in Sudan is therefore settled more by price than by anything a trial would measure, unless trials find unusually large responses at some sites. This is the main threat to the project's impact and belongs in the proposal.

## 3. Trial-size model

**Method** (`15_trial_design_model.py`, header gives the full specification). Response at 50 kg N is a Gaussian process over the seven OFRA-IT covariates, calibrated on OFRA site means. Candidate and target units are 0.25-degree cells (553 in Sudan, 843 in South Sudan) with aridity index at least 0.2. Risk is violent ACLED events within 50 km over the last 24 months (to 31 October 2025), each weighted 1 + ln(1 + fatalities), per year. A greedy search chooses the trial cells that most reduce posterior variance across the country, subject to a risk cap. Monte Carlo (40 draws) simulates the trials: a cell is *decidable* when the 80% interval of its response excludes break-even.

**Result 1: the data do not support covariate transfer.** Fitted lengthscale is 0.16 standardized units for sorghum (0.20 maize); the median Sudan cell is 1.44 from the nearest OFRA site (maize 2.02), against 0.36 between OFRA sites themselves. Leave-country-out skill of the GP over the pooled mean is **0.02**, matching the Inference Tool finding. Forcing a long lengthscale (1.5 or 3) and refitting makes the covariate-explained variance collapse (sorghum signal SD 429 to 42 kg/ha at lengthscale =1.5, with the log-likelihood only 1.5 worse), so long-range transfer is not rejected but is unsupported.

**Result 2: therefore trial count scales with the number of places decided on.** Under the data-fitted model each trial informs mostly its own cell. Mean posterior SD of the area response falls only from 429 to about 380 kg/ha after 80 trials per country, and the share of cells where fertilizer can be called pays or not at 80% confidence is 16-28% at pre-spike prices and 6-9% at spike prices (80 trials per country, any risk cap). Covering the whole domain at this resolution means several hundred trials per country, which is not a plausible grant.

**Result 3 (optimistic bound, imposed not fitted):** if covariates explain half of between-site variance with lengthscale 1.5, then:

| Sorghum, 80% decidable share | k = 0 | 10 trials | 30 | 80 |
|---|---|---|---|---|
| Sudan, pre-spike, any cap | 0.47 | 0.71 | 0.76 | 0.82 |
| Sudan, spike | 0.00 | 0.25-0.29 | 0.42-0.44 | 0.50-0.57 |
| South Sudan, pre-spike | 0.84 | 0.88-0.90 | 0.91-0.93 | 0.92-0.94 |
| South Sudan, spike | 0.01 | 0.27-0.34 | 0.45-0.47 | 0.56-0.59 |

Posterior SD falls to 107-138 kg/ha. The pre-spike k = 0 values are high only because the OFRA prior mean (476) sits far above break-even (120); OFRA trials sit on better land and better management than ordinary farms (the plateau and control comparison in v4), so that prior is probably too favourable. Roughly 30 trials per country capture most of the available gain; returns diminish after that.

**Result 4: the risk cap matters through eligibility, not information.** Cells with risk at or below 2 (weighted events a year) are 19% of Sudan's and 23% of South Sudan's domain; at or below 10, 45% and 44%; at or below 40, 80% and 74%. Information gain differs little between caps (decidable share at 80 trials, optimistic case, Sudan: 0.79 at cap 2 against 0.82 with no cap) because low-risk cells span the covariate range about as well. Under the data-fitted model all cells inform only themselves, so the cap changes almost nothing. What the cap changes is cost and feasibility: the mean risk of chosen sites is 0.4-0.8 at cap 2, about 4 at cap 10, and 12-76 with no cap. A cap of about 10 loses little information and excludes the worst-affected cells.

**Budget mapping (illustrative; unit costs are assumptions, not quotes).** At $20,000-$60,000 per site over three seasons (insurance, security, crop cuts, fertilizer, travel), 30 sites per country cost $0.6-1.8 million and 80 sites $1.6-4.8 million. The risk premium for higher caps is not modeled and is the main place where real budget numbers are needed.

## 4. Verdict against your criteria

1. **Fertilizer availability.** Absent for smallholders in South Sudan; present but price-shocked and import-dependent in Sudan. A South Sudan arm needs a supply-or-subsidy plan to be decision-relevant.
2. **Price versus gain.** At spike prices the average OFRA sorghum gain is below break-even; the trial's value then lies in finding where the response is large, which is exactly what the covariates cannot predict.
3. **Prediction gain.** Under what OFRA supports, 30-80 trials per country move accuracy modestly (SD 429 to about 380 kg/ha). Only if covariates transfer much better than OFRA shows (the imposed bound) does about 30 trials per country give a large gain. **Deciding which of these holds is Aim 1, and is cheap and needs no field work.** The grant should therefore be staged: fund Aim 1 first, and release the trial money only if the hold-out test shows covariates do transfer or the price falls below the threshold.
4. **Conflict cap.** A cap near 10 weighted events a year keeps about 45% of cells and costs little information.

## 5. Limits

- One response parameter at one N rate; maize and sorghum calibrated separately; sorghum rests on 92 OFRA sites, none in the Horn.
- Isotropic kernel on seven standardized proxy layers; geographic proximity is not used; cell centre risk from 24 months of ACLED, a window that moves with the war.
- The domain is climate-defined (aridity index at least 0.2); WorldCover finds almost no cropland in South Sudan (843 cells, 7 with at least 5% cropland), so cropland weighting would zero it out.
- "Decidable" ignores the farm-level variation inside a 28 km cell; the planner-level decision is harder than shown.
- Price ratios use one farmer's urea price, my VCR and a placeholder grain price.
- Nothing here is independently reproduced.
