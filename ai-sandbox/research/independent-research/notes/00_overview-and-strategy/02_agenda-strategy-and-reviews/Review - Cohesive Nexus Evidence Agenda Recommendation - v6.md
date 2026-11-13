# Review and brainstorm: a cohesive nexus evidence agenda (v6)

*Claude, 2026-11-12, sixth pass. Folds in the source probe, the documentation probe and the novelty spot check, for the Friday peer talk (fellow PhD students, 30 minutes). Review only: Presentation Strategy v3, the deck, tracker and project plans are untouched. This is a spot check, not an exhaustive search; where evidence runs out, this version says so and recommends wording.*

**Tags.** **[V]** verified project behavior or checked against a primary text. **[C]** checked by me against a transcript or source file. **[S]** relies on Gemini's summary only. **[I]** interpretation. **[P]** proposal. **[O]** owner decision.

## Version history

| Version | What it was |
|---|---|
| v1 to v4 | Framings, staged pipeline, RQ relabel, value of information, validation definitions, 2x2 buildout, deck sketch |
| [v5](Review%20-%20Cohesive%20Nexus%20Evidence%20Agenda%20Recommendation%20-%20v5.md) | Partner funnel, gate inventory, timeline, saturation subproject, pre-registration, triage, procurement |
| **v6** | this file: novelty and documentation-probe findings, first-case recommendation, talk wording, open choices |

**Carried by reference, unchanged:** v5 §1 (partner funnel), §2 (gates), §3 (timeline), §4 to §7; the 12-slide sketch and appendix plan (v4 §7); the claims table (v3 §7, v4 §9, v5 §9) with additions in §5 below.

## What changed from v5

1. **Novelty status per research question**, after reading the claim-bearing papers (§1).
2. **First case recommendation** from the documentation probe (§2).
3. **Talk wording**: what is safe to say, what to reword, what to drop (§3).
4. **RQ1 prior art still to look at**, with what to look for (§4).
5. Claims table additions and open choices (§5, §6).

---

## 1. Novelty status after the spot check

Sources: Gemini's `Novelty Check - Claim Spot Check - v1` and my [Claude Claim Check v1](../03_novelty-check/Novelty%20Check%20-%20Claude%20Claim%20Check%20-%20v1.md). Papers read were the 13 priority-1 transcripts; three RQ1 documents (ALNAP, IDinsight, Elrha) were not obtained.

| RQ | Status | Basis |
|---|---|---|
| **RQ1 knowledge audit and value of information** | **Distinct from the nearest prior art I found; not shown to be unaddressed.** | Brown, Salisbury and Ball (2025) apply value of information to grant allocation (a $3.4M trial against about $190M of funding it could redirect) **[C]**. They do not address crisis settings or programme-design choices in the five pages. IDinsight's simulation-based tool for deciding whether to commission an evaluation is closer in spirit and is **unread** **[S]**. |
| **RQ2 decision space** | **Narrower gap than first claimed.** | Cyclic causal models exist mathematically (Bongers et al. 2021) but say nothing on participatory elicitation **[S]**. Tennant et al. (2021) is a review of how DAGs are reported in health research, **not** a participatory method **[C]**. No precedent found yet for participatory DAG mapping with practitioners. |
| **RQ3 transfer** | **Partly answered by the transport and site-selection literature.** | Transport theory, partial-identification bounds (Gechter 2024) and k-median site selection (Montiel Olea et al.) exist **[S]**. Prediction platform and replication-prediction models exist (DellaVigna, Pope and Vivalt 2019; Altmejd et al. 2019) **[S]**. |
| **Saturation as a stopping rule** | **Capture-recapture exists in medical reviews; no gap map using it found.** | Kastner et al. (2009) and White et al. (2020) **[S]**. Absence in gap maps is a search result, not a proof. |

**Correction to carry:** Crost, Felter and Johnston (2016) found that conditional cash transfers *decreased* conflict incidents and insurgent influence in treated villages (first 9 months), with displacement not ruled out **[C]**. The sabotage finding belongs to their 2014 paper on a community-driven development programme. Gemini's Summary v4 line 71 and RQ3 v4 line 58 say "increased"; they are wrong.

**Reference hygiene [V]:** all DOIs in the v4 reference list resolve to the cited papers except the arXiv entry (registry-resolved elsewhere). Identifiers come from registries, not model recall.

---

## 2. First case for the desk audit

Sources: the documentation probe, Gemini scores v2 (out of 16: Ethiopia PSNP 4 = 14, Kenya HSNP2 = 13, Somalia = 11) and my two spot checks.

| | Kenya HSNP Phase 2 | Ethiopia PSNP 4 | Somalia |
|---|---|---|---|
| Document trail | **Checked by me [C]**: inventory, seven options, Option 3, completion-review figures | Closeout documents (ICR, IEG review) **not checked** | Status "no ICR disclosed" **not checked**; needs a browser |
| Fit with the agenda | Drought, **not conflict**. The seven options vary scale, speed and financing, **not intervention type** | Larger programme, wider design choices [S] | Conflict setting, thinner record [S] |

**Recommendation [P]:** use Kenya as the worked illustration for Friday because its trail is verified, and say plainly that it is a drought case whose options differ in scale, not in intervention type. Treat Ethiopia as the likely better *audit* case and have someone spot-check its closeout documents before committing. Do not present the Gemini score ranking as a result; it is a first-pass rubric. **[O]** First-case choice remains yours.

**Pending Kenya checks you agreed to:** log-frame and evidence trace on HSNP2; prediction-power check for a pre-registered terminal evaluation; triage-funnel sanity check on the Business Case. Not started; not needed to give the talk.

---

## 3. Wording for the talk

**Safe to say [C]/[S]:**
- Value of information is established in health economics and has recently been applied to philanthropic grant allocation (Brown et al. 2025).
- Mayors in a large Brazilian experiment attached positive value to research, and a research session raised adoption of a tax-reminder policy by 10 points, from 32 percent (Hjort et al. 2021) **[C]**.
- Cash transfers can reduce conflict incidents in a conflict setting (Crost et al. 2016), but village-level effects may reflect displacement **[C]**.
- A fiscal multiplier of about 2.5 for large cash transfers in Kenya (Egger et al. 2022) **[C]**.
- Minimax site selection for external validity reduces to a k-median problem (Montiel Olea et al.) **[S]**.

**Reword:**
- Not "nobody has done an evidence audit for programme design" but "the nearest prior art I found values research for grant allocation; I have not yet read the IDinsight or ALNAP work".
- Groh et al. (2016) is a wage-subsidy trial with a large short-lived effect, **not** an example of expert forecasting failure **[C]**.
- Bongers et al. provides mathematics for cyclic models, not a participatory method **[S]**.

**Drop:** Tennant et al. as a participatory-DAG precedent; any statement that cash transfers provoke rebel sabotage.

---

## 4. RQ1 prior art still to look at (a short manual task)

Three documents could narrow the RQ1 claim. A 20-minute look at each is enough; what to look for:

1. **IDinsight, "Improving decisions about evidence: IDinsight's new Value of Information work" (blog, March 2022).** Does the tool apply to *programme-design* choices or only to "commission an evaluation or not"? Any humanitarian or crisis example? What inputs does it need (priors, deadline, costs)? Is there a step that audits *existing* evidence before simulating a new study?
2. **ALNAP / ODI, Campbell and Knox Clarke (2019), on humanitarian decision-making.** Gemini quotes "only 3.4 percent of recorded decisions referenced research"; verify the figure, its definition and sample. The report title differs between sources (the handoff and Gemini give different titles); confirm the exact title.
3. **Elrha, Smith, Swithern and Harrison (2022), on evidence use in the humanitarian sector.** What is the main finding on *why* evidence is not used? Does it propose a method for deciding when evidence is worth seeking?

The three claims in Gemini's RQ1 note rest on landing pages only **[S]**; none should be quoted aloud before this look.

---

## 5. Claims table additions

| Claim | Verdict | Gate |
|---|---|---|
| RQ1 is distinct from Brown et al. 2025 | **Supported in scope [C]** | State as "nearest prior art found" |
| RQ1 has no prior art in humanitarian settings | **Not supported** | Read IDinsight, ALNAP, Elrha first |
| Cash transfers increased insurgent violence (Crost) | **Wrong [C]** | Replace with the finding in §1 |
| Tennant et al. shows participatory DAG elicitation | **Wrong [C]** | Drop |
| Kenya HSNP2 is a conflict-setting case | **Wrong [C]** | Describe as a drought case |
| Ethiopia is the best first audit case | **Unverified** | Spot-check closeout documents |

## 6. Open choices

Carried from v5 §8: funnel time-box, IRB scope for outreach, gate presentation for the talk (four-gate version suggested), who runs the saturation literature check, pre-registration registry, peer talk date (Friday), whether to start the case-source listing.

New:
1. **First case:** Kenya as illustration with caveats, and Ethiopia as the likely audit case?
2. **RQ1 prior art:** will you look at the three documents (§4) before Friday, or present RQ1 with the reworded claim only?
3. **Gemini notes:** ask Gemini for a `v5` novelty set with the Crost correction, or rely on this review and the two spot-check notes?

*Not touched: Presentation Strategy v3, Marp deck, tracker, plans.*
