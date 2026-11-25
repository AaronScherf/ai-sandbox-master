# Website citation gate: design v1

Date: 2026-11-25. Author: Claude (design). Implementer: Codex, after the owner approves this design.

## Problem

Research notes under `ai-sandbox/research/` can't reach `main` with unsettled citations. `tools.land_branch` runs `reference_review.gate()` (strict mode) on every changed note, and blocks the branch on any defect, open review item or unresolved DOI.

The website repo (`ai-sandbox/personal-website/AaronScherf.github.io`, a separate git repo that the monorepo ignores) has no landing tool. Branches are fast-forwarded and pushed by hand, and a push to `main` deploys to GitHub Pages (`.github/workflows/deploy.yml`). The `GEMINI.md` "Citing literature" rule (website commit 35f88e4) is only an instruction. Nothing stops a page with a made-up DOI or an untitled citation from going live, and if the writing agent's worktree or session ends first, the findings go with it.

## Current state of the website (measured 2026-11-25)

- 86 tracked Markdown files under `content/`.
- One DOI in the whole site: `10.5555/123456` in `content/publications/conference-paper/index.md`, the Hugo Blox template's placeholder.
- Links are mostly to GitHub (143), Hugo Blox docs (47), the site itself (23) and image hosts. None are links to papers.

So the website doesn't cite literature yet. The gate is for what's coming: research blurbs (`codex/integrate-research-blurb`, `codex/research-blurb-drafts`), blog posts held to the new standards (`codex/blog-post-standards`), and publication pages.

## Options

| | A. Local landing tool (recommended) | B. GitHub Actions job before deploy | C. Git pre-push hook |
|---|---|---|---|
| Sees the owner's decisions | Yes: reads the shared ledger in `academic-rag-model/.reference_checker_review/` | **No**: the ledger is local and untracked, so every accepted item comes back as open and blocks | Yes |
| What it blocks | The merge and the push | Only the deploy: the bad commit is already on `main` | The push |
| Registry cache | Shared local cache (warm) | Empty on every run, unless saved with `actions/cache` | Shared local cache |
| Fits the change-ID approval | Yes, same as `land_branch` | No | No |
| Can be skipped | Only by not using it, which the agent rules forbid | No | Per clone, and `--no-verify` skips it |

B is ruled out by the ledger: CI can't see the owner's accepts, so it would block on items already decided. Publishing the ledger to fix that would mean committing review state to a public repo. C gives no change ID and is easy to skip. A matches how research notes already land.

## Design (option A)

A new module, `ai-sandbox/academic-rag-model/tools/land_website.py`, mirroring `land_branch`:

```
python -m tools.land_website check <website-worktree>
python -m tools.land_website land <website-worktree> --change-id <id>
```

**`check`** does these steps and never merges or pushes:

1. Confirms the worktree belongs to the website repo, sits on a non-`main` branch, and has a clean tree.
2. Fetches `origin` and requires `origin/main` to be an ancestor of the branch (fast-forward only).
3. Overlap check: lists the other website branches and worktrees that change any of the same files, and blocks while any exist. This is the check I currently run by hand.
4. Citation gate: collects the Markdown files the branch adds or modifies under `content/`, using the same diff rules as `land_branch.changed_research_notes` (A, M, and renames other than R100). It then runs `reference_review.gate(paths, client, repo_root=<monorepo root>)` with the shared registry cache. Ledger keys are paths relative to the monorepo root (`ai-sandbox/personal-website/AaronScherf.github.io/content/...`), so they can't collide with research notes.
5. Prints a change ID: a hash of the branch SHA, the `origin/main` SHA and the gate result, built the same way `land_branch` builds its ID.

**`land`** re-runs `check`, requires the same change ID, then runs `git merge --ff-only <branch>` in the website's main checkout and `git push origin main`. If the main checkout has local changes that the merge would touch, it stops and reports them instead of setting them aside.

**When the gate blocks,** it prints the same per-note actions as `land_branch` (fix the defects, sync the review page, apply decisions). Open items go to the same review page (`https://claude.ai/artifact/EQM9L22JbowiAGMfx8jUQe`).

**Front matter:** publication pages carry the DOI in YAML front matter (`doi: ...`). The checker must read that field as a citation of the page's own `title:`. Without this, every publication page would come back as a citation with no title. The template placeholder `10.5555/123456` must come back NOT_FOUND, and the gate should block on it until the example page is deleted or fixed. That makes the placeholder a ready-made test case.

**Agent rules:** the website's `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` replace the hand fast-forward-and-push step with `land_website check`, then owner approval of the change ID, then `land_website land`. The monorepo's `CLAUDE.md` line saying the website has no landing tool changes too.

## How long it takes

Measured 2026-11-25 by running `reference_review.gate()` on a copy of the ledger, using `Proposal Draft - v5.md` (19 KB, 12 DOIs; 11 defects, all TITLE_MISSING):

| Case | Gate time |
|---|---|
| Cache filled (every DOI looked up before) | 0.3 s |
| Empty cache (every DOI new) | 31.7 s, about 2.6 s per new DOI |

A typical run lands between the two. Only DOIs the cache hasn't seen cost registry time, and the lookups are free public APIs (Crossref, OpenAlex). A blog post with 5 new citations would take about 15 s on its first check and well under a second after that.

The website gate adds nothing else slow. `land_branch` takes longer overall because it runs the project's test suite; the website has no tests. An optional Hugo build (open question 1) would add the build's run time.

## Not covered

- **Plain URLs:** links to papers by URL count as `url_only` and don't block. Resolving them is the separate open item "resolving plain URLs", the same gap research notes have.
- **Citations with no DOI and no URL:** prose like "Smith (2020)" isn't extracted, so it isn't checked.
- **Whether a paper supports the claim:** that's the claim-support check on the to-do list.
- **Pages already live:** pages already on the website's `main` aren't checked until someone edits them.

## Open questions for the owner

1. **Hugo build in `check`:** should `check` also run `hugo --minify` and block when the build fails? Recommended yes; it catches broken front matter.
2. **Scope:** should the gate cover all of `content/`, or only `content/blog/`, `content/publications/` and the research blurb pages? Recommended all of `content/`: it costs nothing on pages without citations.
3. **The placeholder page:** should `content/publications/conference-paper/` be deleted before the gate goes live, or kept as a known block until real publications replace it?
