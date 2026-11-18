# Reference checker wrong-title and citation-gate acceptance

Date: 2026-11-18. Branch: `codex/reference-checker-title-gate`, based on
`origin/main` at `866cab75`. This tracks the v12 and v13 handoffs. Only v12's
first step is implemented so far; later steps remain separate commits.

| Step | Evidence required | State |
| --- | --- | --- |
| v12 wrong-title decision and migration | Fixture decisions; two exact live defects relabeled | Done |
| v12 page button | Button payload and JavaScript syntax check | Done |
| v12 title search | Recorded Crossref/OpenAlex cases | Pending |
| v12 tier and ledger routing | Shared rank, defects and review selection tests | Pending |
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
