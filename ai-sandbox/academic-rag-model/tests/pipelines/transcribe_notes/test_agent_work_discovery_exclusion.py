# tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py
import os
import tempfile
import unittest
from pathlib import Path

from pipelines.postprocess_notes.postprocess_discovery import discover_markdown_files
from tools.corpus_health.discovery import _walk_files


class TestAgentWorkNotDiscovered(unittest.TestCase):
    def test_discover_markdown_files_ignores_dot_agent_work(self):
        with tempfile.TemporaryDirectory() as hub:
            agent_work_md = os.path.join(hub, ".agent_work", "run-1", "doc", "task-0001.md")
            os.makedirs(os.path.dirname(agent_work_md))
            with open(agent_work_md, "w", encoding="utf-8") as f:
                f.write("not a real transcription")
            # discover_markdown_files only walks processed_outputs/ directories
            # by basename -- a .agent_work/ tree is never under one.
            found = discover_markdown_files([hub])
            self.assertEqual(found, [])

    def test_corpus_health_discovery_prunes_dot_agent_work(self):
        # Final review I8: the previous version of this test asserted
        # callable(lambda ...), which is always true and never actually
        # called into tools.corpus_health.discovery -- it verified
        # nothing. This calls the real _walk_files() the way scan() does.
        with tempfile.TemporaryDirectory() as hub:
            agent_work_md = os.path.join(hub, ".agent_work", "run-1", "doc", "task-0001.md")
            os.makedirs(os.path.dirname(agent_work_md))
            with open(agent_work_md, "w", encoding="utf-8") as f:
                f.write("not a real transcription")
            real_md = os.path.join(hub, "course", "notes.md")
            os.makedirs(os.path.dirname(real_md))
            with open(real_md, "w", encoding="utf-8") as f:
                f.write("a real note")

            found = _walk_files(Path(hub), on_error=lambda msg: self.fail(msg))

            self.assertIn(Path(real_md), found)
            self.assertNotIn(Path(agent_work_md), found)
            self.assertFalse(any(".agent_work" in p.parts for p in found))


if __name__ == "__main__":
    unittest.main()
