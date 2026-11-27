# Landing a task branch

Part of [the worktree procedure](WORKTREE_WORKFLOW.md); read that first. Use this
when a task branch is finished.

## Integrate one task at a time

Only the user lands work on `main`. Agents never merge into or push to `main`
on their own. When a task branch is finished, the agent:

1. Runs the landing check from `ai-sandbox/academic-rag-model/` inside its
   worktree (the `tools` package must be importable, so the worktree root fails
   with `No module named 'tools'`). A worktree has no
   `.venv` of its own (it is gitignored), so use the main checkout's interpreter:
   `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch check`.
   The check verifies the branch is clean, not on `main`, and not already
   published; rebases it onto `main`; selects test targets; and reports overlaps.
   It never merges or pushes. Markdown-only changes skip pytest, and so do
   changes only outside `academic-rag-model/` (hub notes, `.index/` JSON,
   research pins; reason `outside_project_only`) unless a path is in
   `OUTSIDE_TEST_INPUTS` in `tools/land_branch.py` (paths tests read; reason
   `allowlist_hit`, full suite). `hub_config.json` is not on that list: the suite
   reads a frozen seed (`tests/conftest.py`), so a change to it runs only
   `tests/core/env/test_shipped_hub_config.py` (`OUTSIDE_TEST_TARGETS`; reason
   `targeted_outside`). Inside the project, a change runs only the test
   files it can affect (`tools/impact_selection.py`): for Python, the tests that
   import the changed module directly or through other modules, plus the tests in
   its mirror folder under `tests/`; for a data file, the tests (and modules'
   tests) that name its path, its file name or a rarely mentioned folder, plus the
   nearest mirror test folder; a data file nothing names runs nothing
   (`data_unreferenced`). Wide selections run in chunks per package. The full
   chunked suite still runs for `--full`, the landing/guard files
   (`guard_policy_change`), `conftest.py`/top-level test helpers
   (`helper_change`), dependency pins and pytest config (`config_change`), a
   deleted or moved Python file (`moved_or_deleted_file`), and code no test imports
   or mirrors (`no_tests_for_code`). The analysis is static: an import built at
   run time is invisible to it, so a periodic full run of `main` is the backstop.
   A rename counts as changes to both its old and new paths.
2. Commits its finished work to its own task branch if not already committed.
   Local commits to a task branch in its own worktree are pre-authorized and
   need no ask. Then asks the user in one message: may I land change `<ID>` on
   `main`? `<ID>` is the `Change ID:` the check printed. The message includes the
   branch, change ID, changed paths, check result, overlaps, and known risks.
3. On a yes, lands with one command from inside the worktree:
   `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch land --change-id <ID>`.
   It refuses unless the main checkout is on `main`; rebases onto the current
   `main`; stops if the change ID no longer matches, if the rebase conflicts, or
   if `main` has since changed a file the branch also changes; re-runs tests
   (see "What a land-time re-test runs") only when `main` gained non-Markdown changes inside
   `academic-rag-model/`, or changed a path in `OUTSIDE_TEST_INPUTS` (root
   `.gitignore`, `ai-sandbox/.obsidian/`, the Novelty Check note; files the
   suite reads) or `OUTSIDE_TEST_TARGETS` (`hub_config.json`); stops on
   a failure or an overlap (a tracked file the branch changes that is dirty in
   the main checkout or changed on another open branch); then runs
   `git merge --ff-only` and `git push origin main` in the main checkout and
   logs the landing. If `main` moves mid-landing it retries: without limit while
   only Markdown commits arrive (up to a 20-attempt guard), and at most 3 times
   when a test re-run is needed. It prints `LANDED <sha>` or `STOP: <reason>`.
   On a STOP, report the reason and ask again. Never fall back to a manual
   merge, and never run a bare `git push`.
4. On a no, records it: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch record --sha <SHA> --outcome declined`.
   (`land` records successful landings itself.)

Approval covers one change ID on one branch, for the session that asked. A clean
rebase keeps the change ID, so `main` moving does not by itself need a new
approval; any edit to the change does. Approval does not carry over to other
sessions or branches. Untracked or unrelated files in the main checkout do not
block a landing.

The binary guard runs from `main`'s copy of `tools/guard_binaries.py` and
`main`'s allowlist (`main_guard` in `tools/land_branch.py`), not the branch's, so
a branch cannot weaken its own judge. `land` also refuses a change that edits a
`GUARD_POLICY_PATHS` file unless the approved check flagged it
(`guard_policy_changed`); if it did not, run `check` again and ask for the new
change ID. The list covers the guard, the landing tool, the pre-commit hook and the
files that pick and run tests (`tools/impact_selection.py`,
`tools/run_tests_chunked.py`); editing one runs the full suite.

## Scheduled full run of `main`

`python -m tools.land_branch full-main` fetches `origin/main`, runs the full
chunked suite in a scratch detached worktree under the system temp dir (the main
checkout is never touched; the worktree is removed afterwards) and appends a
`scheduled_full` record (sha, result, failed and flaky chunks, per-chunk
timings) to the landing log. Chunks that fail are re-run once: one that then
passes is logged as flaky and does not fail the run, so the command exits 1 only
when a chunk fails twice. `python -m tools.landing_metrics` shows the last run.
`check` prints a `WARNING:` when the last run failed, did not finish, is more
than 48 hours old or was never logged; the warning does not block a landing. A
run takes 15 to 30 minutes.

When a run fails: run it again by hand to confirm, then record a TODO naming the
failed chunks and the sha, and route the fix.

The owner chose a nightly schedule (2026-11-27); `land` relies on this run
(below). To create it with Windows Task Scheduler, run once in PowerShell
(`-StartWhenAvailable` starts a run that was missed while the laptop was off;
by default the task runs only while you are logged on and on AC power):

```powershell
$dir = "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model"
$action = New-ScheduledTaskAction -Execute "$dir\.venv\Scripts\python.exe" -Argument "-m tools.land_branch full-main --worktree C:\Users\theaa\ai-sandbox-master" -WorkingDirectory $dir
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "ai-sandbox full-main" -Action $action -Trigger $trigger -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable)
```

Remove it with `Unregister-ScheduledTask -TaskName "ai-sandbox full-main"`.

## What a land-time re-test runs

After rebasing, `land` finds the tests the branch's diff can affect and the
tests `main`'s new commits can affect, both on the rebased tree. Only tests in
both sets can newly fail from combining them, so only those run (`Retest mode:
overlap`). An empty overlap runs nothing and uses no retry. A side whose impact
cannot be bounded (config, top-level test helper, guard policy, moved or deleted
Python file, code no test imports or mirrors, an `OUTSIDE_TEST_INPUTS` path)
sets no limit, so the other side's tests run; if neither is bounded, the full
suite runs. An explicit `--full` approval, and a `main` change to the selection
code itself since the approval, are never narrowed. A branch that changes the
guard policy or the selection code re-tests with the full suite.

Narrowing needs the newest `full-main` record to be `passed`, at most 48 hours
old, and on a commit in `main`. A run that started and did not finish also turns
narrowing off. Otherwise `land` says why, re-runs the approved
selection as before, and for a targeted branch adds the shared tests (a test
`main` added that depends on the branch is not in the approved list).

Blind spot: the selection is static. Run-time imports, subprocess-only tests
and files found by glob are invisible to it, and an overlap re-test no longer
covers them by chance. The nightly run finds such a break after it has landed,
within about a day.

Merge style is rebase onto `main`, then `--ff-only`. Do not use `--no-ff`
merges. Rebasing is allowed only on a branch that is exclusively owned and not
published.

Before a landing, `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.active_work` shows
overlaps with other open worktrees and with the main checkout's uncommitted
files. Review any overlap with the user before asking to land.

Review combined behavior even if Git finds no textual conflicts. Preserve both
tasks' intent when resolving conflicts; send design ambiguities to Claude
instead of blindly accepting ours or theirs. A PR is a useful review boundary
when publishing is part of the task. Push or deploy only within the user's
authorized scope.
