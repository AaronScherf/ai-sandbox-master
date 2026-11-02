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

---

# Findings (2026-11-02, read-only audit)

Nothing was moved, deleted or rewritten. History queries were read-only (`rev-list`, `cat-file`, `ls-files`).

## Corrections to the brief

- No `.github/` exists: **no CI workflows are tracked.** The "one slow CI" is not in this repo.
- `personal-website` is not in the monorepo; `.gitignore:1` marks it a separate repo, cloned by `workspace_generator.sh:88-90`.
- There is no top-level `ai-sandbox/processed_outputs/`. Outputs live under
  `academic-hub/academic_resources/<course>/textbooks/processed_outputs/`.
- `trading` is one file (`notes/think or swim.md`); `utility-scripts` is two files.

## 1. Coupling table

| Subproject | Reaches into | Reached by | Own manifest/tests/CI | Standalone? |
|---|---|---|---|---|
| academic-hub (vault) | nothing (docs only) | rag-model `core/env/academic_hub_paths.py:17,42-67`; `core/indexer/index_card.py:114`, `chunk_index.py:31` | none | content only |
| academic-rag-model | hub (`academic_hub_paths.py:17`); research (`agent/literature/cli.py:22,38`, `discover.py:207`); website + research (`resume_manager/convert_resume.py:24,28`); `ai-sandbox/.env` (`gemini_utils.py:86`) | utility-scripts docs | requirements, pytest (319 test files), Dockerfile; no CI | partial: needs sibling folders and `.env` |
| personal-website | absent here | read by `convert_resume.py:24`; SHA-audited by `tools/audit_website_sync.py:17` and `docs/trackers/subproject_registry.json` | own repo | yes (build/deploy unverified) |
| research | docs only | `.index/` written by rag-model `agent/literature/cli.py:38`, `core/indexer/index_search.py:964`; `journal-articles/` by `discover.py:207` | none | partial: `.index` and `journal-articles` are generated and gitignored |
| trading | none | none | none | yes |
| utility-scripts | `.env` (`textbook_analysis.py:42`); hub textbook outputs by CLI path | none | none (no requirements) | partial |

`.env` consumers: rag-model (all keys, incl. `PAID_GEMINI_KEY`, which is missing from `.env.example`) and utility-scripts (`GEMINI_API_KEY`).

Strongest couplings: (1) the hub folder layout is an API hard-coded in `academic_hub_paths.py`; (2) the shared `.env` found by relative path; (3) `research/.index` produced by rag-model with a hard-coded `../research` root; (4) `convert_resume.py` needs the website clone. Stale docs: research README names `academic-rag-model/indexer/index_search.py` (now `core/indexer/`); utility-scripts instructions cite a nonexistent `academic-hub/processed_outputs`.

## 2. History and IP risk (public repo `AaronScherf/ai-sandbox-master`)

- 1,562 commits, 4,554 blobs, 281 MB pack. No dangling gitlinks at HEAD (`c17c1264` is just a vault auto-backup), no `.env` blob in history.
- **Course PDFs in history: 94 files, ~192 MB, all under `academic-hub`** (professor_notes, syllabi, recitation slides, TA notes, problem sets). About 29 are instructor-owned (professor_notes, syllabus, slides). 92 PDFs are still tracked at HEAD. Your main checkout shows many as uncommitted deletions, so a removal is already in progress; it would not purge history.
- **Textbook-derived text in history:** four `*.rag.md.bak` full-text conversions (Hayashi, Simon, Press, Rubinstein; 0.4-2.4 MB each), plus 93 tracked `textbooks/**/processed_outputs` files at HEAD (mostly json metadata and image descriptions). No textbook PDFs found.
- ~192 MB of the pack is hub binaries (PDFs, 8-19 MB excalidraw SVGs), so the hub is also what makes clones heavy.
- Consequence: **any new public repo that inherits history inherits the exposure.** Any hub split must be a fresh repo (squashed, no history). Cleaning the existing public repo requires `git filter-repo` plus a force-push, and GitHub forks, caches and clones may still hold old objects. Treat the old content as already exposed unless the owner decides otherwise.

## 3. Recommendation

**Option 1 (status quo plus pointers), with the IP cleanup handled as a separate decision.**

Why not split by coupling: rag-model and hub are one system (code hard-codes the vault layout, 925 + 215 files), and the research index is generated by rag-model. Splitting them breaks the shared-`.env` and relative-path assumptions for little gain. `trading` and `utility-scripts` are too small to justify a repo. The website is already separate. Full split is the costliest and has the same IP problem.

Steps (effort in brackets):
1. Add a pointer README or doc entry in the monorepo for `reprokit` and `compound-shocks-panel`; mark the stale `projects/02_compound_shocks/` scaffold as migrated [30 min].
2. Fix the two stale docs and add `PAID_GEMINI_KEY` to `.env.example` [30 min].
3. Finish committing the in-progress removal of tracked course PDFs, and add a `.gitignore` rule or pre-commit guard for them [1 h].
4. Owner decision: purge history (filter-repo the 94 PDFs and `.rag.md.bak` files, force-push, tell collaborators to re-clone), or make the vault private. Needs your approval before any history command [2-4 h plus verification].
5. Revisit a hub split only if the vault must be private. Do it as a fresh private repo with a documented path or version pin, no submodules, and a configurable hub root in `academic_hub_paths.py` [1-2 days].

Risks: filter-repo changes every SHA (memory notes already warn old SHAs fail to resolve; the landing-metrics and tracker SHAs would break); force-push needs coordination with open worktrees and branches (about 50 local `claude/` `codex/` `gemini/` branches); a hub split loses atomic code-plus-vault commits.

## 4. Open questions (need your answer)

1. Must the vault or textbook-derived material be private, or is cleaning the public history enough?
2. Do you want the existing public history purged (filter-repo and force-push), accepting changed SHAs?
3. Does `personal-website` read from the hub, or deploy alone? (Its repo is absent here; unverified.)
4. Are `trading` and `utility-scripts` active? Fold `utility-scripts` into rag-model, or leave?
5. Do cross-project design docs stay in the monorepo, or move with their projects?
6. The GCP pipeline docs (`gcp_instructions.md`, `journal_discovery_instructions.md`) are referenced but not tracked here. Are they intentionally untracked?
