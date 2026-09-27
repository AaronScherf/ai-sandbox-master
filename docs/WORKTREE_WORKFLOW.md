# Concurrent agent work

Use one branch and one Git worktree per writing task, with exactly one
writer per worktree. Reserve the original checkout for a single designated
integrator (the user, or an explicitly assigned agent). Read-only sessions
may inspect it. This applies to Codex, Claude, and Gemini.

Worktrees isolate checked-out files, HEAD, and staging areas. Git objects,
refs, configuration, and remotes remain shared. This prevents accidental
working-file overwrites when paths are respected; it cannot eliminate merge
conflicts or incompatible changes. Markdown rules are a working agreement,
not an operating-system access restriction.

## Create and assign workspaces

Assign each task an owner, scope, base commit, and unique branch/path.
Prefer separate files or packages for concurrent work. Coordinate changes
to common/, indexer/, dependencies, and schemas; start dependent tasks from
the prerequisite's committed result. Design ambiguities route to Claude.

Run this PowerShell example from the original repository root, substituting
unique task names. Confirm the ignore check succeeds. main is the agreed
local integration branch, not necessarily the latest remote commit.

```powershell
git status --short
git worktree list
git check-ignore .worktrees/probe
$taskBase = git rev-parse main
git worktree add -b codex/indexer-tests .worktrees/codex-indexer-tests $taskBase
git worktree add -b claude/tutor-change .worktrees/claude-tutor-change $taskBase
```

.worktrees/ is already ignored. Never use --force to reuse a checked-out
branch or occupied path. Existing .claude/worktrees/ locations can stay;
do not move, unlock, or remove another session's worktree.

Uncommitted changes are NOT included in a new worktree. Leave them with
their owner; do not stash, reset, or copy them wholesale. If needed by a
task, have the owner commit the required work on a task branch first.

Open a separate IDE window/project for each worktree and launch its agent
there. A terminal cd does not retarget an already-connected IDE tool.
Reconnect the IDE or use shell operations in the assigned worktree if its
tools still point at the original checkout.

## Check before writing

At session start and before staging or committing:

```powershell
Get-Location
git rev-parse --show-toplevel
git branch --show-current
git status --short
```

Report the absolute worktree path, branch, and task scope. Explicitly read
that worktree's root agent instructions, this procedure, and applicable
subproject CLAUDE.md; do not rely on automatic instruction discovery.
If the branch/path is wrong or unfamiliar changes appear, stop writes and
resolve ownership. Do not clean up another session's changes.

- Keep edits, formatting, generated files, and commands inside the assigned
  worktree. Check absolute paths used by scripts and IDE tools.
- Stage explicit paths; inspect git diff --cached before committing.
  Never use git add ., git add -A, or git commit -a.
- Do not switch another worktree's branch, mutate another task's refs, or
  change shared Git configuration.
- Do not use reset --hard, clean -fd/-fdx, forced worktree removal, forced
  branch deletion, or force-push as routine cleanup.
- Keep history stable after handoff. Rebase only an exclusively owned,
  unpublished branch that no other task depends on.

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

## Integrate one task at a time

The task owner supplies the branch, commit ID, changed paths, validation
results, dependencies, and remaining risks. Workers do not merge into main
or push an integration branch unless assigned the integrator role.

The integrator ensures the integration checkout is clean and no other
session is writing there. If dirty, defer integration and leave changes
with their owner rather than stashing or discarding them. Then, for example:

```powershell
git status --short
git merge --no-ff codex/indexer-tests
# Run relevant checks on the combined result before merging the next task.
```

Review combined behavior even if Git finds no textual conflicts. Preserve
both tasks' intent when resolving conflicts; send design ambiguities to
Claude instead of blindly accepting ours/theirs. A PR is a useful review
boundary when publishing is part of the task. Push/deploy only within the
user's authorized scope.

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

## Adopt the policy in existing sessions

Have the designated integrator commit the guidance before basing new tasks
on it. Existing worktrees retain old copies until updated; existing sessions
must explicitly read the updated procedure and acknowledge their scope/path.
Do not assume a running agent reloads guidance. Preserve current work in
the original checkout with its owner; use dedicated worktrees for future
writing tasks. Adoption does not authorize migrating or cleaning up ongoing
sessions.
