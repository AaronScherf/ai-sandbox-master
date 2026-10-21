# Markdown-only indexing implementation status — 2026-10-21

**Branch:** `codex/markdown-only-index-implementation`.
**Design:** `docs/superpowers/specs/indexer/2026-10-20-markdown-only-indexing-design.md`.
**Plan:** `docs/superpowers/plans/indexer/2026-10-20-markdown-only-indexing.md`.

## Requirement and evidence

| Requirement | Implemented | Fixture evidence | Live evidence |
| --- | --- | --- | --- |
| Recursive Markdown discovery and producer ownership | `core/indexer/markdown_sources.py` plus reserved producer paths | `test_markdown_sources.py` | Read-only sample below; no live writes |
| Honest origin and linked companions | Card schema carries `source_kind` and optional parent/role/basis | Unknown, generated, reclassification, question-sidecar tests | Read-only card/path sample only |
| Stable identity, edits, moves, and missing sources | Path-derived IDs, unique same-hash move reconciliation, orphan/search handling | Edit/move/copy/orphan/retry tests | No live indexing run |
| Exact, bounded, auditable apply | `index-md` preview/apply, exact path, paid-card cap, per-target JSON audit, shared lock, atomic shard and rollup files | Selector, CLI preview, cap, and apply fixtures | Writer coordination and live audit pending |
| Search and passage consumers | Missing Markdown cards hidden; stale companion chunks ignored | File/passage tests | No live chunk/query run |

## Read-only corpus sample

The main checkout's `academic_notes/` nested repository was read only. An
econometrics preview found 235 Markdown paths: 86 producer-owned, 84 generated
companion candidates, 31 non-content auxiliaries, 31 unknown-origin notes, and
3 unlinked auxiliaries **before** a correction for processed Excalidraw plain
transcripts. These counts are diagnostic, not a reliable eligible total or a
paid-run estimate. A full econometrics run would exceed the default 25-card
cap; no run was started.

The sample was compared directly with source Markdown on disk:

- `econometrics/problem_sets/processed_outputs/problem_set_1.md` and
  `problem_set_2.md` are content-bearing problem statements with no verified
  upstream asset in the index; they are classified as unknown-origin Markdown.
- `problem_set_1_gemini_solutions.md` and `problem_set_1_solutions.md` contain
  solution text. Their parent is unlinked in the first preview because the
  Markdown problem-set card does not yet exist; a rebuild indexes ordinary
  notes first and reclassifies unlinked auxiliaries afterward.
- A Cameron Microeconometrics chapter `.rag.md` has distinct chapter text
  under a whole-book output folder and a unique whole-book card; it is a
  generated companion. The `00_front_matter.rag.md` is also a child candidate,
  though its standalone retrieval value remains unverified.
- Raw `lecture_notes/*.excalidraw.md` files are canvas sources. The initial
  classifier also marked `lecture_notes/processed_outputs/*.excalidraw.md`
  as non-content; direct inspection showed those files contain a real plain
  transcription. **Corrected rule:** attach a processed plain transcript to
  its corresponding `.excalidraw.rag.md` card when present. When the producer
  cannot be resolved, report ambiguous ownership rather than inventing
  provenance. Excalidraw question sidecars remain separate producer cards.

No false positive remained in this small inspected sample after that rule
change. It is not evidence that all courses or every generated auxiliary have
been correctly classified. The nested notes repository was not modified.

## Remaining gates

The indexer suite passed (493 tests), then the eight-group full chunked suite
passed in 700.1 seconds. Two final focused fixtures passed after the last
chapter-classification guard. The landing check will rerun the full suite on
the committed branch. A bounded
live indexing run requires coordination with every
writer to the shared `.index/` directory, a fresh preview and call cap, and a
per-target post-run card/content audit. Passage indexing and downstream use
must be checked separately. The pending problem-corpus heading-detection
change is outside this branch.
