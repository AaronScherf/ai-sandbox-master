# Hub Path Resilience P3: Reconcile Engine and Review Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Moves and renames of hub files self-repair (single exact match) or become review items (ambiguous/weak), with no API calls, no silent wrong links and no deletions.

**Architecture:** `hub_id` gives authored Markdown/Excalidraw a stable identity; `core/indexer/reconcile.py` snapshots the tree, matches it against cards (id/hash, then git renames, then ranked similarity) and returns typed differences; an apply module repairs exact matches (logged, undoable) and emits envelope items for everything else; relink items go in the corpus-health ledger and are answered on one interactive Artifact page, each applied through reconcile's own `resolve`/`reject` (the `offering_links.py` pattern).

**Tech Stack:** Python 3.13, pytest, `git` CLI (rename detection), existing `core/indexer` + `tools/corpus_health` modules.

**Spec:** `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md` (sections 1, 4, 5, 6, Phases, Acceptance, Decisions). Handoff brief: P3 section. P4 (scan/preflight/vocabulary-learner fold-in) and P5 (`ACADEMIC_HUB_ROOT`) get their own plans after this lands.

## Global Constraints

- Zero API calls in every test; the model client is mocked to raise on any call.
- Auto-repair only for a single exact match (byte hash / `hub_id`); logged and reversible. Never relink on similarity alone; never delete anything.
- `hub_id` is written into `academic_notes/` (separate repo): dry-run by default, say so before running with `--apply`; Aaron commits there.
- Canonical content hash must stay compatible: adding a `hub_id` line must not change any card's `content_hash` (strip it like `LOCATION_FIELDS`; `content_hash_matches` legacy fallback stays).
- No preflight in landing checks. One phase per branch (`claude/hub-path-p3-reconcile`, worktree per `docs/WORKTREE_WORKFLOW.md`); core changes run `python -m tools.run_tests_chunked` (~14 min, close memory-heavy programs).
- Windows: CRLF files (Edit tool or Python `newline=""`), worktrees lack `academic_notes/` and `.env`. Stage explicit paths only.
- Review surface is an interactive Artifact page with decisions in its `db` collection (`academic-rag-model/CLAUDE.md`, Scope); load `artifact-capabilities` before writing it.

## Review Focus

- Two identical files after a move (same hash, two candidates): review item, neither linked.
- Case-only rename on Windows (`Notes.md` -> `notes.md`): treated as a move/no-op, not an orphan plus a new file.
- A note with no frontmatter or a CRLF/BOM file when writing `hub_id`: written without corrupting bytes; second run is a no-op.
- Card whose file was deleted and another file with similar stem appears: orphan reported, similarity candidate only suggested.
- Interrupted repair (crash after card write, before log line): re-running reconcile is idempotent.

## File Structure

- Create `core/indexer/hub_identity.py`: `hub_id` generate/read/write for `.md` (frontmatter) and `.excalidraw` (top-level JSON key).
- Create `core/indexer/reconcile.py`: snapshot, matching, classification (`Difference`), `reconcile(hub_root) -> ReconcileResult`.
- Create `core/indexer/reconcile_git.py`: `git_renames(repo_root) -> dict[str, str]` old->new relative paths.
- Create `core/indexer/reconcile_apply.py`: `apply_repairs`, `undo_repair`, `resolve`, `reject`, repair log.
- Create `core/indexer/review_envelope.py`: shared item envelope + converters.
- Create `tools/write_hub_ids.py`, `tools/hub_review.py` (export items / apply decisions).
- Modify `core/indexer/index_card.py` (`IDENTITY_FIELDS` stripped from canonical hash; `find_clone_card`), `core/indexer/index_search.py:411-421` (`_clone_card_id`), `core/indexer/duplicate_check.py:386-426` (new clones get stored id), `audio_generator/state.py:24` (canonical hash), `tools/corpus_health/discovery.py` (no change in P3; P4 adds the scan hook).
- Tests: `tests/core/indexer/test_hub_identity.py`, `test_reconcile_match.py`, `test_reconcile_apply.py`, `test_review_envelope.py`, `test_reconcile_scenarios.py` (acceptance matrix, reuses `hub_fixture.py`), `tests/audio_generator/test_state_hash.py`, `tests/tools/test_write_hub_ids.py`, `tests/tools/test_hub_review.py`.

---

### Task 1: `hub_id` identity and hash compatibility

**Files:** Create `core/indexer/hub_identity.py`, `tests/core/indexer/test_hub_identity.py`; modify `core/indexer/index_card.py:89-135`.

**Interfaces:**
- Produces: `new_hub_id() -> str` (12 hex chars); `read_hub_id(path: str) -> str | None`; `write_hub_id(path: str, hub_id: str | None = None) -> str` (returns existing id if present; never overwrites); `IDENTITY_FIELDS = ("hub_id",)` in `index_card.py`, stripped by `_strip_location_lines` alongside `LOCATION_FIELDS`.

- [ ] **Step 1: Write failing tests** in `test_hub_identity.py`: `test_write_then_read_roundtrip`, `test_second_write_keeps_id` (same id, file bytes unchanged), `test_crlf_and_bom_preserved` (only one added line, CRLF line ending), `test_no_frontmatter_gets_block`, `test_excalidraw_json_gets_top_level_key` (JSON still parses, other keys equal), and `test_hub_id_line_does_not_change_content_hash`: `compute_content_hash` equal before/after `write_hub_id`, and `content_hash_matches(path, old_legacy_hash)` still true for a file whose old hash was stored with no id line... (legacy hash of the new file differs; assert only canonical equality).
- [ ] **Step 2: Run** `python -m pytest tests/core/indexer/test_hub_identity.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `hub_identity.py` with byte-level frontmatter edit (reuse the split logic of `_strip_location_lines`; do not round-trip through `render_frontmatter`, which would reorder/reformat). For `.excalidraw`: verify first that Excalidraw/Obsidian preserve an unknown top-level key on save; if not, store the id in the scene's `appState`-independent `"hub_id"` only after confirming, else fall back to a `<name>.excalidraw.id` free approach is NOT allowed (no sidecars, spec section 2) -- stop and ask Aaron. Extend `_strip_location_lines` to also drop `IDENTITY_FIELDS`.
- [ ] **Step 4: Run** the new tests plus `tests/core/indexer/test_content_hash.py tests/core/indexer/test_stale_hash_compat.py`. Expected: PASS.
- [ ] **Step 5: Commit** explicit paths: `feat(indexer): hub_id identity and hash-neutral id line`.

### Task 2: `tools/write_hub_ids.py` and stable clone ids

**Files:** Create `tools/write_hub_ids.py`, `tests/tools/test_write_hub_ids.py`, `tests/core/indexer/test_clone_card_lookup.py` (extend); modify `index_card.py:443-453`, `index_search.py:411-421`, `duplicate_check.py:386-426`.

**Interfaces:**
- Consumes: `write_hub_id`, `read_hub_id`.
- Produces: `python -m tools.write_hub_ids [--hub-root P] [--apply]` (dry-run lists would-write count per course; `--apply` writes `hub_id` to every authored `.md`/`.excalidraw` under `academic_notes/` and sets `hub_id` on the matching card); cards gain `hub_id`. `find_clone_card(cards, duplicate_of_file_id, rel_md_path, hub_id: str | None = None)`: match `hub_id` first, then exact path; the single-`duplicate_of_file_id` fallback is removed. New clone cards (`duplicate_check`) get a generated `hub_id` written to the clone note and card; `_clone_card_id` returns the card's existing `file_id` when found, and only derives a new id for a clone that has no card.

- [ ] **Step 1: Failing tests**: `test_dry_run_writes_nothing`; `test_apply_writes_ids_and_card_hub_id`; `test_apply_is_idempotent`; `test_find_clone_card_prefers_hub_id_over_path`; `test_moved_clone_with_hub_id_keeps_its_card`; `test_two_clones_of_one_canonical_without_hub_id_returns_none` (no silent pick).
- [ ] **Step 2: Run** them; expected FAIL.
- [ ] **Step 3: Implement** the tool (reports "writes into academic_notes/, a separate repo" on `--apply`) and the three modifications; update callers of `find_clone_card` found by `Grep find_clone_card`.
- [ ] **Step 4: Run** `python -m pytest tests/tools/test_write_hub_ids.py tests/core/indexer/test_clone_card_lookup.py tests/core/indexer/test_duplicate_check.py tests/core/indexer/test_index_search.py -v`. Expected PASS.
- [ ] **Step 5: Commit** `feat(indexer): hub_id writer tool and stored clone ids`.

### Task 3: Snapshot, matching, git renames

**Files:** Create `core/indexer/reconcile.py`, `core/indexer/reconcile_git.py`, `tests/core/indexer/test_reconcile_match.py`.

**Interfaces:**
- Produces: `@dataclass Difference(kind: Literal["moved","orphan","untracked","ambiguous"], file_id: str, old_path: str, candidates: list[Candidate], evidence: str)`; `@dataclass Candidate(path: str, basis: Literal["hub_id","byte_hash","git_rename","similarity"], score: float)`; `snapshot(hub_root: str) -> dict[str, FileEntry]` (rel path with `/`, casefolded key for Windows case handling, size, mtime; hashes computed lazily and only for paths not already at their card's `path`); `git_renames(repo_root: str) -> dict[str, str]` via `git diff -M --name-status HEAD` plus `git log --follow` for cards still unresolved; `reconcile(hub_root: str) -> list[Difference]`. Pure read: never writes.
- Rules: card path exists and hash matches -> no difference. Else exactly one candidate by `hub_id`/byte hash -> `moved`. Several exact candidates -> `ambiguous`. Git rename supplies a candidate only when no exact one exists and is `moved` only if the file content hash (canonical) also matches; otherwise `ambiguous` with that candidate. Similarity (stem + course + body shingle Jaccard, builder's choice) yields `ambiguous` candidates with `basis="similarity"` only. No candidates -> `orphan`.

- [ ] **Step 1: Failing tests** (fixture hub, cards written with `save_shard`): `test_renamed_file_same_content_is_moved`, `test_nested_one_layer_is_moved`, `test_identical_copies_after_move_are_ambiguous` (two candidates, none chosen), `test_rename_and_edit_is_ambiguous_with_similarity_candidate_ranked_first`, `test_deleted_file_is_orphan_and_nothing_removed`, `test_case_only_rename_is_not_orphan`, `test_authored_note_matched_by_hub_id_after_edit`, `test_reconcile_makes_no_api_call` (client fixture raises).
- [ ] **Step 2: Run**; expected FAIL.
- [ ] **Step 3: Implement** per rules; use `parse_hub_path` for course/category context, not position parsing.
- [ ] **Step 4: Run** `python -m pytest tests/core/indexer/test_reconcile_match.py -v`. Expected PASS.
- [ ] **Step 5: Commit** `feat(indexer): reconcile snapshot and matching`.

### Task 4: Auto-repair, log, undo

**Files:** Create `core/indexer/reconcile_apply.py`, `tests/core/indexer/test_reconcile_apply.py`.

**Interfaces:**
- Consumes: `Difference`, `update_card_paths`, `set_card_fields`.
- Produces: `apply_repairs(hub_root: str, differences: list[Difference]) -> list[RepairRecord]` (only `kind == "moved"`; updates `path`, `rag_md_path`, location hints in frontmatter via canonical-hash-neutral edit; appends `{repair_id, file_id, old, new, ts}` to `.index/reconcile_log.jsonl` BEFORE the card write, marks `done` after); `undo_repair(hub_root: str, repair_id: str) -> bool`; `RepairRecord` dataclass.

- [ ] **Step 1: Failing tests**: `test_move_repairs_card_path_and_hash_still_valid`; `test_repair_logged_and_undo_restores_card`; `test_rerun_after_interrupted_repair_is_idempotent` (log line present, card not written); `test_ambiguous_and_orphan_are_never_applied`.
- [ ] **Step 2: Run**; expected FAIL. **Step 3: Implement.** **Step 4: Run** the file; expected PASS.
- [ ] **Step 5: Commit** `feat(indexer): logged reversible reconcile repairs`.

### Task 5: Review envelope, ledger integration, resolve/reject

**Files:** Create `core/indexer/review_envelope.py`, `tests/core/indexer/test_review_envelope.py`; extend `reconcile_apply.py`; add finding kind `relink` handling in `tools/corpus_health` (state ledger only; no scan hook until P4).

**Interfaces:**
- Produces: `@dataclass ReviewItem(item_id: str, type: str, subject_ids: list[str], candidates: list[dict], status: Literal["pending","accepted","declined","deferred"], created: str, updated: str)`; `difference_to_item(d: Difference) -> ReviewItem` (type `"relink"`, deterministic `item_id` from file_id + sorted candidate paths); `offering_link_to_item(entry: dict) -> ReviewItem` and `pairing_to_item` for the other two ledgers (read-only adapters, no storage merge); `resolve(hub_root, file_id, chosen_path) -> bool` (repair via Task 4 logic, writes log) and `reject(hub_root, file_id) -> bool` (records dismissal so it is not re-raised; leaves card unlinked). Unresolved relink cards are skipped by consumers (`Catalog.lookup`/pairing) -- add a card field `link_state: "unresolved"` set when an item is raised, cleared on resolve.

- [ ] **Step 1: Failing tests**: `test_ambiguous_difference_becomes_pending_relink_item_and_card_marked_unresolved`; `test_item_id_stable_across_runs`; `test_resolve_with_chosen_candidate_repairs_and_clears_unresolved`; `test_resolve_with_path_not_in_candidates_refused`; `test_reject_dismisses_and_is_not_reraised`; `test_envelope_adapters_cover_offering_links_entry`.
- [ ] **Step 2: Run**; FAIL. **Step 3: Implement**, storing relink findings through `StateStore.refresh([Finding(kind="relink", ...)])`. **Step 4: Run** `python -m pytest tests/core/indexer/test_review_envelope.py tests/core/indexer/test_reconcile_apply.py tests/tools -k "corpus_health or review" -v`; PASS.
- [ ] **Step 5: Commit** `feat(indexer): shared review envelope and relink resolve/reject`.

### Task 6: Shared review Artifact page and `tools/hub_review.py`

**Files:** Create `tools/hub_review.py`, `tests/tools/test_hub_review.py`, the page source `tools/hub_review_page.html`.

**Interfaces:**
- Produces: `python -m tools.hub_review export [--out PATH]` (pending items from the three ledgers as envelope JSON); `python -m tools.hub_review apply DECISIONS.json` (each decision `{item_id, action: "accept"|"decline"|"defer", chosen: str|None}` dispatched to the owning module's resolve/reject; unknown/stale ids reported, never fatal). Page: one checkbox/Link/Dismiss row per item showing ranked candidates, decisions in the page's `db` collection, grouped by item type.

- [ ] **Step 1: Failing tests** (apply path only; the page is checked manually): `test_export_lists_items_from_all_three_ledgers`; `test_apply_dispatches_relink_to_reconcile_resolve`; `test_apply_dispatches_offering_link_to_offering_links_resolve`; `test_stale_item_id_reported_not_raised`.
- [ ] **Step 2: Run**; FAIL. **Step 3: Implement** the tool. Read how the existing offering-links review artifact moves decisions (`core/indexer/offering_links.py`, reference artifact in CLAUDE.md) and mirror it; load `artifact-capabilities`, publish a private page with the `db` capability, then read decisions via `ArtifactData`. **Step 4: Run** tests; PASS; open the published page and answer one fixture item end-to-end.
- [ ] **Step 5: Commit** `feat(tools): hub_review export/apply and shared review page`.

### Task 7: Audio state hash

**Files:** Modify `audio_generator/state.py:24-26`; create `tests/audio_generator/test_state_hash.py`.

**Interfaces:** `compute_content_hash(md_path) -> str` becomes the canonical hash (location + `hub_id` lines stripped); `needs_regeneration` also accepts the stored legacy raw-byte hash (new `legacy_content_hash(md_path)`; callers at `pipeline.py:104,237,293` unchanged except they pass both).

- [ ] **Step 1: Failing tests**: `test_moved_note_with_rewritten_source_lines_does_not_regenerate`; `test_state_stored_with_legacy_hash_does_not_regenerate_until_content_changes`; `test_body_edit_regenerates`.
- [ ] **Step 2: Run**; FAIL. **Step 3: Implement** reusing `index_card._strip_location_lines` (make it public as `strip_location_lines`). **Step 4: Run** `python -m pytest tests/audio_generator -q`; PASS.
- [ ] **Step 5: Commit** `fix(audio): hash notes canonically so moves do not regenerate audio`.

### Task 8: Acceptance matrix and docs

**Files:** Create `tests/core/indexer/test_reconcile_scenarios.py`; modify `core/indexer/README.md`; add status doc `docs/status/indexer/2026-11-03-hub-path-resilience-p3.md`.

- [ ] **Step 1: Write the matrix tests** against `make_hub`, all with a client fixture that raises on any call: `test_nest_one_layer`, `test_rename_file_auto_repairs`, `test_rename_and_edit_raises_ranked_review_item`, `test_scenario_e_course_folder_renamed_is_one_review_item_or_all_exact_repaired` (assert whichever behavior Task 3 implements: exact-hash matches auto-repair every file, so assert zero pending items and every card path updated), `test_two_identical_files_after_move_review_neither_linked`, `test_delete_file_reports_orphan_deletes_nothing`. The 7th row (pipeline refuses with unresolved item) is P4; add `xfail(strict=True, reason="P4 preflight")`.
- [ ] **Step 2: Run** `python -m pytest tests/core/indexer/test_reconcile_scenarios.py -v`. Expected PASS (one xfail).
- [ ] **Step 3: Docs**: README section "Reconcile and review" (commands, repair log, undo, `write_hub_ids` caveat); status doc with live To-do (P4/P5 pointers, unresolved: alias matching still exact-casefold).
- [ ] **Step 4: Full suite** `python -m tools.run_tests_chunked` (~14 min). Expected: all pass.
- [ ] **Step 5: Commit** `test(indexer): reconcile acceptance matrix; docs`.

---

## Self-review notes

- Spec coverage: identity tiers (T1-2), clone ids (T2), matching order (T3), actions (T4-5), review page + ledgers (T5-6), audio hash (T7), scenarios incl. (e) and acceptance rows 1-6 (T8); row 7 deferred to P4 by design.
- Open assumption flagged in T1: whether Excalidraw preserves an unknown top-level JSON key; the task stops and asks Aaron rather than adding a sidecar.
- Open assumption flagged in T6: how page decisions travel from the `db` collection to `apply`; mirror `offering_links` before deciding.
