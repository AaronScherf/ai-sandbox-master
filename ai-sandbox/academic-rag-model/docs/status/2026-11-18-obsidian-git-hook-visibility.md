# TODO-0096: blocked Obsidian Git backup visibility (2026-11-18)

## Repository and scope

- The `ai-sandbox/` vault is in the monorepo. Its Obsidian Git backup commits exist through 2026-10-04 (`0c3d9934`). This is the vault targeted by the hub guard design, and its commits inherit the shared `.githooks` setting.
- The laptop also uses `ai-sandbox/academic-hub/academic_notes/` as a separate Obsidian vault and Git repository (2026-09-21 and 2026-09-26 Obsidian sync status notes). Its backup commits continue through 2026-11-11 (`d17d6d5`). `git config --get core.hooksPath` returned no value there. The monorepo hook does not cover these commits.
- Actual enabled plugins, settings, and the vault currently open in desktop Obsidian remain unverified; `.obsidian/` settings were not read.

## Static plugin review and isolated Git probe

- Only the tracked `ai-sandbox/.obsidian/plugins/obsidian-git/main.js` was read. Desktop manager constructs `simple-git` with `baseDir:a` at the vault path (line 152), and calls `this.git.commit(...)` (line 155).
- In a throwaway repo with the same hook and guard script, a staged `ai-sandbox/academic-hub/probe.pdf` made `git commit` exit **1**, stdout `''`, stderr `R1: ai-sandbox/academic-hub/probe.pdf -- hub binary; keep it in academic_resources/ untracked, or add it to tools/guard_binaries_allow.txt with a reason\n`.
- The plugin's commit handler catches the failed operation: `catch(o){return this.displayError(o),!1}` (line 366). `commitAndSync` skips its push when `commit(...)` is false (line 366).
- `displayError` uses `this.settings.showErrorNotices&&new ke.Notice(n.message,i)`, always calls `console.error(...)`, and sends `n.message` to the status bar **if present** (line 377). Defaults are `showErrorNotices:!0` and `showStatusBar:!0` (line 105). The settings UI can turn error notices off (line 161).
- Automatic backup schedules the next interval in its task callback: `e!==!1&&(this.saveLastAuto(new Date,"backup"),this.startAutoCommitAndSync())` (line 174). The commit handler returns `!1` to `commitAndSync`, but the automatic task returns `!0` after awaiting it; thus the timer continues, with no immediate retry loop or permanent stop.

**Verdict: not covered for the currently documented laptop `academic_notes` vault.** For a backup from the outer `ai-sandbox/` vault, the hook failure reaches the plugin and is visible as a Notice with default settings; disabling error notices can leave only the console and an optional status bar. Actual desktop visibility has not been observed. The smallest fix for nested-vault protection is a separate hook/guard installed in that repository, after deciding whether its binary policy should match the monorepo's. For the outer vault, keep error notices enabled or verify a persistent visible failure indicator.

## Owner desktop confirmation, if the outer vault is still used

1. Open a scratch **copy** of the outer `ai-sandbox/` vault in desktop Obsidian, with its own Git repo and the same hook; leave the live vault closed.
2. Enable Obsidian Git in that scratch vault and note its error-notice and status-bar settings.
3. Add and stage a throwaway `ai-sandbox/academic-hub/probe.pdf` in the scratch repo.
4. Trigger Obsidian Git's backup; record any Notice, status-bar text, and console error.
5. Wait through one backup interval; record whether it retries, then discard the scratch copy.
