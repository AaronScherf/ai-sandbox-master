# Hub path resilience P4: scan hook, pipeline preflight, vocabulary learner (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Status:** plan only, written 2026-11-05. Nothing implemented. Owner approval needed before Task 1.

**Goal:** Detection fires in both places the spec names: the daily scan raises relink and vocabulary items, and a pipeline refuses to run on an unresolved item it needs. Row 7 of the scenario matrix goes green.

**Architecture:** One new module, `core/indexer/preflight.py`, owns the tree fingerprint and the "refuse" decision. The scan (`tools/corpus_health/cli.py`) calls the existing `raise_relink_items` and a new vocabulary pass. Review items for new folder names reuse the shared envelope and page. No new storage format; the fingerprint lives in the local corpus-health state directory.

**Tech Stack:** Python 3.13, pytest, existing `StateStore` ledger, `review_envelope`, `hub_review`. Zero API calls in any test.

**Spec:** `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md` (sections 5 and "Resolved open questions"). P3 state: `docs/status/indexer/2026-11-03-hub-path-resilience-p3-status.md`.

## Global Constraints

- Every test runs with model-client construction forbidden (the `_no_model_client` autouse fixture in `tests/core/indexer/test_reconcile_scenarios.py`). Any API call fails the test.
- The scan never mutates corpus files (spec section 5). It may write the local ledger only.
- Preflight and scan never auto-apply repairs. Exact moves are applied only by `hub_review repair --apply`.
- No preflight in landing checks (owner decision 4).
- Run Python as modules from `ai-sandbox/academic-rag-model` with `.venv`. Full suite: `python tools/run_tests_chunked.py`.
- Hub writes (live `academic_notes`) belong to the owner; implementation tasks touch fixtures in `tmp_path` only.

## What the code already does (verified 2026-11-05)

- `StateStore.refresh(findings, sweep_kinds=None)` already leaves `relink` and `orphan_card` alone: `SELF_REFRESHED_KINDS` is excluded from the default sweep (`tools/corpus_health/state.py:20,225`). The P3 status wording ("a bare refresh would sweep") is stale on this point. **The real gap is that nothing in the scan produces those items.** `tools/corpus_health/cli.py:77` calls only `store.refresh(report.findings)`.
- `raise_relink_items` writes the ledger **and** each card's `link_state: "unresolved"` in the tracked `.index/` (`reconcile_apply.py:404-431`). That conflicts with "scan never mutates corpus files", so Task 3 adds a ledger-only mode.
- Nothing refuses to use an unresolved card. `link_state` is read only by `review_envelope.is_unresolved`. There is no `preflight` anywhere.
- The vocabulary learner exists (`core/env/hub_vocab_learn.propose_vocabulary(hub_root, vocab) -> dict` with keys `category_candidates`, `group_candidates`, `ignore_candidates`, `unclassified`; each item `{"name", "courses"}`) and already skips names the vocabulary classifies. `tools.hub_vocabulary.confirm(config_path, name, kind, alias_of, replace)` stores an answer in `hub_config.json`.
- Row 7 is `test_pipeline_refuses_with_unresolved_item_it_needs` in `tests/core/indexer/test_reconcile_scenarios.py:203`, `xfail(strict=True)`, body `assert False`.

## Review Focus (inputs the spec implies but no existing test covers)

1. A pipeline run while the tree is unchanged since the last reconcile and an item is still open: must still refuse (the fast path reads the ledger, not only the fingerprint).
2. An open item for a *different course* than the pipeline needs: must not block it.
3. An exact move waiting (not yet repaired): the card points at a missing file, so a paid pipeline would regenerate. Must block, with a pointer to `hub_review repair`.
4. Lock held by a running pipeline when the scan wants to raise items: scan must degrade to a warning, not fail or hang.
5. Two files carrying the same `hub_id` (found live, see Task 4): must be reported, not silently trusted.

## File structure

| File | Change | Responsibility |
|---|---|---|
| `core/indexer/preflight.py` | create | `Needs`, `tree_fingerprint`, `check`, `require_resolved`, `UnresolvedLinksError` |
| `core/indexer/reconcile_apply.py` | modify `raise_relink_items*` | add `mark_link_state: bool = True` |
| `tools/corpus_health/cli.py` | modify `scan` branch (~line 72-81) | call relink pass and vocabulary pass after `store.refresh` |
| `core/indexer/duplicate_ids.py` | create | `find_duplicate_hub_ids`, `restamp_duplicates` |
| `core/indexer/review_envelope.py` | modify | `vocab_name_to_item`, `duplicate_id_to_item` |
| `tools/hub_review.py` | modify `collect`, `_dispatch` | list and apply `vocab_name` items via `tools.hub_vocabulary.confirm` |
| `core/indexer/index_search.py`, `pipelines/transcribe_notes/transcribe_notes.py`, `audio_generator/pipeline.py` | modify entry points | call `preflight.require_resolved` before any API client is built |
| `core/indexer/README.md` | modify "Reconcile and review" | document scan, preflight, escape hatch |
| `tests/core/indexer/test_preflight.py`, `test_scan_relink.py`, `test_duplicate_ids.py`, `test_vocab_items.py` | create | per task |

---

### Task 1: Preflight core (`core/indexer/preflight.py`)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Needs: courses: frozenset[str] | None = None; file_ids: frozenset[str] = frozenset()` (`courses=None` means the whole hub).
  - `tree_fingerprint(hub_root: str) -> str`: sha256 over sorted `(relpath, size, mtime_ns)` for files under `academic_notes/` and `academic_resources/`, skipping `.git`, `.obsidian`, `.index`.
  - `check(hub_root: str, needs: Needs, store=None) -> list[ReviewItem]`: returns the blocking items.
  - `require_resolved(hub_root: str, needs: Needs, store=None, *, ignore: bool = False) -> None`: raises `UnresolvedLinksError(items)` (message names the count and `python -m tools.hub_review page --hub-root <hub>`; also names `hub_review repair` when exact moves block); with `ignore=True` prints a one-line warning to stderr and returns.
  - `class UnresolvedLinksError(RuntimeError)` with `.items`.
- Consumes: `reconcile.reconcile`, `reconcile_apply.raise_relink_items_unlocked`, `review_envelope.difference_to_item`, `StateStore.entries(kinds=...)`, `index_card.find_card_by_file_id`.

Decisions:
- **Fingerprint storage is `<state_dir>/preflight.json`** (`default_state_dir(hub_root)`, local, under git common dir), not `.index/` as the spec's section 5 says. mtimes differ per machine, and `.index/` is tracked, so a stored fingerprint there would produce a diff on every run and be wrong on every other machine. The spec leaves fields to the builder; this is a deliberate deviation to confirm.
- Flow: fingerprint equal to stored -> read open ledger items only (no reconcile). Differs -> run `reconcile`, `raise_relink_items_unlocked(..., mark_link_state=False)`, store the new fingerprint, then read the ledger. A stored fingerprint is written only after a reconcile that finished.
- Blocking rule: `relink` items and waiting `moved` differences block when their card's `course` is in `needs.courses` (or `file_id` in `needs.file_ids`, or `courses is None`). `orphan` items warn on stderr and never block (the file is gone; nothing to read).

- [ ] **Step 1: Write failing tests** in `tests/core/indexer/test_preflight.py`: `test_unchanged_tree_still_refuses_on_open_item` (fingerprint stored, item open in ledger, `require_resolved` raises without calling `reconcile`, assert via monkeypatch counter == 0), `test_item_in_other_course_does_not_block`, `test_waiting_exact_move_blocks_and_names_repair`, `test_orphan_warns_but_does_not_block`, `test_ignore_flag_returns_with_warning`, `test_fingerprint_changes_on_rename_and_edit_and_ignores_obsidian_dir`.
- [ ] **Step 2: Run** `python -m pytest tests/core/indexer/test_preflight.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the signatures above. Walk with `os.scandir`; use `os.path.normcase` on the state-dir key as `default_state_dir` does.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `git add core/indexer/preflight.py tests/core/indexer/test_preflight.py` ; message `feat: add pipeline preflight core`.

### Task 2: Wire entry points and turn row 7 green

**Interfaces:** Consumes `require_resolved`, `Needs`.

Entry points and what each needs (implementer confirms each `main`/argv shape by reading it; not verified here):
- `index_search chunk --course X`, `rebuild`, `index-md`, `retag`: `Needs(courses={X})` or whole hub. `chunk` embeds passages (paid), so it is the row 7 pipeline.
- `transcribe_notes` and `audio_generator.pipeline`: the course(s) in their args.
- `query` and `ask` are read-only: **warn, never refuse**.
- Every refusing entry point gets `--ignore-unresolved` and calls preflight **before** `get_gemini_client` or any client construction.

- [ ] **Step 1: Replace row 7.** In `test_reconcile_scenarios.py`, remove the `xfail` marker and write `test_pipeline_refuses_with_unresolved_item_it_needs(tmp_path, store)`: build the rename-and-edit fixture from `test_rename_and_edit_raises_ranked_review_item` (line 115), `raise_relink_items`, then call the `chunk` entry point on course `econ` through its `main` with argv. Assert: exit is non-zero (`SystemExit` code 2), stderr contains `hub_review page`, the autouse `_no_model_client` fixture was never tripped, and `_digest(hub)` is unchanged. Then `resolve` the item and assert the same call gets past preflight (stub the work after it).
- [ ] **Step 2: Run** `python -m pytest tests/core/indexer/test_reconcile_scenarios.py -k pipeline_refuses -v`. Expected: FAIL (no preflight call yet).
- [ ] **Step 3: Add the calls** in the entry points above and the `--ignore-unresolved` flag.
- [ ] **Step 4: Run** the same command. Expected: PASS. Run `python -m pytest tests/core/indexer tests/pipelines tests/audio_generator -q`. Expected: no new failures (entry-point tests may need a hub with no open items; they get that by default because preflight finds nothing).
- [ ] **Step 5: Commit** explicit paths; message `feat: refuse pipelines on unresolved relink items`.

**Acceptance: row 7 passes with the `xfail` marker gone.** The suite must show `0 xfailed` for this file.

### Task 3: Scan raises relink items

**Interfaces:** `raise_relink_items(hub_root, differences=None, store=None, *, mark_link_state: bool = True)` and the `_unlocked` twin; with `False` it writes the ledger only and skips `set_link_state` (lines 429 and 431).

- [ ] **Step 1: Tests** in `tests/core/indexer/test_scan_relink.py`: `test_scan_raises_relink_item_in_ledger_without_touching_cards` (digest of `.index/` card shards identical before and after), `test_scan_does_not_sweep_existing_relink_items`, `test_scan_with_busy_write_lock_warns_and_continues` (patch `corpus_write_lock` to raise its timeout error; assert `report.errors` or a warning line mentions it and exit stays 0 or the existing incomplete code, whichever the scan uses for non-fatal warnings), `test_scan_notes_waiting_exact_moves_in_text_report` (informational line "N exact moves waiting: run hub_review repair", no new ledger kind).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the flag, then in `cli.py` after `store.refresh`: `raise_relink_items(str(config.academic_hub_root), store=store, mark_link_state=False)`. `hub_review` keeps the default `True`, so the page flow is unchanged.
- [ ] **Step 4: Run** `python -m pytest tests/tools/corpus_health tests/core/indexer -q`. Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 4: Duplicate `hub_id` detection

**Why now (finding):** two live notes carry `hub_id: fcf8dd35633a`: `econometrics/part_2/lecture_notes/Econometrics 2026-11-04 10.09.10.excalidraw.md` (since renamed `... LIML ...`, uncommitted) and `microecon/part_2/lecture_notes/Microeconomics 2026-10-22 10.13.17.excalidraw.md`. Facts from `academic_notes` history:
- Neither file had an id at `76a134d`; both gained exactly `hub_id: fcf8dd35633a` in the stamp commit `cf8b8c2`. Their contents differ (md5 differs, sizes differ), so they are not byte copies.
- The id is `uuid.uuid4().hex[:12]` (`hub_identity.new_hub_id`), `write_hub_id` returns an existing id untouched, and `write_hub_ids.apply` calls it once per file. **The stamper cannot produce a repeat on its own.** So the id was already present in one file, or was copied between them, between the stamping write and the commit. I have not proven which. Likely cause: the Excalidraw plugin or a duplicate-drawing action on one file while the stamper ran. This needs the owner's recollection or the Obsidian side to confirm.
- The microecon file in the owner's working tree now reads `hub_id: 1b1e67d2d8a5` (uncommitted), so someone already changed it; the committed state still has the duplicate. Leave it with the owner.
- What reconcile does today: `by_hub_id` returns a list. While both cards sit at their own paths, nothing happens (no difference). The failure appears on a move: a hub_id-tier card whose file moved finds two files with its id and returns `ambiguous` (safe, a review item). `find_card` by id and the P3 "patch path fills a missing card hub_id from its file" can still attach one id to two cards unnoticed. So today duplicates are latent, not corrupting.

**Interfaces:**
- `find_duplicate_hub_ids(hub_root: str) -> dict[str, list[str]]` (id -> hub-relative paths, only ids with 2+ files; also ids held by 2+ cards).
- `restamp_duplicates(hub_root: str, keep: dict[str, str], apply: bool = False) -> list[tuple[str, str, str]]`: for each duplicated id, keeps the file named in `keep` (default: the file the card currently points at, else the oldest by git first-commit) and calls `replace_hub_id` on the others; dry run by default; updates the card's `hub_id` for the restamped file. Returns `(path, old_id, new_id)`.
- `review_envelope.duplicate_id_to_item(...)`: type `duplicate_id`, subject = the paths, candidates = which file keeps the id.

- [ ] **Step 1: Tests** in `tests/core/indexer/test_duplicate_ids.py`: `test_two_files_same_id_reported`, `test_dry_run_writes_nothing` (digest equal), `test_apply_restamps_only_the_loser_and_updates_its_card`, `test_move_with_duplicate_id_is_ambiguous_not_moved` (documents current reconcile behavior as a regression test), `test_duplicate_reported_in_scan_text`.
- [ ] **Step 2: Run, expect FAIL. Step 3: Implement. Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit.** Repair against the live `academic_notes` is an owner-run step, after the quiet-hub check below; the plan does not run it.

### Task 5: Fold in the vocabulary learner

**Rule (owner-approved, spec "Resolved open questions" 1-2):** the scan raises one review item per *new* folder name; the answer is stored once through `confirm`; nothing is classified from an unconfirmed name.

**Interfaces:**
- `review_envelope.vocab_name_to_item(name: str, courses: list[str], proposed: str | None) -> ReviewItem`: `item_id = _digest("vocab_name", name.casefold())`, `type="vocab_name"`, `candidates = [{"kind": "category"|"group"|"ignore", "proposed": bool}]`.
- Scan: `propose_vocabulary(hub_root, load_vocabulary(hub_config))` -> one ledger finding per name, kind `vocab_name`, swept normally by the scan (a name that is later confirmed drops out of `propose_vocabulary`, so the finding vanishes). It is **not** added to `SELF_REFRESHED_KINDS`.
- `hub_review._dispatch` for `vocab_name`: accept with a chosen kind -> `tools.hub_vocabulary.confirm(config_path, name, kind, alias_of=None, replace=False)`; dismiss -> `store.decide(..., "declined", ...)` so the name is asked once (declined fingerprints stay declined across scans).
- Writing `hub_config.json` changes parsing for audio discovery and course-material signals, so the dispatch prints the `impact` summary line (`tools.hub_vocabulary.impact`) after confirm.

- [ ] **Step 1: Tests** in `tests/core/indexer/test_vocab_items.py`: `test_new_folder_name_raises_one_item`, `test_confirmed_name_not_raised_again`, `test_declined_name_stays_declined_across_scans`, `test_unclassified_single_course_name_is_raised_without_proposal`, `test_accept_writes_hub_config_via_confirm`, `test_scan_never_writes_hub_config`.
- [ ] **Step 2-4:** fail, implement, pass.
- [ ] **Step 5: Commit.**

### Task 6: Docs and trackers

- [ ] Update `core/indexer/README.md` "Reconcile and review" (scan behavior, preflight, `--ignore-unresolved`, duplicate-id tool, vocabulary items). Correct the stale sweep wording in the P3 status doc and append a P4 status section.
- [ ] Add/adjust tracker bullets per the placement table below. Move the P4 lines out of the P3 status "To-do".
- [ ] Full suite: `python tools/run_tests_chunked.py`. Expected: green, `0 xfailed` in `test_reconcile_scenarios.py`.

---

## Where each extra item belongs

| Item | Home | Why |
|---|---|---|
| Duplicate `hub_id` (`fcf8dd35633a`) | **P4 Task 4** | Detection belongs with the scan; reconcile handles it safely but silently today |
| Excalidraw top-level `hub_id` in plain `.excalidraw` JSON | **Tracker** (Source Indexer and Search) | Needs a manual experiment in Obsidian (does the plugin keep an unknown top-level key on save?). No P4 code depends on it. The live hub's scenes appear to be `.excalidraw.md` (frontmatter), which is already stamped. Verify the plain-JSON case before changing the `--include-excalidraw-json` default |
| Git filter-driver gap in `reconcile_git.py` | **Tracker** (already there) | Security hardening, independent of P4. Approach already leaning: refuse nested repos whose local config defines `filter.*`. Reasonable as a small Codex task |
| Similarity thresholds (`MIN_SHARED_SHINGLES=12`, `_BODY_ALONE=0.7`, `_W_*`, `SIMILARITY_THRESHOLD=0.5`) | **Tracker** | Cannot be tuned without real moves on the live hub; blocked on `hub_review export` against it |
| Copies only for `.md`; PDF twins stay a single link; undoing a relink leaves copy cards | **Tracker** | Known limits of the P3 copy feature, no dependency from P4 |
| `hub_review apply` runs one reconcile per decision | **Tracker**, revisit after Task 3 | Cost scales with decisions; scan/preflight each do one reconcile, so P4 does not make it worse. A `reconcile` result cache keyed on the Task 1 fingerprint would fix both, worth doing if apply batches get large |
| NFD/NFC path normalization; exact-casefold alias matching | **P5** | Pairs with root discovery and cross-platform path handling (spec "Windows path-case handling"). Not triggered by Windows hubs today |

## Test strategy

- Unit and fixture tests per task on `tmp_path` hubs from `tests/core/indexer/hub_fixture.py`, `StateStore(tmp_path / "state")`, the fake write lock. No network, no model client.
- Acceptance: row 7 (Task 2). Also keep rows 1-6 and `test_content_tier_card_with_existing_path_is_not_hashed` green.
- Regression guard: a test that a hub with no open items runs every wired entry point unchanged (preflight is a no-op).

## Preconditions before any live-hub step (none are in this plan)

Before the owner runs the duplicate-id repair or `hub_review repair --apply` on the real hub: no transcribe, audio or rebuild Python process running; `academic_notes` has no uncommitted changes from this work; the owner commits `academic_notes`. At the time of writing, `academic_notes` has uncommitted owner changes (deletions, Excalidraw edits) and the `cf8b8c2` stamp commit is unpushed. Three `python` processes were running during this session and could not be identified from here.

## P5 outline: `ACADEMIC_HUB_ROOT`

1. A single `hub_root()` resolver (env var `ACADEMIC_HUB_ROOT`, then `hub_config.json`, default `../academic-hub`), replacing per-module `../academic-hub` joins; every CLI's `--hub-root` defaults to it.
2. Move `TEXTBOOK_FOLDER_NAMES` and the `part_N` pattern into the hub config where they still sit in code.
3. Temp-scaffold fixtures: `make_hub` becomes the shared scaffold for all hub-touching tests, so tests no longer assume the checked-in hub.
4. NFD/NFC normalization and alias matching in reconcile lookups.
5. Acceptance: the full suite passes with `ACADEMIC_HUB_ROOT` pointing at a scaffold in `tmp_path`, and a public clone with no hub runs the tests.

## Decisions for the owner

1. Fingerprint in the local state dir instead of `.index/` (Task 1).
2. Orphans warn, never block; waiting exact moves block (Task 1).
3. The scan writes the ledger only, never `link_state` (Task 3). This means cards are marked unresolved only after `hub_review export/page` or a preflight reconcile that opts in; preflight reads the ledger, so nothing depends on the mark.
4. Declined vocabulary names are never asked again (Task 5).

## Self-review

Spec coverage: scan hook (Task 3), preflight (Tasks 1-2), vocabulary fold-in (Task 5), row 7 (Task 2), duplicate ids (Task 4), docs (Task 6). Gaps: the entry-point argv shapes in Task 2 and the lock-busy error type in Task 3 are not verified; the implementer reads them first. The cause of the duplicate id is not proven (Task 4).
