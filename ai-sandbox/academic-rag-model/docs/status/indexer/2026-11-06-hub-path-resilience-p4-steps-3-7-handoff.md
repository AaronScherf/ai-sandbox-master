# Hub path resilience: steps 3 to 7 handoff (for a new Claude session, 2026-11-06)

Read this first, then grep (do not read whole) `2026-11-05-hub-path-resilience-p4-status.md` and the "Reconcile and review" / "Scan, preflight and vocabulary" sections of `core/indexer/README.md`. Spec: `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md`.

## State at handoff

- P3 (reconcile engine, review page) and P4 (scan hook, pipeline preflight, duplicate `hub_id` tool, vocabulary review items) are on `main` (PR #26, PR #28 merged 2026-11-06). Row 7 of the scenario matrix is green.
- `academic_notes` (separate repo `academic-notes-vault`) is committed and pushed through `7eaf8f0` (2026-11-06): 151 `hub_id` stamps (`cf8b8c2`), the microecon duplicate-id fix, new part_2 notes. The live hub has **0 duplicate `hub_id`s** (dry run 2026-11-06).
- **Nothing P3/P4 has been run for real against the live hub except `write_hub_ids` stamping and the duplicate dry run.** The live `hub_review export`, `repair`, review page, and the first `corpus_health scan` with the new findings are all still to do.
- Quirk: `academic_notes` shows ~208 files as modified, all **line-ending only** (working tree CRLF, repo blobs LF, `core.autocrlf=false`). They were hidden by git's cached stats until the index was rebuilt on 2026-11-06. Never `git add -A` there; stage explicit paths. Do not "fix" the line endings without asking Aaron (Obsidian Git / Direct Git Sync write that repo too).

## Ground rules (from CLAUDE.md and the P4 work)

- Follow `docs/WORKTREE_WORKFLOW.md`: use a `claude/<task>` branch and worktree for any repo write (code, docs). Only Aaron lands on `main`; never merge or push `main`. Stage explicit paths.
- Run Python as modules from `ai-sandbox/academic-rag-model` (worktrees have no `.venv`; system Python 3.13 works). Tests make zero API calls. Warn before any run estimated over $1. Full suite: `python tools/run_tests_chunked.py` (about 10 minutes).
- Before any step that writes to the hub: no transcribe/audio/rebuild python process running (`Get-CimInstance Win32_Process`), and `academic_notes` git status shows no changes of yours. Aaron commits `academic_notes`.
- Never print or commit secrets (`ai-sandbox/.env`). The repo is public.
- Pipelines now refuse (exit 2) on unresolved relink items or waiting exact moves; `--ignore-unresolved` bypasses. Expect this once step 3 raises real items.

## Step 3: first real reconcile on the live hub

HUB = `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub`.

1. Pure read first: `python -m tools.hub_review export --hub-root HUB --no-raise --out <scratch>\export.json` and `python -m tools.hub_review repair --hub-root HUB` (dry run, no `--apply`). Report: counts of exact moves, ambiguous items, orphans, and the top candidates with their basis/score. `--no-raise` writes nothing.
2. Show Aaron the exact moves before applying. `python -m tools.hub_review repair --hub-root HUB --apply` writes card paths in `.index/` (tracked in the hub repo) and the repair log `.index/reconcile_log.jsonl`; `undo REPAIR_ID` reverts one. Apply only with Aaron's go-ahead.
3. Then `export` without `--no-raise` to raise the ambiguous/orphan items (writes the local ledger and card `link_state`).

## Step 4: first real `corpus_health scan`

`python -m tools.corpus_health scan --config <config>` (config template `tools/corpus_health/corpus_health.example.json`; Aaron has a real one for the daily scan, see `tools/corpus_health/run_daily_scan.ps1`; ask where it lives if you cannot find it). It writes only the local ledger. Expect: relink/orphan items (from step 3), `vocab_name` items for folder names not yet in `hub_config.json`, possibly a "no hub_config.json" warning if the hub root is wrong, and the "N exact moves waiting" notice. Note which findings are new vs expected.

## Step 5: publish and validate the review page

`python -m tools.hub_review page --hub-root HUB` writes the page. Publish it as an Artifact with a `db` capability (load the `artifact-design` and `artifact-capabilities` skills first; this repo's convention is a checkbox/Link/Dismiss page, reference `core/indexer/offering_links.py`). Validate end to end in a browser: decisions → `decisions.json` → `python -m tools.hub_review apply decisions.json --hub-root HUB --dry-run`, then for real with Aaron's go-ahead. Specifically check the **`vocab_name` kind radios**, which have never been tried in a browser (proposed kind pre-selected, names are rendered with `textContent`). Expect to find page bugs; fix them on a branch.

## Step 6: tune similarity (only after step 3 shows real moves)

Constants in `core/indexer/reconcile.py`: `SIMILARITY_THRESHOLD=0.5`, `MAX_SIMILARITY_CANDIDATES=5`, `_W_STEM, _W_COURSE, _W_BODY = 0.6, 0.15, 0.25`, `MIN_SHARED_SHINGLES=12`, `_BODY_ALONE=0.7`. Judge them on the ranked candidates and Aaron's accept/decline decisions from step 5; change only with evidence, and add a regression test per change. If step 3 shows no ambiguous items, record "untuned, no data" and leave them.

## Step 7: P5 (`ACADEMIC_HUB_ROOT`)

Plan P5 first (spec phases table): a single `hub_root()` resolver (env `ACADEMIC_HUB_ROOT`, then `hub_config.json`, default `../academic-hub`) replacing per-module `../academic-hub` joins; move `TEXTBOOK_FOLDER_NAMES` and the `part_N` pattern into the hub config; make `tests/core/indexer/hub_fixture.make_hub` the shared temp-scaffold for hub-touching tests; NFD/NFC path normalization and alias matching in reconcile lookups. Acceptance: the full suite passes with `ACADEMIC_HUB_ROOT` pointing at a `tmp_path` scaffold. Write the plan as a doc on a `claude/` branch and ask Aaron before implementing (same as P4).

## Open follow-ups to fold in where natural (tracker: `docs/trackers/academic_hub_to_do.md`, Source Indexer and Search)

- Preflight is not wired into `postprocess_notes`, `convert_textbook`, `generate_video_notes`, `migrate_sources_to_resources`, the agent CLIs (`study_guide`, `summary_enhance`, `concept_graph`, `literature`).
- `ignore=True` still takes the write lock; `query`/`ask` run the full check; the scan reconciles outside the lock; an orphan-card duplicate finding persists after `--fix-duplicates --apply`.
- Excalidraw plain-JSON top-level `hub_id` is unverified (needs an Obsidian experiment).
- Git filter-driver gap in `core/indexer/reconcile_git.py`; copy limits (`.md` only); one full reconcile per `hub_review apply` decision.

## Suggested first message for the new session

> Continue hub path resilience from `docs/status/indexer/2026-11-06-hub-path-resilience-p4-steps-3-7-handoff.md`. Start with step 3 (pure-read dry runs only), report what the live hub shows, and wait for my go-ahead before any `--apply`.
