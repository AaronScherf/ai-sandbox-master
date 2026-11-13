# Process audit: did the v1–v9 reviews drift, and is there a slide document? (v1)

*Claude, 2026-11-12. Review only. Reads the whole trail against the original handoff and the v3 strategy. Not re-read in full: v1 and v2 (taken from the v3 crosswalk and summaries), the critique analysis, source verification, and the 3R documents. Not touched: Presentation Strategy v3, the Marp deck, tracker, plans.*

**Tags.** **[C]** checked by me in the files named. **[I]** interpretation. **[P]** proposal. **[O]** owner decision.

## 1. Short answer
**No, we do not yet have a slide document that can be turned into a final Marp deck.** [C]
- The last slide-by-slide structure for the nexus framing is the **12-slide sketch in v4 §7** (titles plus a "change" note) and the **appendix list A1–A12** (titles plus what each clarifies). Strategy v3 has a full 15-slide blueprint (takeaway, content, visual per slide) but it predates the staged pipeline, the RQ relabelling and everything from v5 on.
- v5 to v9 contain **no slide structure**. They contain talk wording (v6 §3, v8 §5), a decision table (v7 §2), a stakeholder table (v9 §4) and restated RQs (v9 §3), all of which are slide material but not yet slides.
- No document has, for each slide, the assertion, content, rationale, evidence source and speaker note under the **current** framing. The existing `presentation_slides.marp.md` is still the original "Planner's Dilemma" deck and still contains claims we removed (Armenia collaboration, the Simulation Response Exercise and dashboard, DML and neural-DAG slides, outlier-trial detection) [C: grep]. **Editing that deck in place would bring them back.** Build the new deck from a text slide document, not from the old file.

## 2. How the argument moved, and what survives in v9

| Version | Added | Status in v9 |
|---|---|---|
| Handoff | Users, choices, barriers; no live simulator; keep the causal-transfer question visible; cash/insurance only as use cases | Kept, except the transfer-model detail (§3a, §3b) |
| v1–v2 | Diagnosis; three framings; staged pipeline in run order | Pipeline survives only as a list of gates in v5 |
| v3 | RQ relabel (RQ1 audit, RQ2 decision space, RQ3 transfer); value-of-information questions; transfer dimensions; evaluation as terminal state; claims table; 12-slide sketch | RQs **redefined in v9**; dimensions, terminal state and claims table not carried |
| v4 | Validation definitions; 2×2 buildout and saturation; desk audit with support-seeking check; portfolio; predictions from priors; 12-slide sketch; appendix A1–A12 | Mostly absent from v7–v9 |
| v5 | Partner funnel; gates inventory (four-gate talk version); timeline (faculty talk April 2027, IRB); saturation subproject; pre-registered predictions; triage funnel | Absent from v7–v9 |
| v6 | Novelty spot check; first case; talk wording; corrections | Corrections carried; first case became Kenya one-beat |
| v7–v9 | Supply/demand framing; decision table; planner discretion; adversarial scan; distance cases; market-failure framing; stakeholders; no figures | Current |

**Good changes, not drift [I]:** moving from "planners lack evidence" to a measured, sector-dependent question; dropping figures; "planner discretion" as a fact on the ground; correcting Crost, Groh, Tennant; keeping Egger/HSNP only as a hypothesis-generating pair; keeping Kenya to one beat. Each was driven by checked text or your reasoning.

## 3. What dropped out or drifted

| # | Item | Where it was | Why it matters now | Proposed treatment |
|---|---|---|---|---|
| a | **Structural breaks as tests of causal transportability**, S-nodes and what a DAG can and cannot identify | Handoff (your slide 12 complaint); v4 slide 9 and A1 | Absent from v5–v9 [C: grep]. This was the focus problem you named, and the RQ3 "causal transfer model" is now described only as conditioning and output specificity | One slide in the main flow plus A1 |
| b | **Transfer distance dimensions** (spatial, temporal, institutional, market, treatment version, population, interference) | v3 §3.2, A7 | v9 open question 3 ("what is comparable?") is this table. v8–v9 use "distance" without it | Use the table as the starting definition on the RQ3 slide; mark it as the item still under investigation |
| c | **Pipeline, gates, data-insufficient gate, evaluation as terminal state** | v3 §2, v5 §2 | v9 gives RQs but not how they connect or where the work stops | One pipeline slide with the four-gate version (v5 §2) |
| d | **Validation definitions, timeline, IRB, funnel time-box** | v4 §2–3, v5 §1, §3 | Needed for the closing "what next" slide; v9 has none | Closing slide plus A4 |
| e | **Pre-registered predictions** (shrinkage, informativeness criterion, power) | v4 §6, v5 §5 | This is how RQ3 is tested; v9 keeps one phrase | One line in the RQ3 or method slide; A6 |
| f | **Desk audit as the smallest credible next step**, support-seeking check, selection problem | v3 §6, v4 §4 | The talk's "ask" and the answer to "how would you measure RQ1" | RQ1 slide and A9 |
| g | **Consolidated claims table** | v3 §7, v4 §9, v6 §5, v7 §7 | Scattered across four files; the removed claims are listed only in v3 | Write one table (appendix and a guard against old-deck claims) |
| h | **Project maturity (what is built, planned, gated)** and the 2×2 toolkit | A8, strategy v3 §3 | Pre-empts overclaiming; v9 mentions only `reprokit` as an audience principle | A8 plus one toolkit slide or appendix |
| i | **RQ2 redefinition** | v3 (constraints, scenarios, log-frames, thresholds, constraint-first screen) versus v9 (what plans rest on; search versus overload) | The constraint-first screen moved into RQ1 (discretion); A3 (example log-frame) and scenario thresholds have no home | Decide: is the log-frame example an illustration of "assumptions in plans" (v9 RQ2)? [O] |
| j | **Peer talk versus faculty talk** | v4 open choice 2; v5 (April 2027) | Friday is a 30-minute peer talk including questions [O]; the April talk is a longer version. Never stated in v7–v9 | State it at the top of the slide document |

## 4. Overfitting and balance risks [I]
1. **The agenda now looks like a cash-transfer talk.** Kenya HSNP, Egger, HSNP LEWIE, Bedoya (graduation), Crost, Bold are all transfer or livelihood programmes. v8 reports that cash and food are the *abundant-evidence* sectors and that health, shelter, education and refugee self-reliance are sparse. The deck has **no worked example from a sparse sector**, so it could not show the other half of its own claim. The handoff said cash, anticipatory cash and insurance should be use cases, not the agenda. Suggest one line on the evidence-use slide saying the examples are drawn from the best-documented sector.
2. **The empirical case for "mixed and sector-dependent" rests on two Gemini scans (about 31 sources) that I have not read** [S]. The numbers are dropped, which is right, but the claim should be worded "a non-systematic scan suggests", not "the field shows".
3. **Three cases carry the transportability argument:** Egger versus HSNP (explicitly unresolved), Bedoya (you are reading it tonight), and Kenya as a one-beat. State on the slide that they are illustrations chosen for documentation, not a sample.
4. **Anticipatory action and insurance were dropped silently** (strategy v3 slide 13 to v3 decision 3). That was a deliberate owner decision, but it is now only in v3 §3.3; one line in the appendix prevents the question "where is anticipatory action?"
5. **Supply-side novelty is stated as "nearest prior art found".** Keep that wording; do not let it harden into "no one has done this".

## 5. Proposed structure for the slide document (for your reaction)

Thirty minutes including questions: about 12 main slides, appendix on request. **[P]**

| # | Slide (assertion) | Built from | State |
|---|---|---|---|
| 1 | A planner in a prolonged crisis must choose among designs | Strategy v3 slide 1, v7 §6 | Ready to write |
| 2 | What the nexus is, who decides and how much room they have (nexus definition, planner discretion, **stakeholders**) | v7 §6, v9 §1, §4 | Ready; definition is my wording, not sourced |
| 3 | Evidence is worth seeking only if it could change the choice (value of information; decision table) | v7 §2 | Ready |
| 4 | What exists, and what the evidence-use picture looks like (qualitative) | v7 §1, v8 §1 | Ready with the §4.2 caveat |
| 5 | Kenya: plentiful evidence did not decide the option (one beat) | Kenya check v1, v7 §5 | Ready |
| 6 | The mismatch is of relevance, not price; the three questions | v9 §3 | Ready |
| 7 | RQ1: measure discretion and the value placed on evidence (desk audit first) | v3 §3.1, v4 §4, v9 §3 | Needs the desk-audit detail restored |
| 8 | RQ2: what plans rest on; search versus overload | v9 §3 | Reconcile with §3i |
| 9 | RQ3: how far does a finding travel? Distance dimensions; "comparable" still open | v3 §3.2, v9 §2 | Open question 3 |
| 10 | Test case: two Kenya cash studies, different spillovers (replication list) and Bedoya as the aspirational case | Replication slide draft v1, v9 §2 | Pending your Bedoya reading and the transcriptions |
| 11 | What a model can claim: structural breaks, selection diagrams, output types, pre-registered predictions | v4 slide 9, v4 §6, v3 §3.4 | Needs the restoration in §3a and §3e |
| 12 | Next step, gates, timeline, how it will be validated | v5 §2–3, v4 §2 | Needs to be rewritten for the new RQs |

Appendix: A1–A12 from v4 §7, updated; plus the consolidated claims table and a line on dropped use cases.

## 6. What I propose to do next
1. Write **Slide Document - Nexus Evidence Agenda - v1.md**: for each slide, the assertion, content, why it is there (rationale), the source with its evidence tag, speaker notes, and a "do not say" line from the claims table. Slides 7–9 and 11–12 will draw on the restored v3–v5 material, marked **[P]** where I am proposing the update.
2. Hold slide 10 and the three open questions (taxonomy, headquarters/field, "comparable") as marked gaps until you have read Bedoya and the Gemini reports.
3. Only then create the new Marp file, in its own name, leaving the old deck untouched.

**Owner choices needed:** (a) the 12-slide list above, or a different cut; (b) whether the stakeholder content sits in slide 2 or on its own slide; (c) whether RQ2's old constraints and log-frame work stays visible (§3i); (d) how much of the pipeline and timeline goes into the main flow versus the appendix.
