import tempfile
import unittest
from pathlib import Path

import yaml

from agent.literature.gold import load_gold, score_record, summarize
from lit_helpers import VOCABS


def _record(**facets):
    core = {"intervention": [], "outcome": [], "study_design": [], "sector": [], "population": [], "data_sources": [],
            "geography": {"countries": [], "regions": [], "scale": "not_stated"}, "results": []}
    core.update(facets)
    return {"core": core, "appraisal": {}}


def _gold(tmp, papers, version=1):
    p = Path(tmp) / "gold_set.yaml"
    p.write_text(yaml.safe_dump({"version": version, "papers": papers}), encoding="utf-8")
    return p


class TestLoad(unittest.TestCase):
    def test_a_good_file_loads(self):
        with tempfile.TemporaryDirectory() as d:
            papers = load_gold(_gold(d, [{"file_id": "abc", "expect": {"countries": ["SO"]}}]))
        self.assertEqual(papers[0]["file_id"], "abc")

    def test_every_problem_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as ctx:
                load_gold(_gold(d, [{"expect": {"colour": ["red"]}}, {"file_id": "x", "expect": {"countries": "SO"}}], version=2))
        text = str(ctx.exception)
        for needle in ("version", "file_id", "colour", "countries"):
            self.assertIn(needle, text)


class TestScore(unittest.TestCase):
    def test_matches_by_vocab_id_label_and_proposed_value(self):
        rec = _record(
            study_design=[{"value": "panel", "vocab_id": "study_design.panel"}],
            data_sources=[{"value": "FSNAU", "vocab_id": "data_source.fsnau"}, {"value": "ACLED", "proposed": True}],
            geography={"countries": ["SO"], "regions": [], "scale": "national"})
        expect = {"study_design": ["study_design.panel"], "data_sources": ["FSNAU", "acled"], "countries": ["SO"]}
        s = score_record(rec, expect, VOCABS)
        self.assertEqual(s["study_design"], {"expected": 1, "found": 1, "matched": 1})
        self.assertEqual(s["data_sources"], {"expected": 2, "found": 2, "matched": 2})
        self.assertEqual(s["countries"], {"expected": 1, "found": 1, "matched": 1})

    def test_extra_and_missing_items_lower_precision_and_recall_counts(self):
        rec = _record(study_design=[{"value": "panel", "vocab_id": "study_design.panel"},
                                    {"value": "rct", "proposed": True}])
        s = score_record(rec, {"study_design": ["study_design.panel", "did"]}, VOCABS)
        self.assertEqual(s["study_design"], {"expected": 2, "found": 2, "matched": 1})


class TestSummarize(unittest.TestCase):
    def test_micro_averages_and_missing_records(self):
        per = {"a": {"study_design": {"expected": 2, "found": 2, "matched": 1}},
               "b": None}  # no record for paper b
        expects = {"a": {"study_design": ["x", "y"]}, "b": {"study_design": ["z"]}}
        s = summarize(per, expects=expects, proposals=[{}, {}], records=1,
                      manifests=[{"tasks": [{"attempts": 0}, {"attempts": 2}]}],
                      double={"compared": 2, "agreed": 1})
        self.assertAlmostEqual(s["facet_precision"], 1 / 2)
        self.assertAlmostEqual(s["facet_recall"], 1 / 3)
        self.assertEqual(s["proposal_rate"], 2.0)
        self.assertEqual(s["bounce_rate"], 0.5)
        self.assertEqual(s["double_pass_agreement"], 0.5)
        self.assertEqual(s["papers_missing_a_record"], ["b"])

    def test_empty_inputs_do_not_crash(self):
        s = summarize({}, expects={}, proposals=[], records=0, manifests=[], double={"compared": 0, "agreed": 0})
        self.assertEqual((s["facet_precision"], s["facet_recall"], s["proposal_rate"], s["bounce_rate"]), (0.0, 0.0, 0.0, 0.0))
        self.assertIsNone(s["double_pass_agreement"])


if __name__ == "__main__":
    unittest.main()
