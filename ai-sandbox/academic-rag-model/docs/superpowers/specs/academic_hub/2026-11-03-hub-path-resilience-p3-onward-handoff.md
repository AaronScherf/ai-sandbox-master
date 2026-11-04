# Hub path resilience: handoff for P3 and beyond

Written 2026-11-03. A brief for the session that plans and builds P3-P5. It is not an approved plan: start with the writing-plans skill (brainstorm only where this brief says a decision is open), and confirm scope with Aaron.

Spec (binding): `2026-11-03-hub-path-resilience-design.md` in this folder. Read sections 1, 4, 5, 6, "Phases", "Acceptance" and "Decisions" first.

## What is already done (on `main`)

| Phase | Result |
| --- | --- |
| P0 | Design approved; scenario matrix in the spec |
| P1 (PR #19) | Canonical content hash ignores `LOCATION_FIELDS` (`core/indexer/index_card.py`); legacy hashes still accepted via `content_hash_matches`; `tools/rehash_content_hashes.py` ran on the live hub (272 rewritten, committed in PR #22) |
| P2 (PR #20, #21) | `core/env/hub_vocabulary.py` (`parse_hub_path`, `load_vocabulary`, aliases), seed `ai-sandbox/academic-hub/hub_config.json`, learner `core/env/hub_vocab_learn.py`, CLI `python -m tools.hub_vocabulary propose|impact|confirm` (documented in `core/indexer/README.md`). Callers moved: `course_part_category`, `Catalog.lookup`, course-material signals, audio discovery, corpus_health, notes-PDF eligibility |
| Owner answers | PR #23 records 49 owner answers in `hub_config.json` (review page: https://claude.ai/artifact/5MZ3npTTxQtdjwN8HrEyHH). If it is not merged yet, merge it before P3 fixtures use the live vocabulary |

Not done and still true: cards and frontmatter carry **no stable ID** (no `hub_id`), nothing detects a move or rename, and nothing repairs links.

## P3: reconcile engine and review integration

Goal (spec section 4): `reconcile(hub_root)` snapshots the tree, compares it with the cards, classifies each difference, and either repairs it (single exact match), raises a review item (ambiguous or weak), or reports an orphan. Never relinks on similarity alone, never deletes.

Already decided by Aaron (do not re-ask):
- Automatic repair of a single exact match: **yes**, logged and reversible.
- `hub_id` in authored-note frontmatter: **yes**; the edit lands in `academic_notes/` (a separate repo); Aaron commits it there. Plan a command that writes ids, and say so before touching that repo.
- One shared review page, separate ledgers, **built together with the engine in P3**: a shared item envelope (type, subject ids, ranked candidates, status, timestamps); relink items go into the corpus-health decision ledger; each item applies through its own module's resolve/reject (`core/indexer/offering_links.py` pattern). The review surface must be an interactive Artifact page with decisions in its `db` collection (see `academic-rag-model/CLAUDE.md`, Scope).
- No preflight in landing checks.

Work items:
1. **Identity tiers** (spec section 1): byte hash for binaries, `hub_id` for authored Markdown/Excalidraw, derived outputs keyed by parent id plus role. Decide how to store `hub_id` for formats without frontmatter (spec leaves it to the builder).
2. **Stable clone ids**: clone cards still derive their id from the path; `find_clone_card` falls back to path or a single `duplicate_of_file_id` match. Replace with a stored id (P1 did not finish this).
3. **Matching**: exact hash or `hub_id`, then git rename detection (`git diff -M`, `git log --follow` over the hub repos), then stem plus course plus body similarity as a ranked suggestion only.
4. **Scenario (e), whole course folder moved** (deferred from P2 with no xfail): one review item, or auto-repair of every file by exact match. Put the test in the new scenario suite.
5. **Audio state hash**: `audio_generator/state.py::compute_content_hash` hashes raw bytes, so a moved note whose `source_*` lines are rewritten regenerates its audio (local and slow, not paid). Read-only audit on 2026-11-03: 314 of 402 live notes have location lines, so this will trigger. Switch it to the canonical hash with a legacy fallback, as P1 did for cards.
6. **Acceptance matrix** from the spec, on a fixture hub, with the model client mocked to fail on any call.

Known limits from the P2 review to keep in mind: unconfirmed folders above a known category count as group layers (by spec; `impact` shows the effect); `route_notes_transcribe.py` ~375 only handles `part_N` roots (report-only); `relocate_index_paths.py` still compares raw bytes (one-off tool, already used).

## P4: daily scan and pipeline preflight

- Add reconcile to `tools/corpus_health scan` (findings only, never mutates corpus files).
- Preflight: each pipeline compares a cheap tree fingerprint (names, sizes, mtimes, stored under `.index/`) with the last reconcile; unchanged continues, changed runs reconcile, and an unresolved item touching what the pipeline needs stops it with a pointer to the review queue. Fingerprint fields are the builder's call.
- **Fold the vocabulary learner into the daily scan** (Aaron's rollout decision): raise a review item only for each *new* folder name, via the shared review page, answered once and stored through `tools.hub_vocabulary confirm` semantics. The one-off `propose` run is already done.

## P5: `ACADEMIC_HUB_ROOT` and temp-scaffold fixtures

Single setting (default `../academic-hub`) used by `core/env/academic_hub_paths.py` and the roughly 50 non-test modules that hard-code `academic-hub` (inventory with grep first and separate real path use from docs); tests that touch hub content use a temporary scaffold instead of the vault. Overlaps with the hygiene/guard work (`2026-11-03-repo-hygiene-and-binary-guard-handoff.md` on branch `claude/hygiene-handoff`) only through `tools/land_branch.py`; also read `docs/MONOREPO_SPLIT_EVALUATION.md` (Update 3) on branch `claude/monorepo-split-handoff`, which lists this as step 2 of the decided direction.

## Constraints

- One phase per branch and PR; core changes (`core/env`, `core/indexer`) run the full suite: `python -m tools.run_tests_chunked` (about 14 minutes; close memory-heavy programs first, it was killed once for low memory).
- Zero API calls in every scenario test; warn Aaron before any run estimated over $1.
- Worktree procedure, explicit-path staging, no secrets, nothing copyrighted; ask before touching git history.
- Windows: CRLF files (use the Edit tool or Python with `newline=""`), heredoc backslashes, worktrees lack `academic_notes/` (separate nested repo) and `.env`.
- Deferred minors worth a look while in these files: alias matching is exact casefold only; `group_patterns`/`is_group_name` have no non-test callers; doc-type maps (`KNOWN_DOC_TYPES`, `LECTURE_NOTE_DOC_TYPES`, `_PROBLEM_TIER_FOLDER_CATEGORIES`, `_CATEGORY_FOLDERS`) are still hard-coded by design.
