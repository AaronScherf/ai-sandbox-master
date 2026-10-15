import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.atomic_io import write_json_atomic


class TestWriteJsonAtomic(unittest.TestCase):
    def test_writes_and_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "data.json"
            write_json_atomic(path, {"a": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            write_json_atomic(path, {"a": 1})
            write_json_atomic(path, {"a": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 2})

    def test_leaves_original_file_intact_if_dump_fails_midway(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            write_json_atomic(path, {"a": 1})

            with patch("discovery.discover_journal_articles.atomic_io.json.dump", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    write_json_atomic(path, {"a": 2})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1})
            # No leftover .tmp file in the directory.
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
