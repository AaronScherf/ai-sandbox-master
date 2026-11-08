# Repo hygiene and hub binary guard: handoff for a worktree session

Written 2026-11-03. A brief, not an approved plan: confirm scope with Aaron before building. Nothing here is built.

## Goal

Stop heavy and copyrighted files from entering this public repo, finish untracking the ones already there, and tidy the leftovers from the monorepo-vs-split evaluation. **No history purge** (owner decision); old objects stay in the pack.

## Read first

| What | Where |
| --- | --- |
| Split evaluation (findings, owner decisions, Update 3 = decided scope) | `docs/MONOREPO_SPLIT_EVALUATION.md` on branch `claude/monorepo-split-handoff` (not on `main`) |
| Guard design (rules R1-R3, three layers, tests, open questions) | `ai-sandbox/academic-rag-model/docs/superpowers/specs/tools/2026-11-03-hub-binary-guard-design.md` on branch `claude/hub-binary-guard-spec` (commit `8d09ca4a`, not on `main`) |
| Landing-speed design (also edits `tools/land_branch.py`) | `ai-sandbox/academic-rag-model/docs/superpowers/specs/tools/2026-11-03-landing-check-speed-design.md` (on `main`) |
| Worktree procedure | `docs/WORKTREE_WORKFLOW.md` |

## Task A: untrack the heavy sources (do first)

State at `origin/main` (2026-11-03): `git ls-files ai-sandbox/academic-hub/academic_resources` shows 92 PDFs, 13 SVGs, 11 PNGs, 4 `*.bak` and some textbook `processed_outputs` json. History keeps them regardless.

**Caution, check before touching:** Aaron's main checkout has about 91 tracked files **deleted from disk** (27 PDFs, 13 SVGs, 31 json, `*.bak`, `.do`, `.dta`, `.jpg`, ...), uncommitted. Those are working-copy deletions, not `git rm --cached`, so the local copies may be gone. That change set belongs to its owner (the structure-fix work): do not run `git add -u` or `git checkout` there, and ask Aaron whether those files were moved elsewhere on purpose before deciding how the untracking commit handles them.

Steps:
1. In a worktree, list what R1 of the guard would match (`git ls-files` with the extension list in the guard spec) and show Aaron the list, grouped by course.
2. `git rm --cached` those paths (keeps working copies where they exist), commit `chore(hub): untrack heavy sources`. Stage explicit paths only.
3. Add `.gitignore` lines for the hub (`ai-sandbox/academic-hub/**/*.svg`, `*.png`, `*.pdf`) so they stay out of `git status`.
Acceptance: `git ls-files ai-sandbox/academic-hub | grep -i -E '\.(pdf|svg|png)$'` is empty; local copies untouched; a fresh clone builds nothing from them (run the full suite).

## Task B: the guard (after A, per the spec)

Implement `tools/guard_binaries.py`, `tools/guard_binaries_allow.txt` (start empty), `.githooks/pre-commit`, the `land_branch` check/land integration, and the `workspace_generator.sh` hook setup, exactly as the spec describes, with its tests. Settle the spec's five open questions with Aaron first (1 MB threshold, small PNGs outside the hub, obsidian-git desktop hooks, auto-install of the hook, who runs the untracking). Per `docs/AGENT_ROUTING.md` Codex implements; Claude reviews.

**Coordination:** the landing-speed session is changing `tools/land_branch.py` at the same time. Rebase on its merged result, or sequence B after it lands, to avoid a conflicting rewrite of the check path. Deletions must pass the guard (so Task A's commit passes).

## Task C: small cleanups (optional, confirm each with Aaron)

From the evaluation's decided scope, each independent and small:
- Fold `ai-sandbox/trading` (one file) and `ai-sandbox/utility-scripts` (two files) into `academic-rag-model`; both inactive. `utility-scripts` reads `ai-sandbox/.env` (`textbook_analysis.py:42`).
- Fix two stale docs: the research README names `academic-rag-model/indexer/index_search.py` (now `core/indexer/`), and the utility-scripts instructions.
- Add `PAID_GEMINI_KEY` to `.env.example` (never print or commit real values).
- Track `gcp_instructions.md` and `journal_discovery_instructions.md` only after a secrets check.
- Add `reprokit` and `compound-shocks-panel` to `ai-sandbox/research/independent-research/projects/repositories.json` with commit pins, gitignore their working trees, and remove the migrated `projects/02_compound_shocks/` scaffold.
- TODO-0093 in `docs/trackers/academic_hub_to_do.md` (make two tests hermetic, delete `RETEST_OUTSIDE_PATHS`) belongs to the landing-speed work, not here.

## Constraints

Dedicated `claude/<task>` or `codex/<task>` worktree; explicit-path staging; no secrets (`ai-sandbox/.env`); never touch history or force-push; the repo is public, so nothing copyrighted goes in; core changes run `python -m tools.run_tests_chunked`; ask before any step that is hard to reverse.

Folder renamed on 2026-11-06: the historical `projects/02_compound_shocks/` links above refer to the retired scaffold; the live project is `projects/compound-shocks-panel/`.
