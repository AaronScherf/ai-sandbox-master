# Review and brainstorm: a cohesive nexus evidence agenda

> **Version note (added 2026-11-10 when versioning began).** This is **v1**, the first pass, before the owner's response. The original file was overwritten in place before any copy was kept, and it was never committed, so this file is **reconstructed from the text written in that first pass**, with this note added. Labels here are the v1 labels: RQ1 = transfer, RQ2 = use. Later versions relabel; see v3's label key. Current version: v3.

*Claude, 2026-11-10, answering the [handoff](Handoff%20-%20Cohesive%20Nexus%20Presentation%20Agenda%20Review.md). Review only: the v3 strategy, deck, tracker and project plans are untouched. Every recommendation below is for the owner to accept or reject. No framing has been chosen and no empirical study selected.*

**Tags.** **[V]** = verified project behavior (what the repo documents). **[I]** = plausible interpretation. **[P]** = new proposal from this review.

**What I read.** The v3 strategy, original narrative (summary, slides 10–15), nexus focus analysis, source verification, `PROJECTS.md`, the follow-up transportability critique (Q1 and Q3), and the Marp deck's slide titles. I did **not** reread the critique analysis, the first revised strategy, the 3R revision, the transcript, the JMMI feasibility review (cited via v3's summary of it), or the Marp slide bodies. External sources are cited as the repo's own documents cite them; I did not re-fetch them this session.

---

## 1. Diagnosis

**[V] What v3 got right.** It makes the prolonged-crisis choice the center, treats the "cash vs. insurance" frame as a hypothetical decision rather than a live portfolio, demotes the simulator to a conditional future product, and adds a qualified JMMI example (slides 7 and §3). It also correctly adds the "cannot identify" branch at slide 11.

**[I] Why slides 12 and 13 lost focus.** Compare the three versions of the back half:

| Slide | Original | v3 | What went wrong in v3 |
|---|---|---|---|
| 10 | Evidence cycle, "asymptotically complete" corpus | What could travel (treatment, market, institution, population links) | Fine. Best slide in the section. |
| 11 | Covariate shift, "satisficing" | Transportability, conditionally, with a four-way decision tree | Fine. The tree (estimate / bounds / mechanism hypothesis / no inference) is the best structural idea in v3. |
| 12 | Structural breaks: a DAG audits whether the causal chain is intact *before* covariate adjustment | "Repeated shocks": a shock can invalidate an earlier borrowing decision; the panel characterizes exposure | The topic changed from *mechanism failure* (a property of the causal model) to *temporal monitoring* (a property of the panel). The DAG, the treatment-version question and the interference question all disappeared. Slide 12 now points back at the panel, not forward at the transfer model. |
| 13 | Method toolkit: which estimator, under which assumptions | Resilience, anticipatory action, risk finance | Method selection vanished and a *substantive domain* arrived. It reads as a new strand because the audience never saw a method slot close. |
| 14 | Simulation exercise | Decision-specific brief | Good change, but the bridge from 13 is now a domain list, so the brief has no method to be the output of. |

**The strongest through-line worth keeping [P]:** *for a specified decision, ask what differs between source and target, which differences the available data can diagnose, what local learning could close the gap, and whether the answer changes a choice once local constraints are known.* v3 holds the first and last links but lost the middle two.

---

## 2. Three agenda framings

**A. Evidence-adaptation process (v3 as written).** The object of study is the process of finding, appraising and adapting evidence for a decision.
- *For:* matches the owner's liked changes; hard to attack on feasibility.
- *Against:* a process is not a falsifiable object, and it is the framing that let slide 12 drift. "Adaptation" can mean anything from a literature brief to a model.

**B. Conditional causal-transfer model (original, narrowed).** The object is a transport model: when does a source effect travel, and what is the target estimate?
- *For:* sharpest; has a theory (selection diagrams, Pearl–Bareinboim; conditional-effect exchangeability and positivity, Dahabreh et al., both cited in the [follow-up critique](../03_rct-transportability/Follow-up%20-%20Data%20Availability%20and%20Transportability%20Critique.md)).
- *Against:* assumes decision relevance, which is the owner's explicit objection; and the critique's own verdict is *yellow*: eligible trials and site coordinates are not established **[V]**. Risks a methods paper with no data.

**C. A graded transfer claim, with its decision value tested (recommended).** The object is a **transfer claim for one decision**, with two linked questions:
- **RQ1 (transfer, mostly conceptual/methodological):** For a named intervention version and target setting, which links between source and target (treatment version, mechanism, delivery institution, market/payment link, population/displacement, interference) differ, which of those differences can be diagnosed or tested with available data, and what is the strongest output the evidence supports: a target estimate, bounds, a mechanism hypothesis, or no inference?
- **RQ2 (use, empirical):** For a specified, revisable transition decision, does that graded claim add anything once local constraints and institutional discretion are known, and does it change an option, a design feature, timing, or a monitoring plan?

*For:* keeps the transfer model visible (RQ1) while making relevance an empirical question (RQ2); every output tier is publishable, including "do not borrow"; the 2×2 supplies inputs without being the claim. *Against:* two questions can sprawl; the discipline is that RQ2 is tested on one decision before RQ1 is generalized.

**What is new vs. open [I].** Transportability theory, heterogeneity of impact evaluations (Vivalt 2020) and evidence-use barriers (Elrha; ALNAP) are established, not new. The proposed combination is: (i) treating the *output tier* as the unit of analysis, including an explicit non-identification branch; (ii) a transfer card whose fields come from the evidence map; (iii) a *constraint-first* test of whether evidence adds value. I could not verify that nobody has done (iii); frame it as an open hypothesis, not a gap claim.

---

## 3. Proposed 15-slide argument map

Slides 1–9 keep v3 with two edits. **[P] Edit 1:** make the evidence-card fields on slide 6 and the map attributes on slide 8 identical to the nodes used in slide 12 (treatment version, delivery institution, market/payment link, population, horizon). This is the cheapest way to make the 2×2 *feed* the transfer model instead of sitting beside it. **Edit 2:** slide 5's feedback arrows should end in the "transfer claim," not in a simulator.

| # | Slide | Source | Note |
|---|---|---|---|
| 1 | Hypothetical repeated-drought choice | v3 | Keep. Name it as hypothetical. |
| 2 | Decision space, not a handoff | v3 | Keep; add "where is there residual discretion?" as the question that returns on slide 14. |
| 3 | What existing evidence and practice answer | v3 | Keep; source audit prevents ALNAP/DEEP/DRC mischaracterization. |
| 4 | Reproducibility ≠ identification ≠ transport ≠ use | v3 | Keep; this four-way separation is reused on slide 11. |
| 5 | The 2×2 as inputs to a transfer claim | v3 + Edit 2 | |
| 6 | 1.1 Evidence cards | v3 + Edit 1 | |
| 7 | 1.2 Context data, JMMI as source audit | v3 | Unchanged. JMMI gate untouched. |
| 8 | 2.1 Evidence boundary | v3 + Edit 1 | |
| 9 | 2.2 Replicate before transporting | v3 | Bangladesh gate stays an open linkage. |

### Slides 10–15 in detail

**Slide 10: What differs between source and target? (v3 10, sharpened)**
- *Takeaway:* "Cash" is a bundle of links that can change independently; transport is a claim about each link, not about the label.
- *Content:* one source (e.g. NGO-delivered transfer in a functioning market) beside one target (public safety net or interrupted rail after displacement). Define the **target claim** (decision-maker, population, version, comparator, outcome, horizon) before comparing. Name the portable object: effect, mechanism, design principle, delivery lesson, or forecast rule (v3 §6 open question).
- *Visual:* source-to-target bridge with five labelled links.
- *Transition out:* "Some of these differences only shift who is treated; others change what the treatment does."
- *Moves to notes:* original slide 10's feedback loops (already on 5), "asymptotic" corpus, outlier-trial validity, prior calibration (§5 below).

**Slide 11: When can an effect be reweighted? (v3 11 + original 11)**
- *Takeaway:* The easy case is a shift in measured modifiers only; everything else needs more than reweighting.
- *Content:* the covariate-shift case, written plainly: target average = source conditional effect averaged over target modifiers (Dahabreh; Sugiyama 2007 on the definition), requiring the same treatment version and outcome meaning, support overlap, and no unmeasured modifier differing silently. Then the four-way output tree from v3: estimate / bounds / mechanism hypothesis / no inference. Replace "satisficing … valid confidence intervals" with "bounds are only as valid as the assumptions they state."
- *Visual:* v3's decision tree, with the first branch labelled "only measured X shifts?"
- *Transition out:* "The rest of the tree is about what happens when the answer to that first question is no."

**Slide 12: Structural breaks are tests of transportability (rebuilt)**
- *Takeaway:* A structural break is not a bad year; it is a selection node pointing at the *mechanism*, which is the case where reweighting measured covariates is invalid.
- *Content:* draw the transmission chain Transfer → liquidity → market purchase → consumption/asset retention, and annotate where source and target differ (selection-diagram S-nodes):
  1. *Treatment version:* amount, timing, conditionality, modality, duration.
  2. *Mechanism:* does purchase require a functioning market and payment access?
  3. *Institutional delivery:* NGO vs. government vs. mobile-money rail; targeting and registration.
  4. *Market/payment links:* price pass-through, supply response, payment reach.
  5. *Population/displacement:* who is present and observed at endline; returnees and hosts.
  6. *Interference:* spillovers to non-recipients (Egger et al. 2022 illustrate this for cash), which can make a geographic response differ from the recipient effect.
  For each node mark one of: *measured / testable locally / unidentified*. That marking is the slide's payload.
- *What a DAG can do:* show which arrows differ, show why a given adjustment set is insufficient, and list what local observation would test a link. *What it cannot:* supply missing outcomes, prove no unmeasured S-node exists, repair non-positivity (a peaceful rural source may have no support for a siege target), or give a magnitude.
- *Repeated shocks, retained as a corollary:* the target changes over time, so the same audit is re-run when the monitoring indicators for a node move. One bullet, not the thesis. The panel's role is to supply monitoring indicators for market and displacement nodes, not outcomes **[V: the panel is a context panel]**.
- *Do not carry over:* the original claim that when the market link breaks "planners know cash will fail and in-kind food must be deployed." That is a hypothesis about modality, not a result.
- *Visual:* two-column DAG, source vs. target, S-nodes colored by the three markings.
- *Transition out:* "Given which links are measured, testable or unidentified, which method is even admissible?"

**Slide 13: Which method for which claim, and how is it validated? (original 13, restated)**
- *Takeaway:* Method follows the output tier; a validation ladder, not an estimator, is the contribution.
- *Content:* a table linking tier to admissible tool: descriptive comparison (no model); reweighting under measured shift (Dahabreh-type); hierarchical pooling (Meager 2019) *only* with comparable estimands, since pooling cannot create comparable treatments or coordinates **[V: follow-up critique]**; bounds and sensitivity analysis; mechanism hypotheses tested with local monitoring. Validation ladder from the critique: replicate → does a spatial/proxy outcome respond to assignment → does it predict the survey effect → leave-one-trial-out prediction as a *stress test, not proof* → target. Success criterion stated against a simple baseline (pooled mean), with "same sign and similar magnitude" on a common outcome scale.
- *Use cases enter here as test-beds,* one row each: cash/safety-net handoff, anticipatory cash, index insurance. For anticipatory action and insurance the chain gains links (forecast → trigger → financing → delivery → welfare; index → loss → payout → welfare), so they appear as the *same DAG with extra nodes*. That is the missing bridge from v3's slide 13: resilience and risk finance are not a new strand but a longer chain, where basis risk and false alarms are additional transfer failures.
- *Visual:* method × required-assumption matrix, plus a three-row use-case strip.
- *Move to notes/future work:* DML, synthetic controls, Dragonnet/TARNet and neural DAGs. The critique says DML concerns nuisance estimation, not proxy validity, and nothing in the repo shows enough usable sites to fit neural estimators.
- *Transition out:* "Even a valid claim is only useful if someone can act on it."

**Slide 14: Does it help a real decision? (v3 14, with a test attached)**
- *Takeaway:* The product is a contestable one-page transfer card per option, and the empirical question is whether it adds value once constraints are known.
- *Content:* revisit slide 1's choice. For each feasible option the card shows: what was delivered in source evidence; link-by-link comparability status (from slide 12); local tests and monitoring indicators; feasibility veto (access, security, authority, funding); evidence-support status (*supported / contested / unidentified*) instead of a rank; and "what would change this conclusion?" **No ranking of cash vs. in-kind vs. insurance.**
- *Observable help/failure:* record the option set before and after the card; whether the card was available before the decision; whether the decision-maker cites it; whether it names an information gap that later becomes a monitoring indicator; and, where the decision is revisable, whether a pre-stated directional prediction matched later monitoring. *Failure signals:* no residual discretion after constraints; evidence arrived late; evidence did not discriminate among surviving options; decision-maker did not trust or read it.
- *Visual:* the card prototype plus a small "constraint-first funnel": options → remove infeasible/mandated → remaining discretion → does evidence discriminate?
- *Move to notes:* the simulation exercise, the cost-per-life-saved dashboard, and the $5M budget mock-up (§5).

**Slide 15: Research questions and the smallest next step (v3 15, restated)**
- *Takeaway:* RQ1 and RQ2, three gates, one decision.
- *Content:* the two questions from §2; the three gates from v3 (decision access → comparability → evaluable use); the next step in §6; unresolved items in the open-questions list. JMMI stays research-only and Bangladesh stays gated.

---

## 4. Use-case comparison [I unless noted]

| Case | Transfer question clarity | Data feasibility now | Decision access | Fit as a *use case* |
|---|---|---|---|---|
| **Cash → safety net handoff** | High: same nominal transfer under NGO vs. public rail vs. interrupted payments | Low for outcomes. The panel is context-only [V]; Option C (Baxnaano) access check is unrun and "may end the option" [V] | Unknown; needs partner | **Best spine example for slides 1, 10, 12, 14.** Broadest relevance, but the deck should not claim target outcome data. |
| **Anticipatory cash** | High and *observable*: timing, forecast, trigger, delivery, outcome | Published evaluations exist (Oxford Bangladesh; WFP Nepal; NBER working paper) [V: source verification] but are disaster, not conflict, settings | Unknown | **Best slide-13 test-bed.** Source is real; whether it transfers to conflict is exactly the question. Do not use the unverified "GoDARTS" platform. |
| **Index insurance** | High, with a clean split (index–loss fit vs. payout vs. welfare) | Blocked: Bangladesh replication lacks public village coordinates [V]; funder thresholds are unverified [V] | Unknown | **Contrast case in notes or an open question**, not the example the deck depends on. |
| **Economic inclusion / graduation or displacement–return** (different case) | Medium: the target population itself changes | Not assessed in the repo; **I have not verified** which trials or data exist | Unknown | Keep as the "different prolonged-crisis case" the handoff asks about, as an open choice for the owner. |

Everything in the "decision access" column requires a partner nobody has identified. Marked here once so it need not be repeated.

---

## 5. Claims to keep, soften, or remove, with the gate that would make each defensible

| Original claim | Verdict | Why | Gate to make defensible |
|---|---|---|---|
| Asymptotically complete corpus | **Remove** | No stopping rule; the HEP "80% clinical" figure behind the gap story was contradicted/unverified [V: source verification] | Pre-stated search/saturation rule and documented coverage gaps (empty vs. unindexed vs. inaccessible) |
| Outlier trial reveals flaw/confounder | **Soften** | Heterogeneity is expected (Vivalt 2020); an outlier may be a real mechanism difference. With ~10 trials there is little power to say which | Measured modifiers, a stated model of expected heterogeneity, and enough trials; otherwise treat as a diagnostic prompt |
| Empirically calibrated priors | **Soften** | Needs comparable estimands; Meager's example is seven microcredit experiments | Common outcome scale, comparable treatment versions, and several located trials |
| Universal reliable impact ranges with valid CIs | **Remove** | Validity depends on the transport assumptions; no repo evidence supports the claim | Bounds with explicit sensitivity analysis |
| Impact estimates in novel localities | **Soften** to "tiered transfer claim" | The critique rates the data yellow [V] | The green condition in the critique's go/no-go table (≥2 trials with accessible assignment/outcome/site links and overlap with a named target) |
| Neural causal tools (Dragonnet, TARNet, neural DAGs) | **Move to future work** | No evidence of enough sites; applicability unverified | A usable multi-site dataset and a baseline they demonstrably beat |
| DML as confounding control | **Soften** | DML is about nuisance estimation, not proxy validity [V: follow-up] | A specific design where nuisance estimation is the problem |
| Simulation-response exercise (cash/food/index options, $5M dashboard, "high expected impact" labels) | **Remove** | The labels are unsupported assertions; v3 already treats a simulator as conditional | Linked data, identifiable target effects, a validated transport model, and demonstrated user value |
| "Planners can't wait for an RCT lookup" | **Remove** as framing | ALNAP's sample is nonrepresentative; the acute window is a boundary, not the center [V] | Replace with a testable claim about residual discretion |
| "If the market link breaks, switch to in-kind food" | **Soften** | A modality hypothesis, not a result | Local market-link evidence and a feasibility check |
| Armenia foundation collaboration "in progress" (original slide 14) | **Owner must confirm or drop** | I found no support in the files I read | A named partner and what they asked for |
| "Complete transport engine proof of concept" (original roadmap) | **Remove** | Contradicts the tracker's maturity: transferability is planned with no repo [V] | n/a |
| Compound-shocks panel supports transfer | **Keep, narrowly** | Built and reproducing, but a context panel without intervention or outcomes [V] | Observed intervention, timing and outcomes before any treatment claim |
| JMMI as additional market context | **Keep as qualified** | Somalia sampled data are NFI vendor prices; coverage ends May 2024; Sudan API failed; reuse rights open [V] | Country-round audit, provider answers and a separately approved analysis change (**gate unchanged**) |

---

## 6. Smallest credible next step [P]

**A constraint-first decision audit for one transition decision.** It tests the motivating claim (does external evidence add value once local constraints and discretion are known?) *without* building a transport estimator, a simulator, or a "best intervention" result.

1. **Choose one revisable decision with documentable history.** Candidates: a Somalia cash-to-safety-net transition (ties to Option C, which still needs its access check), or another owner-chosen case. Documents first (programme plans, public reviews); interviews only with a partner and the review the study requires.
2. **Reconstruct the choice set.** For each option record who could decide, the mandate, funding window, security and access constraint, and when it could be revisited.
3. **Apply the constraint-first screen.** How many options survive? If constraints already pin the choice, external evidence adds nothing, and *that is a finding*.
4. **For surviving options, fill the transfer card from existing sources.** Use the evidence map and context panel (slides 6–8). Mark each link as measured, testable, or unidentified. Do not estimate an effect.
5. **Judge discrimination and timing.** Did the evidence available at decision time separate the surviving options? Would a named local indicator have changed a design or a monitoring plan?

*Smallest success:* one decision with real residual discretion, where the card changed the assessed option set or exposed a gap the decision-maker agrees was decisive. *Informative failures:* no residual discretion; evidence not available in time; evidence did not discriminate; barrier is trust or authority. Each of these answers RQ2 and each is reportable.

*Needs outside parties:* a partner (or public documentation rich enough to proceed without one), ethics review if interviews are used, and any data owner's permission. Nothing here changes the JMMI production gate, the Bangladesh linkage gate, or any approval.

---

## 7. Unresolved owner choices

1. **Framing:** A (process), B (transfer model), or C (graded claim + decision test; recommended)? Everything else waits on this.
2. **Spine example:** cash→safety net (recommended), or another case? And is anticipatory cash the slide-13 test-bed, or does it become the main case?
3. **Weight of RQ2:** a headline question, or a secondary test after the transfer work?
4. **Temporal transport:** is "the target changes over time" a corollary (my recommendation) or its own strand?
5. **Armenia foundation claim:** confirm status or drop.
6. **Decision for the audit:** which transition decision, and whether to open partner conversations or start desk-based.
7. **Human-subjects route** if any practitioner interviews are in scope.
8. **Whether the deck's audience** is a committee, funders or practitioners. It changes how much slides 11–13 can carry.

*Not touched: v3 strategy, Marp deck, tracker, plans, JMMI integration gate, Bangladesh linkage gate.*
