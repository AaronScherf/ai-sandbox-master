# Codex handoff: does a blocked Obsidian Git backup fail visibly? (TODO-0096, last open point)

From Claude, to Codex. Written 2026-11-18. Use a `codex/<task>` branch and worktree per `docs/WORKTREE_WORKFLOW.md`; stage explicit paths. Do not land; the owner lands.

## Question to answer

The pre-commit binary guard hook is enabled and verified at the git CLI level. Still undecided: when the hook **blocks** a commit that Obsidian Git (desktop) makes, does the user see the failure, or does the plugin retry silently or swallow it? A silent block would mean backups stop with no warning.

## Facts already established (2026-11-18, do not re-derive)

- `git config core.hooksPath` is `.githooks` in the shared repo config (`C:/Users/theaa/ai-sandbox-master/.git/config`). It covers every worktree of the monorepo.
- `.githooks/pre-commit` runs `python -m tools.guard_binaries --staged` from `ai-sandbox/academic-rag-model/`. A scratch worktree refused a staged hub PDF and accepted a `.md` commit on 2026-11-11.
- The plugin is installed: `ai-sandbox/.obsidian/plugins/obsidian-git/` tracks `main.js`, `manifest.json`, `styles.css`. Its `data.json` (settings) is **not** tracked, so whether it is enabled and how it is configured on this machine is unknown.
- Design basis: `docs/superpowers/specs/tools/2026-11-03-hub-binary-guard-design.md`, layer 3 and open question 3. Desktop obsidian-git runs the git CLI, so the hook applies. Mobile uses an in-process git and ignores hooks; the tablet repo is `academic_notes/`, a separate repo, out of scope.
- The hook only exists in the **monorepo's** config. `academic_notes/` is a different repo with its own config. Confirm which repo the desktop vault's Obsidian Git commits into before testing; if it is `academic_notes/`, the hook does not apply there and the finding is "not covered", which is itself the answer.

## Part 1 (do this): static review, no GUI needed

1. Do not open `.obsidian/` JSON settings. Read only `ai-sandbox/.obsidian/plugins/obsidian-git/main.js`; grep for how a failed `commit` is handled: a `Notice`, an error log, a status-bar state, auto-retry, and whether the auto-backup interval loop continues or stops after a failure.
2. In a throwaway repo (temp dir, not the monorepo) with the same hook installed, stage a PDF and run `git commit`. Record the exit code and stderr, since that is what the plugin receives.
3. State, from the plugin code, what the user sees for that exit code and stderr. Quote the lines you rely on.

## Part 2 (owner, desktop): GUI confirmation, only if Part 1 is not conclusive

Codex cannot drive Obsidian. If Part 1 leaves doubt, write 5 numbered steps for the owner: stage a throwaway `.pdf` under the hub in a scratch copy, trigger Obsidian Git's backup, note whether a notice appears and whether it retries. Do not run this against the live vault.

## Deliverable

A short report (under 40 lines) in `docs/status/` or as an addendum to this file's branch, with: (a) the repo Obsidian Git commits into, (b) what the plugin does on a blocked commit, with quoted code, (c) verdict: **visible failure / silent failure / not covered**, (d) if silent or not covered, the smallest fix (for example a hook message the plugin surfaces, or a second guard), without implementing it.

Then update the TODO-0096 entry in `docs/trackers/academic_hub_to_do.md` per the project's to-do rule: remove "Still open" if the verdict is visible failure; otherwise open a new pending to-do for the fix.

Constraints: no API calls, no writes to the live vault or hub, no edits to `ai-sandbox/.obsidian/`.
