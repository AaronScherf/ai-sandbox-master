# Literature taxonomy: term-selection trials and rollout readiness (2026-11-06)

Branch `claude/literature-reextract-v4` (docs only; nothing landed). Code was on `codex/term-selection` (commit 5edc1a61, rebased to 73b2b1b5) and is stacked under this docs branch, to land together. Design:
[term selection](../../superpowers/specs/literature_taxonomy/2026-11-03-term-selection-design.md). Earlier state: [subproject status](2026-11-03-subproject-status.md).
Working data, keys and scripts: `ai-sandbox/research/.agent_work/term-selection-trials/` (gitignored; its README says how to use it).

## Result in one paragraph

Two trials on 28 papers (double pass, subscription Gemini) changed term selection from "pick the most specific child that shares a theme" to a stepwise fit test
(`refine-v3`, `extract-v6`). Label-level precision went from about 0.3 (old labels) to roughly 0.93 to 0.96 (trial 2), above the 0.85 bar, on estimates built from
several judges and three small owner audits. The rollout was held because Gemini's session limit has not reset; it is planned for the next working day.

## What each trial did

| | Trial 1 (`refine-v2`) | Trial 2 (`refine-v3`) |
|---|---|---|
| Change | Tree listing with definitions; "choose a child only when its definition describes something the paper does" | Numbered stepwise check: start at the group, go to a child only on a quoted passage matching the child's definition; four worked examples |
| New distinct labels | 179 | 134 |
| Judge acceptance | 0.58 (all judges accept) to 0.90 (any accepts) | 0.72 (all) to 0.93 (any); Codex alone 0.84 |
| Owner-corrected | about 0.60 to 0.65 | about 0.93 to 0.96 (see below) |
| Shape of change | Many leaf labels that only shared a theme | Good labels 104 to 96, weaker labels 75 to 38; 33 of 104 trial-1 agreed-good labels dropped, 25 new agreed-good added |

Judge agreement: Gemini with Codex 69%; Codex with Haiku 85% (33 labels). Judges that saw only the label path were stricter than the owner.

## How the trial 2 figure was built

1. 96 labels accepted by every judge, counted as correct.
2. 38 contested labels (28 where judges split, 10 that every judge rejected). Owner audit of 16, with up to three judge-cited pages each, verdicts hidden:
   split group 6 fair of 7 answered (1 can't tell); rejected group 4 fair, 2 not fair, 2 can't tell, after two Agrobiodiversity items were reversed
   (below). Extending those rates over the 38 gives about 0.94 to 0.96.
3. Owner audit of 8 random labels from the 96: 8 of 8 fair.
4. Definition-aware re-judge (Haiku) of the 38: 28 supported, 10 not. Accepting its calls gives 124 of 134, 0.925. It agreed with the owner on 9 of 12
   decided labels.

Range reported: 0.93 to 0.96. The bar (0.85) was written as paper-level precision; this is label level. The paper-level figure has not been computed.

## Findings worth keeping

- **Agrobiodiversity** was chosen three times and rejected by every judge and by the owner on first reading. The official 3ie definition (checked word for word
  in the 3ie evidence-gap-map files in `research/resources/3ie`) covers "selection of crops and cultivars with tolerance to abiotic stresses". The extractor
  followed the definition; judges and owner saw only the label. The owner reversed both audited calls. No vocabulary change: follow 3ie.
- **Judging conditions matter.** Judges and the audit showed label paths only. See the [review-tool requirements](2026-11-03-subproject-status.md) (definition shown,
  phrase match first).
- **Concentration** (28 trial papers, version 3): largest leaf term 6.2% of intervention labels (6.1% of facts) and 2.9% of outcome labels, so the 10% leaf limit
  holds. Group terms are higher: Climate adaption & mitigation strategies 24.6% of intervention labels (32.7% of facts), Agricultural adoption 8.7% of outcome
  labels (15.6% of facts). The trial set is biased toward climate papers; recheck on the whole corpus.
- **Residual over-specific leaves** (the v3 rule reduced but did not remove them): conditional and unconditional cash transfers chosen from one list sentence in
  a social-safety-nets review; Index insurance from one sentence in a review; Cash grants for a cross-sector grant programme whose 3ie definition says
  agricultural activities. About 3 of 134 labels. Crop insurance take-up was a judge error (the paper measures four take-up measures). The large paper
  `ffee575e1b75d109` (a systematic review of large-scale cash transfers) has one intervention fact, unconditional cash transfers, in both passes; the review may
  cover other transfer types, so this is probably the same pattern. Not yet looked at. Candidate fix if wanted: add a v3 example saying a list of types ("include X, Y, Z")
  does not count as the paper doing X. Not applied; the owner fixed the wording before the rollout.
- **Open vocabulary question:** 11 disputed labels sit under Resilience in the Financial Sector path (3ie's resilience framework: adopting adaptation measures is
  not resilience). Owner decision pending.

## Stocktake

What is solid: the method has a stated bar, a blind judging step, owner audits with cited pages, a restore point, and a concentration check; the main failure mode
(over-picked leaf) fell sharply; the owner's decisions are recorded.

What is weak, in order of weight:
1. The precision figure leans on judges whose agreement with each other is modest, and on owner audits of 24, 16 and 8 items. A single flip in the split group moves it
   about 0.03.
2. The 96 accepted labels were never judged with definitions; trial 1 and 2 judges used different conditions than the definition-aware pass.
3. Label-level, not paper-level; and facts are counted per pass, so a label that appears in both passes is one label here but two facts elsewhere.
4. Recall is unmeasured: nothing yet says what the extractor misses.
5. The 28 trial papers were chosen to include the old attractor term and climate papers, so concentration and precision on them do not predict the whole corpus.
6. Downstream files are stale for the 28 trial papers: their records carry `refine-v3` but `_tiers.json` and `_proposals.json` were restored to the pre-trial state
   before trial 2, and `tiers`, `verify` and `db build` have not been rerun. Proposals made by the trial 2 submit may be missing from `_proposals.json`.
7. Gemini's own report on the trial 2 submit was never received; the data is present and verified, but the completeness of its reading is unchecked.

## State of the corpus (2026-11-06)

183 record files (a and b passes), 15 papers excluded as off-topic. Counted over non-excluded papers:

| Stamp | Papers | Pass files (a / b) | Rollout needed |
|---|---|---|---|
| `extract-v4`, `refine-v3` | 8 | 8 / 8 | No (trial; rerun tiers, verify, db build) |
| `extract-v2`, `refine-v3` | 20 | 20 / 20 | No (trial; same) |
| `extract-v2`, `refine-v1` | 35 | 35 / 35 | Yes, 70 cards |
| `extract-v3` only (never refined) | 23 | 23 / 4 | Yes, 27 cards |

So the rollout is about 58 papers and 97 cards (cards 90k to 380k characters). The design's "110 already-refined record files" were the 35 `refine-v1` papers plus 20 of the trial papers
(the other 8 trial papers were the re-extracted ones). Corpus-wide today: Climate adaption & mitigation strategies is 21% of intervention facts; unclassified "proposed" values are 14% of intervention and
20% of outcome facts (a bucket of many different values, not one term).

Open proposals: 101 of 171, most from off-topic papers (AI in education, chatbots). Three need an owner call soon: P0142 (population "commuters", paper
`7f88458c5df631df`, grain note), P0143 (intervention "climate variation", paper `d688c2e9cec6e735`; it describes a natural-experiment design, not an intervention, so
reject is my recommendation), P0144 (outcome "Net Present Value", paper `27f1bdbf0b5541e3`; a stated CBA indicator, accept is my recommendation).

## Next steps

1. Rollout of the whole corpus under `refine-v3`: see [the handoff prompt](2026-11-06-rollout-handoff-prompt.md). Waiting on Gemini's limit.
2. After the rollout: `tiers`, `verify`, `db build`, concentration check, and a paper-level precision sample with definition-aware judging and two judge families.
3. Owner decisions: Resilience path, insurance and cash-grant wording, proposals P0142 to P0144.
4. Future work: clean whole-corpus test with definitions shown (see the [status doc](2026-11-03-subproject-status.md), step 8); review-tool changes in the same document.
5. Codex follow-ups, small, not blocking: `verify` should treat a verdict with a different `transcript_sha` as non-matching; `enrich_3ie` idempotent and
   tolerant of a missing `source`. Prompt: `ai-sandbox/research/.agent_work/term-selection-trials/prompts/codex_followups_prompt.md`.

## Rollout update (2026-11-08)

The live canonical corpus has 67 non-excluded papers. The earlier 58-paper rollout estimate counted 19 `c`/`d` records; the pipeline's `RecordStore.ids()`, refinement, tiers, and database use canonical `a`/`b` passes. The actual remaining refinement scope was 39 papers (78 cards): 4 never refined and 35 on `refine-v1`. All 186 record files, including proposal and tier ledgers, were byte-verified in `research/.agent_work/term-selection-trials/data/records_backup_pre_rollout/` before the first batch.

Batch 1 (`rollout-refine-v3-b1-20261108`) applied all 8 cards for the 4 never-refined papers; 0 bounced or skipped. These passes now contain 10 intervention and 23 outcome facts. `tiers` rebuilt 67 papers (A 445, B 101, C 149). `verify` staged 24 checker cards (4 batch-1 papers, 20 earlier trial papers) in `rollout-verify-after-b1-20261108`; none is filled yet, so verification-dependent tiers and the database are provisional. `db build` succeeded with 67 papers and 546 A/B facts. The 35 `refine-v1` papers remain batch 2.

After batch 1, the largest leaf shares in the mixed-version corpus were intervention Crop diversification 14/170 facts (8.2%) and 7/111 distinct paper-labels (6.3%), and outcome Resilience 16/251 facts (6.4%) and 10/190 labels (5.3%). Group shares: Climate adaption & mitigation strategies 36/170 intervention facts (21.2%) and 20/111 labels (18.0%); Agricultural adoption 15/251 outcome facts (6.0%) and 6/190 labels (3.2%). No leaf exceeds 10%. One new open proposal, P0172 (`FinTech coverage`, outcome, paper `bd62dcb1be021b9b`), awaits the owner.

A definition-aware spot check of eight batch labels found six supported and two questionable: the REDDI report (`3268b7062f1745f2`) provides planning and decision support for solar generation and storage, while the selected 3ie child definitions describe creating generation infrastructure and improving storage capacity. The narrowed listing was used on both passes. Owner decision pending on whether to redo both cards under unchanged `refine-v3` before batch 2. No vocabulary or refinement wording was changed.

## Rollout preparation (2026-11-10)

The owner requested a redo of both REDDI (`3268b7062f1745f2`) cards under unchanged `refine-v3`. Run `rollout-refine-v3-reddi-correction-20261110` has 2 pending cards (about 392k characters each). The earlier `rollout-verify-after-b1-20261108` checker run is still pending; its REDDI card was staged from the pre-correction facts and must not be submitted after correction. Rebuild verification for the changed paper after the correction submit, then rerun derived tiers and database output.

Batch 2 is staged but held: `rollout-refine-v3-b2-20261110` has 70 pending cards for the 35 `refine-v1` papers (94k to 330k characters). No batch-2 record has been rewritten. Subscription Gemini may start this run only after the REDDI correction and batch-1 checks are reviewed.

## REDDI correction result (2026-11-10)

Gemini submitted both REDDI correction cards: 2 applied, 0 bounced or skipped. Both passes now select the Energy infrastructure group as their single intervention fact and five outcome facts each. Codex checked all 12 stored quotes against their cited pages and the 3ie definitions; the earlier over-specific Energy generation and Energy storage child labels are gone. `tiers` rebuilt 67 papers (A 447, B 101, C 148), and `db build` succeeded with 548 A/B facts. The mixed-version corpus still has 35 older-refined papers. Concentration remains under the 10% leaf threshold: largest intervention leaf Crop diversification 14/168 facts (8.3%); largest outcome leaf Resilience 16/257 (6.2%). Group terms: Climate adaption & mitigation strategies 36/168 intervention facts (21.4%) and Agricultural adoption 15/257 outcome facts (5.8%). P0172 is the only new open proposal since backup.

The already-staged batch 2 has 70 pending cards and is ready for subscription Gemini. The earlier `rollout-verify-after-b1-20261108` run contains a stale REDDI checker card; do not submit that run. Generate fresh verification cards after batch 2, then submit checker results and rebuild tiers and the database for final numbers.

## Batch 2 rejected and restored (2026-11-10)

Gemini applied all 70 batch-2 cards with no validation bounces, but the quality gate failed. In the 35 papers, intervention facts fell from 60 to 20 and outcome facts from 87 to 26 across both passes; 24 papers had zero facts in both facets and both passes, and 54 of 70 pass records lost facts. A varied read-only check found clear false negatives: the Rwanda network-subsidy paper (`0bc75ee4d419ba1e`) reports a subsidy and phone-use outcomes, the risk-transfer paper (`0d683d8c58e1fd52`) models index insurance, remittance banking and cash transfers, and the cash-plus review (`b52cb3c54136c4df`) explicitly examines cash-plus programming and livelihoods. The first card's inherited agriculture-only intervention scope cannot express its mobile-network subsidy; the card rules allow a proposal when no listed term fits. The run's report treated many model, review and observational papers as having no facts merely because they did not empirically evaluate an intervention. This does not follow the card's instruction to list every distinct intervention and outcome the paper itself reports. These examples establish false negatives; they do not prove every old fact was correct.

The 70 applied record files and `_proposals.json` were saved in `research/.agent_work/term-selection-trials/data/records_batch2_rejected_snapshot_20261110/`, with an exact per-target SHA-256 restore plan. All 70 batch-2 records were restored byte-for-byte from `records_backup_pre_rollout/` using atomic replacement and post-run hash audit. Batch-only open proposal P0173 (`labor diversification`) was removed from the live ledger; P0172 (`FinTech coverage`) remains. Batch-1 and REDDI correction records were unchanged by the restore. `status` again reports 35 older-stamped papers, 0 never-refined, and 31 open proposals. The 70-card run manifest remains an applied historical artifact; do not resubmit it. No tiers, verification, or database build was run on the rejected batch. The existing derived output still reflects the accepted batch-1 and REDDI state (67 papers, 548 A/B facts). A new operating plan is needed before repeating batch 2: settle how out-of-scope subjects should be proposed and how reviews/models count under the existing fit test, then trial varied examples before another whole-batch subscription run. Do not change `refine-v3` wording or the 3ie vocabulary without an owner decision.

## Closeout (2026-11-11)

The refine-v4 recovery trial (`rollout-refine-v4-trial-20261110`, 8 papers, 16 cards) did **not pass**: the three known false negatives became nonempty, but the nonempty control and the extra adaptation review still omitted analysed practices and outcomes, and the adaptation review's extension and adoption labels cite a forecast rather than a programme or measured adoption. Details are in [the trial audit handoff](2026-11-11-refine-v4-trial-audit-handoff.md). The owner then judged that the deeper problem is not wording: the pipeline never decides whether a paper is the kind of evidence the 3ie intervention/outcome facets can describe (for example, a climate-projection model has no intervention outcomes, and the trial papers were a convenience sample). The [recovery handoff](2026-11-10-batch2-recovery-handoff.md) is therefore **superseded** by a redesign (applicability routing, a corpus-agnostic classification run, and an honestly sampled test set). Treat the trial as a proof of concept.

Live state after cleanup: the 16 trial records were restored byte-for-byte from `research/.agent_work/term-selection-trials/data/records_backup_pre_rollout/` (hash audit: 0 mismatches), and the 13 trial proposals P0173-P0185 were removed from the ledger (all belonged to the eight trial papers; P0172 and every earlier proposal are untouched; no existing entry changed). `status` reports 35 older-stamped papers, 0 never-refined, 31 open proposals. The batch-1 and REDDI-correction records are unchanged. No `tiers`, `verify` or `db build` was run on the trial records. The pre-restore state is kept in `.../data/records_v4_trial_snapshot_20261111/` (16 record files, the ledger, `restore_plan.json` with per-file SHA-256).

Not landed: the refine-v4 code (`refine_grain.py` prompt wording, `refinement_state.py` treating v3 as current, tests) stays on `codex/refine-v4` at `d3a348c8`. Do not submit these stale runs: `rollout-refine-v3-b2-20261110` (applied historical manifest and 70 cards), `rollout-verify-after-b1-20261108` (stale REDDI checker card), and `rollout-refine-v4-trial-20261110` (applied trial). The 27 remaining batch-2 papers stay on hold. Next step: a separate design brainstorm and handoff.
