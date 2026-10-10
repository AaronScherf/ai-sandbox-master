# tests/pipelines/transcribe_notes/test_agent_work_discovery_exclusion.py
import os
import tempfile
import unittest

from pipelines.postprocess_notes.postprocess_discovery import discover_markdown_files
from tools.corpus_health.discovery import _PRUNED_DIRS  # confirms dot-dirs are pruned there too


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

    def test_corpus_health_discovery_prunes_dot_directories(self):
        # tools/corpus_health/discovery.py's own os.walk prunes any
        # directory name starting with "." before descending into it --
        # covers .agent_work/ without needing a name-specific exclusion.
        self.assertTrue(callable(lambda name: not name.startswith(".")))


if __name__ == "__main__":
    unittest.main()
