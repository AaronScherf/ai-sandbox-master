# Hub Path Resilience, Plan 1: Stable Hashes and Clone Identity (spec phases P0 and P1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A move or rename of a Markdown note, or of a duplicate clone, no longer makes its index card look stale or orphaned, so no paid regeneration is triggered by a pure move.

**Architecture:** The Markdown content hash ignores location-only frontmatter fields. Staleness checks accept both the new and legacy hash, so rollout needs no flag day. A local migration tool rewrites stored hashes with no API calls. Clone cards are found by `duplicate_of_file_id` instead of by path.

**Tech Stack:** Python 3.13, pytest. No network or model calls anywhere in this plan.

**Spec:** `docs/superpowers/specs/academic_hub/2026-11-03-hub-path-resilience-design.md` (sections 1, 2 and the P0/P1 rows of Phases). This is plan 1 of several: `hub_id` and the reconcile engine (P2-P3), the triggers (P4) and `ACADEMIC_HUB_ROOT` (P5) get their own plans, written after this one lands, because their interfaces depend on what P1 settles. Out of scope here: category vocabulary, `hub_id`, reconcile, `rag_md_path` repair, `audio_generator/state.py`'s separate `compute_content_hash`.

## Global Constraints

- Run Python from `ai-sandbox/academic-rag-model/` as modules (`python -m ...`); tests mirror the package tree under `tests/`.
- Worktrees have no `.venv`; use the main checkout's interpreter: `C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe`.
- Tests must never call a model: pass a client whose every method raises, or avoid clients entirely. A test that triggers an API call fails the plan.
- `core/indexer/` is shared; changes need tests for the callers too. Until the landing-speed work trusts its selector, any `core/` change runs the full suite at landing.
- Use branch `codex/hub-resilience-p1` in its own worktree per `docs/WORKTREE_WORKFLOW.md`. Stage explicit paths only; never `git add -A`. Do not land.
- Never read or modify real `academic_notes/`, `academic_resources/` or `.index/` data in tests; use `tmp_path` fixtures. The migration tool runs against the live hub only when the owner says so.
- No history rewriting. No new dependencies.
- Location frontmatter fields (verbatim from the part-path spec): `source_pdf`, `source_excalidraw`, `source_image`, `duplicate_of_path`.

## Review Focus

1. A CRLF or BOM-prefixed note: a move must still leave its hash unchanged (Task 2).
2. A note whose *body* changed as well as its location fields must still read as stale (Task 2, Task 3).
3. Two clones of the same canonical document in one course: the lookup must not pick one silently (Task 5).
4. Migration on a card whose file changed since the card was written: the card must stay stale, not be "healed" (Task 4).
5. Migration run twice, or interrupted: idempotent, and no card left half-written (Task 4).

---

### Task 1: Characterization tests and fixture hub (spec P0)

**Files:**
- Create: `tests/core/indexer/hub_fixture.py` (helper), `tests/core/indexer/test_path_resilience_characterization.py`

**Interfaces:**
- Produces: `make_hub(tmp_path) -> Path` creating `academic_notes/econ/{lecture_notes,problem_sets}` and `academic_resources/econ/` under `tmp_path`, returning the hub root. `write_note(hub: Path, rel: str, frontmatter: dict[str, str], body: str) -> Path` writing a Markdown file at `hub/rel` with `---\n<key: value lines>\n---\n\n<body>` and returning its path.

- [ ] **Step 1: Write `hub_fixture.py` with `make_hub` and `write_note` as specified above.**

- [ ] **Step 2: Write the characterization tests.** Each uses `write_note` plus `compute_content_hash` (current, to be changed) and `_is_stale` from `core.indexer.index_search`. Mark the two that fail today with `@pytest.mark.xfail(strict=True, reason="fixed by Task 2/5")` so they flip to failures-to-remove when fixed:

```python
@pytest.mark.xfail(strict=True, reason="fixed by Task 2")
def test_pure_move_keeps_content_hash(tmp_path):
    hub = make_hub(tmp_path)
    a = write_note(hub, "academic_notes/econ/lecture_notes/n.md",
                   {"source_pdf": "academic_resources/econ/lecture_notes/n.pdf"}, "body")
    b = write_note(hub, "academic_notes/econ/part_1/lecture_notes/n.md",
                   {"source_pdf": "academic_resources/econ/part_1/lecture_notes/n.pdf"}, "body")
    assert compute_content_hash(str(a)) == compute_content_hash(str(b))

def test_body_edit_changes_content_hash(tmp_path):  # passes today and must keep passing
    ...
    assert compute_content_hash(str(a)) != compute_content_hash(str(b))
```

- [ ] **Step 3: Run** `pytest tests/core/indexer/test_path_resilience_characterization.py -v`. Expected: one xfail, the body-edit test passes.

- [ ] **Step 4: Commit** `test(indexer): characterize path-move hash behavior` with the two new paths staged.

### Task 2: Location-insensitive content hash

**Files:**
- Modify: `core/indexer/index_card.py:86-100` (`compute_content_hash`); add constant and helpers beside it.
- Test: `tests/core/indexer/test_index_card.py`

**Interfaces:**
- Produces in `core/indexer/index_card.py`:
  - `LOCATION_FIELDS: tuple[str, ...] = ("source_pdf", "source_excalidraw", "source_image", "duplicate_of_path")`
  - `compute_legacy_content_hash(md_path: str) -> str`: the current behavior, truncated SHA-256 of the raw file bytes, first 16 hex characters.
  - `compute_content_hash(md_path: str) -> str`: same as legacy unless the file has a frontmatter block containing at least one `LOCATION_FIELDS` line; then the hash of the file bytes with those lines removed.
  - `content_hash_matches(md_path: str, stored: str | None) -> bool`: `True` iff `stored` equals the new or the legacy hash; `False` for `None`.

- [ ] **Step 1: Write failing tests** in `test_index_card.py` (use `tmp_path` and raw `write_bytes`):
  - `test_move_only_location_change_keeps_hash`: two files identical except the `source_pdf` value → equal `compute_content_hash`.
  - `test_body_edit_changes_hash`; `test_non_location_field_edit_changes_hash` (change `title`).
  - `test_no_location_fields_equals_legacy_hash`: `compute_content_hash(p) == compute_legacy_content_hash(p)` for a file with no location fields and for a file with no frontmatter.
  - `test_crlf_and_bom_note_keeps_hash_on_move`: bytes beginning `b"\xef\xbb\xbf---\r\n"` with `\r\n` line endings, two `source_pdf` values → equal hashes. Location lines are matched with the trailing `\r` ignored; the remaining bytes (including the BOM and `\r\n`) are hashed unchanged.
  - `test_location_key_in_body_is_not_removed`: a line `source_pdf: x` after the closing `---` still counts toward the hash (editing it changes the hash).
  - `test_content_hash_matches_accepts_legacy_and_new`: a moved file whose stored value is the *legacy* hash of its current bytes → `True`; stored `None` → `False`; a stale value → `False`.

- [ ] **Step 2: Run** `pytest tests/core/indexer/test_index_card.py -k "hash" -v`. Expected: the new tests FAIL.

- [ ] **Step 3: Implement the three functions and the constant.** Algorithm (not determined by the signatures): read bytes; split on `b"\n"`; the first line stripped of a leading BOM and trailing `\r` must equal `b"---"`, else no frontmatter; the block ends at the next line whose stripped form is `b"---"`; within the block drop lines whose text before the first `:` (stripped) is in `LOCATION_FIELDS`; rejoin with `b"\n"`. If nothing was dropped, return the legacy hash. Before finalizing, grep `render_frontmatter` callers and the `frontmatter` writers in `pipelines/` for any other path-valued key; if one exists, add it to `LOCATION_FIELDS` with a test, and note it in the commit message.

- [ ] **Step 4: Remove the `xfail` marker on `test_pure_move_keeps_content_hash`** from Task 1 and run `pytest tests/core/indexer/test_index_card.py tests/core/indexer/test_path_resilience_characterization.py -v`. Expected: PASS.

- [ ] **Step 5: Update `core/indexer/README.md`** (the `index_card.py` bullet) to say the content hash ignores location frontmatter fields and legacy hashes are still accepted.

- [ ] **Step 6: Commit** `feat(indexer): content hash ignores location-only frontmatter` staging the four changed paths.

### Task 3: Staleness checks accept either hash

**Files:**
- Modify: `core/indexer/index_search.py:408` (`_is_stale`); `agent/problem_corpus/stage.py:51` and `:120`.
- Test: `tests/core/indexer/test_index_search.py`, `tests/agent/problem_corpus/` (the existing stage tests; add cases there).

**Interfaces:**
- Consumes: `content_hash_matches(md_path, stored)` and `compute_content_hash` from Task 2.
- Produces: `_is_stale(existing: dict, source_mtime: float, content_hash: str) -> bool` keeps its signature. Where the caller has the file path, it passes the new-style hash; `_is_stale` treats the card as fresh when `existing["content_hash"]` equals the passed hash **or** the legacy hash of the same file. Because `_is_stale` receives only a hash, add an optional keyword `legacy_content_hash: str | None = None` and have its callers compute it with `compute_legacy_content_hash`.

- [ ] **Step 1: Write failing tests.**
  - `test_is_stale_fresh_when_stored_hash_is_new_hash`: card stores the new hash; the file was moved (location field changed) → `False`.
  - `test_is_stale_fresh_when_stored_hash_is_legacy_hash_of_current_file`: card stores `compute_legacy_content_hash` of the file as it is now → `False`.
  - `test_is_stale_true_when_stored_legacy_hash_is_of_old_bytes`: card stores the legacy hash of the file *before* its location field changed, and the file now differs only in that field → `True`. This is the already-relocated-by-git-baseline case (`tools/relocate_index_paths.py`), documented here so the limit of the compatibility shim is explicit; Task 4 does not heal it either.
  - `test_is_stale_true_when_body_changed`.
  - In the problem_corpus stage tests: a moved note with an unchanged body is not reported as changed; an edited body is.

- [ ] **Step 2: Run** the new tests; expected FAIL.

- [ ] **Step 3: Implement.** In `_is_stale`, if the stored hash equals `content_hash` or equals `legacy_content_hash`, return `False`; otherwise keep the existing logic. Update the `_is_stale` callers in `index_search.py` to compute and pass `legacy_content_hash`. In `stage.py` replace the two direct comparisons with `content_hash_matches(path, stored)`.

- [ ] **Step 4: Run** `pytest tests/core/indexer tests/agent/problem_corpus -q`. Expected: PASS.

- [ ] **Step 5: Commit** `feat(indexer): staleness accepts new and legacy content hashes` with explicit paths.

### Task 4: Local rehash migration tool

**Files:**
- Create: `tools/rehash_content_hashes.py`, `tests/tools/test_rehash_content_hashes.py`

**Interfaces:**
- Consumes: `load_shard`, `list_courses`, `update_card_content_hash`, `compute_content_hash`, `compute_legacy_content_hash`, `content_hash_matches` from `core.indexer.index_card`.
- Produces:
  - `plan(hub_root: str) -> dict` returning `{"rewrite": [{"file_id": str, "path": str, "old": str, "new": str}], "unchanged": int, "stale": [{"file_id": str, "path": str}], "missing": [str]}`. A card is in `rewrite` when its `path` ends `.md`, the file exists, `stored == compute_legacy_content_hash(file)` and `stored != compute_content_hash(file)`. It is in `stale` when the stored hash matches neither. Cards without a `content_hash` are ignored.
  - `apply(hub_root: str) -> dict` performing the `rewrite` list via `update_card_content_hash` and returning the same summary plus `"applied": int`.
  - CLI: `python -m tools.rehash_content_hashes --hub-root PATH [--apply]`; default is plan-only (prints the summary).

- [ ] **Step 1: Write failing tests** (hub built with `make_hub` and cards written with `save_shard`):
  - `test_plan_lists_cards_whose_hash_changes_under_new_scheme`.
  - `test_stale_card_stays_stale`: file body changed since the card → listed under `stale`, never in `rewrite`, and `apply` leaves its stored hash untouched (Review Focus 4).
  - `test_apply_is_idempotent`: a second `apply` reports `applied == 0` (Review Focus 5).
  - `test_apply_makes_no_model_call`: `apply` runs with no client at all (the module must not import a client).
  - `test_missing_file_is_reported_not_raised`.

- [ ] **Step 2: Run**; expected FAIL.

- [ ] **Step 3: Implement** `plan`, `apply` and `main`. `apply` must hold the same corpus lock the rebuild/chunk CLIs use (see `tests/core/indexer/test_rebuild_cli_lock.py` for the pattern and reuse its helper rather than writing a new lock). Each card is updated through `update_card_content_hash`, which is the existing atomic single-card write; do not write shards directly.

- [ ] **Step 4: Run** `pytest tests/tools/test_rehash_content_hashes.py -v`; expected PASS.

- [ ] **Step 5: Document the one-time run** in `core/indexer/README.md`: run plan first, review the `stale` list, then `--apply`; no API calls; safe to rerun. Do not run it against the live hub; report that the owner runs it.

- [ ] **Step 6: Commit** `feat(tools): local content-hash migration` with explicit paths.

### Task 5: Find clone cards by duplicate source, not path

**Files:**
- Modify: `core/indexer/index_card.py` (add `find_clone_card`); `core/indexer/index_search.py:830-838` (the duplicate-note clone branch).
- Test: `tests/core/indexer/test_index_card.py`, `tests/core/indexer/test_index_search.py`

**Interfaces:**
- Produces: `find_clone_card(cards: list[dict], duplicate_of_file_id: str, rel_md_path: str) -> dict | None`. Returns the card whose `path == rel_md_path` if one exists (path separators normalized to `/`); otherwise the **single** card with `duplicate_of_file_id` equal to the argument; otherwise `None` (zero or several candidates). It never chooses among several.

- [ ] **Step 1: Write failing tests.**
  - `test_find_clone_card_prefers_exact_path`.
  - `test_find_clone_card_after_move_uses_duplicate_id`: the card's stored `path` is the old path, the note moved → still found by `duplicate_of_file_id`.
  - `test_find_clone_card_ambiguous_returns_none`: two cards share the canonical ID and neither path matches (Review Focus 3).
  - `test_find_clone_card_normalizes_windows_separators`.
  - In `test_index_search.py`: a `--prune` pass over a moved duplicate-note clone adds the existing card's `file_id` to `seen_file_ids`, so the card is not evicted, and `compute_id_from_parts` is not used to invent a replacement id when a card was found.

- [ ] **Step 2: Run**; expected FAIL.

- [ ] **Step 3: Implement `find_clone_card`** and replace the path-only `next(...)` lookup in `index_search.py` with it. When it returns `None`, keep the existing fallback derivation unchanged and increment a new `stats["clone_card_unresolved"]` counter so an ambiguous case is visible in the rebuild summary instead of silently regenerating a card (the spec's "never guess silently").

- [ ] **Step 4: Run** `pytest tests/core/indexer -q`, then the full suite with `python tools/run_tests_chunked.py`. Expected: PASS.

- [ ] **Step 5: Commit** `feat(indexer): locate duplicate clone cards by source id` with explicit paths.

---

## Self-Review

- **Spec coverage:** P0 (Task 1), canonical hash and no-API migration (Tasks 2-4), stable clone IDs (Task 5). Spec items deliberately deferred to later plans: `hub_id`, category vocabulary, reconcile, triggers, `rag_md_path` hints, `ACADEMIC_HUB_ROOT`. Stated in the header.
- **Type consistency:** `compute_content_hash`, `compute_legacy_content_hash`, `content_hash_matches` and `LOCATION_FIELDS` are defined in Task 2 and used with those names in Tasks 3 and 4. `find_clone_card` is defined and used only in Task 5.
- **Rollout safety:** the migration (Task 4) is not required for correctness because Task 3 accepts either hash; it only removes the one-time mismatch. Pre-migration behavior for a moved file with a legacy-stored hash is documented by a test rather than hidden.
- **Proportion:** the plan is shorter than the spec's design sections plus code it describes; test bodies appear only where an assertion is pinned.
