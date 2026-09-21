# Pipeline Autonomy Policies — Design

## Context

Two existing pieces of the textbook conversion pipeline require a human to
resolve every ambiguous or cost-relevant decision, every run:

- Cross-course duplicate detection (`indexer/duplicate_check.py`, see
  `docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md`)
  never auto-skips a Tier 2 (fuzzy) match, regardless of score.
- VM RAM-sizing logging Phase 1 (see
  `docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md`) is
  pure observability — the pipeline still asks a human before creating the
  VM (cost sanity check) and again if a book OOM-kills twice (possible
  machine-type resize).

Both are deliberately conservative today, for good reasons documented in
their own specs. But they block the goal this spec and its sibling
(`docs/superpowers/specs/2026-09-20-textbook-conversion-skill-design.md`)
are working toward: a single-prompt, largely-unattended conversion run,
where a human is asked only for genuine architectural decisions.

This spec defines the decision policies an autonomous driver (the skill
in the sibling spec, or a human following the agent-instructions doc
directly) uses to resolve these without blocking on every run — deliberately
biased toward **acting, then confirming after**, not asking before acting,
because:
- A wrong duplicate *skip* costs one book, fixed by one later rerun once
  noticed — cheap and localized.
- A wrong duplicate *conversion* (missing a real duplicate) costs real GPU
  VM time for a redundant conversion — the more expensive mistake to make
  routinely, so the policy below is biased against it.
- A resize triggered by a false/borderline OOM is bounded and reversible
  (a modest amount of extra Spot L4 time), not worth blocking a whole run
  over.

## Goals

- Auto-resolve high-confidence Tier 2 duplicate matches immediately (skip
  + copy + clone), queued for a lightweight post-hoc human confirmation
  instead of blocking before the batch even starts.
- Preserve a hard stop only for the genuinely ambiguous confidence band,
  where the existing test suite already documents a concrete
  false-positive risk (Mas-Colell's *Microeconomic Theory* vs.
  Rubinstein's *Lecture Notes in Microeconomic Theory* — title overlap
  alone clears the surfacing threshold despite being different books).
- Give a clean, safe recovery path when a post-hoc confirmation reveals a
  wrong auto-skip.
- Replace the single "second OOM" stop point with a bounded, self-verifying
  escalation ladder, and turn every escalation into real data for the
  still-empty `vm_sizing_log.jsonl` dataset instead of a one-off decision
  with no lasting value.
- Reduce the cost impact of any OOM-driven resize by ordering a batch so
  its largest (highest-risk) book converts last, since a resize changes
  the machine type for the rest of that batch, not just the offending book.
- Extend the existing RAM-sizing markers with cumulative counters so a
  future analysis can test whether OOM risk is driven by a book's own
  size, cumulative batch volume, or both — instead of guessing. (A
  cumulative-pressure mechanism is already *confirmed* for GPU VRAM within
  a batch — see `textbook/convert_textbook.py` lines ~991-997 — but
  unconfirmed for system RAM, which is the resource the one real OOM-kill
  actually exhausted.)
- Replace the pre-VM-creation cost sanity check's blocking prompt with an
  automatic proceed + logged estimate, escalating only when a batch is
  unprecedented relative to history.

## Non-goals

- No predictive multi-tier VM provisioning — still Phase 2 of the
  RAM-sizing spec, still deferred. This spec's OOM ladder is reactive
  (respond to a real OOM), not predictive (choose machine type upfront
  from a model).
- No concurrent multi-VM batch splitting. A book that needs a bigger
  machine still runs the rest of that same batch on the resized instance,
  not a separate VM — the existing one-VM-per-batch architecture
  (`convert_textbook.py`'s `main()` loads vision models once and reuses
  them across every book in `args.inputs`) is unchanged by this spec.
- No change to Tier 1 (exact byte-hash) duplicate handling — already fully
  automatic today, already correct.
- No change to the nested-subfolder-inclusion gate — this remains a
  genuine ask-the-user decision, designed in the sibling skill spec, not
  here.
- No design for *how* these policies get invoked end-to-end (single-prompt
  skill, orchestrator script) — that's the sibling spec. This spec is the
  decision logic only, usable by a human following the existing
  agent-instructions doc directly if the skill doesn't exist yet.

## Component 1: Duplicate auto-resolution policy (`indexer/duplicate_check.py`)

### 1a. Two-tier confidence policy

- **score >= `AUTO_SKIP_THRESHOLD`** (proposed `0.85` — an initial
  judgment call, not derived from data; revisit once real runs provide a
  distribution to tune against): auto-resolve as "yes" using the existing
  `copy_duplicate_artifacts` mechanics (same as today's Tier 1 flow), but
  the cloned card gets a new field `duplicate_pending_confirmation: true`.
  No prompt, no blocking.
- **`SURFACE_THRESHOLD` (0.6) <= score < `AUTO_SKIP_THRESHOLD`**: unchanged
  from today's Tier 2 behavior — surfaces via the existing
  "Needs confirmation" report section, requires an explicit human decision
  before that book proceeds. This is deliberately where the
  Mas-Colell/Rubinstein-style false-positive risk concentrates, so it
  keeps the existing "never auto-skip" guarantee.
- **score < `SURFACE_THRESHOLD`**: not a candidate at all (unchanged).

### 1b. Pending-confirmation store

New functions in `indexer/duplicate_check.py`, mirroring the existing
dismissal store's shape and conventions:

- `_pending_confirmation_path(academic_hub_root) -> str` →
  `<academic_hub_root>/.index/duplicate_pending_confirmation.json`
- `load_pending_confirmations(academic_hub_root) -> list[dict]`
- `save_pending_confirmations(academic_hub_root, entries) -> None`
- `record_pending_confirmation(academic_hub_root, entry: dict) -> None`

Entry shape:
```json
{"incoming_file_id": "...", "pdf_filename": "Ok.pdf", "course": "microecon",
 "matched_course": "econometrics", "matched_file_id": "...",
 "matched_title": "Real Analysis with Economic Applications",
 "score": 0.91, "new_card_file_id": "...", "queued_at": "2026-09-20T..."}
```

### 1c. Reporting

- `run_duplicate_check`'s return dict gains a new key,
  `"auto_skipped_pending_confirmation": list[dict]`, populated whenever
  1a's high-confidence branch fires.
- `_print_report` gains a new section: `"Auto-skipped as likely duplicate
  -- please confirm (N)"`, listing pdf filename, matched course/title,
  and score.
- New CLI mode: `python -m indexer.duplicate_check --review-pending
  [--academic-hub-root ...]` — lists every pending entry across **all**
  courses (not scoped to one `--textbook-subdir`, unlike the normal run
  mode), so it can be checked independent of any particular course's next
  batch.
- New CLI flags to resolve one entry:
  `--confirm-pending FILE_ID` (removes the pending entry, no further
  action — the clone stands as correct) and
  `--reject-pending FILE_ID` (triggers 1d's recovery).

### 1d. Recovery when rejected

New function `reject_pending_confirmation(academic_hub_root,
incoming_file_id) -> None`:

1. Look up the pending entry by `incoming_file_id`.
2. Remove the cloned card (`new_card_file_id`) from its course's shard;
   call `recompute_course_entry` for that course.
3. Delete the copied `processed_outputs/<BookDir>/` folder that was
   created for that clone.
4. Call `record_dismissal(academic_hub_root, incoming_file_id,
   matched_file_id)` — so this pair is never proposed again, matching the
   existing "never re-surfaced" dismissal guarantee.
5. Remove the entry from the pending-confirmation store.
6. The original PDF was never touched (existing convention: a resolved
   duplicate's source PDF deliberately stays in place) — it naturally
   reappears in "to convert" the next time `duplicate_check` runs against
   that course, and gets a real conversion.

### 1e. Invocation-time surfacing

Whatever drives this pipeline (skill or human) should check
`--review-pending` at the **start** of every run, before touching
anything new, and surface any outstanding items — so pending
confirmations don't silently accumulate unreviewed across many runs.

## Component 2: OOM/cost escalation ladder

### 2a. Pre-VM-creation cost check

Replace the blocking "ask user to confirm" step
(`convert_textbook_agent_instructions.md` Step 1.3) with: compute the same
PDF-count/total-size estimate as today, print it, proceed automatically.
Escalate (stop and ask) only if the estimate exceeds a fixed, conservative
cap — initial cap is a judgment call pending real history (e.g. total size
or book count well beyond any batch in the pipeline's documented worked
examples); this loosens once `vm_sizing_log.jsonl` has enough rows to
define "unprecedented" empirically instead of arbitrarily.

### 2b. Batch ordering by size

Before Step 3.2 (upload), sort `PDF_FILENAMES` **ascending by file size**
(the cheapest available proxy signal — a plain `stat`, no PDF parsing
needed; page count is the other available signal but requires opening the
file, and it isn't yet known which one better predicts RAM risk — see
Component 2d).

Rationale: a resize event changes the machine type for the **rest of the
batch**, not just the offending book (one VM, one continuous process — see
Non-goals). Putting the largest/highest-risk book last means that if a
resize does trigger, there's little or nothing left in the batch to run
unnecessarily on the more expensive machine type.

### 2c. Escalation ladder (replaces the single "second OOM" stop point)

1. **1st confirmed OOM-kill on a book:** fully automatic —
   `gcloud compute instances reset`, wait, relaunch on the same machine
   type. This promotes today's documented "manual recovery" steps
   (Debugging appendix) into the orchestrator itself. No report needed
   beyond the log line.
2. **2nd confirmed OOM-kill on the same book:** automatic resize
   (`gcloud compute instances stop` → `set-machine-type g2-standard-8` →
   `start`) and relaunch. **Flagged in real time** — a note the moment it
   happens, not a blocking prompt and not only in the end-of-run summary —
   specifically so a *pattern* of frequent resizes across many separate
   runs stays visible (if `g2-standard-4` turns out to be the wrong
   default, this is the signal that would show it, without needing to dig
   through historical reports after the fact). Self-check: after relaunch,
   confirm the book completes without `chunk_is_degraded` firing again;
   if it completes cleanly, write the outcome (book, pages, file size,
   pre/post machine type) into `vm_sizing_log.jsonl` as a real data point
   — every escalation becomes evidence for the still-empty Phase 2
   dataset, not just a one-off decision.
3. **3rd confirmed OOM-kill on the same book** (i.e., it recurs even on
   the bigger machine): genuine stop-and-ask. Two different machine sizes
   both failing on the same book is outside anything this pipeline has
   seen, and is a real signal something other than "needed more RAM" is
   going on.

### 2d. RAM_SIZING_START marker extension

Add two fields to the existing marker
(`textbook/convert_textbook.py`), keeping the "smallest possible change"
discipline the original Phase 1 spec used:

```
RAM_SIZING_START book=<name> pages=<n> file_size_bytes=<n> cumulative_pages_so_far=<n> cumulative_file_size_bytes_so_far=<n> ts=<unix_ts>
```

`cumulative_*` = sum of `pages`/`file_size_bytes` over every book already
started in this same batch invocation (including the current one),
tracked via two module-level counters incremented at each
`RAM_SIZING_START`. This lets a future analysis test whether peak RAM
correlates better with a book's own size or with how much volume has
already run through the same warm inference server this session — the
GPU-VRAM equivalent of this is already confirmed (see Goals); this is the
data needed to check whether system RAM behaves the same way, instead of
assuming it does.

`textbook/vm_sizing_log.py`'s `parse_book_windows`/`build_rows` need the
matching two new fields added to their output rows (additive — existing
fields/behavior unchanged).

### 2e. End-of-run cost reconciliation

The pipeline's final report includes actual VM wall-clock time and an
approximate cost figure (machine-hour rate × hours, Spot pricing) next to
the pre-run estimate from 2a — closing the loop on whether the estimate
was any good, without it ever having blocked the run.

## Error handling

- Same "fail toward converting, never toward silently skipping" rule as
  the original duplicate-detection spec: any error scoring/evaluating a
  Tier 2 candidate results in treating it as no-match, same as today —
  this spec's auto-skip only ever fires on a *successfully computed*
  high-confidence score, never as a side effect of an error path.
- A resize command failing (e.g. `set-machine-type` rejected) is not a
  new failure mode this spec introduces error handling for beyond what
  Step 2.1's existing scope-fix flow already does (stop/reconfigure/start,
  same mechanism) — an unhandled failure here should surface exactly as
  loudly as any other unhandled `gcloud` failure in this pipeline today.

## Testing

- `indexer/duplicate_check.py`: new tests for the pending-confirmation
  store (mirroring the existing `TestDismissals`), the two-tier threshold
  branch in `run_duplicate_check`, `--review-pending` /
  `--confirm-pending` / `--reject-pending` CLI wiring, and the full
  reject-recovery flow (clone card removed, dismissal recorded, original
  PDF re-appears in `to_convert` on a second run).
- `textbook/vm_sizing_log.py`: `parse_book_windows` and `build_rows` tests
  extended for the two new marker fields, including a pre-existing-log
  (no cumulative fields) backward-compatibility case.
- `start_conversion.sh`: extend the existing stubbed
  `free`/`date`/`python3` smoke-test pattern to cover the 3-rung
  escalation state machine's *logic* (which rung fires when, given a
  sequence of simulated OOM exit codes) as far as that's scriptable
  without a real VM.
- No unit test can safely exercise a real
  `gcloud compute instances stop`/`set-machine-type`/`start` sequence —
  that path is a real-run verification item, consistent with how the rest
  of this pipeline's GCP-touching code has always been verified (see the
  `2026-09-10-textbook-conversion-status.md` real-run debugging history).

## Documentation updates

- `convert_textbook_agent_instructions.md`: the "When to stop and ask"
  list's cost-check, Tier 2, and OOM entries get replaced with references
  to this spec's policies (nested-subfolder inclusion remains listed
  as-is — out of scope here).
- `convert_textbook_instructions.md` (human-interactive doc): unchanged.
  These policies are specifically for the more-automated path; a human
  running the pipeline manually keeps the existing blocking prompts,
  which cost them nothing they haven't already accepted.

## Open items deferred to the future

- Whether cumulative volume or a book's own size (or some combination)
  actually predicts OOM risk — answerable only once Component 2d's data
  accumulates across several real batches.
- The exact `AUTO_SKIP_THRESHOLD` (0.85 proposed) and the "unprecedented
  batch size" cap in 2a are both initial judgment calls, not derived from
  data — revisit once real runs provide a baseline.
- Predictive (Phase 2) VM sizing and true multi-VM batch splitting remain
  out of scope, as in the original RAM-sizing spec.
