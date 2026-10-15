# Excalidraw agent driver — design spec

**Status:** draft, not yet implemented.
**Branch:** `claude/excalidraw-agent-driver`.
**Follows:** `docs/superpowers/specs/transcribe_notes/
2026-10-15-consolidated-pipeline-design.md`'s Stage 2 ("Excalidraw agent
driver (future work)"), which deferred this because it "needs its own
task-card design (chunk image + trailing-context text, not a page image)."
This spec is that design.

## Goal

Extend the collect/submit/manifest pattern `transcribe_notes.py` already has
for PDFs (`AgentDriver`, `agent_submit.submit_doc`, `.agent_work/<run-id>/`)
to `transcribe_excalidraw.py`, so Excalidraw notes stop being unconditionally
deferred when `route_notes_transcribe.py` runs with `--driver agent`. Once
this lands, "update my notes for `<course>`" (the Stage-1 goal) covers
Excalidraw notes on the subscription path too, not just PDFs.

**Post-review amendment (2026-10-15):** the consolidated-pipeline spec's
default driver flipped from `"api"` to `"agent"`, with a new explicit
`--allow-api-fallback` flag at `--submit` time (see that spec's "Amendment"
section). This spec's CLI-integration section below is written against that
amended default, not Stage 1's original `default="api"` text.

## Verified current state (this session, commit `c406ce3`)

- `transcribe_chunks()` (`transcribe_excalidraw.py:214`) calls
  `transcribe_page_via_gemini` directly in a loop over every chunk, with no
  persisted cache — a rerun always redoes every chunk from scratch. This is
  different from PDFs, which read/write `<name>_pages_cache.json` via
  `core.env.gemini_utils.load_json_cache`/`save_json_cache` and only call the
  driver for pages still missing. There is nothing for an agent driver to
  check against to know what's "already staged" vs. "needs a new card," so a
  cache must exist before collect/submit mechanics can work at all.
- `expand_transcription()` (`transcribe_excalidraw.py:373`) is a second,
  separate generative stage, called only after all chunks transcribe
  successfully. For a non-slide note it's one `generate_content` call; for a
  slide-aware note, `expand_with_verbatim_slides` (`:316`) calls a `generate`
  callback once per handwriting segment (could be 1, could be many,
  determined by `split_labeled_segments`).
- `route_notes_transcribe.py`'s `_defer_excalidraw_for_agent_driver` (added in
  Stage 1) unconditionally empties `plan.excalidraw_todo` whenever
  `--driver agent` is passed, printing "deferred: Excalidraw has no agent
  driver yet." This spec's implementation removes that function's call site
  (not the function necessarily — see Open items) and routes Excalidraw pairs
  into the same collect/submit flow PDFs already use.
- `agent_driver.py`'s `AgentPending` and `NullDriverFired` exceptions are
  already generic (no PDF-specific state), confirmed by reading the file —
  reused as-is, no new exception types needed.
- `agent_work.py`'s `doc_slug_for(pdf_path, file_id)` and `doc_work_dir` are
  also generic string/path functions — reused as-is for Excalidraw notes,
  keyed on the `.excalidraw.md` path (not the image path, since the image is
  a derived export that can switch between `.png`/`.svg`).

## Decisions already made (owner, this session)

1. **Two separate agent stages**, not one bundled round-trip: collect+submit
   fully finishes chunk transcription before expansion's cards are ever
   written. Mirrors the PDF pattern exactly — `submit_doc` already re-invokes
   `process_pdf` once a tier-3 document's current card is complete but more
   remain, restaging rather than finishing in one shot; this is the same
   restaging idea applied across stages instead of within one.
2. **One task card per note per stage**, with multiple sections inside it
   (`## Chunk N` / `## Segment N`) — not one card per chunk or per segment.
   Mirrors the existing tier-3 multi-page card (`## Page N` sections in one
   card).

## Architecture

### New: a persisted chunk cache

`<output_dir>/<base_name>_chunks_cache.json` and `_chunks_driver.json`,
written/read via the same `load_json_cache`/`save_json_cache` helpers PDFs
already use (`core.env.gemini_utils`), keyed by stringified chunk index
(`"0"`, `"1"`, ...). `transcribe_chunks` is rewritten to:

1. Load the cache (empty dict if none exists).
2. Call the driver only for chunk indices not already in the cache.
3. Save the cache after every chunk (not just at the end) — matches PDFs'
   per-page save pattern, so a crash mid-run doesn't lose earlier chunks.

This is a behavior change for the plain API path too (not agent-only): a
second run after a partial failure now resumes instead of redoing every
chunk. That's a strict improvement and needed either way, so it isn't gated
behind `--driver agent`.

### New: `ExcalidrawDriver` protocol

One protocol, two methods — same shape as `TranscriptionDriver` in
`agent_driver.py`, added to that file (it already documents itself as "the
driver seam for transcribe_notes.py's two Gemini call sites"; this adds
transcribe_excalidraw.py's two call sites alongside them, same module, same
`ApiDriver`/`AgentDriver`/`NullDriver` naming convention but as new classes
— `ExcalidrawApiDriver`, `ExcalidrawAgentDriver`, `ExcalidrawNullDriver` —
since the method signatures differ from the PDF driver's):

```python
class ExcalidrawDriver(Protocol):
    def transcribe_chunk(
        self, excalidraw_md_path: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str: ...

    def expand_note(
        self, excalidraw_md_path: str,
        segments: list[tuple[str, str, list[str]]],  # (label, text, neighbor_slide_texts)
    ) -> dict[int, str]: ...  # segment index -> expanded text
```

`ExcalidrawApiDriver.transcribe_chunk` wraps today's direct
`transcribe_page_via_gemini` call (through `call_with_retries`, unchanged
behavior). `ExcalidrawApiDriver.expand_note` wraps
`expand_with_verbatim_slides`'s per-segment `generate()` loop for the
slide case, and a single call for the non-slide case — both paths return a
`{segment_index: text}` dict so `expand_note`'s return shape is uniform
regardless of how many underlying calls it took.

### Task cards

**Transcription card** (one per note, written when ≥1 chunk is missing from
the cache): all missing chunks in one card, `## Chunk N` sections, each with
its image and `build_chunk_transcription_prompt`'s prompt text (built with
whatever accumulated context the *cache* already has for earlier chunks —
real context, not a placeholder, since cached chunks are real transcriptions
already). A card note (reusing tier-3's phrasing) tells the agent: for any
chunk in this card *after* the first, carry forward your own transcription of
this card's earlier chunks as context, same as tier-3 batches today.

**Expansion card** (one per note, written once transcription is fully
cached): one `## Segment N` section per `split_labeled_segments` segment
(a non-slide note is a single segment covering the whole raw markdown — no
special-case formatting). Each section shows the segment's own text to
expand, plus its neighboring slide text (if any) as read-only context,
mirroring `build_handwriting_expansion_prompt`. Expected-output format block
matches the existing `--- PAGE <n> ---` convention, adapted to
`--- SEGMENT <n> ---`.

### Submit-side validation

New `validate_excalidraw_chunk_output`/`validate_excalidraw_expansion_output`
in `agent_submit.py`, reusing what already generalizes
(`_looks_like_repetition_loop`, `_unclosed_code_fence`,
`_unbalanced_display_math`, the duplicate-segment check) and dropping what's
PDF-specific (the local-text-hint length-ratio warning — Excalidraw chunks
have no OCR text layer to compare against).

### `submit`'s restaging across stages

`submit_doc`'s existing recursive restage (tier-3: not all pages cached yet
→ stage the next batch and call `process_pdf` again) extends to a second
axis: transcription complete but expansion not yet collected → after writing
all chunks into `_chunks_cache.json`, call `process_excalidraw_note` again
with a fresh `ExcalidrawAgentDriver`; its `expand_note` call raises
`AgentPending` (first collect for this note), which is the signal to stage
the expansion card and report "incomplete: transcription complete, expansion
card staged" rather than "complete."

### CLI integration

`route_notes_transcribe.py` stops calling `_defer_excalidraw_for_agent_driver`
on the Excalidraw todo list under the (now-default) agent driver; instead it
dedupes (reusing `dedupe_by_file_id`, generalized to accept any path list —
it already only touches `compute_file_id`, which works on any file) and
passes the Excalidraw pairs into `run_plan` alongside the PDF path, using
`ExcalidrawAgentDriver` the same way PDFs use `AgentDriver`. `--submit`
matches collected Excalidraw doc-slugs the same way it already matches PDF
slugs (by `doc_slug_for(md_path, compute_file_id(md_path))`).
`--bootstrap`'s printed contract is updated to say Excalidraw notes are
included now, replacing Stage 1's "Excalidraw notes are not part of this
run" line. `--submit --allow-api-fallback` finishes a note's remaining
pending/bounced chunk or expansion cards via `ExcalidrawApiDriver`, same as
the PDF path — see the consolidated-pipeline spec's amendment.

## Guardrails (carried over from the consolidated-pipeline spec)

- No hidden generative fallback: a note with a pending expansion card is
  reported "pending agent work," never silently re-expanded through a
  metered call. `--allow-api-fallback` at `--submit` time is the one
  sanctioned, explicit exception (see the consolidated-pipeline spec's
  amendment) — it is never implied by a timeout, an error, or any other
  automatic condition.
- Grounding retrieval (`_retrieve_grounding`, `search_passages`) stays on the
  direct API path always — it's an embedding/retrieval call, not a
  generative one, same reasoning the consolidated-pipeline spec used to keep
  chunk/embed off the agent driver entirely.
- `--dry-run` previews (chunk counts, cache hit/miss per note) without
  writing cards or cache files.

## Acceptance evidence

Unit tests for: the new chunk cache (resumability — a chunk already in cache
is never re-requested from the driver), `ExcalidrawAgentDriver`'s card
writing for both transcribe and expand stages (mirroring
`tests/pipelines/transcribe_notes/test_route_agent_driver.py`'s style),
`agent_submit.py`'s new validators, and the cross-stage restage in
`submit_doc`. No live API calls in tests. Run via
`python -m pytest tests/pipelines/transcribe_notes/`.

## Open items for the implementation plan

- Whether `_defer_excalidraw_for_agent_driver` is deleted outright or kept
  dead-code-free by removing its only call site and the function together —
  implementation plan should just delete it; nothing else calls it.
- Exact slug collision behavior if a PDF and an Excalidraw note in the same
  run happen to produce the same `doc_slug_for` output (same base filename,
  same first-8-hex-chars file id) — vanishingly unlikely (file id is a
  content hash) but worth a one-line guard or an explicit non-goal note in
  the plan.
