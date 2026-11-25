# Website citation gate: Codex handoff v1

Date: 2026-11-25. From: Claude (design and review). To: Codex (implementation and tests).

Design: [website citation gate design v2](2026-11-25-website-citation-gate-design%20-%20v2.md). The owner approved its three decisions on 2026-11-25. Read the design first; this handoff lists what to build, what to test and how to report.

## Before you start

- Run `python -m tools.active_work` from `ai-sandbox/academic-rag-model/`.
- Create the branch `codex/website-citation-gate` from the latest monorepo `main` in its own worktree.
- Wait for website branch `claude/remove-placeholder-publication` (65b7828, deletes `content/publications/conference-paper/`) to land on the website's `main` before running the gate against the real site. Claude lands it by hand after owner approval. The tests don't depend on it.

## Part 1: monorepo code (branch `codex/website-citation-gate`)

New module `ai-sandbox/academic-rag-model/tools/land_website.py`, with tests in `tests/tools/test_land_website.py`. Reuse `tools/land_branch.py` by import (`run_git`, `change_id`, the log helpers, the citation-gate error text). Don't copy its code. If a helper needs a parameter to work on a second repo, add it with a default that keeps `land_branch` unchanged.

```
python -m tools.land_website check <website-worktree>
python -m tools.land_website land <website-worktree> --change-id <id>
```

**`check`** never merges or pushes. It stops at the first failing step and says which step failed:

1. **Repo:** the worktree's `origin` URL ends in `AaronScherf/AaronScherf.github.io(.git)`. The branch isn't `main`, and the worktree has no tracked changes and no untracked files outside `.gitignore`.
2. **Fast-forward:** `git fetch origin`, then `origin/main` must be an ancestor of `HEAD`.
3. **Overlaps:** for every other local branch in the website repo that isn't merged into `origin/main`, compare `git diff --name-only origin/main...<b>` with this branch's files. Block on any shared path and name the branch and paths. Merged branches are listed as retirement candidates and don't block.
4. **Hugo build:** run `hugo --minify --quiet --destination <temp dir>` in the worktree, with `<website main checkout>/node_modules/.bin` first on `PATH`. Find the main checkout from the first entry of `git worktree list --porcelain`. If `node_modules/.bin` is missing, stop with "run npm install in <main checkout>"; never run `npm install` yourself. Block on a non-zero exit and print the last 20 lines of output. Delete the temp dir.
5. **Citation gate:** collect the files the branch adds or modifies under `content/` that end in `.md`, case-insensitive, using the same A/M/R-not-R100 rules as `land_branch.changed_research_notes`. Run `reference_review.gate(paths, RegistryClient(DEFAULT_CACHE, online=True), repo_root=<monorepo root>)`, so ledger keys look like `ai-sandbox/personal-website/AaronScherf.github.io/content/...`. On a block, raise the same per-note message format as `land_branch.run_citation_gate`.
6. **Change ID:** `land_branch.change_id` (the diff fingerprint against the merge-base with `main`), computed in the website worktree. Append a check entry to a log in the website repo's git common dir, in the same JSON-lines format as `land_branch`. Print the ID and the line "Nothing has been merged or pushed. Ask the user to approve change <id>."

**`land`:**
- Requires a passing check entry for that change ID on that branch, then re-runs `check`. Refuse if the ID changed.
- In the website main checkout, refuse if there are tracked changes (staged or not) to any path the merge would touch. Untracked files such as `content/blog/drafts/` don't block. Never stash, reset or discard anything.
- Then run `git merge --ff-only <branch>` and `git push origin main`. If the push fails after the merge, say that `main` was fast-forwarded locally but not pushed, as `land_branch` does.
- Log the outcome. Don't delete the branch or the worktree.

**Front matter (`tools/reference_checker.py`):**
- A YAML `doi:` field in a page's leading `---` block is a citation, and its cited title is the front matter's `title:`.
- Today the DOI regex picks the field up with no title, so a publication page would come back TITLE_MISSING.
- Keep this change small and covered by tests. Body text and research notes must behave exactly as before; check that by running the existing `test_reference_checker*.py` and `test_reference_review*.py` unchanged.

## Part 2: agent rules

**Monorepo**, on the same branch:
- `CLAUDE.md` "Citing literature": change "The landing gate enforces this for Markdown under `ai-sandbox/research/`." to also name website `content/` through `tools.land_website`.
- Add a short "Website gate" section to `docs/reference-checker/README.md` with the two commands and the six check steps.
- In `docs/reference-checker/HISTORY.md`, add a section saying why the gate is a local tool rather than a CI job (the ledger is local; design v2, "Options").

**Website repo**, on a separate website branch `codex/website-landing-rules`:
- In `CLAUDE.md` and `GEMINI.md` (the website has no `AGENTS.md`; don't create one), replace the hand fast-forward-and-push step with: run `land_website check` from the monorepo, the owner approves the change ID, then `land_website land`.
- In `GEMINI.md` line 30, "This repo has no landing gate, so the check is part of finishing the draft" becomes a statement that the landing gate runs the check, and that running `reference_review raise` before handing off is still required.
- This branch is the first one landed with the new tool, once Part 1 is on monorepo `main`.

## Tests (`tests/tools/test_land_website.py`)

Use temporary git repos and a fake registry client, as `test_land_branch.py` does. No network, no real Hugo: inject the build command so tests can make it pass or fail.

1. Page selection: A, M and R<100 under `content/` are selected. R100, deletions, `.md` outside `content/`, and non-Markdown files under `content/` are not. `.MD` is selected.
2. `check` blocks, each naming its step:
   - on `main`;
   - with a dirty tree;
   - with an untracked file that isn't ignored;
   - when not fast-forward;
   - on an overlap with another unmerged branch (a merged branch doesn't block);
   - when the build fails;
   - when `node_modules/.bin` is missing.
3. Gate:
   - a fixture page citing `10.5555/123456` gives NOT_FOUND and blocks;
   - a body DOI without a title gives TITLE_MISSING and blocks;
   - a front-matter `doi:` with a `title:` matching the registered title is CONFIRMED and passes;
   - a front-matter `doi:` with a mismatched `title:` gives TITLE_WRONG;
   - a branch with no changed pages under `content/` skips the gate and passes.
4. Ledger keys are relative to the monorepo root and don't collide with a research note of the same file name.
5. `land`:
   - refuses an unknown or stale change ID;
   - refuses when the main checkout has a tracked change to a merged path;
   - lands with an unrelated untracked file present;
   - reports a failed push after a local fast-forward;
   - never stashes.
6. `land_branch` behaves as before: the existing `test_land_branch.py` passes unchanged.

## Acceptance (Claude runs these after review)

- `python -m tools.land_website check` on `claude/remove-placeholder-publication` (if not yet landed): passes, with no gate pages (deletions only).
- `check` on a scratch website branch that adds a page citing `10.5555/123456` blocks at the citation gate with NOT_FOUND. Delete the scratch branch afterwards.
- `check` on `codex/website-landing-rules` passes.
- Timing: report the wall time of each `check`. The design expects about 8 s with a warm cache.

## Report back

Report:
- the branch and commit;
- the monorepo `land_branch check` change ID, paths, overlaps and test counts;
- the website branch commit;
- any change to `land_branch.py` and why it keeps `land_branch` behaving the same;
- anything in this handoff you changed or think is wrong.

Don't land anything; the owner approves each change ID.
