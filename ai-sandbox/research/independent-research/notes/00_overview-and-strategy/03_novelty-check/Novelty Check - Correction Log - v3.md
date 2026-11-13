# Novelty Check: Correction Log (v3)

**Document:** `Novelty Check - Correction Log - v3.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Record of corrections applied in the v3-to-v4 correction pass across the PhD Research Agenda novelty assessment files (`RQ1 Knowledge Audit`, `RQ2 Decision Space`, `RQ3 Transfer`, and `Summary`).

---

## 1. Item 1: Montiel Olea et al. (2024), arXiv:2408.09187

### What Was Wrong in v3
In v1, v2, and v3, this paper was cited as:
> *Montiel Olea, J. L., et al. (2024). Externally valid policy choice. arXiv preprint arXiv:2408.09187 [econ.EM].*

The title "Externally valid policy choice" was incorrect.

### Primary Audit from arXiv
* **Exact URL Opened:** `https://arxiv.org/abs/2408.09187`
* **Exact Title as Displayed:** `Externally Valid Selection of Experimental Sites via the k-Median Problem`
* **Exact Authors as Displayed:** `José Luis Montiel Olea, Brenda Prallon, Chen Qiu, Jörg Stoye, Yiwei Sun`
* **Primary Abstract as Displayed:**
  > "We present a decision-theoretic justification for viewing the question of how to best choose where to experiment in order to optimize external validity as a $k$-median problem, a popular problem in computer science and operations research. In particular, when treatment effect heterogeneity across experimental and policy-relevant sites is substantial (in a sense we make precise), we present conditions under which minimizing the worst-case, welfare-based regret among all nonrandom schemes that select $k$ sites to experiment is equivalent to solving a $k$-median problem. The connection costs in the relevant $k$-median problem are given by ex-ante bounds on worst-case voltage effects between sites, and minimizing the sum of worst-case voltage effects can be cast as a linear integer program. Two empirical applications illustrate the theoretical and computational benefits of the suggested procedure."
* **Version History Check:**
  * `[v1]` Sat, 17 Aug 2024 12:56:12 UTC (5,148 KB)
  * `[v2]` Fri, 29 Aug 2025 14:27:09 UTC (2,546 KB)
  * `[v3]` Thu, 1 Oct 2026 01:05:06 UTC (2,226 KB)
  Each individual version (`abs/2408.09187v1`, `abs/2408.09187v2`, and `abs/2408.09187v3`) was fetched and inspected. All three versions display the exact same title: *"Externally Valid Selection of Experimental Sites via the k-Median Problem"*. The arXiv version history contains no earlier or alternate title. The erroneous title "Externally valid policy choice" in prior drafts was an unverified confabulation influenced by the empirical welfare maximization / policy-choice literature.
* **Substantive Description Check:**
  The one-sentence summary in the RQ3 note states: *"Montiel Olea et al. (2024) framed externally valid site selection as a minimax-regret problem equivalent to the $k$-median facility location problem."* This description directly matches the opened abstract's finding that minimizing worst-case welfare-based regret across candidate experimental sites is equivalent to solving a $k$-median problem via linear integer programming.

---

## 2. Item 2: Verification Tag Taxonomy & Reclassification

### Root Cause of Misleading v3 Description
In the v3 notes, all 51 references were marked `[VERIFIED]`, and Section 4 stated that full publisher pages had been audited. In reality, as acknowledged in the v2 report, an automated Python script (`check_all_dois.py`) resolved the DOIs against the live REST APIs of Crossref (`api.crossref.org`) and DataCite (`api.datacite.org`). This script verified that the DOI returned HTTP status 200 and that the registered title and primary author matched the citation strings. The script did **not** fetch, render, or read the full article texts or publisher landing pages. Claiming that "full publisher pages audited" and marking them `[VERIFIED]` obscured the boundary between programmatic identifier resolution and actual reading of findings.

### New Tag Taxonomy
To ensure complete epistemic honesty, the verification tag vocabulary has been updated across all v4 files:

| Tag | Definition | Count |
| :--- | :--- | :---: |
| **`[REGISTRY-MATCHED]`** | DOI resolved at Crossref or DataCite; registered title and first author match citation. Nothing read. | **41** |
| **`[ABSTRACT-READ]`** | Abstract opened at a publisher or preprint page; substantive description in the note confirmed against abstract text. | **1** |
| **`[INSTITUTIONAL-URL]`** | Official institutional repository, organization publication page, or book overview page opened (no DOI registry check). | **9** |
| **`[FULL-TEXT-READ]`** | Full paper text read and specific supporting passages verified. | **0** |
| **`[UNVERIFIED]`** | Identifier unverified or unresolved. | **0** |
| **Total** | | **51** |

---

## 3. Counts per Tag by Research Question Note

| Document | Total Refs | `[REGISTRY-MATCHED]` | `[ABSTRACT-READ]` | `[INSTITUTIONAL-URL]` | `[FULL-TEXT-READ]` | `[UNVERIFIED]` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RQ1 Knowledge Audit** | 15 | 11 | 0 | 4 | 0 | 0 |
| **RQ2 Decision Space** | 13 | 8 | 0 | 5 | 0 | 0 |
| **RQ3 Transfer** | 23 | 22 | 1 | 0 | 0 | 0 |
| **Total Across All Notes** | **51** | **41** | **1** | **9** | **0** | **0** |

### Breakdown of References by Tag

#### RQ1 Knowledge Audit (15 References)
* `[REGISTRY-MATCHED]` (11): Alonso-Coello et al. (2016); Brown, Salisbury, & Ball (2025); Butler & Broockman (2011); Claxton (1999); Claxton & Sculpher (2006); Coburn & Penuel (2016); Coughlan de Perez et al. (2015); Fenwick, Claxton, & Sculpher (2008); Hjort et al. (2021); Lopez et al. (2020); Vivalt & Coville (2023).
* `[INSTITUTIONAL-URL]` (4): Campbell & Knox Clarke (2019, ALNAP); Henrick et al. (2017, W.T. Grant Foundation); IDinsight / Allier-Gagneur et al. (2022, IDinsight Blog); Smith, Swithern, & Harrison (2022, Elrha).

#### RQ2 Decision Space (13 References)
* `[REGISTRY-MATCHED]` (8): Andrews, Pritchett, & Woolcock (2013); Barbrook-Johnson & Penn (2022); Bongers et al. (2021); Bowen et al. (2020); Haasnoot et al. (2013); Hausmann, Rodrik, & Velasco (2008); Kok (2009); Tennant et al. (2021).
* `[INSTITUTIONAL-URL]` (5): Bakewell & Garbutt (2005, INTRAC); Ben-Haim (2006, ScienceDirect / Academic Press); Hummelbrunner (2010, FASID); Lempert, Popper, & Bankes (2003, RAND Corporation); O'Brien et al. (2018, OPM / DFID).

#### RQ3 Transfer (23 References)
* `[REGISTRY-MATCHED]` (22): Allcott (2015); Altmejd et al. (2019); Bareinboim & Pearl (2016); Brok et al. (2008); Crost, Felter, & Johnston (2016); Dahabreh et al. (2020); DellaVigna & Pope (2018); DellaVigna, Pope, & Vivalt (2019); Doocy & Tappis (2017); Egger et al. (2022); Gechter (2024); Groh et al. (2016); Hotz, Imbens, & Mortimer (2005); Kastner et al. (2009); Meager (2019); Pearl & Bareinboim (2014); Pritchett & Sandefur (2015); Rosenzweig & Udry (2020); Saunders et al. (2018); Vivalt (2020); Wetterslev et al. (2008); White, Saran, & Welch (2020).
* `[ABSTRACT-READ]` (1): Montiel Olea et al. (2024, arXiv:2408.09187).

---

## 4. Claims Resting on `[REGISTRY-MATCHED]` References Only

In compliance with the correction protocol, all claims that depend on what a paper found (and not merely on its bibliographic existence) where the paper was verified solely via registry resolution are listed below. Each corresponding claim in the v4 notes has been tagged with `*(Claim rests on [REGISTRY-MATCHED] reference only)*`.

### Claims in RQ1: Knowledge Audit
1. **Bayesian VOI in Health Economics:** Research should be commissioned only when EVSI exceeds research costs, treating adoption without evaluation as an alternative to clinical trials.
   * *Sources:* Claxton (1999); Claxton & Sculpher (2006). `[REGISTRY-MATCHED]`
2. **Separating Evidence Value from Implementation Value:** Distinguishing the expected payoff of acquiring more evidence from the payoff of investing in implementation adherence.
   * *Sources:* Fenwick, Claxton, & Sculpher (2008). `[REGISTRY-MATCHED]`
3. **Philanthropic VOI Allocation:** GiveWell's calculation of EVPI/EVSI to allocate capital between direct program grants and field evaluations.
   * *Sources:* Brown, Salisbury, & Ball (2025). `[REGISTRY-MATCHED]`
4. **Physical Disaster Cost-Loss Thresholds:** Cost-loss decision analysis applied to extreme weather forecasts for forecast-based disaster financing in Peru and globally.
   * *Sources:* Coughlan de Perez et al. (2015); Lopez et al. (2020). `[REGISTRY-MATCHED]`
5. **GRADE Evidence-to-Decision Criteria:** Structured multi-criteria frameworks (problem priority, effect magnitude, resources, equity, acceptability, feasibility).
   * *Sources:* Alonso-Coello et al. (2016). `[REGISTRY-MATCHED]`
6. **Willingness to Pay for Evidence:** Brazilian municipal policymakers exhibit positive willingness to pay for research via BDM mechanisms, valuing larger samples higher, with research summaries increasing policy adoption by 10 percentage points.
   * *Sources:* Hjort et al. (2021). `[REGISTRY-MATCHED]`
7. **Asymmetric Belief Updating & Variance Neglect:** Development policymakers update beliefs significantly more in response to positive estimates than negative ones, and disregard sample sizes.
   * *Sources:* Vivalt & Coville (2023). `[REGISTRY-MATCHED]`
8. **Political Science Outreach Audit Rates:** Unsolicited outreach to public officials yields response rates between 15% and 50%.
   * *Sources:* Butler & Broockman (2011). `[REGISTRY-MATCHED]`
9. **Research-Practice Partnership Trust Preconditions:** Partnerships require prolonged relational trust and formal institutional alignment rather than cold outreach.
   * *Sources:* Coburn & Penuel (2016). `[REGISTRY-MATCHED]` (with Henrick et al., 2017 `[INSTITUTIONAL-URL]`).

### Claims in RQ2: Decision Space
1. **Adaptive Social Protection Typologies:** Frameworks defining social safety net adaptations (vertical/horizontal expansion, piggybacking, shadow alignment).
   * *Sources:* Bowen et al. (2020). `[REGISTRY-MATCHED]` (with O'Brien et al., 2018 `[INSTITUTIONAL-URL]`).
2. **Dynamic Adaptive Policy Pathways:** Adaptation tipping points, transient policy trees, and sell-by dates under deep climate uncertainty.
   * *Sources:* Haasnoot et al. (2013). `[REGISTRY-MATCHED]`
3. **Participatory Systems Mapping Protocols:** Co-producing causal loop diagrams with policymakers.
   * *Sources:* Barbrook-Johnson & Penn (2022). `[REGISTRY-MATCHED]`
4. **Applied DAG Elicitation Guidelines:** Avoiding collider bias and intermediate confounder conditioning in causal graphs.
   * *Sources:* Tennant et al. (2021). `[REGISTRY-MATCHED]`
5. **Foundations of Cyclic Structural Causal Models:** Mathematical representation of feedback loops via $\sigma$-separation and unique solvability.
   * *Sources:* Bongers et al. (2021). `[REGISTRY-MATCHED]`
6. **Growth Diagnostics Decision Trees:** Constraint-first prioritization identifying the single most binding impediment to private investment.
   * *Sources:* Hausmann, Rodrik, & Velasco (2008). `[REGISTRY-MATCHED]`
7. **Problem-Driven Iterative Adaptation:** Deconstructing institutional failure via fishbone diagrams and iterative authorization.
   * *Sources:* Andrews, Pritchett, & Woolcock (2013). `[REGISTRY-MATCHED]`
8. **Fuzzy Cognitive Maps for Scenarios:** Translating stakeholder mental models into semi-quantitative scenario simulations.
   * *Sources:* Kok (2009). `[REGISTRY-MATCHED]`

### Claims in RQ3: Evidence Transfer & Transportability
1. **Selection Diagrams and Do-Calculus Transportability:** Necessary and sufficient non-parametric conditions for transportability across populations via selection nodes.
   * *Sources:* Pearl & Bareinboim (2014); Bareinboim & Pearl (2016). `[REGISTRY-MATCHED]`
2. **Trial-to-Target Conditional Exchangeability:** Generalizing trial findings to target populations using inverse odds weighting, g-formula, and doubly robust estimators.
   * *Sources:* Dahabreh et al. (2020). `[REGISTRY-MATCHED]`
3. **Partial Identification Bounds under Relaxed Assumptions:** Bounding target treatment effects under relaxed rank invariance without point identification.
   * *Sources:* Gechter (2024). `[REGISTRY-MATCHED]`
4. **Breakdown of Reweighting under Unobserved Market Interactions:** Location-transfer reweighting fails when unobserved site characteristics or local equilibrium prices interact with treatment.
   * *Sources:* Hotz, Imbens, & Mortimer (2005); Rosenzweig & Udry (2020). `[REGISTRY-MATCHED]`
5. **Empirical Effect Heterogeneity across Sites:** Documenting substantial cross-site dispersion across international development trials.
   * *Sources:* Vivalt (2020); Meager (2019); Pritchett & Sandefur (2015). `[REGISTRY-MATCHED]`
6. **Site Selection Bias in Multi-Site Trials:** Non-random site selection produces severe external validity bias across 111 energy deployments.
   * *Sources:* Allcott (2015). `[REGISTRY-MATCHED]`
7. **Expert Forecasting Failures in Development:** Academic experts and practitioners systematically mispredict intervention impacts and overestimate post-subsidy employment persistence.
   * *Sources:* Groh et al. (2016); DellaVigna & Pope (2018). `[REGISTRY-MATCHED]`
8. **Pre-Registered Expert Prediction Platforms:** Social Science Prediction Platform systematically records expert prior distributions.
   * *Sources:* DellaVigna, Pope, & Vivalt (2019). `[REGISTRY-MATCHED]`
9. **Machine Learning Predictors of Lab Replication:** Trained models predict binary replication success in experimental psychology and economics with 65–70% accuracy.
   * *Sources:* Altmejd et al. (2019). `[REGISTRY-MATCHED]`
10. **Evidence Thinness for Cash in Conflict:** Cash transfers demonstrate robust food security impacts in natural disasters but possess thin, fragmented evidence in active armed conflict.
    * *Sources:* Doocy & Tappis (2017). `[REGISTRY-MATCHED]`
11. **Conflict Escalation from Conditional Aid:** Conditional cash transfers in the Philippines increased insurgent violence due to rebel sabotage incentives.
    * *Sources:* Crost, Felter, & Johnston (2016). `[REGISTRY-MATCHED]`
12. **General Equilibrium Multiplier Spillovers:** Unconditional cash transfers generate large local fiscal multipliers (2.5) with minimal price inflation.
    * *Sources:* Egger et al. (2022). `[REGISTRY-MATCHED]`
13. **Evidence Gap Maps Lack Stopping Rules:** EGMs map evidence visually across matrices but lack formal statistical stopping criteria.
    * *Sources:* White, Saran, & Welch (2020). `[REGISTRY-MATCHED]`
14. **Capture-Mark-Recapture Search Completeness:** Using capture-recapture ecology estimators to establish systematic review stopping rules.
    * *Sources:* Kastner et al. (2009). `[REGISTRY-MATCHED]`
15. **Trial Sequential Analysis Monitoring Boundaries:** Applying sequential monitoring boundaries to cumulative meta-analyses to avoid false-positive conclusions.
    * *Sources:* Brok et al. (2008); Wetterslev et al. (2008). `[REGISTRY-MATCHED]`
16. **Qualitative Saturation Models:** Differentiating four operational models of saturation in qualitative research.
    * *Sources:* Saunders et al. (2018). `[REGISTRY-MATCHED]`

---

## 5. Verification Audit Log

All 42 DOIs were programmatically verified against Crossref (`api.crossref.org`) and DataCite (`api.datacite.org`) using `check_all_dois.py`. Montiel Olea et al. (2024) was directly verified by opening `https://arxiv.org/abs/2408.09187` and auditing its abstract and version history.
