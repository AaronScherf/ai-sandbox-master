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


_RAM_SIZING_START_RE = re.compile(
    r"RAM_SIZING_START book=(?P<book>\S+) pages=(?P<pages>\d+) "
    r"file_size_bytes=(?P<file_size_bytes>\d+) ts=(?P<ts>\d+)"
    r"(?: cumulative_pages_so_far=(?P<cumulative_pages_so_far>\d+) "
    r"cumulative_file_size_bytes_so_far=(?P<cumulative_file_size_bytes_so_far>\d+))?"
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
        m = _RAM_SIZING_END_RE.search(line)
        if m and m.group("book") in starts:
            start = starts.pop(m.group("book"))
            windows.append({**start, "end_ts": int(m.group("ts")), "status": m.group("status")})

    for start in starts.values():
        windows.append({**start, "end_ts": None, "status": "incomplete"})
    return windows


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
            "cumulative_pages_so_far": w["cumulative_pages_so_far"],
            "cumulative_file_size_bytes_so_far": w["cumulative_file_size_bytes_so_far"],
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
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "a", encoding="utf-8", newline="\n") as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(new_rows)


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
