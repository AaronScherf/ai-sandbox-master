# Shared data, child repos and retiring worktrees

Part of [the worktree procedure](WORKTREE_WORKFLOW.md); read that first. Use this
before touching child repos or shared data, and when removing a worktree.

## Isolate data and runtime side effects

Outer-repository worktrees do not populate or isolate the separate
academic_notes/, portfolio, or independent-project repositories. For work
in a child repo, identify its root with git rev-parse --show-toplevel and
create a worktree belonging to that repo with a distinct destination.
Never point two writers at the same child checkout.

Ignored PDFs, .env, virtual environments, and local models are not copied.
Provision only what is needed; use a per-worktree virtual environment when
installing or changing dependencies. Never print or commit secrets.
Do not run workspace_generator.sh merely to initialize a task worktree:
it can pull child repositories and optionally sync data.

Use fixtures or a worktree-local corpus for tests and pipelines. Do not
junction/symlink writable output directories to the live vault. Check all
input/output roots before running converters, indexers, resume tools, or
sync processes; relative defaults may resolve differently in a worktree.
Writes to a shared corpus, index, resume master, or cloud destination need
one assigned writer and coordination with sync processes such as Obsidian
Git sync. Use distinct ports/output paths for concurrent servers/builds.
Worktrees do not isolate external side effects.

## Retire completed worktrees

After integration, confirm the owner session and background processes have
stopped, the worktree is clean, and no needed ignored/untracked files remain.
Check git status --short --ignored inside the worktree too. Then, from the
original checkout, the integrator may run:

```powershell
git worktree remove .worktrees/codex-indexer-tests
git branch -d codex/indexer-tests
```

If Git refuses, investigate; do not force removal or use filesystem deletion.
Squash/cherry-pick integration can require a separate history/ownership check
because Git may not recognize the branch as merged. git worktree lock
protects against administrative removal/pruning, not concurrent file edits.

On Windows, `git worktree remove` can unregister the worktree successfully
while the directory deletion itself fails with `Invalid argument`,
`Device or resource busy` or `Permission denied` -- a file-handle lock, not a
content-safety refusal. The usual cause is the removing session itself: its
shell (or IDE) still has its working directory inside the worktree, as it does
right after `land_branch land`. Prevent it by leaving first: run the removal
from a fresh shell started in the main checkout (a `cd` within the same
PowerShell process is not always enough). This is a different case from the
paragraph above:
confirm with `git worktree list` that the path is no longer registered
before treating it as safe. Once it's gone from that list, Git tracks
nothing there, and a plain filesystem `rm -rf` /
`Remove-Item -Recurse -Force` on the orphaned directory is cosmetic
cleanup, not the forced/filesystem deletion being warned against above. If
the path is still registered, that is the real refusal case -- investigate,
don't force.

## Windows-specific gotchas

`git show <ref>:<path>` and `git cat-file -p <ref>:<path>` get silently
mangled by git-bash's MSYS path conversion when `<ref>` contains slashes
(a branch name like `origin/codex/foo`) -- `origin/codex/foo:.gitignore`
becomes `origin\codex\foo;.gitignore`, producing a confusing
"fatal: Not a valid object name" or "fatal: ambiguous argument" error that
looks like the ref doesn't exist. Use the commit SHA instead of the branch
name (`git show 08e76bb:.gitignore`) to sidestep it, or set
`MSYS_NO_PATHCONV=1` for the one command.
