# Agent-driven transcription mode — design spec

**Status:** draft, pending owner review. **Branch:** `claude/transcribe-agent-mode-notes`.

## Why

`transcribe_notes.py` routes documents to the cheapest tier that fits (local
extraction, hybrid batch repair, whole-document batching, or full
page-by-page vision with accumulated context), but every tier past local
extraction pays metered Gemini calls. The user wants a subscription IDE
agent (Antigravity first; Claude Code also works) to do that vision work
instead, as a selectable transport, not a replacement for the API path.
First validation target: the 7 tier-3 (handwritten) documents and ~513
flash-lite pages under `academic_resources/microecon/{2024_class,2025_class}`
(see the dry-run numbers in
`docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md`,
2026-10-09 entry). General option for any large run, not microecon-specific.

Pattern to copy: `agent/tutor`'s `prep-collect` / `prep-submit` contract —
a CLI step writes work for the agent to fill in by hand, a second CLI step
validates and only then lets the result flow into the real output path.

## Non-goals

- No shared `core/` collect/submit/validate helper yet. `docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md`
  wants the same shape of helper for its own critic/explainer task cards;
  that spec's own stated decision is to build its version behind a
  `Driver`-style interface now and adopt a shared helper later if one lands
  first. This spec does the same — no joint design work blocking either.
- No change to tier routing, defect detection (`page_looks_defective`,
  `has_reliable_pagination`), or the write/index path (`build_final_markdown`,
  `_write_markdown_and_index`). The agent driver only changes how a batch's
  or page's transcribed text is obtained.
- No local Ollama vision tier. Untested here and the pipeline's own README
  already flags Marker/Surya OCR as weak on handwriting; a local vision
  model is a separate, unvalidated idea and out of scope.
- Does not eliminate all metered cost: `_write_markdown_and_index` calls
  `reconcile_and_write`, which uses the Gemini `client` for document-type/tag
  classification during indexing, regardless of which driver produced the
  transcription. This is a small existing cost, unaffected by this design.

## Architecture: a `Driver` swapped inside the existing tier loops

`process_pdf`'s four tiers (local, hybrid repair, whole-document batch,
accumulating tier-3) stay exactly as they are — same routing decisions, same
`_pages_cache.json` cache, same batching (`split_run_into_batches`,
`group_into_runs`), same prompts (`build_transcription_prompt`,
`build_batch_transcription_prompt`) and same response parsing
(`parse_transcription_response`, `parse_batch_transcription_response`). The
only change is a `Driver` seam at the three call sites that currently call
Gemini directly (`repair_batch`'s batch call, `repair_page_individually`'s
single-page call, and tier-3's `transcribe_page_via_gemini` call):

```python
class TranscriptionDriver(Protocol):
    def transcribe_batch(self, pdf_path, batch, prompt, image_paths) -> dict[int, str] | None
    def transcribe_page(self, pdf_path, page_num, prompt, image_path) -> str | None
```

- **`ApiDriver`** (default, `--driver api`): wraps today's
  `transcribe_batch_via_gemini`/`transcribe_page_via_gemini` calls verbatim.
  No behavior change from today.
- **`AgentDriver`** (`--driver agent`): makes no network call. It renders
  the batch/page's images (same DPI as the tier, via
  `render_page_to_image_bytes`, written to disk instead of kept in memory),
  writes a task card recording the prompt + image paths + expected output
  shape, appends a row to the run's worklist, and returns `None` (a
  "pending" result).

`process_pdf`'s existing retry/fallback code already treats "this batch/page
didn't come back" as non-fatal — it logs a warning and continues (hybrid/
whole-doc tiers) or stops cleanly for a rerun (tier-3, because of
accumulated context). A driver returning `None` reuses that exact path: no
new control flow in `process_pdf` itself, just a different source of "this
one isn't done yet." This means `collect` for a document *is* a call to
`process_pdf` with `AgentDriver` installed — not a separate scan that
duplicates tier/defect logic.

## `collect`

```
python -m pipelines.transcribe_notes.transcribe_notes --notes-subdir <dir> --driver agent --collect
```

Runs `process_pdf` with `AgentDriver` over every document in the subdir
(skipping cached pages/batches exactly as today). For each PDF, writes to
`processed_outputs/_agent_work/<run-id>/<doc-slug>/`:

- `images/page-<NNNN>.png` — rendered once per page needed, at the tier's
  existing DPI (150 for hybrid/whole-doc, 200 for tier-3).
- `task-<NNNN>.md` — one card per batch unit:
  - tier-2/2b batches: the existing batch size (≤12 pages,
    `_MAX_BATCH_SIZE`), prompt from `build_batch_transcription_prompt`
    (including before/after bookend context where applicable), the batch's
    image paths, and an `## Expected output` block giving the exact
    `--- PAGE N ---` delimited format `parse_batch_transcription_response`
    parses.
  - tier-3 batches: a new fixed batch size of 5–8 pages
    (`_AGENT_TIER3_BATCH_SIZE`, exact value left to the plan), prompt from
    `build_transcription_prompt` per page within the card, the card's image
    paths, and — for every card after the first — the trailing
    `_ACCUMULATION_WINDOW` pages' **already-submitted** text pulled from
    the cache. **Strict ordering is load-bearing here**: `collect` only
    emits a document's next tier-3 card once the previous one shows
    `submitted` in the worklist (not merely `pending`/`filled`), since the
    next card's accumulated-context block depends on that prior card's real
    submitted output, not a guess. `collect` run again on a document with
    outstanding unsubmitted tier-3 cards is a no-op for that document until
    they're submitted.
  - a `## Agent output` section, initially empty, with the same
    page-delimited format as `## Expected output` — the agent fills this in
    place rather than writing a separate results file.
- `worklist.md` — one row per task card: tier, page range, output path,
  status (`pending` → `filled` → `submitted` | `bounced: <reason>`).

## `submit`

```
python -m pipelines.transcribe_notes.transcribe_notes --submit <run-id> [--doc <slug>]
```

For every card marked `filled` in the worklist:

1. Parse `## Agent output` with the existing `parse_batch_transcription_response`
   (batches) or `parse_transcription_response` (single pages) — no new
   parsing code.
2. Validate:
   - every page number the card expected is present and non-empty;
   - parsed page count matches the card's declared range;
   - `$...$`/`$$...$$` delimiters balanced per page;
   - no leftover code fence or truncation marker — reuse
     `_looks_like_repetition_loop`, plus a new check that each page's text
     ends on reasonable closing punctuation/delimiter rather than
     mid-sentence or mid-`$`.
3. **Pass:** write each page's text into the document's existing
   `_pages_cache.json` under the same `str(page_num)` key the `ApiDriver`
   uses — same file, same format, no migration. Mark the card `submitted`.
   Once every card for a document is `submitted`, call `build_final_markdown`
   + `_write_markdown_and_index` exactly as `process_pdf` does today, so
   frontmatter, caches, offering labels, and indexing are identical to a
   pure-API run.
4. **Fail:** mark the card `bounced: <reason>` in the worklist; the agent
   re-reads that specific card, redoes just that batch in place, and
   `submit` is re-run. Nothing else in the document is touched.

Because both drivers write into the same `_pages_cache.json`, a run isn't
locked to one driver end-to-end: `--driver api` can finish any cards the
agent skipped, or vice versa, on a plain rerun.

## CLI surface

```
--driver {api, agent}     # default: api (today's behavior, unchanged)
--collect                 # with --driver agent: render + write task cards, no transcription
--submit <run-id> [--doc <slug>]   # validate filled cards and write through
```

`--driver agent` is a general flag on the existing
`transcribe_notes`/`route_notes_transcribe` CLI, not a microecon-specific
mode — any large `--notes-subdir` run can use it.

## Open items for the implementation plan

- Exact tier-3 agent batch size (`_AGENT_TIER3_BATCH_SIZE`): 5–8 pages,
  pick a default from real context-window behavior during implementation.
- Whether `collect` should stage more than one not-yet-submitted tier-3
  card ahead at a time (bounds work-dir size vs. lets the agent batch its
  own turns) — default to staging exactly one ahead until proven too slow.
- Exact wording/regex for the "ended mid-sentence or mid-delimiter"
  truncation heuristic in `submit`.
- Task-card Markdown template field names and exact worklist schema.
- Validation-dry-run on the 7 tier-3 docs + ~513 flash-lite pages before
  any real agent run, to confirm card sizing and the cache round-trip work
  end to end with zero paid calls.
