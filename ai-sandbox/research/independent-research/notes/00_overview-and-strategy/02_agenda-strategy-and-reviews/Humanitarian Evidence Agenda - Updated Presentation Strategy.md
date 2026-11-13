# Research presentation narrative: humanitarian evidence across decision horizons

*Discussion draft in the format of the [original presentation strategy](Research%20Presentation%20Narrative%20-%20Humanitarian%20Transportability%20Pipeline.md), 2026-11-09. Read with the [critique analysis](Humanitarian%20Evidence%20Agenda%20-%20Critique%20Analysis.md) and [primary-source verification](Humanitarian%20Evidence%20Agenda%20-%20Source%20Verification.md). This revises the narrative for discussion; it does not change project approvals or claim that a live decision-support system exists.*

## 1. Executive summary: the humanitarian planner's dilemma

Humanitarian planners must act with incomplete information, but the question they need answered changes with the decision horizon. In the immediate response, the binding question may be whether a population can be reached safely and on time, through which corridor, market, partner, or payment channel. In a prolonged crisis, planners can compare delivery modes, learn from monitoring, negotiate changes to grants, and examine effects on welfare and markets. Before a forecastable shock, resilience and anticipatory action require decisions about preparedness investments, trigger rules, and financing, often before local outcome data exist.

The agenda asks which forms of evidence are useful **at each decision**, when they can be assembled, and how to know whether they improve decisions. Academic causal evidence remains an important input where the intervention, population, implementation, and time horizon are sufficiently comparable. It may provide mechanism hypotheses, plausible ranges, and a basis for testing generalizability. Operational evidence—needs, access, markets, procurement, delivery, protection, costs, and institutional constraints—may be more decisive in the first response window. Neither category alone determines a feasible portfolio.

### The overarching research question

> How can a reproducible research program connect global causal and implementation evidence with local context and operational data, while identifying which claims can support immediate action, adaptation in prolonged crises, and advance planning for shocks—and when the evidence is too weak to justify a quantitative recommendation?

The presentation retains the original 2×2 architecture and trial-transportability thread. The key change is to make transportability **one conditional research branch** of a broader evidence-for-decisions program. It studies whether operational constraints truly dominate immediate choices, whether causal synthesis becomes more valuable later or upstream in standard-setting, and whether the two can be combined without false precision.

## 2. Situating the problem: literature and practitioner reality

| Dimension | Research opportunity | Practical constraint or falsification test |
|---|---|---|
| Evidence discovery | Organize academic, gray, and operational knowledge by the decisions each source could inform. | Faster retrieval matters only if a decision-maker has time, authority, and a usable choice to change. |
| Choice among interventions | Study the feasible set: cash, in-kind aid, vouchers, services, pre-positioning, or insurance where relevant. | Mandates, earmarks, safety, minimum standards, supply, and implementation capacity may rule out apparent options. |
| Data availability | Fuse climate, conflict, market, needs, displacement, activity, procurement, and logistics records where compatible. | Public availability is distinct from timeliness, representative measurement, legal access, and joinability. |
| Impact and external validity | Replicate studies and examine how effects vary with context and delivery. | A transported treatment effect is conditional on overlap, comparable treatment, implementation, and limited interference. Some targets are not identified. |
| Operational value | Test whether evidence changes access, timing, modality, coverage, cost, safety, and welfare. | A polished dashboard or study is not evidence of adoption or better outcomes. |

The humanitarian–development nexus organizes these questions by **transition**, not by a single “humanitarian” label. An acute response may prioritize rapid feasibility and minimum standards. A prolonged crisis permits iterative monitoring, implementation research, and sometimes credible causal evaluation. Development and resilience work can invest in baseline systems, forecast calibration, social protection, and preparedness before the next shock. The transitions can reverse when conflict intensifies or a new disaster hits.

This framing also makes the original disagreement a research object. The critique argues that political and logistical constraints dominate; the original memo emphasizes inaccessible causal evidence. Both may be true in different institutions, sectors, and phases. ALNAP's [field study](https://alnap.cdn.ngo/media/documents/alnap-beyond-assumptions-how-humanitarians-make-operational-decisions.pdf) observed multiple decision styles, while its [evidence review](https://calpnetwork.org/wp-content/uploads/2020/01/alnap-insufficient-evidence.pdf) supports good evidence use; neither warrants a universal anti-RCT claim. The program should map actual planning gates and document when evidence was requested, what was available, what choice was open, and whether it changed the choice.

## 3. The 2×2 mutually reinforcing architecture

The four components remain standalone, reproducible outputs, with `reprokit` as a research reproducibility framework (see the [tracker's project entry](../../../PROJECTS.md); its separate repository is present only in the main checkout). They support several possible analyses rather than feeding inevitably into a single simulator.

| Component | Retained contribution | Expanded question and validation gate |
|---|---|---|
| **1.1 Literature discovery and synthesis** | Search and appraise causal evaluations and policy research. | Include implementation, logistics, anticipatory action, and gray literature; audit retrieval completeness and claim accuracy. |
| **1.2 Context data fusion** | Harmonize climate, conflict, market, and other subnational variables. | Explore operational datasets with explicit collection, latency, missingness, spatial-unit, licensing, and representativeness checks. |
| **2.1 Evidence taxonomy and gaps** | Map intervention, outcome, and geography. | Add decision phase, study design, implementation conditions, data quality, access, and outcome horizon. Distinguish a true evidence gap from an indexing gap. |
| **2.2 Reproducible evaluations** | Curate and replicate eligible trials and quasi-experiments, including their geolocation constraints. | Audit intervention fidelity, scale, interference, attrition, target overlap, and the availability of comparable outcomes. |

The feedback loop is an **auditable research cycle**: a decision question guides search; search identifies relevant datasets and missing evidence; data audits constrain the estimand; replication and implementation evidence inform hypotheses; observed failures revise the taxonomy. The output may be a synthesis, a panel, a replication, a feasibility assessment, an uncertainty range, or an explicit “cannot infer.” Corpus completeness and operational deployment are not presumed.

The [tracker](../../../PROJECTS.md) provides the current anchors: the compound-shocks panel has reproduced Somalia and Sudan builds; `reprokit` v0.4.0 is released; the Bangladesh insurance replication has an unresolved village-coordinate gate; the evidence map is in brainstorming; the data-fusion toolkit is deferred; and transferability remains a planned evidence line. These are different maturity states. The revised story should not present the 2×2 as an integrated working product.

### Conditional methods and decision outputs

1. **Immediate response:** describe needs and constraints, compare feasible routes/modalities, and expose missing or stale information. Outcomes include time to delivery, coverage, cost, and safety. Scenario ranges or feasibility bounds may be useful if measurement supports them.
2. **Protracted response:** compare implementation strategies and adapt delivery using monitoring, process evidence, and, where feasible, causal designs. Examine welfare, displacement, market effects, and the ability to change grants or contracts.
3. **Resilience and anticipatory action:** evaluate forecasts, trigger errors, lead times, pre-positioning, and the effects of acting before a shock. Here transportability and prospective evaluation may be especially relevant, subject to validation.
4. **Insurance and risk finance:** separate the validity of the hazard index, prediction of loss, payout rules, payment delivery, and welfare effects. Compare these with grants and other preparedness tools. Determine evidence thresholds with funders and beneficiaries empirically.

Formal transport estimators, hierarchical models, synthetic comparisons, and machine learning remain possible methods. Each needs a defined estimand, observable prerequisites, calibration checks, and a baseline comparison. A DAG can state assumptions and failure pathways; it cannot make a broken delivery link observable. No method automatically converts noisy crisis feeds into valid target-site treatment effects.

## 4. The 15-slide presentation blueprint

### Slide 1: Title and narrative hook

**Title:** The humanitarian planner's dilemma: evidence across response, recovery, and resilience. **Takeaway:** The evidence question changes as time, authority, and data change. **Visual:** Three aligned decision clocks—hours/days, months/years, and before the next shock—rather than one universal response deadline.

### Slide 2: The problem in practice: search, feasibility, and choice

**Takeaway:** Search costs matter, but the first decision may be constrained by access, supply, funding, and safety. **Content:** Contrast a flash-response logistics decision, an in-flight modality change, and an advance trigger decision. Ask what choices were actually open. **Visual:** A shrinking feasible-choice set with evidence needs attached to each gate.

### Slide 3: State of the art and the evidence-use question

**Takeaway:** Academic evaluations, evidence maps, operational platforms, and practitioner judgment answer different questions. **Content:** Treat the claim of an “unmet integrated tool” as a testable proposition; compare [REACH's JMMI API](https://marketsincrises.net/wp-content/uploads/2025/08/REACH-Joint-Market-Monitoring-Initiative-JMMI-Guidance-Document-V1-2025.pdf), [DEEP](https://docs.thedeep.io/), and [DRC Foresight](https://drc.ngo/en/pages/foresight-displacement-forecasts/) on timeliness, decision fit, quality, and user uptake. Their existence narrows, but does not settle, the proposed research gap. **Visual:** Evidence type × decision horizon matrix, with known and unknown cells.

### Slide 4: Foundational architecture: `reprokit`

**Takeaway:** Reproducibility makes evidence auditable and portable as research, but field usefulness requires separate validation. **Content:** Show study, evidence, and library archetypes and the actual status of each. **Visual:** Source → provenance → artifact → independent validation → possible use.

### Slide 5: The 2×2 evidence engine

**Takeaway:** The original four components remain, with operational and implementation questions alongside effects. **Content:** Literature search, context fusion, taxonomy, and evaluation repository; decision phase is a cross-cutting tag. **Visual:** Original 2×2 with outputs branching to synthesis, feasibility, and conditional causal analysis.

### Slide 6: Component 1.1, discovery and synthesis

**Takeaway:** Search academic and gray sources for effects, delivery conditions, and failure modes. **Content:** Include a claim-verification and source-access step; ask whether retrieved evidence reaches a real planning gate. **Visual:** Search → screen → appraise → decision-relevant synthesis, with a measured search-cost baseline.

### Slide 7: Component 1.2, subnational and operational data

**Takeaway:** The Somalia/Sudan panel is a research foundation; logistics and implementation need a separate data audit. **Content:** Candidate sources include market monitoring, needs assessments, 3W/4W, displacement, procurement, and logistics records. REACH has a public JMMI API, while IOM's public [DTM API](https://dtm.iom.int/data-and-analysis/dtm-api) serves non-sensitive aggregates. Check spatial unit, update lag, selection, and access before joining. **Visual:** Dataset cards displaying those limitations, not a seamless “live feed.”

### Slide 8: Component 2.1, evidence coverage

**Takeaway:** An evidence map must distinguish effect evidence from feasibility and implementation evidence. **Content:** Add phase, setting, delivery, and data-quality tags; map blank cells cautiously. **Visual:** Intervention × outcome matrix filtered by response phase and evidence type.

### Slide 9: Component 2.2, trials and the geolocation gate

**Takeaway:** Replication is valuable even when location linkage is unavailable; effect transfer needs further gates. **Content:** Bangladesh insurance coordinate limitation; treatment consistency, uptake, spillovers, and outcome comparability. **Visual:** Eligibility flow that separates replication, spatial linkage, and transportability.

### Slide 10: Evidence cycle and heterogeneity

**Takeaway:** Feedback generates questions and tests; an outlier is a lead, not proof of a flawed study. **Content:** Compare context, implementation, estimands, measurement, and selection. **Visual:** Several plausible explanations branching from a discrepant effect estimate.

### Slide 11: Causal transportability under covariate shift

**Takeaway:** Estimate target effects only under explicit overlap and transport assumptions. **Content:** Show when a defensible range is possible, when sensitivity analysis is needed, and when no effect is identified. **Visual:** A decision tree with “estimate,” “bound,” and “insufficient support.”

### Slide 12: Structural breaks in crisis settings

**Takeaway:** Security, market, payment, or delivery failures can sever a proposed mechanism. **Content:** Use causal diagrams to list dependencies and operational records to test them; identify stale observations. **Visual:** Cash-to-welfare chain with annotated failure points and source timestamps.

### Slide 13: Methods matched to questions

**Takeaway:** Method choice follows the estimand and data, not a universal toolkit. **Content:** Descriptive monitoring, process tracing, forecasting, delivery-time analysis, causal evaluation, and transport methods each have different tests. **Visual:** Question → data → assumptions → validation → admissible output.

### Slide 14: Decision support as a scenario exercise

**Takeaway:** Compare feasible choices with transparent constraints and uncertainty. **Content:** A tabletop example considers cash, in-kind, and pre-positioned stocks; insurance belongs primarily to a prior financing decision unless coverage and triggers already exist. Present results as conditional scenarios, not a live optimized prescription. **Visual:** A one-page decision brief showing alternatives, binding constraints, evidence age, and unknowns.

### Slide 15: Frontiers and roadmap

**Takeaway:** The agenda tests evidence use as well as methods. **Content:** Near-term: use the companion source audit to verify literature claims and audit one operational dataset alongside the existing panel and trial work. Later possibilities: test a specific transport estimand, evaluate prolonged-crisis adaptation, and compare anticipatory triggers or insurance payouts. Documented [Bangladesh](https://www.csae.ox.ac.uk/anticipatory-cash-transfers-in-climate-disaster-response) and [Nepal](https://www.wfp.org/publications/nepal-anticipatory-action-impact-evaluation) evaluations make the anticipatory-action question concrete; they do not establish the transcript's named “GoDARTS” platform. All further work remains subject to data and owner decisions. **Visual:** Three research questions by horizon, each with a falsification test.

## 5. Additional section: operational effectiveness and logistical efficiency

This section can become speaker notes, a discussion slide, or a follow-on study without changing the deck's 15-slide count. The core distinction is between **whether an intervention would work if delivered** and **whether the response can deliver it safely, promptly, and at scale**. Both matter, and the second can determine whether the first estimate has any immediate relevance.

Potential questions: What predicts time to first delivery and stockouts? When do planned targets diverge from verified outputs? How do corridor disruptions, procurement lead times, vendor restocking, payment rails, and donor reprogramming rules constrain feasible modalities? Do local procurement or cash approaches change local prices and available supply? Are cost-per-person and cost-per-timely-delivery rankings the same? What protection or distributional harms are hidden by throughput metrics?

Candidate sources named in the transcript—3W/4W, IATI, logistics reports, market monitoring, needs assessments, procurement, and grant documents—need a small record-level access and linkage audit before a design or aggregate claim. The transcript's proposed friction bounds, procurement analysis, and grant adaptation studies are hypotheses, not ready-made identified estimators. A useful first output might simply be a reproducible comparison of what each source measures, where it is missing, and which decision it could credibly inform.

## 6. Open questions for the discussion

- **Nexus timing:** When does a crisis become stable enough for outcome evaluation, and when does renewed violence invalidate what was learned? Which evidence transfers between humanitarian agencies and development institutions?
- **Resilience:** Which investments and trigger rules can be planned before a shock? How should plans respond to shocks outside historical experience and to changing exposure?
- **Insurance:** What level of forecast calibration, loss prediction, payout reliability, and demonstrated welfare benefit do different funders require? How much basis risk is acceptable, and who bears it?
- **Decision value:** Does a more accurate effect estimate change a choice more than a faster access or delivery update? This should be tested in actual decision settings.
- **Institutional claims:** Where do mandates and earmarks bind, and where can practitioners adapt? What evidence does each gate accept?

This revised narrative preserves the original intellectual structure and empirical assets while making its most ambitious causal and operational claims subject to evidence. The [long-form analysis](Humanitarian%20Evidence%20Agenda%20-%20Critique%20Analysis.md) records the competing interpretations and their unresolved tests.
