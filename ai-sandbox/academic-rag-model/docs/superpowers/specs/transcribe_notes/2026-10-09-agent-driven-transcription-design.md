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

**Revision note (2026-10-09c):** the same peer did a second pass on
commit `add8381` and confirmed the four blockers are fixed, with six
further points folded in below: `collect` must never write regardless of
pending state, not only when something is pending (tier-1 docs and
fully-cached docs have nothing pending and would otherwise still write);
`collect` must also short-circuit `process_pdf`'s duplicate-link branch
and skip `os.makedirs`, not just the tier write calls; tier-3's `Driver`
needed its multi-page-card mechanics spelled out, since `transcribe_page`
is a per-page call but cards are 5–8 pages; `submit`'s re-run of
`process_pdf` needed an explicit guard against spending money on a
partially-submitted document; `.agent_work/` is confirmed **not**
gitignored today (a real risk on a public repo) and the `.gitignore` rule
is now a required plan task, not an open item; and four smaller points
(mixed-driver provenance, scoping the length-warning to tier-2 only, a
`bootstrap` subcommand printing the agent's operating contract, and
simplifying duplicate handling to a plain re-run). Verified by re-reading
the relevant code, including confirming `academic-hub/.agent_work/` is
not currently gitignored; nothing executed.

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
    def transcribe_page(self, pdf_path, page_num, prompt, image_path, total_pages) -> str  # raises AgentPending
```

- **`ApiDriver`** (default, `--driver api`): wraps today's
  `transcribe_batch_via_gemini`/`transcribe_page_via_gemini` calls
  unchanged, still through `call_with_retries`. No behavior change from
  today.
- **`AgentDriver`** (`--driver agent`): makes no network call. For a
  batch call (`transcribe_batch`), it renders the batch's images, writes
  one task card for the whole batch, and raises `AgentPending` — the
  batch tiers already call this once per batch, so no further change is
  needed there. Tier-3 is different: `process_pdf`'s tier-3 loop calls
  `transcribe_page` once *per page*, but a tier-3 card covers 5–8 pages.
  On the call for a card's first pending page `n`, `AgentDriver.transcribe_page`
  stages a card covering pages `n..min(n+k-1, total_pages)` (it receives
  `total_pages` precisely so it can clamp at the document's end), writing
  each page's own `hint_text` and image into that one card, then raises
  `AgentPending` for page `n`. `process_pdf`'s existing tier-3 `break` on
  any exception (`transcribe_notes.py` ~1346-1352) then ends the loop
  exactly as it does for a real API failure — this is why no change to
  tier-3's loop body is needed beyond the `except AgentPending` split: the
  loop was already built to stop and let a rerun resume from the first
  uncached page. `submit` later writes all `k` pages from that one card
  into the cache at once, so the next `collect`/rerun resumes past the
  whole card, not just page `n`.

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

Fix, revised again after the second review: the first fix ("return early
if anything is pending") was still wrong — a tier-1 (fully clean, 0 API
calls) document, or a document whose pages are *all already cached* from
a prior run, has nothing pending, so it would fall through to
`_write_markdown_and_index` anyway and need the classification client and
write lock, contradicting "collect needs no client/no lock." Corrected
rule: a `collect_pdf(pdf_path, ...)` entry point **never calls
`_write_markdown_and_index`, unconditionally** — not "only when
something is pending." Concretely:

- Tier-1 documents (no `AgentDriver` call happens at all, since they need
  zero API calls either way) are **skipped entirely** in collect mode —
  reported as "nothing to collect, already free," not routed through the
  write path at all.
- For every other tier, `collect_pdf` runs the same batching/loop logic as
  `process_pdf` but replaces the write call with a report: "N/M pages
  cached, 0 pending — ready for submit's rerun" or "N/M pages cached, K
  pending — task cards written," and returns before reaching
  `_write_markdown_and_index` either way.

This also fixes a second instance of the same bug at the top of
`process_pdf` (~1109-1122): the `find_existing_transcription` /
`link_duplicate_note` branch runs *before* any tier routing, and
`link_duplicate_note` performs a real index write (`save_shard`) that
needs the write lock — confirmed by the peer review hitting a transient
`PermissionError` on `os.replace(.index/microecon.json, ...)` from this
exact branch during a real run. In collect mode, a byte-identical match
is reported ("would link to <path>, 0 API calls needed") instead of
calling `link_duplicate_note`. `process_pdf` also calls
`os.makedirs(output_dir, exist_ok=True)` before any of this, which
creates an empty `academic_notes/<course>/...` directory even when
nothing is ultimately written; harmless on its own, but `collect_pdf`
skips it too since there is never anything to write there in collect
mode.

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

**Confirmed by the second review: `academic-hub/.agent_work/` is NOT
gitignored today** (`git check-ignore` returns no match), and this repo
is public — the rendered page images are course material. Adding a
`.gitignore` rule for `ai-sandbox/academic-hub/.agent_work/` is therefore
a **required plan task that lands before the first `collect` run**, not
an open item to confirm later. `core/indexer/index_search.py` does skip
dot-directories during its own directory walk (lines 259 and 283), but
that only covers that one indexer entry point — the plan must include a
test that `.agent_work/` content is not discovered by any of
`postprocess_discovery.py`, `corpus_health`, or `offering_links.py`
either, rather than assuming the one confirmed skip generalizes.

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
cards per unique `file_id`. **Simplified per the second review (point
6d):** rather than calling `link_duplicate_note` directly for each
duplicate once the canonical copy is submitted, the duplicate is simply
left for a later `process_pdf` run (API or agent collect) over its own
folder — by then `find_existing_transcription` finds the now-finished
canonical card and links it through the existing, already-tested path,
with no new call site needed.

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
**re-runs `process_pdf` for that document** once every page/batch the
current tier needs is already cached. `process_pdf`'s own cache-check
branches (`if all(str(p) in cache for p in batch): continue`, tier-3's
`if str(page_num) in cache: continue`) mean it falls straight through to
the unchanged `_write_markdown_and_index` call with zero new API calls,
getting frontmatter/merge/routing/offering_label construction for free
and identical to a pure-API run.

**Guard (second review, point 4):** "re-runs `process_pdf`" needs a
condition and a safety net, or a bug could spend real money. (1) The
rerun only fires when the manifest shows **every** card for that document
is `submitted` — a document with one card still `pending`/`bounced` is
left alone; `submit` reports it as incomplete rather than re-running
anything. (2) The rerun is invoked with a `NullDriver` that raises on any
`transcribe_batch`/`transcribe_page` call instead of the real `ApiDriver`
— since every page should already be cached at that point, a `NullDriver`
call ever actually firing means a cache-completeness bug, and it's
surfaced as a hard error rather than silently falling through to a paid
API call.

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
  transcribing). **Scoped to tier-2 (hybrid/whole-document batch) cards
  only** (second review, point 6b): tier-2's `hint_text` is the PDF's own
  embedded text layer and is a meaningful length baseline, but tier-3's
  hint is handwriting-app text extraction that's often empty or junk, so
  the same comparison there would just be noise. Anything else that
  looked unusual but didn't match a bounce rule is also warn-only.

A bounced card is re-marked `bounced: <reason>` in the manifest; the agent
re-reads that one card, redoes it in place, and `submit` is re-run.
Nothing else in the document is touched.

### Provenance (should-fix)

`model` in frontmatter currently records the real Gemini model
(`gemini-3.1-flash-lite`, etc.) and would be false for agent-transcribed
pages. Add `driver: api | agent | mixed` and, when any pages are
agent-transcribed, `agent_name` (e.g. `antigravity`) and the list of
agent-transcribed page numbers, to the frontmatter metadata dict passed
into `build_frontmatter`. A document is `mixed` when some of its pages
were submitted via the agent driver and others via the API driver (e.g.
a bounced tier-2 batch finished with `--driver api` instead of a redo) —
`submit`'s rerun of `process_pdf` (see the guard above) must pass this
per-page provenance through from the manifest rather than assuming the
whole document used one driver (second review, point 6a). `routing`
itself is left untouched (see Non-goals) since `postprocess_discovery.py`
branches on its exact values.

Because both drivers write into the same `_pages_cache.json`, a run isn't
locked to one driver end-to-end: `--driver api` can finish any cards the
agent skipped, or vice versa, on a plain rerun of `process_pdf`.

## CLI surface

```
--driver {api, agent}     # default: api (today's behavior, unchanged)
--collect                 # with --driver agent: render + write task cards + manifest, no transcription, no client, no lock
--submit <run-id> [--doc <slug>]   # validate filled cards, write cache, re-run process_pdf to finish the write path
--bootstrap <run-id>      # print the agent's operating contract (see below)
```

`--driver agent` is a general flag on the existing
`transcribe_notes`/`route_notes_transcribe` CLI, not a microecon-specific
mode — any large `--notes-subdir` run can use it.

**`bootstrap` (second review, point 6c):** the user wants a contract to
paste directly into Antigravity, the same way `agent/tutor bootstrap`
prints one. `--bootstrap <run-id>` prints: read `worklist.md`/
`manifest.json` for this run; fill only the `## Agent output` section of
each `task-NNNN.md`, never touch any other file or section; for a
tier-3 card, carry transcribed context forward *within* the card from
page to page (only the card's first page gets real prior context from
the cache); once a card (or a batch of cards) is filled, run `submit`;
if a card comes back `bounced: <reason>`, redo only that card in place
and re-run `submit`; stop and report once the worklist shows nothing
`pending`/`filled` left for this run.

## Required before the first real run (not optional open items)

- Add a `.gitignore` rule for `ai-sandbox/academic-hub/.agent_work/`
  before any `collect` is run against real documents.
- A test confirming `.agent_work/` content is not discovered by
  `postprocess_discovery.py`, `corpus_health`, or `offering_links.py` (the
  indexer's own dot-directory skip at `index_search.py:259,283` is
  confirmed but doesn't cover these other entry points).

## Open items for the implementation plan

- Exact tier-3 agent batch size (`_AGENT_TIER3_BATCH_SIZE`): 5–8 pages,
  pick a default from real context-window behavior during implementation.
- Exact `manifest.json` schema and `task-NNNN.md` template field names.
- Whether `submit`'s auto-staging of the next tier-3 card should have a
  cap (bound work-dir size) — default to staging exactly one ahead until
  proven too slow.
- Validation-dry-run on the 7 held-back tier-3 docs (~125 pages) before
  any real agent run, to confirm card sizing, the `AgentPending` seam, and
  the cache round-trip work end to end with zero paid calls.
