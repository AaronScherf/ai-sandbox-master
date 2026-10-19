import tempfile
import unittest
from pathlib import Path

from agent.literature.vocab import load_vocabularies

FACET_VOCABS = {"intervention", "outcome", "sector", "study_design", "population", "data_source", "hazard_type"}


class TestOverlay(unittest.TestCase):
    def test_the_committed_provisional_lists_load_by_default_and_a_directory_overlays_them(self):
        base = load_vocabularies()
        self.assertTrue({"study_design", "population", "data_source", "hazard_type"} <= set(base))
        self.assertTrue(all(base[n].provenance == "provisional" for n in ("study_design", "population")))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "sector.yaml").write_text(
                "vocabulary: sector\nversion: 3\nprovenance: 3ie\nsource: test\nterms:\n"
                "  - {id: sector.health, label: Health}\n", encoding="utf-8")
            merged = load_vocabularies(d)
        self.assertEqual(merged["sector"].version, 3)
        self.assertTrue({"study_design", "population", "data_source", "hazard_type"} <= set(merged))


if __name__ == "__main__":
    unittest.main()


class TestDataSourceTerms(unittest.TestCase):
    def test_administrative_records_is_told_apart_from_published_statistics(self):
        from agent.literature.vocab import load_vocabularies
        ds = load_vocabularies()["data_source"]
        self.assertEqual(ds.version, 2)
        for tid in ("data_source.administrative_records", "data_source.government_statistics"):
            self.assertTrue(ds.terms[tid].definition, tid)
        self.assertIn("aggregate", ds.terms["data_source.government_statistics"].definition)
