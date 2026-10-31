# Recursive `part_N` course discovery: design

**Status:** proposed for review. No code, fixture test, relocation or index rebuild has been done.
**Scope:** `core/env/`, `core/indexer/`, `pipelines/transcribe_notes/`, `tools/corpus_health/`, and a new one-shot tool, for courses under `academic_notes/<course>/part_N` and `academic_resources/<course>/part_N`.

## Recommendation

Ship discovery and a local, no-API index relocation together, and do not run `rebuild` as part of this release. Fixing discovery alone is unsafe: the frontmatter edits make 221 of the 239 cards look stale, which would trigger about 3,900 API calls.

## Requirements

1. Match notes and resources by their full path below the course, including `part_N`.
2. Exclude textbooks from notes-PDF transcription at every depth, and find them for their own indexing pass.
3. Preserve marked-subset behavior and keep source-only offerings out of the wrong pipeline.
4. Find nested Excalidraw and video notes without rediscovering processed outputs.
5. Derive the content category; never treat `part_N` as the category.
6. Preserve stable file identity and distinguish moved files from genuinely new Markdown.
7. Specify fixture tests and a read-only live audit before any rebuild.
8. State the refresh cost and how to avoid an accidental paid bulk rebuild.

## Evidence

**How far to trust this.** Everything in this section comes from read-only probes of the live tree on 2026-10-31. The proposed rules ran only as a scratch prototype with card paths migrated in memory, so its counts are predictions for the implementation to confirm. The course folder is `microecon`, not `microeconomics`. The index was last written 2026-10-24, so it predates the moves and proves nothing about them.

| Finding | Evidence | Consequence |
|---|---|---|
| Frontmatter edits changed card hashes | All 221 differ from their baseline blob only in `source_pdf`, `source_excalidraw`, `source_image` or `duplicate_of_path`; the other 18 have matching hashes | `_is_stale` would regenerate 205 cards (the 16 clones are skipped) and re-embed 3,505 chunks |
| Regenerating drops labels | `generate_index_card` is called with no `offering_label` | 71 cards lose it; the cheap-patch path can also erase it (TODO-0040) |
| The `part_1` name passes the mirror gate | `academic_notes/<course>/part_1` matches `academic_resources/<course>/part_1` | Recursing behind that gate would sweep 11 textbook PDFs and 35 source-only PDFs (`class_2023`, `class_2025`) |
| Clone IDs include the source path | `compute_id_from_parts([duplicate_of_file_id, rel_pdf_path])` | Rebuild would orphan the 16 clone cards after the move |
| Textbook metadata is stale | All 10 `_metadata.json` `rag_md_path` values lack `part_1` | Rebuild would write the old path back; rendering and chapter ownership would then be misclassified |
| `folder_category` is wrong | All 525 preview rows report `part_1` | It is used only in the prompt, but it is also the invalid-`doc_type` fallback (live cards already have `problem_sets`, `exam_kit`) |
| `rebuild` is blocked today | Preview shows 137 + 121 paid Markdown cards against a cap of 25 | A safe accident, but the cap ignores producer regeneration |

The review also confirmed the three reported defects: `route_notes_transcribe.discover_pdf_sources` misses nested sources, `index_search` finds no nested books or scenes, and `_notes_pdf_paths` includes the 11 textbook PDFs.

## Repositories and write destinations

| Path | Repository | Role in this work |
|---|---|---|
| `ai-sandbox/academic-rag-model/` | Outer, public | Code, tests and docs, on a task branch |
| `ai-sandbox/academic-hub/.index/` | Outer, public | Relocation writes here, in the main checkout, under the corpus lock |
| `ai-sandbox/academic-hub/academic_notes/` | Nested, private | Read only for this work; the owner commits the moves there separately |
| `ai-sandbox/academic-hub/academic_resources/` | Outer, PDFs ignored | Read only |

## Discovery rules

Add one shared helper in `core/env/academic_hub_paths.py`. It parses `academic_{notes,resources}/<course>/[part_N/]<category>/<inner>/<file>`, where the part must match `^part_\d+$`.

1. **Category:** the first segment after any part. A file directly under the course or `part_N` has no category and is reported, never processed.
2. **Textbooks:** a case-insensitive textbook folder name at any depth excludes the file from notes-PDF discovery, on both the notes and resources sides. The book pass then walks the whole course tree for `<textbook>/**/processed_outputs/<book>/`, with no mirror gate.
3. **Notes-PDF eligibility:** skip hidden folders, `processed_outputs` and textbooks. A resources PDF qualifies if it sits under a `.notes_subset.json` root, or if the notes folder for the same `(part, category)` exists.
4. **Source-only material:** `class_2023`, `class_2025`, `part_2` and `part_3` stay out, with counts reported. The empty legacy `econometrics/problem_sets` folder has no resources counterpart, so it does nothing.
5. **Recursion:** part-layout courses recurse below the category. Legacy courses keep current behavior (route one level, rebuild recursive), which avoids silently adding 25 math-camp PDFs to the paid queue.
6. **Excalidraw:** walk recursively for `*.excalidraw.md`, pruning hidden folders, `processed_outputs` and textbooks, and require a category. `rag.md` and `questions.md` stay sibling outputs.
7. **Video notes:** require category `lecture_notes` and a `.meta.json` next to the `.md`. A sidecar-less `.md` belongs to the Markdown classifier, and the warning for it goes away.
8. **`folder_category`:** PDFs keep their immediate parent; Markdown and Excalidraw use the content category. No function may return `part_N`.
9. **`markdown_sources` and reserved paths:**
   - `_book_parent` locates `<textbook>/**/processed_outputs/<book>/chapters` and supports `Bonus/`.
   - `_auxiliary_parent` compares `(part, category)`, so a hint cannot link across offerings.
   - Book renderings come from `textbook_rag_md_path(book_dir)`, not the metadata value.

### Functions affected

| Function | Change |
|---|---|
| `route_notes_transcribe._discover_migrated_pdf_sources` | Use the `(part, category)` gate and part-layout recursion |
| `route_notes_transcribe._walk_content_dirs` | Also prune textbook folders |
| `index_search._notes_pdf_paths` | Same gate; prune textbooks and resources-side `processed_outputs`; include marked roots; skip uncategorized files |
| `index_search._excalidraw_note_paths` | Rule 6 |
| `index_search._textbook_book_dirs` | Rule 2, using the shared textbook-name check |
| `index_search._video_lecture_note_paths` | Rule 7 |
| `index_search._markdown_reserved_paths` | Reuse the walkers above; rule 9 for books |
| `markdown_sources._book_parent`, `_auxiliary_parent` | Rule 9 |
| `markdown_sources.classify_markdown` | Derive `folder_category` from the helper |
| `tools/corpus_health/discovery._eligible_resource_note_pdf` | Same gate as route |

## Identity and moved versus new

| Card type | Identity | After the move |
|---|---|---|
| PDF, scene | Source bytes | Stable, apart from the scene drift below |
| Textbook | PDF bytes | All 10 fallback PDFs hash to `source_pdf_file_id` |
| Video | Member video IDs | Stable |
| Question sidecar | Parent note ID | Stable unless the parent drifted |
| Clone | Includes old path | **Keep the old ID**; rebuild marks it seen by matching the card's path |

Add a one-shot `tools/relocate_index_paths.py --root <hub> --course <c> --baseline ca3b286`. It is a dry run by default, and `--apply --writer-coordinated` takes the corpus lock. It classifies each card as follows:

- **`path_only`:** the new file's hash equals the card's hash.
- **`moved_frontmatter`:** all of these must hold:
  - The baseline blob (LF or CRLF form) hashes to the card's hash.
  - The body matches after normalizing line endings.
  - Only the four allowed keys differ.
  - Each new value equals the old value with `part_1` inserted.
- **`edited` or `ambiguous`:** fails closed, nothing is written for that row, and it is reported.

Pinning `ca3b286` means the proof still works after `academic_notes` commits the move. On apply the tool:

- Patches `path`, `source_pdf_path`, `source_asset_path` and `rag_md_path`.
- Updates `content_hash` on the card and its matching chunks, keeping embeddings, summaries and labels.
- Remaps the path keys in `materials/<course>.decisions.json`.
- Keeps a backup of the files it changes outside the repo, and is safe to rerun because already-relocated cards are recognized.

Uncarded Markdown is reported as `moved_uncarded` if the old path exists at baseline, otherwise `new_since_baseline`. Equal bytes alone never merge two files that both exist.

## Minimum safe release

Work in a `claude/part-path-discovery` worktree from `main`. Pass `--root` explicitly, because the default resolves to the worktree's own hub.

1. Add the path helper and use it in the functions listed above.
2. Fix the clone seen-ID, the textbook rendering path, and `reconcile_and_write` so `None` no longer erases `offering_label`.
3. Add `rebuild --plan --json`, which creates no client. Add `--max-paid` (default 25) covering producer and Markdown work, enforced before any write.
4. Add the relocation tool. Regenerate the catalog after relocation with the existing `core/course_materials` step. This should be local (a grep found no client use in `classify.py`), but confirm that first.
5. Update the indexer and transcription READMEs.

The owner then commits the `academic_notes` moves separately in that repo, and relocation runs in the main checkout. The release needs no rebuild, server or new store. Relocation needs no new human review surface, since each row is either proven or fails closed.

| Capability | After release |
|---|---|
| Discovery | Shared layout rules; legacy courses unchanged |
| Scope | `--course`, exact `--file`, `--max-paid` |
| Side effects and cost | Relocation writes only `.index/`, with no API calls; rebuild is planned and capped |
| Outputs | Per-target JSON with reason, identity and action |
| Idempotency | Relocation can be rerun; a second plan shows no moved rows |
| Verification | Fixtures, then a live dry run, then a post-apply audit |

## Tests

Add these to `tests/core/indexer/test_index_search.py`, `test_markdown_sources.py` and `test_route_notes_transcribe.py`, plus a new relocation test file and the corpus-health callers:

- **Discovery matrix:** nested PDFs with and without mirrors, `part_2` without a mirror, a marker at part and offering level, a marker inside `Textbooks`, stray files, an empty legacy folder, and unchanged legacy and math-camp layouts.
- **Textbooks:** `part_1/textbooks`, `Bonus/`, the alias, Title-Case, and stale metadata.
- **Outputs:** Excalidraw and video notes nested, with `processed_outputs` never rediscovered, including `*.excalidraw.md` raw transcripts.
- **Categories:** a parametrized check that `part_N` never appears as `folder_category`, plus the `doc_type` fallback.
- **Relocation:** CRLF and LF baselines; allowed frontmatter changes, wrong value, extra key, and body edit; clone ID kept and chunk hash patched; label kept, decisions remapped, and interrupted rerun.
- **Cost guards:** a fake client asserts zero calls for `--plan`, for relocation, and when the cap is exceeded.

## Read-only live audit before any rebuild

1. Run route `--dry-run --course`, `rebuild --plan`, `index-md` and relocation dry-run from the worktree against the absolute live root.
2. Hand-check at least 10 varied rows against the files: nested PDF, marked subset, source-only, textbook, chapter, hint, clone, sidecar, drifted scene, stray.
3. Record any false positives and correct the rules before trusting totals.
4. Confirm `git status` shows no new writes in `.index/` or `academic_notes`.

## Cost

Tokens are estimated at 4 characters each. The repo has no price table, so the dollar figures assume $0.25/M for flash-lite input and $0.15/M for embeddings, not checked against current pricing.

| Action | Calls | Approx. cost | Other effect |
|---|---|---|---|
| Discovery fix plus plain rebuild and chunk | 3,915 | $0.35 | Rewrites summaries, drops 71 labels, orphans 16 clones |
| Relocation | 0 | $0 | None |
| Backlog cards after relocation (127 chapters, 81 notes) | 416 | $0.55 | New cards |
| Chunking that backlog | Not counted | $0.85 | About 5.7M tokens, overlapping existing book chunks |

The full backlog comes to about $1.40, which needs the owner's go-ahead under the over-$1 rule. Six cards marked `needs_indexing` and six drifted scenes also remain as paid work, about 24 calls plus their sidecars and chunks.

To avoid an accidental bulk run: do not use `--force`, `--prune` or a raised cap; run `chunk` only after a `--dry-run`; and do not run `rebuild` before relocation.

## Decisions

**Needed before relocation:**

- **Dirty `.index` files:** the outer repo has large uncommitted changes to `courses.json`, the `econometrics` and `microecon` shards, and `materials/econometrics.json`. Their owner must confirm or commit them first, because they are the relocation's input.

**Owner decisions, with the recommended answer:**

1. **`part_2` and `part_3`:** keep them source-only. Opt in with a `.notes_subset.json` marker rather than an empty mirror folder, since Git does not keep empty folders.
2. **Math-camp's 25 nested PDFs:** leave them out and decide separately.
3. **Six drifted microecon scenes:** report them only for now. Their bytes match the baseline but not the card ID, so this predates the move. Refreshing them mints new IDs and leaves old orphaned cards searchable.
4. **Backlog:** index selected notes first and skip chapter chunking until the overlap with book chunks is resolved.
5. **`part_1/wald_hypothesis_testing_quiz_prep.v4.final.pdf`:** leave it uncategorized and reported. It is currently queued only by accident of the gate.

**Outside this change, but relevant:**

- **Tracked PDFs:** 92 PDFs under `academic_resources` are still tracked in the public repo: 63 math-camp, 15 econometrics, 12 microecon, 2 math_methods. Ignore rules do not untrack them, and committing the deletions does not remove them from history.

## Other one-level assumptions

| Location | Effect | When to fix |
|---|---|---|
| `tools/corpus_health/discovery.py:122` | False missing-output results for source-only PDFs | This release |
| `core/course_materials/signals.py:105` | Loses role votes, because the category reads as `part_1` | Before rerunning the catalog or concept graph |
| `core/course_materials/model.py:92` | Prefix match can widen to a whole part | Before rerunning the catalog or concept graph |
| `audio_generator/discovery.py:94,116` | Misses nested notes and textbooks | Before the next audio run |
| `agent/study_guide/cli.py:43-51`, `draft.py:47,238`, `revise/run.py:37` | Writes and reads legacy paths; moved `guide_plans` are not found | Before the next guide run |
| `agent/rag/generate_quiz_guide.py:26`, `report_builder.py:54`, `pipelines/generate_video_notes/note_indexing.py:29` | New output lands outside `part_N` | Before their next write |
| `guide_specs/econometrics/wald_lm_lr_tests_new_material.toml` | 6 old `exclude_guide` paths, which should raise `PlanError` | Before that guide is rerun |
| Stored text in `guide_plans`, `summaries`, `lecture_notes`, `tutoring`, `problem_sets` | About 5,500 old path references; editing them changes hashes | Treat as history unless a reader breaks |
| Card `rag_md_path` on 7 of 10 books | Whole-book file is absent because books are chapters-only; Hansen is also absent at baseline | Separate bug |

These look safe at the new depth: `to_resources_root`, `resolve_output_dir`, `find_subset_roots`, `find_containing_offering_label`, `discover_pending_notes`, `derive_course`, `_folder_category_from_path`, and `related.py`'s same-folder check.

## Acceptance evidence

The expected numbers come from the prototype, so any difference needs explaining rather than adjusting.

| Check | Econometrics | Microecon |
|---|---|---|
| Eligible PDFs | 69 | 119 |
| PDFs still to transcribe | 1 (`econometrics_midterm_q3.pdf`) | 0 |
| Textbook PDFs excluded | 4 | 7 |
| Source-only PDFs reported | 97 | 5 |
| Scenes found / with `rag.md` | 21 / 13 | 29 / 17 |
| Scenes queued (the rest lack exports) | 0 | 0 |
| Books found | 4 | 6 |

- **Other courses:** math-camp stays at 33 discovered PDFs with 5 video sidecars, and math_methods stays at 2.
- **Relocation dry run:** 239 cards split into 18 `path_only` and 221 `moved_frontmatter`, with 0 `edited`. All 16 clone IDs are unchanged.
- **After apply:**
  - Every card and chunk `file_id` and embedding is unchanged, and all 80 labels are present.
  - Every card path exists and its hash matches the file.
  - Only pre-existing unchunked files appear in `chunk --dry-run`.
  - `academic_notes` is unchanged by the tool.
- **After relocation, `rebuild --plan` should show:** 0 refreshes caused by the move; 208 Markdown rows (119 econometrics, 89 microecon); only the listed drift and `needs_indexing` items beyond those; and a refusal at the default cap.
- **Tests:** the affected files pass, then `python tools/run_tests_chunked.py`, because `core/` changed.

## Related work

- [Markdown-only indexing design](2026-10-20-markdown-only-indexing-design.md): owns the classifier and the 25-card cap this design extends.
- [Notes subset discovery design](../transcribe_notes/2026-10-03-notes-subset-discovery-design.md): owns the `.notes_subset.json` behavior this design preserves.
- [To-do tracker](../../../trackers/academic_hub_to_do.md): TODO-0006 (Markdown without a source PDF) and TODO-0040 (persist `offering_label`).
