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
   need no ask. Then asks the user in one message: may I merge and push commit
   `<SHA>` to `main`? The message includes the branch, SHA, changed paths, check
   result, overlaps, the main checkout's `git status --short` snapshot, and known
   risks.
3. On a yes, lands in the main checkout only after these checks pass:
   - `git branch --show-current` prints `main`. If it does not, stop and tell the
     user; never merge into whatever branch the main checkout happens to be on.
   - `git status --short` matches the snapshot the agent recorded when it asked
     for approval (include that snapshot in the approval message). Any
     difference means another session has changed the checkout: stop and ask.

   Then:

   ```powershell
   git merge --ff-only <branch>
   git push origin main
   ```

   Then verify with `git log -1`. Never run a bare `git push`.
4. Records the answer: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe -m tools.land_branch record --sha <SHA> --outcome landed|declined`.

Approval covers one commit SHA. If the SHA changes, including after a rebase,
ask again. Approval does not carry over to other sessions or branches.

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
