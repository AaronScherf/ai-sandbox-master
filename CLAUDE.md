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
- Landing is blocked when another open branch changes the same tracked file (the check reports "Overlaps"; the overlap is symmetric). Keep one set of shared docs (specs, plans, handoffs) on exactly one branch; never copy another branch's docs into yours. Run `tools.active_work` before starting and before asking to land, and resolve any overlap first.
- Start each task branch from the latest `main`, and install `requirements.txt` into the shared `.venv` (`.venv\Scripts\python.exe -m pip install -r requirements.txt`) before the first landing check; a missing package fails the whole check.
- A landing check that fails on a test unrelated to the branch: run that test alone on `main` and on the branch, and report both results; do not land on a failed check or work around `land`. Re-run the check (a clean re-run is the only way to a passing change ID). Approval covers one change ID, so name the ID, paths, overlaps and the `git push origin main` in a single ask.

## Pending to-dos

When I say "add this as a pending to-do" (or "add to pending", "put it on the to-do list"), record it right away without asking first, and do not start the work. Append one bullet to [`ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md`](ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md):
- Don't read the whole tracker (it is long). Grep `^## ` for its headings, then read only the target section.
- Put it under the matching `## <subproject>` heading (e.g. `## Notes Transcription`, `## Textbook Conversion`). If none fits, add a new `##` section directly under the file's title.
- Write it so someone without this conversation can act on it: what and why, the files or functions involved, and any approach or decision already reached. Aim for ~800 characters; put longer evidence in a status doc and link it. End with `(added YYYY-MM-DD)`.
- Reply with one line naming the heading used.
- **Exempt from the worktree rule.** Make this edit directly in the main checkout, on `main`, without creating a worktree or branch. Stage only that one file by path (never `git add -A`), commit it to `main` with a message starting `todo:`, and leave everything else in the checkout untouched. Standing authorization for this single file only; any other change keeps the worktree procedure.

## Reviewable documents

Whenever Claude asks me to review a document (a spec, plan, status doc, or
any other file), present a clickable link to it, not just the path. A
committed file not yet pushed gets a `file://` link to its absolute local
path; a file already on a pushed branch/PR can instead link to its GitHub
URL. Do this without being asked each time.

## Multi-agent routing

Gemini (Antigravity) and Codex also work this repo. See
[the routing convention](docs/AGENT_ROUTING.md): Gemini defaults to existing
pipeline operation, documentation review, website writing, and large-context
reads; Codex handles code maintenance, tests, and Git mechanics; Claude handles
architecture, technical design tradeoffs, and code/security review.

## Citing literature

Applies to anything Claude writes or revises that cites literature: research notes, handoffs, reviews, website pages. Reference: [reference checker README](ai-sandbox/academic-rag-model/docs/reference-checker/README.md).
- Take identifiers (DOIs, URLs) and bibliographic details from a registry lookup or a source file, never from memory.
- Give every citation the work's title. Find the work in a registry by title and authors, then take its DOI from that record; never fill in a title by reading a DOI's record.
- Before handing off, run `python -m tools.reference_review raise <note>` from `ai-sandbox/academic-rag-model/`. Fix every defect, and report the counts along with any items left for review.
- Never write `[source-verified]`, `[REGISTRY-MATCHED]` or a similar tag yourself; only the checker and the user's review decide that.
- When the queue has open items, sync the review page (`https://claude.ai/artifact/EQM9L22JbowiAGMfx8jUQe`) and apply decisions with `reference_review apply`.
- A matched DOI says nothing about whether the paper supports the claim. Read the paper before quoting a finding from it.
- The landing gates enforce this for Markdown under `ai-sandbox/research/` through `tools.land_branch` and website `content/` through `tools.land_website`.

## Bug report intake

Follow [reviewer responsibilities](docs/BUG_HANDOFF.md#reviewer-responsibilities).
