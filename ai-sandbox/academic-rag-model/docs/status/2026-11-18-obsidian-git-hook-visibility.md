# TODO-0096: blocked Obsidian Git backup visibility (2026-11-18)

## Repository and scope

- The `ai-sandbox/` vault is in the monorepo. Its Obsidian Git backup commits exist through 2026-10-04 (`0c3d9934`). This is the vault targeted by the hub guard design, and its commits inherit the shared `.githooks` setting.
- The laptop also uses `ai-sandbox/academic-hub/academic_notes/` as a separate Obsidian vault and Git repository (2026-09-21 and 2026-09-26 Obsidian sync status notes). Its backup commits continue through 2026-11-11 (`d17d6d5`). `git config --get core.hooksPath` returned no value there. The monorepo hook does not cover these commits.
- The live vault's enabled-plugin and notice settings remain unverified; `.obsidian/` settings were not read. The separate scratch-vault desktop behavior was observed on 2026-11-22.

## Static plugin review and isolated Git probe

- Only the tracked `ai-sandbox/.obsidian/plugins/obsidian-git/main.js` was read. Desktop manager constructs `simple-git` with `baseDir:a` at the vault path (line 152), and calls `this.git.commit(...)` (line 155).
- In a throwaway repo with the same hook and guard script, a staged `ai-sandbox/academic-hub/probe.pdf` made `git commit` exit **1**, stdout `''`, stderr `R1: ai-sandbox/academic-hub/probe.pdf -- hub binary; keep it in academic_resources/ untracked, or add it to tools/guard_binaries_allow.txt with a reason\n`.
- The plugin's commit handler catches the failed operation: `catch(o){return this.displayError(o),!1}` (line 366). `commitAndSync` skips its push when `commit(...)` is false (line 366).
- `displayError` uses `this.settings.showErrorNotices&&new ke.Notice(n.message,i)`, always calls `console.error(...)`, and sends `n.message` to the status bar **if present** (line 377). Defaults are `showErrorNotices:!0` and `showStatusBar:!0` (line 105). The settings UI can turn error notices off (line 161).
- Automatic backup schedules the next interval in its task callback: `e!==!1&&(this.saveLastAuto(new Date,"backup"),this.startAutoCommitAndSync())` (line 174). The commit handler returns `!1` to `commitAndSync`, but the automatic task returns `!0` after awaiting it; thus the timer continues, with no immediate retry loop or permanent stop.

**Verdict: visible failure for the outer `ai-sandbox/` vault in the tested scratch setup; not covered for the separate `academic_notes/` repository.** The outer-vault commit was refused with a popup Notice and the automatic backup kept retrying. Backups remain blocked until the PDF is unstaged. The live vault's notice setting was not checked. Nested-vault protection would require a hook/guard in that repository after its binary policy is decided (TODO-0101).

## Desktop scratch-vault probe (owner, 2026-11-22)

- Obsidian Git 2.39.0, with the hook and guard copied into the scratch vault; a hub PDF was staged. Python was on Obsidian's PATH, so the guard ran.
- **Commit-and-sync** showed a popup Notice with a shortened `R1: ... hub binary` message. The console contained the full guard message.
- The one-minute automatic backup retried and hit the same error each time. Its stack trace showed each run rescheduling the next.
- The PDF was never committed. This is an observed scratch-vault result, not an observation of the live vault's settings or behavior.
