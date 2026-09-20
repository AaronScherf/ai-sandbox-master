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
        self.assertEqual(peak_ram_used_mb(self._samples(), 1015, None), 9000)

    def test_no_samples_in_window_returns_none(self):
        self.assertIsNone(peak_ram_used_mb(self._samples(), 5000, 6000))

    def test_empty_samples_returns_none(self):
        self.assertIsNone(peak_ram_used_mb([], 1000, 2000))


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
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "vm_sizing_log.jsonl")
            append_rows([{"book": "A", "start_ts": 1000}], output_path)
            with open(output_path, "rb") as f:
                raw = f.read()
            self.assertNotIn(b"\r\n", raw)


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
