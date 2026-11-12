# Novelty Check: Summary of Literature Findings across the PhD Agenda

**Document:** `Novelty Check - Summary - v1.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-10 / 2026-11-11  
**Scope:** Synthesis and comparative novelty assessment across Research Questions 1, 2, and 3, including cross-cutting evidence saturation.

---

## 1. Research Agenda Verdict Table

| Research Question | Verdict | Strongest Prior Work | What Remains Open (Aaron's Contribution) |
|---|---|---|---|
| **RQ1: Knowledge Audit & Value of Information** | **Partly answered** | • **Health Economics VOI:** Claxton (1999), Claxton & Sculpher (2006), Fenwick et al. (2008) on EVPI/EVSI for research commissioning.<br>• **Philanthropic VOI:** Brown, Salisbury, & Ball (2025, *AEA P&P*) on GiveWell's grant-allocation VOI model.<br>• **Policymaker Demand:** Hjort et al. (2021, *AER*) on WTP for research; Vivalt & Coville (2023, *JDE*) on belief updating.<br>• **Evidence Barriers:** ALNAP (Campbell & Knox Clarke, 2019); Elrha (Smith et al., 2022). | • Translating formal EVSI into a qualitative, rapid intake protocol that screens whether external evidence can marginally shift a crisis choice.<br>• Defining the "value of no additional research" as an explicit deliverable when constraints bind.<br>• Documenting the researcher-practitioner outreach funnel as an empirical observable of revealed demand. |
| **RQ2: Decision Space, Constraints & Scenario Log-Frames** | **Partly answered** | • **Adaptive Safety Nets:** OPM SRSP synthesis (O’Brien et al., 2018); World Bank ASP (Bowen et al., 2020).<br>• **Participatory Systems Mapping:** Barbrook-Johnson & Penn (2021); Sterman (2000); Kosko (1986).<br>• **Constraint Diagnostics:** Growth Diagnostics (Hausmann et al., 2008); PDIA (Andrews et al., 2013).<br>• **Deep Uncertainty:** Robust Decision Making (Lempert et al., 2003); Dynamic Adaptive Policy Pathways (Haasnoot et al., 2013). | • Synthesizing a "constraint-first" diagnostic screen that eliminates infeasible options before evidence retrieval.<br>• Developing a workshop protocol to elicit identification-compliant *acyclic* DAGs from practitioners.<br>• Constructing scenario-specific log-frames with node-level data inventories and calibrated cutoff thresholds that force operational pivots. |
| **RQ3: Evidence Transfer & Prospective Transportability** | **Partly answered** | • **Transport Theory:** Pearl & Bareinboim (2011, 2014); Bareinboim & Pearl (2016); Dahabreh et al. (2020, 2021).<br>• **Empirical Heterogeneity & Site Bias:** Vivalt (2020, *JEEA*); Meager (2019, *AEJ:Applied*); Allcott (2015, *QJE*); Rosenzweig & Udry (2020, *REStud*); Montiel Olea et al. (2023).<br>• **Expert Forecasts:** DellaVigna & Pope (2018); DellaVigna et al. (2020, SSPP).<br>• **Cash Reviews:** Doocy & Tappis (2017); Crost et al. (2016). | • Defining a 4-tier categorical output architecture (point estimate, bounds, mechanism hypothesis, no inference) for crisis transfer.<br>• Executing the first prospective, pre-registered statistical transport prediction in a crisis, tested against a built-in evaluation.<br>• Formulating a formal two-layer saturation stopping metric (coverage stability and value stability) for Evidence Gap Maps. |

---

## 2. The Three Most Important Surprises

### Surprise 1: The Total Absence of Decision-Theoretic VOI in Operational Aid Programming
Despite three decades of sophisticated mathematical development in health economics (where Expected Value of Sample Information is routinely used by NICE and health technology agencies to decide whether to commission a clinical trial) and despite the emergence of value-of-information models in humanitarian forecast triggers (e.g., KNMI/Red Cross cost-loss thresholds for early action) and global philanthropy (GiveWell’s 2025 AEA paper), **formal VOI has never been adapted to operational humanitarian or transition program design**. 

Aid agencies and donors still treat evidence acquisition as an unconditioned moral good or a rigid compliance checkbox rather than an economic commodity whose value is strictly bounded by whether it can change an operational decision before the window closes. Operationalizing a lightweight VOI intake screen that explicitly values the *"no further evidence is needed because constraints bind"* outcome is entirely unaddressed in the literature.

### Surprise 2: The Unacknowledged "Cyclic vs. Acyclic" Barrier in Participatory Modeling
Every major participatory causal modeling method used with policymakers—Participatory Systems Mapping (PSM), Causal Loop Diagrams (CLDs), Fuzzy Cognitive Maps (FCMs), and System Dynamics—deliberately emphasizes **feedback loops, mutual causality, and circularity**. However, modern formal causal inference (Pearl’s do-calculus, selection diagrams, and transportability theory) mathematically requires **strict acyclicity (Directed Acyclic Graphs, DAGs)** to achieve identification and d-separation. 

In the existing literature, these two communities simply do not talk to each other: systems mappers allow loops that make formal causal transport mathematically impossible, while causal econometricians draw sparse DAGs in academic isolation without engaging practitioners' mental models. There is virtually no literature or protocol addressing how to elicit identification-compliant, time-indexed DAGs from frontline decision-makers without alienating them.

### Surprise 3: Pre-Registration Exists for Human Hunches, But Not for Causal Transport Models
While pre-registration has expanded rapidly across social science—exemplified by the Social Science Prediction Platform (SSPP; DellaVigna, Pope, & Vivalt), where researchers record human expert forecasts—**no one has ever pre-registered an algorithmic or statistical causal transport prediction in a crisis setting and compared it with a subsequent trial**. 

Econometricians test transport models retrospectively on historical datasets (e.g., leave-one-site-out tests on Opower or microcredit), while trialists register prospective RCTs without formally modeling transport from prior source trials. The idea of linking the two—pre-registering a specific point estimate or Manski/Gechter bounds generated by a formal transport model, implementing an intervention with an evaluation built in, and testing the ex-ante prediction against the realized effect—is an open, highly original methodology. 

Furthermore, a cross-cutting check on Evidence Gap Maps (EGMs) revealed that despite dozens of published gap maps in the humanitarian and development sectors, **none have formal statistical stopping rules or capture-recapture saturation metrics**, leaving researchers unable to distinguish an empty literature from an underpowered search.

---

## 3. Implications for the PhD Roadmap

1. **Thesis Chapters (Years 1–3):**  
   Focusing the thesis on **RQ1 and RQ2** provides an airtight, defensible scholarly contribution. Retrospective case audits can demonstrate the Knowledge Audit and Multi-Scenario Threshold Log-Frame on rich historical program records without risking PhD completion on active partner outreach. The partner outreach funnel can be analyzed as empirical data on institutional friction.
2. **Dissertation & Follow-On (Years 4–6):**  
   **RQ3** serves as the major methodological and empirical leap. Developing the 4-tier categorical transport model, establishing saturation metrics for evidence gap maps, and executing the prospective pre-registered prediction mini-study establishes a distinctive, high-impact research agenda bridging causal inference, humanitarian logistics, and development economics.
