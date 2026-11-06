# Hub path resilience: steps 3 to 7 handoff (for a new Claude session, 2026-11-06)

> **OUTCOME (2026-11-06): FROZEN.** Steps 3 and 4 were run; the owner decided to freeze P3/P4 as built. Steps 5, 6 and 7 are **not planned**; do not start them without a new trigger (see "Outcome" below). The rest of this document is kept as the record of what was handed off.

## Outcome (2026-11-06)

Step 3 (pure read, nothing written to the hub), live hub:
- `hub_review export --no-raise`: 0 items. `hub_review repair` (dry run): 0 exact moves. 0 ambiguous items, 0 orphans, 0 false positives, no noise from derived files, `processed_outputs/`, `.rag.md` or the CRLF-only `academic_notes` files.
- Sanity check that the empty result is real and not a blind engine: all 359 cards in `.index/` (econometrics 98, math-camp 50, math_methods 62, microecon 149) point to paths that exist. No `.index/reconcile_log.jsonl` exists, so no repair has ever run.
- Owner-visible cost: nothing was stale, so nothing would have been noticed without the tool. The `hub_id` stamps and the duplicate-id fix had already removed the real problems.

Step 4 (`corpus_health scan` with the real config at `%LOCALAPPDATA%\CorpusHealth\scan.json`, 24 s, writes only the local ledger): 286 findings, **no relink, orphan or "exact moves waiting" findings**. The new P4 finding kind is `vocab_name` (16 findings: folder names not in `hub_config.json`, e.g. `class_2021`, `class_2022`, `2023_class`, `packet`, `reviews`, `sealed`, `tutoring`, `TA_solutions`, `student answers`, `Pat`, `Hannah`, `lab_3`, `Scripts`, three timestamp folders under microecon). These are vocabulary decisions for the owner, not defects. The other kinds (`note_transcription_missing` 144, `index_card_missing` 23, `textbook_conversion_missing` 20, `excalidraw_export_missing` 32, and so on) predate P4.

Found while scanning: on Windows, `python -m tools.corpus_health scan` writing to a redirected stdout exits 2 with `'charmap' codec can't encode character '́'` (an NFD filename). `PYTHONUTF8=1` works around it. Tracked in the to-do tracker; the scheduled task may already avoid it by how `run_daily_scan.ps1` captures output.

Decision: freeze. Not done and not planned: step 5 (publish and validate the review page; the `vocab_name` kind radios stay untried in a browser), step 6 (similarity thresholds stay untuned, "untuned, no data"), step 7 (P5 `ACADEMIC_HUB_ROOT`). Unwired pipelines stay in the tracker. Trigger to reopen: a real `hub_review export`/`scan` finding (a moved or renamed file that triggers a paid rebuild, or an ambiguous item), or a non-Windows hub.

Read this first, then grep (do not read whole) `2026-11-05-hub-path-resilience-p4-status.md` and the "Reconcile and review" / "Scan, preflight and vocabulary" sections of `core/indexer/README.md`. Spec: `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md`.

## State at handoff

- P3 (reconcile engine, review page) and P4 (scan hook, pipeline preflight, duplicate `hub_id` tool, vocabulary review items) are on `main` (PR #26, PR #28 merged 2026-11-06). Row 7 of the scenario matrix is green.
- `academic_notes` (separate repo `academic-notes-vault`) is committed and pushed through `7eaf8f0` (2026-11-06): 151 `hub_id` stamps (`cf8b8c2`), the microecon duplicate-id fix, new part_2 notes. The live hub has **0 duplicate `hub_id`s** (dry run 2026-11-06).
- **Nothing P3/P4 has been run for real against the live hub except `write_hub_ids` stamping and the duplicate dry run.** The live `hub_review export`, `repair`, review page, and the first `corpus_health scan` with the new findings are all still to do.
- Quirk: `academic_notes` shows ~208 files as modified, all **line-ending only** (working tree CRLF, repo blobs LF, `core.autocrlf=false`). They were hidden by git's cached stats until the index was rebuilt on 2026-11-06. By type: 123 `.md` (mostly `math-camp/` textbook `.rag.md` and `processed_outputs`, `ta_notes`, `handwritten_notes`, `problem_sets`), 59 `.json`, 8 `.css`, 6 `.tex`, 4 `.js`, 2 `.gitignore`; 20 are `.obsidian/plugins`. Every line of each file differs (`git ls-files --eol` shows `i/lf w/crlf`); content is identical. Exact cause unknown (a Windows tool rewrote them locally without committing). Never `git add -A` there; stage explicit paths. Do not "fix" the line endings without asking Aaron (Obsidian Git / Direct Git Sync write that repo too).

## Decision gate: is more work on this worth doing? (read before step 3)

P3/P4 may be more than the original small fix ("a moved file triggers a paid rebuild") needed. Aaron asked this directly on 2026-11-06 and the honest answer was "partly yes". Treat step 3 as the evidence, and say plainly in your step 3 report which case applies:

- **Few or zero real moves, no ambiguous items:** recommend freezing the system as built. Skip step 6 (record "untuned, no data"), do not plan P5 beyond a one-paragraph note, and leave the unwired pipelines in the tracker.
- **Real ambiguity (several ambiguous items with plausible candidates):** the similarity engine and review page are earning their keep. Proceed to steps 4, 5, 6.
- **Either way:** before steps 6 and 7, ask Aaron whether the work is worth doing. Do not start new feature work (new pipelines wired to preflight, new item kinds, new heuristics) on your own.

What to look for in the step 3 dry run:
1. Count of exact moves vs ambiguous vs orphans. Exact moves are the cheap, safe case (hash match, `repair` handles them).
2. For each ambiguous item: is the top candidate obviously right to a human glance? If the top-1 is nearly always right, the thresholds are fine. If it is often wrong or there are several near-ties, that is the tuning evidence for step 6.
3. Orphans: are they real deletions, or moves the engine failed to match (false negatives)? Spot-check a few against the vault.
4. False positives: anything proposed as moved that was not (e.g. same-stem notes across courses, templated files).
5. Noise: items raised for derived outputs, `processed_outputs/`, `.rag.md`, or the CRLF-only files below (they change mtimes and may trip the preflight fingerprint but must not create items).
6. Cost of living with it: would you, as the owner, have noticed these problems without the tool? If the answer is "no, nothing was stale", that supports freezing.

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

> Continue hub path resilience from `docs/status/indexer/2026-11-06-hub-path-resilience-p4-steps-3-7-handoff.md`. Read its "Decision gate" section first. I am not sure the P3/P4 work is proportionate to the original small fix, so treat step 3 as the evidence. Start with step 3 (pure-read dry runs only: export with `--no-raise`, and `repair` without `--apply`). Report counts of exact moves, ambiguous items and orphans, whether the top candidate is right for each ambiguous item, and any false positives or noise. Then tell me plainly whether the data says to freeze the system or keep tuning. Wait for my go-ahead before any `--apply`, any raise, and before starting steps 6 or 7. Do not begin new feature work.
