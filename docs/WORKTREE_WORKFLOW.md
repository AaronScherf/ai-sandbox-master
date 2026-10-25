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

## Docs that may skip a branch

Docs under `ai-sandbox/academic-rag-model/docs/status/` and
`docs/superpowers/`, and package READMEs, may go direct to `main` with explicit
paths, only when no other session has uncommitted changes to that file. Shared
logs are append-only. Any other path goes through a branch.

## Companion procedures

Only the user lands work on `main`; agents never merge into or push to `main`
on their own. Read these only when their trigger applies:

- [WORKTREE_LANDING.md](WORKTREE_LANDING.md): when a task branch is finished
  and should go to `main` (landing check, approval message, merge, record;
  merge style; overlap review).
- [WORKTREE_DATA_AND_RETIRE.md](WORKTREE_DATA_AND_RETIRE.md): before working in
  a child repo (`academic_notes/`, portfolio), running anything that writes
  shared data, a corpus, an index or a server, or removing a worktree; also
  Windows Git quirks.

## Adopt the policy in existing sessions

Have the designated integrator commit the guidance before basing new tasks
on it. Existing worktrees retain old copies until updated; existing sessions
must explicitly read the updated procedure and acknowledge their scope/path.
Do not assume a running agent reloads guidance. Preserve current work in
the original checkout with its owner; use dedicated worktrees for future
writing tasks. Adoption does not authorize migrating or cleaning up ongoing
sessions.
