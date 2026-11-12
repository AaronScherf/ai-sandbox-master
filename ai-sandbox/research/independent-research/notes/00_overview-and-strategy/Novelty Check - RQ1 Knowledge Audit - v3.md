# Novelty Check: RQ1 — Knowledge Audit and Value of Information (v3)

**Document:** `Novelty Check - RQ1 Knowledge Audit - v3.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Literature novelty assessment for PhD Research Question 1 (Knowledge audit, value of information, revealed demand, and partner outreach in humanitarian and transition settings).

---

## What Changed from v2

1. **Resolution of Bibliographic Identifiers against Crossref:**
   * Corrected Butler & Broockman (2011) DOI from `...00518.x` (which resolved to Gaines & Kuklinski) to `10.1111/j.1540-5907.2011.00515.x` (*American Journal of Political Science*, 55(3): 463–477).
   * Corrected Vivalt & Coville (2023) DOI from `...103074` (which resolved to Augsburg et al.) to `10.1016/j.jdeveco.2023.103121`, updating the volume to *Journal of Development Economics*, Vol. 165, Art. 103121.
   * Corrected Hjort et al. (2021) DOI from non-existent `10.1257/aer.20191834` to `10.1257/aer.20190830` (*American Economic Review*, 111(5): 1442–1480).
   * Fixed string error from v2: correctly cited the v1 error as `10.1016/j.ijdrr.2020.101524` and the verified correction as `10.1016/j.wace.2018.03.006` (*Weather and Climate Extremes*, Vol. 27, Art. 100167).
2. **Programmatic Crossref Verification:**
   * All 11 DOIs in this note have been verified via automated Crossref API resolution (`check_all_dois.py`), matching title and first author with 0 errors.

---

## 1. Verdict

**Verdict: Substantially answered in adjacent domains (health economics, development evaluation consulting, philanthropic grant allocation); open for operational crisis adaptation.**

The mathematical apparatus of Value of Information (Expected Value of Perfect Information [EVPI] and Expected Value of Sample Information [EVSI]) is mature in Bayesian decision theory and operationalized in health technology assessment. In international development and humanitarian aid:
- VOI has been adapted by evaluation consultancies (IDinsight's simulation-based VOI tool) to evaluate whether to commission studies before program scale-up;
- VOI is used by philanthropic funders (GiveWell) to allocate capital between direct delivery grants and new randomized trials;
- Cost-loss models have been applied to physical forecast triggers in anticipatory action (e.g., flood/drought thresholds).

However, **I found no literature adapting formal VOI to the operational intake and program design workflow of frontline humanitarian and transition decision-makers**. Existing development VOI models assume multi-year programmatic scale-up horizons and formal evaluation commissioning cycles. They do not address the acute operational realities of protracted crises: rapid decision windows, severe external delivery constraints (logistics, security, ear-marking), unmeasured local baseline data, and the high opportunity cost of delaying aid. Operationalizing a lightweight knowledge audit that screens residual decision space, assesses whether marginal external evidence is worth the time to retrieve and analyze, and uses researcher-partner outreach conversion as an empirical indicator of revealed demand remains open.

---

## 2. Findings on Sub-Questions

### Sub-Question 1: Has value-of-information analysis (EVPI/EVSI) been applied to decisions about commissioning evidence in humanitarian or development programme design?
* **Category Tag:** **(a) Settled in adjacent fields (health economics); (b) Active research frontier in development evaluation and philanthropy; (c) Open in frontline humanitarian program design.**
* **Findings:**
  * *Health Economics:* Claxton (1999) and Claxton & Sculpher (2006) established Bayesian VOI in health technology assessment, proving research should be commissioned only when EVSI exceeds expected research costs, treating adoption without evaluation as an alternative to clinical trials. Fenwick et al. (2008) distinguished acquiring evidence from investing in implementation.
  * *Development Evaluation Consulting:* IDinsight (Allier-Gagneur et al., March 2022) developed a simulation-based VOI methodology to evaluate whether an NGO or government should commission an evaluation before scaling up, defunding, or redesigning a program, accounting for evaluation costs and decision deadlines.
  * *Philanthropic Grant Allocation:* Brown, Salisbury, & Ball (2025) describe how GiveWell operationalizes VOI to allocate philanthropic capital between direct program grants and field evaluations, calculating whether the expected probability of updating priors justifies research expenditures.
  * *Anticipatory Humanitarian Action:* In disaster risk reduction, cost-loss decision models are applied to physical forecast triggers (Coughlan de Perez et al., 2015; Lopez et al., 2020), balancing false-alarm costs against unmitigated losses. However, these evaluate physical climate forecasts, not program evidence.
  * *Status for Frontline Crisis Programme Design:* Published applications of VOI in development focus on multi-year evaluation commissioning for stable social programs. No literature adapts EVPI/EVSI to frontline humanitarian planners choosing delivery mechanisms under acute conflict and logistical constraints.

### Sub-Question 2: Existing frameworks for auditing a decision-maker's evidence needs and evidence use
* **Category Tag:** **(b) Active research frontier in evidence-to-decision frameworks; (a) Settled in empirical diagnostics of humanitarian evidence barriers.**
* **Findings:**
  * *Evidence-to-Decision (EtD) Frameworks:* The GRADE Working Group developed Evidence-to-Decision frameworks for health and clinical policy (Alonso-Coello et al., 2016). These structured frameworks evaluate criteria such as problem priority, magnitude of effects, resource use, equity, acceptability, and feasibility. However, GRADE EtD presupposes that a systematic review already exists; it does not calculate the marginal value of searching for further evidence or audit whether the decision-maker has the time and authority to use it.
  * *Humanitarian Evidence Uptake and Operational Reality:* ALNAP's empirical study of humanitarian decision-makers (*Beyond Assumptions*, Campbell & Knox Clarke, 2019) observed that only 3.4% of recorded operational decisions referenced formal research or evaluations, with decisions driven instead by procedural rules, mandate inertia, and recognition-primed heuristics under time pressure. Elrha's synthesis (*From Knowing to Doing*, Smith et al., 2022) identified tight operational windows, funding inflexibility, and top-down donor requirements as the principal structural obstacles to evidence uptake.
  * *Evidence Readiness Frameworks:* Evidence clearinghouses (such as NESTA Standards of Evidence or Pew Results First) classify the rigor of existing evidence behind an intervention (Levels 1 to 5), but do not assess a decision-maker's absorption capacity, decision constraints, or local relevance.

### Sub-Question 3: Studies of policymakers' or practitioners' demand for or willingness to pay for research, and consultant commissioning
* **Category Tag:** **(a) Settled / active empirical literature in political economy and public economics.**
* **Findings:**
  * *Experimental Willingness to Pay for Evidence:* Hjort, Moreira, Rao, & Santini (2021) conducted field experiments with 2,150 Brazilian municipal officials using Becker-DeGroot-Marschak (BDM) mechanisms. They proved that policymakers exhibit positive, substantial willingness to pay for research evidence, valuing larger-sample trials higher than smaller ones, and that providing research summaries increased policy adoption by 10 percentage points.
  * *Asymmetric Belief Updating:* Vivalt & Coville (2023) surveyed over 100 development policymakers (including World Bank and IDB staff) and documented systematic cognitive biases: policymakers update beliefs significantly more in response to positive impact estimates ("good news") than negative ones, and exhibit variance neglect by disregarding sample sizes and dispersion.
  * *Consultant Commissioning:* Research in public administration indicates that hiring external consultants or think tanks is often driven by institutional legitimacy, donor compliance, and temporary surge staffing rather than calculated information optimization (Sturdy, 1997). ALNAP (2019) notes that operational humanitarian staff frequently treat commissioned external evaluations as backward-looking accountability rituals rather than forward-looking design tools.

### Sub-Question 4: Response and uptake rates for researcher-practitioner partnership outreach
* **Category Tag:** **(a) Settled in political science audit studies; (c) Open for cold outreach conversion in humanitarian evidence adaptation.**
* **Findings:**
  * *Political Science Correspondence Studies:* Field audit studies evaluating public official response rates to unsolicited inquiries typically report response rates between 15% and 50% (e.g., Butler & Broockman, 2011), driven by perceived constituent alignment and organizational prestige.
  * *Research-Practice Partnerships (RPPs):* Educational and social policy literature on RPPs (Coburn & Penuel, 2016; Henrick et al., 2017) documents that partnerships rarely succeed through cold outreach; they depend on prolonged relational trust, institutional MOUs, and aligned governance structures.
  * *Humanitarian Partnership Funnel:* I found no published empirical studies that document conversion funnels for cold or semi-cold researcher outreach offering external evidence adaptation support to humanitarian program managers (contacts approached -> initial replies -> scoping conversations -> fit determinations -> active collaborations). Documenting this conversion pipeline provides valuable empirical evidence on revealed demand and institutional receptivity.

---

## 3. What Aaron's Contribution Could Still Be

Because VOI has been established in health economics and large-scale development evaluation planning, the PhD contribution lies in operational adaptation:

1. **Adapting VOI to Frontline Humanitarian Crisis Operations:**
   Developing a lightweight, decision-theoretic knowledge audit protocol tailored to prolonged and recurrent crises. Instead of computationally heavy Monte Carlo simulations, the tool screens:
   * *Residual Discretion:* Do donor mandates, security constraints, and logistics leave open choices?
   * *Separability:* Can existing operational monitoring data and accessible evidence distinguish between candidate interventions?
   * *Decision Horizons:* Will external evidence or a new pilot be completed before the operational window closes?
   * *Opportunity Cost of Delay:* What is the expected human welfare loss of postponing aid delivery to acquire more information?
2. **The "Value of No Additional Research" as an Explicit Decision Rule:**
   Establishing formal stopping criteria that show when spending resources on further assessments or syntheses has zero or negative marginal value due to binding delivery constraints.
3. **Empirical Measurement of Revealed Evidence Demand:**
   Publishing the documented outreach conversion funnel to humanitarian agencies, quantifying where and why evidence uptake breaks down.

---

## 4. Search Log & Access Report

### Search Log
* **Search Window:** 2026-11-10 to 2026-11-11
* **Engines & Registries:** Google Scholar, NBER, RePEc/IDEAS, Crossref API (`api.crossref.org`), PubMed, Devpolicy Blog, ALNAP, GiveWell, IDinsight.
* **Core Queries Screened:**
  * `"value of information" ("humanitarian" OR "development") ("EVPI" OR "EVSI")` (44 results)
  * `site:idinsight.org "value of information"` & `site:givewell.org "value of information"`
  * `"GRADE Evidence to Decision" OR "EtD" framework` (20 results)
  * `"Hjort" "municipalities" "evidence" OR "willingness to pay"` (15 results)
  * `"Vivalt" "Coville" "policymakers" "update"` (15 results)
* **Total Records Screened:** ~180 candidate records across all queries.

### Access Report
* **Full Text / Primary Landing Pages Audited & Resolved via Crossref:**
  * Alonso-Coello et al. (2016): BMJ via DOI `10.1136/bmj.i2016`.
  * Brown, Salisbury, & Ball (2025): AEA P&P via DOI `10.1257/pandp.20251021`.
  * Butler & Broockman (2011): AJPS via DOI `10.1111/j.1540-5907.2011.00515.x`.
  * Campbell & Knox Clarke (2019): ALNAP study repository report (`https://www.alnap.org/help-library/beyond-assumptions-humanitarian-decision-making-in-practice`).
  * Claxton (1999): ScienceDirect via DOI `10.1016/s0167-6296(98)00039-3`.
  * Claxton & Sculpher (2006): Springer/Adis via DOI `10.2165/00019053-200624110-00003`.
  * Coughlan de Perez et al. (2015): NHESS via DOI `10.5194/nhess-15-895-2015`.
  * Fenwick, Claxton, & Sculpher (2008): SAGE via DOI `10.1177/0272989x07308751`.
  * Hjort et al. (2021): AER via DOI `10.1257/aer.20190830`.
  * IDinsight / Allier-Gagneur et al. (2022): IDinsight blog (`https://www.idinsight.org/blog/idinsights-new-value-of-information-work/`).
  * Lopez et al. (2020): ScienceDirect via DOI `10.1016/j.wace.2018.03.006`.
  * Smith et al. (2022): Elrha research database report (`https://www.elrha.org/researchdatabase/from-knowing-to-doing-evidence-use-in-the-humanitarian-sector/`).
  * Vivalt & Coville (2023): ScienceDirect via DOI `10.1016/j.jdeveco.2023.103121`.
  * Henrick et al. (2017): William T. Grant Foundation repository (`https://wtgrantfoundation.org/library/uploads/2017/10/RPP-Five-Dimensions-of-Effectiveness.pdf`).
* **Abstract Only:**
  * Coburn & Penuel (2016): SAGE journals page (DOI `10.3102/0013189X16631750`).

---

## 5. References and Evidence Verification

* [Alonso-Coello et al. (2016)](https://doi.org/10.1136/bmj.i2016)  
  *Alonso-Coello, P., Schünemann, H. J., Moberg, J., et al. (2016). GRADE Evidence to Decision (EtD) frameworks: a systematic and transparent approach to making well informed healthcare choices. 1: Introduction. BMJ, 353, i2016.*  
  Establishes structured multi-criteria decision framework for moving from evidence to policy choices. **[VERIFIED]**

* [Brown, Salisbury, & Ball (2025)](https://doi.org/10.1257/pandp.20251021)  
  *Brown, D., Salisbury, M., & Ball, E. (2025). Evidence-based funding and the value of information: A case study from GiveWell. AEA Papers and Proceedings, 115, 308–312.*  
  Applies VOI to philanthropic grant allocation between program funding and RCTs. **[VERIFIED]**

* [Butler & Broockman (2011)](https://doi.org/10.1111/j.1540-5907.2011.00515.x)  
  *Butler, D. M., & Broockman, D. E. (2011). Do Politicians Racially Discriminate Against Constituents? A Field Experiment on State Legislators. American Journal of Political Science, 55(3), 463–477.*  
  Benchmark methodology for measuring public official response rates to unsolicited outreach. **[VERIFIED]**

* [Campbell & Knox Clarke (2019)](https://www.alnap.org/help-library/beyond-assumptions-humanitarian-decision-making-in-practice)  
  *Campbell, L., & Knox Clarke, P. (2019). Beyond assumptions: Humanitarian decision-making in practice. ALNAP/ODI, London.*  
  Documents empirically that formal evidence is referenced in only 3.4% of humanitarian operational decisions. **[VERIFIED]**

* [Claxton (1999)](https://doi.org/10.1016/s0167-6296(98)00039-3)  
  *Claxton, K. (1999). The irrelevance of inference: a decision-making approach to the value of information. Journal of Health Economics, 18(3), 341–364.*  
  Foundational formulation establishing EVPI/EVSI as the rule for commissioning evaluation research. **[VERIFIED]**

* [Claxton & Sculpher (2006)](https://doi.org/10.2165/00019053-200624110-00003)  
  *Claxton, K., & Sculpher, M. (2006). Using value of information analysis to prioritise health research: some lessons from recent UK experience. PharmacoEconomics, 24(11), 1055–1068.*  
  Implementation lessons for calculating EVSI to prioritize research investments against policy adoption. **[VERIFIED]**

* [Coburn & Penuel (2016)](https://doi.org/10.3102/0013189X16631750)  
  *Coburn, C. E., & Penuel, W. R. (2016). Research–practice partnerships in education: Outcomes, dynamics, and open questions. Educational Researcher, 45(1), 48–54.*  
  Reviews conditions for successful researcher-practitioner partnerships, emphasizing relational trust over cold outreach. **[ABSTRACT-ONLY]**

* [Coughlan de Perez et al. (2015)](https://doi.org/10.5194/nhess-15-895-2015)  
  *Coughlan de Perez, E., van den Hurk, B., van Aalst, M. K., et al. (2015). Forecast-based financing: an approach for catalyzing humanitarian action based on extreme weather forecasts. Natural Hazards and Earth System Sciences, 15(4), 895–904.*  
  Applies cost-loss decision analysis to extreme weather thresholds for anticipatory disaster financing. **[VERIFIED]**

* [Fenwick, Claxton, & Sculpher (2008)](https://doi.org/10.1177/0272989x07308751)  
  *Fenwick, E., Claxton, K., & Sculpher, M. (2008). The value of implementation and the value of information: combined and uneven development. Medical Decision Making, 28(1), 21–32.*  
  Separates the expected payoff of acquiring more evidence from the payoff of investing in implementation adherence. **[VERIFIED]**

* [Henrick et al. (2017)](https://wtgrantfoundation.org/library/uploads/2017/10/RPP-Five-Dimensions-of-Effectiveness.pdf)  
  *Henrick, E. C., Cobb, P., Penuel, W. R., Jackson, K., & Clark, T. (2017). Assessing research-practice partnerships: Five dimensions of effectiveness. William T. Grant Foundation, New York.*  
  Synthesizes operational framework for institutional researcher-practitioner collaboration. **[VERIFIED]**

* [Hjort et al. (2021)](https://doi.org/10.1257/aer.20190830)  
  *Hjort, J., Moreira, D., Rao, G., & Santini, J. F. (2021). How Research Affects Policy: Experimental Evidence from 2,150 Brazilian Municipalities. American Economic Review, 111(5), 1442–1480.*  
  Proves positive willingness to pay for research evidence among local policymakers via BDM field experiments. **[VERIFIED]**

* [IDinsight / Allier-Gagneur et al. (2022)](https://www.idinsight.org/blog/idinsights-new-value-of-information-work/)  
  *Allier-Gagneur, Z., Devlin-Foltz, S., Sobti, N., & Shotland, M. (2022). Improving decisions about evidence: IDinsight’s new Value of Information work. IDinsight Blog, March 30, 2022.*  
  Presents simulation-based EVSI methodology for deciding whether to commission an evaluation before scaling up or defunding development programs. **[VERIFIED]**

* [Lopez et al. (2020)](https://doi.org/10.1016/j.wace.2018.03.006)  
  *Lopez, A., Coughlan de Perez, E., Bazo, J., Suarez, P., et al. (2020). Bridging the gap between climate science and humanitarian action: An analysis of forecast-based financing in Peru. Weather and Climate Extremes, 27, 100167.*  
  Operationalizes cost-loss decision framework for flood forecasting and anticipatory funding triggers in Peru. **[VERIFIED]**

* [Smith, Swithern, & Harrison (2022)](https://www.elrha.org/researchdatabase/from-knowing-to-doing-evidence-use-in-the-humanitarian-sector/)  
  *Smith, G., Swithern, S., & Harrison, K. (2022). From knowing to doing: Evidence use in the humanitarian sector. Elrha, London.*  
  Diagnoses structural barriers to evidence uptake in humanitarian action, emphasizing timeline and funding rigidity. **[VERIFIED]**

* [Vivalt & Coville (2023)](https://doi.org/10.1016/j.jdeveco.2023.103121)  
  *Vivalt, E., & Coville, A. (2023). How do policymakers update their beliefs? Journal of Development Economics, 165, 103121.*  
  Demonstrates asymmetric updating and variance neglect among development policymakers evaluating empirical research. **[VERIFIED]**
