# Landing check speed: design

**Status:** proposed for review. No code changed. Owner: Claude (design); Codex implements per `docs/AGENT_ROUTING.md`.
**Scope:** `tools/land_branch.py`, `tools/run_tests_chunked.py`, `docs/WORKTREE_LANDING.md`. Context: `docs/MONOREPO_SPLIT_EVALUATION.md` (branch `claude/monorepo-split-handoff`).

## Problem

Landing checks take too long: 175 logged runs of the landing gate (`.git/agent-landing-log.jsonl`, 2026-10-07 to 2026-11-03) cost about 21 hours of check time. Median per run is 6 min, p90 about 12 min, max 24 min. 22 runs failed and wasted 69 min. Landing also re-runs the suite after a rebase (`retested`).

## Evidence

| Finding | Evidence | Consequence |
|---|---|---|
| Targeted selection almost never runs | 174 of 175 checks ran the whole suite (all 9 `tests/` chunks); one ran targeted | `select_test_targets` exists but is effectively dead code |
| Agents are told to pass `--full` | `docs/WORKTREE_LANDING.md:13-20` makes `--full` the gate for every non-Markdown branch; every check since 2026-10-25 has `full=True` (33 of 33 with a recorded flag) | The documented procedure, not the code, forces the full suite |
| Reconstructed from diffs, most branches did not need it | Of the 135 pre-`--full`-flag checks whose diff could be rebuilt: 110 touched at most 2 packages and not `core/`; 17 touched `core/`; 6 had a non-`.py`/`.md` file (`.js`, `.html`, `.json`); 2 touched 3+ packages. The 33 runs with `--full` set were not reconstructed | About 80% of those runs (720 min) are candidates for targeted runs |
| Failures are costly | 22 failed checks, 69 min | Run likely-failing tests first and fail fast |
| No per-chunk timing is logged | `ChunkResult.seconds` exists but is not written to the log | We cannot yet say which chunk dominates; measure before optimizing |

The reconstruction used `git merge-base <sha> main` for each logged sha; 7 shas no longer resolve (175 = 135 + 33 + 7). Counts are indicative, not exact.

## Decisions already made (owner, 2026-11-03)

- Any change under `core/` runs the full suite until the selector is trusted.
- Which non-`.py` extensions are safe to skip is unknown and must be determined, not assumed.
- Hub-and-spokes by dependency is the long-term direction. Physical splitting is not the first step.

## Design

### Step 1: measure (no behavior change)

- Log `ChunkResult.seconds` per chunk in `check` events, plus the changed-path summary (top-level packages, extensions) and the reason the run was full.
- Report the slowest tests with `--durations`, so a handful of slow tests can be isolated.
- Acceptance: one week of log data answers which chunk dominates and how often each trigger fires.

### Step 2: stop forcing `--full` (biggest win, lowest risk)

- Change the procedure so `--full` is no longer the default gate. `land_branch check` selects targets itself; `--full` stays as an explicit override.
- Selection rules, in order. Any rule that cannot decide falls through to the full suite:
  1. Markdown-only: skip (exists).
  2. Any change under `core/`, `conftest.py`, `pytest.ini`, `requirements.txt`, root `tests/` helpers, or an unrecognized file type: full suite.
  3. Otherwise run `tests/<package>` for each changed package, plus the changed test files.
- Update `docs/WORKTREE_LANDING.md` to match (remove the "pass `--full` for every other branch" rule).
- Acceptance: a unit test per rule; a replay of the logged diffs shows the predicted share of targeted runs.

### Step 3: determine safe extensions

- For each non-`.py`/`.md` extension seen in the diffs (`.js`, `.html`, `.json`, then `.txt`, `.yaml`, `.svg`, `.png`), search `tests/` and the code under test for reads of that extension or of the specific file. An extension is skippable only if no test reads files of that type from the changed location.
- Output is an allowlist with the evidence per entry. Until then these stay on the full-suite fallback.

### Step 4: dependency-aware selection (spokes)

- Build the import graph from the packages (`core`, `agent`, `audio_generator`, `discovery`, `pipelines`, `resume_manager`, `tools`). A spoke that imports another spoke pulls that spoke's tests in; `core/` still runs everything until the graph is trusted.
- Validate by replaying the logged branches: the selected set must include every test that failed historically for that diff.

### Step 5: reduce the cost of the full suite and of retests

- Fail fast: run changed-package chunks first, then the rest, and stop at the first failure.
- Skip the post-rebase retest when the rebase added no changes to files the suite reads (compare the file sets of `main` since the check).
- Revisit parallel runs (reverted 2026-10-06 after a timing flake) only after the flaky test is fixed.

### Step 6: physical split (deferred)

Only if steps 1-5 do not meet the target. It needs a versioned `core/` (pin or package, no submodules) and cross-repo commits.

## Target

Median targeted check at most 90 s; median over all checks at most 3 min; full suite at most 8 min. Revisit after step 1 data.

## Related efforts (separate)

- **Hub path model:** the `part_N` fix handled one nesting layer by name. A more general path model (match notes and resources by relative path, configurable category depth, stable card identity) and the `ACADEMIC_HUB_ROOT` setting touch the same module (`core/env/academic_hub_paths.py`) and should be one separate effort, sequenced after this one.
- **PDF/SVG guard:** a pre-commit and landing check blocking those files under `academic-hub/`.
