# Multi-Agent Routing Convention: Initial Design and Rollout

Summary of a single session (2026-09-23) that established a routing
convention for the three coding agents now working this workspace — Claude
(Claude Code), Gemini (Antigravity), and OpenAI Codex — and wired it into
the repo's context files. Triggered by the user adding Antigravity and
Codex alongside Claude and wanting task dispatch between them to be
deliberate rather than ad hoc, with a specific goal of keeping Claude's
per-session token budget from being spent on work another agent is better
suited for.

## Decision

Route by task shape:

- **Claude** — judgment and continuity work: new project/subproject
  initiation, brainstorming, architectural tradeoffs, code/security review,
  and anything that depends on prior decisions or open threads (Claude is
  the only one of the three with a persistent cross-session memory system
  in this workspace; Gemini and Codex sessions start cold every time).
- **Gemini** — large-context reads that don't require a decision:
  summarizing/auditing more than ~5-10 files or a full directory tree, long
  status-doc/PDF/transcript synthesis, full-codebase sweeps. Reports
  findings back rather than picking a direction.
- **Codex** — routine, mechanical, well-specified work: git mechanics
  (rebase, cherry-pick, branch cleanup), running/fixing unit tests,
  lint/format passes, script execution, dependency bumps, boilerplate.

Escalation runs both ways: a routine agent that hits a judgment call mid-task
stops and hands up to Claude instead of deciding it; Claude hands large
mechanical or read-heavy work down instead of spending session budget on it
directly. This mirrors the existing Explore-subagent-on-haiku pattern
already used inside Claude Code sessions in this repo (see root `CLAUDE.md`
token-efficiency section) — Gemini/Codex are the same idea applied across
tools instead of within one.

## Why a single canonical doc, not three copies

The convention lives in one place, `docs/AGENT_ROUTING.md` at the
`ai-sandbox-master` repo root, and `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md`
each link to it rather than repeating it. Duplicating the same content
across three files invites exactly the kind of silent drift already seen
with `academic_notes/.gitignore` (each device's Direct Git Sync plugin
stamping its own local rules over the shared file — see
`2026-09-21-obsidian-git-sync-status.md`). One doc, edited once, is the
guard against that here.

## Files touched

- `docs/AGENT_ROUTING.md` (new) — the canonical convention.
- `GEMINI.md`, `AGENTS.md` (new, repo root) — per-agent entry points, each
  pointing at `docs/AGENT_ROUTING.md` plus minimal workspace orientation
  (which subproject to work in, the shared git staging rule) so Gemini and
  Codex sessions have a baseline even though neither previously had a
  context file in this repo.
- `CLAUDE.md` (root), `ai-sandbox/academic-rag-model/CLAUDE.md`,
  `ai-sandbox/academic-hub/CLAUDE.md` — each got a short "Multi-agent
  routing" section pointing back to `docs/AGENT_ROUTING.md`.
- `ai-sandbox/personal-website/AaronScherf.github.io/CLAUDE.md` — got a
  self-contained note instead of a link, since that directory is a
  **separate public git repo**, not part of this monorepo; a relative link
  into `ai-sandbox-master/docs/` would dangle for anyone who clones just
  that repo.

## Open questions / follow-ups

- **Unconfirmed:** whether Gemini Antigravity and Codex discover a
  repo-root `GEMINI.md`/`AGENTS.md` when a session is launched from inside
  `academic-rag-model/` or `academic-hub/` (i.e. whether they walk up the
  directory tree the way Claude Code does), or only read a context file
  from the session's own cwd. If it's the latter, root-only files won't be
  seen from subproject sessions and per-subproject `GEMINI.md`/`AGENTS.md`
  copies would need to be added — noted as an open question in
  `docs/AGENT_ROUTING.md` itself.
- No enforcement mechanism exists yet — routing currently depends on
  whoever launches a session picking the right tool and each agent
  self-reporting when it should escalate. Worth revisiting if routing
  mistakes start happening in practice; a standalone dispatch layer was
  considered and deliberately deferred as premature for what is still a
  manual, single-user workflow.
