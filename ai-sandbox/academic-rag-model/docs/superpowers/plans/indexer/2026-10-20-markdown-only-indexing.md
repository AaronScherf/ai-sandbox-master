# Markdown-only academic notes: implementation plan

**Status:** implementation and fixture verification complete on `codex/markdown-only-index-implementation`; full suite and live indexing pending.
**Spec:** [2026-10-20-markdown-only-indexing-design.md](../../specs/indexer/2026-10-20-markdown-only-indexing-design.md).
**Goal:** Index eligible Markdown-only files and substantive generated companions throughout `academic_notes/` as first-class shared-corpus cards with honest provenance and parent links, then make them usable by existing search and chunk consumers.

## Implementation tracking (2026-10-21)

| Milestone | Status | Evidence still required |
| --- | --- | --- |
| Discovery and varied live read-only classification | Implemented and fixture-tested | Live sample recorded in status doc; broader sample during bounded live run |
| Card provenance, identity, and reconciliation | Implemented and fixture-tested | Live card audit pending |
| Rebuild, exact target, and bounded apply | Implemented and fixture-tested | Writer coordination and live audit pending |
| Search, passage, and caller coverage | Indexer suite passed (493 tests); full suite pending | Live chunk/query observations pending |
| Bounded live indexing | Deferred | Coordinated writers and audited API run |

## Execution context and global constraints

- Start implementation in a new dedicated worktree and `codex/<task>` branch under `docs/WORKTREE_WORKFLOW.md`; this docs worktree is only for the proposal. Read root `AGENTS.md`, package `CLAUDE.md`, `core/indexer/README.md`, and hub `CLAUDE.md` before editing.
- `core/indexer/` is shared by all pipelines. Preserve existing PDF, textbook, video-note, Excalidraw, essay, and journal-article cards and their readers. No source-note writes, fake upstream paths, guessed derivative status, or duplicate cards for attached alternate renderings.
- `academic_notes/` is a separate nested Git repository and a read-only input. Code/docs and `academic-hub/.index/` belong to the outer repository. The exact worktree may lack the nested repo, so use the main checkout for read-only inventory and a test fixture for edits; point any controlled live run at the intended root explicitly.
- Before enabling any exact-target repair, provide an exact selector, per-target machine-readable results, coordination with every writer of `.index/`, atomic shard output, and a post-run audit. If one is missing, keep apply disabled. Shared corpus locking covers `rebuild` and `chunk`, but not every other writer; arrange a quiet window or additional writer coordination for a live batch.
- No paid large batch without a preview and explicit bounded scope/call cap. Use only configured personal API credentials; do not print them. Existing `chunk` runs separately and has its own embedding cost.
- A new card does not by itself prove passage retrieval works. Track fixture tests, live index generation, live chunk generation, and later observed consumer behavior separately. Do not fold the pending problem-corpus heading change into this branch.

## Requirement-to-evidence map

| Requirement | Implementation task | Acceptance evidence |
| --- | --- | --- |
| Recursive, all-course eligible Markdown discovery | 1 | Fixture classifier and varied live read-only audit, with false positives recorded |
| Separate substantive companions from attached renderings and unknown-origin notes | 1, 2, 4 | Parent/role/origin assertions; companion search/chunk tests; no duplicate rendering card |
| No duplicate producer cards or invented provenance | 1, 2 | Owner exclusions and null-upstream card assertions |
| Stable edits, moves, orphan state, and old-card compatibility | 2, 3 | Reconciliation/identity fixtures and legacy regression tests |
| Search and passage availability | 3, 4 | File search and `chunk`/passage tests, then bounded live checks |
| Exact-target, bounded, auditable application | 3, 5 | JSON per target, cost cap, lock/atomicity tests, post-run audit |
| Documentation and cross-pipeline safety | 4, 5 | README/CLI help review and full chunked test suite |

## Task 1 — Candidate inventory and pure classification

**Files:** `core/indexer/index_search.py` or a small `core/indexer/markdown_sources.py`; `tests/core/indexer/test_markdown_sources.py`.

1. Implement deterministic recursive scanning of `academic_notes/<course>/` with normalized hub-relative paths and exact course filtering. Return a structured classification for each `.md` path before any API/client creation. Reject symlink/path escape, empty file, hidden tree, and case-colliding paths.
2. Build ownership from producer discovery/metadata and existing cards. Keep PDF-paired outputs with their PDF producer even if no card exists yet. Distinguish an attached alternate rendering (`rag_md_path` or explicit producer pointer), a machine manifest/raw canvas, an already-indexed specialized companion (Excalidraw questions), a substantive generated companion (for example a textbook chapter or producer-declared solution), and an unknown-origin note. Do not blanket-exclude `.rag.md` or `processed_outputs/`. Resolve a unique parent using documented producer metadata/path rules; report `ambiguous_parent` without inventing a relationship. Index otherwise useful unlinked hints/solutions as unknown-origin Markdown.
3. Test nested folders, mirrored resource PDFs, existing special-producer cards, same-content alternate rendering, substantive chapter/question companions, unknown-origin notes, ambiguous/missing parents, and repeated scanning. Compare varied live read-only findings with source files: econometrics problem sets, microecon hints/solutions, raw Excalidraw, attached `.rag.md`, textbook chapter `.rag.md`, question sidecars, and manifests. Record each false positive and correct the rule before using counts.

**Gate:** fixture classifier passes; documented live sample has zero unexplained false positives. The earlier 387 unmatched paths remain only a diagnostic count, not an eligible total.

## Task 2 — Provenance-aware cards and stable reconciliation

**Files:** `core/indexer/index_card.py`, classifier module, `tests/core/indexer/test_index_card.py` and new targeted cases.

1. Add `source_kind="markdown_only"` for unknown-origin notes and `source_kind="generated_companion"` for producer-confirmed generated children. Add `companion_of_file_id`, `companion_role`, and `relationship_basis` only with a verified unique relationship; an unknown-origin note may have a verified companion link without being labeled generated. Set null `source_pdf_path` and `source_asset_path` on new Markdown cards/failure cards, retaining actual legacy specialized-producer paths. Audit null-sensitive readers, including cross-course moves, backfills, prompt/card generation, and downstream serialization. Keep old cards valid without migration.
2. Derive namespaced path IDs only for new Markdown notes and generated companions with no existing card at that path. Keep the existing Excalidraw question ID and backfill `source_kind="generated_companion"` plus relationship metadata through its producer, without making a duplicate. If later evidence reclassifies an unknown-origin note as generated, update its provenance in place. Use `content_hash` to refresh summary and embedding on edit under the same ID. Reconcile a unique unmatched old same-hash card with compatible ownership only when its old path is gone; move its course/path without regeneration. Ambiguous or simultaneous copies get separate IDs. Re-resolve parent ID after a parent move or re-identification. Include the moved ID in the rebuild seen set.
3. Ensure repeated unchanged runs make no paid calls; a failed generation card retries; an edit invalidates old summary/embedding and later chunks; a missing file can become orphaned and reappear. Confirm same-content copies do not overwrite one another, a missing parent leaves a present child retrievable with a reported dangling relationship, and legacy PDF identity is unchanged.

**Gate:** identity/provenance/parent-link fixtures pass; one test exercises null upstream paths through the full save/load/reconcile path. Record any caller that cannot tolerate null as a blocker before proceeding.

## Task 3 — Rebuild, exact-target apply, and orphan semantics

**Files:** `core/indexer/index_search.py`, card/shard I/O if atomicity is missing, `tests/core/indexer/test_index_search.py`.

1. Add Markdown-only and generated-companion discovery to ordinary `rebuild()` after producer ownership is known and before orphan handling. Add all present companion IDs to `seen_file_ids` even if a parent is missing; audit the existing Excalidraw question producer's parent-dependent walker for this case. Keep the course filter and legacy producer order safe; do not relabel a previously owned producer card as unknown-origin Markdown. Attached renderings remain parent card paths, not new IDs.
2. Add exact hub-relative Markdown selection and read-only JSON preview, with per-target classification, origin, separate-card flag, parent path/ID/role/basis, action/ID/hash/estimated calls. Add a bounded apply path with per-target JSON results. Preflight `rebuild` and exact apply before any writes or paid calls: default maximum 25 new/changed Markdown-only or generated-companion cards, overridable with `--max-markdown-paid N` after preview. A selected-file run cannot orphan or prune unrelated cards. Verify existing shard save is atomic; if not, make it atomic before apply. Hold the shared corpus lock.
3. For Markdown-only and generated-companion cards, exclude missing/orphaned paths from `search()` while retaining existing PDF-backed orphan behavior. Reappearance restores search. Test stale-card and `--prune` handling, failed target isolation, cap failure before writes/calls, path traversal rejection, and an exact-file run with unrelated cards present.

**Gate:** one-target dry run and apply are deterministic and auditable in fixtures, and no unrelated card changes. If other `.index/` writers cannot be coordinated for a live run, stop at fixture verification.

## Task 4 — Consumers, docs, and regression coverage

**Files:** `core/indexer/chunk_index.py` only if needed, `core/indexer/README.md`, CLI help, `tests/core/indexer/`, relevant caller tests in `tests/agent/` and `tests/pipelines/`.

1. Test that unknown-origin and generated-companion cards appear separately in ordinary file search and index-card consumers. Run `chunk` against each and test passage retrieval, content-change replacement, missing-file handling, and stale chunk exclusion. Test that an attached rendering has no second card or duplicate search hit. Keep existing `chunk --course` and `--file-id` controls.
2. Search for all `source_pdf_path` and `source_asset_path` readers and test or fix code that assumes non-null strings. Include at least one legacy PDF card and specialized producer card in regression fixtures. Confirm source `academic_notes/` files are not edited.
3. Document schema meaning, companion and attached-rendering rules, preview/apply syntax, cost, chunk step, and examples. Make explicit that `markdown_only` does not assert derivative authorship, and that a companion relationship alone does not prove generation.

**Gate:** targeted indexer and affected caller tests pass. Run `python tools/run_tests_chunked.py` from `academic-rag-model/` for the full suite; log package results, not just a final exit code.

## Task 5 — Bounded live verification and landing handoff

1. Read-only preview one varied course and inspect a small sample against the underlying Markdown. Record false positives/negatives and adjust classification before relying on total counts. Capture exact paths and expected action counts.
2. Coordinate a quiet period for all `.index/` writers. With the user's already-authorized local pipeline scope and package guidance on large paid batches, choose a small explicit course or exact-file batch containing an unknown-origin note, a substantive companion, and an attached rendering; set a call cap. Apply only that selection. Audit every result against its card path, provenance, parent relationship, ID, status, and content hash; sample generated summary accuracy against source Markdown. Run targeted chunking and a file/passage query, confirming the companion is separate and the attached rendering is not duplicated. Check `academic_notes/` Git status stayed unchanged. Report actual API call counts and failures.
3. Commit code/tests/docs on the task branch with explicit staged paths. Run `python -m tools.land_branch check --full` if required by the worktree workflow, record the exact commit SHA and main dirty-state snapshot, then request landing approval for that SHA. Do not merge or push from an unapproved handoff.

**Release evidence:** classify separately as implemented, fixture-tested, bounded-live-tested, and observed in downstream use. Econometrics problem collection remains a separate follow-up after this indexer release, the pending heading-detection fix, and an audited targeted index/chunk run.
