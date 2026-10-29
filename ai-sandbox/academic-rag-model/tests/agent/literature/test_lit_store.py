import json
import tempfile
import unittest

from agent.literature import schema
from agent.literature.store import RecordStore, check_file_id


class TestSchemaConstants(unittest.TestCase):
    def test_facets_map_to_vocabulary_names(self):
        self.assertEqual(
            schema.FACETS,
            {"intervention": "intervention", "outcome": "outcome", "study_design": "study_design",
             "sector": "sector", "population": "population", "data_sources": "data_source"},
        )

    def test_enums_and_limits(self):
        self.assertEqual(schema.EFFECT_DIRECTIONS, ("positive", "negative", "null", "mixed", "not_reported"))
        self.assertEqual(schema.CONFIDENCE, ("low", "medium", "high"))
        self.assertEqual((schema.MIN_QUOTE_CHARS, schema.MAX_QUOTE_CHARS), (8, 300))


class TestRecordStore(unittest.TestCase):
    def test_round_trip_keeps_non_ascii_and_uses_one_file_per_paper(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            rec = {"identity": {"file_id": "abc123", "title": "Élasticité β"}}
            path = s.write(rec)
            self.assertEqual(path.name, "abc123.json")
            self.assertEqual(s.read("abc123"), rec)
            self.assertIn("Élasticité", path.read_text(encoding="utf-8"))
            self.assertEqual(s.ids(), ["abc123"])

    def test_pass_b_is_a_separate_file_and_not_listed_as_a_paper(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            s.write({"identity": {"file_id": "abc123"}}, "a")
            s.write({"identity": {"file_id": "abc123"}, "marker": "b"}, "b")
            self.assertEqual(s.path("abc123", "b").name, "abc123.b.json")
            self.assertEqual(s.read("abc123", "b")["marker"], "b")
            self.assertEqual(s.ids(), ["abc123"])

    def test_excluded_ids_are_hidden_from_ids_but_not_all_ids(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            for fid in ("aaa", "bbb", "ccc"):
                s.write({"identity": {"file_id": fid}})
            self.assertEqual(s.excluded(), set())
            s.exclude(["bbb"])
            self.assertEqual(s.excluded(), {"bbb"})
            self.assertEqual(s.ids(), ["aaa", "ccc"])
            self.assertEqual(s.all_ids(), ["aaa", "bbb", "ccc"])
            self.assertIsNotNone(s.read("bbb"))

    def test_exclude_is_additive_validates_ids_and_can_be_undone(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            s.exclude(["aaa"])
            s.exclude(["bbb"])
            self.assertEqual(s.excluded(), {"aaa", "bbb"})
            with self.assertRaises(ValueError):
                s.exclude(["../x"])
            s.include(["aaa"])
            self.assertEqual(s.excluded(), {"bbb"})

    def test_missing_record_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(RecordStore(root).read("nope"))

    def test_file_id_may_not_carry_a_path(self):
        for bad in ("../x", "a/b", "a\\b", "", ".hidden", "a b"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    check_file_id(bad)

    def test_write_is_atomic_leaving_no_temp_file(self):
        with tempfile.TemporaryDirectory() as root:
            s = RecordStore(root)
            s.write({"identity": {"file_id": "abc123"}})
            self.assertEqual([p.name for p in s.dir.iterdir()], ["abc123.json"])


if __name__ == "__main__":
    unittest.main()
