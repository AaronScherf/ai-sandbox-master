# Multi-Agent Routing Convention: Worktree Isolation Added, Codex Root Discovery Confirmed

Follow-up to `2026-09-23-agent-routing-status.md`, which established the
routing convention itself (which of Claude, Gemini, Codex handles what).
This session's changes address the gap that convention left open: routing
says who does a task, but not how three agents avoid clobbering each
other's files and git state while doing it. That gap is now closed by a
dedicated worktree procedure, wired into all three per-agent entry points.

## How the three-agent approach works today (current state)

Four files at the `ai-sandbox-master` repo root compose into the full
picture, each with a single job:

- **`docs/AGENT_ROUTING.md`** — canonical routing logic. Claude takes
  judgment/architecture/continuity work (it is the only agent with
  cross-session memory here); Gemini takes large-context reads that don't
  require a decision; Codex takes routine, mechanical, well-specified work.
  Escalation runs both ways — a routine agent stops and flags Claude on a
  judgment call; Claude delegates down instead of spending session budget
  on bulk reads or mechanical work.
- **`docs/WORKTREE_WORKFLOW.md`** (new this session) — the isolation
  mechanics underneath that routing: one branch + one Git worktree per
  writing task, exactly one writer per worktree, naming convention
  `<agent>/<task>` (e.g. `codex/indexer-tests`, `claude/tutor-change`),
  explicit prohibitions on `git add -A`, force-ops, or touching another
  session's worktree, and a serialized integration step owned by one
  designated integrator.
- **`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`** (repo root) — one per agent,
  each a thin entry point: workspace orientation plus a link to both docs
  above rather than duplicated content. `AGENTS.md` is Codex's file by the
  same naming convention Codex's own tooling expects (analogous to how
  `CLAUDE.md` is discovered by Claude Code) — confirmed with the user this
  session that it is a dedicated file, not a generic fallback the other two
  agents also read.
- Each subproject's own `CLAUDE.md` (`academic-rag-model/`,
  `academic-hub/`) carries a short "Multi-agent routing" pointer back to
  `docs/AGENT_ROUTING.md` rather than restating it.

Net effect: a session in any of the three tools reads one small entry-point
file, gets routed to the shared convention doc for "should I even be doing
this," and to the worktree doc for "how do I do it without stepping on
another session's files."

## What changed since 2026-09-23

The prior status doc shipped the routing convention (who does what) but
left conflict-avoidance for concurrent writers unaddressed. This session
added:

- `docs/WORKTREE_WORKFLOW.md` (new) — full procedure: assigning
  owner/scope/base-commit/branch per task, pre-write checks
  (`git status`, `git branch --show-current`, etc.), explicit-path staging,
  data/runtime-side-effect isolation notes (child repos, ignored PDFs/.env,
  shared corpus writers), serialized integration, and worktree retirement.
- `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, and `docs/AGENT_ROUTING.md` each
  got a short addition linking to it and naming that agent's branch prefix
  (`claude/<task>`, `gemini/<task>`, `codex/<task>`).

**Not yet committed** — `git status` shows `docs/WORKTREE_WORKFLOW.md` as
untracked and the four other files as locally modified. This status doc
describes work in progress, not a shipped state; the designated integrator
still needs to commit before other sessions can rely on it being present.

## Confirmed this session

- Codex reports it is running from the correct repo root and reading
  `AGENTS.md` there. This directly narrows (for Codex specifically) the
  open question the 2026-09-23 doc raised about whether non-Claude agents
  discover a repo-root context file at all. It does **not** resolve the
  harder half of that question — whether Codex would still find it when
  launched from inside a subproject directory like `academic-rag-model/`
  rather than the root — since this confirmation was from a root-launched
  session.

## Open questions / follow-ups (carried forward + updated)

- Still unconfirmed: root-context-file discovery from a subproject cwd,
  for both Gemini and Codex (Codex's root-launch case is now confirmed;
  subproject-launch case is not, for either tool).
- No enforcement mechanism exists for either the routing convention or the
  worktree procedure — both depend on whoever launches a session choosing
  correctly and self-reporting escalations. Still deliberately deferred as
  premature for a manual, single-user workflow; revisit if routing or
  worktree mistakes start happening in practice.
- Commit the pending worktree-workflow changes (see above) before treating
  the procedure as active guidance other sessions can assume is in place.
