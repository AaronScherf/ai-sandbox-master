import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.note_indexing import index_group_note, write_group_note


class TestWriteGroupNote(unittest.TestCase):
    def test_writes_markdown_and_sidecar_under_lecture_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rel_md, rel_meta = write_group_note(tmp, "math-camp", "real-analysis", "# Notes", {"member_video_ids": ["A"]})
            self.assertEqual(rel_md, "academic_notes/math-camp/lecture-notes/real-analysis.md")
            self.assertEqual(rel_meta, "academic_notes/math-camp/lecture-notes/real-analysis.meta.json")
            with open(os.path.join(tmp, rel_md), "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "# Notes")
            with open(os.path.join(tmp, rel_meta), "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"member_video_ids": ["A"]})


class TestIndexGroupNote(unittest.TestCase):
    @patch("video_notes.note_indexing.reconcile_and_write")
    def test_calls_reconcile_and_write_with_group_identity_file_id(self, mock_reconcile):
        mock_reconcile.return_value = {"file_id": "x"}
        with tempfile.TemporaryDirectory() as tmp:
            rel_md, rel_meta = write_group_note(tmp, "math-camp", "real-analysis", "# Notes", {"member_video_ids": ["A", "B"]})
            result = index_group_note(tmp, "math-camp", ["A", "B"], rel_md, rel_meta, MagicMock())
            self.assertEqual(result, {"file_id": "x"})
            _, kwargs = mock_reconcile.call_args
            self.assertEqual(kwargs["folder_category"], "lecture-notes")
            self.assertEqual(kwargs["content_sample"], "# Notes")
            self.assertEqual(kwargs["path"], rel_md)
            self.assertEqual(kwargs["source_pdf_path"], rel_meta)
