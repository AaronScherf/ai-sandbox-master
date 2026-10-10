# tests/pipelines/transcribe_notes/test_agent_work.py
import json
import os
import tempfile
import unittest

from pipelines.transcribe_notes.agent_work import (
    ManifestEntry,
    agent_work_dir,
    doc_slug_for,
    doc_work_dir,
    dedupe_by_file_id,
    load_manifest,
    render_worklist,
    save_manifest,
)


class TestLayout(unittest.TestCase):
    def test_agent_work_dir_is_under_hub_root_dot_agent_work(self):
        path = agent_work_dir("/hub", "run-1")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1"))

    def test_doc_slug_combines_basename_and_file_id_prefix(self):
        slug = doc_slug_for("/hub/academic_resources/microecon/foo bar.pdf", "abcdef1234567890")
        self.assertTrue(slug.startswith("foo_bar"))
        self.assertIn("abcdef12", slug)
        self.assertNotIn(" ", slug)

    def test_doc_work_dir_nests_under_run(self):
        path = doc_work_dir("/hub", "run-1", "foo--abcdef12")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1", "foo--abcdef12"))


class TestManifest(unittest.TestCase):
    def test_round_trips_entries(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="pending", bounce_reason=None),
            ]
            save_manifest(doc_dir, entries)
            loaded = load_manifest(doc_dir)
            self.assertEqual(loaded, entries)

    def test_load_manifest_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            self.assertEqual(load_manifest(doc_dir), [])

    def test_render_worklist_writes_human_readable_file(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="submitted", bounce_reason=None),
                ManifestEntry(task_id="task-0002", tier="hybrid", pages=[4, 5], status="bounced", bounce_reason="missing page 5"),
            ]
            render_worklist(doc_dir, entries)
            with open(os.path.join(doc_dir, "worklist.md"), encoding="utf-8") as f:
                content = f.read()
            self.assertIn("task-0001", content)
            self.assertIn("submitted", content)
            self.assertIn("missing page 5", content)


class TestDedupe(unittest.TestCase):
    def test_duplicate_pdfs_collapse_to_one_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            c = os.path.join(tmp, "c.pdf")
            with open(a, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(b, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(c, "wb") as f:
                f.write(b"%PDF-1.4 different content")
            canonical, duplicates_of = dedupe_by_file_id([a, b, c])
            self.assertEqual(len(canonical), 2)
            self.assertIn(a, canonical)
            self.assertIn(c, canonical)
            self.assertEqual(duplicates_of[a], [b])


if __name__ == "__main__":
    unittest.main()
