# Question Resolver: Design

**Status:** approved in conversation 2026-10-03; written spec pending review.
**Packages:** new `core/indexer/questions.py` (pure, no network), new `agent/rag/resolve_questions.py` (retrieval + generation + CLI); small hooks in `pipelines/transcribe_notes/transcribe_excalidraw.py` and `core/indexer/index_search.py`.

## Motivation

The slide-aware Excalidraw pipeline tags handwritten open questions (sidebar
questions, regions marked with `?`) as `[Question]` in both outputs
(`<name>.excalidraw.md` raw, `<name>.excalidraw.rag.md` expanded) so a later
step can resolve them. Today there are 7 such tags across 4 notes
(microecon 09-07, 09-10, 09-17, 09-22), and nothing answers them.

**Goal:** a manual command that finds each open question, answers it with an
explanation grounded in the course corpus where possible, stores the answer
where it survives regeneration of the notes, and leaves a visible, retrievable
trail in the `.rag.md` so an agent reading that note knows the question is no
longer open and where the answer is.

## Decisions (made in conversation)

1. **Storage: sidecar plus marker.** Answers live in a per-note sidecar file; the
   `.rag.md` gets a "resolved, see sidecar" marker on each tag. In-place answers
   were rejected because `--reexpand` and re-transcription rewrite the `.rag.md`.
   A sidecar alone was rejected because a reader of the `.rag.md` would see only a
   bare `[Question]` and could not know an answer exists.
2. **Trigger: manual command only** (`python -m agent.rag.resolve_questions`).
   Transcription is already the expensive, failure-prone step; the resolver stays
   separate and re-runnable after prompt or corpus improvements.
3. **Grounding policy: always answer, and label the grounding.** Grounded answers
   cite retrieved passages; ungrounded answers (weak or no corpus support) are
   labeled in the sidecar and in the marker. Reuses the `/hint` pattern in
   `rag_agent.py` (key terms, `retrieve_passages(..., key_terms=...)`,
   `grounded = any passage mentions a key term`, else an ungrounded fallback).
4. **Approach 1:** a dedicated module reusing `_extract_key_terms`, `retrieve_passages`
   and `_term_match_count`, with its own prompt. Rejected: calling `answer_question()`
   per question (chat-shaped: history, problem-request routing, viz/report/summary
   side effects, no grounded flag) and batching all of a note's questions in one
   call (loses the per-question grounding signal).

## Question identity

- Source of truth for what questions exist: the **raw transcript**
  (`processed_outputs/<name>.excalidraw.md`), which regeneration of the `.rag.md` never changes.
- A tag's **question text** is the text following `[Question]` up to the next `?`
  (inclusive), else to end of line, capped at 200 chars, whitespace-collapsed.
- **Question id** = `q<ordinal>-<8 hex>`: `ordinal` is the 1-based position among the
  raw transcript's tags; the hex is the first 8 chars of SHA-256 of the
  lowercased, whitespace-collapsed question text. Stable across `.rag.md`
  regeneration because it never reads the `.rag.md`.

## Sidecar: `processed_outputs/<name>.excalidraw.questions.md`

Frontmatter (flat, via `build_frontmatter`): `source_excalidraw`, `source_note_file_id`,
`resolver_model`, `resolved_at` (updated on each write), `questions` (count).
One section per question:

```
## q1-1a2b3c4d - <question text>
<!-- qid: q1-1a2b3c4d; grounded: true; model: gemini-3.6-flash; resolved_at: <iso>; stale: false -->

**Context:** <quote of the surrounding handwriting, trimmed>

<answer prose, LaTeX kept as $...$ / $$...$$>

**Sources:** <citation 1>; <citation 2>
```
Ungrounded entries replace the last line with `**Sources:** none -- not sourced from your course materials.`
The metadata comment is the machine-readable record; the parser reads only it
and the section boundaries (`## ` headings), so prose edits by the user survive.

Writes are atomic (temp file in the same directory, then `os.replace`) and happen
only when at least one entry is new or updated. A failed question writes nothing
for that question and is retried on the next run. Existing entries are kept
verbatim unless `--redo` selects them.

## Resolution flow (per question)

1. **Context**: the raw block enclosing the tag (the `[Handwritten]` segment, or the whole
   body for a handwriting-only note), trimmed to about 1500 chars centered on the tag, plus the
   previous and next `[Slide]` blocks (about 800 chars each) when the note has slides.
2. **Key terms**: `_extract_key_terms(question + context, client)`.
3. **Retrieve**: `retrieve_passages(roots, query=question + short context, client,
   course=<note's course>, key_terms=key_terms)`. The note's own `.rag.md` and sidecar
   are excluded from the results so a question is never "grounded" in itself.
4. **Grounded?** `not key_terms or any(_term_match_count(p.text, key_terms) for p in passages)`
   (identical to `/hint`).
5. **Generate**: grounded -> a prompt with the question, context and excerpts (cite by the
   excerpt's own citation string); ungrounded -> same prompt without excerpts, told to
   answer from general knowledge and to say when it is unsure. Default model
   `gemini-3.6-flash`; `--model` overrides. Temperature 0.2.
6. **Record** the entry (answer, grounded flag, model, citations).

## Marker in the `.rag.md`

Only the tag token is rewritten; the question text stays.

- Open: `[Question]`
- Answered, grounded: `[Question: answered -> <sidecar filename>#<qid>]`
- Answered, ungrounded: `[Question: answered (ungrounded) -> <sidecar filename>#<qid>]`

(The filename is the sidecar's basename, since it sits in the same folder; it may contain
spaces, so the marker is plain text, not a Markdown link.)

`questions.apply_markers(raw_path, rag_path)` is **deterministic (no model call)** and idempotent:

1. Read tags from the raw transcript (ids, question text) and from the `.rag.md`
   (matching `\[Question(?::[^\]]*)?\]`, so open and already-marked tags both count).
2. Pair them: **by position** when the counts are equal; otherwise greedily by
   `difflib.SequenceMatcher` ratio >= 0.8 on normalized question text.
3. For each paired raw tag that has a sidecar entry, rewrite the `.rag.md` tag to the marker
   for that entry; a raw tag with no sidecar entry leaves its `.rag.md` tag open.
4. A sidecar entry whose raw tag has no match in the `.rag.md` is flagged `stale: true` in its
   metadata comment (not deleted); `stale` returns to `false` if a later pass matches it.
5. Writes the `.rag.md` only if its text changed.

Called from: the resolver (after the sidecar write succeeds); `write_outputs` in
`transcribe_excalidraw.py`, right after the `.rag.md` is written and **before** indexing,
so regenerated notes get their markers back and the card's content hash matches the file.
Failure in `apply_markers` inside `write_outputs` is non-fatal (print a `WARNING:`).

## Indexing the sidecar

- New doc type `excalidraw_questions` (constant in `index_card.py`, alongside `EXCALIDRAW_DOC_TYPES`).
- `rebuild()` gets a discovery path for `*.excalidraw.questions.md` and indexes each with
  `reconcile_and_write(..., known_doc_types={"excalidraw_questions"}, content_sample=<sidecar text>)`.
- `file_id = compute_id_from_parts(["excalidraw_questions", <source note's file_id>])`:
  stable across sidecar rewrites (hashing the sidecar's own bytes would mint a new card on every write).
- `chunk` splits it at the per-question `##` headings, giving citable per-question passages.
- Writing markers changes the `.rag.md` content hash, so `rebuild` re-embeds that note's card once.
  The resolver does not call `rebuild`; the user (or the next scheduled rebuild) does.

## CLI

`python -m agent.rag.resolve_questions [--root R] [--course C] [--note FILENAME] [--dry-run] [--redo] [--model M] [--max-questions N]`

- Discovers notes by scanning `processed_outputs/*.excalidraw.md` raw transcripts that
  contain `[Question]`. **Skips notes whose card has `subset_of`** (their questions duplicate the
  with-slides version's; the answer lives with the superset).
- `--dry-run`: lists notes and question ids/text, no API calls, no writes.
- Prints the total question count before the first model call. Uses
  `get_gemini_client("PAID_GEMINI_KEY")`, the project's convention for pipeline runs (the free-tier
  `GEMINI_API_KEY` caps at 20 requests/day per model).
- Per-question failures are isolated: the run continues, and the exit summary lists failed ids.
- Idempotent: ids already in a sidecar are skipped unless `--redo`; `--max-questions` caps a run.

## Testing

- `core/indexer/questions.py` unit tests: tag discovery (line-start and mid-sentence tags);
  id stability when the `.rag.md` rewords the question; sidecar round trip and atomic write;
  marker rewrite for grounded/ungrounded; `apply_markers` by position, by similarity when counts
  differ, leaving unmatched tags open, flagging stale entries, idempotence, no write when unchanged.
- `resolve_questions` tests with a fake Gemini client and patched retrieval: grounded and
  ungrounded paths, key-term check, own-note exclusion from retrieval, per-question failure
  isolation, `--redo`, `--dry-run` makes no calls, subset notes skipped.
- Hook tests: `write_outputs` re-applies markers from an existing sidecar and survives
  `apply_markers` failure; `rebuild` indexes a sidecar with the stable id and does not duplicate
  the card across rewrites.
- Regression: the full suite (1939+) must pass; `core/indexer` is shared.
- Real-data check: `--dry-run` on microecon lists exactly the 7 questions across 4 notes; the real
  run (4 notes, about 14-21 model calls) only with the user's go-ahead, then verify with a query that a
  resolved answer is retrievable and the `.rag.md` shows markers.

## Out of scope

- Interactive or multi-turn question answering (that is the tutor's job).
- Editing the raw transcript or the user's own handwriting transcription.
- Reusing a superset's answers inside subset notes' markers.
- Pruning stale sidecar entries, and rewriting answers when the corpus later improves
  (use `--redo`).
- Resolving `[Question]` tags in non-Excalidraw notes.

## Open questions for the implementation plan

- **Shared segment helper.** Splitting `**[Slide]**`/`**[Handwritten]**` blocks now exists in
  `transcribe_excalidraw.py` and a minimal copy in `core/indexer/related.py`; the resolver would
  be a third user. Recommendation: one small refactor task moving it to a shared module in
  `core/` that all three import.
- **Where `apply_markers` imports its tag regex from** so the transcriber, resolver and tests
  agree on one definition of "a `[Question]` tag".
- Prompt wording for the grounded and ungrounded answers (to be pinned by the plan with tests that
  assert the structure, not the model's output).
