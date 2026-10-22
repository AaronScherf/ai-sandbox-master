import tempfile
import unittest

from agent.literature.cluster import (ClusterError, define_cluster, load_cluster, parse_constraint,
                                      save_cluster, topic_dir)
from lit_helpers import VOCABS
from synth_helpers import F1, F2, F3, build, three_papers


class TestCluster(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, _ = build(self.tmp.name, three_papers())

    def define(self, *where, floor="B"):
        return define_cluster(self.target.records, VOCABS, "demo", list(where), floor)

    def test_papers_join_when_every_constraint_matches_a_tier_a_or_b_fact(self):
        self.assertEqual(self.define("sector=social protection").file_ids, [F1, F3])
        self.assertEqual(self.define("intervention=voucher").file_ids, [F2])
        self.assertEqual(self.define("sector=social protection", "intervention=cash transfer").file_ids, [F1, F3])
        self.assertEqual(self.define("sector=social protection", "intervention=voucher").file_ids, [])

    def test_a_term_id_and_a_country_code_work_as_values(self):
        self.assertEqual(self.define("sector=sector.social_protection").file_ids, [F1, F3])
        self.assertEqual(self.define("countries=so").file_ids, [F1, F2, F3])

    def test_an_unknown_facet_or_term_fails_loudly(self):
        with self.assertRaises(ClusterError):
            parse_constraint("colour=blue")
        with self.assertRaises(ClusterError):
            self.define("sector=no such sector")
        with self.assertRaises(ClusterError):
            define_cluster(self.target.records, VOCABS, "demo", [])

    def test_a_bad_topic_name_is_refused(self):
        with self.assertRaises(ClusterError):
            define_cluster(self.target.records, VOCABS, "../x", ["countries=SO"])

    def test_a_cluster_round_trips_through_cluster_yaml(self):
        cluster = self.define("sector=social protection")
        path = save_cluster(self.tmp.name, cluster)
        self.assertEqual(path, topic_dir(self.tmp.name, "demo") / "cluster.yaml")
        self.assertEqual(load_cluster(self.tmp.name, "demo"), cluster)


if __name__ == "__main__":
    unittest.main()
