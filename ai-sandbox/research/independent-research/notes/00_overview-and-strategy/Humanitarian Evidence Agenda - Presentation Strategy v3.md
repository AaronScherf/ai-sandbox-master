# Research presentation narrative v3: evidence for prolonged crises and the humanitarian–development transition

*Discussion draft, 2026-11-09. This is a new strategy memo in the format of the [original narrative](Research%20Presentation%20Narrative%20-%20Humanitarian%20Transportability%20Pipeline.md), informed by the [nexus focus analysis](Humanitarian%20Development%20Nexus%20-%20Research%20Focus%20Analysis.md), [critique analysis](Humanitarian%20Evidence%20Agenda%20-%20Critique%20Analysis.md), [source verification](Humanitarian%20Evidence%20Agenda%20-%20Source%20Verification.md), and [projects tracker](../../PROJECTS.md). It proposes a presentation argument; it does not revise the Marp deck, approve a study, or assert that a decision tool has been deployed.*

## 1. Executive summary: the prolonged-crisis choice

After several seasons of drought, displacement, and interrupted livelihoods, partners may still need emergency cash while also deciding whether to connect households to a regular safety net, add productive support, strengthen payment systems, or pre-arrange support for the next shock. The relevant choice may involve a government, a humanitarian organization, a development funder, and affected communities. Their mandates and feasible options differ. Evidence from another place may help, but a treatment called “cash” can differ in amount, timing, eligibility, delivery, market setting, and outcome horizon.

**The agenda's center is the decision to adapt support during a prolonged or recurring crisis**, when there is some opportunity to compare and revise interventions, but stable-development assumptions remain fragile. The immediate response is an important boundary: access, safety, and delivery can dominate a retrospective effect estimate. The longer-run development question is another boundary: an intervention tested in a peaceful setting does not automatically apply under displacement, market disruption, or renewed conflict. The nexus is a set of overlapping decisions and institutions, rather than a single handoff date. The [OECD DAC recommendation](https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-5019) calls for context-specific collaboration and collective outcomes; its [interim review](https://www.oecd.org/en/publications/the-humanitarian-development-peace-nexus-interim-progress-review_2f620ca5-en.html) documents continuing coordination, programming, and financing challenges. Those sources motivate examining the interface; they do not prove a uniform transition pathway.

### The overarching research question

> When a crisis persists or recurs, how can researchers and practitioners decide which external evidence is relevant to a locally feasible intervention, what must be learned in the target setting, and whether using that evidence improves a medium-term choice or preparedness plan?

The proposed contribution is **decision-specific evidence adaptation**: identify the choice and its decision-maker; assemble causal, implementation, operational, and local knowledge; examine treatment and context comparability; state what can be inferred and with what uncertainty; and test whether the resulting evidence changes a decision or an outcome. A transported causal effect is one possible result, contingent on data and assumptions. A finding that borrowing is unsafe, or that the binding barrier is institutional authority, is also useful.

For this presentation, use a recurring example: *after repeated drought and displacement, should partners maintain short-term transfers, connect recipients to continuing social protection, add livelihood support, or invest in a system that can scale before the next shock?* Treat this as a **hypothetical decision frame**, not as a documented live portfolio in Somalia or Sudan. It gives the audience a common test for every component: What evidence would change this choice, and what would make the evidence inapplicable?

## 2. Situating the problem: research and practitioner reality

| Decision interface | Evidence that could help | Question that could defeat the proposed use |
|---|---|---|
| Emergency relief to sustained protection | Comparative effects, targeting and implementation evidence, market and payment data, beneficiary experience. | Is there authority and funding to continue or alter support, and can the target population actually be reached? |
| Relief to recovery or economic inclusion | Evidence on cash alone versus combined support, assets, livelihoods, services, displacement, and longer outcomes. | Are the treatment, population, institution, and outcome comparable across source and target settings? |
| Repeated shocks to preparedness | Exposure and forecast data, trigger performance, delivery lead times, welfare effects of earlier action. | Does the forecast identify the losses of concern, and can action reach people before the shock? |
| Pre-arranged insurance or risk finance | Index–loss fit, basis risk, contract and payout rules, delivery, welfare and distributional effects. | Who bears false alarms or missed losses, and what evidence threshold does a particular funder or buyer apply? |

The [World Bank adaptive social protection framework](https://www.worldbank.org/en/publication/human-capital/publication/adaptive-social-protection-building-resilience-to-shocks-key-findings) offers a concrete institutional comparator: programs, data, finance, and partnerships connect regular protection to shock response. It does not establish that any one transfer or governance arrangement works everywhere. [Elrha's evidence-use review](https://www.elrha.org/resource/from-knowing-to-doing-evidence-use-in-the-humanitarian-sector) identifies time, funding, and relevance barriers, and highlights partnership, brokering, translation, and Global South leadership. Its literature review and consultations justify studying evidence use, not claiming a proven effect of a new evidence product. The [ALNAP decision study](https://alnap.cdn.ngo/media/documents/alnap-beyond-assumptions-how-humanitarians-make-operational-decisions.pdf) describes varied decision practices in a nonrepresentative sample. Neither side of the original debate has a universal rule: the value of causal synthesis depends on the choice, while local constraints do not make external evidence irrelevant in every setting.

The researcher–practitioner interface should therefore begin with **a jointly specified decision**, a named user, a feasible option set, and outcomes that affected people value. The researcher can map the evidence and mechanisms, diagnose transport assumptions, identify local data needed to update them, and make uncertainty legible. Practitioners and affected communities can challenge the choice set, outcome, implementation description, and acceptable risk. A useful study can investigate whether an evidence brief changed an option, a design feature, timing, or no decision at all. A brief's production is not itself evidence of impact.

## 3. The 2×2 mutually reinforcing architecture

Preserve the original four components as **separate research assets**. They create a path from an actual decision to an auditable claim, with feedback when the evidence fails. `reprokit` supports reproducible outputs across components; it is research infrastructure, not a deployed humanitarian decision system.

| | **1. Find and describe what is known** | **2. Test what can be used here** |
|---|---|---|
| **Evidence** | **1.1 Discovery and synthesis:** retrieve trials, quasi-experiments, gray evaluations, implementation and qualitative work for a choice; record intervention version, outcome horizon, institution, and known limits. | **2.1 Evidence coverage:** classify intervention, shock, population, delivery, institution, study design, geography, and horizon; distinguish an empty literature from missing indexing or inaccessible evidence. |
| **Local and replicable analysis** | **1.2 Context data:** assemble climate, conflict, displacement, market, delivery, and other relevant observations at defensible spatial and temporal scales; document selection, lag, missingness, and permissions. | **2.2 Reproducible evaluations:** replicate eligible studies and inspect treatment fidelity, attrition, spillovers, geolocation, outcome comparability, and target overlap before any transport exercise. |

The practical cycle is **decision → search → context and implementation audit → eligible comparison → conditional inference → feedback from use and outcomes**. It can end with a descriptive synthesis, a range, a locally testable mechanism, a credible target estimate, or an explicit inability to infer. The original idea of a single live simulation should remain an illustration of a future product, conditional on linked intervention and outcome data, validation, and demonstrated user value.

The [tracker](../../PROJECTS.md) distinguishes present assets from proposed integrations. The Somalia and Sudan compound-shocks panel was built and reproducibly run as of its recorded status, but is a context panel rather than an intervention–outcome study. `reprokit` v0.4.0 is released. The evidence map is in brainstorming; transferability is planned without a dedicated repository; the data-fusion library is deferred; and the Bangladesh insurance replication has a village-coordinate linkage gate. The JMMI test proposed in the [handoff](JMMI%20API%20-%20Somalia%20and%20Sudan%20Panel%20Test%20Handoff.md) now has a [read-only feasibility review](../../projects/compound-shocks-panel/docs/feasibility/jmmi-api-2026-11-09.md); it did not integrate JMMI into either panel.

### JMMI after the feasibility review: a qualified data decision

**Do not add JMMI to the compound-shocks panel's production analysis now.** The [2026-11-09 project review](../../projects/compound-shocks-panel/docs/feasibility/jmmi-api-2026-11-09.md) establishes potential value as *additional market context*, not as a replacement for WFP prices or a source of household outcomes. In Somalia, 22/22 sampled JMMI Admin-2 codes matched the panel's COD-AB geography, with special handling required for Banadir. Yet the sampled May 2024 API round contains non-food-item vendor prices while the panel uses WFP food prices; the two API formats also disagree on currency labels. The API catalog's Somalia coverage ends in May 2024, leaving the final 17 months of the panel window uncovered. Vendor restocking and shop availability might add a distinct construct, subject to missingness and definition checks. A **research-only Somalia restocking pilot** is justified; food-price substitution or production ingestion is not.

For Sudan, tested `SDN` Open API requests returned errors and the live catalog omitted Sudan even though the dashboard lists it. Three public analysis workbooks for October and November 2024 and May 2025 loaded; all 32, 28, and 45 sampled locality codes, respectively, matched the panel's COD-AB codes. Some workbooks include district market-functionality and restocking summaries, which could add context beyond WFP prices. Same-month WFP price overlap was only 6, 4, and 10 localities in those rounds; the three files do not establish continuous coverage. Physical price quantities, round-specific field definitions, and rights to redistribute derived workbook values remain unresolved. A **research-only Sudan workbook feasibility pilot** is warranted, while the tested API route and production ingestion are not.

The immediate next gate is a country-round coverage and variable-definition audit, followed by provider clarification on the Sudan API discrepancy, currency and price units, the API–website row differences, and reuse terms. The project has [draft questions for REACH](../../projects/compound-shocks-panel/docs/feasibility/reach-jmmi-clarification-questions-2026-11-09.md), not yet sent. A future provider addition would need the panel's harmonization record and a separately approved analysis change. These constraints make JMMI a useful case of the agenda's evidence-adaptation problem: an accessible source can be geographically joinable yet still be too sparse, differently defined, or legally unclear for the proposed inference.

### Conditional methods and decision outputs

1. **Define the target claim.** State the decision-maker, target population, intervention and comparator, implementation arrangement, outcome, horizon, and unit of analysis. In a prolonged crisis, “continue cash” and “add productive support” are different treatment versions; a new shock can change both.
2. **Check whether borrowing is defensible.** Ask whether source and target share relevant mechanisms and covariate support; whether markets, payment rails, security, selection, displacement, and spillovers change treatment or outcome; and whether local observations can probe those assumptions. Heterogeneity across evaluations and implementing organizations, documented by [Vivalt](https://academic.oup.com/jeea/article-abstract/18/6/3045/5908781), motivates the check without validating a particular transport estimator.
3. **Match the output to identification.** Use scenario comparisons or mechanism hypotheses when only partial information exists. Estimate a target effect only with a defensible design, comparable outcomes, and stated sensitivity. Report an implementation or access veto separately from the predicted effect *if delivered*. Do not make a numeric recommendation when the target claim is unidentified.
4. **Measure the value of the evidence process.** Record whether the synthesized evidence was available before a decision, understood, contested, and used; compare choices or outcomes where a credible study design permits. Study why a brief was ignored as carefully as why one was adopted.

## 4. The 15-slide presentation blueprint

The slide sequence keeps the original architecture and methods arc while moving the decision setting from the first emergency hours to the repeated-crisis transition. Each slide should have one assertion or question; the visuals below are concepts for a future deck, not claims that an exhibit already exists.

### Slide 1: Title and narrative hook

**Takeaway:** The central problem is adapting evidence when relief and development decisions overlap. **Content:** Pose the hypothetical repeated-drought choice between continuing transfers, linking to a safety net, adding livelihood support, and preparing for the next shock. **Visual:** A household and program timeline with recurring shocks and decision points.

### Slide 2: The decision space, not a clean handoff

**Takeaway:** A new shock can revive urgent relief while a multi-year transition remains underway. **Content:** Name the partners, mandates, available options, and uncertain outcomes in the example. Ask which decisions actually permit adaptation. **Visual:** Three overlapping bands—urgent protection, sustained support, preparedness—with named decision gates.

### Slide 3: What existing evidence and practice can answer

**Takeaway:** The gap is decision-specific adaptation and use, not a complete absence of platforms or studies. **Content:** Contrast impact evaluations, implementation and qualitative evidence, context monitoring, and existing synthesis and forecast products. Use the [source audit](Humanitarian%20Evidence%20Agenda%20-%20Source%20Verification.md) to avoid mischaracterizing ALNAP, REACH, DTM, or anticipatory studies. **Visual:** A question-to-evidence matrix with explicit blanks.

### Slide 4: Reproducibility as a foundation

**Takeaway:** A reproducible panel or replication makes a claim inspectable but does not make it transferable. **Content:** Explain `reprokit` and the difference between reproducibility, identification, transport, and decision use. **Visual:** Four checkpoints, each with a separate failure condition.

### Slide 5: The 2×2 evidence architecture

**Takeaway:** Four standalone assets support a conditional inference cycle. **Content:** Introduce components 1.1, 1.2, 2.1, and 2.2 and show how a concrete choice sends the researcher back to search or data collection. **Visual:** The 2×2 above, with feedback arrows rather than a funnel ending in a simulator.

### Slide 6: Component 1.1—find evidence for this choice

**Takeaway:** Study relevance depends on treatment, setting, implementation, and outcome, not only keywords. **Content:** Example search for continued cash versus cash plus livelihood support in recurrent shocks; include causal and implementation studies and assess retrieval and appraisal quality. **Visual:** A small evidence-card template with “what was delivered,” “to whom,” and “under which constraints.”

### Slide 7: Component 1.2—describe the target context

**Takeaway:** Context data reveal possible effect modifiers and feasibility gates, not household welfare impacts by themselves. **Content:** Show how the Somalia/Sudan panel describes changing shock exposure. Use the [JMMI review](../../projects/compound-shocks-panel/docs/feasibility/jmmi-api-2026-11-09.md) as a concrete source audit: Somalia API codes join but its sampled NFI prices and currency labels cannot replace WFP food prices; Sudan workbooks join by locality but the tested API route fails and coverage and reuse remain open. **Visual:** Source-to-variable table with geography, period, construct, missingness, and permitted use.

### Slide 8: Component 2.1—map the evidence boundary

**Takeaway:** An evidence map should reveal where source studies resemble the target choice and where they do not. **Content:** Add shock type, crisis phase, delivery institution, displacement, and outcome horizon to the intervention × outcome taxonomy; identify indexing gaps separately. **Visual:** Matrix whose empty cells are marked “no study found,” “not searched,” or “data inaccessible.”

### Slide 9: Component 2.2—replicate before transporting

**Takeaway:** A reproduced source estimate is a starting point, not a target-setting answer. **Content:** Explain the trial eligibility and geolocation gate, using the Bangladesh insurance project as an example of an unresolved linkage. Include intervention fidelity and outcome measurement checks. **Visual:** Source-study audit with pass, fail, and unknown fields.

### Slide 10: What could travel between settings?

**Takeaway:** Mechanisms, treatment versions, institutions, and populations can change independently. **Content:** Compare the same nominal support under NGO delivery, a public safety net, and an interrupted payment system. Ask which differences are measured, testable, or fatal to a proposed comparison. **Visual:** Source-to-target bridge with separate links for treatment, market, institution, and population.

### Slide 11: Causal transportability, conditionally

**Takeaway:** Target-site effect estimation requires a defined estimand, overlap, and credible assumptions. **Content:** Present the steps and sensitivity checks, and a “cannot identify” branch. Explain why a DAG or hierarchical model can clarify assumptions but cannot repair missing outcomes or impossible delivery. **Visual:** A decision tree ending in estimate, bounds, mechanism hypothesis, or no inference.

### Slide 12: Repeated shocks and structural breaks

**Takeaway:** A shock can invalidate an earlier borrowing decision. **Content:** Use conflict, displacement, market closure, or institutional change as candidate breaks; ask what monitoring would trigger a new audit. The panel can characterize exposure, but a treatment and outcome study would be additional work. **Visual:** Before/after timeline showing which assumptions changed.

### Slide 13: Resilience, anticipatory action, and risk finance

**Takeaway:** Preparing for the next shock requires separate evidence about prediction, timing, implementation, and welfare. **Content:** Use documented [Bangladesh anticipatory-cash research](https://www.csae.ox.ac.uk/anticipatory-cash-transfers-in-climate-disaster-response) and the [WFP Nepal evaluation](https://www.wfp.org/publications/nepal-anticipatory-action-impact-evaluation) as examples of evaluable timing; do not assume effects transfer to conflict settings. For insurance, separate index–loss fit, basis risk, payout delivery, and welfare effects. Funder evidence thresholds remain a research question. **Visual:** Forecast → trigger → financing → delivery → welfare chain, with failure points.

### Slide 14: A decision-specific evidence brief

**Takeaway:** The researcher offers a conditional comparison that practitioners can contest and update. **Content:** Revisit the Slide 1 choice. Display feasible options, relevant source evidence, local tests, implementation constraints, outcome horizons, uncertainty, and a rule for revisiting the choice after a new shock. State whose judgment and data shape the brief. **Visual:** One-page prototype with a prominent “what would change this conclusion?” field.

### Slide 15: Research questions and a credible next step

**Takeaway:** The agenda can be tested with one named transition decision before broadening. **Content:** Propose a jointly selected case, a decision-specific evidence and data audit, then a test of whether the resulting comparison changed design or exposed a decisive information gap. Keep subsequent transport or anticipatory evaluation contingent on data, partnerships, and owner decisions. **Visual:** A three-gate roadmap: decision access → comparability → evaluable use.

## 5. Operational effectiveness and logistical efficiency: a boundary and an interface

The [earlier strategy](Humanitarian%20Evidence%20Agenda%20-%20Updated%20Presentation%20Strategy.md) raises delivery delays, procurement, stockouts, access, and cost. These may be central in the immediate response, but a full optimization study of corridors or distribution is a separate research agenda requiring local operational data and partners. In this presentation, operational evidence serves three narrower functions: **(1) feasibility**—can the intervention be delivered safely; **(2) treatment definition and fidelity**—what was actually delivered, by whom and when; and **(3) effect modification**—could markets, payment access, or displacement change the effect of support? If a binding constraint rules an option out, that fact belongs in the evidence brief before any impact ranking. Conversely, a feasible option is not shown to improve welfare merely because it can be delivered.

A useful **potential follow-up**, adjacent to this agenda's acute-response boundary, is Elrha's [Artificial Intelligence Needs Assessment Assistant (AINAA)](https://www.elrha.org/projects/artificial-intelligence-needs-assessment-assistant-ainaa). Its project page describes rapid analysis of needs-assessment data with expert review for frontline response. That is a different decision and evidence task from adapting intervention effects during a prolonged crisis. The page lists intended outputs but no published delivery updates, so it is a comparator to investigate rather than evidence of a validated deployed tool. A follow-up could ask how assessment outputs enter later transition choices, what quality checks are needed, and whether rapid analysis actually changes decisions.

This is a candidate interface with practitioners, not an assumption that all operational datasets are ready to join. The [data-source register](Potential%20Data%20Sources%20-%20Research-Wide%20Register.md), [source audit](Humanitarian%20Evidence%20Agenda%20-%20Source%20Verification.md), and completed [JMMI feasibility review](../../projects/compound-shocks-panel/docs/feasibility/jmmi-api-2026-11-09.md) record leads and caveats. The JMMI check established some usable geographic joins and new candidate market constructs; it did not establish the coverage, definitions, and rights needed for production panel use, nor a causal effect of cash.

## 6. Open questions and research program boundaries

- **Where is the choice?** Which transition decisions have genuine discretion, a usable timeline, and decision-makers willing to revisit a plan? Which are constrained by mandate, funding, security, or public authority?
- **What should travel?** Is the portable object a treatment effect, a mechanism, a treatment design principle, a delivery lesson, or a forecast rule? Which source–target differences can be measured and which leave the claim unidentified?
- **Whose outcome counts?** Do near-term consumption gains translate into retained assets, schooling, safety, reduced later need, or durable recovery? How should returnees, hosts, and people who move during follow-up be represented?
- **How is resilience evaluated?** Does earlier or continuing support protect prior gains across repeated shocks? What is the appropriate comparison when exposure changes, action is anticipatory, and a trigger sometimes fires incorrectly?
- **What evidence does insurance require?** For a particular contract and funder, what predictive calibration, loss correspondence, payout performance, and welfare evidence are required? How does that compare with grants or contingency finance, and who bears basis risk?
- **Does the interface add value?** Does a co-produced evidence brief change a program feature, timing, funding, or outcome compared with existing planning? If not, was evidence irrelevant, untrusted, late, or blocked by authority? These are empirical alternatives, not a presumed answer.

The smallest coherent next empirical step is to **select one real, revisable transition decision** with a partner, then document its feasible options, evidence requests, and measurable outcomes. The current portfolio can support evidence discovery, context description, and replication, but it does not yet establish an integrated decision study. This strategy preserves that distinction while making prolonged-crisis adaptation and preparedness the presentation's central contribution.
