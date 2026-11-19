# Reference review incomplete-lookup acceptance

Started: 2026-11-18; final acceptance: 2026-11-19. Branch:
`codex/reference-review-incomplete-state`, cut from `origin/main` at
`b599a5dc` and rebased onto `f75c7360`. Scope: v14's ledger-state fix only.

| Requirement | Acceptance evidence | State |
| --- | --- | --- |
| Incomplete DOI lookups use the gate's shared predicate | Recorded rows for `UNRESOLVED` and `unavailable`; metadata gap remains complete | Done |
| Preserve a prior item's status, candidates and `updated` | Declined human-defect and accepted-item fixtures | Done |
| Preserve a matching prior checker or human defect without opening a new item | Matching and changed-mention defect fixtures | Done |
| Keep new failures pending; reopen accepted items only for material complete changes | New-failure, citation, tier and registry fixtures; line and sibling fixtures | Done |
| Show kept-state count and retry advice in `raise` only when positive | CLI zero and positive fixtures | Done |
| Five-note copied-ledger run, forced failure then normal | Per-run open items, defects, fresh unresolved count | Done |
| Focused suites and formal landing check | Pass/skip counts, change ID | Pending |

The main ledger, cache, notes, review page, routing document, and Gemini
instructions are outside this branch's write scope. Tests use recorded answers.
The acceptance run writes only a worktree-local copy of the main ledger and
uses a worktree-local cache. No user decisions are changed.

## Starting live state

Read-only inspection of the main ledger found zero review items and three
`TITLE_WRONG` defects: Lopez (`10.1016/j.wace.2018.03.006`), Brown
(`10.1257/pandp.20251021`), and Rosenzweig/Udry
(`10.1093/restud/rdz021`). The RQ1 and RQ3 note lines still cite those
DOIs with the titles recorded in the defects. These are live file
observations, not fixture evidence or the acceptance run.

## Implementation and fixture evidence

`raise_items` and `gate` now share one incomplete-lookup predicate: tier
`UNRESOLVED`, or `unavailable` in the row reason. For an incomplete DOI row,
the ledger retains a prior item with its status, candidates, and `updated`
unchanged. When there is no prior item, it retains a prior checker or human
defect only if its citation mention texts still match. A new incomplete finding
continues to open a pending item. On a complete lookup, an accepted item
reopens only when its tier, citation text, or registered title, authors, year
or venue changes. A moved line or changed sibling list leaves it accepted.
The `raise` CLI reports a machine-readable kept-state count and prints a
retry-advice line to stderr only when that count is positive.

The review suite passed **42 tests, 0 skipped**. The four checker suites
passed **98 tests, 1 skipped**. These use recorded rows and registry answers,
so they verify state transitions and checker compatibility, not live registry
behavior. The formal landing check has not run.

## First copied-ledger acceptance observation

I copied the main ledger and registry cache into ignored worktree-local
directories, then raised all five named notes with six cited-title queries
forced to fail. The fresh gate reported three unresolved DOI rows: two in RQ1
and one in RQ3. All three existing TITLE_WRONG defects remained, but the
open-item count rose from zero to two. On a normal second run, open items
returned to zero and the ledger was semantically identical to the starting
copy, with the same three defects.

The two transient pending items corresponded to Lopez and Rosenzweig/Udry.
Their prior defects have `source: human`, and the main ledger had no prior
review item for either note/DOI pair. The numbered v14 rule named a prior
checker defect in that no-item case, while its acceptance expectation said
both runs should leave the ledger unchanged. Claude ruled that a matching
human defect also counts as prior state. The implementation now preserves
either defect source when note, DOI, and mention text match. No main ledger,
note, or shared cache was written by this acceptance run.

A later read found 48 pending items in the main ledger from other note work.
The exact RQ1 Lopez and RQ3 Rosenzweig/Udry note/DOI pairs still had no prior
review item; their human defects remained. Repeating the copied-ledger run
raised that snapshot's open count from 48 to 50 on forced failure and back
to 48 on normal lookup. This is a changing external baseline, not a change
caused by this worktree.

## Acceptance after the human-defect ruling

I copied the then-current main ledger (54 open items, 21 defects) and cache
into ignored worktree-local paths and raised the five named notes twice.
The first pass forced six cited-title query failures; the second used the
copied cache and normal online lookup. Both resulting ledgers were
semantically identical to the starting copy: **54 open items and 21 defects**
(11 TITLE_WRONG, 6 WRONG_WORK, 4 NOT_FOUND). No item or defect was added or
removed in either pass.

| Note | Forced pass: defects / open / unresolved | Normal pass: defects / open / unresolved |
| --- | --- | --- |
| RQ1 Knowledge Audit v4 | 2 / 0 / 2 | 2 / 0 / 0 |
| RQ2 Decision Space v4 | 0 / 0 / 0 | 0 / 0 / 0 |
| RQ3 Transfer v5 | 1 / 0 / 1 | 1 / 0 / 0 |
| Summary v3 | 0 / 0 / 0 | 0 / 0 / 0 |
| Literature Gap Memo v2 | 0 / 0 / 0 | 0 / 0 / 0 |

The forced pass shows that the fresh gate still fails closed on three
unresolved rows while the prior ledger state stays stable. This is a live
read-only registry/cached-answer run against a worktree ledger copy, not a
write to the shared ledger or behavior observed over time. The checker and
gate algorithms outside `reference_review.py`, the notes, and the review
page were not changed.

## Accepted-item comparison refinement

A later review narrowed the complete-lookup reopening rule for accepted
items to tier, citation text and four registry fields (title, authors, year,
venue). The focused fixtures verify that moving a citation to another line
and changing only its sibling list both retain `accepted`, while changes to
each registry field or the tier reopen it. The retry-advice line is absent
when the kept-state count is zero. After this refinement, the copied-ledger
acceptance again preserved the 54-open-item, 21-defect snapshot on both
passes; the forced pass reported three unresolved rows and the normal pass
reported zero. This is a worktree-local run, not a main-ledger write.
