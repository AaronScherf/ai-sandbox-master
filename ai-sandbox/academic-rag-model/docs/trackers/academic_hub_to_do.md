# Pending Improvements for the Academic Hub by Subproject

<!-- Convention: one bullet per pending item under its subproject's `##` heading, ending in
     `(added YYYY-MM-DD)`. New sections go directly under this title: the file ends in pasted
     example text, so don't append at the end. Agents add items when asked to "add this as a
     pending to-do" (see the root CLAUDE.md). -->

## Git Workflow Between Agents (brainstorm pending, nothing implemented)
- The user wants to brainstorm a smoother git workflow between agents (Claude, Codex, Gemini) before
  changing any rules or tooling, and to pick this up with another agent. Everything below is evidence
  and candidate ideas from one long Claude session, not decisions. Read first: `docs/WORKTREE_WORKFLOW.md`,
  `docs/AGENT_ROUTING.md`, the root `CLAUDE.md` ("Git" and "Pending to-dos"). (added 2026-10-04)

### The problem, with evidence from the 2026-10-03/04 session
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

### Existing policy to build on (and where proposals collide with it)
- Already in `docs/WORKTREE_WORKFLOW.md`: one writer per worktree, `.worktrees/` ignored, integration "one
  task at a time", retire-worktree procedure, Windows `git show` path gotcha, child-repo worktrees, "adopt
  the policy in existing sessions" (running agents do not reload guidance; they must be told).
- Collisions to resolve: the doc prescribes `git merge --no-ff` (merge commits) while rebase-then-ff gives
  linear history (the doc allows rebasing only an exclusively owned, unpublished branch); workers "do not
  merge into main unless assigned the integrator role" yet in practice the user tells an agent to merge;
  "integration checkout must be clean" is never true; "do not junction/symlink writable output dirs to the
  live vault" vs. needing real data in tests/runs.

### Candidate changes (unimplemented; roughly by payoff)
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

### Open design questions for the brainstorm
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

### Useful snippets from this session
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

### Guardrails for whoever implements
- Keep: never `git add -A`/`git add .`; never print or commit `ai-sandbox/.env`; no force-push, `reset
  --hard`, or `clean`; never remove another agent's worktree; commit/push only when the user asks; the
  monorepo is public on GitHub (see the root `.gitignore` comments for the IP exclusions).
- Changes to `WORKTREE_WORKFLOW.md` take effect only for sessions told to re-read them.

## Notes Transcription (`pipelines/transcribe_notes`)
- Move the `*_pages_cache.json` resume caches out of `processed_outputs/` into `processed_outputs/_cache/`, to cut clutter when browsing folders (89 files, ~2.2 MB, all tracked in the `academic_notes` repo). Plan: the cache path is built in one place (`transcribe_notes.py`, `cache_path`, around line 1095) so change it there; read `_cache/` first and fall back to the old location so unmigrated caches still resume; update `tools/audit_metadata.py`, which moves a cache along with its `.md`; one-shot `git mv` of the existing 89 in the `academic_notes` repo; test both locations plus the fallback. The caches are only read when the same document is rerun or `--force`d (to skip pages already paid for); the indexer, search and tutor never touch them. Deferred by the user (added 2026-10-04)
- Reprocess `LN_Analysis.pdf` and `LN_Linear Algebra.pdf` using whole-document batching and PyMuPDF dict-mode: their existing outputs predate the dict-mode/subscript reconstruction and whole-document batching improvements. Estimated cost under $0.30 total. Paused at user request pending review. (added 2026-10-04)
- Radical/square-root font encoding repair: in PDF font extractions (e.g. `Analysis_Exercises.pdf` page 6), square-root signs can extract as plain ASCII 'p' or missing glyphs due to broken ToUnicode font mappings; implement a regex/post-processing repair pass. (added 2026-10-04)

## Journal Article Discovery (`discovery/discover_journal_articles`)
- Playwright-driven automated download tier: for paywalled or institutional journals where manual download from `needs_manual_downloads.md` is tedious, build a Playwright browser automation script using institutional SSO. (added 2026-10-04)
- OpenAlex vs. Academic Hub semantic tag consolidation and topic clustering: test OpenAlex concept tags against the indexer's tag mining system on a larger corpus (>20 papers) to enable cross-vault reference and automatic topic clustering. (added 2026-10-04)
- Unified discovery-to-index convenience pipeline: create a wrapper CLI that orchestrates search/discovery (`pipeline.py`), conversion (`convert_journal_articles.py`), and index card generation in one command. (added 2026-10-04)

## Source Indexer and Search (`core/indexer`)
- Tag co-occurrence graph persistence: compute and persist the tag co-occurrence matrix in `.index/` so that related concepts across courses can be traversed in Obsidian graph view or via CLI search. (added 2026-10-04)
- Automated document-pairing detection: automatically detect and record links between problem sets and their corresponding solution sets, or lecture slides and lecture notes, in index cards. (added 2026-10-04)

## Resume Manager (`resume_manager`)
- Paired cover-letter generation: add a cover-letter generator (`cover_letter.py`) that uses the tailored application's selected facts, target company/role, and job description (design spec §10). (added 2026-10-04)
- Named-entity preservation verification in `fact_diff.py`: extend validation beyond numeric metrics and repeated openings to check that award names, degrees, and core tools are not dropped during tailoring. (added 2026-10-04)
- Generalized section header matching in `normalize.py`: extend `match_section_header()` synonyms and line-shape heuristics to support alternate source resume layouts beyond the initial master format. (added 2026-10-04)

## RAG Tutoring Agent (`agent/rag`)
- Persistent conversation and student history: persist REPL session transcripts and diagnostic records to disk (e.g. under `.sessions/` or student profile) so multi-turn context and mastery history survive process restarts. (added 2026-10-04)
- Automated third-model adjudication in `/verify`: implement an automated verification evaluator to resolve diagnostic ambiguities when student answers partially match retrieved context. (added 2026-10-04)
- Cross-course foundational retrieval testing: validate retrieval performance on multi-course queries (e.g. Econometrics questions requiring Math Camp matrix algebra lemmas). (added 2026-10-04)

## Visualization Sub-Agent (`agent/viz`)
- Template library expansion: add new Plotly visualization templates for recurring mathematical/economic concepts (e.g. utility maximization, IS-LM, consumer surplus) beyond the initial 4 templates. (added 2026-10-04)
- Parameter extraction from retrieved context: extract specific numbers, equations, or matrix values from retrieved passages to populate templates with course-specific data instead of default toy values. (added 2026-10-04)

## Audio Generator (`audio_generator`)
- Paragraph-level splitting fallback for oversized sections: in `sections.py`, split oversized sections by paragraph boundaries when individual markdown sections exceed the TTS chunk limit, preventing oversized audio parts. (added 2026-10-04)
- LLM summary-to-audio pipeline: build the direct workflow for generating audio from synthesized lecture summaries rather than raw note transcripts. (added 2026-10-04)
- Textbook chapter-boundary integration: connect `chapter_index.py` from `convert_textbook` to enable narrated audio overviews per textbook chapter. (added 2026-10-04)

## Notes Post-Processing (`pipelines/postprocess_notes`)
- Multi-directory batch post-processing: update `postprocess_notes.py` CLI to process multiple course directories in a single command. (added 2026-10-04)
- Statistical anomaly z-score calibration: tune the causal z-score and perplexity thresholds in `local_model_scoring.py` to reduce false positives on short or highly symbolic mathematical notes. (added 2026-10-04)

## Textbook Conversion (`pipelines/convert_textbook`)
Things to fix in post-processing?
- subscripts and superscripts seem to get mixed up a lot (Hansen)
- internal links are not preserved (Hansen)
- Table of Contents does not link to anything
- Some complex Latex contains errors (Hansen)
- Inline latex equations often yield bad formatting in output
	- Dropping some hats from estimators
- Could add internal links to obsidian when figures or sections are mentioned
- Printed TOC spurious entry repair in `chapter_index.py`: `parse_printed_toc()` extracts a spurious frontmatter entry in books like Hammack; add filtering for Roman-numeral or unnumbered frontmatter page markers. (added 2026-10-04)
- Front-matter image filter boundary tuning in `describe_images.py`: refine the filter to avoid dropping legitimate introductory diagrams near the start of Chapter 1. (added 2026-10-04)



Example from Hansen:

Latex Error:

Q_{XX}^{-1} = \begin{bmatrix} Q_{11} & Q_{12} \\ Q_{21} & Q_{22} \end{bmatrix}^{-1} \stackrel{\text{def}}}{=} \begin{bmatrix} Q_{11}^{-1} & Q_{12}^{-1} \\ Q_{21}^{-1} & Q_{22}^{-1} \end{bmatrix} = \begin{bmatrix} Q_{11}^{-1} & -Q_{11}^{-1} Q_{12}^{-1} Q_{22}^{-1} \\ -Q_{22}^{-1} Q_{21} Q_{11}^{-1} & Q_{22}^{-1} \end{bmatrix} \quad (2.43)



#### 2.24 OMITTED VARIABLE BIAS

Again, let the regressors be partitioned as in [\(2.41\)](#page-76-0). Consider the projection of *Y* on *X*<sup>1</sup> only. Perhaps this is done because the variables *X*<sup>2</sup> are not observed. This is the equation

$$Y = X'_1 \gamma_1 + u \quad (2.45)$$

$$\mathbb{E} [X_1 u] = 0.$$

Notice that we have written the coefficient as γ<sup>1</sup> rather than β<sup>1</sup> and the error as *u* rather than *e*. This is because (2.45) is different than [\(2.42\)](#page-76-0). Goldberger (1991) introduced the catchy labels **long regression** for [\(2.42\)](#page-76-0) and **short regression** for (2.45) to emphasize the distinction.

Typically,  $\beta_1 \neq \gamma_1$ , except in special cases. To see this, we calculate

$$\begin{aligned} n_1 &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 Y] \\ &= (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 (X'_1 \beta_1 + X'_2 \beta_2 + \epsilon)] \\ &= \beta_1 + (\mathbb{E}[X_1 X'_1])^{-1} \mathbb{E}[X_1 X'_2] \beta_2 \\ &= \beta_1 + \Gamma_{12} \beta_2 \end{aligned}$$

where <sup>12</sup> = *<sup>Q</sup>*−<sup>1</sup> <sup>11</sup> *Q*<sup>12</sup> is the coefficient matrix from a projection of *X*<sup>2</sup> on *X*1, where we use the notation from Section [2.22.](#page-76-0)

Observe that γ<sup>1</sup> = β<sup>1</sup> + 12β<sup>2</sup> = β<sup>1</sup> unless <sup>12</sup> = 0 or β<sup>2</sup> = 0. Thus the short and long regressions have different coefficients. They are the same only under one of two conditions. First, if the projection of *X*<sup>2</sup> on *X*<sup>1</sup> yields a set of zero coefficients (they are uncorrelated), or second, if the coefficient on *X*<sup>2</sup> in [\(2.42\)](#page-76-0) is zero. The difference 12β<sup>2</sup> between γ<sup>1</sup> and β<sup>1</sup> is known as **omitted variable bias**. It is the consequence of the omission of a relevant correlated variable.




Another example:

In general, many parameters of interest can be written as a function of moments of  $Y$ . Notationally,  $\beta = g(\mu)$  and  $\mu = \mathbb{E}[h(Y)]$ . Here, the  $Y$  are the random variables,  $h(Y)$  are functions (transformations) of the random variables, and  $\mu$  is the expectation of these functions.  $\beta$  is the parameter of interest, and is the (nonlinear) function  $g(\cdot)$  of these expectations.

In this context, a natural estimator of  $\beta$  is obtained by replacing  $\mu$  with  $\hat{\mu}$ . Thus  $\hat{\beta} = g(\hat{\mu})$ . The estimator  $\hat{\beta}$  is often called a **plug-in estimator**. We also call  $\hat{\beta}$  a moment, or moment-based, estimator of  $\beta$ , since it is a natural extension of the moment estimator  $\hat{\mu}$ .

natural extension of the moment estimator  $\hat{\mu}$ .  
Take the example of the variance  $\sigma^2 = \text{var} [Y]$ . Its moment estimator is

$$\hat{\sigma}^2 = \hat{\mu_2 - \hat{\mu}_1^2 = \frac{1}{n} \sum_{i=1}^n Y_i^2 - \left( \frac{1}{n} \sum_{i=1}^n Y_i \right)^2.$$

This is not the only possible estimator for  $\sigma^2$  (there is also the well-known bias-corrected estimator), but  $\hat{\sigma}^2$  is a straightforward and simple choice.





Formatting:

Technically, the estimator β in [\(3.7\)](#page-99-0) only exists if the denominator is nonzero. Since it is a sum of squares, it is necessarily nonnegative. Thus β exists if *<sup>n</sup> <sup>i</sup>*=<sup>1</sup> *<sup>X</sup>*<sup>2</sup> *<sup>i</sup>* > 0.


Inline formatting drops hats that are present in nearby equations, should be easy to fix.
#### 3.8 LEAST SQUARES RESIDUALS

As a by-product of estimation, we define the **fitted value** *Yi* <sup>=</sup> *<sup>X</sup> i* β and the **residual**

$$\hat{e}_i = Y_i - \hat{Y}_i = Y_i - X'_i \hat{\beta}. \quad (3.14)$$

Sometimes *Yi* is called the predicted value, but this is a misleading label. The fitted value *Yi* is a function of the entire sample, including *Yi*, and thus cannot be interpreted as a valid prediction of *Yi*. It is thus more accurate to describe *Yi* as a *fitted* rather than a *predicted* value.

Note that *Yi* <sup>=</sup> *Yi* <sup>+</sup> *ei*, and

$$Y_i = X'_i \hat{\beta} + \hat{e}_i. \quad (3.15)$$

We make a distinction between the **error** *ei* and the **residual** *ei*. The error *ei* is unobservable, while the residual *ei* is an estimator. These two variables are frequently mislabeled, which can cause confusion.




Confusing letters in script form:

<span id="page-106-0"></span>When *Xi* contains a constant, an implication of [\(3.16\)](#page-105-0) is

$$\frac{1}{n} \sum_{i=1}^n \hat{c}_i = 0. \quad (3.17)$$

Thus the residuals have a sample mean of 0 and the sample correlation between the regressors and the residual is 0. These are algebraic results and hold true for all linear regression estimates.



