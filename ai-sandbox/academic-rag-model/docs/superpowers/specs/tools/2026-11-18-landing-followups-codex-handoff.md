# Codex handoff: landing follow-ups after rules 1-4 and 6 (2026-11-18)

From Claude (design), to Codex (implementation). Supersedes `docs/handoffs/2026-11-11-codex-landing-selection-and-guard-brief.md`, which is stale (its Part A is mostly landed). Use a `codex/<task>` branch and worktree per `docs/WORKTREE_WORKFLOW.md`; stage explicit paths; tests make no API calls. Do not land; the owner lands.

**Read first (grep, do not read whole):** `docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md` ("Implementation status" section), `docs/WORKTREE_LANDING.md`, `tools/land_branch.py` (`selection_reason`, `run_checks`, `OUTSIDE_TEST_INPUTS`), `tools/impact_selection.py`, `tools/run_tests_chunked.py` (`run_selected`).

## What already landed (do not redo)

- `79be34ba`: `OUTSIDE_TEST_INPUTS`, reasons `outside_project_only`, `allowlist_hit`, `guard_policy_change`, guard test `tests/tools/test_outside_test_inputs.py`.
- `8b7a5cec`: `tools/impact_selection.py` (import closure, data-file readers, mirror folders), reasons `targeted`, `data_unreferenced`, `moved_or_deleted_file`, `no_tests_for_code`, `helper_change`, `config_change`; `core/` no longer means the full suite.

**Both parts below edit `tools/land_branch.py` and `tests/tools/test_land_branch.py`. Do them on one branch, in the order given, or land one before starting the other, so there is no overlap.**

## Part B: TODO-0095, judge a branch by `main`'s guard

Problem: `land_branch` imports `guard_binaries` from the branch being landed, so a branch that weakens the guard is judged by its own edited copy. Call sites: `guard_binaries.check_range(worktree, MAIN_BRANCH)` in `_run_check` and again in `_run_land`.

1. Run the guard from `main`: either execute `python -m tools.guard_binaries --range main...HEAD` with `cwd` at `main_checkout(worktree).path`, or load `main`'s copy with `git show main:ai-sandbox/academic-rag-model/tools/guard_binaries.py`. Pick the simpler one and say why. Keep `_base_allowlist` reading the allowlist from `main`.
2. When `GUARD_POLICY_PATHS` changed (`policy_changed` is already computed), `land` refuses unless the owner's approval covers that change ID. Reuse the existing change-ID approval; do not add a second mechanism.
3. Test: a branch edits `guard_binaries.py` to allow PDFs and stages a hub PDF; both `check` and `land` must still refuse. Keep true: a branch that only adds an allowlist line is judged against `main`'s allowlist.

## Part A remainder: the scheduled full run (proposal rule 5)

The static import analysis cannot see run-time imports or tests that run code only through a subprocess, so a periodic full run of `main` is the backstop that catches what selection misses.

1. Add `python -m tools.land_branch full-main`: run the full chunked suite against `origin/main` in a scratch detached worktree (never in the main checkout), remove the worktree afterwards, and append `{"event": "scheduled_full", ...}` to the landing log with per-chunk timings and pass/fail.
2. Surface it in `tools/landing_metrics.py`: last scheduled run, its result, and age; flag a failure.
3. Do not create the schedule yourself. Document in `docs/WORKTREE_LANDING.md` how the owner can schedule it (Windows Task Scheduler command line) and leave the decision to them.
4. Tests with a fake runner; no real suite run in unit tests.

## Optional, separate branches

- **TODO-0100** (hermetic tests against `hub_config.json`): large; only after the above lands.
- **TODO-0093 and TODO-0094:** their text still names `RETEST_OUTSIDE_PATHS`, now `OUTSIDE_TEST_INPUTS`. Refresh the wording. In TODO-0094, item (3) is already handled (a re-test filters deleted test files); items (1) and (4) remain.

## Report back

Branch and commit, test results, and anything you changed from this brief and why. Do not change `impact_selection` semantics without adding a test for the case first.
