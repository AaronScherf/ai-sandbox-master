# Novelty Check: Summary of Literature Findings across the PhD Agenda (v4)

**Document:** `Novelty Check - Summary - v4.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Synthesis and comparative novelty assessment across Research Questions 1, 2, and 3, including cross-cutting evidence saturation.

---

## What Changed from v3

1. **Epistemic Tag Vocabulary:** Transitioned all references to the 5-tier taxonomy: `[REGISTRY-MATCHED]`, `[ABSTRACT-READ]`, `[INSTITUTIONAL-URL]`, `[FULL-TEXT-READ]`, and `[UNVERIFIED]`. Across the 51 references, 41 are `[REGISTRY-MATCHED]`, 1 is `[ABSTRACT-READ]`, and 9 are `[INSTITUTIONAL-URL]`. None are `[FULL-TEXT-READ]`.
2. **Montiel Olea et al. (2024) Audit:** Verified on arXiv (`https://arxiv.org/abs/2408.09187`) that the exact title is *"Externally Valid Selection of Experimental Sites via the k-Median Problem"*, and authors are Montiel Olea, Prallon, Qiu, Stoye, and Sun. Confirmed across all three versions (`v1`, `v2`, `v3`). Re-tagged as `[ABSTRACT-READ]`.
3. **Audit of Registry-Matched Claims:** Explicitly identified substantive findings in the agenda that rest solely on `[REGISTRY-MATCHED]` citations where full texts were not read.

---

## 1. Research Agenda Verdict Table

| Research Question | Verdict | Strongest Prior Work (with Provenance Tags) | What Remains Open (Aaron's Contribution) |
|---|---|---|---|
| **RQ1: Knowledge Audit & Value of Information** | **Substantially answered in adjacent domains; open for operational crisis adaptation** | • **Health Economics VOI:** Claxton (1999); Claxton & Sculpher (2006); Fenwick et al. (2008) on EVPI/EVSI for research commissioning. `[REGISTRY-MATCHED]`<br>• **Development Evaluation VOI:** IDinsight (Allier-Gagneur et al., 2022) on simulation-based EVSI for commissioning development evaluations. `[INSTITUTIONAL-URL]`<br>• **Philanthropic VOI:** Brown, Salisbury, & Ball (2025, *AEA P&P*) on GiveWell's grant-allocation VOI model. `[REGISTRY-MATCHED]`<br>• **Policymaker Demand:** Hjort et al. (2021, *AER*) on WTP for research; Vivalt & Coville (2023, *JDE*) on belief updating. `[REGISTRY-MATCHED]`<br>• **Evidence Barriers:** ALNAP (Campbell & Knox Clarke, 2019); Elrha (Smith et al., 2022). `[INSTITUTIONAL-URL]` | • Translating formal EVSI into a qualitative, rapid intake protocol screening whether external evidence can marginally shift a crisis choice.<br>• Defining the "value of no additional research" as an explicit deliverable when constraints bind.<br>• Documenting researcher-practitioner outreach funnels as an empirical observable of revealed demand. |
| **RQ2: Decision Space, Constraints & Scenario Log-Frames** | **Partly answered** | • **Adaptive Safety Nets:** OPM SRSP synthesis (O'Brien et al., 2018) `[INSTITUTIONAL-URL]`; World Bank ASP (Bowen et al., 2020) `[REGISTRY-MATCHED]`.<br>• **Participatory Systems Mapping:** Barbrook-Johnson & Penn (2022). `[REGISTRY-MATCHED]`<br>• **Cyclic Causal Models:** Bongers et al. (2021, *Annals of Statistics*). `[REGISTRY-MATCHED]`<br>• **Epidemiological DAG Elicitation:** Tennant et al. (2021). `[REGISTRY-MATCHED]`<br>• **Constraint Diagnostics:** Growth Diagnostics (Hausmann et al., 2008) `[REGISTRY-MATCHED]`; PDIA (Andrews et al., 2013) `[REGISTRY-MATCHED]`.<br>• **Deep Uncertainty:** Robust Decision Making (Lempert et al., 2003); Info-Gap (Ben-Haim, 2006). `[INSTITUTIONAL-URL]`<br>• **Dynamic Pathways:** Dynamic Adaptive Policy Pathways (Haasnoot et al., 2013). `[REGISTRY-MATCHED]` | • Synthesizing a "constraint-first" diagnostic screen that eliminates infeasible options before evidence retrieval.<br>• Developing a field-ready workshop protocol to elicit identification-compliant, time-indexed *acyclic* DAGs from practitioners.<br>• Constructing scenario-specific log-frames with node-level data inventories and calibrated cutoff thresholds that force operational pivots. |
| **RQ3: Evidence Transfer & Prospective Transportability** | **Partly answered** | • **Transport Theory:** Pearl & Bareinboim (2014, *Statistical Science*); Bareinboim & Pearl (2016); Dahabreh et al. (2020); Gechter (2024). `[REGISTRY-MATCHED]`<br>• **Empirical Heterogeneity & Site Bias:** Vivalt (2020, *JEEA*); Meager (2019, *AEJ:Applied*); Allcott (2015, *QJE*); Rosenzweig & Udry (2020, *REStud*). `[REGISTRY-MATCHED]`<br>• **Optimal Site Selection:** Montiel Olea et al. (2024, arXiv:2408.09187). `[ABSTRACT-READ]`<br>• **Pre-Registered Predictions:** Altmejd et al. (2019, *PLOS ONE*); DellaVigna & Pope (2018); DellaVigna, Pope, & Vivalt (2019, *Science*). `[REGISTRY-MATCHED]`<br>• **Cash in Crises:** Doocy & Tappis (2017); Crost, Felter, & Johnston (2016, *JDE*); Egger et al. (2022, *Econometrica*). `[REGISTRY-MATCHED]`<br>• **Synthesis Saturation:** Kastner et al. (2009); Brok et al. (2008, *IJE*); White, Saran, & Welch (2020). `[REGISTRY-MATCHED]` | • Defining a 4-tier categorical output architecture (point estimate, bounds, mechanism hypothesis, no inference) for crisis transfer.<br>• Executing the first prospective, pre-registered statistical transport prediction in a crisis, tested against a built-in evaluation.<br>• Formulating a formal two-layer saturation stopping metric (coverage stability and value stability) for Evidence Gap Maps. |

---

## 2. Key Substantive Insights and Novelty Boundaries

### Insight 1: Value of Information is Established for Global Funders, But Unapplied to Frontline Crisis Design
While the mathematical foundations of Value of Information (EVPI and EVSI) have been refined for decades in Bayesian decision theory and health economics (Claxton, 1999; Fenwick et al., 2008), its application to international development has only recently emerged. Where it has appeared—such as GiveWell’s philanthropic grant-allocation model (Brown, Salisbury, & Ball, 2025) and IDinsight’s simulation-based EVSI framework (Allier-Gagneur et al., 2022)—it has been formulated for **high-level, multi-year evaluation commissioning decisions** (e.g., whether to fund an RCT before scaling a stable national program).

In contrast, **I found no literature adapting formal VOI to the operational program design workflow of frontline humanitarian and transition managers**. Humanitarian agencies still treat evidence acquisition either as an unconditioned moral priority or as a rigid compliance checkbox, rather than an economic commodity whose value is strictly bounded by whether it can change an operational decision before a rapid decision window closes. Developing a rapid knowledge audit protocol that screens residual discretion and establishes formal stopping rules represents a significant, unaddressed contribution.

### Insight 2: The Methodological Chasm Between Participatory Systems Mappers and Causal Econometricians
Every prominent participatory causal mapping method utilized with policy practitioners—Participatory Systems Mapping (PSM; Barbrook-Johnson & Penn, 2022), Causal Loop Diagrams (CLDs), and Fuzzy Cognitive Maps (Kok, 2009)—prioritizes **feedback loops, circularity, and mutual causality**. In contrast, formal causal transportability theory (Pearl & Bareinboim, 2014; Dahabreh et al., 2020) relies fundamentally on **Directed Acyclic Graphs (DAGs)** to achieve d-separation, back-door adjustment, and identification of causal effects across heterogeneous populations.

While cyclic structural causal models exist mathematically (e.g., Bongers et al., 2021, *The Annals of Statistics*) using $\sigma$-separation, and feedback can be unrolled across time in dynamic Bayesian networks ($X_t \to Y_t \to X_{t+1}$), development and humanitarian participatory workshops overwhelmingly produce static cyclic loops. Consequently, the systems mapping community co-produces complex, looped mental models that cannot be used for formal causal identification, while econometricians formulate sparse DAGs in academic isolation without practitioner engagement. Developing a practical elicitation protocol that guides non-technical planners to express dynamic feedback as time-indexed, identification-compliant DAGs is an open, high-value methodological bridge.

### Insight 3: Pre-Registration Exists for Replication Models and Human Forecasts, But Not for Causal Transport Predictions in Crises
Pre-registration has become standard practice across social science, encompassing both human expert predictions (e.g., thousands of forecasts recorded on the Social Science Prediction Platform; DellaVigna, Pope, & Vivalt, 2019, *Science*) and statistical models predicting binary lab replication outcomes (Altmejd et al., 2019). Furthermore, econometricians frequently evaluate transportability retrospectively on historical multi-site datasets (e.g., leave-one-site-out tests on Opower or microcredit; Allcott, 2015; Meager, 2019; Gechter, 2024).

However, **I found no example in development or humanitarian aid where a researcher calibrated an ex-ante causal transport model (or partial identification bounds) using external evidence and target baseline data, pre-registered numerical predicted treatment effects and bounds for an unstudied crisis target population, and prospectively evaluated those predictions against a newly fielded field trial**.

Furthermore, a cross-cutting investigation into Evidence and Gap Maps (EGMs; White, Saran, & Welch, 2020) revealed that despite dozens of published gap maps across humanitarian and development sectors, **none have operationalized quantitative stopping rules or capture-recapture saturation metrics (such as Kastner et al., 2009; Brok et al., 2008)**. EGMs classify matrix cells as "gaps" purely based on retrieved studies, leaving researchers unable to formally distinguish whether an empty cell reflects true absence of evidence or an underpowered search.

---

## 3. Epistemic Verification Status of Key Literature Claims

To maintain rigorous transparency, the table below documents the verification level for the key empirical literature claims cited across the research agenda:

| Domain | Claim | Supporting Citation | Verification Level |
|---|---|---|---|
| **VOI Theory** | EVSI defines optimal research commissioning rules against policy adoption | Claxton (1999); Claxton & Sculpher (2006) | `[REGISTRY-MATCHED]` |
| **VOI Implementation** | Separates evidence acquisition payoff from implementation adherence payoff | Fenwick, Claxton, & Sculpher (2008) | `[REGISTRY-MATCHED]` |
| **Philanthropic VOI** | GiveWell calculates EVPI/EVSI to allocate capital between grants and research | Brown, Salisbury, & Ball (2025) | `[REGISTRY-MATCHED]` |
| **Evidence Demand** | Brazilian mayors exhibit positive willingness to pay for research via BDM trials | Hjort et al. (2021) | `[REGISTRY-MATCHED]` |
| **Cognitive Biases** | Policymakers update beliefs asymmetrically on good news and neglect sample variance | Vivalt & Coville (2023) | `[REGISTRY-MATCHED]` |
| **Humanitarian Evidence** | Only 3.4% of operational humanitarian decisions cite formal research | Campbell & Knox Clarke (2019) | `[INSTITUTIONAL-URL]` |
| **Cyclic SCMs** | Feedback loops mathematically formalized via $\sigma$-separation and solvability | Bongers et al. (2021) | `[REGISTRY-MATCHED]` |
| **Adaptive Pathways** | Adaptation tipping points and transient policy trees under deep uncertainty | Haasnoot et al. (2013) | `[REGISTRY-MATCHED]` |
| **Constraint Screening** | Growth diagnostics decision trees identify single most binding economic constraint | Hausmann, Rodrik, & Velasco (2008) | `[REGISTRY-MATCHED]` |
| **Administrative Traps** | PDIA deconstructs institutional failure via fishbone diagrams and authorization | Andrews, Pritchett, & Woolcock (2013) | `[REGISTRY-MATCHED]` |
| **Transport Theory** | Selection diagrams ($S$-nodes) provide complete graphical criteria for transport | Pearl & Bareinboim (2014); Bareinboim & Pearl (2016) | `[REGISTRY-MATCHED]` |
| **Conditional Exchange** | Trial-to-target generalization via inverse odds weighting and g-computation | Dahabreh et al. (2020) | `[REGISTRY-MATCHED]` |
| **Partial Bounds** | Relaxing rank invariance yields partial identification bounds across sites | Gechter (2024) | `[REGISTRY-MATCHED]` |
| **Site Selection Bias** | Non-random site selection produces severe external validity bias across 111 utilities | Allcott (2015) | `[REGISTRY-MATCHED]` |
| **Optimal Site Selection** | Externally valid experimental site selection equivalent to $k$-median problem | Montiel Olea et al. (2024) | `[ABSTRACT-READ]` |
| **Forecasting Failures** | Experts overestimate wage subsidy persistence in Jordan; DellaVigna & Pope trial | Groh et al. (2016); DellaVigna & Pope (2018) | `[REGISTRY-MATCHED]` |
| **Cash in Conflict** | CCTs in the Philippines increased insurgent violence due to rebel sabotage incentives | Crost, Felter, & Johnston (2016) | `[REGISTRY-MATCHED]` |
| **General Equilibrium** | Unconditional cash generates 2.5 local fiscal multiplier with minimal inflation | Egger et al. (2022) | `[REGISTRY-MATCHED]` |
| **Synthesis Saturation** | Capture-mark-recapture models establish systematic review stopping boundaries | Kastner et al. (2009) | `[REGISTRY-MATCHED]` |
| **Meta-Analysis TSA** | Trial sequential analysis controls type I error in cumulative meta-analyses | Brok et al. (2008); Wetterslev et al. (2008) | `[REGISTRY-MATCHED]` |

---

## 4. Verification Tag Counts Across the Entire Agenda

Across all four documents (`RQ1`, `RQ2`, `RQ3`, and `Summary`), the 51 unique references are classified as follows:
- **`[REGISTRY-MATCHED]`**: **41 references** (80.4%) — DOIs resolved via live Crossref / DataCite REST APIs using `check_all_dois.py`. HTTP status 200, title, and primary author verified against registry metadata; article full texts were not read.
- **`[ABSTRACT-READ]`**: **1 reference** (2.0%) — Montiel Olea et al. (2024, arXiv:2408.09187); abstract page opened, title and authors verified, version history inspected, and substantive finding confirmed.
- **`[INSTITUTIONAL-URL]`**: **9 references** (17.6%) — Official publication URLs or book overview pages opened (ALNAP, Elrha, W.T. Grant Foundation, IDinsight, INTRAC, FASID, RAND, OPM, Academic Press).
- **`[FULL-TEXT-READ]`**: **0 references** (0.0%) — Full text passages were not audited.
- **`[UNVERIFIED]`**: **0 references** (0.0%) — Every reference in the bibliography resolved.

---

## 5. Strategic Recommendations for the PhD Roadmap

1. **Thesis Core (Years 1–3: RQ1 & RQ2):**
   * Focusing the core doctoral thesis on **RQ1 (Knowledge Audit)** and **RQ2 (Decision Space & Scenario Log-Frames)** provides a robust, methodologically defensible scholarly contribution with minimal delivery risk.
   * Both questions can be rigorously validated through retrospective case audits using rich, multi-year archival program records from protracted crisis settings (e.g., Somalia, South Sudan, or northeast Nigeria).
   * Researcher-practitioner outreach funnels can be documented systematically as primary empirical data on institutional friction and revealed evidence demand, without conditioning PhD completion on securing active operational partnerships.
2. **Dissertation Leap & Horizon Work (Years 4–6: RQ3 & Cross-Cutting):**
   * **RQ3 (Evidence Transfer & Prospective Transport Evaluation)** and the **EGM Saturation Metrics** represent high-ambition methodological frontiers.
   * Developing the 4-tier categorical output hierarchy (point estimates, partial identification bounds, mechanism hypotheses, principled no-inference assertions) establishes a clear theoretical framework.
   * Executing the prospective pre-registered transport evaluation—pre-registering calibrated transport bounds before fielding an operational trial or quasi-experiment—provides a distinctive, high-impact research agenda bridging econometric transportability theory, humanitarian logistics, and social protection policy.
