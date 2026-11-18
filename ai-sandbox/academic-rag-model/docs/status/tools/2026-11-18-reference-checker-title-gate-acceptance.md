# Reference checker wrong-title and citation-gate acceptance

Date: 2026-11-18. Branch: `codex/reference-checker-title-gate`, based on
`origin/main` at `866cab75`. This tracks the v12 and v13 handoffs; later steps
remain separate commits.

| Step | Evidence required | State |
| --- | --- | --- |
| v12 wrong-title decision and migration | Fixture decisions; two exact live defects relabeled | Done |
| v12 page button | Button payload and JavaScript syntax check | Done |
| v12 title search | Recorded Crossref/OpenAlex cases | Done |
| v12 tier and ledger routing | Shared rank, defects and review selection tests | Done |
| v12 acceptance | Fresh five-note checker and worktree ledger run | Done |
| v13 store resolution | Worktree-layout test for main ledger and cache | Done |
| v13 gate function | Per-note fixture counts and block/pass tests | Done |
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

## V12 five-note acceptance

I ran the checker on the five named worktree notes with a new, empty registry
cache. It checked 76 citation rows, made 187 fresh HTTP lookups (all returned
200), and reached the title search on exactly these three rows:

| Note and line | DOI | Search result |
| --- | --- | --- |
| RQ1 Knowledge Audit v4, 122 | `10.1257/pandp.20251021` (Brown et al.) | TITLE_WRONG; no cited-title match in Crossref or OpenAlex; registered title: *Valuing Information as a Philanthropic Funder* |
| RQ1 Knowledge Audit v4, 166 | `10.1016/j.wace.2018.03.006` (Lopez et al.) | TITLE_WRONG; no cited-title match; registered title: *Bridging forecast verification and humanitarian decisions: A valuation approach for setting up action-oriented early warnings* |
| RQ3 Transfer v5, 137 | `10.1093/restud/rdz021` (Rosenzweig and Udry) | TITLE_WRONG; no cited-title match; registered title: *External Validity in a Stochastic World: Evidence from Low-Income Countries* |

Brown's result differs from Aaron's earlier accepted same-work decision. The
checker now treats its cited title as an unfound title and records a defect;
this is reported for Claude and Aaron to reconcile, without changing the
threshold or the note. The title and DOI at each line above were checked
against the note text. A separate RQ3 DOI (`10.1002/cl2.1075`) remains REVIEW
for author overlap; it did not reach title search.

I copied the main review, dismissal, and defect files into an ignored
worktree-local store, then raised the five notes there. The resulting store
has three defects: the two existing human TITLE_WRONG defects and the new
Brown checker TITLE_WRONG defect. The review file is empty after refreshing
these five notes; all ten prior decisions remain in the copied dismissal
file (eight accepted, two declined). Main's ledger was not changed. This is
one live registry observation and a worktree-only ledger preview, not a
published review page or behavior observed over time. The v13 gate and full
suite have not run yet.

## V13 shared store and cache

The default review ledger and registry cache now resolve through Git's common
directory to the main checkout's project directory. An explicit store or cache
still permits isolated tests and worktree previews. A test created a real Git
repository and linked worktree and verified that the helper points back to
the main project directory; the module defaults were also checked. The
focused review suite passed: 21 passed, 0 skipped. This is layout and fixture
evidence; the gate and full suite were not run in this step.

## V13 gate function

`reference_review.gate` now raises each note once and reports per-note defect,
open-item, unresolved-lookup, and URL-only counts. It blocks on checker or
human defects, pending or deferred questions, and DOI lookups or title/guard
queries that could not finish. Accepted questions, CONFIRMED/AUTHOR_YEAR rows,
and URL-only rows do not block. Recorded-row tests cover all three defect
tiers, resolve and defer transitions, unavailable lookup paths, URL counting,
and a retained human defect. The focused review suite passed: 27 passed,
0 skipped. This is fixture evidence; landing wiring and the full suite remain
pending.
