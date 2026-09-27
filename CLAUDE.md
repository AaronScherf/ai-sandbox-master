# CLAUDE.md

Monorepo. Almost all work happens in `ai-sandbox/academic-rag-model/` (Python pipelines) or `ai-sandbox/academic-hub/` (the content vault they populate); each has its own CLAUDE.md. `personal-website/` has its own too. Stay inside the subproject I name; don't explore siblings unless the task crosses them.

## Token efficiency
- Read only what the task needs: Grep/Glob first, then targeted line ranges. Don't read a whole file over ~500 lines unless the task genuinely requires all of it.
- Don't open PDFs, images, `.obsidian/`, or generated JSON (`seen.json`, `_metadata.json`, `.index/` cards) unless I ask or the task is about that file.
- Status docs under `academic-rag-model/docs/status/` and `docs/superpowers/` are long (up to ~70KB). Grep for the relevant heading/section instead of reading them whole.
- Keep responses brief: no restating the plan, no recap of unchanged code, no closing summary beyond what changed and how it was verified.
- For broad multi-directory searches, use an Explore subagent (model: haiku) and bring back conclusions, not file dumps.
- If a task will need very large reads or a long debug loop, say so in one line before starting.

## Git

Before any write, follow [the worktree procedure](docs/WORKTREE_WORKFLOW.md).
Use a dedicated `claude/<task>` branch and worktree; launch the session there
and keep shell and IDE edits inside it. Main is for the designated integrator.
- Stage explicit task paths only, never `git add -A` / `git add .`. Preserve unrelated changes encountered during handoff; one writer per worktree still applies.
- This repo is public on GitHub. Never commit secrets (`ai-sandbox/.env`) or copyrighted source material; the root `.gitignore` comments explain the IP-driven exclusions.

## Multi-agent routing

Gemini (Antigravity) and Codex also work this repo. See
[the routing convention](docs/AGENT_ROUTING.md): Gemini defaults to existing
pipeline operation, documentation review, website writing, and large-context
reads; Codex handles code maintenance, tests, and Git mechanics; Claude handles
architecture, technical design tradeoffs, and code/security review.

## Bug report intake

Follow [reviewer responsibilities](docs/BUG_HANDOFF.md#reviewer-responsibilities).
