# Landing selected a stale full-suite check after a newer skip

- **Recorded:** 2026-11-22 18:32 EST (UTC-05:00)
- **Reporter:** Codex
- **Status:** Reproduced; awaiting Claude review
- **Proposed reviewer:** Claude (landing-policy decision and cross-component review)
- **Repository:** outer monorepo (`<monorepo>` below)
- **Persistence:** tracked handoff promoted from the ignored local bug-intake report; no raw log or private attachment is committed.

## User request and mismatch

The owner asked to land the microeconomics index branch before rebasing the GMM branches and expected the revised landing protocol to skip pytest for hub-only JSON changes. The current `check` did skip pytest. During `land`, however, the helper selected an older check for the **same change ID** and reran the entire chunked test suite. This added 1,045.5 seconds of completed retest time to a two-file index landing. The branch ultimately landed; this is a performance and policy-selection mismatch, not a failed merge or incorrect index output.

Expected: the landing step should honor the current, passing `outside_project_only` check for this unchanged branch diff, or clearly state a policy reason requiring broader validation. The intended November rule says outside-project changes that tests cannot read should not trigger a per-landing full run. The deliberate stronger-check rule may conflict with that new rule; Claude should decide the precedence.

## Original run and evidence

- **Task checkout:** `<monorepo>/.worktrees/codex-microecon-ps3-transcribe`, branch `codex/microecon-ps3-transcribe`, clean at the 2026-11-22 check; rebased SHA `58725fb18ac8ef97a73557025a43770ae9eb4e1d`. The branch changed only `ai-sandbox/academic-hub/.index/courses.json` and `ai-sandbox/academic-hub/.index/microecon.json`.
- **Main checkout:** `<monorepo>`. No dirty path relevant to those two index files was observed. Unrelated main-checkout changes were present; an exact dirty-path snapshot from the original check was not retained.
- **Change ID:** `0a36077705198635614f0ba1909af4b7005851e50adde7a00967ebfc0701addb`.
- **Runtime:** Windows, Python 3.13.7 in `ai-sandbox/academic-rag-model/.venv`, Git 2.45.1.windows.1. No model or API backend was involved.
- **Commands:** From the task checkout's `ai-sandbox/academic-rag-model/`, run `<monorepo>/ai-sandbox/academic-rag-model/.venv/Scripts/python.exe -m tools.land_branch check`, then `... -m tools.land_branch land --change-id 0a36077705198635614f0ba1909af4b7005851e50adde7a00967ebfc0701addb`.
- **Durable log:** `<monorepo>/.git/agent-landing-log.jsonl` (shared Git common directory). Filter `event=check`, branch above, and the change ID. The log is append-only and was not edited for this report.

| Event | UTC time | Base | Result | Selection | Targets |
|---|---|---|---|---|---|
| Older check | 2026-11-16 22:06:42 | `96fda871` | passed, 912.8 s | `non_py_file`, `full=false` | all eight test chunks |
| Newer check | 2026-11-22 18:04:48 | `8f69141b` | skipped, 0.0 s | `outside_project_only`, `full=false` | none |
| Landing | 2026-11-22 18:31:47 | current main | landed `58725fb1`, retested | older check selected | all eight chunks, all exit 0 |

The completed landing retest logged `agent` 156.1 s, `audio_generator` 111.7 s, `core` 159.0 s, `discovery` 5.8 s, `pipelines` 120.9 s, `resume_manager` 12.5 s, `tools` 455.6 s, and root 23.9 s. Two earlier attempts were manually stopped before the unexpected retest was diagnosed; they have no completed landing record and are not needed to reproduce the selection.

## Reproduction and code trace

**Read-only reproduction against the real log:** calling `approved_check(task_worktree, branch, change_id)` after landing returned the **2026-11-16** record, not the latest 2026-11-22 record. No live landing was rerun for this investigation.

**Synthetic reproduction:** one isolated temporary log with two checks for the same branch and change ID, in the order above, returned the older record:

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools.land_branch import approved_check

old = dict(event="check", branch="codex/example", change_id="same",
           sha="old", base="old-base", checks="passed",
           selection_reason="non_py_file", full=False)
new = dict(event="check", branch="codex/example", change_id="same",
           sha="new", base="new-base", checks="skipped",
           selection_reason="outside_project_only", full=False)
with TemporaryDirectory() as directory:
    log = Path(directory) / "agent-landing-log.jsonl"
    log.write_text("\n".join(json.dumps(x) for x in (old, new)) + "\n")
    with patch("tools.land_branch.log_path", return_value=log):
        assert approved_check(log.parent, "codex/example", "same")["sha"] == "old"
```

The executed synthetic version used `tempfile.TemporaryDirectory` and printed `latest: new skipped outside_project_only` and `selected: old passed non_py_file`; it exited 0. This reproduces record selection without Git, network, or a test run.

**Observed code path on main `14573f5b`:**

1. `tools/land_branch.py:424-442` scans check records in reverse time order but ranks `non_py_file` as 2 and a skipped `outside_project_only` as 0. The older record wins despite the newer timestamp and base. The log key is branch plus change ID; the SHA and policy version do not filter candidates.
2. `tools/land_branch.py:474-511` uses the selected record's old base and reason. Between `96fda871` and `8f69141b`, main changed 15 non-Markdown paths inside `academic-rag-model`, so the land-time `code_delta` condition was met. Because the selected record was `passed` rather than `skipped`, the helper called `run_checks` with its historical `non_py_file` reason.
3. `tools/land_branch.py:282-316` treats `non_py_file` as a full-suite reason and calls `tools/run_tests_chunked.py:92` through `run_all`. The landing log confirms all eight chunks ran.

The selection behavior is explicitly covered by `tests/tools/test_land_branch.py::test_approved_check_prefers_stronger_pass`, although that test uses an explicit full check versus a later targeted check. Other relevant cases include the outside-project skip tests and `test_retest_uses_approved_reason`. This is a confirmed explanation of this run. Whether to change precedence is a policy decision, not yet an implemented fix.

## Initial map and open questions for Claude

- **Entry point and shared helpers:** `tools/land_branch.py` (`check`, `approved_check`, `land`, `selection_reason`, `run_checks`); `tools/git_workflow.py` (shared log location, branch diff and main ancestry); `tools/run_tests_chunked.py` (chunked runner).
- **Tests:** `tests/tools/test_land_branch.py`, `tests/tools/test_landing_metrics.py`, `tests/tools/test_outside_test_inputs.py`; inspect callers and log consumers beyond this starting list.
- **Contracts:** `docs/WORKTREE_LANDING.md`; `docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md` (outside-project skip and no per-landing full run); `docs/superpowers/specs/2026-10-25-landing-approval-by-change-design.md` (approval identity); `docs/superpowers/specs/tools/2026-11-18-landing-followups-codex-handoff.md`.
- **Open policy question:** When a newer check under changed selection rules says `outside_project_only`, should an older broad check still count as stronger? Preserve deliberate explicit `--full` semantics and safety for actual project-code changes while avoiding stale policy reasons.
- **Alternatives to evaluate:** stale log data, mistaken branch/change ID, or wrong runtime are not supported here: both records match the same branch/change ID, the live `check` printed skipped, the real-log `approved_check` call selected the old record, and the completed landing log recorded the full retest. Other cross-component effects remain for Claude to inspect.

## Acceptance criteria for a fix

1. A minimal regression case with an old `non_py_file` passed record and a newer `outside_project_only` skipped record for one unchanged diff selects a record consistent with the current policy and does **not** schedule a full-suite retest merely because main changed code since the old base.
2. A deliberately requested `--full` check and a code-changing branch with a valid targeted/full approval retain their intended safety behavior. Define what happens when policy versions differ and when main changes after the latest check.
3. The landing log or console makes the selected check's timestamp, base, reason, and any retest reason visible enough to diagnose unexpected work.
4. Validate with focused unit tests for selection and land-time retesting, then a safe fixture landing. Do not rerun a live push just to demonstrate this performance issue.

## Handoff prompt

> Review `ai-sandbox/academic-rag-model/docs/handoffs/2026-11-22-landing-stale-check-selection-claude-handoff.md` against the relevant full codebase on current `main` (incident inspected at `14573f5b`). Reproduce the mismatch, trace callers and shared dependencies beyond the initial file list, distinguish a code defect from data/configuration/requirements issues, and propose or implement a fix within your role. Validate against the recorded acceptance criteria. Preserve explicit full-check intent and the landing safety gates while evaluating stale check records.

## Reviewer findings and disposition

- Claude findings: pending.
- Fix commit: none.
- Post-fix validation: not run.
- Remaining limitation: the report's synthetic reproduction confirms record selection, and the live log confirms the resulting retest; no fix or post-fix run exists yet.
