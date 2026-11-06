# Hub path resilience P4: scan, preflight, vocabulary (status, 2026-11-05)

Spec: `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md`. Previous phase: `2026-11-03-hub-path-resilience-p3-status.md`. Usage: "Reconcile and review" in `core/indexer/README.md`. Zero API calls anywhere.

## What shipped

- `core/indexer/preflight.py`: `Needs`, `tree_fingerprint`, `check`, `require_resolved`, `enforce`, `UnresolvedLinksError`. Refusing entry points fail closed; read-only modes warn. Orphans warn; open relink items and waiting exact moves block. `raise_relink_items*` gained keyword `mark_link_state` (False = ledger only).
- Entry points wired: `index_search` chunk / rebuild / index-md `--apply` / retag (refuse); `query`/`ask` and read-only modes warn (`chunk`/`retag --dry-run`, `index-md` without `--apply`, `rebuild --plan`); `transcribe_notes` (refuses unless `--dry-run` without `--submit`/`--collect`); `audio_generator.pipeline`. `--ignore-unresolved` bypasses. Refusal is `SystemExit(2)` pointing at `python -m tools.hub_review page --hub-root <hub>` (and `hub_review repair` for waiting moves). Acceptance row 7 (`test_pipeline_refuses_with_unresolved_item_it_needs`) is green; the xfail is removed.
- Scan (`tools/corpus_health/cli.py`): after `store.refresh` it raises relink/orphan items via `raise_relink_items(mark_link_state=False)` (skipped with `--no-state`); adds `duplicate_hub_id` and `vocab_name` findings (before refresh); non-fatal `warnings`/`notices` on `ScanReport`; notice "N exact moves waiting: run hub_review repair".
- `core/indexer/duplicate_ids.py` and `python -m tools.write_hub_ids --fix-duplicates [--apply]` (dry run default).
- `vocab_name` review items: `tools/corpus_health/vocab.py`, `review_envelope.vocab_name_to_item`; `hub_review` lists them and applies accepted ones through `tools.hub_vocabulary.confirm`.

## Decisions and costs

- Fingerprint and remembered waiting moves live in `<state_dir>/preflight.json`, not `.index/` (deviation from spec section 5): mtimes are per machine and `.index/` is tracked. Cost: each machine pays one full reconcile after a pull. Waiting exact moves are not ledger items, so they are stored in the file and count only while the card path still equals the recorded old path.
- Fail closed for refusing entry points (an error inside preflight blocks the run); read-only modes only warn when preflight itself cannot run. Escape hatch: `--ignore-unresolved`.
- Orphans warn, never block (a file with no candidate is not something a pipeline can wait on). Relink items and waiting exact moves block.
- The scan writes the ledger only, never `link_state`; cards are marked unresolved after `hub_review export/page` or a preflight reconcile that opts in. Preflight reads the ledger, so nothing depends on the mark.
- Declined vocabulary names are asked once (never re-raised).

## Duplicate hub_id finding

Two live notes in `academic_notes` carried `hub_id` `fcf8dd35633a` after the stamp commit `cf8b8c2`. Neither had an id at `76a134d`, and their contents differ. The stamper cannot produce a repeat on its own; the cause is not proven. Reconcile handled it safely but silently. P4 now reports it as a scan finding and offers `write_hub_ids --fix-duplicates`. The repair is owner-run and was NOT run on the live hub.

## Deferred minors (P4)

- Preflight: `_KIND_TO_TYPE` KeyError if `SELF_REFRESHED_KINDS` grows; fast path is blind to `.index` shard changes from a git pull; `demote_undone` applied twice per reconcile; `_save` leaks a temp file on `json.dump` error; no test for a waiting move in another course.
- Entry points: `query`/`ask` run the full check (reconcile and state writes) though read-only; `--dry-run` and `index-md` without `--apply` refuse in some paths while `rebuild --plan` warns (inconsistent rule); `ignore=True` still takes the write lock and runs the check; `--dry-run` refused on a non-git hub; `_link_preflight` docstring says read-only modes build no client but `chunk`/`retag --dry-run` do; no subprocess test of a real exit 2 in the transcribe CLI.
- Scan: moved-count notice is computed before `demote_undone` (overstates); warning lacks the exception type name; no test that a successful second raise keeps items; the lock is faked in all tests.
- Duplicate ids: `relpath` ValueError on cross-drive in `_first_commit_time`; git pathspec not `:(literal)`; the orphan-card duplicate finding persists after `--fix-duplicates --apply`; hash neutrality untested for no-frontmatter and CRLF files.
- Vocabulary: no `hub_config.json` means the feature is silently off (should warn, `cli._add_vocab_findings`); the confirm-refused path is untested (and `SystemExit` is not caught by `except Exception`); no real apply run over an accepted `vocab_name`.

## To-do

- Owner, before any live-hub step: confirm the hub is quiet (no transcribe, audio or rebuild process running) and `academic_notes` has no uncommitted changes from this work.
- Run `python -m tools.write_hub_ids --hub-root HUB --fix-duplicates` (dry run) on the live hub, review which note keeps `fcf8dd35633a`, then `--apply`, and commit `academic_notes`.
- Then the P3 live steps still pending: stamping check, `hub_review repair` dry run, publish and validate the review page.
- P5: `ACADEMIC_HUB_ROOT` discovery, NFD/NFC and alias matching. Tracker bullets are in `docs/trackers/academic_hub_to_do.md` (Source Indexer and Search).
