You are the Codex session that owned the `codex/evidence-map-repo` worktree. Your task is a READ-ONLY loss check. Do not edit, commit, push, or re-clone anything until you have reported to Aaron.

What happened (2026-11-08/09)
- Claude landed your branch `codex/evidence-map-repo` on `main` (rebased onto origin/main; the landed commits are the same four, with new SHAs; main is now at 0f7449c5 or later).
- The lander then stopped because it counted your still-registered worktree as in-progress work (your branch tip bca7753b still held the pre-rebase commits). Claude removed the worktree with `git worktree remove` (no --force). Git does not refuse over IGNORED files.
- The worktree contained the evidence-map child repository as an ignored directory:
  C:\Users\theaa\ai-sandbox-master\.worktrees\codex-evidence-map-repo\ai-sandbox\research\independent-research\projects\evidence-map\
  (its own .git, remote https://github.com/AaronScherf/evidence-map.git, private). That directory was deleted with the worktree.
- Claude re-cloned it from the remote into the main checkout at
  C:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\projects\evidence-map\
  at commit f34cf8e69414fc438e7746fbc315a8ba971bfe6f ("Narrow evidence map to cash transfers in compound crises"), which is the remote's main and the commit pinned in projects/repositories.json. Only committed-and-pushed state was restored.

What could have been lost (anything never pushed to the remote)
- Uncommitted edits to tracked files (README.md, protocol.md, project.yaml, synthesis.md, evidence/manifest.yaml, notes/, and so on).
- Local commits on any branch that were never pushed.
- Ignored or untracked local content: cache/ (sources, text), .env, .venv, outputs/ run products, scratch files, extraction records if they were git-ignored.
- Stashes (the stash stack is shared across worktrees, so `git stash list` in the main checkout still shows entries made inside the child repo ONLY if they were made in the outer repo; the child repo's own stash died with its .git).

What to do
1. From your own session transcript or logs, list every file you created or edited inside projects/evidence-map/ after the remote's last push, and every command you ran there (git commit, uv run reprokit ..., evidence-run, verify-sources, migrate-review, fetches). Note timestamps.
2. Compare against the re-cloned repo: `git -C <main checkout path>\...\projects\evidence-map log --oneline -5`, and diff each file you edited against what is on disk now. Also check `git reflog` is empty (it is a fresh clone, so any local-only commit is gone).
3. Check whether anything you produced there is recoverable elsewhere: status docs or handoffs you wrote in the monorepo, the landed handoff doc `2026-11-08-evidence-map-study-catalogue-design-handoff.md`, copies in your scratch directories, or the Windows Recycle Bin (git worktree remove normally does not use it, so do not count on it).
4. Report to Aaron, in this form:
   - Lost: files/commits that existed only in the deleted directory, with what they contained.
   - Not lost: everything confirmed present on the remote or in the re-clone.
   - Unknown: anything you cannot confirm either way.
   - Recommended recovery: re-create from transcript only after Aaron approves, in a dedicated worktree or directly in the re-cloned child repo as a normal commit. Do not push without approval.
5. Do not delete or move the re-cloned directory, do not run `git worktree` commands against other sessions' trees, and do not force anything.

Safety
- Keep private data, credentials, PDFs and raw datasets out of logs and prompts.
- If the evidence-map project holds a Zotero API key or similar in .env, that file is gone too; do not paste its contents anywhere. Tell Aaron which variable names it needed so he can recreate it.
