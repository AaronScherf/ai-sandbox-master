# Question Resolver: Status Summary

Start here for "what happened and where do we stand" on the question
resolver: a manual command that answers the `[Question]` tags the Excalidraw
transcription pipeline leaves in handwritten lecture notes, stores the
answers beside the note, and marks each tag in the `.rag.md` as resolved.
Design reference:
`docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md`;
implementation plan:
`docs/superpowers/plans/agent/rag/2026-10-03-question-resolver.md`. Builds on
the slide-aware transcription work
(`docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md`,
2026-10-03 section) and the `/hint` grounding pattern in `rag_agent.py`.

Merged to `main` (`e55402c`) and run for real on the four microecon notes
that have tags; the resulting sidecars, markers and index cards are
committed (`academic_notes` repo `165084f`, monorepo index `59846d7`).

## What shipped

- **`python -m agent.rag.resolve_questions [--root R] [--course C]
  [--note TEXT] [--dry-run] [--redo] [--model M] [--max-questions N]`**
  (`agent/rag/resolve_questions.py`). For each unanswered tag: extract key
  terms from the question and its handwriting context, retrieve course
  passages (`retrieve_passages`, excluding the note's own files by
  hub-relative path), and answer. **Grounded** means a passage survived
  exclusion and (no key terms were extracted, or some passage mentions one);
  otherwise the answer is generated from general knowledge and labeled
  **ungrounded**. Default model `gemini-3.6-flash` on `PAID_GEMINI_KEY`.
- **Sidecar** `<name>.excalidraw.questions.md` next to the note: one
  `## q<n>-<hash> - <question>` section per question with a machine-readable
  metadata comment (grounded flag, model, timestamp, stale flag), the
  handwriting context, the answer, and a Sources list (or "none -- not
  sourced from your course materials"). Written atomically (temp file then
  rename).
- **Markers in the `.rag.md`.** Only the tag token changes:
  `[Question: answered -> <sidecar>#<id>]`, or `answered (ungrounded)`; the
  question text stays. `apply_markers()` (`core/indexer/questions.py`) is
  deterministic (no model call) and idempotent, and is re-run by
  `transcribe_excalidraw.write_outputs` whenever a note is regenerated,
  before indexing, so `--reexpand` cannot lose them.
- **Stable ids.** `q<ordinal>-<8 hex of the lowercased question text>`, taken
  from the *raw* transcript, which regeneration of the `.rag.md` never
  changes. When the raw tag count differs from the `.rag.md`'s, tags pair by
  text similarity (>= 0.8); unmatched sidecar entries are flagged `stale`.
- **Indexed.** `rebuild` indexes each sidecar as an `excalidraw_questions`
  card under a derived id (rewrites update one card); `chunk` splits it per
  question. Subset notes (`subset_of`) are skipped.
- Idempotent and failure-isolated: answered ids are skipped unless `--redo`;
  a question that errors or returns an empty answer writes nothing and is
  retried next run; `--dry-run` makes no API calls; exit code 1 on any failure.
- Shared helpers moved to `core/env/excalidraw_text.py` (tag regex, segment
  splitter), used by the transcriber, the subset linker and the resolver.

Design decisions the user made (sidecar plus marker rather than in-place
answers, since `--reexpand` rewrites the `.rag.md`; manual trigger only; always
answer but label the grounding) are in the spec.

## Real-corpus validation

`--dry-run` on microecon listed exactly 4 notes / 7 questions (09-07: 1,
09-10: 1, 09-17: 1, 09-22: 4). The real run resolved all 7 with no failures:
**4 grounded, 3 ungrounded** (09-17 "why can they still be used?"; 09-22
"what is furthest you can get from A while in B?" and "what if we don't
observe choices from all choice sets?"). Spot-checked: the grounded IIA answer
(09-07) correctly says IIA is necessary but not sufficient and cites
`1.Course_Intro.md` and `2.Utility_Maximization_1.md`; the ungrounded 09-17
answer says plainly that it has no sources. After `rebuild`, a query for the
IIA question ranks the 09-07 sidecar first (0.88, ahead of the notes at 0.74
and `1.Course_Intro` at 0.72). All 7 markers are in the `.rag.md` files; no
open tags remain.

## Corrections made against real evidence, not assumptions

1. **Plan correction: an empty retrieval must not count as grounded.**
   `/hint`'s check (`not key_terms or any(...)`) would call a retrieval with
   no passages and no extracted terms "grounded"; a guard now requires at
   least one surviving passage.
2. **Own-note exclusion compared filenames only.** Two same-named notes in
   different folders of one course would have excluded each other's passages
   (false "ungrounded"). Now compares hub-relative paths. (Found in review.)
3. **Ids embed the ordinal, so deleting/reordering an earlier question and
   re-transcribing shifted every later id**, which would have orphaned the
   answer and silently re-billed the question. `rekey_entries()` now moves an
   answer onto the question's new id by its text hash, with no model call,
   in both `apply_markers` and `resolve_note`. (Found in review.)
4. **First microecon `rebuild` in weeks surfaced old drift, not new bugs**:
   an edited scene had a new card (old one orphaned), and two cards were
   orphaned because their scene files had been renamed while the outputs kept
   the old names. Fixed by renaming the outputs and pruning; see the
   transcription and indexer status docs.
5. A strict `SyntaxWarning`-as-error run failed on another session's test
   file with an invalid `\h` escape (pre-existing, not touched); our own files
   are clean under the strict flag.

## Specific limitations, honestly assessed

- **Ungrounded answers are general-knowledge explanations, not checked against
  your course.** They are labeled everywhere, but a fluent wrong answer can
  still end up in the index. Treat the three ungrounded answers as leads to
  verify. A question whose subject is simply absent from the corpus (the
  Hausdorff-style one on 09-22) stays ungrounded until sources are added.
- **Passage-level retrieval does not include the new answers yet**: `chunk`
  has not been run for microecon, so only file-level `query` finds the
  sidecars. (File-level retrieval is what the check above used.)
- Answers are not refreshed when the corpus improves; use `--redo`.
- Editing a question's wording changes its hash, so it is treated as a new
  question and the old entry goes stale (never pruned automatically).
- The tag regex has no code-span or LaTeX awareness, so a literal
  `[Question]` written in handwriting would be read as a tag.
- No file locking between `write_outputs` and the resolver; `apply_markers`
  is idempotent, so the next run self-heals.
- Once a sidecar exists, `rebuild` makes a second classification/embedding
  call per note.

## What's next

- Run `python -m core.indexer.index_search chunk --course microecon` so
  passage-level search includes the resolved answers (costs embeddings).
- Re-run the resolver with `--redo` on the ungrounded questions after the
  relevant textbook material is converted/indexed.
- Deferred minors above (code-span awareness, locking, rebuild cost note).
- The resolver is Excalidraw-only; `[Question]`-style resolution for other
  note types is out of scope for now.

Full suite on `main` after the merge: 2148 passing.
