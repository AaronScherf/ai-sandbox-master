# Consolidated notes orchestrator (Stage 3, part 2) — design spec

**Status:** draft, not yet implemented.
**Branch:** `claude/notes-pipeline-orchestrator`.
**Follows:** `2026-10-15-consolidated-pipeline-design.md` (Stage 3's first bullet —
the question-resolver agent driver — shipped separately on
`claude/question-resolver-agent-driver`, see
`agent/rag/2026-10-16-question-resolver-agent-driver-design.md`). This spec
covers Stage 3's second bullet: the thin orchestrator.

## Goal

One command ("update my notes for econometrics") drives a course from raw
PDFs/Excalidraw canvases through a chunked, searchable corpus: transcribe →
expand → SVG backup → resolve tagged questions → chunk/embed. Re-entrant: a
course with agent work still pending advances only what's ready and reports
the rest as pending, since collect/submit is multi-session by nature (human
relay to Antigravity).

## Where it lives

Extends `pipelines/transcribe_notes/route_notes_transcribe.py` in place —
not a new file. That module's `build_plan()`/`run_plan()` already is the
per-course "check the whole corpus" orchestrator, and it already carries the
`--driver {api,agent}` / `--collect` / `--run-id` / `--submit RUN_ID` /
`--allow-api-fallback` / `--bootstrap RUN_ID` flags for PDF transcription
(Stage 1). This spec applies those same flags uniformly across all three
agent-capable surfaces instead of adding new ones.

## Per-file stage state

Each discovered PDF/Excalidraw source advances through:

```
needs_transcribe → transcribe_pending → needs_resolve_questions
  → resolve_pending → needs_chunk → done
```

- `needs_transcribe` / `transcribe_pending`: existing Stage 1/2 states
  (`filter_unprocessed_pdfs`/`filter_unprocessed_excalidraw` plus agent
  manifest status). Unchanged by this spec.
- `needs_resolve_questions`: the markdown sidecar exists on disk (finalized,
  not just "transcribed this run") **and** the note contains at least one
  `[Question]` tag not yet answered. A note with no question tags skips
  straight past this state.
- `resolve_pending`: `resolve_questions`'s own manifest shows cards
  staged/bounced for this note under the active run-id.
- `needs_chunk`: transcription finalized, and either the note has no
  questions or all of them are answered. `chunk_index`'s own content-hash
  check (unchanged by this spec) decides whether re-chunking is a no-op.
- `done`: chunked at the current content hash.

**Ordering invariant:** a note transcribed via the agent driver *in this
same invocation* is never eligible for `needs_resolve_questions` in that
same invocation. Finalization only happens at `--submit` time, and a note
that was just submitted this call could still have bounced cards reported
in the same run. Treating "submitted this run" as equivalent to "finalized
on disk, read back on the next invocation" would risk staging
resolve-questions cards against content that isn't actually settled yet.
So: compute each note's stage from what's on disk at the *start* of the
call, never from in-memory results produced during the call. A note
finalized this run becomes resolve-questions-eligible on the *next*
`route_notes_transcribe.py` invocation. This keeps re-entrancy simple (every
call asks "what's finalized as of right now?") at the cost of one extra
round trip for notes that go through both transcription and question
resolution in the same session — acceptable, since collect/submit already
assumes a human relay to Antigravity between calls.

## Execution flow per course

1. `build_plan()` gains two more fields beyond today's PDF/Excalidraw lists:
   notes needing resolve-questions work, and notes needing chunk/embed.
   Computed by importing `agent/rag/resolve_questions.py`'s existing
   manifest/cache helpers and `core/indexer/chunk_index.py`'s existing
   content-hash check — no new state files, no duplicate bookkeeping.
2. `run_plan()`, after its existing transcribe/expand/backup steps:
   - **Resolve-questions step:** for each course with eligible notes, call
     `resolve_questions`'s per-course entry points in-process (not a
     subprocess), passing through `args.driver`, `args.run_id`,
     `args.collect`, `args.submit`, `args.allow_api_fallback`. Same
     collect/submit semantics as the PDF/Excalidraw surfaces: `--collect`
     stages key-term/answer cards under `.agent_work/<run-id>/<doc-slug>/`
     (same convention, already collision-free — resolve-questions and
     transcription use different card filenames within a doc's directory);
     `--submit RUN_ID` consumes them.
   - **Chunk/embed step:** for each course with eligible notes, call
     `chunk_index`'s existing per-course chunk function in-process. No
     agent card — this step is unconditional local work (subject to its
     own freshness check), so it runs on every invocation regardless of
     `--collect`/`--submit`, the same way SVG backup already does.
3. `print_summary()` gains per-course counts for the two new stages:
   resolved / pending questions, chunked / pending chunk.

## CLI

No new flags. `--driver`, `--collect`, `--run-id`, `--submit RUN_ID`,
`--allow-api-fallback`, `--bootstrap RUN_ID` already exist on
`route_notes_transcribe.py` (Stage 1) and now govern all three
agent-capable surfaces together under one run-id, instead of PDF
transcription alone. `--dry-run` previews resolve-questions and chunk
eligibility the same way it already previews transcription/backup work,
without calling any API or writing any file.

## Guardrails (carried over from the parent spec, apply here too)

- **No hidden generative fallback.** `needs_resolve_questions` notes under
  `--driver agent` without `--submit --allow-api-fallback` report as
  pending, never silently retried against the metered API.
- **Warn over $1.** Unchanged — each underlying stage already enforces this
  independently; the orchestrator doesn't re-estimate across stages.
- **Resumability carries through.** Each stage's own freshness check
  (transcription manifest, resolve-questions answer cache, chunk hash)
  decides what's stale; the orchestrator does not duplicate that logic, only
  sequences the calls.

## Out of scope

- Stage 4 (`--maintain-guides`) — untouched, future work.
- No new agent-card format. Resolve-questions and chunk/embed reuse their
  existing entry points and manifests as-is; this spec only wires calls and
  state computation into `route_notes_transcribe.py`.

## Acceptance evidence

Unit tests mirroring `tests/pipelines/transcribe_notes/test_route_notes_
transcribe.py`'s existing `tmp_path`-based style: per-file stage
computation (all six states), the ordering invariant (a note finalized
mid-call does not appear eligible for resolve-questions within that same
call), and the new summary output — run via `python -m pytest tests/
pipelines/transcribe_notes/test_route_notes_transcribe.py`. No live API
calls in tests. A real-corpus `--dry-run` before the first non-dry-run use,
per existing convention.
