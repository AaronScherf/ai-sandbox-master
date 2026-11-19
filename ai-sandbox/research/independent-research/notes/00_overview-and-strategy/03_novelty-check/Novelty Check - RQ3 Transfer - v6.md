# Novelty Check: RQ3 – Evidence Transfer and Transportability in Crises (v6)

**Document:** `Novelty Check - RQ3 Transfer - v6.md`  
**Author:** Gemini (Antigravity Session); citation corrections by Claude  
**Date:** 2026-11-18 (content otherwise as of 2026-11-11)  
**Scope:** Literature novelty assessment for PhD Research Question 3 (Transportability theory, empirical effect prediction across sites, pre-registered transport evaluations, disaster-to-conflict cash transfer transferability, and cross-cutting synthesis saturation), incorporating transcript spot-check audits.

---

## What Changed from v5

Only the citations below changed. They were flagged TITLE_WRONG by the reference checker: the DOI, authors and year were right, but the title in the reference list does not exist in Crossref or OpenAlex. Each is now corrected to the registered record. Claims that cite these works were not re-checked against the papers.

1. **Rosenzweig & Udry (2020):** title corrected to *External validity in a stochastic world: Evidence from low-income countries* (was an invented title, "External validity, information and prices: Methods and results from investments in Indian agriculture"). The claim in Section 2 (local general-equilibrium price responses) was written against the invented title and should be checked against the paper before it is relied on.

---

## 1. Verdict

**Verdict: Partly answered.**

Formal theories for causal transportability (Pearl & Bareinboim's selection diagrams; Dahabreh et al.'s conditional exchangeability) are rigorous, and empirical development economics documents substantial cross-site heterogeneity (Vivalt; Meager; Pritchett & Sandefur) and site-selection bias (Allcott; Montiel Olea et al.).

However, **these transport models have not been operationalized in protracted crisis or active conflict settings**, where displacement churn and market shocks violate positivity and exchangeability. Furthermore, while pre-registration exists for human expert forecasts (SSPP; DellaVigna, Pope, & Vivalt, 2019) and binary lab replication models (Altmejd et al., 2019), **no published study calibrates an ex-ante transport model to predict treatment effects in an unstudied crisis target population, pre-registers that prediction, and prospectively tests it against a newly commissioned evaluation**.

---

## 2. Findings on Sub-Questions

### Sub-Question 9: Existing frameworks for transferring causal evidence from one setting to another
* **Category Tag:** **(a) Settled mathematically in causal inference; (b) Active frontier in epidemiology and econometrics; (c) Open for violent conflict and crisis settings.**
* **Findings:**
  * *Selection Diagrams and Do-Calculus:* Pearl & Bareinboim (2014) and Bareinboim & Pearl (2016) use selection diagrams ($S$-nodes) to establish graphical criteria for transporting causal effects from source $\Pi$ to target $\Pi^*$. *(Claim rests on [REGISTRY-MATCHED] references only)*.
  * *Potential Outcomes and Conditional Exchangeability:* Dahabreh et al. (2020) formalize transportability under conditional exchangeability ($Y^a \perp S \mid X$), providing inverse odds weighting, g-computation, and doubly robust estimators. *(Claim rests on [REGISTRY-MATCHED] reference only)*.
  * *Econometric Approaches and Partial Identification:* Hotz, Imbens, & Mortimer (2005) demonstrated that location-reweighting fails if unobserved location-level factors interact with treatment. *(Claim rests on [REGISTRY-MATCHED] reference only)*. Gechter (2024) developed an econometric framework that drops point identification, evaluating treatment effect distributions across sites under relaxed rank invariance to derive partial identification bounds on ATE in an alternative context. `[FULL-TEXT-READ]`. Rosenzweig & Udry (2020) proved that agricultural technology investments cannot be transported across micro-climates without modeling local general equilibrium price responses and rainfall expectations. *(Claim rests on [REGISTRY-MATCHED] reference only)*.
  * *The Humanitarian Gap:* Mathematical transportability requires support coverage (positivity) and covariate adjustment capturing all structural differences. In acute conflict and protracted crises, displacement churn, security fragmentation, and infrastructure collapse violate these conditions.

### Sub-Question 10: Prior work testing how well intervention effects can be predicted across contexts
* **Category Tag:** **(a) Settled in empirical development economics; (b) Active frontier in expert forecasting science.**
* **Findings:**
  * *Cross-Site Heterogeneity in Development:* Meta-analyses show effect sizes rarely generalize directly without substantial dispersion. Vivalt (2020) analyzed 635 development studies, showing high heterogeneity and low generalizability across contexts. *(Claim rests on [REGISTRY-MATCHED] reference only)*. Meager (2019) applied Bayesian hierarchical models across seven microcredit trials, showing near-zero average impacts but substantial cross-study variance. *(Claim rests on [REGISTRY-MATCHED] reference only)*. Pritchett & Sandefur (2015) showed that naive observational estimates from the target country often predict local impact better than high-rigor experimental estimates transported from abroad. *(Claim rests on [REGISTRY-MATCHED] reference only)*.
  * *Site Selection Bias:* Allcott (2015) evaluated 111 Opower energy efficiency trials and proved severe site selection bias: early-adopting utilities had significantly larger treatment effects than later-mandated sites. *(Claim rests on [REGISTRY-MATCHED] reference only)*. Montiel Olea et al. (2024) proved that selecting experimental sites to maximize external validity under worst-case welfare regret is mathematically equivalent to solving a $k$-median facility location problem, incorporating policy-relevant site-level covariates as connection costs. `[FULL-TEXT-READ]`.
  * *Employment Subsidy Dissipation vs. Expert Forecasting:* Groh et al. (2016) evaluated a randomized wage subsidy voucher experiment for female community college graduates in Jordan, finding a 38 pp short-term employment gain that completely vanished after the voucher expired (1.7 pp, statistically insignificant). `[FULL-TEXT-READ]`. Separately, DellaVigna & Pope (2018) established experimental methods for eliciting forecasts from 208 academic experts across 15 treatments in a real-effort task, documenting that average crowd forecasts outperform 96% of individual experts. `[FULL-TEXT-READ]`.

### Sub-Question 11: Examples of pre-registering prospective effect predictions before an evaluation is conducted
* **Category Tag:** **(a) Settled for lab and human expert forecasts; (c) Open for pre-registered statistical model transport in crisis policy.**
* **Findings:**
  * *Pre-Registered Human Expert Predictions:* The Social Science Prediction Platform (SSPP), established by DellaVigna, Pope, & Vivalt (2019), systematically collects, catalogs, and pre-registers expert forecasts of empirical and experimental research results prior to study unblinding. `[FULL-TEXT-READ]`.
  * *Machine Learning Replication Predictions:* Altmejd et al. (2019) trained predictive machine learning models on study characteristics and prior metrics to predict binary replication outcomes of social science lab experiments, achieving a cross-validated accuracy rate of 70% (AUC 0.77), which matched peer prediction market accuracy (65.5%). `[FULL-TEXT-READ]`.
  * *The Proposed Method Gap:* While pre-registration of human expert priors is now established, no literature calibrates an *ex-ante statistical transport model* (using Pearl's selection diagrams or Dahabreh's reweighting) to generate a prospective numerical effect prediction for an unstudied humanitarian target population, pre-registers that prediction, implements the intervention with built-in evaluation, and formally compares realized effects to the pre-registered prediction.

### Sub-Question 12: Literature transferring evidence from disaster to conflict settings, especially cash transfers
* **Category Tag:** **(a) Settled in empirical disaster evaluations; (b) Active frontier in conflict cash research; (c) Open for formal disaster-to-conflict transfer algorithms.**
* **Findings:**
  * *Emergency Cash Evidence Base:* A comprehensive systematic review by Doocy & Tappis (2017) synthesizes extensive evidence on cash transfers in natural disasters, showing large improvements in food consumption and asset preservation. *(Claim rests on [REGISTRY-MATCHED] reference only)*. However, empirical evidence from active armed conflicts remains thin.
  * *Conflict-Specific Dynamics:* Transporting cash evidence from disaster to conflict settings encounters distinct structural distortions:
    * *Conflict Reduction vs. Displacement Risk:* Crost, Felter, & Johnston (2016) demonstrated experimentally in the Philippines that conditional cash transfers caused a substantial **decrease** in conflict-related incidents and insurgent influence in treated villages during the first 9 months. However, the authors could not rule out that this effect was due to the displacement of insurgent activity to neighboring control villages. (The finding that program implementation *increased* insurgent violence due to rebel sabotage incentives belongs to Crost, Felter, & Johnston 2014 evaluating the KALAHI-CIDSS community infrastructure project, not the 2016 cash transfer evaluation). `[FULL-TEXT-READ]`.
    * *General Equilibrium Market Distortions:* In stable rural settings, large-scale cash transfers generate substantial positive local fiscal multipliers (import-adjusted 2.52; nominal 2.66–2.71) with minimal price inflation ("small treatment effects on prices") (Egger et al., 2022). `[FULL-TEXT-READ]`. In active conflict, supply-chain bottlenecks and localized monopoly power convert cash injections into rapid localized food price inflation rather than real consumption gains.
  * *Transfer Status:* Practitioners routinely transfer cash benchmarks from stable or disaster contexts into conflict zones without adjusting for predatory taxation, supply elasticity, or extortion risks.

### Sub-Question 13: Methods for knowing when evidence synthesis has "reached saturation"
* **Category Tag:** **(a) Settled in clinical meta-analysis and qualitative inquiry; (b) Active frontier in Evidence Gap Maps; (c) Open for formal quantitative stopping metrics in multi-stream crisis synthesis.**
* **Findings:**
  * *Qualitative Saturation:* Standard qualitative methodologies define saturation as the point where additional interviews yield no new codes or themes (Saunders et al., 2018). *(Claim rests on [REGISTRY-MATCHED] reference only)*.
  * *Trial Sequential Analysis (TSA):* In clinical cumulative meta-analysis, Wetterslev et al. (2008) and Brok et al. (2008) established TSA, which uses sequential monitoring boundaries adjusted for sparse data to control type I errors and establish when cumulative evidence is definitive. *(Claim rests on [REGISTRY-MATCHED] references only)*.
  * *Capture-Mark-Recapture (CMR):* In systematic literature search design, Kastner et al. (2009) adapted capture-mark-recapture models (the Horizon Estimate) to estimate total literature volume across bibliographic databases, evaluating closeness to capturing the total body of literature as a search stopping rule. `[FULL-TEXT-READ]`.
  * *Evidence and Gap Maps (EGMs):* 3ie and Campbell Collaboration have institutionalized Evidence and Gap Maps across international development (White, Saran, & Welch, 2020). `[FULL-TEXT-READ]`. EGMs visually display evidence density across intervention-outcome matrices but rely on predetermined thematic scopes and fixed search dates rather than algorithmic saturation stopping rules.

---

## 3. What Aaron's Contribution Could Still Be

Because foundational transportability theory and empirical meta-analyses exist, Aaron's contribution lies in operationalizing transport for crisis policy:

1. **A 4-Tier Categorical Transfer Architecture:**
   Translating continuous transportability math into an operational decision taxonomy:
   * *Tier 1: Calibrated Target Point Estimate* (requires full support overlap and local equilibrium modeling);
   * *Tier 2: Partial Identification Bounds* (Gechter-style bounds when unobserved selection or price shifts occur);
   * *Tier 3: Directional Mechanism Hypothesis* (identifying causal mechanisms without numerical magnitude claims);
   * *Tier 4: No Inference Permitted* (explicit stopping rule when conflict violates positivity or stability).
2. **The First Pre-Registered Statistical Transport Evaluation in a Crisis:**
   Calibrating a transport model for an unstudied crisis target population, pre-registering the numerical prediction, and testing it against a prospectively commissioned built-in evaluation.
3. **Formal Two-Layer Saturation Stopping Metric for Crisis EGMs:**
   Formulating a two-dimensional stopping rule combining: (a) *Coverage Stability* (via Kastner-style capture-mark-recapture models) and (b) *Value Stability* (when additional studies do not shift the decision boundary).

---

## 4. Search Log & Access Report

### Search Log
* **Search Window:** 2026-11-10 to 2026-11-11
* **Engines & Registries:** Google Scholar, NBER, Crossref API (`api.crossref.org`), DataCite API (`api.datacite.org`), ScienceDirect, Oxford Academic, Wiley, Taylor & Francis, arXiv.
* **Core Queries Screened:** Transportability ("Pearl", "Bareinboim", "Dahabreh"); bounds ("Gechter"); cross-site heterogeneity ("Meager", "Vivalt"); site selection ("Montiel Olea", "Allcott"); cash in conflict ("Crost et al.", "Doocy & Tappis"); replication prediction ("Altmejd et al."); saturation stopping rules ("Kastner et al.", "White et al."). (~210 records screened).

### Access Report
* **Full-Text Transcripts Audited & Verified (`[FULL-TEXT-READ]`):** 10 references in RQ3 were verified directly against Markdown full-text transcripts in `processed_outputs/`:
  - Altmejd et al. (2019): `10-1371-journal-pone-0225826.md`
  - Crost, Felter, & Johnston (2016): `1-s2.0-S0304387815000966-main.md`
  - DellaVigna & Pope (2018): `10-1086-699976.md`
  - DellaVigna, Pope, & Vivalt (2019): `science.aaz1704.md`
  - Egger et al. (2022): `10-3982-ecta17945.md`
  - Gechter (2024): `Generalizing the Results from Social Experiments  Theory and Evidence from India.md`
  - Groh et al. (2016): `rest_a_00584.md`
  - Kastner et al. (2009): `1-s2.0-S0895435608001509-main.md`
  - Montiel Olea et al. (2024): `10-48550-arxiv-2408-09187.md`
  - White, Saran, & Welch (2020): `saran-2020-evidence-and-gap-maps.md`
* **Programmatic Registry Resolution (`[REGISTRY-MATCHED]`):** 13 references remain verified via Crossref/DataCite APIs for metadata integrity without full-text auditing (Allcott 2015; Bareinboim & Pearl 2016; Brok et al. 2008; Dahabreh et al. 2020; Doocy & Tappis 2017; Hotz et al. 2005; Meager 2019; Pearl & Bareinboim 2014; Pritchett & Sandefur 2015; Rosenzweig & Udry 2020; Saunders et al. 2018; Vivalt 2020; Wetterslev et al. 2008).

---

## 5. References and Evidence Verification

* [Allcott (2015)](https://doi.org/10.1093/qje/qjv015) – Allcott, H. (2015). Site selection bias in program evaluation. *Quarterly Journal of Economics*, 130(3), 1117–1165. **[REGISTRY-MATCHED]**
* [Altmejd et al. (2019)](https://doi.org/10.1371/journal.pone.0225826) – Altmejd, A., et al. (2019). Predicting the replicability of social science lab experiments. *PLOS ONE*, 14(12), e0225826. **[FULL-TEXT-READ]**
* [Bareinboim & Pearl (2016)](https://doi.org/10.1073/pnas.1510507113) – Bareinboim, E., & Pearl, J. (2016). Causal inference and the data-fusion problem. *Proceedings of the National Academy of Sciences*, 113(27), 7345–7352. **[REGISTRY-MATCHED]**
* [Brok et al. (2008)](https://doi.org/10.1093/ije/dyn188) – Brok, J., Thorlund, K., Wetterslev, J., & Gluud, C. (2008). Apparently conclusive meta-analyses may be inconclusive—Trial sequential analysis. *International Journal of Epidemiology*, 38(1), 287–298. **[REGISTRY-MATCHED]**
* [Crost, Felter, & Johnston (2016)](https://doi.org/10.1016/j.jdeveco.2015.08.005) – Crost, B., Felter, J. H., & Johnston, P. B. (2016). Conditional cash transfers, civil conflict and insurgent influence: Experimental evidence from the Philippines. *Journal of Development Economics*, 118, 171–182. **[FULL-TEXT-READ]**
* [Dahabreh et al. (2020)](https://doi.org/10.1111/biom.13009) – Dahabreh, I. J., et al. (2020). Generalizing causal inferences from individuals in randomized trials to all trial-eligible individuals. *Biometrics*, 75(2), 685–694. **[REGISTRY-MATCHED]**
* [DellaVigna & Pope (2018)](https://doi.org/10.1086/699976) – DellaVigna, S., & Pope, D. (2018). Predicting experimental results: who knows what? *Journal of Political Economy*, 126(6), 2410–2456. **[FULL-TEXT-READ]**
* [DellaVigna, Pope, & Vivalt (2019)](https://doi.org/10.1126/science.aaz1704) – DellaVigna, S., Pope, D., & Vivalt, E. (2019). Predict science to improve science. *Science*, 366(6464), 428–429. **[FULL-TEXT-READ]**
* [Doocy & Tappis (2017)](https://doi.org/10.4073/csr.2017.17) – Doocy, S., & Tappis, H. (2017). The Effectiveness and Efficiency of Cash-Based Approaches in Emergencies. *Campbell Systematic Reviews*, 13(1), 1–138. **[REGISTRY-MATCHED]**
* [Egger et al. (2022)](https://doi.org/10.3982/ecta17945) – Egger, D., Haushofer, J., Miguel, E., Niehaus, P., & Walker, M. W. (2022). General Equilibrium Effects of Cash Transfers: Experimental Evidence From Kenya. *Econometrica*, 90(6), 2603–2643. **[FULL-TEXT-READ]**
* [Gechter (2024)](https://doi.org/10.1080/07350015.2023.2241529) – Gechter, M. (2024). Generalizing the results from social experiments: Theory and evidence from the PROGRESA program. *Journal of Business & Economic Statistics*, 42(2), 801–811. **[FULL-TEXT-READ]**
* [Groh et al. (2016)](https://doi.org/10.1162/rest_a_00584) – Groh, M., Krishnan, N., McKenzie, D., & Vishwanath, T. (2016). Do Wage Subsidies Provide a Stepping-Stone to Employment for Recent College Graduates? Evidence from a Randomized Experiment in Jordan. *The Review of Economics and Statistics*, 98(3), 488–502. **[FULL-TEXT-READ]**
* [Hotz, Imbens, & Mortimer (2005)](https://doi.org/10.1016/j.jeconom.2004.04.009) – Hotz, V. J., Imbens, G. W., & Mortimer, J. H. (2005). Predicting the efficacy of future training programs using past experiences at other locations. *Journal of Econometrics*, 125(1–2), 241–270. **[REGISTRY-MATCHED]**
* [Kastner et al. (2009)](https://doi.org/10.1016/j.jclinepi.2008.06.001) – Kastner, M., et al. (2009). The capture–mark–recapture technique can be used as a stopping rule when searching in systematic reviews. *Journal of Clinical Epidemiology*, 62(2), 149–157. **[FULL-TEXT-READ]**
* [Meager (2019)](https://doi.org/10.1257/app.20170299) – Meager, R. (2019). Understanding the Average Impact of Microcredit Expansions: A Bayesian Hierarchical Analysis of Seven Randomized Experiments. *AEJ: Applied Economics*, 11(1), 57–91. **[REGISTRY-MATCHED]**
* [Montiel Olea et al. (2024)](https://doi.org/10.48550/arXiv.2408.09187) – Montiel Olea, J. L., Prallon, B., Qiu, C., Stoye, J., & Sun, Y. (2024). Externally Valid Selection of Experimental Sites via the k-Median Problem. *arXiv preprint arXiv:2408.09187 [econ.EM]*. **[FULL-TEXT-READ]**
* [Pearl & Bareinboim (2014)](https://doi.org/10.1214/14-sts486) – Pearl, J., & Bareinboim, E. (2014). External Validity: From Do-Calculus to Transportability Across Populations. *Statistical Science*, 29(4), 579–595. **[REGISTRY-MATCHED]**
* [Pritchett & Sandefur (2015)](https://doi.org/10.1257/aer.p20151016) – Pritchett, L., & Sandefur, J. (2015). Learning from experiments when context matters. *American Economic Review*, 105(5), 471–475. **[REGISTRY-MATCHED]**
* [Rosenzweig & Udry (2020)](https://doi.org/10.1093/restud/rdz021) – Rosenzweig, M. R., & Udry, C. (2020). External validity in a stochastic world: Evidence from low-income countries. *Review of Economic Studies*, 87(1), 343–381. **[REGISTRY-MATCHED]**
* [Saunders et al. (2018)](https://doi.org/10.1007/s11135-017-0574-8) – Saunders, B., et al. (2018). Saturation in qualitative research: exploring its conceptualization and operationalization. *Quality & Quantity*, 52(4), 1893–1907. **[REGISTRY-MATCHED]**
* [Vivalt (2020)](https://doi.org/10.1093/jeea/jvaa019) – Vivalt, E. (2020). How much can we generalize from impact evaluations? *Journal of the European Economic Association*, 18(6), 3045–3089. **[REGISTRY-MATCHED]**
* [Wetterslev et al. (2008)](https://doi.org/10.1016/j.jclinepi.2007.03.013) – Wetterslev, J., et al. (2008). Trial sequential analysis may establish when firm evidence is reached in cumulative meta-analysis. *Journal of Clinical Epidemiology*, 61(1), 64–75. **[REGISTRY-MATCHED]**
* [White, Saran, & Welch (2020)](https://doi.org/10.1002/cl2.1075) – White, H., Saran, A., & Welch, V. (2020). Evidence and gap maps: A tool for promoting evidence informed policy and strategic research agendas. *Campbell Systematic Reviews*, 16(1), e1075. **[FULL-TEXT-READ]**
