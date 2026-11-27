# Overlap-only land-time re-test (TODO-0103)

Design: `../../superpowers/specs/tools/2026-11-25-landing-retest-overlap-design.md`.
Rule and conditions: `docs/WORKTREE_LANDING.md`, "What a land-time re-test runs".

## State, 2026-11-25
- Code and fixtures built. Narrowing was inactive until the first real pass (below).
- The scheduled task is not installed. (Installed 2026-11-27; see "Remaining".)

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
1. ~~Real `full-main` run~~ done 2026-11-26.
2. ~~Install the scheduled task~~ installed 2026-11-27 (daily 03:00, machine-local); first
   nightly run passed on `f7aaef09` the same day.
3. A real landing logged `retest_mode: overlap`; then close TODO-0103.
4. Two weeks later: review failures, missed nights, and any break the nightly run found that a
   narrowed re-test let through.

## Final review, 2026-11-26
Fixed: a selector change on an earlier `main` move no longer lets a later move narrow; a branch
editing the guard or selection code re-tests in full; an unfinished `full-main` turns narrowing off.
Also fixed (older bug, seen live on this branch): `check` recorded `main` as read after its tests, so a
commit landing during the check counted as tested and `land` did not re-test it.

First real `full-main` (run by another session): passed on `3c3745e4`, 806 s, 2026-11-26.

Known gaps, not fixed:
- A `full-main` that finds no chunks logs `passed`.
- A future-dated `scheduled_full` record is accepted.
- When `main` changed the selection code, a targeted re-test does not add new dependent tests.
- A skipped approval (`doc_only`, `data_unreferenced`) is still never re-tested.
- `_data_mirror_tests` (older code) prefixes `tests/` to paths already under `tests/`.
- The `land` record keeps only the last move's `retest_mode` and `narrowing_off`.
- ~~`impact_selection.py` and `run_tests_chunked.py` are not in `GUARD_POLICY_PATHS`~~ added
  2026-11-27 (owner's decision).
