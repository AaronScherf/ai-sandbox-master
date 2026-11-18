# AUTHOR_YEAR acceptance run: guard completeness finding

Date: 2026-11-17. Branch: `codex/reference-checker-author-year`.
This is the fifth step of the reference checker v10 handoff. It records a live
registry run and a finding requiring Claude's design decision before landing.

## Run and state

The five requested notes in the worktree were byte-identical to their main
checkout counterparts (SHA-256 comparison). I copied the main checkout's
ignored review ledger (21 items: 19 deferred, 2 accepted) and registry cache
into ignored worktree-local report storage, then re-raised only `RQ1 v4`,
`RQ2 v4`, `RQ3 v5`, `Summary v3`, and `Literature Gap Memo - v2` with the new
code. The run checked 65 DOI mentions (59 note/DOI pairs), made 176 registry
lookups (26 fresh successful responses and 150 cache hits), and exited 0.
The two accepted decisions remained in `dismissals.json`; their review items
dropped as expected. No defects were produced.

| Preview queue | Before | After |
| --- | ---: | ---: |
| Pending | 0 | 5 |
| Deferred | 19 | 3 |
| Accepted review items | 2 | 0 |
| Total review items | 21 | 8 |

The five pending items were previously deferred; candidate evidence changed
for each, so the existing ledger upsert reset its status. The remaining queue
is one RQ1 item, one RQ3 item, and six Summary items. RQ2 and Memo have none.

## Each previously PLAUSIBLE item

Results below refer to the item's titleless citation in the five notes. The
DOI distinguishes repeated author names and note mentions. "Pass" means
`AUTHOR_YEAR`, and "review" means `PLAUSIBLE`.

| Citation | DOI | Result | Live Crossref finding |
| --- | --- | --- | --- |
| Bongers et al. (2021) | `10.1214/21-aos2064` | Pass | No sibling in completed guard. |
| Maystadt & Ecker (2014) | `10.1093/ajae/aau010` | Pass | No sibling in completed guard. |
| Zens & Thalheimer (2025) | `10.1214/24-aoas1959` | Pass | No sibling in completed guard. |
| Marchiori, Maystadt, & Schumacher (2012) | `10.1016/j.jeem.2012.02.001` | Pass | No sibling in completed guard. |
| Hjort et al. (2021) | `10.1257/aer.20190830` | Pass | No shared-team sibling in completed guard. |
| Pearl & Bareinboim (2014) | `10.1214/14-sts486` | Review | 970 results; first-author matches remain in the tails of all three 100-row pages, so the guard reaches its limit. |
| Thalheimer, Schwarz, & Pretis (2023) | `10.1016/j.gloenvcha.2023.102641` | Pass | No sibling in completed guard. |
| McGuirk & Burke (2020) | `10.1086/709993` | Pass | No sibling in completed guard. |
| Egger et al. (2022) | `10.3982/ecta17945` | Pass | No sibling in completed guard. |
| Butler & Broockman (2011) | `10.1111/j.1540-5907.2011.00515.x` | Review | 6,124 results; first-author matches remain in all three page tails, so the guard reaches its limit. |
| Harari & La Ferrara (2018) | `10.1162/rest_a_00730` | Pass | 3,099 results; six Harari-first works in page one, none in its final ten; guard stops. |
| Allcott (2015) | `10.1093/qje/qjv015` | Review | 19 distinct works found; first five siblings stored. |
| Vivalt & Coville (2023) | `10.1016/j.jdeveco.2023.103121` | Review | One sibling found, `10.1596/1813-9450-10994`. |
| Groh et al. (2016) | `10.1162/rest_a_00584` | **Pass: unsafe** | 11,129 results; two pages read, no shared-team work found; second page tail has no Groh-first record, so guard stops. |
| Raleigh, Choi, & Kniveton (2015) | `10.1016/j.gloenvcha.2015.03.005` | **Pass: unsafe** | 68,038 results; first page has no Raleigh-first record, so guard stops. |
| Brok et al. (2008) | `10.1093/ije/dyn188` | Review | Two siblings found: `10.1136/adc.2007.118000` and `10.1016/j.jclinepi.2007.10.007`. |

Claude's hand probe predicted nine passes, five reviews with siblings, and two
paging-dependent results. This run produced 11 passes, three reviews with
siblings, and two incomplete guards. The main differences are Groh and Raleigh
passing despite known same-team works, Pearl remaining incomplete, and Harari
passing after one page. Brok remains in review, but the query found two of the
probe's three siblings. The all-cited-surnames rule caused no additional
difference among these 16 rows.

## Independent Crossref spot check and blocker

I checked the two unexpected passes against separate Crossref bibliographic
searches and DOI records. Crossref registers
[`10.1186/s40175-016-0055-9`](https://api.crossref.org/works/10.1186%2Fs40175-016-0055-9)
as a different 2016 Groh/Krishnan/McKenzie/Vishwanath employment paper. It
also registers
[`10.1186/s40172-015-0022-8`](https://api.crossref.org/works/10.1186%2Fs40172-015-0022-8)
as a different 2015 Groh/McKenzie/Vishwanath paper. Crossref registers
[`10.1080/03050629.2017.1235271`](https://api.crossref.org/works/10.1080%2F03050629.2017.1235271)
as a different Raleigh/Choi paper, issued online in 2016. Each meets the
same-team and date-window criteria, yet none appeared in the guard's scanned
pages. The broad author query's large result set and the page-tail stopping
rule can therefore produce a false automatic pass. This is an observed live
misclassification, not an inference from the hand probe alone.

The main checkout's persistent ledger was **not updated**: the preview would
silently remove these two deferred questions from Aaron's review queue. Do not
land or re-raise the main queue until Claude resolves the completeness rule.
The main ledger still has 21 items (19 deferred, 2 accepted) and zero defects.
The notes and their owner decisions were not edited.

## Verification limits

The focused fixture suite (`test_reference_review.py`,
`test_reference_checker_author_year.py`, `test_reference_checker_guard.py`,
`test_reference_checker.py`) passed: 109 passed, 1 skipped. This acceptance
run did not exercise the review page sync, a full test suite, future registry
changes, or an owner review. The preview JSON and response cache are ignored,
worktree-local artifacts; the report above is the committed evidence. No code
was tuned to the acceptance results.
