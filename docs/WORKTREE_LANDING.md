# Landing a task branch

Part of [the worktree procedure](WORKTREE_WORKFLOW.md); read that first. Use this
when a task branch is finished.

## Integrate one task at a time

Only the user lands work on `main`. Agents never merge into or push to `main`
on their own. When a task branch is finished, the agent:

1. Runs the landing check from any folder inside its worktree. A worktree has no
   `.venv` of its own (it is gitignored), so use the main checkout's interpreter:
   `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch check --full`.
   The check verifies the branch is clean, not on `main`, and not already
   published; rebases it onto `main`; runs the full test suite (`--full` is the
   landing gate, spec decision 7); and reports overlaps. It never merges or pushes.
   Omit `--full` only when every file the branch changed since its merge-base
   with `main` is Markdown (check with `git diff --name-only main...HEAD`
   inside the worktree): `land_branch` itself then reports `checks: skipped`
   with no pytest run, since nothing a test can read changed. Pass `--full`
   for every other branch, including one that mixes a Markdown file with
   anything else (a dependency pin, a lockfile, a non-`.py` test fixture) --
   don't treat "mostly docs" as equivalent to doc-only.
2. Commits its finished work to its own task branch if not already committed.
   Local commits to a task branch in its own worktree are pre-authorized and
   need no ask. Then asks the user in one message: may I land change `<ID>` on
   `main`? `<ID>` is the `Change ID:` the check printed. The message includes the
   branch, change ID, changed paths, check result, overlaps, and known risks.
3. On a yes, lands with one command from inside the worktree:
   `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch land --change-id <ID>`.
   It refuses unless the main checkout is on `main`; rebases onto the current
   `main`; stops if the change ID no longer matches, if the rebase conflicts, or
   if `main` has since changed a file the branch also changes; re-runs the
   approved check's tests only when `main` gained non-Markdown commits; stops on
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
