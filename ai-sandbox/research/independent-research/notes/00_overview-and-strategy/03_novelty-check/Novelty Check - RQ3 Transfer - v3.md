# Novelty Check: RQ3 — Evidence Transfer and Transportability in Crises (v3)

**Document:** `Novelty Check - RQ3 Transfer - v3.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Literature novelty assessment for PhD Research Question 3 (Transportability theory, empirical effect prediction across sites, pre-registered transport evaluations, disaster-to-conflict cash transfer transferability, and cross-cutting synthesis saturation).

---

## What Changed from v2

1. **Resolution of Bibliographic Identifiers against Crossref:**
   * Corrected Allcott (2015) DOI to `10.1093/qje/qjv015` (*The Quarterly Journal of Economics*, 130(3): 1117–1165).
   * Corrected Brok et al. (2008) venue to *International Journal of Epidemiology*, 38(1): 287–298 (online 2008; print 2009), DOI: `10.1093/ije/dyn188`.
   * Corrected Egger et al. (2022) venue to *Econometrica*, 90(6): 2603–2643, DOI: `10.3982/ecta17945`.
   * Corrected Groh et al. (2016) venue and title to *The Review of Economics and Statistics*, 98(3): 488–502 ("...Recent College Graduates..."), DOI: `10.1162/rest_a_00584`.
   * Corrected DellaVigna, Pope, & Vivalt date to **25 October 2019**, *Science*, 366(6464): 428–429, DOI: `10.1126/science.aaz1704`.
   * Corrected Pearl & Bareinboim (2014) venue to *Statistical Science*, 29(4): 579–595, DOI: `10.1214/14-sts486`.
2. **Substantive Clarification on Forecast Accuracy (Groh et al. / DellaVigna & Pope):**
   * Clarified that Groh et al. (2016) evaluated the Jordan wage subsidy trial (finding 38 pp initial gains that vanished post-subsidy). The finding that experts overestimated persistence was an external forecasting experiment conducted on Groh et al.'s findings by **DellaVigna & Pope (2018, *JPE*)** and David McKenzie.
3. **Programmatic Crossref Verification:**
   * All 23 DOIs were verified via automated Crossref/DataCite resolution (`check_all_dois.py`), matching title and author with 0 errors.

---

## 1. Verdict

**Verdict: Partly answered.**

Formal mathematical theories for causal transportability (Pearl & Bareinboim's selection diagrams; Dahabreh et al.'s trial-to-target conditional exchangeability) are rigorous, and empirical development economics has documented substantial cross-site heterogeneity (Vivalt, Meager, Pritchett & Sandefur) and site-selection biases (Allcott, Montiel Olea et al.). 

However, **these formal transport models have not been operationalized in protracted crisis or active conflict settings**, where displacement churn and market disruptions violate positivity and conditional exchangeability assumptions. Furthermore, while pre-registration exists for human expert forecasts (SSPP) and binary lab replication models (Altmejd et al., 2019), **I found no literature that calibrates an ex-ante causal transport model (or partial identification bounds) to predict numerical treatment effects in an unstudied crisis target population, pre-registers that prediction, and prospectively tests it against a newly fielded evaluation**.

---

## 2. Findings on Sub-Questions

### Sub-Question 9: Transportability and generalizability theory and applications in development or crisis settings
* **Category Tag:** **(a) Settled in theory; (c) Absent in crisis settings.**
* **Findings:**
  * *Structural Causal Models:* Pearl & Bareinboim (2014, *Statistical Science*) and Bareinboim & Pearl (2016) established graph-based transportability using selection diagrams ($S$-nodes) and do-calculus to identify target effects $P^*(y \mid \text{do}(x))$ by fusing source trials with target covariates.
  * *Potential Outcomes / Epidemiology:* Dahabreh et al. (2020) formalized generalizability via conditional effect exchangeability ($Y^a \perp S \mid X$), positivity, and treatment consistency using g-computation and IPW weighting.
  * *Failure in Crises:* In protracted crises: (1) treatment versions change (hawala vs. banking); (2) common support fails (inaccessible zones lack trial data); (3) unmeasured modifiers (extortion, siege) violate conditional exchangeability.
  * *Partial Identification Bounds:* When common support fails, point identification collapses. Gechter (2024) developed sensitivity intervals for generalizability under unmeasured modifier dependence, but bounding methods remain unapplied to crisis aid.

### Sub-Question 10: Empirical work on predicting effects in new sites
* **Category Tag:** **(a) Settled / active in empirical development economics.**
* **Findings:**
  * *Cross-Site Heterogeneity:* Vivalt (2020) evaluated 635 development effect sizes from AidGrade, finding massive cross-site heterogeneity (median $I^2 = 82\%$), with observable covariates explaining little variance.
  * *Bayesian Hierarchical Modeling:* Meager (2019) analyzed 7 microcredit RCTs, showing wide posterior predictive distributions for a *new site* despite pooled mean effects near zero, cautioning against point extrapolations.
  * *Site Selection Bias:* Allcott (2015, *QJE*) proved severe site selection bias across 111 energy sites. Montiel Olea et al. (2024) framed externally valid site selection as a minimax-regret problem equivalent to the $k$-median facility location problem.
  * *Temporal Heterogeneity:* Rosenzweig & Udry (2020) showed agricultural RCTs interact heavily with weather shocks; an RCT in a drought year gives biased predictions for normal years.
  * *Observational vs. Experimental Tradeoff:* Pritchett & Sandefur (2015) demonstrated local observational estimates frequently achieve lower Mean Squared Error than transported RCTs due to large context heterogeneity.

### Sub-Question 11: Prospective, pre-registered predictions of treatment effects compared with later experiments
* **Category Tag:** **(a) Settled for human expert forecasts; (b) Active for machine-learning replication predictions; (d) Unaddressed for pre-registered causal transport models in crises.**
* **Findings:**
  * *Human Expert Forecasts:* DellaVigna & Pope (2018) and DellaVigna, Pope, & Vivalt (2019, *Science*) established the Social Science Prediction Platform (SSPP). Aggregated prior forecasts correlate with realized results, though forecasters exhibit overconfidence. In a prominent forecasting study on Groh et al.'s (2016) Jordan wage subsidy trial, DellaVigna & Pope (2018) showed that academic researchers and practitioners substantially overestimated program persistence.
  * *Pre-Registered Replication Models:* Altmejd et al. (2019) pre-registered machine learning models predicting binary lab replication outcomes (AUC 0.73).
  * *The Transport Model Gap:* While human forecasts are pre-registered on SSPP and statistical models predict binary lab replications, **I found no literature that:** (1) calibrated an ex-ante causal transport model (selection diagrams or Gechter bounds) using source evidence and target baseline data; (2) pre-registered numerical effect predictions and bounds prior to rollout; and (3) prospectively tested those predictions against a newly fielded trial in an unstudied crisis setting.

### Sub-Question 12: Cash transfer evidence under conflict or displacement and disaster-to-conflict transfer
* **Category Tag:** **(a) Settled for cash efficacy; (a) Settled negatively regarding unadjusted transfer from disaster to conflict.**
* **Findings:**
  * *Efficacy in Crises:* Systematic reviews (Doocy & Tappis, 2017) confirm unconditional cash transfers (UCTs) effectively improve consumption in emergencies, often with superior cost-efficiency to in-kind food.
  * *Conflict Interactions:* In the Philippines, Crost, Felter, & Johnston (2016) showed CCT eligibility caused a statistically significant **decrease** in insurgent incidents in treated villages, as improved welfare reduced rebel support. (Conversely, Crost, Felter, & Johnston 2014 found CDD infrastructure projects increased violence due to rebel sabotage).
  * *Disaster-to-Conflict Transfer Breakdown:* Transporting cash evidence from natural disasters to conflict zones breaks down due to: (1) *Market Inelasticity* (sieges turn cash into local inflation); (2) *Predation* (armed actors tax beneficiaries); (3) *Delivery Collapse* (disrupted banking forces reliance on informal hawala); (4) *Displacement Churn* (forced flight violates SUTVA; Egger et al., 2022, *Econometrica*).

### Cross-Cutting Sub-Question 13: Measures of saturation or stopping in evidence synthesis and evidence gap maps
* **Category Tag:** **(a) Settled in clinical systematic reviews (CMR, TSA); (c) Method exists elsewhere, but absent in Evidence and Gap Maps.**
* **Findings:**
  * *Capture-Mark-Recapture in Searches:* Adapted from ecology to systematic reviews, Capture-Mark-Recapture (CMR; Kastner et al., 2009; Spoor et al., 1996) models database overlap to estimate unretrieved studies, though unequal catchability across databases restricts prospective stopping rules.
  * *Trial Sequential Analysis (TSA):* In clinical meta-analysis, Wetterslev et al. (2008) and Brok et al. (2008, *IJE*) developed TSA using alpha-spending boundaries to establish when cumulative meta-analysis reaches firm power.
  * *Qualitative Saturation:* Saunders et al. (2018) formalize thematic saturation models for qualitative evidence.
  * *Gap in Evidence Gap Maps (EGMs):* In international development and humanitarian aid, Evidence and Gap Maps (EGMs; White, Saran, & Welch, 2020) cross-tabulate interventions against outcomes. However, **existing EGMs possess no quantitative stopping rules or saturation metrics**. Empty cells are labeled "gaps" without statistical metrics establishing whether the gap reflects true absence of evidence, insufficient search coverage, or an arbitrary search cutoff.

---

## 3. What Aaron's Contribution Could Still Be

Aaron's contribution for RQ3 lies in **translating formal transportability and bounding methods to crisis realities, and conducting the first prospective validation**:

1. **A Four-Tier Output Architecture for Crisis Evidence Transfer:**
   Formalizing an explicit hierarchy based on verified target data: (1) *Point Estimate Prediction* (common support and complete modifier overlap verified); (2) *Partial Identification Bounds* (Manski or Gechter bounds when support is incomplete); (3) *Testable Mechanism Hypotheses* (using DAGs to specify local causal pathways); (4) *Principled "No Inference" Assertion* (documenting evidence cannot inform the choice).
2. **First Prospective Pre-Registered Transport Evaluation in a Crisis:**
   Calibrating an ex-ante transport model for an operational decision (e.g., cash vs. safety net transfer), pre-registering numerical predicted effects and bounding intervals prior to implementation, building an evaluation into rollout, and prospectively comparing realized results against ex-ante predictions.
3. **Formal Saturation Metrics for Evidence Gap Maps:**
   Developing an objective stopping metric for EGMs: combining *Coverage Stability* (monitoring marginal study yield) and *Value Stability* (monitoring shifts in pooled effect distributions).

---

## 4. Search Log & Access Report

### Search Log
* **Search Window:** 2026-11-10 to 2026-11-11
* **Engines & Registries:** Google Scholar, NBER, Crossref API (`api.crossref.org`), DataCite API (`api.datacite.org`), ScienceDirect, Oxford Academic, Wiley, Taylor & Francis, arXiv.
* **Core Queries Screened:** `"transportability" ("Pearl" OR "Bareinboim" OR "Dahabreh")`; `"Michael Gechter" "treatment effects" OR "bounds"`; `"Meager" "Average Impact of Microcredit"`; `"Montiel Olea" "arXiv:2408.09187"`; `"Crost" "Felter" "Johnston" "cash"`; `"Altmejd" "Predicting the replicability"`; `"capture-mark-recapture" "systematic reviews"`; `"Evidence and gap maps" "White"`. (~210 records screened).

### Access Report
* **Crossref / DataCite Programmatic Resolution:** All 23 DOIs were programmatically resolved via `api.crossref.org` and `api.datacite.org` using `check_all_dois.py`. Every DOI resolved with matching title and first author (23 passed, 0 failed). Full publisher pages audited: Allcott (2015), Altmejd et al. (2019), Bareinboim & Pearl (2016), Brok et al. (2008), Crost et al. (2016), Dahabreh et al. (2020), DellaVigna & Pope (2018), DellaVigna et al. (2019), Doocy & Tappis (2017), Egger et al. (2022), Gechter (2024), Groh et al. (2016), Hotz et al. (2005), Kastner et al. (2009), Meager (2019), Montiel Olea et al. (2024), Pearl & Bareinboim (2014), Pritchett & Sandefur (2015), Rosenzweig & Udry (2020), Saunders et al. (2018), Vivalt (2020), Wetterslev et al. (2008), White et al. (2020).

---

## 5. References and Evidence Verification

* [Allcott (2015)](https://doi.org/10.1093/qje/qjv015) — Allcott, H. (2015). Site selection bias in program evaluation. *Quarterly Journal of Economics*, 130(3), 1117–1165. Documents severe site-selection bias across 111 energy deployments. **[VERIFIED]**
* [Altmejd et al. (2019)](https://doi.org/10.1371/journal.pone.0225826) — Altmejd, A., et al. (2019). Predicting the replicability of social science lab experiments. *PLOS ONE*, 14(12), e0225826. Pre-registered statistical models predicting binary lab replications. **[VERIFIED]**
* [Bareinboim & Pearl (2016)](https://doi.org/10.1073/pnas.1510507113) — Bareinboim, E., & Pearl, J. (2016). Causal inference and the data-fusion problem. *PNAS*, 113(27), 7345–7352. Synthesizes graph-based transportability theory. **[VERIFIED]**
* [Brok et al. (2008)](https://doi.org/10.1093/ije/dyn188) — Brok, J., Thorlund, K., Wetterslev, J., & Gluud, C. (2008). Apparently conclusive meta-analyses may be inconclusive—Trial sequential analysis adjustment of random error risk due to repetitive testing of accumulating data in apparently conclusive neonatal meta-analyses. *International Journal of Epidemiology*, 38(1), 287–298. **[VERIFIED]**
* [Crost, Felter, & Johnston (2016)](https://doi.org/10.1016/j.jdeveco.2015.08.005) — Crost, B., Felter, J. H., & Johnston, P. B. (2016). Conditional cash transfers, civil conflict and insurgent influence: Experimental evidence from the Philippines. *Journal of Development Economics*, 118, 171–182. **[VERIFIED]**
* [Dahabreh et al. (2020)](https://doi.org/10.1111/biom.13009) — Dahabreh, I. J., et al. (2020). Generalizing causal inferences from individuals in randomized trials to all trial-eligible individuals. *Biometrics*, 75(2), 685–694. **[VERIFIED]**
* [DellaVigna & Pope (2018)](https://doi.org/10.1086/699976) — DellaVigna, S., & Pope, D. (2018). Predicting experimental results: who knows what? *Journal of Political Economy*, 126(6), 2410–2456. **[VERIFIED]**
* [DellaVigna, Pope, & Vivalt (2019)](https://doi.org/10.1126/science.aaz1704) — DellaVigna, S., Pope, D., & Vivalt, E. (2019). Predict science to improve science. *Science*, 366(6464), 428–429. **[VERIFIED]**
* [Doocy & Tappis (2017)](https://doi.org/10.4073/csr.2017.17) — Doocy, S., & Tappis, H. (2017). The Effectiveness and Efficiency of Cash-Based Approaches in Emergencies. *Campbell Systematic Reviews*, 13(1), 1–138. **[VERIFIED]**
* [Egger et al. (2022)](https://doi.org/10.3982/ecta17945) — Egger, D., Haushofer, J., Miguel, E., Niehaus, P., & Walker, M. W. (2022). General Equilibrium Effects of Cash Transfers: Experimental Evidence From Kenya. *Econometrica*, 90(6), 2603–2643. **[VERIFIED]**
* [Gechter (2024)](https://doi.org/10.1080/07350015.2023.2241529) — Gechter, M. (2024). Generalizing the results from social experiments: Theory and evidence from the PROGRESA program. *Journal of Business & Economic Statistics*, 42(2), 801–811. **[VERIFIED]**
* [Groh et al. (2016)](https://doi.org/10.1162/rest_a_00584) — Groh, M., Krishnan, N., McKenzie, D., & Vishwanath, T. (2016). Do Wage Subsidies Provide a Stepping-Stone to Employment for Recent College Graduates? Evidence from a Randomized Experiment in Jordan. *The Review of Economics and Statistics*, 98(3), 488–502. **[VERIFIED]**
* [Hotz, Imbens, & Mortimer (2005)](https://doi.org/10.1016/j.jeconom.2004.04.009) — Hotz, V. J., Imbens, G. W., & Mortimer, J. H. (2005). Predicting the efficacy of future training programs using past experiences at other locations. *Journal of Econometrics*, 125(1–2), 241–270. **[VERIFIED]**
* [Kastner et al. (2009)](https://doi.org/10.1016/j.jclinepi.2008.06.001) — Kastner, M., et al. (2009). The capture–mark–recapture technique can be used as a stopping rule when searching in systematic reviews. *Journal of Clinical Epidemiology*, 62(2), 149–157. **[VERIFIED]**
* [Meager (2019)](https://doi.org/10.1257/app.20170299) — Meager, R. (2019). Understanding the Average Impact of Microcredit Expansions: A Bayesian Hierarchical Analysis of Seven Randomized Experiments. *AEJ: Applied Economics*, 11(1), 57–91. **[VERIFIED]**
* [Montiel Olea et al. (2024)](https://doi.org/10.48550/arXiv.2408.09187) — Montiel Olea, J. L., et al. (2024). Externally valid policy choice. *arXiv preprint arXiv:2408.09187 [econ.EM]*. **[VERIFIED]**
* [Pearl & Bareinboim (2014)](https://doi.org/10.1214/14-sts486) — Pearl, J., & Bareinboim, E. (2014). External Validity: From Do-Calculus to Transportability Across Populations. *Statistical Science*, 29(4), 579–595. **[VERIFIED]**
* [Pritchett & Sandefur (2015)](https://doi.org/10.1257/aer.p20151016) — Pritchett, L., & Sandefur, J. (2015). Learning from experiments when context matters. *American Economic Review*, 105(5), 471–475. **[VERIFIED]**
* [Rosenzweig & Udry (2020)](https://doi.org/10.1093/restud/rdz021) — Rosenzweig, M. R., & Udry, C. (2020). External validity, information and prices: Methods and results from investments in Indian agriculture. *Review of Economic Studies*, 87(1), 343–381. **[VERIFIED]**
* [Saunders et al. (2018)](https://doi.org/10.1007/s11135-017-0574-8) — Saunders, B., et al. (2018). Saturation in qualitative research: exploring its conceptualization and operationalization. *Quality & Quantity*, 52(4), 1893–1907. **[VERIFIED]**
* [Vivalt (2020)](https://doi.org/10.1093/jeea/jvaa019) — Vivalt, E. (2020). How much can we generalize from impact evaluations? *Journal of the European Economic Association*, 18(6), 3045–3089. **[VERIFIED]**
* [Wetterslev et al. (2008)](https://doi.org/10.1016/j.jclinepi.2007.03.013) — Wetterslev, J., et al. (2008). Trial sequential analysis may establish when firm evidence is reached in cumulative meta-analysis. *Journal of Clinical Epidemiology*, 61(1), 64–75. **[VERIFIED]**
* [White, Saran, & Welch (2020)](https://doi.org/10.1002/cl2.1075) — White, H., Saran, A., & Welch, V. (2020). Evidence and gap maps: A tool for promoting evidence informed policy and strategic research agendas. *Campbell Systematic Reviews*, 16(1), e1075. **[VERIFIED]**
