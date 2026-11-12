# Handoff to Gemini: novelty claim spot check (time-boxed, for a Friday peer talk)

Written 2026-11-12 by Claude. This is a SPOT CHECK, not an exhaustive search. Aaron presents to fellow PhD students on Friday (30 minutes). Goal: decide which Gemini novelty claims are safe to say aloud. Stop when the table below is filled; do not widen the search.

## Rules
- Read only the transcripts in `C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\journal-articles\novelty-check\processed_outputs\` (Markdown, `<!-- page N -->` delimiters). Do not re-fetch papers or cite anything from memory.
- For every claim: give a verdict (SUPPORTED / NOT SUPPORTED / PARTLY / NOT FOUND IN TEXT), a short verbatim quote (under 25 words) and its page number. If you cannot find a passage, say NOT FOUND; do not infer.
- Do not edit existing notes. Write one new file: `Novelty Check - Claim Spot Check - v1.md` in your worktree `notes/00_overview-and-strategy/`. No commits to main; do not touch other worktrees.
- Tags: use FULL-TEXT-READ only for what you actually read in the transcript.
- No API spend beyond your normal session.

## Claims to check (file stem, then the claim as Gemini's Summary v4 or RQ notes state it)
1. `1-s2.0-S0304387815000966-main` Crost et al. 2016. Already verified by Claude: the paper finds cash transfers DECREASED conflict incidents and insurgent influence (displacement not ruled out). Just confirm and record the page; then list every place in Summary v4 / RQ3 v4 that says "increased" and must change.
2. `hjort-et-al-2021-...` Hjort et al. Summary v4 line 58: Brazilian mayors' willingness to pay for research via BDM trials. Also: is there a "10 percentage points" effect claim, and what exactly is it about?
3. `10-1371-journal-pone-0225826` Altmejd et al. Is there a "65-70%" figure? What is it (accuracy of what, on what)?
4. `10-3982-ecta17945` Egger et al. Summary v4 line 72: "2.5 local fiscal multiplier with minimal inflation". Check the multiplier value and the inflation statement.
5. `rest_a_00584` Groh et al. and `10-1086-699976` DellaVigna and Pope: Summary line 70 "experts overestimate wage subsidy persistence in Jordan". Is that what Groh found? Is the DellaVigna and Pope trial about forecasting?
6. `brown-et-al-2025-valuing-information-as-a-philanthropic-funder` (5 pp): the NEAREST PRIOR ART for RQ1. What exactly does it do (EVPI/EVSI for grants vs research)? Does it cover humanitarian or crisis settings, programme-design choices, or decision-specific evidence audits? Quote what it does and does not claim.
7. `10-1214-21-aos2064` Bongers et al.: do the cyclic models cover feedback loops of the kind in participatory system maps, and does it say anything about practical elicitation? (Only what the abstract and intro support.)
8. `10-1093-ije-dyaa213` Tennant et al.: what do they say about participatory or expert-elicited DAGs? Is it a participatory (stakeholder workshop) method or a literature-based one?
9. `science.aaz1704` DellaVigna, Pope and Vivalt: what is the platform, what is recorded, and is it pre-registration of predictions?
10. `10-48550-arxiv-2408-09187` Montiel Olea et al.: confirm the k-median result and whether it addresses site selection under policy-relevant covariates.
11. `Generalizing the Results from Social Experiments...` Gechter: confirm the partial-identification bounds claim.
12. `1-s2.0-S0895435608001509-main` Kastner et al. and `saran-2020-evidence-and-gap-maps` White et al.: does Kastner use capture-recapture to judge saturation of literature searches, and does White et al. say anything on stopping rules for gap maps? (Supports the Summary v4 line 45 claim that no gap map uses quantitative stopping rules; judge only whether these two papers contradict it.)

## Output format
One table: claim number, source stem, verdict, quote, page. Then three short lists: (a) claims safe to say in the talk, (b) claims that need rewording (give the corrected wording), (c) claims to drop. Finish with a one-paragraph read on how the RQ1 contribution compares with Brown et al. (2025), without recommending anything about the talk.

## Not in scope
Missing PDFs (Campbell and Knox Clarke, IDinsight, Smith et al.), the 5 oversized skipped files, the 28 P2 papers beyond those named, references without DOIs.
