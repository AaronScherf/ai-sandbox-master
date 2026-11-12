# Novelty Check: Summary of Literature Findings across the PhD Agenda (v3)

**Document:** `Novelty Check - Summary - v3.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Synthesis and comparative novelty assessment across Research Questions 1, 2, and 3, including cross-cutting evidence saturation.

---

## What Changed from v2

1. **Resolution of Bibliographic Identifiers against Crossref:**
   * Updated citations throughout the synthesis table and narrative to reflect the 10 audited Crossref/DataCite DOIs:
     * Butler & Broockman (2011, *AJPS*, DOI: `10.1111/j.1540-5907.2011.00515.x`).
     * Vivalt & Coville (2023, *JDE*, Vol. 165: 103121, DOI: `10.1016/j.jdeveco.2023.103121`).
     * Hjort et al. (2021, *AER*, 111(5): 1442–1480, DOI: `10.1257/aer.20190830`).
     * Bongers et al. (2021, *The Annals of Statistics*, 49(5): 2885–2915, DOI: `10.1214/21-aos2064`).
     * Allcott (2015, *QJE*, 130(3): 1117–1165, DOI: `10.1093/qje/qjv015`).
     * Brok et al. (2008, *IJE*, 38(1): 287–298, DOI: `10.1093/ije/dyn188`).
     * Egger et al. (2022, *Econometrica*, 90(6): 2603–2643, DOI: `10.3982/ecta17945`).
     * Groh et al. (2016, *REStat*, 98(3): 488–502, DOI: `10.1162/rest_a_00584`).
     * DellaVigna, Pope, & Vivalt (**2019**, *Science*, 366(6464): 428–429, DOI: `10.1126/science.aaz1704`).
     * Pearl & Bareinboim (2014, *Statistical Science*, 29(4): 579–595, DOI: `10.1214/14-sts486`).
2. **Substantive Clarity:**
   * Maintained all calibrated verdicts and claim bounds established in v2, incorporating the exact publisher-verified venues and publication years.

---

## 1. Research Agenda Verdict Table

| Research Question | Verdict | Strongest Prior Work | What Remains Open (Aaron's Contribution) |
|---|---|---|---|
| **RQ1: Knowledge Audit & Value of Information** | **Substantially answered in adjacent domains; open for operational crisis adaptation** | • **Health Economics VOI:** Claxton (1999), Claxton & Sculpher (2006), Fenwick et al. (2008) on EVPI/EVSI for research commissioning.<br>• **Development Evaluation VOI:** IDinsight (Allier-Gagneur et al., 2022) on simulation-based EVSI for commissioning development evaluations.<br>• **Philanthropic VOI:** Brown, Salisbury, & Ball (2025, *AEA P&P*) on GiveWell's grant-allocation VOI model.<br>• **Policymaker Demand:** Hjort et al. (2021, *AER*) on WTP for research; Vivalt & Coville (2023, *JDE*) on belief updating.<br>• **Evidence Barriers:** ALNAP (Campbell & Knox Clarke, 2019); Elrha (Smith et al., 2022). | • Translating formal EVSI into a qualitative, rapid intake protocol that screens whether external evidence can marginally shift a crisis choice.<br>• Defining the "value of no additional research" as an explicit deliverable when constraints bind.<br>• Documenting the researcher-practitioner outreach funnel as an empirical observable of revealed demand. |
| **RQ2: Decision Space, Constraints & Scenario Log-Frames** | **Partly answered** | • **Adaptive Safety Nets:** OPM SRSP synthesis (O’Brien et al., 2018); World Bank ASP (Bowen et al., 2020).<br>• **Participatory Systems Mapping:** Barbrook-Johnson & Penn (2022); Sterman (2000); Kosko (1986).<br>• **Cyclic Causal Models:** Bongers et al. (2021, *Annals of Statistics*).<br>• **Epidemiological DAG Elicitation:** Tennant et al. (2021).<br>• **Constraint Diagnostics:** Growth Diagnostics (Hausmann et al., 2008); PDIA (Andrews et al., 2013).<br>• **Deep Uncertainty:** Robust Decision Making (Lempert et al., 2003); Dynamic Adaptive Policy Pathways (Haasnoot et al., 2013). | • Synthesizing a "constraint-first" diagnostic screen that eliminates infeasible options before evidence retrieval.<br>• Developing a field-ready workshop protocol to elicit identification-compliant, time-indexed *acyclic* DAGs from practitioners.<br>• Constructing scenario-specific log-frames with node-level data inventories and calibrated cutoff thresholds that force operational pivots. |
| **RQ3: Evidence Transfer & Prospective Transportability** | **Partly answered** | • **Transport Theory:** Pearl & Bareinboim (2014, *Statistical Science*); Bareinboim & Pearl (2016); Dahabreh et al. (2020); Gechter (2024).<br>• **Empirical Heterogeneity & Site Bias:** Vivalt (2020, *JEEA*); Meager (2019, *AEJ:Applied*); Allcott (2015, *QJE*); Rosenzweig & Udry (2020, *REStud*); Montiel Olea et al. (2024, arXiv:2408.09187).<br>• **Pre-Registered Predictions:** Altmejd et al. (2019, *PLOS ONE*); DellaVigna & Pope (2018); DellaVigna, Pope, & Vivalt (2019, *Science*).<br>• **Cash in Crises:** Doocy & Tappis (2017); Crost, Felter, & Johnston (2016, *JDE*); Egger et al. (2022, *Econometrica*).<br>• **Synthesis Saturation:** Kastner et al. (2009); Brok et al. (2008, *IJE*); White, Saran, & Welch (2020). | • Defining a 4-tier categorical output architecture (point estimate, bounds, mechanism hypothesis, no inference) for crisis transfer.<br>• Executing the first prospective, pre-registered statistical transport prediction in a crisis, tested against a built-in evaluation.<br>• Formulating a formal two-layer saturation stopping metric (coverage stability and value stability) for Evidence Gap Maps. |

---

## 2. The Three Most Important Surprises

### Surprise 1: Value of Information is Established for Global Funders, But Unapplied to Frontline Crisis Design
While the mathematical foundations of Value of Information (EVPI and EVSI) have been refined for decades in Bayesian decision theory and health economics (Claxton, 1999; Fenwick et al., 2008), its application to international development has only recently emerged. Crucially, where it has appeared—such as GiveWell’s philanthropic grant-allocation model (Brown, Salisbury, & Ball, 2025) and IDinsight’s simulation-based EVSI framework (Allier-Gagneur et al., 2022)—it has been formulated for **high-level, multi-year evaluation commissioning decisions** (e.g., whether to fund an RCT before scaling a stable national program).

In contrast, **I found no literature adapting formal VOI to the operational program design workflow of frontline humanitarian and transition managers**. Humanitarian agencies and donors still treat evidence acquisition either as an unconditioned moral priority or as a rigid compliance checkbox, rather than an economic commodity whose value is strictly bounded by whether it can change an operational decision before a rapid decision window closes. Developing a rapid knowledge audit protocol that screens residual discretion and establishes formal stopping rules (identifying when further evidence synthesis has zero marginal value because constraints bind) represents a significant, unaddressed contribution.

### Surprise 2: The Methodological Chasm Between Participatory Systems Mappers and Causal Econometricians
Every prominent participatory causal mapping method utilized with policy practitioners—Participatory Systems Mapping (PSM; Barbrook-Johnson & Penn, 2022), Causal Loop Diagrams (CLDs), and Fuzzy Cognitive Maps (Kok, 2009)—prioritizes **feedback loops, circularity, and mutual causality**. In contrast, formal causal transportability theory (Pearl & Bareinboim, 2014; Dahabreh et al., 2020) relies fundamentally on **Directed Acyclic Graphs (DAGs)** to achieve d-separation, back-door adjustment, and identification of causal effects across heterogeneous populations.

While cyclic structural causal models exist mathematically (e.g., Bongers et al., 2021, *The Annals of Statistics*) using $\sigma$-separation, and feedback can be unrolled across time in dynamic Bayesian networks ($X_t \to Y_t \to X_{t+1}$), development and humanitarian participatory workshops overwhelmingly produce static cyclic loops. Consequently, the systems mapping community co-produces complex, looped mental models that cannot be used for formal causal identification, while econometricians formulate sparse DAGs in academic isolation without practitioner engagement. Developing a practical elicitation protocol that guides non-technical planners to express dynamic feedback as time-indexed, identification-compliant DAGs is an open, high-value methodological bridge.

### Surprise 3: Pre-Registration Exists for Replication Models and Human Forecasts, But Not for Causal Transport Predictions in Crises
Pre-registration has become standard practice across social science, encompassing both human expert predictions (e.g., thousands of forecasts recorded on the Social Science Prediction Platform; DellaVigna, Pope, & Vivalt, 2019, *Science*) and statistical models predicting binary lab replication outcomes (Altmejd et al., 2019). Furthermore, econometricians frequently evaluate transportability retrospectively on historical multi-site datasets (e.g., leave-one-site-out tests on Opower or microcredit; Allcott, 2015; Meager, 2019; Gechter, 2024).

However, **I found no example in development or humanitarian aid where a researcher calibrated an ex-ante causal transport model (or partial identification bounds) using external evidence and target baseline data, pre-registered numerical predicted treatment effects and bounds for an unstudied crisis target population, and prospectively evaluated those predictions against a newly fielded field trial**. 

Furthermore, a cross-cutting investigation into Evidence and Gap Maps (EGMs; White, Saran, & Welch, 2020) revealed that despite dozens of published gap maps across humanitarian and development sectors, **none have operationalized quantitative stopping rules or capture-recapture saturation metrics (such as Kastner et al., 2009; Brok et al., 2008)**. EGMs classify matrix cells as "gaps" purely based on retrieved studies, leaving researchers unable to formally distinguish whether an empty cell reflects true absence of evidence or an underpowered search.

---

## 3. Implications for the PhD Roadmap

1. **Thesis Core (Years 1–3: RQ1 & RQ2):**
   * Focusing the core doctoral thesis on **RQ1 (Knowledge Audit)** and **RQ2 (Decision Space & Scenario Log-Frames)** provides a robust, methodologically defensible scholarly contribution with minimal delivery risk.
   * Both questions can be rigorously validated through retrospective case audits using rich, multi-year archival program records from protracted crisis settings (e.g., Somalia, South Sudan, or northeast Nigeria).
   * Researcher-practitioner outreach funnels can be documented systematically as primary empirical data on institutional friction and revealed evidence demand, without conditioning PhD completion on securing active operational partnerships.
2. **Dissertation Leap & Horizon Work (Years 4–6: RQ3 & Cross-Cutting):**
   * **RQ3 (Evidence Transfer & Prospective Transport Evaluation)** and the **EGM Saturation Metrics** represent high-ambition methodological frontiers.
   * Developing the 4-tier categorical output hierarchy (point estimates, partial identification bounds, mechanism hypotheses, principled no-inference assertions) establishes a clear theoretical framework.
   * Executing the prospective pre-registered transport evaluation—pre-registering calibrated transport bounds before fielding an operational trial or quasi-experiment—provides a distinctive, high-impact research agenda bridging econometric transportability theory, humanitarian logistics, and social protection policy.
