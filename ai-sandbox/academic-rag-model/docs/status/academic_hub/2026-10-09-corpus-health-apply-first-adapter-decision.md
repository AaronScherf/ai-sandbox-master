# Corpus Health `apply`: first safe repair adapter — design decision

**Date:** 2026-10-09 (revised 2026-10-09 after Codex's implementation review)
**Plan:** `docs/superpowers/plans/academic_hub/2026-10-08-corpus-health-orchestrator.md`, Task 7
**Trigger:** Codex blocked on Task 7 pending an architecture decision on the first adapter.
**Scope note:** This does not reopen the 2026-10-09 deferral (`c76d94d`) of note
transcription/Excalidraw/enhancement/question-resolution/postprocessing adapters.
Those stay blocked behind `academic_notes/` sync quiescence and the source-pipeline
quality fix, unchanged.

**Revision note:** Codex reviewed the first version of this decision against the
actual `tools/corpus_health/discovery.py`/`finding.py` code before implementing it
and found five contract errors below the headline decision — all five checked out
against the code. The headline decision (chunk repair first, card reconciliation
blocked, fix atomicity) is unchanged; the "Adapter contract" and "Decision"
sections below are corrected in place. Where the original text said something the
code contradicts, it has been struck through in spirit and replaced, not left
alongside the correction.

## Question

Given the writer-lock adoption already landed (Task 6: `index rebuild`/`retag`/`chunk`,
direct note/Excalidraw/router CLIs, postprocessing, local textbook image description),
is a narrowly scoped **indexing** repair — `missing_card`/`stale_card`/`missing_chunks`/
`stale_chunks` findings from `core.indexer.audit.audit_markdown_index` — safe to be
Task 7's first enabled adapter?

## What was verified

**`missing_card` / `stale_card` → `index_search rebuild`:** `rebuild()`
(`core/indexer/index_search.py:555`) has no file-scope parameter at all — only
`--course`, `--force`, `--prune`. A single missing/stale card can only be repaired by
re-walking every notes PDF and every textbook directory in that card's course
(`_notes_pdf_paths`/`_textbook_book_dirs`), calling `_reconcile_one` for each, which
calls the Gemini client. There is no code path that reconciles exactly one file. This
confirms the plan's own existing caution ("no non-mutating preview... no apply until
scope is verified") rather than resolving it — scope does not exist today, so
`missing_card`/`stale_card` **cannot** be a precise, single-finding action with the
current public API.

**`missing_chunks` / `stale_chunks` → `index_search chunk --file`:**
`chunk()` (`core/indexer/chunk_index.py:396`) only considers cards that already have a
real embedding (`orphaned`/`needs_indexing`/no `embedding` are skipped first), so it
never touches a card `rebuild` would still need to create. Its `--file` match is:

```python
if file is not None and not card["path"].endswith(file):
    continue
```

`file` is matched with `str.endswith`, not equality and not anchored on a path
separator. Passed a bare filename (`"exam1.md"`), it also matches any other card whose
stored path happens to end the same way (`"old_exam1.md"`), silently re-chunking (and
re-embedding) the wrong file. Passed the exact stored relative path, `endswith` reduces
to an exact match in practice today — but that is an accident of how
`academic_hub_paths` currently builds `course/category/processed_outputs/<stem>/<stem>.md`
paths, not a guaranteed contract of this function. **Do not call this API with anything
except a value that is already known to equal one card's full stored `path`, and do not
treat `endswith` as a safe selector in its own right.**

`generate_chunks_for_file()` calls `client.models.embed_content` once per chunk the
target file produces — a real, bounded, per-item Gemini cost, not zero. This is
acceptable under the plan's existing "paid/API actions require an explicit
per-source decision" rule, but the review UI must show it as a paid action, not a free
one.

Writes are scoped correctly: `chunk` only ever writes `.index/chunks/<course>.json`
under the root already covered by `corpus_write_lock([root], "index chunk")`
(`core/indexer/index_search.py:936`) — it never touches Markdown, frontmatter, or
`academic_notes/`. The CLI already acquires the shared lock for the real (non-dry-run)
path, consistent with Task 6.

**Corrections from Codex's review, verified against `discovery.py`/`finding.py`/`audit.py`:**

1. **The finding has no `file_id`.** `Finding` (`tools/corpus_health/finding.py`) has
   `kind`, `root`, `path`, `fingerprint`, … — no `file_id` field, and the ledger key
   (plan Task 4) is built from `(root, scope, kind, fingerprint)`, not `file_id`.
   `discovery.py` sets `fingerprint=record.content_hash` (a content hash), and `path`
   to `record.index_path` — a card's *stored path*, not its identity key. The adapter
   must look up the live card by `index_path` (and course) itself, the same way
   `audit_markdown_index`'s internal `cards_by_path` does, and read `file_id` off
   *that* card — it is never handed one.
2. **The scanner emits one finding kind, not two.** `discovery.py:438-444` emits a
   single kind, `"index_chunks_missing_or_stale"`, whenever
   `record.chunks_status in {"missing_chunks", "stale_chunks"} and record.card_status
   != "missing_card"`. Critically, that condition does **not** also exclude
   `needs_indexing`, `course_mismatch`, `unverified_large`, `unverified_legacy`, or
   `stale_card` — `audit.py` computes `chunks_status` for *any* card that exists at
   all (`audit.py:140-152`), regardless of `card_status`. So this one finding kind can
   legitimately be reported for a card `chunk()` would itself skip
   (`needs_indexing`/no embedding — `chunk_index.py:412`) or for a card that still
   needs `rebuild` to reconcile first (`stale_card`). The adapter must re-derive
   `card_status` for the live card at apply time and require it to be exactly
   `"current"` before calling `chunk()`; any other `card_status` makes this specific
   attempt **blocked**, not failed, and not silently skipped.
3. **`finding.root` is a label, not a filesystem path.** `discovery.py` passes the
   literal string `"academic-hub-index"` as `root` for this finding kind — it is not
   the corpus's real `hub_root` directory. The adapter must resolve the real `hub_root`
   from its own orchestrator config (the same config value the scan that produced this
   finding was run with), not from the `Finding` object, and must use that same
   `hub_root` for every path join, lookup, and the eventual `chunk()` call.
4. **Stats are corpus/course-wide, not target-scoped.** `chunk()`'s returned `stats`
   dict (`chunked`/`unchanged`/`failed`/`skipped_no_embedding`) is a running total over
   every card the loop visits, not a result for one target file — even with a `course`
   filter, a card that fails for an unrelated reason or a card that is skipped for
   lacking an embedding still increments the aggregate counters. A 0 exit status plus
   an unparsed `print(stats)` (a Python dict repr, not JSON — it uses single quotes and
   is not safely machine-readable) is not sufficient evidence that the target file was
   actually (re)chunked. The exact-selector fix must also make the single-file result
   unambiguous (see Decision item 1 below), and the CLI must emit it as parseable JSON.
5. **No `blocked` ledger status exists today, and `applied`/`failed` are referenced but
   never set.** `tools/corpus_health/state.py` only transitions between
   `pending_review`/`accepted`/`declined`/`deferred`/`vanished`; `"applied"` appears
   only inside a defensive guard (`decide()`/`decide_many()` refuse to re-decide an
   already-`"applied"` entry), and nothing in the current code ever sets `applied` or
   `failed`. Task 7 must add real `mark_applied`/`mark_failed`/`mark_blocked` state
   transitions (see "Ledger status semantics" below), not assume they already exist.

**Atomicity gap (new finding, affects both `chunk` and `rebuild`):** neither
`save_chunks()` (`chunk_index.py:45`) nor `save_shard()` (`index_card.py:132`) write
atomically — both do a direct `open(path, "w")` + `json.dump`. The shared lock prevents
two writers from racing each other, but it does not protect a *single* writer from
leaving a truncated/corrupt JSON shard behind if the process is killed mid-`json.dump`
(Ctrl-C, OOM, a crashed `subprocess.run` child). `core/env/corpus_write_lock.py`'s own
`_write_owner()` already shows the pattern to copy: `tempfile.mkstemp` in the same
directory, `fsync`, then `os.replace`. This is a real residual risk for Task 7's
"post-run verification contract" (`actions.py` can detect a corrupt shard after the
fact via the audit API, but cannot recover it), independent of the lock question.

## Decision

Ship Task 7's `apply` dispatcher for **all** finding kinds now (so blocked findings get
a real, explained "blocked" status instead of silently not existing), but enable an
executing adapter in v1 only for `index_chunks_missing_or_stale`, and only after these
prerequisite fixes land in `core/indexer/chunk_index.py` and `index_search.py` (not in
the orchestrator package):

1. **Exact-match file selector, invoked through the CLI, not in-process.** Add a
   `--file-id <id>` flag to the `chunk` subcommand in `index_search.py`, separate from
   the existing `--file` (keep `--file`'s suffix-match behavior unchanged for
   interactive use — it is not safe to repurpose). Internally, `chunk()` gains a
   `file_id: str | None` parameter filtering with `card["file_id"] == file_id`,
   restricted to at most the one matching card, instead of `card["path"].endswith(file)`.
   Task 7's plan text is explicit — "Invoke module entry points with
   `subprocess.run([...])`, never shell-concatenated commands" — so the adapter calls
   `subprocess.run([sys.executable, "-m", "core.indexer.index_search", "chunk",
   "--root", root, "--course", course, "--file-id", file_id, "--json"])`, it does not
   call `chunk_index.chunk()` in-process. (The first version of this decision proposed
   an in-process call as an allowed alternative; Codex correctly flagged that against
   the plan's own explicit subprocess requirement, so the subprocess path is now the
   only path.)
2. **Structured, target-scoped output.** Add a `--json` flag (or make JSON the only
   output once `--file-id` is set) that prints a result scoped to the one requested
   file, not the aggregate corpus-wide `stats` dict — e.g.
   `{"file_id": ..., "matched": true, "chunks_written": N, "card_status": "current"}`
   with `"matched": false` when no card has that `file_id` in the given course, and a
   `"card_status"` field reporting what `audit.py` would call the card's status so the
   adapter does not have to re-derive it from a second process call. `print(stats)`
   today is a Python dict repr (single-quoted), not valid JSON — do not parse it.
3. **Atomic `save_chunks()`.** Same temp-file-plus-`os.replace` pattern already used by
   `corpus_write_lock._write_owner()`. Do the same for `save_shard()` while touching this
   code, even though `rebuild` stays unexecuted in v1 below — it is the same class of
   bug and costs nothing extra to fix now; call this out as a small separate commit so
   it doesn't block the `chunk` adapter on an unrelated rebuild change.

`missing_card`/`stale_card`-shaped problems (the orchestrator's `index_card_missing`/
`index_card_stale` finding kinds, and any `index_chunks_missing_or_stale` finding whose
live card is not exactly `"current"`) stay **blocked, with a stated reason** ("no
exact-file repair exists for index-card reconciliation yet — `rebuild` always rescans
its whole course") rather than silently absent from `apply`. Do not build a new
single-card reconcile entry point as part of Task 7; that is new product surface
(effectively a `reconcile_one_file()` sibling of `_reconcile_one`), not a mechanical
adoption of existing capability, and the plan's own bar for a first adapter is
"deterministic, low-cost actions that have precise scope and supported verification"
using what already exists. Revisit card reconciliation as a later adapter once such an
entry point is deliberately designed (its own short decision, not bundled here).

## Ledger status semantics (new in Task 7)

`state.py` today only has `pending_review`/`accepted`/`declined`/`deferred`/`vanished`.
Task 7 adds three real transitions, all driven by `apply`, never by `review`:

- **`applied`**: the adapter ran, the subprocess exited 0, `matched: true`, and a
  fresh `audit_markdown_index` call confirms `chunks_status` is no longer
  `missing_chunks`/`stale_chunks` for that card. Terminal for this finding occurrence.
- **`failed`**: the adapter attempted execution and it did not succeed — nonzero exit,
  `matched: true` but `chunks_written` didn't resolve the status on re-audit, or the
  post-run re-audit itself errors. Carries the redacted exit status/stderr. Not
  retried automatically; reappears for the user to decide again only if the next scan
  still reports the finding (its fingerprint/action-signature invalidation from Task 4
  already handles this — no new mechanism needed).
- **`blocked`**: the finding is `accepted` but the live precondition for running its
  adapter is not met right now — `card_status != "current"` for an
  `index_chunks_missing_or_stale` finding, or the finding's kind has no adapter at all
  (`index_card_missing`/`index_card_stale`, every deferred note/Excalidraw/postprocess
  kind, textbook conversion). Not a failure: no lock was taken, no subprocess ran, no
  cost was spent. Non-terminal — every `apply --accepted` run re-checks a `blocked`
  entry's live precondition first and executes it automatically (using the decision the
  user already recorded) the moment it clears, without asking the user to re-accept.
  Report the specific unmet precondition in the run output each time so a permanently
  blocked kind (card reconciliation) doesn't look like a disappearing bug.

## Adapter contract (`tools/corpus_health/actions.py`)

For an `accepted`, still-pending `index_chunks_missing_or_stale` finding:

1. Resolve `hub_root` from the orchestrator's own config (never from `finding.root`,
   which is the literal label `"academic-hub-index"` for this kind, not a filesystem
   path). Derive the course from `finding.path` (`record.index_path`) the same way
   `audit.py` does (`parts[1]` when `parts[0]` is `academic_notes`/`academic_resources`).
2. Look up the live card at `hub_root` for that `index_path`/course (same lookup
   `audit_markdown_index`'s `cards_by_path` performs) and read its `file_id` and current
   `content_hash` off of it — the finding carries neither. Require, in order, before
   taking the lock or spending anything: the card exists; its path resolves under the
   configured `hub_root` (`os.path.isfile`); its `content_hash` equals the finding's
   `fingerprint` (stale-approval rejection); its derived `card_status` is exactly
   `"current"`. Any failure here is `blocked` (precondition not met) except a
   fingerprint mismatch, which is the existing "changed source invalidates acceptance,
   return to pending review" rule from Task 4, not `blocked`.
3. Acquire `corpus_write_lock([hub_root], "corpus-health apply: index chunk")` for the
   finding's root only.
4. Run the CLI per Decision item 1, capture stdout/stderr/exit status, release the lock.
5. Parse the JSON result. `matched: false` or nonzero exit → `failed` (card vanished or
   lock/process error between steps 2 and 4 — rare, still handled, never silently
   dropped). `matched: true` → re-run `audit_markdown_index` scoped to this one card and
   require `chunks_status` is no longer `missing_chunks`/`stale_chunks`; record
   `applied` on confirmation, `failed` otherwise.
6. On any exception (including a lock failure or a crashed subprocess), record `failed`
   for this item only and continue with the next accepted finding (existing Task 7
   failure-isolation rule).

## Test criteria to add

- `chunk_index.chunk(..., file_id=...)` selects exactly one card even when a second,
  unrelated card's `path` is a string suffix of the first (regression fixture for the
  bug this replaces); `--file` (suffix match) keeps its old, unrelated behavior unchanged.
- `index_search chunk --file-id ... --json` prints `matched: false` (not an aggregate
  stats dict) when no card in the given course has that `file_id`, and
  `matched: true, chunks_written: N, card_status: ...` scoped to the one card otherwise.
- `save_chunks()`/`save_shard()`: simulate a write interrupted partway (e.g. monkeypatch
  `json.dump` to raise after partial output) and assert the on-disk file is byte-identical
  to its pre-call contents — proves the temp-file swap, not just "no exception leaked."
- `actions.py` adapter test: accepted finding whose card `content_hash` has changed since
  acceptance is rejected before any lock/subprocess call (stale-approval rejection, already
  required by Task 7's acceptance criteria — add the chunk-specific fixture).
- `actions.py` adapter test: an `index_chunks_missing_or_stale` finding whose live card
  is `needs_indexing`/`stale_card`/`course_mismatch` (not `"current"`) is recorded
  `blocked` with that specific `card_status` as the reason, and never takes the lock or
  spends a subprocess call — regression fixture for Codex's point 2 (the scanner's single
  finding kind covers states `chunk()` itself would skip or shouldn't touch yet).
- `actions.py` adapter test: an `index_card_missing`/`index_card_stale` finding reaches
  `apply` and is recorded `blocked` with the "no exact-file reconcile" reason, never
  attempted.
- `actions.py` adapter test: a `blocked` entry whose precondition has since cleared (card
  now `"current"`) is executed on the next `apply --accepted` run without re-asking the
  user — proves the non-terminal `blocked` → `applied`/`failed` transition.
- Reuse, do not duplicate, the existing lock-contention coverage in
  `tests/core/indexer/test_chunk_cli_lock.py` — Task 7's own test only needs to prove the
  adapter *acquires* the lock (e.g. via a stub that raises `CorpusWriteLockError` when a
  second holder is simulated), not re-prove the lock primitive itself.

## Summary

| Finding kind | v1 `apply` behavior | Why |
|---|---|---|
| `index_chunks_missing_or_stale` with live `card_status == "current"` | Executed, gated on the `chunk_index.py`/CLI fixes above | Exact-file-capable once selector is fixed; writes are scoped and lock-covered; cost is bounded and per-item |
| `index_chunks_missing_or_stale` with any other live `card_status` | `blocked`, re-checked every run | The scanner's finding kind doesn't imply the card is ready; `chunk()` would skip or shouldn't touch it yet |
| `index_card_missing`, `index_card_stale` | `blocked`, permanent until a new adapter exists | `rebuild` has no single-file scope; building one is new scope, not mechanical adoption |
| note/Excalidraw/enhancement/question-resolution/postprocessing | Blocked, unchanged | Per `c76d94d` (2026-10-09): source pipeline quality + `academic_notes/` sync-quiescence gate |
| textbook GPU/VM conversion | Blocked, unchanged | Per plan: no cloud/VM automation in v1 |
