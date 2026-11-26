# Land-time re-test: test the overlap (TODO-0103)

Status: draft for owner approval. Answers the Codex handoff
`2026-11-25-landing-retest-claude-design-handoff.md` (branch `codex/todo-0103-claude-handoff`).

## Intent
Parallel branches should not be forced to land one at a time. Today any code commit on `main`
re-runs the approved selection, so a full-suite branch pays 12-19 minutes per re-test and can run
out of the three allowed. Landing log since 2026-11-01: 7 of 143 land events re-tested, about
78 minutes in total; one landing used all three.

Non-goals: a landing queue, batching, changing `check`'s selection, changing the change-ID approval,
the overlap, binary-guard or citation stops, or the retry limits.
Anti-goal: a faster gate that lets a combined-tree failure through without anything noticing.

## Approaches
- **A. Re-test the overlap (owner's pick, with the nightly full run required first).** Cheapest
  re-tests and closes the gap below. Trusts static impact analysis more.
- B. Narrow only full-suite re-tests to `main`'s side. Smaller, leaves the gap.
- C. Landing lock. Trusts nothing new, but re-tests stay slow and sessions queue.

## Gap in the current gate (read from code; reproduce with a failing test first)
A targeted branch re-runs only the approved `check_targets` (`run_checks`, `selected_targets`).
A test that `main` adds, which depends on the branch's change, is never run.

## The rule
After rebasing, compute on the rebased tree:
- `S_b`: tests the branch's diff can affect.
- `S_m`: tests the files `main` changed since the last tested base can affect.

A test untouched by one side behaves as it did without that side, and it already ran against the
other. So only tests in both can newly fail from the combination. The graph must be the rebased
one, so that an import added by either side counts.

| Case | Re-test runs |
|---|---|
| Both sides bounded | `S_b ∩ S_m` (empty: nothing) |
| One side unbounded | the other side's set |
| Both unbounded | full suite |
| Approved check was `--full` (`explicit_full`) | full suite, as today |
| `main` changed `land_branch.py`, `impact_selection.py` or `run_tests_chunked.py` | no narrowing (the running code may be stale) |
| Narrowing switched off (below) | approved selection as today, plus `S_b ∩ S_m` when targeted |
| Approved check skipped tests | no re-test, as today |

A side is **unbounded** when `select_tests` returns a `run_all_reason` (config, top-level helper,
moved or deleted Python file, code no test imports or mirrors), when it touches a guard-policy
path, or when it changes an `OUTSIDE_TEST_INPUTS` path. `OUTSIDE_TEST_TARGETS` paths add their
mapped tests to that side's set. A data file nothing names adds nothing, as at `check`.

Example: `main` edits `a.py`, the branch edits `b.py`, and `test_x` imports a module that imports
both. `test_x` is in `S_m` and in `S_b`, so it runs.

## What this cannot see (accepted, with a backstop)
Imports built at run time, subprocess-only tests, and files found by glob are invisible to the
analysis. `check` already has this blind spot; today's full re-tests sometimes cover it by luck,
and narrowing removes that. The nightly full run of `main` is the backstop: it finds such a break
within about a day, **after** it has landed, not before.

## Nightly full run (prerequisite, enforced in code)
`land` narrows only if the newest `scheduled_full` record in the landing log has `result` =
`passed`, is at most **48 hours** old, and its `sha` is an ancestor of `main`. Otherwise it prints
why narrowing is off and uses the old rule. So a missing, failed, interrupted or stale run
degrades to today's behaviour without anyone having to act.

- Runner: a Windows scheduled task for the existing `full-main` command, daily at 03:00 with
  `-StartWhenAvailable`, so a run missed while the laptop was off starts later. The owner runs or
  approves the install command; the task lives outside Git.
- Retry: the next night, or run `full-main` by hand.
- Surface: the machine record stays in the landing log. The owner sees it in the line `land`
  prints and in `tools.landing_metrics`. No other alert in this release.
- Memory: a full run overlapping a `check` on this machine is untested. A memory failure shows as
  a failed run, which switches narrowing off. No lock in this release.
- `full-main` has never run for real. One real passing run is required acceptance evidence.

## Logging
The `land` record gains `retest_mode` (`overlap`, `approved`, `full`), the number of test files
run, and the reason narrowing was off, if it was.

## Acceptance evidence
1. Fixtures, written first: the gap (new test on `main`); the shared-dependency example; each row
   of the table; each narrowing-off condition (none, failed, stale, non-ancestor); moving `main`.
2. Replay of the 7 logged re-tests: files that would have run against files that did. For
   TODO-0100's three, a first pass gives 12, 114 and 58 files of 388.
3. A real `full-main` pass, then a real landing logged with `retest_mode: overlap`.
4. Review after two weeks of nightly records: failures, missed days, and any break the nightly run
   found that a narrowed re-test let through. Any such break: reconsider the rule.

The change edits the guard policy, so its own landing runs the full suite and needs owner approval.

## Left to the builder (my calls)
Claude builds it. One release: the code stays inert until a nightly run passes. Files:
`tools/land_branch.py`, `tests/tools/test_land_branch.py`, `docs/WORKTREE_LANDING.md`, and the
tracker entry. The 48-hour window and 03:00 time are my proposals.

## Later, only if needed
A landing lock; an alert when the nightly run fails; running subprocess-heavy tests on every
re-test if the nightly run shows that blind spot matters.
