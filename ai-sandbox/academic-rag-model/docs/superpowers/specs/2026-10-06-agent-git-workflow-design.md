# Agent Git Workflow Design

**Status:** Approved by the user 2026-10-06 (committed as 0bd8e38). Implementation tracked in the plan of the same date.
**Date:** 2026-10-06
**Scope:** how Claude, Codex, and Gemini agents land work on `main` in this monorepo.
**Source brief:** `ai-sandbox/academic-rag-model/docs/trackers/academic_hub_to_do.md`, section "Git Workflow Between Agents".

## 1. Goal

Land agent work faster and with fewer collisions, without weakening the safety rules in `docs/WORKTREE_WORKFLOW.md` and the root `CLAUDE.md`. Success is measured by the metrics in section 7, not by assertion.

## 2. Decided

These were settled with the user during the brainstorm (2026-10-05 and 2026-10-06).

1. **Who lands on `main`: the user only.** Agents never merge or push to `main` on their own. At the end of a session, an agent asks the user in one message whether it may commit the branch, then whether it may merge and push. Approval covers one named commit SHA. If the SHA changes, the agent asks again. Approval does not carry over to later sessions or branches.
2. **Merge style: rebase onto `main`, then `git merge --ff-only`.** This replaces the `--no-ff` rule in `WORKTREE_WORKFLOW.md`. Rebasing is allowed only on a branch that is exclusively owned and unpublished (the existing rule). A branch is not pushed before landing.
3. **Direct-to-`main` lane, phase 1:** the to-do tracker only (existing exemption in the root `CLAUDE.md`). Everything else follows the branch-and-worktree path until the lanes in section 4 are approved.
4. **Docs lane:** `docs/status/`, `docs/superpowers/`, and READMEs may go direct to `main` with explicit paths, but only when no other session has uncommitted changes to that file. Anything else goes through a branch. Shared logs are append-only.
5. **Obsidian auto-backup:** accepted for now. The user has reduced the sync frequency in the Obsidian Git plugin, which the user reports cuts sweeps but does not change the target branch (the plugin offers no branch setting). Backups still land on `main`. The sweep count stays in the metrics (section 7) to judge whether this is enough.
6. **Generated output (`.index/*.json`, site and transcription outputs):** treatment unchanged. Some of these feed the website and notes transcription, so they stay tracked and are committed as they are today. No new single-writer rule; revisit only if conflicts appear.
7. **Test policy at landing:** a changed-package subset while iterating; the full suite once per landing as the gate. Measure `pytest-xdist` before adopting it.
8. **Claims for shared packages:** no claims file. Branch naming (`claude/`, `codex/`, `gemini/`) plus the active-work report at pre-check. A branch touching `core/indexer/` or `core/env/` is flagged to the user before the commit ask.
9. **Commit ask:** one combined message (commit, merge, and push together). Root `CLAUDE.md` requires asking before any commit, so no standing permission for branch commits.

## 3. Landing flow (proposed)

For a branch `claude/<task>`, `codex/<task>`, or `gemini/<task>`, in its own worktree:

1. **Pre-check:** the worktree is clean and the branch has a single owner. Record `git status --short`, `git log -3`, and the branch name.
2. **Rebase:** `git rebase main` inside the worktree. Resolve conflicts with the design rule from the worktree doc: preserve both tasks' intent, and send design ambiguities to Claude.
3. **Checks:** run the tests for the changed packages. The full suite (about 107 s on this machine) runs before landing. A changed-package subset is enough while iterating (decision 7).
4. **Overlap report:** compare the branch against its merge-base (not against the branch tip) with the main checkout's uncommitted files. Also check other open worktrees for overlapping paths, especially shared packages (`core/indexer/`, `core/env/`).
5. **Ask the user:** one message with the branch, the commit SHA, the changed paths, the test result, overlaps, and known risks. Two yes/no questions: may I commit, and may I merge and push. Each agent also states whether it did the rebase or re-ran checks, since that is the cleanup this design is meant to reduce.
6. **Land on yes:** `git merge --ff-only <branch>` in the main checkout, only if that checkout's `git status --short` is unchanged. Then `git push`. Verify the result with `git log -1`.
7. **Retire** the worktree and branch only as the existing retirement procedure says.

Steps 1 to 4 are a script candidate (see section 5). The script never merges or pushes.

## 4. Lanes (open for approval)

| Lane | Paths | Route |
|---|---|---|
| Code | `core/`, `pipelines/`, `agent/`, `tests/`, tools | Worktree, branch, landing flow |
| Docs | `docs/status/`, `docs/superpowers/`, package READMEs | Direct to `main` with explicit paths, no test run, when no other session has uncommitted changes to the file (decision 4) |
| To-do tracker | `docs/trackers/academic_hub_to_do.md` | Direct to `main` (existing exemption) |
| Generated vault and index output | `.index/*.json`, pipeline outputs under `academic_notes/` | Unchanged from today (decision 6) |

## 5. Tooling (proposed, not built)

Ordered by expected payoff. Each item is a separate implementation task.

1. **Landing helper** covering steps 1 to 4 of section 3. It prints a summary and never merges or pushes.
2. **Test speed-up:** test `pytest-xdist` (`-n auto`), measured on this machine before adoption. The current ~25 s figure in the brief is a guess and must not be used as a baseline.
3. **Active-work report:** for each worktree, list changed files against its merge-base and flag overlaps in shared packages.
4. **Worktree lifecycle helper:** list merged or idle worktrees as retirement candidates. It never removes a worktree on its own. It also prints the `--root` and `PYTHONPATH` needed to run a pipeline in a worktree against the live vault (the workflow doc currently forbids junctions; this helper avoids the manual steps).
5. **Landing log:** one line per landing, appended to a log file (location to decide), recording rebase needed, checks re-run, and the time from branch cut to landing. This feeds the metrics in section 7.
6. **Cross-repo land helper** for `academic_notes/` plus monorepo index output. Lower priority; only needed once the vault lane is decided.

## 6. Open questions

Decisions 4 to 9 in section 2 settled the earlier open items. Still open:

1. **Pipeline write location from worktrees:** worktree-local corpus (current policy) or live vault (what real validation needs)? Proposed: tests always use worktree-local fixtures. Pipelines that change the live corpus run only from the main checkout, or with `--root` pointed at the live vault by whoever integrates; the helper prints the exact command. Paid Gemini runs still need the user's go-ahead. This decides whether the helper in section 5.4 is needed.
2. **Obsidian auto-backup target branch:** the plugin offers no branch setting, so this is a follow-up only if the metrics show sweeps still block landings.

## 7. Metrics

Baseline (git only, read-only), window 2026-07-14 to 2026-10-05, 908 commits on `main`: 64 merge commits, 8 `vault backup:` commits, 4 `todo:` commits, 2 revert or fixup commits, and 11 of the last 300 commits touching three or more top-level areas.

Measured after implementation, over an equal-length window:

- **Sweeps:** `vault backup:` commits on `main`, and direct-to-`main` commits outside the docs and tracker lanes.
- **Merge friction:** merge-tree conflicts at landing, and reverts or fixups within a few days of a landing.
- **Branch hygiene:** worktree and branch counts; merged-but-not-retired branches.
- **Time to land:** days from branch cut to landing.
- **Agent cleanup:** from the landing log (section 5.5): rebases needed, checks re-run, and re-asks.
- **Tokens:** Claude sessions only, from session transcripts. Codex and Gemini are out of scope for now.

Compare per landing, not raw totals. The work changes between periods, so results show a trend, not cause.

The metrics script is read-only, lives in the scratchpad (outside the repo), and runs only `git log`, `git rev-list`, `git worktree list`, and `git merge-tree`.

## 8. Guardrails (unchanged)

- Stage explicit paths only. Never `git add -A` or `git add .`.
- Never print or commit `ai-sandbox/.env`.
- No force-push, `reset --hard`, or `clean`.
- Never remove another agent's worktree or branch.
- Commit or push only when the user asks, and only with the approval described in section 2.
- The monorepo is public on GitHub. Check the root `.gitignore` before committing.
- Changes to `WORKTREE_WORKFLOW.md` take effect only for sessions told to re-read them. Running agents must be told.

## 9. Out of scope

- Changing merge rules or tooling before this spec is approved.
- Metrics for Codex and Gemini token usage.
- The Obsidian plugin's settings, unless the user supplies them.
- Anything in `academic_notes/` that is not an output of the landing helper.

## 10. Next step

On approval of this spec, the next step is an implementation plan (writing-plans), then implementation in a separate `claude/` worktree. Routing: design decisions stay with Claude; the mechanical landing script and test changes go to Codex, per `docs/AGENT_ROUTING.md`.
