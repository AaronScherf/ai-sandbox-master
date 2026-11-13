# Review and brainstorm: a cohesive nexus evidence agenda (v3)

*Claude, 2026-11-10, third pass. Answers the [handoff](Handoff%20-%20Cohesive%20Nexus%20Presentation%20Agenda%20Review.md). Review only: the v3 *strategy*, deck, tracker and project plans are untouched.*

**Naming caution.** "v3" in this filename is the version of *this review*. The separate [Presentation Strategy v3](Humanitarian%20Evidence%20Agenda%20-%20Presentation%20Strategy%20v3.md) is a different document. Below, "strategy v3" means that one.

**Tags.** **[V]** verified project behavior. **[I]** plausible interpretation. **[P]** proposal from this review. **[O]** owner decision or owner-supplied idea, recorded as given.

## Version history

| Version | File | State | What it was |
|---|---|---|---|
| v1 | [v1](Review%20-%20Cohesive%20Nexus%20Evidence%20Agenda%20Recommendation%20-%20v1.md) | Reconstructed from the first pass (original overwritten before saving) | Three framings, 15-slide map, framing recommendation C, two research questions (RQ1 transfer, RQ2 use) |
| v2 | [v2](Review%20-%20Cohesive%20Nexus%20Evidence%20Agenda%20Recommendation%20-%20v2.md) | Exact copy of the file as it stood | Staged pipeline, owner's RQ3→RQ2→RQ1 labels, dimensions, compressed 12-slide sketch |
| **v3** | this file | Current | RQ relabel in run order, timeline, value-of-information framing, evaluation as terminal state, restored slide crosswalk |

**Convention [P]:** each revision round is a new file with a `- vN` suffix. Earlier versions are not edited. Each new version carries a "what changed" list.

## What changed from v2

1. **RQs relabelled in run order** (key below).
2. **Tentative timeline** against the PhD calendar (§4).
3. **Value-of-information framing** expanded with owner's notes and a selection-bias problem (§3.1).
4. **Evaluation layer is now the terminal state** of the agenda, with a falsifiability test and a caution about wide bounds (§3.4).
5. **Slide crosswalk restored** (§5), covering the original, strategy v3, v1's 15-slide map and v2's 12-slide sketch, plus the **appendix list**. It surfaced one omission in v2's sketch: the transfer card slide was dropped.
6. Claims table carried forward; one row added.

## RQ label key

| Stage (run order) | v1 label | v2 label | **v3 label (current)** |
|---|---|---|---|
| Knowledge audit / value of information | – (did not exist) | RQ3 | **RQ1** |
| Decision space (constraints, scenarios, log-frames) | RQ2 (use) in part | RQ2 | **RQ2** |
| Transfer diagnostics and computation | RQ1 | RQ1 | **RQ3** |

---

## 1. Decisions recorded

| # | Item | Status |
|---|---|---|
| 1 | Framing C (graded transfer claim, decision value tested), extended into a staged pipeline | **[O] accepted** |
| 2 | Claims table | **[O] accepted** (§7) |
| 3 | Spine use case: cash vs. safety net; anticipatory cash only as a modality-and-timing sub-question | **[O]** |
| 4 | Transfer dimensions: temporal, spatial (with environmental), institutional, market | **[O]** |
| 5 | Armenia claim | **[O] dropped** |
| 6 | Candidate case: desk-based, richly documented, geographically specific | **[O] held for next step** |
| 7 | Human subjects | **[O]** none yet; practitioner interviews later |
| 8 | Audience: PhD peers now, committee later; 30 minutes including questions | **[O]** |
| 9 | RQs relabelled in run order | **[O]** done in this version |
| 10 | Timeline: RQ1 and RQ2 validated by the thesis (end of year 3); rigorous RQ3 answer by the dissertation (year 5–6) | **[O]** tentative; see §4 |
| 11 | Evaluation layer is the terminal state of the agenda | **[O]** |
| 12 | Revision rounds are kept as versioned reports | **[O]** |

---

## 2. The pipeline, in run order

| Stage | Question | Method character | Standalone output |
|---|---|---|---|
| **RQ1: knowledge audit** | What does the decision-maker already know and have access to, and would new evidence (or a more accessible version of existing evidence) be marginally worth the time, effort and cost to collect, analyze and understand? | Qualitative; intake form or interview; decision-theory framing (§3.1) | Go/no-go on evidence work; or "make existing information usable" |
| **RQ2: decision space** | What are the constraints and discretion of this decision, and which interventions would be considered under which conditions? | Participatory DAG mapping and scenario planning (document-derived until a human-subjects phase) | Scenario-specific log-frames; per-node data inventory and decision thresholds; constraint-first screen |
| **RQ3: transfer** | Which sources are informative, how far are they from the target (spatial, temporal, institutional, market, treatment version, population, interference), and which output does the evidence support? | Transportability diagnostics, then computation with a method chosen by the data | Output tier (estimate / bounds / mechanism hypothesis / no inference) and the computed output where supported |
| **Gate: data insufficient** | Which specific gaps block inference and how could each be remedied? | Gap register | Ranked remedies (pilot, survey, custom geodata, data request, adjusted monitoring) |
| **Terminal state: evaluation** | Was the prediction right, and was the decision process useful? | Prospective evaluation designed in from the start | Pre-registered prediction and an evaluation plan; later, results |

Cross-cutting: **portfolio** (related decisions sharing data, with synergies and conflicts) and **iteration** (new evidence feeds back to RQ1). Both are documented extensions after one decision works.

The "no inference" case still yields synthesis, a context data space, log-frames and scenario plans **[O]**. The AI-assisted rapid feedback idea for the gap register traces to Elrha's AINAA *project page*, which lists intended outputs and no published delivery updates, so it is a comparator, not a validated tool **[V: strategy v3 §5]**.

### 3.1 Framing value of information

**Owner's position [O]:** the judgment is inherently qualitative; the practical form is an intake form or interview; partners would likely collaborate only if they believed they needed more evidence, so the hard case is identifying the *no additional evidence would help* situations (the decision-maker is saturated, or constraints are binding). An economics-style frame, perhaps a **willingness-to-pay** test validated against consultant pricing or donor grant sizes, is a later refinement.

**Proposal [P]:** make the judgment tractable by writing it as a small set of questions that map onto the decision-theory idea that evidence is worth only what it can change:
- *Does residual discretion exist?* (options remaining after constraints)
- *Can existing information already separate the surviving options?* (saturation)
- *Is the timeline compatible with collecting more?* (cost and delay)
- *Who bears the cost of being wrong, and is it reversible?*

**Literature to review [I]:** I believe the relevant strands are value of information in Bayesian decision analysis (expected value of perfect and sample information), bounded rationality and satisficing, decision-making under deep uncertainty (robust decision-making, info-gap) and humanitarian operations research. This is from my own knowledge, **not verified in the repo**, so treat it as a reading list to check.

**Selection problem [I]:** if only partners who want more evidence agree to participate, the data cannot show when evidence is not valuable. Possible mitigations: (a) include the "no new evidence" outcome as an explicit, useful deliverable for the partner (it saves them cost); (b) use the desk-based retrospective audit, which has no self-selection into the study, to see negative cases; (c) screen on the intake form *before* revealing what research is on offer.

### 3.2 Dimensions of transfer distance (unchanged from v2)

| Dimension | What differs | Data character | Existing asset [V] |
|---|---|---|---|
| Spatial (incl. environmental) | Agro-ecology, terrain, access, hazard exposure, settlement and displacement | Gridded or admin-level panels | Compound-shocks panel (Somalia/Sudan): context only |
| Temporal | Source vs. target period; seasonality; multi-year cycles (e.g. ENSO); climate-trend non-stationarity | Long time-series | Panel covers a limited window; adequacy for supercycles unestablished [I] |
| Institutional | NGO vs. public delivery, registries, payment rails, mandate, funding windows | Mostly coded documentary data | None; a coded institutional panel would be new [I] |
| Market | Prices, functionality, pass-through, payment reach | Price and functionality panels | WFP prices in panel; JMMI qualified and **not** in production |
| Treatment / population / interference | Version, who is present, spillovers | Programme records, trial microdata | Not held; Bangladesh replication gated on village coordinates |

### 3.3 Use case

Cash vs. safety net runs through every stage. Modality and timing, including anticipatory cash (Bangladesh and Nepal evaluations as a worked example **[V]**), appear once the decision space judges cash viable. Insurance is a note only. Economic inclusion and displacement–return are unassessed.

### 3.4 Evaluation as terminal state

**Owner's position [O]:** a full evaluation may not report in time for the dissertation. But if the pipeline produces a causal prediction, persuades a decision-maker to implement the intervention, and builds in an evaluation, then the hypothesis (the ex post effect lies within the predicted bounds) is **falsifiable even if not yet tested**.

**My additions [I]:**
- *The prediction is the research object, so pre-register and time-stamp it before implementation.* That is what makes it falsifiable.
- *"Within the predicted bounds" is a weak test if the bounds are wide.* A pre-specified informativeness criterion is needed: bounds narrower than a naive baseline's (such as the pooled source mean), and a stated sign and minimum magnitude. Otherwise the prediction can hold without meaning anything.
- *One prediction-vs-outcome comparison is one test.* It supports or disconfirms the transfer claim for that case; it does not validate the method in general. Say "falsifiable, one case" to avoid overstating.
- *Whether the decision process helped* has no counterfactual in a single case. Options (pre-registered calibration, stepped introduction across sites, cross-decision comparison) are weak individually.
- *Persuading a decision-maker to implement* is itself a result for RQ1 and RQ2, and the largest dependency: the terminal state needs a partner willing to implement, evaluate and accept possible randomization limits. Ethical and operational limits apply to evaluation designs in live crisis programmes.

---

## 4. Tentative timeline [P, for owner correction]

*Current point: about halfway through year 1. "Thesis" is read as the end-of-year-3 milestone and "dissertation" as the final document at the end of year 5 or 6. Please confirm that reading.*

| Window | Aim | Output |
|---|---|---|
| Rest of year 1 | Choose the framing; case search (desk-based); literature on value of information and decision-making under uncertainty; 30-minute peer talk | Case shortlist; reading notes; talk |
| Year 2 | Retrospective audit on one or two documented programmes, run RQ1→RQ2 on documents and RQ3 as an audit (no estimator); draft the intake form; **start human-subjects review before any partner contact** [I: lead time] | Audit report; draft instrument; first paper candidate |
| Year 3 (thesis milestone) | **RQ1 and RQ2 validated:** demonstrated on retrospective cases, and ideally piloted with a partner under approved human-subjects review | Thesis chapters on knowledge audit and decision space |
| Years 4–5/6 | **Rigorous RQ3:** compute outputs for a chosen case; design the prospective prediction and evaluation; implement with a partner if achievable; dissertation | Pre-registered prediction; evaluation plan; results if timing allows |

"Validated" for RQ1 and RQ2 needs a definition. Suggested: *the stage produced a usable output on at least one documented case, and an independent reader (or the partner) judged the output faithful.* That is a choice for the owner.

*Risk:* the partner dependency sits in years 3–5, while the case search happens now. The retrospective audit protects the thesis milestone from that risk.

---

## 5. Slide crosswalk (restored and extended)

### 5.1 Four versions side by side

| Original deck slide | Strategy v3 | v1 15-slide map | v2 12-slide sketch | Treatment |
|---|---|---|---|---|
| 1 Title and hook (planner's dilemma) | 1 Hook: repeated-drought choice | 1 (v3 kept) | 1 The decision | Rewritten |
| 2 Search costs and portfolio decisions | 2 Decision space, not a clean handoff | 2 (kept, add residual-discretion question) | 1 (merged), 3 Decision space | Reframed |
| 3 Limits of existing frameworks | 3 What existing evidence answers | 3 (kept) | 4 Existing evidence and practice | Kept |
| 4 `reprokit` | 4 Reproducibility as foundation | 4 (kept) | 6 Toolkit (compressed) | Compressed |
| 5 2×2 engine | 5 The 2×2 architecture | 5 (+ end in transfer claim) | 5 Pipeline and 6 Toolkit | Reframed as inputs |
| 6 Component 1.1 | 6 Find evidence for this choice | 6 (+ node-matched card fields) | **Appendix** | Moved |
| 7 Component 1.2 | 7 Describe the target context; JMMI audit | 7 (kept) | **Appendix** | Moved |
| 8 Component 2.1 | 8 Map the evidence boundary | 8 (+ node-matched attributes) | **Appendix** | Moved |
| 9 Component 2.2 (geolocation gate) | 9 Replicate before transporting | 9 (kept) | **Appendix** | Moved |
| 10 Evidence cycle; relative trial validity | 10 What could travel | 10 What differs (sharpened) | 7 What differs | Cycle claims removed |
| 11 Covariate shift; satisficing | 11 Causal transportability, conditionally | 11 When can an effect be reweighted | 8 Reweighting and output tiers | Kept, claim softened |
| 12 Structural breaks (DAG) | 12 Repeated shocks and structural breaks | 12 Breaks as tests of transportability (rebuilt) | 9 Structural breaks | Rebuilt |
| 13 Method toolkit | 13 Resilience, anticipatory action, risk finance | 13 Method and validation ladder | 10 Method, validation, prospective test | Restored |
| 14 Simulation response exercise | 14 Decision-specific evidence brief | 14 Does it help a decision (card, test) | **No slide; see §5.2** | Simulator removed |
| 15 Frontiers, open questions, roadmap | 15 RQs and a credible next step | 15 (same, restated) | 11 Gap register and case search; 12 Research questions | Rewritten |

### 5.2 What was in the appendix list, and a gap in v2

In v2's sketch the **appendix** held: strategy v3's component slides 6–9 (evidence cards, context data, evidence boundary, replicate-before-transport), the JMMI source audit, and the claims table. Original slides 6–9 follow the same route.

**Gap found while restoring the table [V: comparing the documents]:** v2's 12-slide sketch has *no slide for the decision-specific transfer card/brief* (strategy v3 slide 14, v1 slide 14). It also has no slide for resilience/risk finance, which was intentional given decision 3. Options **[P]**: (a) fold the card into the pipeline slide as its output; (b) fold it into the method slide as the thing that carries the prospective prediction; (c) add it as a thirteenth slide, which probably breaks the time budget. I lean toward (a), plus a one-line mention on the evaluation slide.

### 5.3 Revised 12-slide sketch (v3, provisional, for discussion)

| # | Slide | Notes |
|---|---|---|
| 1 | The decision | Cash vs. safety net; hypothetical |
| 2 | RQ1: is more evidence worth it? | Knowledge audit; value of information |
| 3 | RQ2: the decision space | Scenarios, log-frames, thresholds |
| 4 | What existing evidence and practice offer | Compact; no mischaracterized sources |
| 5 | The pipeline | Stages, gate, loop, terminal evaluation; transfer card as output (option a) |
| 6 | The toolkit behind it | The 2×2 as inputs, honest maturity; `reprokit` |
| 7 | RQ3: what differs between source and target | Dimensions, nodes |
| 8 | Reweighting and output tiers | The decision tree |
| 9 | Structural breaks as tests of transportability | DAG; S-nodes; temporal/spatial/institutional/market |
| 10 | Method and validation | Ladder; prospective prediction |
| 11 | Terminal state and gap register | Falsifiable prediction; remedies; case search |
| 12 | Research questions, timeline, open issues | Includes the thesis/dissertation split |

Appendix as in §5.2. At about 20 minutes of slides, this is ~1.7 minutes per slide, so slides 7–10 may need merging. Decide after discussing the substance.

---

## 6. Smallest credible next step

Unchanged in logic from v2, relabelled. **A desk-based retrospective audit** of one richly documented programme: reconstruct RQ1 (what the decision-maker knew), RQ2 (decision space and scenarios, from documents), and RQ3 as an audit of the sources available *at design time*, then trace closeout results back to design choices **[O]**. Criteria: design documentation tracing evidence use; M&E data over the programme's life including a closeout evaluation; geographic specificity; real scale; preferably cash vs. safety net. Cautions: hindsight bias (use date-stamped information only) and selection toward well-documented programmes **[I]**. No programme is named; I have not verified that any meets all criteria. Later, optionally, the owner contacts the partner to validate details. No human subjects now.

---

## 7. Claims to keep, soften, or remove

*Accepted [O] in the previous round. Carried forward; ★ = added in v2 or v3.*

| Claim | Verdict | Why | Gate |
|---|---|---|---|
| Asymptotically complete corpus | **Remove** | No stopping rule; "80% clinical" figure contradicted/unverified [V] | Saturation rule and documented coverage gaps |
| Outlier trial reveals flaw/confounder | **Soften** | Heterogeneity expected (Vivalt 2020); little power with ~10 trials | Measured modifiers, model of expected heterogeneity, enough trials |
| Empirically calibrated priors | **Soften** | Needs comparable estimands (Meager: seven microcredit experiments) | Common scale and comparable treatments across several located trials |
| Universal reliable impact ranges with valid CIs | **Remove** | Depends on transport assumptions | Bounds with stated sensitivity |
| Impact estimates in novel localities | **Soften** to tiered claim | Critique rates data yellow [V] | Green condition in the critique's go/no-go table |
| Neural causal tools | **Future work** | No evidence of enough sites | Multi-site dataset and a baseline they beat |
| DML as confounding control | **Soften** | DML concerns nuisance estimation [V] | A design where that is the problem |
| Simulation-response exercise and dashboard | **Remove** | Unsupported labels | Linked data, identifiable effects, validated model, demonstrated user value |
| "Planners can't wait for an RCT lookup" | **Remove** as framing | ALNAP sample nonrepresentative [V] | Replace with a test of residual discretion |
| "Market link breaks → switch to in-kind" | **Soften** | A modality hypothesis | Local market evidence and feasibility |
| Armenia collaboration | **Dropped [O]** | Not far enough along | Resolved |
| "Complete transport engine proof of concept" | **Remove** | Contradicts tracker maturity [V] | n/a |
| Compound-shocks panel supports transfer | **Keep, narrowly** | Context panel only [V] | Observed intervention, timing, outcomes |
| JMMI as additional market context | **Keep, qualified** | Coverage, definition, rights gates [V] | Audit, provider answers, separate approval (**gate unchanged**) |
| ★ Participatory DAGs and scenarios produce usable log-frames | **Proposal** | Nothing in repo yet | Document-derived version first; partner later |
| ★ New evidence adds value over what the decision-maker has | **Open hypothesis** | The agenda's motivating claim | RQ1 audit; bounded value-of-information judgment |
| ★ Pre-stated predictions validate the transport claim | **Proposal; one case at a time** | Needs a planning-phase partner | Pre-registration, informativeness criterion, partner and ethics |
| ★ Decision-process usefulness is measurable | **Open** | One decision has no counterfactual | Calibration, stepped introduction, or cross-decision comparison |
| ★ Related-decision synergies can be modeled | **Proposal** | Dependency layer on log-frames | One decision first |
| ★ Willingness to pay for evidence can be validated against consultant or grant pricing | **Parked [O]** | Too detailed for now | Revisit after RQ1 instrument exists |

---

## 8. Unresolved owner choices

1. **Confirm the milestone reading** in §4: "thesis" is the end-of-year-3 milestone; "dissertation" is year 5 or 6.
2. **Define "validated" for RQ1 and RQ2** at the thesis milestone.
3. **Transfer card placement** in the talk: option (a) pipeline slide, (b) method slide, or (c) extra slide.
4. **Value-of-information literature review:** who does it and when; check the reading list in §3.1.
5. **Selection-bias mitigation** for RQ1: which of the three options (or others).
6. **Informativeness criterion** for the prospective prediction: baseline and minimum effect.
7. **Case search:** who runs it (desk research by me, a Gemini sweep, or you) and where to look.
8. **Compressed structure:** approve the §5.3 sketch or choose another cut.
9. **Portfolio layer** in the first talk: documented extension (my suggestion) or included.

*Not touched: strategy v3, Marp deck, tracker, plans, JMMI integration gate, Bangladesh linkage gate.*
