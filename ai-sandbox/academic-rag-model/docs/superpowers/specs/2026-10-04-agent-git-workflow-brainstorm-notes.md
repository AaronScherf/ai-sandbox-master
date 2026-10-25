# Agent git workflow brainstorm notes (2026-10-04)

Moved verbatim on 2026-10-25 from `docs/trackers/academic_hub_to_do.md`, section
"Git Workflow Between Agents" (TODO-0028), to keep the tracker short. Historical: written
before the brainstorm of 2026-10-05/06, whose approved outcome is
`2026-10-06-agent-git-workflow-design.md` in this folder. Several candidates below have since
shipped (e.g. `tools/land_branch.py`, `tools/active_work.py`, rebase + `--ff-only` landing);
check the design spec and `docs/WORKTREE_WORKFLOW.md` before treating any item as open.

## The problem, with evidence from the 2026-10-03/04 session
- **Landing a branch is a hand-run ritual.** Three landings (`14ca7f4` slide-aware transcription +
  subset linking, `e55402c` question resolver, `6de9095` to-do rule) each took roughly: count commits
  `main` gained since the branch point (14 both times for the big ones), `git merge-tree` conflict check,
  `git merge main` into the branch, full test suite (~107 s, 1939-2148 tests), a by-hand overlap check
  against `main`'s dirty files, then `git merge --ff-only`. One real textual conflict in three landings:
  `transcribe_excalidraw.py`, where both sides edited the same `print(...)` line (main switched it to
  `resolve_output_dir(...)`, the branch added a `return True` after it).
- **The main checkout is never clean**, yet the policy ("The integrator ensures the integration checkout
  is clean") assumes it is. It always holds the user's/Obsidian's and other agents' work: `.obsidian/*`,
  `lab_1_report.md`, `journal-articles/needs_manual_downloads.md`, `.index/*.json`, untracked
  `academic_resources/microecon/2025_class/`. So overlap with dirty files has to be computed by hand.
  Pitfall hit once: comparing `main` against the branch *tip* lists files `main` itself changed; the right
  comparison is the branch against the **merge-base**.
- **Obsidian "vault backup" auto-commits land on `main` in both repos** (monorepo log has
  `vault backup: 2026-10-01 17:00:21`; the `academic_notes` repo has `vault backup: 2026-10-03 21:50:07`),
  sweeping whatever tracked files are dirty. That made switching branches in the main checkout feel unsafe,
  so generated data was committed straight to `main` twice (monorepo `59846d7`, `academic_notes`
  `165084f`), outside the worktree rule. The Obsidian Git plugin's real settings were NOT inspected
  (`.obsidian/` is off-limits unless asked).
- **Two repos, one logical change.** The monorepo `.gitignore` (line 9) ignores
  `ai-sandbox/academic-hub/academic_notes/`, which is its own git repo (tablet sync). Resolving questions
  produced outputs in `academic_notes` and index changes (`.index/*.json`) in the monorepo, so one change
  needed commits in both. `WORKTREE_WORKFLOW.md` says child repos need their own worktrees, but real
  pipeline runs write to the live vault.
- **Shared aggregate files mix agents' work.** `.index/courses.json` held both our `microecon` change and
  another session's in-progress `econometrics` change. Committing only ours needed partial staging by
  building a blob (see snippets) because `git add -p` is not available non-interactively.
- **Worktrees lack ignored files** (`.env`, SVG sources, vault data). Running a pipeline from a worktree
  failed with a misleading "PAID_GEMINI_KEY not set" (fixed 2026-10-03: `load_dotenv_override()` now falls
  back to the main checkout's `.env`), and real runs still need
  `PYTHONPATH="$(pwd -W)" python -m <module> --root <main>/ai-sandbox/academic-hub` by hand. The policy
  forbids junctioning the live vault, which is right but leaves no easy path.
- **Docs-only changes got the same ceremony as code** (worktree, branch, merge). The to-do tracker now has
  a standing exemption (root `CLAUDE.md`, 2026-10-04); other docs do not.
- **Worktree sprawl.** 12 worktrees registered on 2026-10-04 (incl. `main`), several merged and idle:
  `claude-excalidraw-slides`, `claude-question-resolver`, `claude-todo-tracking`, `claude-status-docs`,
  the three `claude-summary-*`, and four `codex-*`. Retirement is manual per the doc.
- **Overlap found late.** Another session changed `core/indexer/index_card.py` and added `offering_links.py`
  while we were in `core/indexer`; we only saw it at merge time.
- **Tests are the other time cost.** ~107 s serial on 8 cores; `pytest-xdist` is not installed. The full
  suite was re-run many times per feature.

- **A shared main checkout plus direct-to-main edits lets other agents' commits sweep up your
  uncommitted work.** On 2026-10-04 this very section was written into the main checkout's tracker
  (uncommitted, under the new to-do exemption) and was then committed by a *different agent's* commit,
  `6d1e107` ("todo: aggregate pending to-dos..."), which was editing the same file in the same checkout.
  When the author went to commit, git reported "nothing to commit, working tree clean". In the same
  window another agent merged this session's `claude/status-docs-1004` branch (`d6f97fe`), retired its
  worktree, and pushed, all while the author was paused on a usage limit. The content ended up intact, but
  commit authorship and order are no longer traceable, and the exemption makes concurrent edits to the
  tracker more likely. Ideas to weigh: a claim step before editing a shared file; one append-only to-do
  file per agent merged later; always re-check `git status`/`git log -3` immediately before editing and
  committing a shared file.

## Existing policy to build on (and where proposals collide with it)
- Already in `docs/WORKTREE_WORKFLOW.md`: one writer per worktree, `.worktrees/` ignored, integration "one
  task at a time", retire-worktree procedure, Windows `git show` path gotcha, child-repo worktrees, "adopt
  the policy in existing sessions" (running agents do not reload guidance; they must be told).
- Collisions to resolve: the doc prescribes `git merge --no-ff` (merge commits) while rebase-then-ff gives
  linear history (the doc allows rebasing only an exclusively owned, unpublished branch); workers "do not
  merge into main unless assigned the integrator role" yet in practice the user tells an agent to merge;
  "integration checkout must be clean" is never true; "do not junction/symlink writable output dirs to the
  live vault" vs. needing real data in tests/runs.

## Candidate changes (unimplemented; roughly by payoff)
1. **Landing helper** (`tools/land.py` or `.ps1`): verify the worktree is clean, rebase (or merge) onto
   `main`, run tests (changed-path subset by default, full with a flag), compute overlap against
   `main`'s dirty files using the merge-base, then `merge --ff-only`; print a summary. Replaces ~6
   manual steps and bakes in the safety checks.
2. **Lanes by risk** in `WORKTREE_WORKFLOW.md`: code (`core/`, `pipelines/`, `agent/`, tests) in a worktree;
   docs (status docs, specs, plans, trackers, READMEs) and pipeline-generated vault/index output may go
   straight to `main` with explicit paths. The to-do exemption is the first instance. Need rules for
   two agents editing one doc (append-only sections, commit promptly).
3. **Merge style decision:** rebase + `--ff-only` (linear, no "Merge main into ..." commits) vs the doc's
   `--no-ff` (explicit integration points). Pick one and update the doc.
4. **Faster tests:** install `pytest-xdist` (`-n auto`) and/or a path-to-tests mapper so iteration runs
   only affected packages; keep the full suite for landing. Not measured; the ~25 s figure is a guess.
   **Caution (2026-10-16):** the full suite's problem turned out to be memory, not CPU
   (`docs/superpowers/specs/2026-10-16-test-suite-memory.md`) -- `tools/run_tests_chunked.py`
   already fixes that by running chunks sequentially. Parallel `-n auto` workers would each
   re-import and hold their own copy of everything, making memory *worse*. If this is picked up,
   measure peak memory with a small fixed `-n` first, not `auto`.
   **Caution (2026-10-20):** see TODO-0073's 2026-10-20 update -- a chunk's wall time varied 2x
   run-to-run, apparently tracking host free memory (likely Windows paging at low headroom), not
   code or chunk count. Any parallelism change here inherits that same risk until a per-chunk peak
   memory measurement exists; concurrent chunks on a low-headroom host could reintroduce the OOM.
5. **Active-work report:** a small tool listing each worktree's changed files vs its merge-base and flagging
   overlaps, so collisions in shared packages (`core/indexer`, `core/env`) are seen before landing.
6. **Scope the Obsidian Git auto-backup** (content paths only, or a separate `vault-backup` branch merged
   periodically) so `main` is not repeatedly swept. Needs the user's plugin config; not inspected.
7. **Cross-repo "land data" helper** that commits `.index/*.json` (monorepo) and the matching
   `academic_notes` outputs together with explicit paths, including partial staging of shared aggregate
   files such as `courses.json`.
8. **Worktree lifecycle helpers:** list merged/idle worktrees as retirement candidates (never auto-remove
   other agents' work), and a `new_worktree` helper that creates the branch/worktree and prints the
   correct `--root`/env for running pipelines against the live vault without junctions.

## Open design questions for the brainstorm
- Who may land on `main`: only the user, or any agent after the user says "merge"? How is that recorded?
- Merge style (item 3), and whether to keep merge commits as audit points.
- When may generated data (index, pipeline outputs) go straight to `main`, and who is its single writer
  (the doc requires "one assigned writer" for shared corpus/index writes)?
- Where should pipelines write when run from a worktree: a worktree-local corpus (policy) or the live
  vault (what real validation actually needs)?
- Can the auto-backup be limited, and does the tablet sync (Fit plugin on the vault repo) constrain that?
- How do Claude/Codex/Gemini claim shared packages so overlaps surface early (claims file, branch
  naming, or the item 5 report)?
- Test policy at landing: full suite always, or changed-package subset plus periodic full runs?

## Useful snippets from this session
- Conflict preview without touching any working tree:
  `git merge-tree --write-tree --name-only main <branch>` (prints `CONFLICT (...)` lines if any).
- Overlap with the main checkout's uncommitted files (merge-base form, the correct one):
  `MB=$(git merge-base main <branch>); comm -12 <(git diff --name-only $MB <branch> | sort) <(git status --short | awk '{print $2}' | sort)`
- Land an exclusively owned, unpublished branch: in the worktree `git rebase main`; in the main checkout
  `git merge --ff-only <branch>`. Verify the main checkout's `git status --short` is unchanged afterwards.
- Stage one entry of a shared aggregate file: build the file from `HEAD`'s version with only your entry
  replaced, then `git hash-object -w --path <file> <tmpfile>` and
  `git update-index --add --cacheinfo 100644,<sha>,<file>`; confirm with `git diff --cached`.
- Child repo from the monorepo root: `git -C ai-sandbox/academic-hub/academic_notes <command>`; stage
  renames there with `git mv` so history follows.
- Run worktree code against the live vault:
  `PYTHONPATH="$(pwd -W)" python -m <module> --root <main-checkout>/ai-sandbox/academic-hub`.
- Windows: `git show origin/some/branch:path` is mangled by MSYS path conversion; use the commit SHA or
  `MSYS_NO_PATHCONV=1` (already in the workflow doc).

## Guardrails for whoever implements
- Keep: never `git add -A`/`git add .`; never print or commit `ai-sandbox/.env`; no force-push, `reset
  --hard`, or `clean`; never remove another agent's worktree; commit/push only when the user asks; the
  monorepo is public on GitHub (see the root `.gitignore` comments for the IP exclusions).
- Changes to `WORKTREE_WORKFLOW.md` take effect only for sessions told to re-read them.
