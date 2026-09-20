# VM RAM-Sizing Logging (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Log peak system RAM used per book conversion, correlated with page count and file size, into a persistent, git-tracked dataset — with zero change to VM provisioning behavior (observability only; Phase 2's predictive multi-tier provisioning is a separate, future spec).

**Architecture:** A background shell loop in `start_conversion.sh` samples `free -m` every 15s for the lifetime of a whole batch run. `convert_textbook.py` prints two structured, tagged lines per book (start: page count, file size, timestamp; end: timestamp, success/failed). Both raw logs get downloaded from the VM after the batch (alongside the existing `processed_outputs` download, before VM deletion), and a new local module correlates them into one JSONL row per book, appended to a persistent dataset.

**Tech Stack:** Bash (start_conversion.sh), Python 3 stdlib only (no new dependency), `unittest` (matches this repo's existing test convention).

**Spec:** `docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md`

## Global Constraints

- No new Python dependency anywhere in this plan (stdlib only: `argparse`, `json`, `os`, `re`, `time`).
- `convert_textbook.py`'s core GPU-timing-sensitive code gets the smallest possible change: two `print()` lines and two boolean flags — no new thread, no new import.
- Any file this plan writes with `open(..., "w")` for a downstream-parsed artifact (the JSONL dataset) must use `newline="\n"` explicitly — this repo hit a real CRLF bug earlier (`indexer/duplicate_check.py`'s `--emit-to-convert`) from relying on Windows' text-mode default.
- The CLI (`textbook/vm_sizing_log.py`) fails loudly (lets exceptions propagate, non-zero exit) on a missing/unreadable input log — it's an offline analysis step run by a human/agent, not unattended VM code.
- The docs-level download+analyze step (Task 4) is best-effort: a failed `scp` must not block the batch's own completion/cleanup sequence.
- JSONL row schema (exact field names): `course`, `book`, `pages`, `file_size_bytes`, `peak_ram_used_mb`, `status`, `machine_type`, `start_ts`, `end_ts`.
- Dedup key for the JSONL dataset: `(book, start_ts)` — rerunning the correlation script against the same raw logs must never produce duplicate rows.
- RAM sample line format (written by `start_conversion.sh`, parsed by `textbook/vm_sizing_log.py`): `<unix_ts> <total_mb> <used_mb> <free_mb> <buff_cache_mb> <available_mb>` (space-separated integers, in that order — the numeric fields of `free -m`'s `Mem:` row).
- Book marker line format (written by `convert_textbook.py`, parsed by `textbook/vm_sizing_log.py`):
  - `RAM_SIZING_START book=<name> pages=<n> file_size_bytes=<n> ts=<unix_ts>`
  - `RAM_SIZING_END book=<name> ts=<unix_ts> status=success|failed`

---

### Task 1: `textbook/vm_sizing_log.py` — parsing, correlation, and CLI

**Files:**
- Create: `textbook/vm_sizing_log.py`
- Test: `tests/test_vm_sizing_log.py`

**Interfaces:**
- Produces: `parse_ram_samples(ram_log_text: str) -> list[dict]`, `parse_book_windows(convert_log_text: str) -> list[dict]`, `peak_ram_used_mb(samples: list[dict], start_ts: int, end_ts: int | None) -> int | None`, `build_rows(convert_log_text: str, ram_log_text: str, course: str, machine_type: str) -> list[dict]`, `load_existing_keys(output_path: str) -> set[tuple[str, int]]`, `append_rows(rows: list[dict], output_path: str) -> int`, `build_arg_parser() -> argparse.ArgumentParser`, `main() -> None`.
- Consumes: the two line formats fixed in Global Constraints above (Tasks 2 and 3 must produce exactly these).

- [ ] **Step 1: Write the failing tests for `parse_ram_samples`**

Create `tests/test_vm_sizing_log.py`:

```python
import json
import os
import tempfile
import unittest

from textbook.vm_sizing_log import (
    parse_ram_samples,
    parse_book_windows,
    peak_ram_used_mb,
    build_rows,
    load_existing_keys,
    append_rows,
    build_arg_parser,
)


class TestParseRamSamples(unittest.TestCase):
    def test_parses_well_formed_lines(self):
        text = "1000 16000 8000 8000 2000 9000\n1015 16000 9000 7000 2000 8500\n"
        samples = parse_ram_samples(text)
        self.assertEqual(len(samples), 2)
        self.assertEqual(samples[0], {
            "ts": 1000, "total_mb": 16000, "used_mb": 8000,
            "free_mb": 8000, "buff_cache_mb": 2000, "available_mb": 9000,
        })

    def test_skips_malformed_lines(self):
        text = "not a valid line\n1000 16000 8000 8000 2000 9000\n"
        samples = parse_ram_samples(text)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["ts"], 1000)

    def test_empty_input(self):
        self.assertEqual(parse_ram_samples(""), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v` (or `python3 -m pytest ...` outside this repo's venv)
Expected: FAIL / collection error — `textbook/vm_sizing_log.py` does not exist yet.

- [ ] **Step 3: Create `textbook/vm_sizing_log.py` with `parse_ram_samples`**

```python
"""
Correlates convert_textbook.py's per-book RAM_SIZING markers against
start_conversion.sh's sampled system RAM into a persistent dataset. See
docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md.

Phase 1 (this module): observability only. No VM provisioning behavior
depends on this data yet.
"""
import argparse
import json
import os
import re


def parse_ram_samples(ram_log_text: str) -> list[dict]:
    """
    Parses lines of the form "<unix_ts> <total_mb> <used_mb> <free_mb>
    <buff_cache_mb> <available_mb>" (start_conversion.sh's RAM sampler
    format) into a list of dicts with those exact keys, all ints.
    Malformed lines are skipped, not fatal -- a corrupt line from a
    truncated download shouldn't lose every other sample in the file.
    """
    samples = []
    for line in ram_log_text.splitlines():
        parts = line.split()
        if len(parts) != 6:
            continue
        try:
            ts, total_mb, used_mb, free_mb, buff_cache_mb, available_mb = (int(p) for p in parts)
        except ValueError:
            continue
        samples.append({
            "ts": ts, "total_mb": total_mb, "used_mb": used_mb,
            "free_mb": free_mb, "buff_cache_mb": buff_cache_mb, "available_mb": available_mb,
        })
    return samples
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: the 3 `TestParseRamSamples` tests PASS (others still fail on import — `parse_book_windows` etc. don't exist yet).

- [ ] **Step 5: Write the failing tests for `parse_book_windows`**

Add to `tests/test_vm_sizing_log.py`:

```python
class TestParseBookWindows(unittest.TestCase):
    def test_matches_start_and_end_by_book_name(self):
        text = (
            "some other log line\n"
            "RAM_SIZING_START book=Ok_Real_Analysis_2007 pages=382 file_size_bytes=41231000 ts=1000\n"
            "more log noise\n"
            "RAM_SIZING_END book=Ok_Real_Analysis_2007 ts=1500 status=success\n"
        )
        windows = parse_book_windows(text)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0], {
            "book": "Ok_Real_Analysis_2007", "pages": 382, "file_size_bytes": 41231000,
            "start_ts": 1000, "end_ts": 1500, "status": "success",
        })

    def test_start_without_matching_end_is_incomplete(self):
        text = "RAM_SIZING_START book=CrashedBook pages=100 file_size_bytes=5000 ts=2000\n"
        windows = parse_book_windows(text)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["status"], "incomplete")
        self.assertIsNone(windows[0]["end_ts"])

    def test_multiple_books_in_one_log(self):
        text = (
            "RAM_SIZING_START book=BookA pages=10 file_size_bytes=100 ts=1000\n"
            "RAM_SIZING_END book=BookA ts=1100 status=success\n"
            "RAM_SIZING_START book=BookB pages=20 file_size_bytes=200 ts=1200\n"
            "RAM_SIZING_END book=BookB ts=1300 status=failed\n"
        )
        windows = parse_book_windows(text)
        self.assertEqual({w["book"] for w in windows}, {"BookA", "BookB"})
        book_b = next(w for w in windows if w["book"] == "BookB")
        self.assertEqual(book_b["status"], "failed")

    def test_no_ram_sizing_lines_returns_empty(self):
        self.assertEqual(parse_book_windows("just some normal log output\nnothing tagged here\n"), [])
```

- [ ] **Step 6: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py::TestParseBookWindows -v`
Expected: FAIL — `parse_book_windows` not defined.

- [ ] **Step 7: Implement `parse_book_windows`**

Add to `textbook/vm_sizing_log.py`:

```python
_RAM_SIZING_START_RE = re.compile(
    r"RAM_SIZING_START book=(?P<book>\S+) pages=(?P<pages>\d+) "
    r"file_size_bytes=(?P<file_size_bytes>\d+) ts=(?P<ts>\d+)"
)
_RAM_SIZING_END_RE = re.compile(
    r"RAM_SIZING_END book=(?P<book>\S+) ts=(?P<ts>\d+) status=(?P<status>success|failed)"
)


def parse_book_windows(convert_log_text: str) -> list[dict]:
    """
    Matches RAM_SIZING_START/RAM_SIZING_END lines by book name into a list
    of dicts: {"book", "pages", "file_size_bytes", "start_ts", "end_ts",
    "status"}. A START with no matching END produces end_ts=None,
    status="incomplete" -- the book never finished (a crash mid-conversion),
    which peak_ram_used_mb below treats as the most informative case, not
    a data gap.
    """
    starts: dict[str, dict] = {}
    windows = []
    for line in convert_log_text.splitlines():
        m = _RAM_SIZING_START_RE.search(line)
        if m:
            starts[m.group("book")] = {
                "book": m.group("book"),
                "pages": int(m.group("pages")),
                "file_size_bytes": int(m.group("file_size_bytes")),
                "start_ts": int(m.group("ts")),
            }
            continue
        m = _RAM_SIZING_END_RE.search(line)
        if m and m.group("book") in starts:
            start = starts.pop(m.group("book"))
            windows.append({**start, "end_ts": int(m.group("ts")), "status": m.group("status")})

    for start in starts.values():
        windows.append({**start, "end_ts": None, "status": "incomplete"})
    return windows
```

- [ ] **Step 8: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: `TestParseRamSamples` and `TestParseBookWindows` PASS.

- [ ] **Step 9: Write the failing tests for `peak_ram_used_mb`**

Add to `tests/test_vm_sizing_log.py`:

```python
class TestPeakRamUsedMb(unittest.TestCase):
    def _samples(self):
        return [
            {"ts": 1000, "used_mb": 5000},
            {"ts": 1015, "used_mb": 9000},
            {"ts": 1030, "used_mb": 7000},
            {"ts": 1045, "used_mb": 6000},
        ]

    def test_finds_max_within_window(self):
        self.assertEqual(peak_ram_used_mb(self._samples(), 1000, 1030), 9000)

    def test_none_end_ts_extends_to_last_sample(self):
        # Incomplete book (no END line) -- window runs to the last
        # available sample, capturing the highest RAM point right before
        # the crash.
        self.assertEqual(peak_ram_used_mb(self._samples(), 1015, None), 9000)

    def test_no_samples_in_window_returns_none(self):
        self.assertIsNone(peak_ram_used_mb(self._samples(), 5000, 6000))

    def test_empty_samples_returns_none(self):
        self.assertIsNone(peak_ram_used_mb([], 1000, 2000))
```

- [ ] **Step 10: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py::TestPeakRamUsedMb -v`
Expected: FAIL — `peak_ram_used_mb` not defined.

- [ ] **Step 11: Implement `peak_ram_used_mb`**

Add to `textbook/vm_sizing_log.py`:

```python
def peak_ram_used_mb(samples: list[dict], start_ts: int, end_ts: int | None) -> int | None:
    """
    Max used_mb among samples with start_ts <= ts <= end_ts. When end_ts is
    None (an incomplete book -- see parse_book_windows), the window
    extends to the last sample's ts instead. Returns None if no samples
    fall in the window (e.g. the RAM log was truncated or missing).
    """
    if not samples:
        return None
    effective_end_ts = end_ts if end_ts is not None else max(s["ts"] for s in samples)
    in_window = [s["used_mb"] for s in samples if start_ts <= s["ts"] <= effective_end_ts]
    return max(in_window) if in_window else None
```

- [ ] **Step 12: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: all tests so far PASS.

- [ ] **Step 13: Write the failing tests for `build_rows`, `load_existing_keys`, and `append_rows`**

Add to `tests/test_vm_sizing_log.py`:

```python
class TestBuildRows(unittest.TestCase):
    def test_combines_windows_and_peak_ram_into_rows(self):
        convert_log_text = (
            "RAM_SIZING_START book=Ok_2007 pages=382 file_size_bytes=41231000 ts=1000\n"
            "RAM_SIZING_END book=Ok_2007 ts=1030 status=success\n"
        )
        ram_log_text = "1000 16000 8000 8000 2000 9000\n1020 16000 13102 2898 2000 4000\n"
        rows = build_rows(convert_log_text, ram_log_text, course="microecon", machine_type="g2-standard-4")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["peak_ram_used_mb"], 13102)
        self.assertEqual(row["course"], "microecon")
        self.assertEqual(row["machine_type"], "g2-standard-4")
        self.assertEqual(row["book"], "Ok_2007")
        self.assertEqual(row["pages"], 382)
        self.assertEqual(row["file_size_bytes"], 41231000)
        self.assertEqual(row["status"], "success")
        self.assertEqual(row["start_ts"], 1000)
        self.assertEqual(row["end_ts"], 1030)

    def test_row_with_no_samples_in_window_has_null_peak(self):
        convert_log_text = (
            "RAM_SIZING_START book=X pages=5 file_size_bytes=100 ts=9000\n"
            "RAM_SIZING_END book=X ts=9010 status=success\n"
        )
        rows = build_rows(convert_log_text, ram_log_text="", course="c", machine_type="m")
        self.assertIsNone(rows[0]["peak_ram_used_mb"])


class TestLoadExistingKeys(unittest.TestCase):
    def test_empty_when_file_does_not_exist(self):
        self.assertEqual(load_existing_keys(os.path.join(tempfile.gettempdir(), "no_such_vm_sizing_log.jsonl")), set())

    def test_reads_book_and_start_ts_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "vm_sizing_log.jsonl")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"book": "A", "start_ts": 1000}) + "\n")
            self.assertEqual(load_existing_keys(output_path), {("A", 1000)})


class TestAppendRows(unittest.TestCase):
    def test_appends_new_rows_as_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "vm_sizing_log.jsonl")
            rows = [{"book": "A", "start_ts": 1000, "peak_ram_used_mb": 9000}]
            added = append_rows(rows, output_path)
            self.assertEqual(added, 1)
            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["book"], "A")

    def test_skips_rows_already_present_by_book_and_start_ts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "vm_sizing_log.jsonl")
            row = {"book": "A", "start_ts": 1000, "peak_ram_used_mb": 9000}
            append_rows([row], output_path)
            added_again = append_rows([row], output_path)
            self.assertEqual(added_again, 0)
            with open(output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1, "duplicate row must not be appended twice")

    def test_writes_lf_only_not_crlf(self):
        # Real bug this session (indexer/duplicate_check.py's
        # --emit-to-convert): plain text-mode open() on Windows writes
        # \r\n, which breaks a downstream line-based parse/mapfile.
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "vm_sizing_log.jsonl")
            append_rows([{"book": "A", "start_ts": 1000}], output_path)
            with open(output_path, "rb") as f:
                raw = f.read()
            self.assertNotIn(b"\r\n", raw)
```

- [ ] **Step 14: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: FAIL — `build_rows`, `load_existing_keys`, `append_rows` not defined.

- [ ] **Step 15: Implement `build_rows`, `load_existing_keys`, `append_rows`**

Add to `textbook/vm_sizing_log.py`:

```python
def build_rows(convert_log_text: str, ram_log_text: str, course: str, machine_type: str) -> list[dict]:
    """One row per book found in convert_log_text, with peak RAM correlated
    from ram_log_text. See the module docstring / design spec for the
    exact schema."""
    samples = parse_ram_samples(ram_log_text)
    windows = parse_book_windows(convert_log_text)
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


def load_existing_keys(output_path: str) -> set[tuple[str, int]]:
    """(book, start_ts) pairs already present in output_path, so
    append_rows can skip them. Empty set if the file doesn't exist yet."""
    if not os.path.exists(output_path):
        return set()
    keys = set()
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            keys.add((row["book"], row["start_ts"]))
    return keys


def append_rows(rows: list[dict], output_path: str) -> int:
    """
    Appends rows not already present (by (book, start_ts)) to output_path
    as JSON Lines. Returns how many were actually added. Safe to call
    repeatedly against the same rows -- rerunning the CLI on the same pair
    of raw logs is always a no-op the second time.
    """
    existing_keys = load_existing_keys(output_path)
    new_rows = [r for r in rows if (r["book"], r["start_ts"]) not in existing_keys]
    if not new_rows:
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "a", encoding="utf-8", newline="\n") as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(new_rows)
```

- [ ] **Step 16: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: all tests PASS.

- [ ] **Step 17: Write the failing test for the CLI wiring**

Add to `tests/test_vm_sizing_log.py`:

```python
class TestBuildArgParser(unittest.TestCase):
    def test_parses_required_flags(self):
        parser = build_arg_parser()
        args = parser.parse_args([
            "--convert-log", "a.txt", "--ram-log", "b.txt",
            "--course", "microecon", "--machine-type", "g2-standard-4",
        ])
        self.assertEqual(args.convert_log, "a.txt")
        self.assertEqual(args.ram_log, "b.txt")
        self.assertEqual(args.course, "microecon")
        self.assertEqual(args.machine_type, "g2-standard-4")
        self.assertEqual(args.output, os.path.join("docs", "status", "vm_sizing_log.jsonl"))

    def test_output_is_overridable(self):
        parser = build_arg_parser()
        args = parser.parse_args([
            "--convert-log", "a.txt", "--ram-log", "b.txt",
            "--course", "c", "--machine-type", "m", "--output", "custom.jsonl",
        ])
        self.assertEqual(args.output, "custom.jsonl")
```

- [ ] **Step 18: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py::TestBuildArgParser -v`
Expected: FAIL — `build_arg_parser` not defined.

- [ ] **Step 19: Implement `build_arg_parser` and `main`**

Add to `textbook/vm_sizing_log.py`:

```python
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Correlate per-book RAM_SIZING markers (convert_textbook.py) against "
                     "sampled system RAM (start_conversion.sh) into a persistent dataset. "
                     "See docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md",
    )
    parser.add_argument("--convert-log", required=True, help="Path to the downloaded convert_log.txt for one run.")
    parser.add_argument("--ram-log", required=True, help="Path to the downloaded ram_sampling_log.txt for the same run.")
    parser.add_argument("--course", required=True, help="Course name, e.g. 'microecon'.")
    parser.add_argument("--machine-type", required=True, help="GCP machine type this run used, e.g. 'g2-standard-4'.")
    parser.add_argument(
        "--output", default=os.path.join("docs", "status", "vm_sizing_log.jsonl"),
        help="JSONL file to append new rows to (default: docs/status/vm_sizing_log.jsonl).",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    with open(args.convert_log, "r", encoding="utf-8") as f:
        convert_log_text = f.read()
    with open(args.ram_log, "r", encoding="utf-8") as f:
        ram_log_text = f.read()

    rows = build_rows(convert_log_text, ram_log_text, args.course, args.machine_type)
    for row in rows:
        if row["peak_ram_used_mb"] is None:
            print(f"WARNING: no RAM samples found in the window for book={row['book']!r}; "
                  f"row will be written with peak_ram_used_mb=null.")

    added = append_rows(rows, args.output)
    print(f"Added {added} new row(s) to {args.output} ({len(rows) - added} already present, skipped).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 20: Run the full test file to verify everything passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_vm_sizing_log.py -v`
Expected: all tests PASS (should be ~18 tests across the 6 test classes above).

- [ ] **Step 21: Commit**

```bash
git add textbook/vm_sizing_log.py tests/test_vm_sizing_log.py
git commit -m "feat(textbook): add vm_sizing_log.py to correlate RAM usage with book size

Phase 1 of docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md
-- observability only, no VM provisioning behavior changes yet."
```

---

### Task 2: `convert_textbook.py` — emit RAM_SIZING markers per book

**Files:**
- Modify: `textbook/convert_textbook.py` (`process_one_pdf`, currently starts at line 820 — line numbers below are relative to the version as of commit `20cdb6a`; search for the quoted snippets if line numbers have since shifted)
- Test: `tests/test_convert_textbook.py`

**Interfaces:**
- Consumes: nothing new. Produces exactly the line formats fixed in Global Constraints (`RAM_SIZING_START ...` / `RAM_SIZING_END ...`) — Task 1's `_RAM_SIZING_START_RE`/`_RAM_SIZING_END_RE` regexes must match these verbatim, so do not change field order, spacing, or key names from what's specified here.

- [ ] **Step 1: Write the failing test for the START marker**

Add to `tests/test_convert_textbook.py` (near the existing `TestProcessOnePdfAbortsOnDegradedChunk` class — reuse its `_setup` pattern):

```python
class TestProcessOnePdfEmitsRamSizingMarkers(unittest.TestCase):
    def _setup(self, tmp):
        input_pdf = os.path.join(tmp, "some_book.pdf")
        with open(input_pdf, "wb") as f:
            f.write(b"not a real pdf, just needs to exist, be hashable, and be sized")
        output_dir = os.path.join(tmp, "output")
        os.makedirs(output_dir)
        reader = _blank_pdf_reader(4)
        args = MagicMock(chunk_timeout=30, page_timeout=30, llm_bib=False)
        return input_pdf, output_dir, reader, args

    def test_emits_start_marker_with_pages_and_file_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            expected_size = os.path.getsize(input_pdf)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", side_effect=RuntimeError("reached boundaries, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn(f"RAM_SIZING_START book=some_book pages=4 file_size_bytes={expected_size} ts=", output)

    def test_no_ram_sizing_marker_when_book_is_skipped_as_already_converted(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            fake_card = {"path": "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.md"}
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=("econ-101", fake_card)), \
                 patch.object(ct, "PdfReader") as mock_reader, \
                 redirect_stdout(captured):
                ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                    workspace=tmp, args=args,
                )
            mock_reader.assert_not_called()
            self.assertNotIn("RAM_SIZING", captured.getvalue())
```

`tests/test_convert_textbook.py` already imports `io` (line 1) — only
`redirect_stdout` is new. Add this import at the top of the file, next to
the existing `from unittest.mock import MagicMock, patch` line:
```python
from contextlib import redirect_stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py::TestProcessOnePdfEmitsRamSizingMarkers -v`
Expected: FAIL — no `RAM_SIZING_START` text is printed yet (`test_emits_start_marker_with_pages_and_file_size` fails; `test_no_ram_sizing_marker_when_book_is_skipped_as_already_converted` should already PASS since nothing prints it today — confirm it passes for the right reason, not by accident).

- [ ] **Step 3: Add the START marker to `process_one_pdf`**

In `textbook/convert_textbook.py`, find:
```python
    is_gcs_input = raw_input.startswith("gs://")
    is_gcs_output = raw_output.startswith("gs://")
    input_key = sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "untitled_input"
```
Change to:
```python
    is_gcs_input = raw_input.startswith("gs://")
    is_gcs_output = raw_output.startswith("gs://")
    input_key = sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "untitled_input"
    # Set once RAM_SIZING_START is actually printed below, and again right
    # before a successful return -- the finally block near the end of this
    # function uses both to decide whether/what RAM_SIZING_END to print.
    ram_sizing_started = False
    ram_sizing_success = False
```

Then find:
```python
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        print(f"Loaded document mapping: {total_pages} total pages.")
```
Change to:
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

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py::TestProcessOnePdfEmitsRamSizingMarkers -v`
Expected: both tests PASS.

- [ ] **Step 5: Write the failing test for the END marker on a real success**

Add to `TestProcessOnePdfEmitsRamSizingMarkers`:

```python
    def test_emits_end_marker_with_status_success_on_a_successful_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("# Some real content\n", {}, False, 0.0)), \
                 patch.object(ct, "get_gemini_client", return_value=None), \
                 patch.object(ct, "load_dotenv_override"), \
                 redirect_stdout(captured):
                ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                    workspace=tmp, args=args,
                )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=success", output)

    def test_emits_end_marker_with_status_failed_on_an_unhandled_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("real content", {}, False, 0.0)), \
                 patch.object(ct.gc, "collect", side_effect=RuntimeError("reached post-checkpoint cleanup, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=failed", output)

    def test_emits_end_marker_with_status_failed_when_a_chunk_is_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("mostly empty", {}, True, 0.75)), \
                 redirect_stdout(captured):
                with self.assertRaises(SystemExit):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=failed", output)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py::TestProcessOnePdfEmitsRamSizingMarkers -v`
Expected: the three new tests FAIL (no `RAM_SIZING_END` printed anywhere yet).

- [ ] **Step 7: Add the END marker to the existing `finally` block**

In `textbook/convert_textbook.py`, find:
```python
        shutil.rmtree(checkpoint_dir, ignore_errors=True)
        return final_destination

    finally:
        if is_gcs_input and os.path.exists(input_pdf):
            os.remove(input_pdf)
```
Change to:
```python
        shutil.rmtree(checkpoint_dir, ignore_errors=True)
        ram_sizing_success = True
        return final_destination

    finally:
        # Fires on every exit path -- a clean return above, a normal
        # exception, or chunk_is_degraded's sys.exit(1) -- since `finally`
        # runs regardless of exception type as it propagates. No marker at
        # all for a book that was skipped as already-converted (those
        # `return` statements are before RAM_SIZING_START is ever printed,
        # so `ram_sizing_started` stays False).
        if ram_sizing_started:
            status = "success" if ram_sizing_success else "failed"
            print(f"RAM_SIZING_END book={input_key} ts={int(time.time())} status={status}")
        if is_gcs_input and os.path.exists(input_pdf):
            os.remove(input_pdf)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_convert_textbook.py -v`
Expected: all tests in the file PASS (this includes the full pre-existing suite — confirm nothing else broke).

- [ ] **Step 9: Run the full project test suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all tests PASS (1357+ from before this plan, plus the new ones from Task 1 and this task).

- [ ] **Step 10: Commit**

```bash
git add textbook/convert_textbook.py tests/test_convert_textbook.py
git commit -m "feat(textbook): emit RAM_SIZING_START/END markers per book

Second half of docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md
-- feeds textbook/vm_sizing_log.py's correlation. Two print statements
and two boolean flags; no new logic, thread, or dependency in the
CUDA-timing-sensitive conversion path."
```

---

### Task 3: `start_conversion.sh` — background RAM sampler

**Files:**
- Modify: `start_conversion.sh`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `~/ram_sampling_log.txt` on the VM, in the line format fixed in Global Constraints — Task 1's `parse_ram_samples` must be able to read it verbatim.

- [ ] **Step 1: Add a configurable sample interval alongside the existing retry-loop constants**

In `start_conversion.sh`, find:
```bash
MAX_RETRIES=5
RETRY_DELAY_S=15
export MAX_RETRIES RETRY_DELAY_S REQUOTED_INPUTS REQUOTED_OUTPUT
```
Change to:
```bash
MAX_RETRIES=5
RETRY_DELAY_S=15
RAM_SAMPLE_INTERVAL_S=15
export MAX_RETRIES RETRY_DELAY_S RAM_SAMPLE_INTERVAL_S REQUOTED_INPUTS REQUOTED_OUTPUT
```

- [ ] **Step 2: Add the sampler-wrapped entry point, right after `run_conversion_with_retries`'s definition**

Find:
```bash
        echo "[System] Retrying in ${RETRY_DELAY_S}s (already-completed chunks will be skipped)."
        sleep "$RETRY_DELAY_S"
        attempt=$((attempt + 1))
    done
    return "$exit_code"
}
export -f run_conversion_with_retries
```
Change to:
```bash
        echo "[System] Retrying in ${RETRY_DELAY_S}s (already-completed chunks will be skipped)."
        sleep "$RETRY_DELAY_S"
        attempt=$((attempt + 1))
    done
    return "$exit_code"
}
export -f run_conversion_with_retries

# Background RAM sampler: records system-wide `free -m` readings for the
# whole lifetime of run_conversion_with_retries (spanning every retry
# attempt, not restarted per attempt), so a downstream correlation step
# (textbook/vm_sizing_log.py) can find the peak RAM used during any given
# book's conversion window. Truncated once here, matching the same
# `: > ~/convert_log.txt` pattern already used below for the main log, so
# a fresh launch never mixes samples from an unrelated earlier batch.
run_conversion_with_ram_sampling() {
    : > ~/ram_sampling_log.txt
    (
        while true; do
            echo "$(date +%s) $(free -m | awk '/^Mem:/{print $2, $3, $4, $6, $7}')"
            sleep "$RAM_SAMPLE_INTERVAL_S"
        done
    ) >> ~/ram_sampling_log.txt &
    local sampler_pid=$!

    run_conversion_with_retries
    local result=$?

    kill "$sampler_pid" 2>/dev/null || true
    return "$result"
}
export -f run_conversion_with_ram_sampling
```

- [ ] **Step 3: Point the tmux session at the new wrapper**

Find:
```bash
tmux new-session -d -s convert "run_conversion_with_retries 2>&1 | tee -a ~/convert_log.txt"
```
Change to:
```bash
tmux new-session -d -s convert "run_conversion_with_ram_sampling 2>&1 | tee -a ~/convert_log.txt"
```

- [ ] **Step 4: Syntax-check the script**

Run: `bash -n start_conversion.sh`
Expected: no output, exit code 0.

- [ ] **Step 5: Smoke-test the sampler in isolation**

This mirrors the smoke test already used earlier in this project for `run_conversion_with_retries` — stub `free`, `date`, and a fast `python3` so the loop runs in seconds instead of on a real VM.

```bash
TESTDIR=$(mktemp -d)
mkdir -p "$TESTDIR/bin" "$TESTDIR/home"
cat > "$TESTDIR/bin/sudo" <<'EOF'
#!/usr/bin/env bash
"$@"
EOF
cat > "$TESTDIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo ""
EOF
cat > "$TESTDIR/bin/pgrep" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
cat > "$TESTDIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
sleep 3
exit 0
EOF
chmod +x "$TESTDIR/bin/"*
export PATH="$TESTDIR/bin:$PATH"
export HOME="$TESTDIR/home"
cd "$TESTDIR/home"

source <(sed -n '/^cleanup_stale_inference_state/,/^export -f run_conversion_with_ram_sampling/p' /path/to/academic-rag-model/start_conversion.sh)
export MAX_RETRIES=1
export RETRY_DELAY_S=0
export RAM_SAMPLE_INTERVAL_S=1
export REQUOTED_INPUTS="gs://fake/input.pdf"
export REQUOTED_OUTPUT="gs://fake/output"

run_conversion_with_ram_sampling
echo "EXIT=$?"
echo "--- ram_sampling_log.txt ---"
cat "$TESTDIR/home/ram_sampling_log.txt"
rm -rf "$TESTDIR"
```
(Replace `/path/to/academic-rag-model/start_conversion.sh` with the real absolute path.)

Expected: `EXIT=0`, and `ram_sampling_log.txt` shows at least 2 lines (the 3-second fake conversion at a 1-second sample interval), each with exactly 6 space-separated fields. No process still running after the script returns (the sampler was killed).

- [ ] **Step 6: Commit**

```bash
git add start_conversion.sh
git commit -m "feat(textbook): sample system RAM for the whole conversion run

First half of docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md
-- writes ~/ram_sampling_log.txt, read by textbook/vm_sizing_log.py
after download."
```

---

### Task 4: Docs — download step and dataset location

**Files:**
- Modify: `convert_textbook_instructions.md`
- Modify: `convert_textbook_agent_instructions.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Task 1's CLI flags (`--convert-log`, `--ram-log`, `--course`, `--machine-type`, `--output`) and default output path; Task 3's log filename (`~/ram_sampling_log.txt`).

- [ ] **Step 1: Add `docs/status/vm_sizing_raw/` to `.gitignore`**

In `.gitignore`, add a new line (anywhere in the file; group with other generated/local-only paths):
```
docs/status/vm_sizing_raw/
```

- [ ] **Step 2: Add the new step to `convert_textbook_instructions.md`**

Find:
```
gcloud storage rm -r "gs://$BUCKET_NAME/processed_outputs/*" "gs://$BUCKET_NAME/input_documents/*" --continue-on-error
```
```

## Step 4: Terminate the Compute Instance
```
Insert a new subsection between them (immediately after the `gcloud storage rm` code block and its closing fence, before `## Step 4`):

```markdown
#### 3.4c: Download RAM-sizing logs and update the local dataset

Optional, but worth doing every run: `convert_textbook.py` and `start_conversion.sh` both log system RAM usage per book as they go (see `docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md`) -- this step pulls those logs down and folds them into a small, growing local dataset (`docs/status/vm_sizing_log.jsonl`) correlating each book's page count/file size with the peak RAM it actually used. Nothing reads this dataset automatically yet; it exists so a future machine-type-sizing decision can be based on real numbers instead of guesswork.

This is best-effort -- if either command below fails (e.g. the VM already looks unhealthy), don't let it block emptying the bucket or deleting the VM; just skip it and move on.

```bash
COURSE_NAME=$(cut -d/ -f2 <<< "$TEXTBOOK_SUBDIR")
RUN_DIR="docs/status/vm_sizing_raw/${TEXTBOOK_SUBDIR//\//_}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN_DIR"
gcloud compute scp $VM_INSTANCE_NAME:~/convert_log.txt $VM_INSTANCE_NAME:~/ram_sampling_log.txt "$RUN_DIR/" --zone=$GCP_ZONE --tunnel-through-iap
```

```bash
python -m textbook.vm_sizing_log \
    --convert-log "$RUN_DIR/convert_log.txt" \
    --ram-log "$RUN_DIR/ram_sampling_log.txt" \
    --course "$COURSE_NAME" --machine-type "g2-standard-4" \
    --output docs/status/vm_sizing_log.jsonl
```

(`--machine-type` should match whatever Step 1.3 actually created the VM with, if you ever change it from the default `g2-standard-4`.) The raw logs land under `docs/status/vm_sizing_raw/` (gitignored -- debugging exhaust for this one run); only `docs/status/vm_sizing_log.jsonl` is meant to be committed and grow across every future batch.
```

- [ ] **Step 3: Add the equivalent step to `convert_textbook_agent_instructions.md`**

Find:
```
Do not run this until every book in the batch is done and 3.4a has been
re-run with nothing new appearing — it deletes the source PDFs any
not-yet-finished book still needs.

## Step 4: Terminate the VM
```
Insert a new subsection between them:

```markdown
### 3.4c Download RAM-sizing logs and update the local dataset

Best-effort — if either command below fails, skip this and continue to
Step 4 rather than treating it as blocking. Pulls both raw logs down and
folds them into `docs/status/vm_sizing_log.jsonl` (gitignored raw logs
under `docs/status/vm_sizing_raw/`; only the `.jsonl` is meant to be
committed). Nothing reads this dataset automatically yet — see
`docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md`.

```bash
COURSE_NAME=$(cut -d/ -f2 <<< "$TEXTBOOK_SUBDIR")
RUN_DIR="docs/status/vm_sizing_raw/${TEXTBOOK_SUBDIR//\//_}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN_DIR"
gcloud compute scp "$VM_INSTANCE_NAME":"$REMOTE_HOME/convert_log.txt" "$VM_INSTANCE_NAME":"$REMOTE_HOME/ram_sampling_log.txt" "$RUN_DIR/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
```

```bash
python -m textbook.vm_sizing_log \
  --convert-log "$RUN_DIR/convert_log.txt" \
  --ram-log "$RUN_DIR/ram_sampling_log.txt" \
  --course "$COURSE_NAME" --machine-type "g2-standard-4" \
  --output docs/status/vm_sizing_log.jsonl
```

(`$REMOTE_HOME` is the value captured in Step 2.2. `--machine-type` should
match whatever Step 1.3 actually created the VM with.)
```

- [ ] **Step 4: Verify code-fence balance in both docs**

Run: `grep -c '^```' convert_textbook_instructions.md convert_textbook_agent_instructions.md`
Expected: both counts are even (matches the check already done for earlier doc edits this project).

- [ ] **Step 5: Commit**

```bash
git add convert_textbook_instructions.md convert_textbook_agent_instructions.md .gitignore
git commit -m "docs(textbook): document the RAM-sizing log download+analyze step

Completes docs/superpowers/specs/2026-09-20-vm-ram-sizing-logging-design.md
(Phase 1). docs/status/vm_sizing_raw/ is gitignored; only the correlated
vm_sizing_log.jsonl is meant to be committed."
```

---

## Final verification

- [ ] Run the full test suite once more: `.venv/Scripts/python.exe -m pytest tests/ -q` — expect all green.
- [ ] `grep -n "RAM_SIZING" textbook/convert_textbook.py` shows exactly the two print lines from Task 2.
- [ ] `grep -n "ram_sampling_log" start_conversion.sh` shows the sampler write (Task 3) and the two scp/download references in both docs (Task 4).
- [ ] Confirm `docs/status/vm_sizing_raw/` is gitignored: `git check-ignore -q docs/status/vm_sizing_raw/anything` exits 0.

This plan intentionally stops at observability. Do not add machine-type selection, batch-splitting, or any provisioning-behavior change here — that's Phase 2, a separate future spec once `docs/status/vm_sizing_log.jsonl` has real data in it.
