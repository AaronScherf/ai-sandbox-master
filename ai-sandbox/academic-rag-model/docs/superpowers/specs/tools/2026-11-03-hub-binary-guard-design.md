# Hub binary guard (block PDFs and SVGs under `academic-hub/`): design

**Status:** proposed for review. No code, hook or untracking has been done. Owner: Claude (design); Codex implements per `docs/AGENT_ROUTING.md`.
**Context:** `docs/MONOREPO_SPLIT_EVALUATION.md` (branch `claude/monorepo-split-handoff`), decision 4: block PDFs and SVGs for good. History is not purged (owner decision), so this only stops new content.

## Problem

`.gitignore` already ignores `academic-hub/academic_resources/**/*.pdf` (line 77) and the textbook PDFs, yet 92 PDFs, 13 SVGs and 11 PNGs are tracked under `academic-hub/`, and the pack holds 192 MB of them. Ignore rules do not stop three paths:

| Path into the repo | Example in history | Why `.gitignore` fails |
|---|---|---|
| Deliberate agent or owner commits that stage the files | `a8fd07e0` "migrate math-camp heavy sources", `1938b63d` "Stage microeconomics slide sources" | `git add -f`, or the file was added before the rule |
| Obsidian Git auto-backups | 5 "vault backup" commits touched `academic-hub` (for example `c17c1264`) | The plugin stages whatever changed; the vault root is `ai-sandbox/` |
| Files tracked before the rule existed | all 92 current PDFs | Ignore rules never untrack |

SVG has no ignore rule at all (Excalidraw exports are 8-19 MB each).

## Decision: guard at three layers, one shared checker

One script, `tools/guard_binaries.py`, decides pass or fail. Three callers use it, from the cheapest to the strictest:

1. **Landing check (authoritative).** `land_branch check` and `land` run the guard on the paths the branch adds or modifies relative to `main` (`git diff --name-status --diff-filter=AM main...HEAD`). A violation refuses the landing with the file list. Only the user lands on `main`, so this covers every agent branch regardless of how it committed.
2. **Pre-commit hook.** A tracked `.githooks/pre-commit` runs the guard on staged paths. Enabled per clone and per worktree by `git config core.hooksPath .githooks` (set once by `workspace_generator.sh`; worktrees share the config). It catches mistakes before they enter a branch. Hooks can be skipped with `--no-verify`, which is why layer 1 is the authority.
3. **Obsidian Git.** Desktop obsidian-git runs the git CLI, so the pre-commit hook applies there. Mobile obsidian-git uses an in-process git and ignores hooks; the tablet repo is `academic_notes/`, which is a separate repo and out of scope. Verify on desktop that a blocked backup fails visibly instead of silently retrying (see open question 3).

Plus a `.gitignore` addition for the hub only: `ai-sandbox/academic-hub/**/*.svg`, `*.png`, and `*.pdf` for the whole hub (not just `academic_resources`). Cheap, visible in `git status`, and keeps agents from staging them by accident.

## Rules the checker enforces

Applied to added or modified paths only, never to deletions (so the untracking commit passes).

| Rule | Blocks | Exceptions |
|---|---|---|
| R1: hub binaries | any `*.pdf`, `*.svg`, `*.png`, `*.jpg`, `*.jpeg`, `*.epub`, `*.docx`, `*.pptx` under `ai-sandbox/academic-hub/` (case-insensitive) | `ai-sandbox/academic-hub/obsidian_styles/**` (CSS only today, listed so a future icon is a conscious decision); an explicit allowlist file |
| R2: size | any added or modified blob over 1 MB anywhere in the repo | allowlist file |
| R3: textbook text | any file under a `textbooks/` or `textbooks-and-papers/` folder that is not `processed_outputs/**/*.json` metadata, and any `*.rag.md.bak` anywhere | allowlist file |

The allowlist is `tools/guard_binaries_allow.txt`, one path or glob per line with a mandatory reason comment. Adding to it is a reviewed change, visible in the landing summary. Start empty.

Not covered by R1: the 7 tracked `Tailored_Resume.pdf` files under `research/` and `academic-rag-model/.codex-validation-run/` (resume outputs, small, not third-party). R2 still bounds them.

## Untracking the existing files

The guard does not require untracking, but R1 would flag any later modification of a tracked PDF. One cleanup commit finishes the job:

1. Owner's main checkout already shows the deletions uncommitted. That change set belongs to its owner; do not touch it from a guard branch.
2. After it lands (or in the same change), `git rm --cached` any tracked file R1 matches, leaving the working copies in place, and commit as `chore(hub): untrack heavy sources`.
3. Do not rewrite history. Old objects stay in the pack (accepted).

## Behavior details

- Output names the rule, the path and the fix: "R1: `academic-hub/.../x.pdf` is a hub binary. Keep it in `academic_resources/` untracked, or add it to the allowlist with a reason."
- The guard reads paths from git, not the working tree, so it is fast and the same in every worktree.
- Renames are checked by the new path.
- `land_branch` records `guard: passed|failed` in the log for the metrics.

## Tests

- Unit tests with a temporary git repo: added PDF under the hub fails; added PDF under `research/` passes R1 but fails R2 if over 1 MB; deleting a tracked PDF passes; modifying one fails; allowlisted path passes; `.rag.md.bak` fails R3; uppercase `.PDF` fails.
- Landing test: a branch adding a hub SVG is refused by `check` with the path listed.
- Hook test: staged hub PDF makes the hook exit non-zero (run the script directly, not through git).

## Open questions

1. Is 1 MB the right R2 threshold? The largest legitimate tracked files today should be listed first to avoid false positives (for example the vendored viewer JS under `agent/concept_graph/viewer/vendor/`).
2. Should small PNGs (the 11 "Pasted image" files at `ai-sandbox/` root, outside the hub) be blocked as well, or only the hub?
3. Does obsidian-git on desktop use the CLI with hooks enabled in this vault? Check `ai-sandbox/.obsidian/plugins/obsidian-git/data.json` settings (not read in this audit; it is under `.obsidian/`).
4. Should the hook be installed automatically by `workspace_generator.sh`, or documented only? Recommend both, since a forgotten setup silently disables layer 2.
5. Who runs the untracking commit, given the pending deletions in the main checkout belong to the structure-fix work?
