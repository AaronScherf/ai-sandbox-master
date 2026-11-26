# Overlap-only land-time re-test: implementation plan (TODO-0103)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `land` re-tests only what the branch and `main`'s new commits can both affect, once a recent nightly full run has passed.

**Architecture:** Pure decision functions in `tools/land_branch.py` (already a guard-policy path), called from the retest block of `_run_land`; execution still goes through `run_checks`.

**Tech Stack:** Python 3.13, `unittest`/pytest, git.

**Spec:** `docs/superpowers/specs/tools/2026-11-25-landing-retest-overlap-design.md`

## Global Constraints

- All paths are relative to `ai-sandbox/academic-rag-model/` unless they start with `docs/WORKTREE_`.
- Run tests with the shared venv: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m pytest <file> -q`. Never `pytest tests/`. No API calls.
- Files are CRLF in the working tree; preserve endings.
- `FULL_RUN_MAX_AGE_HOURS = 48`. `retest_mode` is one of `overlap`, `approved`, `full`.
- The change-ID check, overlap, binary-guard, citation and failed-test stops and `MAX_RETEST_ATTEMPTS = 3` are unchanged.
- An approved check that was `--full`/`explicit_full` re-runs the full suite; a skipped one does not re-test.

## Review Focus

- A `scheduled_full` log record missing `at`, `sha` or `result`: narrowing is off; `land` does not crash.
- An older passing run followed by a newer failed one: the newest governs, narrowing off.
- `main` renames or deletes a module: `main`'s side is unbounded, so the branch's tests run.
- The overlap is empty: nothing runs, nothing falls back to the full suite, and no retry is consumed.
- `main` moves twice during one landing: the second selection covers only the second delta.

---

### Task 1: Decision functions

**Files:**
- Modify: `tools/land_branch.py` (next to `selection_reason`)
- Test: `tests/tools/test_land_branch.py` (new class `RetestDecisionTests`)

**Interfaces (produces):**
- `SELECTOR_PATHS: tuple[str, ...]` = `tools/land_branch.py`, `tools/impact_selection.py`, `tools/run_tests_chunked.py`
- `affected_tests(relative: set[str], outside: set[str], project_root: Path) -> set[str] | None` (`None` = unbounded). Unbounded on `_touches_guard_policy`, any `is_outside_test_input`, or `select_tests(...).run_all_reason`; otherwise its files plus existing `outside_test_targets(outside)`.
- `overlap_tests(branch: set[str] | None, main: set[str] | None) -> set[str] | None`
- `FULL_RUN_MAX_AGE_HOURS = 48`; `narrowing_off_reason(entries: list[dict], repo: Path, now: datetime | None = None) -> str` (`""` = narrowing on). Uses the newest `scheduled_full` entry and `is_ancestor(repo, sha, MAIN_BRANCH)`.

- [ ] **Step 1: Write the failing tests**
  - `test_overlap_table`: `overlap_tests({"a","b"},{"b","c"}) == {"b"}`; `(None,{"c"}) == {"c"}`; `({"a"},None) == {"a"}`; `(None,None) is None`; `({"a"},{"c"}) == set()`.
  - `test_shared_dependency_is_in_the_overlap`: tree with `core/x.py` importing `core.a` and `core.b`, and `tests/core/test_x.py` importing `core.x`; `overlap_tests(affected_tests({"core/a.py"}, set(), tmp), affected_tests({"core/b.py"}, set(), tmp))` contains `tests/core/test_x.py`.
  - `test_unbounded_sides`: `affected_tests` is `None` for `{"conftest.py"}`, `{"requirements.txt"}`, `{"tools/land_branch.py"}`, a deleted `{"core/gone.py"}`, and `outside={".gitignore"}`.
  - `test_mapped_outside_target_counts`: with the shipped test file present, `affected_tests(set(), {"ai-sandbox/academic-hub/hub_config.json"}, tmp) == {"tests/core/env/test_shipped_hub_config.py"}`.
  - `test_narrowing_off_reasons` on a `make_repo` repo: `""` for a passed entry 1 hour old on `main`'s sha; non-empty for no entry, `result="failed"`, 49 hours old, sha on a side branch, entry without `at`/`sha`/`result`, and an old pass followed by a newer failure.
- [ ] **Step 2:** run `-k RetestDecision`; expect import failures.
- [ ] **Step 3:** implement the functions.
- [ ] **Step 4:** run `-k RetestDecision`; expect pass.
- [ ] **Step 5:** commit `feat(landing): decide what a land-time re-test must run (TODO-0103)`.

### Task 2: Use them in `land`

**Files:**
- Modify: `tools/land_branch.py` (`_run_land` retest block, `LandResult`)
- Test: `tests/tools/test_land_branch.py` (`LandByChangeIdTests`)

**Interfaces:**
- Consumes Task 1.
- `LandResult` gains `retest_mode: str = ""`, `retest_files: int = 0`, `narrowing_off: str = ""` (defaults last).

Behaviour, evaluated on the rebased tree each time `code_delta` is non-empty and the check was not skipped:

| Condition, first match | `retest_mode` | What runs |
|---|---|---|
| approved `--full`/`explicit_full` | `approved` | as today |
| `main`'s delta touches `SELECTOR_PATHS` | `approved` | as today |
| overlap is `None` | `full` | `run_checks(full=True)` |
| narrowing off, approved reason targeted* | `approved` | approved targets ∪ overlap |
| narrowing off, otherwise | `approved` | as today |
| overlap non-empty | `overlap` | `run_checks(reason="targeted", selected_targets=sorted(overlap))` |
| overlap empty | `overlap` | nothing; do not increment `retests`; advance `tested_base` |

\* `targeted`, `targeted_multi`, `multi_package`, `targeted_outside`.
Print one line naming the mode, the file count, and `narrowing_off` when set.

- [ ] **Step 1: Write the failing gap test** `test_retest_runs_a_new_main_test_that_depends_on_the_branch`: branch edits `agent/a.py` (with an existing `tests/agent/test_a.py`); after approval with `check_targets=["tests/agent/test_a.py"]`, `main` adds `tests/tools/test_new.py` importing `agent.a`. Assert the `selected_targets` passed to the patched `run_checks` include `tests/tools/test_new.py`.
- [ ] **Step 2:** run it; expect FAIL (only the approved target). This reproduces the gap; if it passes, stop and report.
- [ ] **Step 3: Write the other failing tests**, each patching `run_checks` and adding a passed `scheduled_full` with `append_log` where narrowing is on:
  - `test_overlap_retest_runs_only_shared_tests` (`retest_mode == "overlap"`)
  - `test_empty_overlap_runs_nothing_and_lands` (`rerun.assert_not_called()`, `retested is False`)
  - `test_narrowing_off_keeps_the_approved_selection` (`narrowing_off` non-empty)
  - `test_explicit_full_is_never_narrowed`
  - `test_main_changing_the_selector_is_not_narrowed`
  - `test_main_deleting_a_module_runs_the_branch_tests`
  - `test_second_main_move_selects_from_the_new_delta_only` (use `_move_main_then_ff`)
- [ ] **Step 4:** run `-k LandByChangeId`; expect the new tests to fail.
- [ ] **Step 5:** implement. `test_retest_uses_approved_reason` has no real tests in its repo, so patch `affected_tests` there to return `set()`; change no other existing assertion without reporting it.
- [ ] **Step 6:** run the whole file (about 8 minutes, in the background); expect all pass.
- [ ] **Step 7:** commit `feat(landing): re-test the overlap when a nightly full run has passed (TODO-0103)`.

### Task 3: Docs, replay, check

**Files:**
- Modify: `docs/WORKTREE_LANDING.md` (step 3 of the procedure; "Scheduled full run of `main`")
- Create: `docs/status/tools/2026-11-25-landing-retest-overlap.md`
- Modify: `docs/trackers/academic_hub_to_do.md` (TODO-0103: built, awaiting a nightly pass; not DONE)

- [ ] **Step 1:** document the rule, the 48-hour condition and its blind spot; replace the `schtasks` example with:

```powershell
$dir = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model"
$action = New-ScheduledTaskAction -Execute "$dir\.venv\Scripts\python.exe" -Argument "-m tools.land_branch full-main --worktree C:\Users\theaa\ai-sandbox-master" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "ai-sandbox full-main" -Action $action -Trigger $trigger -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable)
```

- [ ] **Step 2:** replay the 7 logged re-tests with `affected_tests`/`overlap_tests` (script in the scratchpad); record files-would-run against files-did in the status doc, noting it uses today's tree.
- [ ] **Step 3:** commit, run `-m tools.land_branch check` (full suite), and ask the owner to approve the change ID.

### After landing (each needs the owner's yes)

- [ ] Run `full-main` once for real; record the result in the status doc. A failure is reported, not worked around.
- [ ] Install the scheduled task; confirm with `Get-ScheduledTask "ai-sandbox full-main"` and, the next day, `-m tools.landing_metrics`.
- [ ] Close TODO-0103 only after a real landing logs `retest_mode: overlap`.
