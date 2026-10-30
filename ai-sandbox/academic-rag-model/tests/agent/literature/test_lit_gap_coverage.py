import os
import tempfile
import time
import unittest
from pathlib import Path

from agent.literature import db
from agent.literature.gap.classify import classify
from agent.literature.gap.coverage import COMPLETENESS, Sidecar, coverage, read_sidecar
from agent.literature.gap.match import Constraint
from agent.literature.gap.subregions import load_subregions
from gap_helpers import VOCABS, fx, make_corpus, write_toy_tables
from synth_helpers import F1, F2, F3, build, three_papers


def sidecar(**over):
    base = dict(eligible=5, excluded=1, without_record=2, open_tier_c=7, db_stale=False, db_path="db.sqlite",
                db_mtime=1.0, db_papers=3, scales={})
    return Sidecar(**{**base, **over})


class TestCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.toy = load_subregions(*write_toy_tables(tmp))

    def cover(self, papers, constraints, **side):
        corpus = make_corpus(papers)
        result = classify(corpus, constraints, VOCABS, self.toy)
        return coverage(corpus, result, constraints, sidecar(**side)), result

    def test_counts_and_distributions_over_direct_plus_adjacent(self):
        cov, result = self.cover({
            "p1": {"year": 2018, "facts": [fx("intervention", "i.cash_uncond"), fx("countries", "SO"), fx("study_design", "d.panel")],
                   "results": [("up", "positive")]},
            "p2": {"year": 2020, "facts": [fx("intervention", "i.cash"), fx("countries", "KE"), fx("study_design", "d.rct")],
                   "results": [("flat", "null")]},
            "p3": {"year": 2010, "facts": [fx("intervention", "i.voucher"), fx("countries", "NG")]},
        }, [Constraint("intervention", "i.cash"), Constraint("countries", "SO")])
        self.assertEqual((result.direct, list(result.adjacent)), (["p1"], ["p2"]))
        self.assertEqual((cov["eligible"], cov["excluded"], cov["without_record"], cov["open_tier_c"]), (5, 1, 2, 7))
        self.assertEqual(cov["designs"], {"Panel": 1, "Randomised trial": 1})
        self.assertEqual(cov["countries"], {"SO": 1, "KE": 1})
        self.assertEqual(cov["year_range"], [2018, 2020])
        self.assertEqual(cov["result_directions"], {"positive": 1, "null": 1})
        self.assertEqual(cov["db"], {"path": "db.sqlite", "mtime": 1.0, "papers": 3, "stale": False})

    def test_thin_flag_at_two_and_three_direct_papers(self):
        def papers(n):
            return {f"p{i}": {"facts": [fx("outcome", "o.food_cons")]} for i in range(n)}
        c = [Constraint("outcome", "o.food_cons")]
        self.assertTrue(self.cover(papers(2), c)[0]["thin"])
        self.assertFalse(self.cover(papers(3), c)[0]["thin"])

    def test_completeness_line_is_always_present(self):
        cov, _ = self.cover({"p1": {"facts": [fx("outcome", "o.health")]}}, [Constraint("outcome", "o.food_cons")])
        self.assertEqual(cov["completeness"], COMPLETENESS)
        self.assertTrue(COMPLETENESS.startswith("Corpus completeness: not measured (needs OpenAlex, slice 2)."))

    def test_blind_spot_proposed_fact_listed_not_counted_in_verdict(self):
        cov, result = self.cover({
            "direct": {"facts": [fx("intervention", "i.cash")]},
            "label-match": {"facts": [fx("intervention", "proposed:cash transfers")]},
            "other": {"facts": [fx("intervention", "proposed:school meals")]},
        }, [Constraint("intervention", "i.cash")])
        self.assertEqual(result.direct, ["direct", "label-match"])
        self.assertEqual(cov["blind_spots"]["proposed"], {"intervention": ["other"]})

    def test_blind_spot_no_country_and_broad_scale_only_with_a_country_constraint(self):
        papers = {"p1": {"facts": [fx("countries", "SO")]}, "p2": {"facts": [fx("outcome", "o.health")]},
                  "p3": {"facts": [fx("outcome", "o.health"), fx("countries", "NG")]}}
        scales = {"p1": "national", "p2": "global", "p3": "multi_country"}
        cov, _ = self.cover(papers, [Constraint("countries", "SO")], scales=scales)
        self.assertEqual(cov["blind_spots"]["no_country_fact"], ["p2"])
        self.assertEqual(cov["blind_spots"]["broad_scale"], ["p2", "p3"])
        cov, _ = self.cover(papers, [Constraint("outcome", "o.health")], scales=scales)
        self.assertNotIn("no_country_fact", cov["blind_spots"])
        self.assertNotIn("broad_scale", cov["blind_spots"])

    def test_empty_corpus_gives_zero_counts_and_no_evidence(self):
        cov, result = self.cover({}, [Constraint("outcome", "o.food_cons")], eligible=0, excluded=0, without_record=0,
                                 open_tier_c=0, db_papers=0)
        self.assertEqual(result.verdict, "no_evidence_in_corpus")
        self.assertEqual((cov["designs"], cov["countries"], cov["year_range"], cov["result_directions"]), ({}, {}, None, {}))
        self.assertTrue(cov["thin"])


class TestReadSidecar(unittest.TestCase):
    def test_counts_with_a_built_target_and_stale_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, _ = build(tmp, three_papers())
            target.records.exclude([F3])
            path = db.db_path(tmp)
            db.build(target, path)
            side = read_sidecar(target, tmp, path)
            self.assertEqual((side.eligible, side.excluded, side.without_record, side.open_tier_c), (3, 1, 0, 0))
            self.assertEqual(side.scales, {F1: "subnational", F2: "subnational"})
            self.assertEqual((side.db_papers, side.db_stale), (2, False))
            later = time.time() + 100
            os.utime(Path(target.records.dir) / f"{F1}.json", (later, later))
            self.assertTrue(read_sidecar(target, tmp, path).db_stale)


if __name__ == "__main__":
    unittest.main()
