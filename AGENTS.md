# AGENTS.md

Monorepo. Work happens in `ai-sandbox/academic-rag-model/` (Python
pipelines) or `ai-sandbox/academic-hub/` (the content vault they populate);
each has its own `CLAUDE.md` with commands, scope, and gotchas that apply
regardless of which agent is running — read the relevant one before editing
there. See `docs/AGENT_ROUTING.md` for the full multi-agent convention.

## What Codex is for in this workspace

Routine, well-specified, mechanical work: git mechanics (rebase,
cherry-pick, branch cleanup), running/fixing unit tests, lint/format passes,
script execution, dependency bumps, boilerplate. If a task turns out to need
a design decision mid-way, stop and flag for Claude rather than deciding it
inline.

## Git

Another agent may share this working directory: stage explicit paths, never
`git add -A` / `git add .`.
