# VM RAM-Sizing Logging (Phase 1) — Design

## Context

The textbook conversion pipeline (`ai-sandbox/academic-rag-model`) currently
runs every batch on a single, fixed machine type (`g2-standard-4`, ~15GB
system RAM, one NVIDIA L4 GPU — see `convert_textbook_instructions.md` Step
1.3). On 2026-09-19 a real batch hit a confirmed Linux kernel OOM-kill
(`dmesg` showed the kernel killing the vLLM inference engine process)
converting a dense, image/table-heavy book. A same-session fix already makes
a recurrence self-diagnosing and safe — `start_conversion.sh`'s
`run_conversion_with_retries` watchdog auto-restarts a dead inference
server, and `convert_textbook.py`'s `chunk_is_degraded` check refuses to
checkpoint a degraded chunk as done — but neither prevents the OOM itself
or right-sizes the VM in advance.

The user's proposal: predict a book's RAM footprint from its size before
provisioning a VM, and split a batch across VM tiers (a large-RAM machine
for the few books that need it, a smaller/cheaper one for the rest) rather
than running the whole batch on one fixed size.

**This spec covers Phase 1 only: observability.** There is exactly one
real OOM data point so far, with no confirmed counterexample (no known
big-but-sparse book that was fine, no known small-but-dense book that
OOM'd) — not enough to trust an automatic sizing decision. Phase 1 adds
RAM-usage logging correlated with book size, with zero behavior change to
provisioning. **Phase 2 (predictive multi-tier VM provisioning) is
explicitly out of scope for this spec** and gets its own brainstorm once
enough real data exists in the log this phase produces.

## Goals

- Capture actual peak system RAM used while converting each book, alongside
  cheap, already-available signals about that book (page count, file size).
- Persist this as a small, structured, git-tracked dataset that accumulates
  across every future batch run, so a future Phase 2 design has real data
  to size VM tiers from.
- Zero risk to the core conversion pipeline: the CUDA-timing-sensitive
  `convert_textbook.py` process gets the smallest possible change (two
  plain print statements, no new dependency, no new thread).

## Non-goals

- No automatic VM tier selection or multi-VM batch splitting (Phase 2).
- No backfill of RAM data for books already converted before this ships —
  those runs were never sampled and can't be reconstructed.
- No per-process (vLLM vs. ocr_error.server vs. python) memory attribution
  — only whole-system `free -m` numbers, matching how the Linux OOM-killer
  itself decides (system-wide pressure, not one process's own footprint).

## Architecture / data flow

```
VM (during a batch run)                    Local repo (after the batch)
------------------------                   ---------------------------
start_conversion.sh:                        docs/status/vm_sizing_raw/
  RAM sampler (background loop)  ---scp-->    <run>/convert_log.txt
    -> ~/ram_sampling_log.txt                 <run>/ram_sampling_log.txt
                                                        |
convert_textbook.py:                                   v
  RAM_SIZING_START/END lines     ---scp-->    textbook/vm_sizing_log.py
    -> ~/convert_log.txt                       (parse, window, correlate)
                                                        |
                                                        v
                                              docs/status/vm_sizing_log.jsonl
                                              (git-tracked, append-only)
```

Raw per-run logs are downloaded but **not** committed (git-ignored) — they
are debugging exhaust for one run. Only the small correlated summary is a
long-term asset.

## Component 1: RAM sampler in `start_conversion.sh`

A background shell loop, started once per `start_conversion.sh` invocation
(spanning every retry attempt inside `run_conversion_with_retries`, not
restarted per attempt), sampling every 15 seconds:

```bash
(
  while true; do
    echo "$(date +%s) $(free -m | awk '/^Mem:/{print $2, $3, $4, $6, $7}')"
    sleep 15
  done
) >> ~/ram_sampling_log.txt &
RAM_SAMPLER_PID=$!
```

Each line: `<unix_ts> <total_mb> <used_mb> <free_mb> <buff_cache_mb> <available_mb>`
(the five numeric fields of `free -m`'s `Mem:` row, in that column order).

The sampler is killed (`kill "$RAM_SAMPLER_PID" 2>/dev/null || true`) after
`run_conversion_with_retries` returns, success or failure, so it never
outlives the tmux session.

`~/ram_sampling_log.txt` is truncated at the start of `start_conversion.sh`
(same `: > ...` pattern already used for `~/convert_log.txt`), so a fresh
launch never mixes samples from an unrelated earlier batch.

## Component 2: structured markers in `convert_textbook.py`

Two plain `print()` lines, no new logic, added to `process_one_pdf`:

- Right after `total_pages` and `file_size_bytes` are known (near the
  existing `"Loaded document mapping: {total_pages} total pages."` line):
  ```
  RAM_SIZING_START book=<sanitized_input_key> pages=<total_pages> file_size_bytes=<n> ts=<unix_ts>
  ```
- Immediately before `process_one_pdf` returns on success, and in a
  `finally`/`except` path on failure, so a crash still emits an END line
  distinguishing "finished" from "died mid-book":
  ```
  RAM_SIZING_END book=<sanitized_input_key> ts=<unix_ts> status=success|failed
  ```

`book` uses the same `sanitize_filename(...)` value already computed as
`input_key` elsewhere in `process_one_pdf` — no new naming scheme.

These lines flow into the existing `convert_log.txt` (already captured via
`tee -a` in the watchdog) — tagged with a fixed prefix so they're
unambiguous and trivially `grep`-able, but otherwise invisible noise to a
human reading the log normally.

## Component 3: download step

A new step added to both instructions docs, run **before** Step 4 (VM
deletion), alongside the existing `processed_outputs` download:

```bash
RUN_DIR="docs/status/vm_sizing_raw/${TEXTBOOK_SUBDIR//\//_}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN_DIR"
gcloud compute scp "$VM_INSTANCE_NAME:~/convert_log.txt" "$VM_INSTANCE_NAME:~/ram_sampling_log.txt" \
  "$RUN_DIR/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
python -m textbook.vm_sizing_log \
  --convert-log "$RUN_DIR/convert_log.txt" \
  --ram-log "$RUN_DIR/ram_sampling_log.txt" \
  --course "$COURSE_NAME" --machine-type "$MACHINE_TYPE" \
  --output docs/status/vm_sizing_log.jsonl
```

`docs/status/vm_sizing_raw/` is added to `.gitignore`. This step is
best-effort: if either scp fails (e.g. the VM already looks unhealthy), log
a warning and continue to the existing download/cleanup steps rather than
blocking the batch's completion on it — this is an observability nice-to-
have, not a correctness requirement.

## Component 4: `textbook/vm_sizing_log.py`

New module, CLI entry point via `python -m textbook.vm_sizing_log`.

**Inputs:** `--convert-log PATH`, `--ram-log PATH`, `--course NAME`,
`--machine-type NAME`, `--output PATH` (defaults to
`docs/status/vm_sizing_log.jsonl`).

**Parsing:**
- `parse_ram_samples(ram_log_text) -> list[RamSample]`: one entry per line,
  `(ts: int, total_mb: int, used_mb: int, free_mb: int, buff_cache_mb: int,
  available_mb: int)`. Malformed lines are skipped, not fatal.
- `parse_book_windows(convert_log_text) -> list[BookWindow]`: matches
  `RAM_SIZING_START`/`RAM_SIZING_END` lines by `book` name. A `START` with
  no matching `END` produces a window with `end_ts=None` and
  `status="incomplete"`.

**Correlation:** `peak_ram_used_mb(samples, start_ts, end_ts) -> int | None`
— the max `used_mb` among samples with `start_ts <= ts <= end_ts` (or
`start_ts <= ts <= last_sample_ts` when `end_ts` is `None`, i.e. an
incomplete book: this window is deliberately the *most* informative row,
capturing the highest RAM point right before a real failure). Returns
`None` if no samples fall in the window (logged as a warning, row still
written with `peak_ram_used_mb: null`).

**Output:** one JSON object appended per book to the `--output` JSONL file:
```json
{"course": "microecon", "book": "Ok_Real_Analysis_with_Economic_Applications_2026",
 "pages": 382, "file_size_bytes": 41231000, "peak_ram_used_mb": 13102,
 "status": "success", "machine_type": "g2-standard-4",
 "start_ts": 1234567890, "end_ts": 1234571490}
```

**Idempotency:** before appending, existing rows in `--output` are read and
any `(book, start_ts)` pair already present is skipped — rerunning the
script against the same pair of raw logs is always safe.

## Error handling

- Missing/unreadable `--convert-log` or `--ram-log`: fail loudly (matches
  the pipeline's existing "fail loudly, not silently" convention) — this
  is an offline analysis step run by a human/agent, not unattended VM code,
  so a clear error and non-zero exit is correct, no silent skip.
- A book window with zero matching RAM samples: warn and still write the
  row with `peak_ram_used_mb: null` — a book existing in the record with an
  unknown peak is more useful than the book silently vanishing from the
  dataset.
- The download+analyze step itself (Component 3) is best-effort per above,
  since it must never block or endanger the real conversion batch's own
  completion/cleanup sequence.

## Testing

- `tests/test_vm_sizing_log.py`: full TDD unit coverage for
  `parse_ram_samples`, `parse_book_windows` (including the no-`END`/
  incomplete case), `peak_ram_used_mb` (including the zero-samples-in-
  window case), the JSONL append/dedup logic, and the CLI's argument
  wiring — following this repo's existing test conventions (see
  `tests/test_duplicate_check.py`, `tests/test_convert_textbook.py`).
- The shell-side sampler loop and the two new `convert_textbook.py` print
  lines are thin enough to verify by direct smoke test (stubbed `free`/
  `date`, matching how `run_conversion_with_retries` was smoke-tested
  live in the prior session), not a formal pytest suite.

## Documentation updates

Both `convert_textbook_instructions.md` and
`convert_textbook_agent_instructions.md` get:
- The new download+analyze step (Component 3), placed immediately before
  Step 4 (VM deletion).
- A short note on what `docs/status/vm_sizing_log.jsonl` is for and that
  it's expected to grow across future batches, feeding a not-yet-designed
  Phase 2.

## Open items for Phase 2 (explicitly deferred, not designed here)

- What signal(s) actually predict peak RAM best (page count alone? file
  size? some cheap density proxy?) — answerable only once
  `vm_sizing_log.jsonl` has enough rows to check correlation.
- How many machine-type tiers to offer and where to draw thresholds.
- Whether/how to split a single subdirectory's batch across sequential
  VMs by predicted tier, and how that interacts with the existing
  main-batch/Bonus-subfolder splitting.
