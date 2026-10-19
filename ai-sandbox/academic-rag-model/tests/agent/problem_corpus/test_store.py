import os
import tempfile
import unittest
from unittest.mock import patch

from agent.problem_corpus.store import corpus_dir, corpus_path, load_records, save_file_records


def _record(file_id, record_id, topic="algebra"):
    return {
        "id": record_id, "course": "math-camp", "topic_tag": topic,
        "problem_text": "Find X.", "solution_text": None, "solution_provenance": None,
        "source": {
            "file_id": file_id, "path": "a.md", "root": "/x", "citation": "a.md, Problem 1",
            "folder_category": "problem_sets",
        },
        "content_hash": "h1", "extracted_at": "2026-09-06T00:00:00+00:00",
    }


class TestCorpusPaths(unittest.TestCase):
    def test_corpus_dir_lives_under_problem_corpus(self):
        self.assertEqual(corpus_dir("/root"), os.path.join("/root", ".problem_corpus"))

    def test_corpus_path_is_course_scoped_json(self):
        path = corpus_path("/root", "math-camp")
        self.assertEqual(path, os.path.join("/root", ".problem_corpus", "math-camp.json"))


class TestLoadRecords(unittest.TestCase):
    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_records(tmp, "math-camp"), [])


class TestSaveFileRecords(unittest.TestCase):
    def test_round_trips_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            records = load_records(tmp, "math-camp")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["id"], "id1")
            self.assertEqual(records[0]["topic_tag"], "algebra")

    def test_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            self.assertTrue(os.path.exists(corpus_path(tmp, "math-camp")))

    def test_replaces_only_the_target_files_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "math-camp", "bbb", [_record("bbb", "id2")])
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id3")])
            ids = {r["id"] for r in load_records(tmp, "math-camp")}
            self.assertEqual(ids, {"id2", "id3"})  # id1 was replaced by id3; id2 untouched

    def test_empty_records_list_removes_the_files_prior_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "math-camp", "aaa", [])
            self.assertEqual(load_records(tmp, "math-camp"), [])

    def test_other_courses_are_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            save_file_records(tmp, "econ-101", "bbb", [_record("bbb", "id2")])
            self.assertEqual(len(load_records(tmp, "math-camp")), 1)
            self.assertEqual(len(load_records(tmp, "econ-101")), 1)

    def test_failed_write_preserves_previous_course_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id1")])
            with open(corpus_path(tmp, "math-camp"), "rb") as f:
                original = f.read()
            with patch("agent.problem_corpus.store.json.dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_file_records(tmp, "math-camp", "aaa", [_record("aaa", "id2")])
            with open(corpus_path(tmp, "math-camp"), "rb") as f:
                self.assertEqual(f.read(), original)
            self.assertEqual(os.listdir(corpus_dir(tmp)), ["math-camp.json"])


if __name__ == "__main__":
    unittest.main()
