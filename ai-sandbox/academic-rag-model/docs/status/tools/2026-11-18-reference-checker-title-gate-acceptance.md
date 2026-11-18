# Reference checker wrong-title and citation-gate acceptance

Date: 2026-11-18. Branch: `codex/reference-checker-title-gate`, based on
`origin/main` at `866cab75`. This tracks the v12 and v13 handoffs. Only v12's
first step is implemented so far; later steps remain separate commits.

| Step | Evidence required | State |
| --- | --- | --- |
| v12 wrong-title decision and migration | Fixture decisions; two exact live defects relabeled | Done |
| v12 page button | Button payload and JavaScript syntax check | Done |
| v12 title search | Recorded Crossref/OpenAlex cases | Done |
| v12 tier and ledger routing | Shared rank, defects and review selection tests | Done |
| v12 acceptance | Fresh five-note checker and worktree ledger run | Pending |
| v13 store resolution | Worktree-layout test for main ledger and cache | Pending |
| v13 gate function | Per-note fixture counts and block/pass tests | Pending |
| v13 landing wiring | Check and land tests, full suite | Pending |
| v13 routing instruction | Documentation review | Pending |
| v13 acceptance | Five-note gate dry run, code-only bypass test | Pending |

## First-step evidence

`reject(item_id, "wrong_title")` now records a note-local human `TITLE_WRONG`
defect with the registered title and a reason saying the DOI is correct.
`apply_decisions` accepts the matching decline action; a repeat is reported
as already applied. `wrong_work` still means an incorrect DOI. The migration
function requires a declined review item, an existing human `WRONG_WORK`
defect, and an explanation that the DOI and registry record are correct and
names the registered title. It replaces the defect file atomically.

The focused fixture file `tests/tools/test_reference_review.py` passed:
19 passed, 0 skipped. This is fixture evidence for decision routing and
migration idempotence; it is not a checker or gate run.

I backed up the main checkout's ignored `review.json` and `defects.json` in
the worktree's ignored `.reference_checker_reports/wrong_title_migration_backup/`
and checked their hashes before migrating. `relabel_defect` returned success
for only these two exact note/DOI pairs:

| Note | DOI | Result | Registered title |
| --- | --- | --- | --- |
| `RQ3 Transfer - v5.md` | `10.1093/restud/rdz021` | `TITLE_WRONG` | External Validity in a Stochastic World: Evidence from Low-Income Countries |
| `RQ1 Knowledge Audit - v4.md` | `10.1016/j.wace.2018.03.006` | `TITLE_WRONG` | Bridging forecast verification and humanitarian decisions: A valuation approach for setting up action-oriented early warnings |

The post-run audit found exactly two defects with those titles. A repeat call
changed no bytes (`defects.json` SHA-256
`7e6612a0c28685914f89b574938dac754f94e3ad5863eb1bf888f5084a1dd0e4`).
The review ledger still contains 10 items. No owner decision was added, and
no note was edited. The review page, checker title search, gate, five-note
acceptance, and full suite were not run in this step.

## Page-button step

The review page now offers a fifth action, **Title wrong, DOI right**. Its
existing decision handler writes `{action: "decline", chosen: "wrong_title"}`
for the selected item; the active-button style and footer explain that the
DOI stays and only this note's title needs correction. The extracted script
passed `node --check`. The focused review-ledger suite passed again:
19 passed, 0 skipped. This verifies JavaScript syntax and decision acceptance;
it is not a published-page or interactive browser run. Claude will publish
the page after landing. The title search, gate, acceptance runs and full suite
remain pending.

## Title-search step

Eligible SAME_WORK rows now query Crossref and OpenAlex for a cited title
scoring below 0.5 against the DOI's registered title. The cited title is
capped at 200 characters; Crossref also receives cited surnames. Both calls
use `RegistryClient` caching, retry and pacing. A title scoring at least
0.92 in either source is attached as `cited_title_found` with DOI, title,
year and source. Two complete searches with no hit add `TITLE_NOT_FOUND` and
the registered title. A failed or malformed search leaves the row in REVIEW
with "title search unavailable". TITLE_WRONG tiering and ledger routing
remain for the next step.

Recorded-answer tests cover the Rosenzweig/Udry and Lopez empty results, an
alternate-work Crossref hit, an OpenAlex-only hit, lookup failure in either source, and
skipping high-scoring and titleless rows. The focused checker and ledger
suite passed: 109 passed, 1 skipped. This is fixture evidence; no live
registry lookup or five-note acceptance was run.

Claude ruled that the v12 NBER test was incorrect: its title scores about
0.69 against the REStud registered title, so it must not trigger this search.
The `< 0.5` trigger remains. Its replacement fixture cites Rosenzweig and
Udry's 2014 AER paper, "Rainfall Forecasts, Weather, and Wages over the
Agricultural Production Cycle" (`10.1257/aer.104.5.278`), against the REStud
DOI. The title scores about 0.26 and the checker records the AER work as
`cited_title_found` while keeping the row in REVIEW.

## Tier and ledger-routing step

`TITLE_WRONG` now ranks above REVIEW and below NOT_FOUND in the shared checker
rank. A complete two-source title search with no match sets the checker tier
to TITLE_WRONG with `TITLE_NOT_FOUND`, the registered title, and the specified
reason. The ledger routes it to a checker defect, not the review queue. A
matching alternate title stays REVIEW; the ledger copies `cited_title_found`
to its candidate and the review page displays that result. A matching human
TITLE_WRONG defect is retained without a duplicate checker defect.

The focused checker and ledger suite passed: 110 passed, 1 skipped. The page
script passed `node --check`. This is recorded-answer and syntax evidence;
the fresh five-note acceptance run, gate, and full suite remain pending.
