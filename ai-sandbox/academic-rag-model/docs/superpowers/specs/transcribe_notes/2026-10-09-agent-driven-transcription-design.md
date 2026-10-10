# Agent-driven transcription mode — design spec

**Status:** draft, revised after peer code review, pending owner review.
**Branch:** `claude/transcribe-agent-mode-notes`.

**Revision note (2026-10-09b):** a peer Claude session reviewed the first
draft against `pipelines/transcribe_notes/transcribe_notes.py` and
`core/env/gemini_utils.py` and found four blocking problems with the
original "return `None`, reuse the existing non-fatal path" design: it
isn't non-fatal (exceptions, not `None`, are what's handled today), it
would write partial/incomplete output, it can't reuse
`_write_markdown_and_index` as a one-line call the way the original draft
claimed, and task-card/image files would land inside the tablet-synced,
indexed `academic_notes/` tree. All four are fixed below (see each
section's "Fix vs. first draft" note). Several should-fix points
(duplicate-group handling, run manifest, tier-3 context scope, validation
bounce criteria, provenance fields, seam location) are incorporated too.
Verified by re-reading the relevant code; nothing executed.

## Why

`transcribe_notes.py` routes documents to the cheapest tier that fits (local
extraction, hybrid batch repair, whole-document batching, or full
page-by-page vision with accumulated context), but every tier past local
extraction pays metered Gemini calls. The user wants a subscription IDE
agent (Antigravity first; Claude Code also works) to do that vision work
instead, as a selectable transport, not a replacement for the API path.
General option for any large run, not microecon-specific.

**Current corpus state** (see
`docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md`,
2026-10-09 entries): the other ~79 prior-year microecon documents from the
original dry-run were already transcribed via the API on 2026-10-09
(~620k input / ~305k output tokens). The **7 tier-3 (handwritten) documents,
~125 pages**, under `academic_resources/microecon/{2024_class,2025_class}`
were deliberately held back for this mode and are the first validation
target.

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
  `has_reliable_pagination`), frontmatter's `routing` values, or the
  write/index path (`build_final_markdown`, `_write_markdown_and_index`).
  `pipelines/postprocess_notes/postprocess_discovery.py` branches on exact
  `routing` strings (`local`, `hybrid`, `gemini_batched`,
  `gemini_accumulating`); this design adds a separate `driver` field rather
  than touching `routing`.
- No local Ollama vision tier — out of scope, per the status doc.
- Does not eliminate all metered cost: `_write_markdown_and_index` still
  calls `reconcile_and_write`, which uses the Gemini `client` for
  document-type/tag classification during indexing, regardless of driver.
- PDF path only. `transcribe_excalidraw.py` has its own separate Gemini
  call and vision loop and is not touched by this design.
- `repair_page_individually` and `transcribe_page_via_gemini`'s own
  signatures are not touched — `postprocess_notes.py` and
  `transcribe_excalidraw.py` also call them directly, and
  `tests/pipelines/transcribe_notes/test_transcribe_notes.py` calls
  `repair_batch(MagicMock(), ...)` against the current signature. The
  driver seam sits at `process_pdf`'s three call sites (below), not inside
  these shared functions.

## Architecture: a `Driver` injected at `process_pdf`'s three call sites

`process_pdf`'s four tiers (local, hybrid repair, whole-document batch,
accumulating tier-3) keep their routing, defect detection, batching
(`split_run_into_batches`, `group_into_runs`), prompts
(`build_transcription_prompt`, `build_batch_transcription_prompt`), and
response parsing (`parse_transcription_response`,
`parse_batch_transcription_response`) exactly as they are. A `Driver` is
injected only at the three places `process_pdf` currently calls
`call_with_retries(lambda: repair_batch(...))`,
`repair_page_individually(...)`, and
`call_with_retries(lambda: transcribe_page_via_gemini(...))` — the call
sites, not the shared functions themselves.

```python
class AgentPending(Exception):
    """Raised by AgentDriver to signal a batch/page has no result yet.
    Never retried, never falls back to per-page calls -- callers must
    catch it ahead of the existing `except Exception` handling."""

class TranscriptionDriver(Protocol):
    def transcribe_batch(self, pdf_path, batch, prompt, image_paths) -> dict[int, str]  # raises AgentPending
    def transcribe_page(self, pdf_path, page_num, prompt, image_path) -> str            # raises AgentPending
```

- **`ApiDriver`** (default, `--driver api`): wraps today's
  `transcribe_batch_via_gemini`/`transcribe_page_via_gemini` calls
  unchanged, still through `call_with_retries`. No behavior change from
  today.
- **`AgentDriver`** (`--driver agent`): makes no network call. It renders
  the batch/page's images (same DPI as the tier, via
  `render_page_to_image_bytes`), writes a task card, appends a row to the
  run manifest, and raises `AgentPending`.

### Fix vs. first draft (BLOCKING #1 and #7)

The first draft said returning `None` "reuses the existing non-fatal
path." **That was wrong.** `call_with_retries` (`core/env/gemini_utils.py:42`)
retries *any* `Exception` three times with 5s/10s/etc. backoff — a plain
`None` return would either be treated as a successful (empty) result, or,
if routed through an exception, would burn three retries and 15s+ of sleep
per pending item for nothing. Worse, in the hybrid and whole-document
tiers, the existing code treats *any* failure of the batch call as a
reason to fall back to per-page calls (`transcribe_notes.py` ~1204-1218,
~1281-1297) — so one pending batch would also spawn up to 12 duplicate
per-page task cards.

Fix: `AgentPending` is a dedicated exception type. At each of the three
call sites inside `process_pdf`, the surrounding `try/except` is split so
`except AgentPending` is checked **first** and simply records "this
batch/page is pending" (no retry, no per-page fallback, no cache write),
and the existing `except Exception` handling (retry exhaustion, per-page
fallback, tier-3's `break`) is unchanged and only ever sees real API
failures. This is new control flow in `process_pdf` — the first draft's
claim of "no new control flow" does not hold; three small `except
AgentPending` branches are added at the existing call sites.

## `collect`

```
python -m pipelines.transcribe_notes.transcribe_notes --notes-subdir <dir> --driver agent --collect
```

Runs `process_pdf` with `AgentDriver` over every document in the subdir
(skipping cached pages/batches exactly as today). **Needs no paid Gemini
client and no corpus write lock** — it never calls `_write_markdown_and_index`
(see Fix below) and only reads/renders locally.

### Fix vs. first draft (BLOCKING #2: no partial output)

The first draft said `collect` for a document "is a call to `process_pdf`
with `AgentDriver` installed." That's incomplete: every tier in
`process_pdf` falls through to `_write_markdown_and_index` after its loop
(`transcribe_notes.py` ~1228, ~1305, ~1365) regardless of whether every
page/batch actually came back — with `AgentDriver` raising `AgentPending`
for everything, that fall-through would write an incomplete `.md` file, a
corrupt index card, and still trigger a metered Gemini classification call
for every document (`main()` also builds a real Gemini client unless
`--dry-run`, ~1408).

Fix: a `collect_pdf(pdf_path, ...)` entry point wraps `process_pdf`'s tier
logic but checks, right before each tier's `_write_markdown_and_index`
call, whether any page in that tier is still pending (not in the cache).
If so, it returns immediately without writing anything — same "stop, rerun
later" contract tier-3 already uses for a real API failure, just applied
uniformly. `collect` mode never reaches `_write_markdown_and_index` and
therefore never needs the classification client or the write lock.

### Fix vs. first draft (BLOCKING #4: card/image location)

The first draft put task cards and rendered images under
`processed_outputs/_agent_work/...`. `resolve_output_dir()`
(`core/env/academic_hub_paths.py:53`) mirrors a notes PDF's
`processed_outputs/` into `academic_notes/` — the lightweight tree that's
both indexed and tablet-synced. Task-card Markdown would get indexed as
notes, and hundreds of MB of rendered PNGs would try to sync to the
tablet.

Fix: task cards, images, and the run manifest go under
`academic-hub/.agent_work/<run-id>/<doc-slug>/` — a dot-directory at the
hub root, outside both `academic_notes/` and `academic_resources/`.
Implementation must confirm (not assume) that `core/indexer` and the
hub's `.gitignore` already skip dot-directories, or add an explicit
exclusion before the first real run.

### Task cards and run manifest

For each PDF, `.agent_work/<run-id>/<doc-slug>/`:

- `images/page-<NNNN>.png` — rendered once per page needed, at the tier's
  existing DPI (150 for hybrid/whole-doc, 200 for tier-3).
- `manifest.json` — **machine-readable**, one entry per task card: tier,
  expected page numbers, DPI, source PDF path, `file_id`
  (`compute_file_id`), status (`pending` → `filled` → `submitted` |
  `bounced: <reason>`). `submit` reads expected pages from here, never by
  parsing the agent-editable card (should-fix: don't trust agent-editable
  text for validation bookkeeping).
- `worklist.md` — a human-readable rendering of the manifest, regenerated
  by `collect`/`submit`, for the agent and the owner to scan at a glance.
- `task-<NNNN>.md` per card:
  - tier-2/2b batches: existing batch size (≤12 pages, `_MAX_BATCH_SIZE`),
    prompt from `build_batch_transcription_prompt` (with bookend context
    where applicable), image paths, and an `## Expected output` block
    (format only — the real expectation lives in `manifest.json`).
  - tier-3 batches: a new fixed batch size of 5–8 pages
    (`_AGENT_TIER3_BATCH_SIZE`, exact value left to the plan). **Only a
    card's first page draws real accumulated context from the
    `_pages_cache.json`** (the trailing `_ACCUMULATION_WINDOW` pages from
    prior *submitted* cards); every later page within the same card
    depends on the agent's own preceding output earlier in that same card,
    which the card must say explicitly so the agent carries its own
    context forward within a card, not just across cards. At ~125 tier-3
    pages and a 5–8 page card size, this is roughly 16–25 collect/submit
    round trips; `submit` auto-stages the next tier-3 card for a document
    immediately after a successful submit, rather than requiring a
    separate `collect` invocation each time.
  - `## Agent output`, initially empty, same page-delimited format as
    `## Expected output` — filled in place.

### Fix vs. first draft (should-fix: duplicates within a run)

`find_existing_transcription` only matches against *finished* transcriptions
elsewhere in the corpus — it has nothing to match against for two
not-yet-transcribed byte-identical copies in the same `collect` run (the
status doc's dry-run found 8 such groups across `2024_class`/`2025_class`).
Fix: `collect` computes `file_id` for every discovered PDF up front and
dedupes within the run before creating any cards — one canonical set of
cards per unique `file_id`, with the duplicate(s) linked via
`link_duplicate_note` once the canonical copy is submitted.

## `submit`

```
python -m pipelines.transcribe_notes.transcribe_notes --submit <run-id> [--doc <slug>]
```

Needs the paid Gemini client (for indexing) and the corpus write lock —
unlike `collect`. Locates documents via the run's `manifest.json`
(`--notes-subdir` alone can't identify a specific run).

### Fix vs. first draft (BLOCKING #3: can't hand-roll the write path)

The first draft said `submit` would "call `build_final_markdown` +
`_write_markdown_and_index` exactly as `process_pdf` does today." It
can't, as a standalone call — frontmatter construction, the hybrid
tier's merge of local text with repaired pages, and the `routing`/`model`/
`offering_label` values are all inline inside `process_pdf`'s own tier
bodies, not factored out.

Fix: after validation passes and pages are written into
`_pages_cache.json`, `submit` does not reimplement any of that — it simply
**re-runs `process_pdf` for that document** (with the real `ApiDriver` or
no driver at all) once every page/batch the current tier needs is already
cached. `process_pdf`'s own cache-check branches
(`if all(str(p) in cache for p in batch): continue`, tier-3's
`if str(page_num) in cache: continue`) mean it falls straight through to
the unchanged `_write_markdown_and_index` call with zero new API calls,
getting frontmatter/merge/routing/offering_label construction for free
and identical to a pure-API run.

### Validation

For each card marked `filled` in the manifest, parse `## Agent output`
with the existing `parse_batch_transcription_response` (batches) or
`parse_transcription_response` (single pages) — no new parsing code.

**Fix vs. first draft (should-fix: validation scope).** The first draft's
"ends on reasonable closing punctuation" check and single-`$` balance
check were overbroad: a page can legitimately end on an equation, a
heading, or a bare page number, and single `$` collides with currency
amounts in econ problem sets. Narrowed to:

- **Bounce (blocking the card)**: a missing or empty expected page;
  `_looks_like_repetition_loop` trips; an unclosed code fence; unbalanced
  `$$...$$` (display math only, not single `$`).
- **Warn only (logged, doesn't block)**: output length far shorter than
  the page's local-text hint length (should-fix: cheap anti-skipping
  signal — catches a page the agent summarized or skipped instead of
  transcribing); anything else that looked unusual but didn't match a
  bounce rule.

A bounced card is re-marked `bounced: <reason>` in the manifest; the agent
re-reads that one card, redoes it in place, and `submit` is re-run.
Nothing else in the document is touched.

### Provenance (should-fix)

`model` in frontmatter currently records the real Gemini model
(`gemini-3.1-flash-lite`, etc.) and would be false for agent-transcribed
pages. Add `driver: api | agent` and, when `agent`, the agent's name
(e.g. `agent_name: antigravity`) to the frontmatter metadata dict passed
into `build_frontmatter`. `routing` itself is left untouched (see
Non-goals) since `postprocess_discovery.py` branches on its exact values.

Because both drivers write into the same `_pages_cache.json`, a run isn't
locked to one driver end-to-end: `--driver api` can finish any cards the
agent skipped, or vice versa, on a plain rerun of `process_pdf`.

## CLI surface

```
--driver {api, agent}     # default: api (today's behavior, unchanged)
--collect                 # with --driver agent: render + write task cards + manifest, no transcription, no client, no lock
--submit <run-id> [--doc <slug>]   # validate filled cards, write cache, re-run process_pdf to finish the write path
```

`--driver agent` is a general flag on the existing
`transcribe_notes`/`route_notes_transcribe` CLI, not a microecon-specific
mode — any large `--notes-subdir` run can use it.

## Open items for the implementation plan

- Exact tier-3 agent batch size (`_AGENT_TIER3_BATCH_SIZE`): 5–8 pages,
  pick a default from real context-window behavior during implementation.
- Confirm `core/indexer` and the hub's `.gitignore` skip
  `academic-hub/.agent_work/`; add an explicit exclusion if not.
- Exact `manifest.json` schema and `task-NNNN.md` template field names.
- Whether `submit`'s auto-staging of the next tier-3 card should have a
  cap (bound work-dir size) — default to staging exactly one ahead until
  proven too slow.
- Validation-dry-run on the 7 held-back tier-3 docs (~125 pages) before
  any real agent run, to confirm card sizing, the `AgentPending` seam, and
  the cache round-trip work end to end with zero paid calls.
