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

---

# Update 2 (2026-11-02): owner answers and revised recommendation

This **supersedes the Recommendation in Findings section 3** (Option 1). Nothing has been moved; more review is needed before any change.

## Owner answers

- Public vs private is out of scope for this discussion. **No history purge.**
- `personal-website` reads the `academic-rag-model` docs, not course material, and is its own repo.
- `trading` and `utility-scripts` are inactive; the "independent" and "research-only" distinctions are outdated. They may be folded in.
- Cross-project design docs stay in this monorepo (the parent).
- The two untracked GCP/journal-discovery docs should be tracked, unless they hold secrets.

## Evidence that changes the plan

- **Landing time is not caused by layout.** `tools/land_branch.py` runs only `academic-rag-model/tests/` (309 files). `personal-website/` is gitignored and a plain folder, so it adds nothing. Logged checks in `.git/agent-landing-log.jsonl`: 163 runs, median 348 s, p90 705 s, max 1,451 s, mostly full-suite runs. The speedup lever is fewer full-suite fallbacks (triggered by non-`.py`, non-`.md` changes or `conftest.py`) and a faster suite, which is a separate task.
- **Independent projects already follow the website model** (standalone repos, gitignored working trees, pinned in `research/independent-research/projects/repositories.json`).
- **The hub is already mostly split.** `academic_notes/` is its own repo and `academic_resources/` content is mostly gitignored. Of 215 tracked hub files, **199 are under `academic_resources/`** (92 PDFs, SVG/PNG exports, textbook `processed_outputs`), i.e. the content you are already untracking. Only about 16 files are real hub config (`CLAUDE.md`, `README.md`, `.index/` cards, `obsidian_styles`, `semester_study_plan`).

## Revised recommendation: Option 2b (decouple, don't create new repos yet)

1. **Independent projects:** keep them under `ai-sandbox/research/independent-research/projects/`. Add `reprokit` and `compound-shocks-panel` to `repositories.json` with commit pins, gitignore their working trees, and remove the migrated `02_compound_shocks/` scaffold.
2. **Configurable hub root:** add one `ACADEMIC_HUB_ROOT` setting (default `../academic-hub`) used by `core/env/academic_hub_paths.py` and the modules that hard-code `academic-hub` (about 50 non-test modules and 23 tests mention it; separate real path use from docs first). Decide who owns `.index/` writes. About 1-2 days.
3. **Public hub template:** ship the empty scaffold (course folders, hub `CLAUDE.md`/`README`, sample config) inside this repo, as `templates/academic-hub/` or an extension of `workspace_generator.sh:68-75`. No third repo, which avoids drift from the code that defines the layout. A new user clones, runs it, and builds their own hub with none of your files.
4. **Test fixtures:** tests that touch hub content use a temporary scaffold instead of the real vault.
5. **No new private hub repo for now.** Because the heavy content is already gitignored, a separate repo would hold about 16 files and add cross-repo commit overhead for little gain. Finish untracking the 199 `academic_resources` files (already in progress in the main checkout) and add a guard so they cannot return. Revisit a private repo only if hub config or `.index/` grows.
6. **Cross-repo reading:** siblings under `ai-sandbox/` plus additional allowed directories, as with the website. No submodules.
7. **Cleanup:** fold `trading` and `utility-scripts` into `research/` or `academic-rag-model`; fix the two stale docs; add `PAID_GEMINI_KEY` to `.env.example`; track the GCP/journal docs after a secrets check.

Landing-test speed is tracked separately from this decision.

## Risks

- The configurable-root refactor touches many modules; mitigate with the temp-scaffold fixture and a grep-based inventory first.
- Untracking files from HEAD does not remove them from history. This is accepted per your no-purge decision, and the old content stays in the public history.

## Open questions

1. Is a deferred private hub repo acceptable, or do you want it now for `.index/` cards and `semester_study_plan`?
2. Should `.index/` stay in the hub or move under the rag-model (it is generated by rag-model)?
3. Where should `trading` and `utility-scripts` land (`research/` vs `academic-rag-model/`)?
4. Should a pre-commit or landing guard block PDFs and SVGs under `academic-hub/` for good?
5. Do you want the full-suite-fallback speedup scoped as its own task?

---

# Update 3 (2026-11-02): decisions on the open questions

## Decided by the owner

1. **Private hub repo: deferred.**
2. **`.index/` stays in the hub.** It is the hub's own catalog: per-course file cards (`<course>.json`), `courses.json`, `tags.json`, `materials/*` (material decisions) and `offering_links/*` (review and dismissals). Passage-level `.index/chunks/` is already gitignored. The data describes hub content, so it travels with the hub; the rag-model code only generates it, writing through `ACADEMIC_HUB_ROOT` (`core/indexer/index_card.py`, `chunk_index.py`). The earlier question of moving it to rag-model is closed. (`research/.index/` is the separate research-side equivalent.)
3. **`trading` and `utility-scripts` fold into `academic-rag-model`.**
4. **Block PDFs and SVGs under `academic-hub/`** with a durable guard (pre-commit and landing check).
5. **Landing-test speed is its own task** (scope below).

## Task scope: faster landing checks

Owner's idea: split subprojects by dependency in a hub-and-spokes layout (light `core/`, spokes `agent`, `audio_generator`, `discovery`, `pipelines`, `resume_manager`, `tools`), so a change does not run unrelated spokes' tests.

Current behavior (`tools/land_branch.py`): changed `.py` files map to the matching `tests/<top-level dir>` only, markdown-only changes skip tests, and anything else (non-`.py`, non-`.md` files, `conftest.py`, unmapped paths) falls back to the full chunked suite. A change under `core/` runs only `tests/core`, even though spokes import it.

Proposed order, cheapest first:
1. **Measure:** count how often each fallback trigger fires in `.git/agent-landing-log.jsonl` (163 checks, median 348 s).
2. **Dependency-aware selection inside the existing repo:** build the import graph from `core/` to the spokes, so a spoke change runs only its tests and a `core/` change runs `core` plus its dependents. Add safe extensions (`.json`, `.txt`, config files that tests do not read) to the skip list. This gives the hub-and-spokes benefit with no layout change.
3. **Physical split into separate packages or repos** only if step 2 is not enough. The cost is versioning `core/` across repos (pin or published package, no submodules) and cross-repo commits, so it is not the first move.

Spec-first before any code; Claude owns the design, Codex the implementation per `docs/AGENT_ROUTING.md`.

## Resolved and remaining

- **Decided:** until the import-graph selector is trusted, any `core/` change runs the full suite.
- **Still to determine (first step of the landing-speed task):** which non-`.py` extensions (`.json`, `.txt`, `.yaml`) are safe to skip. Method: for each extension, grep `tests/` and the code under test for reads of files with that extension, and check the landing log for runs it triggered. Skip only extensions with no test or fixture reads; leave the rest on the full-suite fallback.

---

# Update 4 (2026-11-03): three lines of effort

The `part_N` structure fix (commits `1530b8f4`, `29fefc3d`, `b05e94f4`, `2b505104`) showed that the hub is brittle: one extra folder layer cost about two days of refactoring and tests. `core/env/academic_hub_paths.py` recognizes only a folder named `part_N` (`^part_\d+$`) directly under a course; any other new layer is read as the content category, which breaks the notes/resources mirror check and makes index cards look stale (card hashes and clone IDs depend on source paths).

**Decision (owner, 2026-11-03): this is a separate effort, not part of the monorepo split.** The work is now three tracks:

1. **Landing check speed (first).** Spec: `ai-sandbox/academic-rag-model/docs/superpowers/specs/tools/2026-11-03-landing-check-speed-design.md` on branch `claude/landing-speed-spec`. Steps 1-2 are with Codex (`codex/landing-speed-impl`). Step 3 audit is done: no extension is safe to skip, so selection uses ownership mapping instead of an allowlist.
2. **Hub path model (second).** A general fix: match notes and resources by relative path below the course, make category depth configurable, and give index cards a stable identity independent of path. The `ACADEMIC_HUB_ROOT` setting from Option 2b step 2 and the temp-scaffold test fixtures fold into this track, since they touch the same module and about 50 callers. Needs its own design spec before any code.
3. **Monorepo hygiene (small, any time).** `repositories.json` pointers for `reprokit` and `compound-shocks-panel`, removal of the migrated `02_compound_shocks/` scaffold, folding `trading` and `utility-scripts` into `academic-rag-model`, the PDF/SVG guard, tracking the two GCP/journal docs after a secrets check, and the stale-doc fixes.

Option 2b stays the recommendation, with step 2 (hub root) and step 4 (fixtures) moved under track 2. The deferred private hub repo and the physical hub-and-spokes split remain deferred.
