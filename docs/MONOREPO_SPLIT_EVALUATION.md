# Monorepo vs split: evaluation handoff

Status: **evaluation only, nothing decided, nothing moved.** Written 2026-11-02 from a design discussion with the
owner. The next session audits coupling and recommends; the owner decides.

## Why this came up

The independent-research work (`ai-sandbox/research/independent-research`) now builds its projects as standalone
public repos, so they can have fast tests and their own CI and be re-run by outsiders:

- `AaronScherf/reprokit` (library) and `AaronScherf/compound-shocks-panel` (first study).
- The monorepo keeps only their design docs, plans and Gemini notes under
  `ai-sandbox/research/independent-research/docs/superpowers/` and `.../notes/`, plus a stale intake scaffold in
  `.../projects/02_compound_shocks/` (migrated into the new repo; no pointer to it exists yet).

The owner then asked whether the other subprojects still benefit from sharing one repo, given that the
independent projects are meant not to borrow from each other.

## Top-level contents (not yet audited)

`ai-sandbox/` contains `academic-hub`, `academic-rag-model`, `personal-website`, `research`, `trading`,
`utility-scripts`, `processed_outputs`, plus loose files. Only the first four were discussed.

## What the discussion established

**Reasons to share one repo (inferred from CLAUDE.md files and memory, not verified in code):**
- `academic-rag-model` pipelines write into the `academic-hub` vault; code and output change together.
- `research/.index/*.json` (literature index) appears to be produced by the same pipelines.
- One set of agent conventions: root `CLAUDE.md`, `docs/AGENT_ROUTING.md`, the worktree procedure, a shared `.env`,
  one pending-to-do tracker.

**Costs of sharing (observed):**
- The repo is public, and the vault and textbook material need constant `.gitignore` care for copyright.
- Git friction already seen: concurrent sessions sharing one index, auto-commit `c17c1264` that added dangling
  gitlinks (`berkeley_thesis/wheat_yield_prediction_gee`, `math_thesis/Novel-Omnibus-...`, no `.gitmodules`), a past
  history rewrite (filter-repo), Obsidian config churn, roughly 65 `.worktrees/` folders.
- Large status docs and one slow CI make agent context expensive.

**Not a reason either way:** agents can work outside their starting directory. The real constraints are permission
scope and the worktree workflow, and both work per repo too.

## Options

1. **Status quo** plus a pointer README in the monorepo for each standalone repo.
2. **Split by coupling (the discussion's leaning):** independent-research projects stay standalone; keep
   `academic-rag-model` and `academic-hub` (and probably the `research` literature pipeline) together; move
   `personal-website` out only if it builds and deploys independently; consider a private repo for the vault if it
   holds copyrighted material.
3. **Full split** into one repo per subproject. Likely too costly while the pipelines are coupled.

## Task for the next session

1. **Audit coupling (read-only).** For each top-level subproject, find paths, imports, config and CI that reach into
   another subproject: Python imports, relative paths, shared `.env` use, scripts that write into another folder, the
   website's source of content, what generates `research/.index`. Use an Explore subagent (model: haiku) per the root
   CLAUDE.md and bring back a dependency table, not file dumps.
2. **Assess history and IP risk** for any candidate to move: whether `git filter-repo` or a fresh repo is needed, and
   whether anything copyrighted is in history that a new public repo must not inherit.
3. **Recommend** one of the options above with the migration steps, effort and risks, then stop for the owner's decision.

## Constraints

- **Do not move, delete or rewrite anything** until the owner approves a specific plan.
- No git submodules (the owner's security preference). Cross-repo links are by documented dependency or version pin.
- Follow `docs/WORKTREE_WORKFLOW.md`: one worktree per writing task. The main checkout has unrelated uncommitted
  changes and other sessions may be working; leave them alone and stage explicit paths only.
- Never commit secrets (`ai-sandbox/.env`) or copyrighted source material; the repo is public.
- Keep reports short, with a link to any document the owner should review (`file://` for unpushed files).

## Open questions for the owner

- Does the vault or textbook material need to be private?
- Does `personal-website` read from the hub, or deploy on its own?
- Are `trading` and `utility-scripts` active, and do they belong with any other subproject?
- Should the monorepo remain the home for cross-project design docs, or should those move with their projects?
