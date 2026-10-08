import json
import os
import tempfile
import unittest

from agent.tutor.packet import (
    LAUNCH_SUFFIX, PacketError, is_validated, load_packet, sealed_section, validate_packet, write_validated,
)
from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet


def _paths(tmp):
    return TutorPaths(tmp, "microecon", "homework_4")


class TestSealedSection(unittest.TestCase):
    def test_extracts_section_by_part_id(self):
        md = "## q1\nfirst\nmore\n## q2\nsecond\n"
        self.assertEqual(sealed_section(md, "q1"), "first\nmore")
        self.assertEqual(sealed_section(md, "q2"), "second")
        self.assertIsNone(sealed_section(md, "q3"))

    def test_part_id_with_regex_characters(self):
        self.assertEqual(sealed_section("## q1.2\nbody", "q1.2"), "body")
        self.assertIsNone(sealed_section("## q1x2\nbody", "q1.2"))


class TestSamplePacket(unittest.TestCase):
    def test_sample_is_valid_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertEqual(validate_packet(paths.packet_dir), [])
            packet = load_packet(paths)
            self.assertEqual([p.part_id for p in packet.parts], ["q1", "q2"])
            self.assertTrue(packet.parts[0].launch_text().endswith(LAUNCH_SUFFIX))


class TestValidation(unittest.TestCase):
    def _edit_json(self, paths, name, fn):
        path = os.path.join(paths.packet_dir, name)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        fn(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_reports_each_kind_of_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self._edit_json(paths, "parts.json", lambda d: d[0].update(concept_tags=[], expected_evidence=[]))
            self._edit_json(paths, "rubric.json", lambda d: d["q2"]["rigor"].pop("Mastered"))
            self._edit_json(paths, "glossary.json", lambda d: d.update({"choice overload": "Means d is chosen more."}))
            with open(os.path.join(paths.packet_dir, "sealed", "solution.md"), "w", encoding="utf-8") as f:
                f.write("## q1\nonly q1\n")
            errors = "\n".join(validate_packet(paths.packet_dir))
            self.assertIn("q1: concept_tags", errors)
            self.assertIn("q1: expected_evidence", errors)
            self.assertIn("rubric q2.rigor missing 'Mastered'", errors)
            self.assertIn("GLOSSARY_NOTATION", errors)
            self.assertIn("sealed/solution.md has no '## q2' section", errors)

    def test_missing_files_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(_paths(tmp).packet_dir)
            self.assertIn("parts.json missing", validate_packet(_paths(tmp).packet_dir))


class TestValidatedMarker(unittest.TestCase):
    def test_edit_after_validation_invalidates_until_resubmitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            self.assertTrue(is_validated(paths.packet_dir))
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "a", encoding="utf-8") as f:
                f.write("\nhuman tweak\n")
            self.assertFalse(is_validated(paths.packet_dir))
            with self.assertRaises(PacketError) as ctx:
                load_packet(paths)
            self.assertIn("prep-submit", str(ctx.exception))
            write_validated(paths.packet_dir)
            load_packet(paths)

    def test_crlf_conversion_does_not_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(tmp)
            write_sample_packet(paths)
            sol = os.path.join(paths.packet_dir, "sealed", "solution.md")
            with open(sol, "rb") as f:
                raw = f.read()
            with open(sol, "wb") as f:
                f.write(raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertTrue(is_validated(paths.packet_dir))
