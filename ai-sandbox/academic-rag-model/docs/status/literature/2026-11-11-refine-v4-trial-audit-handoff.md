# Refine-v4 trial audit: Claude design handoff (2026-11-11)

## Status and boundary

The owner requested a Claude design handoff after the eight-paper trial audit. **The remaining 27 batch-2 papers are on hold.** Leave the 16 applied trial records in place pending an owner decision; do not silently repair or resubmit them. Do not stage more papers or run `tiers`, `verify`, or `db build`. Do not submit the historical `rollout-refine-v3-b2-20261110` or `rollout-verify-after-b1-20261108` runs. No proposal was accepted, rejected, or resolved in this audit.

The approved recovery design and pass criteria are in [2026-11-10-batch2-recovery-handoff.md](2026-11-10-batch2-recovery-handoff.md). Refine-v4 implementation is committed on `codex/refine-v4` at `d3a348c8`; its literature tests previously passed (450 tests, 112 subtests). This handoff records **live trial observations**, not evidence that the full rollout works. The code has not been landed.

The live run is `C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\.agent_work\rollout-refine-v4-trial-20261110\`. Its manifest reports 16 applied, 0 bounced, 0 skipped, 0 pending. Each of the eight papers has both pass-a and pass-b records stamped `refine-v4` under `research/.index/study_records/`. The operating prompt required subscription Gemini and no paid API; the completion report did not supply billing evidence. The audit made no pipeline writes.

The 49 stored intervention/outcome quotes all pass the repository's **normalized** cited-page matcher against the offered card passages. A stricter whitespace-collapsed literal comparison matches 38/49; the other 11 rely on the matcher's Unicode, punctuation, or hyphen normalization. Neither check establishes that a quote supports the chosen term or that all facts were listed. The pre-rollout backup has 14 intervention and 23 outcome facts across these 16 passes; refine-v4 has 22 and 27. This aggregate smoke check passes, while individual papers still have omissions.

## Paper-level audit

Counts below are `interventions / outcomes`. Citations are offered page numbers from the run cards. The findings are based on the paper text and the official 3ie definitions, not on whether a `refine-v1` record had a label. This is a targeted content audit, not a complete precision estimate.

| Paper | Pass a | Pass b | Evidence and finding |
|---|---:|---:|---|
| `0bc75ee4d419ba1e` Rwanda subsidy | 2 / 3 | 2 / 2 | P1 says Rwanda subsidized handsets; the subsidy is now captured as proposed in both passes. P7 supports vouchers; P1 supports phone usage and operator revenue. Passes created near-duplicate subsidy and voucher proposals, but the paper has an implemented subsidy and a simulated voucher alternative. |
| `0d683d8c58e1fd52` risk-transfer model | 3 / 3 | 3 / 3 | P14 says “we assess” index insurance, a remittance bank, and cash transfers; all three are listed. The same page says the model assesses “the number of households below an immobility threshold”; **both passes omit that distinct outcome**. |
| `b52cb3c54136c4df` cash-plus review | 2 / 2 | 1 / 2 | P21 says the review identified 25 programme evaluations and synthesized income, social inclusion, and economic inclusion; P22 reports effects on the latter two. Both passes list income and food security but **omit social and economic inclusion**. Pass b also collapses graduation programmes and transfers into one proposed “cash-plus programming” fact. |
| `cbed05af4d4cf1c4` Zambia nonempty control | 3 / 1 | 2 / 1 | P1 says the paper examines rotation, reduced tillage, legume intercropping, improved seeds, and inorganic fertiliser, and that legume intercropping significantly increases yields. Both passes list rotation/tillage and maize yield but **omit legume intercropping and inorganic fertiliser**. Pass b also omits improved seeds. These are analyzed practices, not a background list. |
| `8874a838b58b7a35` conceptual control | 0 / 0 | 0 / 0 | P1–P2 describe a conceptual risk-management framework and bibliometric synthesis. Empty intervention/outcome facets are defensible under the approved rule; no clear named policy or measured outcome was identified in this check. |
| `1af1d5a9827dfd07` Somalia observational study | 0 / 1 | 0 / 1 | P2 reports measured PTSS severity, captured by both passes. P7 also reports that 51.3% perceived stress-related worsening of anxiety and depression. **Possible additional measured mental-health outcome** for Claude to assess; interventions remain empty. |
| `c65835b631399b98` Somalia simulation | 0 / 2 | 0 / 2 | P8 presents model projections for rainfall and temperature; P11–P13 report the results. Both passes capture these as proposed outcomes. The pass-a/pass-b proposals appear conceptually duplicative. No clear omitted intervention was identified. |
| `7a890946b00f1b17` adaptation review | 2 / 2 | 2 / 2 | P2 says the review examines adaptation strategies; P6 discusses changing planting dates and P5 discusses irrigation. **Neither pass lists these review subjects.** Pass a assigns `intervention.agricultural_extension` from P7's statement that services are likely to support adoption, but the 3ie term requires a programme expanding access to extension. It assigns `outcome.agricultural_adoption` from the same forecast, but that term requires the extent to which farmers adopt practices. The cited sentence establishes neither child-level claim. |

The three known false-negative papers are now nonempty, and the conceptual control is plausible. The approved trial gate still has material problems: the nonempty control lost a strongly supported practice, the extra adaptation review has clear omissions, and two of its children lack definition-level support. The model and cash-plus review have additional omissions. **Codex recommends treating the trial as not passed; the owner makes the pass/fail decision.**

## Proposal state

Thirteen new proposals, `P0173`–`P0185`, are open. No proposal decision is implied by a stored fact.

| Paper | New proposals | Review issue |
|---|---|---|
| Rwanda `0bc75ee4d419ba1e` | P0173–P0175, P0178–P0180 | Subsidy and voucher concepts recur across passes under different names; consumer surplus and welfare differ in scope. Preserve the distinction between implemented subsidy and modeled voucher alternative. |
| Somalia simulation `c65835b631399b98` | P0176–P0177, P0184–P0185 | Rainfall/depressed rainfall and temperature/temperatures appear to be pass-level duplicates. |
| Cash-plus review `b52cb3c54136c4df` | P0181 | Broad cash-plus term may hide reviewed programme components. |
| Adaptation review `7a890946b00f1b17` | P0182–P0183 | Broad adaptive-practices and climate-smart-agriculture proposals need definition-aware review. |

The risk-transfer model's remittance bank matched pre-existing P0002; it is not a new proposal. P0172 and all older open proposals remain outside this audit.

## Decisions requested from Claude for owner review

1. Diagnose the remaining **listing-completeness** failures under the exact refine-v4 instructions: omission of an analyzed practice in an empirical paper, an outcome in a model, and subjects/outcomes of reviews. Recommend the smallest change that distinguishes a paper's own analysis or review synthesis from background, motivation, and cited examples. Preserve the owner's rule that lists of types alone do not prove the paper analyzes each type.
2. Diagnose **term-fit** failures separately from listing omissions. The adaptation review's extension/adoption labels cite a forecast, while their 3ie definitions require an access-expanding programme and measured adoption. Specify how a card or validation step should prevent that child assignment without suppressing a real reported subject. The approved constraints on shared `CHOOSING_RULE`, `FIT_TEST_EXAMPLES`, and the official vocabulary remain in force unless the owner explicitly changes them.
3. Advise whether the observed proposal volume and pass-level near-duplicates warrant any design adjustment, while keeping the approved scoped listing and `proposed: true` behavior unless the owner decides otherwise. Do not resolve proposals as part of the design review.
4. Propose a small, reviewable recovery check and versioning plan for any revised prompt. The owner must decide whether the 16 applied trial records stay, are corrected selectively, or are redone. Any further card run requires owner authorization; the 27 remaining papers stay on hold.

Do not treat the structural validator, the aggregate count increase, or this targeted audit as a whole-corpus precision result. The original design's later verification, tier, database, and concentration steps still follow a successful rollout and owner decision.
