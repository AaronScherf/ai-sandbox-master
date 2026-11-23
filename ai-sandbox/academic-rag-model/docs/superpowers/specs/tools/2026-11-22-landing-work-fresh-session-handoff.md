# Fresh-session handoff: landing speed and guard follow-ups (2026-11-22)

Goal of the work: the owner's daily changes are mostly non-code (transcriptions, notes, hub data). A landing check should not run the full 15-minute suite for those. State on `main` (`6e017b91`, in sync with `origin/main`).

## Done and landed (do not redo)
- Dependency-allowlist policy and `OUTSIDE_TEST_INPUTS` (`79be34ba`); import-closure test selection in `tools/impact_selection.py` (`8b7a5cec`). Rules and measured numbers: `docs/WORKTREE_LANDING.md`, and the "Implementation status" section of `docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md`.
- Obsidian Git visibility: desktop probe done 2026-11-22. A blocked commit shows a Notice and the automatic backup retries; the PDF is never committed. Report: `docs/status/2026-11-18-obsidian-git-hook-visibility.md`. TODO-0096 closed.
- Merged worktrees retired 2026-11-22. Scratch vault deleted.

## Remaining tasks, in order
1. **Codex follow-ups, not started:** `docs/superpowers/specs/tools/2026-11-18-landing-followups-codex-handoff.md`.
   - Part B (TODO-0095): `land_branch` must judge a branch by `main`'s `guard_binaries`, not the branch's own copy. Call sites: `check_range(worktree, MAIN_BRANCH)` in `_run_check` and `_run_land`.
   - Part A remainder: `land_branch full-main` (full suite on `origin/main` in a scratch worktree), logging `scheduled_full`, shown in `tools.landing_metrics`. The owner decides whether to schedule it; document Task Scheduler, do not create it.
   - Both edit `tools/land_branch.py` and its test file: one branch, B then A. This is guard code, so the owner reviews it before landing.
2. **TODO-0100:** make the tests that read `hub_config.json` hermetic, so changing hub config stops selecting about 165 test files. Large; after item 1.
3. **TODO-0101:** decide how the separate `academic_notes/` vault gets the binary guard (the monorepo hook does not cover it).
4. **Wording refresh:** TODO-0093 and TODO-0094 still say `RETEST_OUTSIDE_PATHS` (now `OUTSIDE_TEST_INPUTS`). In TODO-0094, item (3) is already handled.
5. **Real-use check:** on the next transcription, confirm the landing check reports `outside_project_only` or `skipped`, not a full run.

## Known limits (accepted)
Static analysis misses run-time imports and subprocess-only tests; shared `core` changes stay wide (`core/indexer/index_card.py` selects 185 of 366 files). The scheduled full run in item 1 is the backstop. Full runs took 912 s to 1866 s, the longer one probably from concurrent sessions.

## Rules to remember
Worktree per task (`docs/WORKTREE_WORKFLOW.md`), explicit-path staging, run `tools.active_work` from `ai-sandbox/academic-rag-model/` before landing. Only the owner approves a landing, one change ID at a time. Do not mark TODOs done without evidence.
