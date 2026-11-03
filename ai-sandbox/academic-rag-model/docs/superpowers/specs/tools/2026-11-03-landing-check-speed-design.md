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
| Roughly half of runs could have been targeted (corrected 2026-11-03) | Replaying 169 logged checks through Codex's selector (branch diffs rebuilt from the log's `base`, else the sha's last commit, so multi-commit branches are under-counted): 87 targeted (687 min), 31 non-`.py` file, 29 doc-only, 20 `core/`, 2 multi-package | Expect about half of the check time to drop to targeted runs; the rest still needs step 5 |
| Failures are costly | 22 failed checks, 69 min | Run likely-failing tests first and fail fast |
| No per-chunk timing is logged | `ChunkResult.seconds` exists but is not written to the log | We cannot yet say which chunk dominates; measure before optimizing |

**Correction:** the first version of this table used `git merge-base <sha> main`, which is empty for branches already fast-forwarded into `main`, and wrongly counted those as targetable (110 runs, 80%). The row above replaces it. Counts are still indicative, not exact.

## Decisions already made (owner, 2026-11-03)

- Any change under `core/` runs the full suite until the selector is trusted.
- Which non-`.py` extensions are safe to skip is unknown and must be determined, not assumed.
- Hub-and-spokes by dependency is the long-term direction. Physical splitting is not the first step.

## Design

### Step 1: measure (no behavior change)

- Log `ChunkResult.seconds` per chunk in `check` events, plus the changed-path summary (top-level packages, extensions) and the reason the run was full.
- Report the slowest tests with `--durations`, so a handful of slow tests can be isolated. **Deferred (2026-11-03):** not implemented in steps 1-2; per-chunk timings are logged first, and `--durations` is added only if one chunk dominates.
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

- (Findings below supersede this plan.) For each non-`.py`/`.md` extension seen in the diffs (`.js`, `.html`, `.json`, then `.txt`, `.yaml`, `.svg`, `.png`), search `tests/` and the code under test for reads of that extension or of the specific file. An extension is skippable only if no test reads files of that type from the changed location.
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

## Step 3 findings (2026-11-03, read-only audit)

Scanned the 66 tracked non-`.py`/`.md` files under `academic-rag-model/` (by extension: 19 `.yaml`, 11 `.js`, 7 `.txt`, 5 `.json`, 4 `.toml`, 3 `.sh`, 3 `.html`, plus singletons) against every `.py` under `tests/` and the code under test. Method: file basename referenced in a test or in non-test code, and which `tests/<package>` references it. Name matching undercounts files loaded by directory or glob, so "unreferenced" below means "not safe to assume skippable".

**Result: no extension is safe to skip.** Every common extension is read somewhere:

| Extension | Read by | Notes |
|---|---|---|
| `.yaml` (19), `.json` (5), `.toml` (4), `.txt` (7) | tests and code in the owning package | Fixtures and config: `agent/concept_graph/sample_data`, `agent/literature/*_data`, `docs/trackers/subproject_registry*.json` (read by `tests/tools`), `guide_specs/*.toml` (read by `tests/agent`) |
| `.js`, `.html`, `.css` | code in the owning package (`agent/concept_graph/build.py`, the `tools/*/review_server.py` files) | Not named in tests directly, but those modules' tests exercise them |
| `.gitignore`, `pytest.ini`, `requirements.txt` | tests in `tools` / `agent` / a root test | Environment-wide: always full suite |
| `.codex-validation-run/**` | `tests/resume_manager` | An oddly placed fixture directory |
| `.LICENSE`, `.gitattributes`, `.ipynb`, `.ps1`, `.sh` | nothing found | Candidate skips, but low value; leave on full-suite fallback unless they start changing often |
| `Dockerfile`, `.python-version` | nothing in tests, but they define the runtime | Always full suite |

**Consequence for the design:** an extension allowlist is the wrong mechanism. Replace it with **ownership mapping**:

1. A non-`.py` file under `<package>/...` maps to `tests/<package>` plus any test file that names its basename.
2. Fixed exceptions: `.codex-validation-run/**` maps to `tests/resume_manager`; `docs/trackers/*.json` to `tests/tools`; `guide_specs/**` to `tests/agent`.
3. Environment files (`.gitignore`, `pytest.ini`, `requirements*.txt`, `Dockerfile`, `.python-version`, `.gitattributes`) and anything that maps to no package or no reader: full suite.
4. Validate by replaying the logged diffs: the ownership map must select every test that references the changed file.

The 31 replayed runs that Codex's selector sends to the full suite for a non-`.py` file are the ones this rule would move to targeted runs; measure the exact number when it is implemented.
