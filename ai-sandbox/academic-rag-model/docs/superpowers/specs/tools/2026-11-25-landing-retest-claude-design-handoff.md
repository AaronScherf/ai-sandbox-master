# Claude design handoff: TODO-0103 land-time re-tests

**Request:** Design a cheaper land-time re-test without weakening the landing gate. This is a design handoff, not approval to change the gate or install a scheduled task. The owner asked that the re-test safety concerns and the missing full-suite schedule be included.

## Required outcome and constraints

- Reduce the delay when `main` gains an unrelated code commit after a branch's passing `check`, especially when the approved check ran the full suite. Keep the approval tied to the same change ID and preserve the existing overlap, binary-guard, citation, and failed-test stops.
- Define when a narrower re-test is sound, when the full suite is mandatory, and what happens when impact analysis cannot bound the affected tests. Do not treat the TODO's “tests affected by BOTH” sketch as an accepted rule.
- Account for the static import graph's blind spots: runtime imports, subprocess-only tests, path/glob data reads, outside-project inputs, and added/deleted/moved files. The selected tests must exercise the branch **after** rebasing onto the current `main`.
- Decide whether an operating periodic full-suite run is a prerequisite for narrowing the gate. The existing `full-main` command is implemented, but no schedule or real scheduled run was found. Installing a schedule remains an owner decision.
- Compare the smallest useful change against a landing queue/lock or batching. Re-derive the smallest release after review: state what is needed now, what can wait, and whether an early phase delivers value on its own.

## Verified current behavior (2026-11-25)

| Capability | Discovery and scope | Side effects, cost, output, and verification |
|---|---|---|
| `tools.land_branch check` | Selects branch tests using `tools/impact_selection.py`; logs selected targets and a passing check against a base SHA. | May rebase the task branch; targeted checks can be wide. `--full` runs the chunked suite. See `docs/WORKTREE_LANDING.md`. |
| `tools.land_branch land` | `_run_land` rebases, checks the change ID and same-file changes, then computes `main_changed` since the approved base. Any non-Markdown project change, `OUTSIDE_TEST_INPUTS`, or `OUTSIDE_TEST_TARGETS` triggers a re-run of the **approved selection** if that check was not skipped. | Runs `run_checks` on the rebased worktree. A full approved check runs the full suite again. At most three test re-runs are allowed while `main` keeps moving; it stops on failure. It also runs the main-copy binary guard, overlap check, citation gate, fast-forward merge, and push. See `tools/land_branch.py` (`_run_land`, `MAX_RETEST_ATTEMPTS`). |
| `tools/impact_selection.py` | Static import graph, mirror tests, and literal/path-based data readers. It selects tests for a changed-file set and has full-suite fallback reasons such as config, helper, guard-policy, and moved/deleted code. | Returns a selection, not proof of all runtime effects. Its graph is built from the worktree's project files. See `select_tests` and `ImportGraph`. |
| `tools.land_branch full-main` | Fetches `origin/main` and tests it in a detached scratch worktree. | Runs the full suite in chunks, logs a `scheduled_full` event with SHA/result/timings, then removes the scratch worktree. The command is implemented and fixture-tested; this does not establish an unattended run. See `full_main` and `tests/tools/test_land_branch.py`. |
| Scheduling/monitoring | `docs/WORKTREE_LANDING.md` gives a Windows Task Scheduler example; `tools.landing_metrics --since 2026-11-01` reports the last logged scheduled run. | The documented `ai-sandbox full-main` task was absent (`schtasks /Query` returned “cannot find”), metrics reported `Scheduled full run: none logged`, and the landing guide says nothing schedules it yet. Another task name or scheduler was not audited. No unattended retry, alert, or response policy is established. |

The `TODO-0103` queue entry reports a 15–20 minute full-suite re-test and a three-retest-limit incident during TODO-0100's landing. Treat that as tracker evidence to verify against the landing log before using exact timing in the design. The prior speed proposal (`docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md`) still says `full-main` was not built; current code and tests supersede that status. TODO-0100 is now closed (`73cccf10`, `3c3745e4`): `hub_config.json` is in `OUTSIDE_TEST_TARGETS` and selects one shipped-config test, rather than the full suite.

## Safety questions for Claude to settle

1. What exactly is the re-test obligation after rebasing: the intersection of branch-affected and main-affected tests, a union/subset with a stronger dependency proof, or a different invariant? Demonstrate that the chosen rule cannot skip a test that passed on the old base but fails only for the **combined** tree. Include an example with two disjoint changed files that interact through a shared dependency or data input.
2. How should `--full` approval, full-suite fallback reasons, a main-side guard-policy change, and changed outside inputs behave? A narrow re-test must not silently discard the meaning of an explicit full check or an unknown-impact fallback. Preserve the check's approved reason and targets where required.
3. What evidence is sufficient to trust impact selection on *both* change sets? Define fallback for runtime imports, subprocess calls, dynamic path/glob reads, new or removed tests, moved/deleted modules, and an unmappable main delta. Consider the impact graph after rebase and changes to the selector itself.
4. How will the periodic full run actually execute? Specify Task Scheduler or another concrete mechanism, run frequency and 15–30 minute scan cost, persistent SHA/result state, stale/missed-run detection, retries after interruption or failure, and what happens when no human is available. Keep the machine log distinct from the owner's review/alert surface. Determine whether it can overlap with landing checks safely on this memory-constrained Windows host.
5. Could a short landing queue or lock eliminate repeated full checks more safely or cheaply for the first release? Define ownership, timeout/crash recovery, and whether batching changes the one-change-ID approval rule. Do not assume a lock exists today.
6. What test and rollout evidence will justify changing a guard-policy file? Use adversarial fixtures for combined-tree failures, stale approvals, moving `main`, and fallback cases; replay representative landing-log changes; then distinguish fixture passes, a successful real landing, and repeated scheduled full runs over time. Require owner approval before the guard-policy change lands.

## Repositories, state, and handoff boundary

The proposed code, tests, guide, and tracker are all in the **outer monorepo**, not the nested `academic_notes` repo. `land_branch` writes the append-only landing log in the outer Git common directory; `full-main` uses a temporary detached outer worktree. A scheduler would be machine-local and its task definition is outside Git. No external service or API is needed for the design. The owner controls any schedule installation and any landing to `main`.

Relevant files: `docs/trackers/academic_hub_to_do.md` (TODO-0103); `tools/land_branch.py`; `tools/impact_selection.py`; `tools/landing_metrics.py`; `tests/tools/test_land_branch.py`; `docs/WORKTREE_LANDING.md`; `docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md`; `docs/superpowers/specs/tools/2026-11-03-landing-check-speed-design.md`; `docs/superpowers/specs/tools/2026-11-25-landing-real-use-check-codex-handoff.md`; `docs/status/tools/2026-11-25-bootstrap-part-i-landing-real-use-v1.md`.

**Requested Claude deliverable:** a reviewed design with the re-test invariant, fallback matrix, full-suite execution/monitoring prerequisite, smallest release and later phases, acceptance evidence, and an implementation handoff for Codex. No gate or scheduler change has been made for TODO-0103.
