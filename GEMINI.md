# GEMINI.md

Monorepo. Work happens in `ai-sandbox/academic-rag-model/` (Python
pipelines) or `ai-sandbox/academic-hub/` (the content vault they populate);
each has its own `CLAUDE.md` with commands, scope, and gotchas that apply
regardless of which agent is running — read the relevant one before editing
there. See `docs/AGENT_ROUTING.md` for the full multi-agent convention.

## What Gemini is for in this workspace

Large-context reads: summarizing or auditing many files or a full directory
tree, long status-doc/PDF/transcript synthesis, full-codebase sweeps. Report
findings; don't make design or architecture calls — flag those back for
Claude instead of deciding.

## Git

Another agent may share this working directory: stage explicit paths, never
`git add -A` / `git add .`.
