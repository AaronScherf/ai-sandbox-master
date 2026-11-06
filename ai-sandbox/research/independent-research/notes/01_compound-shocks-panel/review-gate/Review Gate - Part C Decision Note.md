# Review Gate, Part C: decision note (2026-11-06)

Recorded by Claude from Aaron's replies on 2026-11-06. This records direction, not approval to build. Nothing below is implemented, and the research directions still need more data and literature exploration before anyone commits to them. Inputs: `Review Gate - Data Audit Review.md` (Part A), `Literature Gap Memo.md` (Part B, Gemini draft, citations unverified), the ACLED Terms note.

## Decisions

| # | Question (Gap Memo section 8) | Decision |
| --- | --- | --- |
| 1 | Research question scope | **Plan options B and C in parallel.** B is shift-share import shocks (Pink Sheet global prices times baseline district dependency). C is Baxnaano cash transfers against climate displacement under conflict. Plans only. Option A (the existing Somalia panel, no new data) was not chosen and stays available as a fallback. Neither B nor C is approved for implementation; each plan ends in a go/no-go. |
| 2 | Sudan panel | **Kept only as a portability check** that the same process replicates in a second country. No standalone chapter. Sudan's sparse prices do not affect the Somalia work. |
| 3 | ACLED redistribution | **Keep ACLED and add UCDP GED; use both.** UCDP is not a perfect substitute for ACLED, so the two are triangulated, not swapped. ACLED follows the reprokit route: replicators fetch it with their own account. UCDP GED is CC BY and can ship in the published panel (confirm the current licence). |

## Facts that qualify the decisions

- **ACLED credentials.** The ACLED API uses OAuth with the account email and password (see the ACLED Terms note, section 1.7). Keeping them in a private, gitignored environment file is fine. Committing or sharing them is the breach. Event-level API access needs an institutional (research-tier) account, with a rolling 12-month lag, so outside replicators need institutional access too.
- **UCDP.** The API needs a free access token requested by email to the maintainer ([API docs](https://ucdp.uu.se/apidocs/)). This is a manual step for Aaron and for each replicator.
- **WFP prices.** The Somalia price file runs to 2026-08 (earliest records 1995). Only about the last decade is needed, so the file's length is not a problem. Imported wheat flour starts in 2017, imported rice and red sorghum in 1995.
- **Baxnaano.** A search on 2026-11-06 found programme descriptions and a design paper but no microdata or district-level beneficiary data, and did not confirm project ID P171346. The Gap Memo's claim of district-level quarterly or monthly disbursements is unverified. Option C may stop at an access check.
- **Needs-assessment data.** Not Sudan-only. Somalia has REACH MSNA rounds (2022, 2023, 2025, planned 2026). The DTM API exists but has not been called by us, because it needs a subscription key.

## Next

Handoffs written the same day (in `docs/superpowers/plans/`): one for Option B, one for Option C, one for the new data sources. The Part C formal approval of a research question and econometric plan is still Aaron's, and comes after those plans report back.
