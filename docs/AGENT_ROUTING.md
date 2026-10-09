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
- Architectural decisions and substantive technical design tradeoffs
- Code review / security review
- Anything that depends on prior decisions or open threads — Claude holds
  cross-session memory in this workspace; Gemini and Codex sessions start
  cold every time
- Technical or product-design decisions escalated by another agent

## Gemini — pipeline operation, documentation, writing, large-context reading

Gemini in Antigravity is the default for:

- Live Socratic tutoring sessions run through `agent/tutor` (start with its `bootstrap` command and follow the
  printed contract); `agent/rag` is for one-off grounded lookups and `/draft` diagnosis, not tutoring sessions.
- Using existing pipelines: live RAG study sessions, resume tailoring for a
  supplied job opportunity, conversions, indexing, and other documented runs.
- Reviewing project documentation for accuracy, clarity, and consistency;
  writing or revising documentation within established behavior.
- Writing and revising project pages and blog posts on the personal website,
  including organizing source material and improving prose in the user's voice.
- Large-context reading: many-file audits, long status-doc/PDF/transcript
  synthesis, full-codebase searches, and large-log/diff triage.

Gemini can make ordinary editorial choices and select documented options
within the user's request. It preserves factual accuracy, citations, resume
claims, and the user's intent. It does not invent results or credentials.
Content drafting does not authorize publishing, deploying, or submitting
applications; act on existing authorization when it explicitly covers those.

For operational tasks, use the existing implementation and configured backend,
confirm input/output locations, and inspect generated results. Follow package
READMEs and local rules for paid batches and shared data. A Gemini-operated
pipeline can still use Ollama or another configured backend internally.

Code defects go to Codex with reproduction details; architecture, new
capabilities, schema changes, and substantive website structure/configuration
tradeoffs go to Claude. Editorial decisions alone do not require escalation.
The website is a separate repository. Its local agent guidance is supplied
by [website PR #3](https://github.com/AaronScherf/AaronScherf.github.io/pull/3).
Check that the chosen website checkout contains that guidance before using
this workflow; the monorepo PR alone does not install files into a child repo.

## Codex — routine, mechanical, well-specified

Use for:
- Git mechanics: rebases, cherry-picks, branch cleanup, routine merges
- Running and fixing unit tests, lint/format passes
- Maintenance/debugging script execution, dependency bumps, boilerplate/CRUD scaffolding

If a "routine" task turns out to need a design decision mid-way (schema
change, a new dependency with real tradeoffs, ambiguous test intent), stop
and flag for Claude rather than deciding it inline.

## Escalation runs both ways

- Gemini finds a routine code failure while operating a pipeline -> send
  Codex the command, expected/actual result, and relevant logs.
- Gemini or Codex encounters an architecture/product decision -> flag it
  for Claude rather than choosing a new design.
- Claude delegates established pipeline usage, documentation review, and
  website writing to Gemini; test fixes, Git mechanics, and maintenance to
  Codex. Large reading/synthesis tasks also default to Gemini.
- These are defaults, not restrictions on the user's explicit assignment.

## Result failures and review cases

Gemini follows [the bug handoff procedure](BUG_HANDOFF.md) for failed checks,
unexpected results, or user-reported incorrect output. It preserves evidence,
writes a local report, and prepares a case for Codex or Claude to review
against the relevant full codebase. Validators passing do not override user
feedback, and a suspected cause is not an established diagnosis.

## Shared rules, all agents, all repos in this workspace

Follow [the worktree procedure](WORKTREE_WORKFLOW.md) before writing:
one task, one branch, one worktree, one writer; integration is serialized.

- Never `git add -A` / `git add .`. Stage explicit task paths only and
  preserve unrelated changes encountered during handoff. This does not permit
  concurrent writers in one worktree.
- Check `git status` before staging or committing; don't assume a broad add
  is safe.
- Deliverables and artifacts produced during agent sessions (such as study
  guides, tutoring hints, audits, synthesized notes, and generated files) must
  be persisted to their proper repository or vault destination (e.g.
  `academic_notes/`), not left solely in temporary agent session storage.
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
