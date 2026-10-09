# Corpus Health `apply`: first safe repair adapter — design decision

**Date:** 2026-10-09
**Plan:** `docs/superpowers/plans/academic_hub/2026-10-08-corpus-health-orchestrator.md`, Task 7
**Trigger:** Codex blocked on Task 7 pending an architecture decision on the first adapter.
**Scope note:** This does not reopen the 2026-10-09 deferral (`c76d94d`) of note
transcription/Excalidraw/enhancement/question-resolution/postprocessing adapters.
Those stay blocked behind `academic_notes/` sync quiescence and the source-pipeline
quality fix, unchanged.

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
executing adapter in v1 only for `missing_chunks` and `stale_chunks`, and only after two
small prerequisite fixes land in `core/indexer/chunk_index.py` (not in the orchestrator
package):

1. **Exact-match file selector.** Add a `file_id: str | None` parameter to `chunk()`
   (or a wrapper) that filters with `card["file_id"] == file_id` instead of
   `card["path"].endswith(file)`. `file_id` is already the corpus's content-identity key
   (`compute_file_id`), already present on every card, already what the orchestrator's
   finding key is built from (plan Task 4) — so the adapter has it on hand and needs no
   path-string reasoning at all. Keep the existing `--file` CLI flag for interactive use
   unchanged (it is a convenience, not something external scripts other than this
   adapter depend on); the orchestrator must call the new `file_id`-keyed path, never
   the CLI's suffix-matched flag.
2. **Atomic `save_chunks()`.** Same temp-file-plus-`os.replace` pattern already used by
   `corpus_write_lock._write_owner()`. Do the same for `save_shard()` while touching this
   code, even though `rebuild` stays unexecuted in v1 below — it is the same class of
   bug and costs nothing extra to fix now; call this out as a small separate commit so
   it doesn't block the `chunk` adapter on an unrelated rebuild change.

`missing_card` and `stale_card` stay **blocked, with a stated reason** ("no exact-file
repair exists for index-card reconciliation yet — `rebuild` always rescans its whole
course") rather than silently absent from `apply`. Do not build a new single-card
reconcile entry point as part of Task 7; that is new product surface (effectively a
`reconcile_one_file()` sibling of `_reconcile_one`), not a mechanical adoption of
existing capability, and the plan's own bar for a first adapter is "deterministic,
low-cost actions that have precise scope and supported verification" using what already
exists. Revisit `missing_card`/`stale_card` as a later adapter once such an entry point
is deliberately designed (its own short decision, not bundled here).

## Adapter contract (`tools/corpus_health/actions.py`)

For an accepted `missing_chunks`/`stale_chunks` finding:

1. Re-verify immediately before executing (plan Task 7's existing requirement): source
   `file_id`/`content_hash` from the finding matches the *current* card in
   `.index/<course>.json`; root is a configured root; action kind is still
   `missing_chunks` or `stale_chunks`.
2. Acquire `corpus_write_lock([root], "corpus-health apply: index chunk")` for the
   finding's root only.
3. Invoke the fixed-selector chunk path as an in-process call (`chunk_index.chunk`
   with the new `file_id=` kwarg), inside the held lease — not a `subprocess.run` of the
   CLI, since the CLI's own `--file` stays suffix-matched and the plan's "no
   shell-concatenated commands" rule is about avoiding shell string-building, not about
   forbidding in-process calls to an already-public, already-tested function. If Codex
   prefers process isolation for crash containment, `subprocess.run([sys.executable, "-m",
   "core.indexer.index_search", "chunk", "--course", course, "--file-id", file_id])` is
   also fine, but then the `--file-id` flag (new, exact) must be added to the CLI parser
   too — do not reuse `--file` for both semantics.
4. On success, release the lock, then call `audit_markdown_index` scoped to that one
   card and assert its status is no longer `missing_chunks`/`stale_chunks` for that
   `file_id`. Record `applied` only on that confirmation; record `failed` (with the
   captured exit status/stderr, redacted) otherwise — never leave it `accepted`.
5. On any exception (including a lock failure or a crash mid-`generate_chunks_for_file`),
   record `failed` for this item only and continue with the next accepted finding
   (existing Task 7 failure-isolation rule).

## Test criteria to add

- `chunk_index.chunk(..., file_id=...)` selects exactly one card even when a second,
  unrelated card's `path` is a string suffix of the first (regression fixture for the
  bug this replaces).
- `save_chunks()`/`save_shard()`: simulate a write interrupted partway (e.g. monkeypatch
  `json.dump` to raise after partial output) and assert the on-disk file is byte-identical
  to its pre-call contents — proves the temp-file swap, not just "no exception leaked."
- `actions.py` adapter test: accepted finding whose card `content_hash` has changed since
  acceptance is rejected before any lock/API call (stale-approval rejection, already
  required by Task 7's acceptance criteria — add the chunk-specific fixture).
- `actions.py` adapter test: a `missing_card`/`stale_card` finding reaches `apply` and is
  recorded as `blocked` with the "no exact-file reconcile" reason, never attempted.
- Reuse, do not duplicate, the existing lock-contention coverage in
  `tests/core/indexer/test_chunk_cli_lock.py` — Task 7's own test only needs to prove the
  adapter *acquires* the lock (e.g. via a stub that raises `CorpusWriteLockError` when a
  second holder is simulated), not re-prove the lock primitive itself.

## Summary

| Finding kind | v1 `apply` behavior | Why |
|---|---|---|
| `missing_chunks`, `stale_chunks` | Executed, gated on the two `chunk_index.py` fixes above | Exact-file-capable once selector is fixed; writes are scoped and lock-covered; cost is bounded and per-item |
| `missing_card`, `stale_card` | Blocked, with reason surfaced in the finding | `rebuild` has no single-file scope; building one is new scope, not mechanical adoption |
| note/Excalidraw/enhancement/question-resolution/postprocessing | Blocked, unchanged | Per `c76d94d` (2026-10-09): source pipeline quality + `academic_notes/` sync-quiescence gate |
| textbook GPU/VM conversion | Blocked, unchanged | Per plan: no cloud/VM automation in v1 |
