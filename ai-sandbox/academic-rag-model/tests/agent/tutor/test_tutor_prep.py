import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from agent.tutor import prep
from agent.tutor.packet import is_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet

PS = "## Question 1\nFirst question text with $d$.\n\n## Question 2\nSecond question text.\n"


def _retrieve(query):
    return [SimpleNamespace(citation="p. 3", path="notes/a.md", score=0.81, text="line one\nline two")]


def _write_ps(tmp):
    psf = os.path.join(tmp, "homework_4.md")
    with open(psf, "w", encoding="utf-8") as f:
        f.write(PS)
    return psf


class TestCollect(unittest.TestCase):
    def test_writes_skeleton_grounding_and_worklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            psf = _write_ps(tmp)
            hints = os.path.join(tmp, "hints.md")
            with open(hints, "w", encoding="utf-8") as f:
                f.write("hint text")
            out = prep.collect(paths, psf, ["1", "2"], _retrieve, hints_file=hints)
            with open(os.path.join(paths.packet_dir, "parts.json"), encoding="utf-8") as f:
                parts = json.load(f)
            self.assertEqual([p["part_id"] for p in parts], ["q1", "q2"])
            self.assertIn("First question text", parts[0]["statement"])
            self.assertEqual(parts[0]["concept_tags"], [])
            with open(os.path.join(paths.packet_dir, "grounding.md"), encoding="utf-8") as f:
                grounding = f.read()
            self.assertIn("## q1", grounding)
            self.assertIn("p. 3", grounding)
            with open(os.path.join(paths.packet_dir, "sealed", "hints.md"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "hint text")
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "")
            self.assertTrue(os.path.exists(os.path.join(paths.packet_dir, "worklist.md")))
            self.assertFalse(out["validated"])

    def test_refuses_to_overwrite_existing_parts_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            psf = _write_ps(tmp)
            with self.assertRaises(FileExistsError):
                prep.collect(paths, psf, ["1"], _retrieve)
            prep.collect(paths, psf, ["1"], _retrieve, force=True)


class TestSubmit(unittest.TestCase):
    def test_skeleton_fails_validation_with_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            psf = _write_ps(tmp)
            prep.collect(paths, psf, ["1"], _retrieve)
            result = prep.submit(paths)
            self.assertFalse(result["ok"])
            self.assertTrue(result["errors"])
            self.assertFalse(is_validated(paths.packet_dir))

    def test_valid_packet_gets_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = TutorPaths(tmp, "microecon", "homework_4")
            write_sample_packet(paths)
            os.remove(os.path.join(paths.packet_dir, "validated.json"))
            self.assertEqual(prep.submit(paths), {"ok": True})
            self.assertTrue(is_validated(paths.packet_dir))
