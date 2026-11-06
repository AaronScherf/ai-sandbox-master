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
