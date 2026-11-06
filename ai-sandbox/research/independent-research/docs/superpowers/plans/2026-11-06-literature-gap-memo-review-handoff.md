# Literature Gap Memo review: handoff

Written 2026-11-06. **Review only.** The memo is Gemini's Part B draft for the compound-shocks Review Gate. This session verifies it and checks whether work done since it was written changes its findings. Do not edit the memo or the panel; write a separate review note. Confirm scope with Aaron first.

## Read first (all on `main`)

Under `ai-sandbox/research/independent-research/`:

| File | Why |
| --- | --- |
| `notes/01_compound-shocks-panel/review-gate/Literature Gap Memo.md` | The thing under review. Key parts: section 4 (novelty), 5 (five identification options), 6 (eight data candidates), 7 (evidence table and search log), 8 (Part C questions). |
| `notes/01_compound-shocks-panel/review-gate/Review Gate - Gemini Brief for Literature Gap Memo.md` | What Gemini was asked to do, including its anti-fabrication rules. |
| `notes/01_compound-shocks-panel/review-gate/Review Gate - Part C Decision Note.md` | Decisions made 2026-11-06 and facts that already qualify the memo. |
| `docs/superpowers/plans/2026-11-06-new-data-sources-handoff.md` | Access findings for the memo's eight candidates. |
| `notes/03_rct-transportability/Follow-up - Data Availability and Transportability Critique.md` | Recent review of crisis cash-transfer RCTs. |

## Task 1: verify the memo as written

- **Citations.** The evidence table marks seven papers `[source-verified]` (Thalheimer et al. 2023, Zens and Thalheimer 2025, McGuirk and Burke 2020, Harari and La Ferrara 2018, Maystadt and Ecker 2014, Raleigh et al. 2015, Abushama et al. 2023), plus the ACLED EULA and the Baxnaano claim. Check each DOI resolves to the stated paper and that the memo's one-line claim matches it. Mark each confirmed, wrong, or unreachable.
- **No-duplicate claim.** Re-run the searches in section 7.2 and extend them (different keywords, Google Scholar, OpenAlex, SSRN, Semantic Scholar). The memo concludes no duplicate paper exists; test that, especially for Somalia displacement with rainfall and conflict, and for the Ukraine-era price shock.
- **Local corpus numbers.** The memo cites 67 papers, 8 on Somalia, 0 on Sudan. Re-run the corpus queries it lists and confirm.
- **Dataset claims in section 6.** Compare each against `2026-11-06-new-data-sources-handoff.md` and the provider pages. Known issues already found: Baxnaano district-level data and project ID P171346 are unconfirmed; UCDP now needs an emailed token; IPC, VIIRS and the DTM API need accounts or keys; the Pink Sheet is a monthly Excel workbook, not a CSV on World Bank Open Data; several "complete coverage 2021-2025" and licence statements are unchecked.

## Task 2: does recent work change the memo's findings?

Work done after the memo (2026-11-03) that may affect it:

1. **The Part A data audit and the ACLED terms note.** Do the audit's findings on missing prices and displacement, and the redistribution findings, change any option's feasibility or the ranking of the five identification options?
2. **The transportability brainstorm and its follow-up.** The follow-up found a substantial set of crisis cash-transfer RCTs (Niger, Philippines, Yemen, Ethiopia, DRC, Somalia, Sudan) that the memo's search may have missed. Does that change the novelty verdict for Option C (cash transfers and displacement under conflict) or the memo's statement that the panel "does not advance cash transfers"?
3. **The Part C decision note and the B and C plans.** The decisions (B and C in parallel as plans, Sudan as a portability check only, ACLED plus UCDP) alter what the memo should be asked to support. Does the memo cover UCDP-as-complement rather than UCDP-as-replacement, and a Sudan check rather than a Sudan chapter?
4. **The new-data-sources access findings.** Which of the memo's three shortlisted datasets (Pink Sheet, Baxnaano, VIIRS) survive once access is accounted for?

## Deliverable

One note, `notes/01_compound-shocks-panel/review-gate/Literature Gap Memo - Verification Review.md`, with: a citation table (confirmed, wrong, unreachable), the revised novelty verdict per option with the searches behind it, a list of memo claims that no longer hold, and a short statement of whether the Part C options (A, B, C) look different now. Mark anything unchecked "unverified". Aaron decides what to do with it.

## Ground rules

- Verify at the source; do not rely on memory or on the memo's own labels.
- No changes to the memo, the panel repository or other notes. One new file.
- Subscription agent, no paid API. If any step would cost more than $1, stop and ask Aaron.
- Follow the repo's worktree and landing procedure (`docs/WORKTREE_WORKFLOW.md`, `docs/WORKTREE_LANDING.md`).
