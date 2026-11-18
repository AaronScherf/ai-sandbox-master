# OpenAlex guard acceptance run

Date: 2026-11-18. Branch: `codex/reference-checker-author-year`.
This follows the v11 handoff and supersedes the blocked v10 acceptance report.
Claude subsequently ruled that a work is another version only when its title
scores at least 0.8 against the registered title. The named threshold now
applies to both OpenAlex and Crossref sibling checks.

## Run and queue preview

Re-raised the five requested notes in a worktree-local copy of the main ledger:
`RQ1 v4`, `RQ2 v4`, `RQ3 v5`, `Summary v3`, and `Literature Gap Memo - v2`.
The run checked 65 DOI mentions, made 243 lookup calls (47 fresh successful
responses and 196 cache hits), and exited 0. All new OpenAlex answers were
fresh; earlier Crossref answers were available from the local cache. The
source notes were not edited. No defects were produced.
After a small internal change to keep the full sibling set until the final
five-item display limit, I restored the ledger snapshot and repeated the run
from cache. It again produced nine passes, seven reviews, and ten queue items.

| Queue status | Before | Preview after |
| --- | ---: | ---: |
| Pending | 0 | 7 |
| Deferred | 19 | 3 |
| Accepted review items | 2 | 0 |
| Total review items | 21 | 10 |

The two accepted decisions remain in `dismissals.json`. Seven deferred items
became pending because the candidate evidence changed. The main checkout's
ledger was not changed, as v11 assigns its re-raise to Claude after landing.

## Every previously PLAUSIBLE item

"Pass" is `AUTHOR_YEAR`; "review" is `PLAUSIBLE`. All 16 titleless rows had
their cited surnames and year checked before the guard.

| Citation | Result | Registry fact |
| --- | --- | --- |
| Bongers et al. (2021) | Review, incomplete | OpenAlex DOI exists, but its first authorship has no author ID; v11 requires fail closed. |
| Maystadt & Ecker (2014) | Pass | Complete first-author listing; the 2013 SSRN version fails the distinct-title test. |
| Zens & Thalheimer (2025) | Pass | Complete OpenAlex listing and no sibling from either source. |
| Marchiori, Maystadt, & Schumacher (2012) | Pass | Complete OpenAlex listing and no sibling from either source. |
| Hjort et al. (2021) | Pass | Complete OpenAlex listing and no shared-team sibling. |
| Pearl & Bareinboim (2014) | Pass | OpenAlex listing complete; Crossref's broad search remains incomplete but cannot veto a pass. |
| Thalheimer, Schwarz, & Pretis (2023) | Pass | Complete OpenAlex listing and no sibling from either source. |
| McGuirk & Burke (2020) | Pass | Complete OpenAlex listing and no sibling from either source. |
| Butler & Broockman (2011) | Pass | OpenAlex listing complete; Crossref's broad search remains incomplete but cannot veto a pass. |
| Egger et al. (2022) | Review, 2 siblings | OpenAlex found `10.1126/sciadv.abe0997` and `10.1101/2022.02.16.22270815`, both with the same first-author ID and a co-author ID. |
| Allcott (2015) | Review, 23 siblings | Single-author first-ID listing found 23 distinct works; first five stored. |
| Vivalt & Coville (2023) | Review, 2 siblings | OpenAlex found `10.1016/j.jdeveco.2024.103425`; Crossref also found `10.1596/1813-9450-10994`. |
| Harari & La Ferrara (2018) | Pass | Complete OpenAlex listing and no sibling from either source. |
| Groh et al. (2016) | Review, 6 siblings | OpenAlex found six qualifying distinct works, including `10.1186/s40175-016-0055-9` and `10.1186/s40172-015-0022-8`; Crossref added none. The first five are stored on the row. |
| Raleigh, Choi, & Kniveton (2015) | Review, 1 sibling | OpenAlex found `10.1080/03050629.2017.1235271`, issued online in 2016. |
| Brok et al. (2008) | Review, 3 siblings | OpenAlex found the third sibling missed in the v10 search, `10.1002/14651858.cd005527.pub2`. |

This gives nine passes and seven reviews. Claude's v11 probe expected Groh,
Raleigh, Brok, Allcott, and Vivalt/Coville in review, and Pearl and Butler to
pass; all do. Two additional reviews are Bongers (missing OpenAlex first
author ID) and Egger (two newly found same-team works). With Claude's 0.8
version threshold, Groh's title scores of 0.63 and 0.50 count as distinct
papers, while the Maystadt SSRN version scores 0.89 and is still ignored.
The five-note preview was rerun from the unchanged main-ledger snapshot after
this ruling. Only Groh's row changed: its sibling count rose from four to six,
and `10.1186/s40175-016-0055-9` now appears in the first five displayed.
The other 15 titleless rows, queue counts, and defects stayed the same.

## Verification and limits

The focused fixture suite (`test_reference_checker_guard.py`,
`test_reference_checker_author_year.py`, `test_reference_review.py`, and
`test_reference_checker.py`) passed with 108 passed and 1 skipped before rebase. The new
fixtures cover the Groh/Raleigh false passes, the Maystadt version, full
OpenAlex paging, fail-closed cases, both sibling sources, and request pacing.
After a clean rebase onto `origin/main`, the full chunked suite passed all
eight chunks in 1,274.3 seconds (`agent`, `audio_generator`, `core`,
`discovery`, `pipelines`, `resume_manager`, `tools`, and root tests). A later
`origin/main` commit changed only an academic-hub lab notebook; the branch was
rebased again to include it, without changing this package.
This is a successful live run against current registry data. It does not
establish future registry stability or correctness of owner decisions. The
review page sync, main-ledger re-raise, and landing were not run.
