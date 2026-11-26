# Overlap-only land-time re-test (TODO-0103)

Design: `../../superpowers/specs/tools/2026-11-25-landing-retest-overlap-design.md`.
Rule and conditions: `docs/WORKTREE_LANDING.md`, "What a land-time re-test runs".

## State, 2026-11-25
- Code and fixtures built. Narrowing is **inactive**: no `scheduled_full` record exists.
- `full-main` has not had a real run, and the scheduled task is not installed.

## Reproduced gap
Before the change, a targeted branch's re-test ran only the approved test files. A fixture where
`main` adds a test importing the branch's module showed it was never run
(`test_retest_runs_a_new_main_test_that_depends_on_the_branch`).

## Replay of logged re-tests since 2026-11-01
On today's tree (388 test files), so counts are approximate. 2 of 7 landings were replayable:
three point at pruned commits and two records lack `approved_base`.

| Landing | Approved run | Overlap rule would run |
|---|---|---|
| `claude/folder-move-frontmatter` (`--full`) | full | full (never narrowed) |
| `claude/hub-config-hermetic`, re-test 1 | full | 12 files |
| `claude/hub-config-hermetic`, re-test 2 | full | 114 files |
| `claude/hub-config-hermetic`, re-test 3 | full | 58 files |

These are file counts, not times. The sample is one narrowable landing.

## Remaining
1. Real `full-main` run; record the result here.
2. Install the scheduled task (owner's call); confirm with `tools.landing_metrics` the next day.
3. A real landing logged `retest_mode: overlap`; then close TODO-0103.
4. Two weeks later: review failures, missed nights, and any break the nightly run found that a
   narrowed re-test let through.
