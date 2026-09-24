# Agent routing convention

Three agents work across this monorepo: Claude (Claude Code), Gemini
(Antigravity), and Codex (OpenAI). This file is the single source of truth
for which agent handles what — `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md`
each link here instead of repeating this content, so the convention can't
drift out of sync between them (see `.gitignore`'s per-device drift problem
in `academic-rag-model/docs/status/2026-09-21-obsidian-git-sync-status.md`
for what happens when duplicated config diverges).

## Why route at all

Claude Code sessions run on a fixed per-session token budget. Reading large
files, whole directory trees, or long status docs just to answer "what does
this do" spends that budget on retrieval instead of judgment. Gemini's
context window and Codex's mechanical-task throughput exist to absorb that
kind of work, so Claude's budget stays free for decisions that actually need
it.

## Claude — judgment, architecture, continuity

Use for:
- New project/subproject initiation, brainstorming, design tradeoffs
- Architectural decisions and anything with more than one reasonable approach
- Code review / security review
- Anything that depends on prior decisions or open threads — Claude holds
  cross-session memory in this workspace; Gemini and Codex sessions start
  cold every time
- Any task a routine agent below stops on because it hit a judgment call

## Gemini — large-context reading, no decisions required

Use for:
- Summarizing or auditing more than ~5-10 files, or a full directory tree
- Long status-doc, PDF, or transcript synthesis
- Full-codebase sweeps ("find every place X pattern is used")
- Large-log or large-diff triage

Gemini reports findings; it doesn't make design calls. If a read surfaces a
decision point, it should say so explicitly and hand back to Claude rather
than picking a direction.

## Codex — routine, mechanical, well-specified

Use for:
- Git mechanics: rebases, cherry-picks, branch cleanup, routine merges
- Running and fixing unit tests, lint/format passes
- Script execution, dependency bumps, boilerplate/CRUD scaffolding

If a "routine" task turns out to need a design decision mid-way (schema
change, a new dependency with real tradeoffs, ambiguous test intent), stop
and flag for Claude rather than deciding it inline.

## Escalation runs both ways

- A routine agent hits ambiguity → escalate up to Claude, don't guess.
- Claude has a large mechanical task queued (e.g. "run the full test suite
  and fix failures," "summarize these 40 PDFs") → delegate down instead of
  spending session budget on it directly.

## Shared rules, all agents, all repos in this workspace

- Never `git add -A` / `git add .` — another agent may share this working
  directory. Stage explicit paths only.
- Check `git status` before staging or committing; don't assume a broad add
  is safe.
- Don't copy this file's content into `CLAUDE.md` / `GEMINI.md` /
  `AGENTS.md` — link to it and add only agent-specific notes locally.

## Open question

Whether Gemini Antigravity and Codex auto-discover a repo-root `GEMINI.md` /
`AGENTS.md` when a session is launched from a subproject directory (the way
Claude Code reads CLAUDE.md relative to cwd) is unconfirmed as of
2026-09-23 — check each tool's docs. If a tool only reads its context file
from cwd rather than walking up, root-only `GEMINI.md`/`AGENTS.md` won't be
seen from inside `academic-rag-model/` or `academic-hub/`, and per-subproject
copies would need to be added.
