# Hub path resilience P3: reconcile and review (status, 2026-11-03)

Spec: `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md`. Usage: "Reconcile and review" in `core/indexer/README.md`.

## What shipped

- `hub_id` identity for notes (`core/indexer/hub_identity.py`, `tools/write_hub_ids.py`), clone-safe id handling, canonical content hash that ignores `hub_id` and location hints (`audio_generator/state.py` uses it too, so moves do not regenerate audio).
- `core/indexer/reconcile.py`: read-only `reconcile(hub_root)` returning `moved | orphan | ambiguous` differences (tiers: hub_id, hash, git rename, similarity).
- `core/indexer/reconcile_apply.py`: `apply_repairs` / `apply_one` / `undo_repair`, crash-safe repair log `.index/reconcile_log.jsonl`, `raise_relink_items`, `resolve`, `reject` backed by the corpus-health ledger.
- `core/indexer/review_envelope.py` and `tools/hub_review.py` (+ page HTML): one review page for relink, orphan, offering-link and pairing items; decisions come back as `decisions.json` and are applied through each module's resolve/reject. `hub_review repair [--apply]` / `undo REPAIR_ID` are the CLI for exact-move repairs.
- Acceptance matrix: `tests/core/indexer/test_reconcile_scenarios.py` (rows 1-6 pass; row 7, pipeline refusal, is a strict xfail until P4). Zero API calls anywhere.

## Design decisions and their costs

- R2: plain `.excalidraw` JSON gets a top-level `hub_id` in `hub_identity`, but `write_hub_ids` skips it by default (`--include-excalidraw-json`) because Excalidraw preserving unknown keys is unverified. Cost: those scenes have no id until verified.
- R4: repairs update card fields only (`path`, `rag_md_path`), never note frontmatter `source_*` hints (would write into the `academic_notes` repo). Cost: cached hints stay stale until a later phase.
- R9: notes with a pre-existing empty frontmatter block are not stamped (hash neutrality is not byte-decidable); reported as skipped. They get no id until given a real frontmatter key.
- R10: a content-tier card whose path exists is never hashed (tested: `test_content_tier_card_with_existing_path_is_not_hashed`). Hashing would auto-apply `moved` for a regenerated file with a stale copy. Cost: a derived file moved away while another file is created at the old path shows no difference.
- R11: `apply_one(new_path=...)` also accepts an `ambiguous` Difference when `new_path` is a candidate (needed by `resolve`); `apply_one_unlocked` is exposed for lock holders. The lock is not reentrant.
- R12: `reconcile_apply` lazily imports `tools.corpus_health` (ledger glue); store is injected, no cycle, but it is a core -> tools dependency. Always run via `python -m` from `academic-rag-model`.
- R13: `hub_review export/page` raise relink items (write the ledger and `link_state`) by default because the ledger must hold an item before it can be resolved. `--no-raise` gives a pure read.
- R14: the single-`duplicate_of_file_id` clone fallback in `find_clone_card` stays removed (no silent guess). A moved clone without a `hub_id` is flagged `orphaned` by the next `rebuild`, then repaired by its exact content hash (`hub_review repair --apply`), which clears the flag; the following `rebuild` sees it again. Cost: until `repair` runs, such a clone is out of search/pairing. Run `write_hub_ids --apply` before moving anything.
- Undo sticks: `apply_repairs` skips a move whose latest log status is `undone`; it is offered as an `ambiguous` relink item instead (`reconcile_apply.demote_undone`). Undoing a `resolve`-chosen relink reopens its ledger item (`StateStore.reopen`) and re-marks `link_state`.
- Scenario (e) (course folder renamed): every file matches exactly (hub_id for notes, byte hash for PDFs), so one `apply_repairs` fixes all and no review item is raised. Card `course` fields stay the old name (reconcile does not touch them).

## Deferred minors

- Identity: explicit `hub_id` arg not validated; `_insert_json_key` blind on malformed JSON; `strip_location_lines` and `_frontmatter_end` duplicate fence logic; whitespace-only frontmatter refused; `replace_hub_id` has no direct unit test and normalizes the id line; re-linking an existing lecture clone replaces its hub_id each time.
- Matching: `_ext`/old-text compare still casefold; APFS NFD/NFC not handled; foreign-id hit makes all content hits non-decisive (safe side); `byte_hash` basis also labels canonical-hash matches (evidence string says which); full-history `git log -M` of the hub path (now pathspec-limited) and O(n^2) rename chaining; no-API test is a tripwire only.
- Apply: `.index/reconcile_log.jsonl` is tracked (consider `.gitattributes merge=union`); `_recover` compares paths without `_norm` and ignores `rag_md_path`; claimed check uses `lower()` and is O(differences x cards); reject/raise interleave can leave a stale `link_state` mark until the next raise; reject on an applied-only item records nothing.
- Page/tool: the page disables an item's buttons once any decision (including defer) is in the db, so re-deciding needs a fresh page; `_CLOSED` omits `blocked`; one full reconcile per resolve/reject.
- Swapped stamped notes are offered to each other, but accepting is refused while the other card holds the path (no swap transaction); a resolve after a dismissal leaves the ledger declined, so undoing that repair reopens nothing; the patch path fills a missing card `hub_id` from its file without checking that no other card already holds that id.

## Fixed in the final wave

- C1: a moved unstamped clone no longer stays `orphaned`: `rebuild` clears the flag on every card it sees, and a repair clears it (logged as `was_orphaned`, restored by undo only if recorded).
- I2: `hub_review repair [--apply]` and `undo REPAIR_ID` subcommands; `export`/`page` print "N exact moves are waiting: run `repair`" to stderr; README no longer implies auto-apply elsewhere.
- I3: undo sticks (an undone move is never re-applied, it becomes a relink candidate); undoing a resolve-chosen repair reopens its ledger item and `link_state`.
- I4: two stamped notes that swapped paths are two `ambiguous` items offering each other's path (never `moved`), with truthful evidence.
- I5: a regenerated card keeps `hub_id` (from the file's stamp, else the old card) and `link_state` (`index_card.carry_note_identity`).
- M-a: `hub_identity` writes are atomic (temp file + `os.replace`).
- M-b: `tools/hub_review.py` docstring puts `--hub-root` after the subcommand and documents `repair`/`undo`.
- M-c: `compute_content_hash` docstring names the `hub_id` exclusion.
- M-d: `write_hub_ids` skips derived outputs (`processed_outputs/`, `*.rag.md`, `*.excalidraw.questions.md`, video notes) and reports them.
- M-e: the git rename scan is limited to the hub path (`-- .`) and a timed-out git call warns on stderr.
- M-f: removed the `_strip_location_lines` alias and the unreachable relink branch of `corpus_health.actions._blocked_reason`.
- M-g: README caveats (stamping re-runs the syllabus digest and legacy-hash audio once; stamp before moving notes) and this list.

## To-do

- P4: the scan hook must pass `sweep_kinds` or call `raise_relink_items` (a bare ledger refresh would sweep relink/orphan findings); preflight so pipelines refuse to run on an unresolved item they need (turns the xfail row green); fold the vocabulary learner in.
- P5: `ACADEMIC_HUB_ROOT` discovery.
- Verify Excalidraw keeps a top-level `hub_id` key in plain `.excalidraw` JSON, then decide on `--include-excalidraw-json` by default.
- Run `python -m tools.write_hub_ids --hub-root HUB` (dry run) on the live hub, review, then `--apply`; Aaron commits the changes in `academic_notes`. Do it BEFORE moving notes (moved clones are then matched by `hub_id`), and run the audio pipeline once first if a TTS re-run is unwanted.
- Publish the review page (`tools.hub_review page`) as an Artifact with a `db` capability and validate it in a browser end to end (decisions -> `decisions.json` -> `apply`).
- Tune similarity weights (`_W_STEM/_W_COURSE/_W_BODY`, `SIMILARITY_THRESHOLD`) on the real hub.
- One full reconcile per resolve/reject decision: batch `apply` over many decisions re-reconciles each time.
- NFD/NFC (APFS) path normalization in reconcile lookups.
- Alias matching is still exact-casefold.
