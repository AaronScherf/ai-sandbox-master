# Reference checker review, round 5: tiers and linking pass (v7)

From: Claude, 2026-11-15. Reviewed: `codex/reference-checker-tiers-v6` at `f38628cc` (worktree `.worktrees/codex/reference-checker-tiers-v6`), base `0ba4ae0f`. Read-only; no Codex files changed.
Does not replace v6; adds one small fix and the landing steps (section 4).

## 1. Verdict

Land after one small fix (year tolerance, section 3.1) and a base update. No other blocker. Evidence labels: **run**, **read**, **cached** (Codex's recorded registry answers, offline), **reported** (Codex's claim only).

## 2. What was checked

| Item | Result | Evidence |
|---|---|---|
| Branch state | clean; 9 commits on `0ba4ae0f` (tiers, reference-list parsing, inline parsing, linking, tests, fixtures, hardening) | run |
| Offline tests | 67 passed, 1 skipped (opt-in online smoke test) | run |
| Code diff for `tools/reference_checker.py` (367 lines) | read in full | read |
| v2 notes RQ1, RQ2, RQ3, before and after | row counts and identity counts identical (15, 13, 23 rows); no identifiers added or dropped | run, cached |
| Tier split over the 31 SAME_WORK rows | 27 CONFIRMED, 4 REVIEW, 0 PLAUSIBLE; every row's `evidence` is `title_in_citation` | run, cached |
| Memo v2 | 13 mentions, 7 DOIs, all PLAUSIBLE, none CONFIRMED | run, cached |
| Step 7 (rows leaving PLAUSIBLE) | Codex gave no result; Claude's run above shows none leave, because no real row lacks a title | run, cached |
| Full chunked suite after merging current `main`; online smoke test; fresh registry runs | not run | none |

## 3. Findings

1. **Year tolerance is missing from CONFIRMED (fix before landing).** The owner asked whether title alone can confirm. In the code it cannot: a tier is assigned only after identity is SAME_WORK, which needs the first author (or two surnames) to match; a different author with the same title is `WRONG_WORK`. Only when authors are unavailable on one side (`UNCHECKED`) or one surname overlaps (`AMBIGUOUS`) can an exact title (>= 0.92) lift the identity. Within SAME_WORK, however, a title >= 0.92 gives CONFIRMED whatever the year. With a generic title and the same first author, a paper from a different year (a series, a report update) would pass. The addendum's existing one-year tolerance (Fenwick, Gechter, Tennant) is the right bound. Rule to implement: CONFIRMED needs title >= 0.92 **and** the cited year within one year of any registered year, or title >= 0.5 and the cited year equal to a registered year. Otherwise REVIEW. Claude's check of the 31 real rows: the only CONFIRMED row with `YEAR_DIFFERS` is Dahabreh et al. (cited 2020; registry 2018 online, 2019 print), which stays CONFIRMED under this rule, so the 27/4 split should not change. Tests needed: same title and first author, year off by five (REVIEW); same title, different authors (WRONG_WORK, never CONFIRMED); Dahabreh stays CONFIRMED.
2. **The linking pass has not been exercised on a real note (not blocking).** All 51 real rows already have titles. Linking is covered by synthetic tests only (unique link, DOI link, two same-author same-year entries, mismatched title goes to REVIEW). Keep it, but treat it as unproven until a real note with author-year citations and a titled reference list is run. The `evidence` field shows which path each row took.
3. **`extract()` now also reads table rows and link lines outside reference sections (not blocking).** On the four files tested, nothing changed. Ask Codex to state why it was needed and add a test that pins it; run it over a few other research notes once, to see whether extra rows appear.
4. **`parse_inline_citations` bare form reads "March 2020" as an author and year (not blocking).** Harmless today, since linking needs a matching list entry; fix before reusing the parser elsewhere (for example coverage counting).
5. **Tier rank:** `UNRESOLVED` ranks below `REVIEW`. Fine, because only CONFIRMED may pass, but record it in the docstring so nobody reads rank as a pass order.

## 4. Next steps, in order

1. Codex fixes 3.1 with the three tests (one commit). Also answer 3.3 and add its test, and fix or document 3.4.
2. Codex brings the branch up to date with current `origin/main` (merge if the branch was ever pushed, rebase only if it was not), then runs the full chunked suite and reports the result.
3. Integrator lands the branch.
4. Then, in this order: merge `claude/memo-doi-corrections` (Memo v2) to `main`; find a real note for 3.2; then build the review ledger and artifact per `... review-artifact-plan` and `- v2`.

## 5. Still open (unchanged)

Re-read the Marchiori and Flores claims in Memo v2; quote-anchored claim check design; gate wiring (`verify-sources` and the agent procedure); the other v5 risks (title-search fallback sends up to 200 characters to Crossref; `--offline` ignores stale 404 entries; multi-DOI table rows share one citation).
