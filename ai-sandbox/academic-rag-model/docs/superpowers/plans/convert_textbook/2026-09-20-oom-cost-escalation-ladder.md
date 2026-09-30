# OOM/Cost Escalation Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the pipeline's blocking cost-check and single-OOM-stop-point with an automatic-by-default cost check, a batch ordered to minimize the cost of any resize, and a bounded 3-rung OOM escalation ladder that only asks a human when it's genuinely warranted.

**Architecture:** Two real code changes (the `RAM_SIZING_START` marker gains cumulative counters in `textbook/convert_textbook.py`, and `textbook/vm_sizing_log.py` learns to parse them) plus four documentation rewrites in `convert_textbook_agent_instructions.md` — that document *is* the executable procedure at this stage (no orchestrator script exists yet; that's the sibling skill spec's future job), so replacing its "stop and ask" language with the new policy is the actual deliverable for those components, the same way this pipeline's earlier features (duplicate detection, RAM-sizing Phase 1) shipped their procedural steps as documentation.

**Tech Stack:** Python 3 stdlib only for the two code tasks (`unittest`, matching `tests/test_convert_textbook.py`/`tests/test_vm_sizing_log.py`'s existing conventions); Markdown/bash for the documentation tasks, verified by code-fence balance rather than an automated test (consistent with how this pipeline's prior doc-only changes were verified).

**Spec:** `docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`, Component 2.

## Global Constraints

- `cumulative_pages_so_far`/`cumulative_file_size_bytes_so_far` are appended **after** `ts=` in the `RAM_SIZING_START` line, not inserted earlier — this keeps the existing `file_size_bytes=(?P<file_size_bytes>\d+) ts=(?P<ts>\d+)` regex sequence intact and makes a pre-existing log (without these fields) a simple "optional trailing groups absent" case, not a reordering.
- No new dependency, no new thread, no change to the CUDA-timing-sensitive parts of `convert_textbook.py` beyond the existing two-print-statement discipline the original RAM-sizing spec established.
- This plan touches `convert_textbook_agent_instructions.md` only — per the sibling spec's own Documentation Updates section, `convert_textbook_instructions.md` (the fully manual, human-interactive doc) is explicitly unchanged; these policies are for the automated path only.
- This plan's documentation task also finalizes the "When to stop and ask" list's Tier 2 entry (item 3), even though Tier 2 auto-resolution itself is the sibling duplicate-auto-resolution plan's concern — that plan intentionally scoped itself to `indexer/duplicate_check.py` only and does not touch this shared doc section, so whichever plan reaches it last (this one) rewrites the full list in one pass rather than splitting one coherent numbered list across two plans' edits.
- VM deletion (the list's current item 4) is **not** touched by this plan — that decision belongs to the sibling textbook-conversion-skill spec's orchestrator, not this one, and remains a stop-and-ask point until that plan exists.
- No orchestrator script is created by this plan. The 3-rung ladder, the dmesg-confirmation requirement, and the auto-proceed cost check are documented here as the procedure a human or agent follows directly, matching how this pipeline's agent-instructions doc already works today.

---

### Task 1: `RAM_SIZING_START` marker gains cumulative counters

**Files:**
- Modify: `textbook/convert_textbook.py` (module-level area near line 38, and the `RAM_SIZING_START` print at lines 890-896)
- Test: `tests/test_convert_textbook.py` (extend the existing `TestProcessOnePdfEmitsRamSizingMarkers` class)

**Interfaces:**
- Consumes: nothing new.
- Produces: two new module-level counters, `_cumulative_pages_this_batch` and `_cumulative_file_size_bytes_this_batch` (both start at 0, persist across every `process_one_pdf` call within one `python -m textbook.convert_textbook` invocation — i.e., for the whole batch, not reset per book). The `RAM_SIZING_START` line gains two new trailing fields consuming these values.

- [ ] **Step 1: Write the failing test**

Add this method to `TestProcessOnePdfEmitsRamSizingMarkers` in `tests/test_convert_textbook.py`, right after `test_emits_start_marker_with_pages_and_file_size`:

```python
    def test_ram_sizing_start_marker_includes_cumulative_totals_across_books(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf_a, output_dir, reader, args = self._setup(tmp)
            input_pdf_b = os.path.join(tmp, "second_book.pdf")
            with open(input_pdf_b, "wb") as f:
                f.write(b"a second fake pdf, different size from the first one")
            size_a = os.path.getsize(input_pdf_a)
            size_b = os.path.getsize(input_pdf_b)

            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", side_effect=RuntimeError("reached boundaries, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf_a, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf_b, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            lines = [l for l in captured.getvalue().splitlines() if l.startswith("RAM_SIZING_START")]
            self.assertEqual(len(lines), 2)

            # First book: cumulative totals equal that book's own totals.
            self.assertIn(f"cumulative_pages_so_far=4", lines[0])
            self.assertIn(f"cumulative_file_size_bytes_so_far={size_a}", lines[0])

            # Second book: cumulative totals include both books.
            self.assertIn(f"cumulative_pages_so_far=8", lines[1])
            self.assertIn(f"cumulative_file_size_bytes_so_far={size_a + size_b}", lines[1])

            # New fields come AFTER ts=, not before it -- confirms the
            # existing field order/regex sequence wasn't disturbed.
            self.assertRegex(lines[0], r"file_size_bytes=\d+ ts=\d+ cumulative_pages_so_far=")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py::TestProcessOnePdfEmitsRamSizingMarkers::test_ram_sizing_start_marker_includes_cumulative_totals_across_books -v`
Expected: FAIL — the cumulative fields don't exist in the printed line yet.

- [ ] **Step 3: Implement**

In `textbook/convert_textbook.py`, find:

```python
os.environ.setdefault("SURYA_INFERENCE_KEEP_ALIVE", "1")

import argparse
```

Change to:

```python
os.environ.setdefault("SURYA_INFERENCE_KEEP_ALIVE", "1")

# Running totals across the whole batch invocation (not reset per book) --
# feeds RAM_SIZING_START's cumulative_* fields, see
# docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
# Component 2d. Module-level rather than a function parameter because
# main()'s per-book loop calls process_one_pdf() once per book with no
# other channel for a running total to flow through.
_cumulative_pages_this_batch = 0
_cumulative_file_size_bytes_this_batch = 0

import argparse
```

Then find:

```python
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        print(f"Loaded document mapping: {total_pages} total pages.")
        # Tagged, machine-parseable line for textbook/vm_sizing_log.py --
        # see docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md.
        # Exact field order/spacing matters: it's matched by regex there.
        print(f"RAM_SIZING_START book={input_key} pages={total_pages} "
              f"file_size_bytes={os.path.getsize(input_pdf)} ts={int(time.time())}")
        ram_sizing_started = True
```

Change to:

```python
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        print(f"Loaded document mapping: {total_pages} total pages.")
        # Tagged, machine-parseable line for textbook/vm_sizing_log.py --
        # see docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md
        # and docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
        # Component 2d. Exact field order/spacing matters: it's matched by
        # regex there -- cumulative_* fields are appended AFTER ts=, not
        # inserted earlier, so a pre-existing log without them still
        # parses its other fields unchanged.
        global _cumulative_pages_this_batch, _cumulative_file_size_bytes_this_batch
        file_size_bytes = os.path.getsize(input_pdf)
        _cumulative_pages_this_batch += total_pages
        _cumulative_file_size_bytes_this_batch += file_size_bytes
        print(f"RAM_SIZING_START book={input_key} pages={total_pages} "
              f"file_size_bytes={file_size_bytes} ts={int(time.time())} "
              f"cumulative_pages_so_far={_cumulative_pages_this_batch} "
              f"cumulative_file_size_bytes_so_far={_cumulative_file_size_bytes_this_batch}")
        ram_sizing_started = True
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py::TestProcessOnePdfEmitsRamSizingMarkers -v`
Expected: PASS (the new test and every pre-existing test in the class).

- [ ] **Step 5: Run the full `test_convert_textbook.py` suite**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py -v`
Expected: PASS — confirms the module-level globals don't disturb any other test (each test module import shares the same globals across tests in one pytest session; if this surfaces cross-test leakage, reset both counters to 0 at the top of `test_ram_sizing_start_marker_includes_cumulative_totals_across_books` before use — check this if any *other* test in the file that also calls `process_one_pdf` and inspects `RAM_SIZING_START` output starts failing intermittently based on test order, and fix by resetting the two globals explicitly in that test's own setup rather than assuming a clean slate).

- [ ] **Step 6: Commit**

```bash
git add textbook/convert_textbook.py tests/test_convert_textbook.py
git commit -m "feat(textbook): add cumulative pages/size totals to RAM_SIZING_START

Second half of docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
Component 2d -- lets a future analysis test whether OOM risk correlates
with a book's own size or with cumulative batch volume.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `vm_sizing_log.py` parses the new cumulative fields

**Files:**
- Modify: `textbook/vm_sizing_log.py` (`_RAM_SIZING_START_RE`, `parse_book_windows`, `build_rows`)
- Test: `tests/test_vm_sizing_log.py` (extend `TestParseBookWindows` and `TestBuildRows`)

**Interfaces:**
- Consumes: the extended `RAM_SIZING_START` line format from Task 1.
- Produces: `parse_book_windows`'s returned dicts gain two new keys, `cumulative_pages_so_far` and `cumulative_file_size_bytes_so_far` (both `int | None` — `None` when parsing a pre-existing log line that predates this field). `build_rows`'s output rows gain the same two keys, passed through unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_vm_sizing_log.py`'s `TestParseBookWindows` class, right after `test_matches_start_and_end_by_book_name`:

```python
    def test_parses_cumulative_fields_when_present(self):
        text = (
            "RAM_SIZING_START book=Ok_Real_Analysis_2007 pages=382 file_size_bytes=41231000 "
            "ts=1000 cumulative_pages_so_far=382 cumulative_file_size_bytes_so_far=41231000\n"
            "RAM_SIZING_END book=Ok_Real_Analysis_2007 ts=1500 status=success\n"
        )
        windows = parse_book_windows(text)
        self.assertEqual(windows[0]["cumulative_pages_so_far"], 382)
        self.assertEqual(windows[0]["cumulative_file_size_bytes_so_far"], 41231000)

    def test_cumulative_fields_are_none_for_a_pre_existing_log_without_them(self):
        # Backward compatibility: a log from before this extension shipped
        # has no cumulative_* fields at all -- must still parse the fields
        # it does have, with the new ones defaulting to None, not raising.
        text = (
            "RAM_SIZING_START book=OldBook pages=100 file_size_bytes=5000 ts=1000\n"
            "RAM_SIZING_END book=OldBook ts=1100 status=success\n"
        )
        windows = parse_book_windows(text)
        self.assertEqual(windows[0]["pages"], 100)
        self.assertIsNone(windows[0]["cumulative_pages_so_far"])
        self.assertIsNone(windows[0]["cumulative_file_size_bytes_so_far"])
```

Add to `TestBuildRows`, right after `test_combines_windows_and_peak_ram_into_rows`:

```python
    def test_cumulative_fields_pass_through_into_the_row(self):
        convert_log_text = (
            "RAM_SIZING_START book=Ok_2007 pages=382 file_size_bytes=41231000 "
            "ts=1000 cumulative_pages_so_far=382 cumulative_file_size_bytes_so_far=41231000\n"
            "RAM_SIZING_END book=Ok_2007 ts=1030 status=success\n"
        )
        ram_log_text = "1000 16000 8000 8000 2000 9000\n"
        rows = build_rows(convert_log_text, ram_log_text, course="microecon", machine_type="g2-standard-4")
        self.assertEqual(rows[0]["cumulative_pages_so_far"], 382)
        self.assertEqual(rows[0]["cumulative_file_size_bytes_so_far"], 41231000)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py::TestParseBookWindows tests/test_vm_sizing_log.py::TestBuildRows -v`
Expected: FAIL — `KeyError: 'cumulative_pages_so_far'`

- [ ] **Step 3: Implement**

In `textbook/vm_sizing_log.py`, find:

```python
_RAM_SIZING_START_RE = re.compile(
    r"RAM_SIZING_START book=(?P<book>\S+) pages=(?P<pages>\d+) "
    r"file_size_bytes=(?P<file_size_bytes>\d+) ts=(?P<ts>\d+)"
)
```

Change to:

```python
_RAM_SIZING_START_RE = re.compile(
    r"RAM_SIZING_START book=(?P<book>\S+) pages=(?P<pages>\d+) "
    r"file_size_bytes=(?P<file_size_bytes>\d+) ts=(?P<ts>\d+)"
    r"(?: cumulative_pages_so_far=(?P<cumulative_pages_so_far>\d+) "
    r"cumulative_file_size_bytes_so_far=(?P<cumulative_file_size_bytes_so_far>\d+))?"
)
```

Then find:

```python
        m = _RAM_SIZING_START_RE.search(line)
        if m:
            starts[m.group("book")] = {
                "book": m.group("book"),
                "pages": int(m.group("pages")),
                "file_size_bytes": int(m.group("file_size_bytes")),
                "start_ts": int(m.group("ts")),
            }
            continue
```

Change to:

```python
        m = _RAM_SIZING_START_RE.search(line)
        if m:
            cumulative_pages = m.group("cumulative_pages_so_far")
            cumulative_bytes = m.group("cumulative_file_size_bytes_so_far")
            starts[m.group("book")] = {
                "book": m.group("book"),
                "pages": int(m.group("pages")),
                "file_size_bytes": int(m.group("file_size_bytes")),
                "start_ts": int(m.group("ts")),
                "cumulative_pages_so_far": int(cumulative_pages) if cumulative_pages is not None else None,
                "cumulative_file_size_bytes_so_far": int(cumulative_bytes) if cumulative_bytes is not None else None,
            }
            continue
```

Then find `build_rows`:

```python
    return [
        {
            "course": course,
            "book": w["book"],
            "pages": w["pages"],
            "file_size_bytes": w["file_size_bytes"],
            "peak_ram_used_mb": peak_ram_used_mb(samples, w["start_ts"], w["end_ts"]),
            "status": w["status"],
            "machine_type": machine_type,
            "start_ts": w["start_ts"],
            "end_ts": w["end_ts"],
        }
        for w in windows
    ]
```

Change to:

```python
    return [
        {
            "course": course,
            "book": w["book"],
            "pages": w["pages"],
            "file_size_bytes": w["file_size_bytes"],
            "peak_ram_used_mb": peak_ram_used_mb(samples, w["start_ts"], w["end_ts"]),
            "status": w["status"],
            "machine_type": machine_type,
            "start_ts": w["start_ts"],
            "end_ts": w["end_ts"],
            "cumulative_pages_so_far": w["cumulative_pages_so_far"],
            "cumulative_file_size_bytes_so_far": w["cumulative_file_size_bytes_so_far"],
        }
        for w in windows
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: PASS — every test in the file, including every pre-existing `TestParseBookWindows`/`TestBuildRows` case (none of them include the new fields in their fixture text, so they exercise the backward-compatible `None` path implicitly).

- [ ] **Step 5: Commit**

```bash
git add textbook/vm_sizing_log.py tests/test_vm_sizing_log.py
git commit -m "feat(textbook): parse RAM_SIZING_START's cumulative fields in vm_sizing_log.py

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Batch ordering by size (documentation)

**Files:**
- Modify: `convert_textbook_agent_instructions.md` (Step 0.3, the `PDF_FILENAMES` rebuild after the duplicate check)

**Interfaces:** None — documentation only.

- [ ] **Step 1: Add the ascending-size sort**

Find this block in `convert_textbook_agent_instructions.md` (Step 0.3):

```
Then rebuild `PDF_FILENAMES` from the emitted file:

```bash
mapfile -t PDF_FILENAMES < /tmp/to_convert.txt
export PDF_FILENAMES
printf '  %s\n' "${PDF_FILENAMES[@]}"
```
```

Replace it with:

```
Then rebuild `PDF_FILENAMES` from the emitted file:

```bash
mapfile -t PDF_FILENAMES < /tmp/to_convert.txt
export PDF_FILENAMES
```

**Sort ascending by file size** (pipeline-autonomy-policies spec,
Component 2b) before reporting or using this list further. A resize
triggered by the OOM escalation ladder (Step 3.3's Debugging appendix)
changes the machine type for the *rest* of the batch, not just the
offending book — putting the largest/highest-risk book last means that if
a resize does trigger, there's little or nothing left in the batch to run
unnecessarily on the pricier machine type.

```bash
if [ ${#PDF_FILENAMES[@]} -gt 0 ]; then
    mapfile -t PDF_FILENAMES < <(
        for f in "${PDF_FILENAMES[@]}"; do
            SZ=$(stat -c%s "../academic-hub/$TEXTBOOK_SUBDIR/$f" 2>/dev/null || stat -f%z "../academic-hub/$TEXTBOOK_SUBDIR/$f")
            printf '%s\t%s\n' "$SZ" "$f"
        done | sort -n | cut -f2-
    )
fi
export PDF_FILENAMES
printf '  %s\n' "${PDF_FILENAMES[@]}"
```
```

- [ ] **Step 2: Verify code-fence balance**

Run: `grep -c '^```' convert_textbook_agent_instructions.md`
Expected: an even count.

- [ ] **Step 3: Commit**

```bash
git add convert_textbook_agent_instructions.md
git commit -m "docs(textbook): sort the conversion batch ascending by file size

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Pre-VM-creation cost check becomes auto-proceed (documentation)

**Files:**
- Modify: `convert_textbook_agent_instructions.md` (Step 1.3)

**Interfaces:** None — documentation only.

- [ ] **Step 1: Replace the blocking confirmation with auto-proceed + an escalation cap**

Find this block in `convert_textbook_agent_instructions.md` (Step 1.3):

```
**Ask the user to confirm before proceeding** — state the PDF count and
total size, that this launches a billed `g2-standard-4` + L4 Spot VM for
a run that (based on prior real runs) takes on the order of hours for a
multi-hundred-page batch, and that a Spot VM can be preempted mid-run
(recoverable, but costs wall-clock). Only create the VM after a yes.
```

Replace it with:

```
**Proceed automatically** (pipeline-autonomy-policies spec, Component
2a) — report the PDF count and total size, that this launches a billed
`g2-standard-4` + L4 Spot VM for a run that (based on prior real runs)
takes on the order of hours for a multi-hundred-page batch, and that a
Spot VM can be preempted mid-run (recoverable, but costs wall-clock) —
then create the VM without waiting for a reply.

**Exception — stop and ask if this batch is unprecedented:** more than 15
books, or more than 2000 MB total (an initial, conservative cap pending
real history — see the spec's Open Items, which flags this exact number
as a judgment call to revisit once `vm_sizing_log.jsonl` has enough real
batches in it). Crossing either threshold means report the size and ask
before proceeding — a batch this much larger than anything seen so far
may reflect a mistake (e.g. an entire library folder pointed at instead
of one course's) rather than a genuinely large intentional run.
```

- [ ] **Step 2: Verify code-fence balance**

Run: `grep -c '^```' convert_textbook_agent_instructions.md`
Expected: an even count (this task adds no new code fences, only prose).

- [ ] **Step 3: Commit**

```bash
git add convert_textbook_agent_instructions.md
git commit -m "docs(textbook): auto-proceed past the cost sanity check, escalate only if unprecedented

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: OOM escalation ladder replaces the manual-recovery procedure (documentation)

**Files:**
- Modify: `convert_textbook_agent_instructions.md` (the "When to stop and ask" list, and the Debugging appendix's OOM-kill section)

**Interfaces:** None — documentation only.

- [ ] **Step 1: Rewrite the "When to stop and ask" list**

Find this block in `convert_textbook_agent_instructions.md`:

```
## When to stop and ask the user

Do not proceed past these points without an explicit answer:
1. **Subdirectory inclusion** (Step 0 below) — every run.
2. **Size/cost sanity check** before creating the VM (Step 1.3) — every run.
3. **Every Tier 2 (fuzzy) duplicate match** (Step 0.4) — never auto-skip one.
4. **VM deletion** at the end of a session (Step 4).
5. **Any Preflight gap** (Step -1) you can't fix yourself — report and stop;
   don't attempt to request quota, enable billing, or grant IAM roles
   beyond what Step -1 itself checks for.
6. **A second genuine system-RAM OOM-kill on the same book/chunk after one
   manual `gcloud compute instances reset` + relaunch already tried** (see
   the Debugging appendix's "chunk is silently degraded" entry) — this is
   a real signal the machine type is undersized for that book's content,
   and resizing (e.g. `g2-standard-4` → `g2-standard-8`, same L4 GPU, more
   system RAM) is a cost-changing decision, not something to do silently.
   Note this is about the *external* reset-and-relaunch, not
   `start_conversion.sh`'s own built-in watchdog retries -- those 5
   automatic attempts happen first, inside the VM, and don't by themselves
   fix an OOM-kill (see the appendix), so their exhaustion alone doesn't
   yet meet this bar. A single tight-but-recovering `free -h` reading, or
   a container/process dying for a reason *other* than a confirmed
   `dmesg`-visible OOM-kill, does not meet this bar either — let the
   watchdog's automatic retries handle those.
```

Replace it with:

```
## When to stop and ask the user

Do not proceed past these points without an explicit answer:
1. **Subdirectory inclusion** (Step 0 below) — every run.
2. **VM deletion** at the end of a session (Step 4).
3. **Any Preflight gap** (Step -1) you can't fix yourself — report and stop;
   don't attempt to request quota, enable billing, or grant IAM roles
   beyond what Step -1 itself checks for.

The size/cost sanity check, Tier 2 duplicate matches, and OOM-kill
recovery are no longer unconditional stop points — see
`docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`
for the policies that replace them:
- **Cost/size** (Step 1.3): proceed automatically; stop and ask only if
  the batch is unprecedented relative to history (spec Component 2a).
- **Duplicate matches** (Step 0.3): a score >= 0.85 auto-resolves
  immediately, queued for post-hoc review via
  `python -m indexer.duplicate_check --review-pending`; only the
  0.6-0.85 band still asks before proceeding (spec Component 1a).
- **OOM-kill recovery** (Debugging appendix below): a 3-rung escalation
  ladder handles the first two confirmed OOM-kills on a book
  automatically; only a third confirmed OOM-kill on the same book — even
  after a resize — still stops and asks (spec Component 2c).
```

- [ ] **Step 2: Rewrite the manual-recovery procedure as an automated ladder**

Find this block in the Debugging appendix (the OOM-kill entry's manual-recovery subsection):

```
  **Manual recovery -- needed only for a `dmesg`-confirmed OOM-kill, or
  when `~/convert_log.txt` shows the watchdog exhausted all 5 retries and
  the "convert" tmux session has ended:**
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="tmux kill-session -t autostop 2>/dev/null; tmux kill-session -t convert 2>/dev/null; echo done"
  ```
  ```bash
  gcloud compute instances reset "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  (Skip the reset if the trigger was retry exhaustion with no `dmesg`
  OOM-kill involved -- that's a different, non-memory root cause, and a
  reset won't fix it; investigate the `FATAL` lines' surrounding log
  context instead.) Wait ~1-2 minutes after a reset, then:
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="sudo docker ps -aq --filter 'name=surya-vllm-' | xargs -r sudo docker rm -f; pgrep -f 'surya\.ocr_error\.server' | xargs -r sudo kill -9; nvidia-smi --query-gpu=memory.used --format=csv,noheader"
  ```
  Confirm that last command reads low (a few hundred MB is fine; multi-GB
  means something is still holding memory) -- this is a belt-and-suspenders
  check; `start_conversion.sh`'s watchdog runs the same cleanup itself on
  every attempt, including the first one after this manual step. Then
  relaunch Step 3.3 with the same book list (already-finished books skip
  via `convert_textbook.py`'s own whole-book check; already-good chunks
  within an in-progress book skip via the per-chunk checkpoint -- and any
  chunk that was mid-flight during the kill was never marked `.done` in
  the first place, since `chunk_is_degraded` exits before that write) and
  re-arm the autostop watcher as usual.
```

Replace it with:

```
  **Automated recovery -- a 3-rung escalation ladder** (pipeline-autonomy-
  policies spec, Component 2c), reached only after the watchdog's own 5
  retries are exhausted and `~/convert_log.txt` shows the "convert" tmux
  session has ended:

  **Precondition for every rung: positively confirm this was an OOM-kill,
  not a different retry-exhaustion cause.** Run:
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="dmesg 2>/dev/null | grep -i 'killed process'"
  ```
  A hit confirms an OOM-kill -- proceed to the matching rung below. No hit
  means a different root cause (torchaudio crash, orphaned-container VRAM
  exhaustion, an unexplained Docker `TaskDelete`) -- a reset will not fix
  this; investigate the `FATAL` lines' surrounding log context instead,
  and do not count this toward the rung ladder below.

  **Rung 1 -- 1st confirmed OOM-kill on this book:** kill both tmux
  sessions, then reset:
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="tmux kill-session -t autostop 2>/dev/null; tmux kill-session -t convert 2>/dev/null; echo done"
  ```
  ```bash
  gcloud compute instances reset "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  Wait ~1-2 minutes, then clean up any leftover inference-server state
  (belt-and-suspenders -- `start_conversion.sh`'s watchdog does this too
  on its first attempt after relaunch):
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="sudo docker ps -aq --filter 'name=surya-vllm-' | xargs -r sudo docker rm -f; pgrep -f 'surya\.ocr_error\.server' | xargs -r sudo kill -9; nvidia-smi --query-gpu=memory.used --format=csv,noheader"
  ```
  Confirm that last command reads low (a few hundred MB is fine; multi-GB
  means something is still holding memory). Relaunch Step 3.3 with the
  same book list (already-finished books and chunks skip via the existing
  whole-book/per-chunk checkpoints) and re-arm the autostop watcher. No
  report needed beyond the log line -- this rung is fully automatic.

  **Rung 2 -- 2nd confirmed OOM-kill on the same book** (the dmesg check
  above applies again): repeat Rung 1's kill-sessions and cleanup steps,
  but resize the machine type instead of a plain reset:
  ```bash
  gcloud compute instances stop "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  ```bash
  gcloud compute instances set-machine-type "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --machine-type=g2-standard-8
  ```
  ```bash
  gcloud compute instances start "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  **Report this the moment it happens** (not just in an end-of-run
  summary) -- a note that a resize occurred, not a blocking question. This
  is specifically so a *pattern* of frequent resizes across separate runs
  stays visible without digging through historical logs; if
  `g2-standard-4` turns out to be the wrong default, this is the signal
  that would show it. Relaunch Step 3.3 with the same book list as in Rung
  1. After it completes cleanly (no further `chunk_is_degraded` firing),
  fold the outcome into the RAM-sizing dataset via Step 3.4c as usual --
  this resize is itself a real data point for the still-thin
  `vm_sizing_log.jsonl`.

  **Rung 3 -- 3rd confirmed OOM-kill on the same book, even after the
  resize:** stop and ask the user. Two different machine sizes both
  failing on the same book, both times a genuine OOM (dmesg-confirmed),
  is outside anything this pipeline has seen and warrants a human look
  rather than a further automatic escalation.
```

- [ ] **Step 3: Verify code-fence balance**

Run: `grep -c '^```' convert_textbook_agent_instructions.md`
Expected: an even count.

- [ ] **Step 4: Commit**

```bash
git add convert_textbook_agent_instructions.md
git commit -m "docs(textbook): replace manual OOM recovery with a 3-rung escalation ladder

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: End-of-run cost reconciliation (documentation)

**Files:**
- Modify: `convert_textbook_agent_instructions.md` (Step 3.4c)

**Interfaces:** None — documentation only.

- [ ] **Step 1: Add a cost-reconciliation note to the existing RAM-sizing download step**

Find this block in `convert_textbook_agent_instructions.md` (Step 3.4c, the closing parenthetical):

```
(`$REMOTE_HOME` is the value captured in Step 2.2. `--machine-type` should
match whatever Step 1.3 actually created the VM with.)
```

Replace it with:

```
(`$REMOTE_HOME` is the value captured in Step 2.2. `--machine-type` should
match whatever Step 1.3 actually created the VM with -- including any
Rung 2 resize from the Debugging appendix's escalation ladder, if one
happened during this run.)

**Cost reconciliation** (pipeline-autonomy-policies spec, Component 2e):
alongside this download, report the actual VM wall-clock time (from
Step 1.3's creation to just before Step 4's deletion) and an approximate
cost figure (machine-hour rate x hours, Spot pricing) next to Step 1.3's
pre-run size/cost estimate -- closing the loop on whether that estimate
was any good, without it ever having blocked the run.
```

- [ ] **Step 2: Verify code-fence balance**

Run: `grep -c '^```' convert_textbook_agent_instructions.md`
Expected: an even count.

- [ ] **Step 3: Commit**

```bash
git add convert_textbook_agent_instructions.md
git commit -m "docs(textbook): report actual vs. estimated cost at end of run

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full project test suite: `.venv/Scripts/python.exe -m pytest tests/ -q` — expect all green.
- [ ] `grep -n "cumulative_pages_so_far" textbook/convert_textbook.py textbook/vm_sizing_log.py` shows the write (Task 1) and the read (Task 2).
- [ ] `grep -c '^```' convert_textbook_agent_instructions.md` — even count, confirming Tasks 3-6 left the document well-formed.
- [ ] Read through the rewritten "When to stop and ask" list and Debugging appendix once, end to end, to confirm they read coherently as a single document — not just that each individual edit's fences balance.

## Self-Review Notes

- **Spec coverage:** 2a (auto-proceed cost check) -> Task 4; 2b (batch ordering) -> Task 3; 2c (escalation ladder) -> Task 5; 2d (RAM marker extension) -> Tasks 1-2; 2e (cost reconciliation) -> Task 6.
- **Placeholder scan:** no TBD/TODO; every code step shows complete, verified-against-the-real-file content; every documentation step shows the complete replacement prose, not a summary of what to write.
- **Type/signature consistency:** `parse_book_windows`'s new dict keys (Task 2) match exactly what Task 1's marker produces (`cumulative_pages_so_far`, `cumulative_file_size_bytes_so_far`); `build_rows` passes them through under the same names into the JSONL schema.
- **Scope:** two code tasks confined to the RAM-sizing observability pipeline (no change to VM provisioning behavior itself, matching the original Phase 1 spec's own constraint), four documentation tasks confined to `convert_textbook_agent_instructions.md`, none touching `convert_textbook_instructions.md`, `indexer/duplicate_check.py`, or `indexer/index_search.py` (the sibling plans' territory).
