import tempfile
import unittest

from agent.literature import contribute, synth
from agent.literature.cluster import define_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS
from synth_helpers import F1, F3, PROV, _answer, build, three_papers


def _doc(*cites, text="Transfers raised food consumption by 12% in treated districts."):
    return {"sections": [{"heading": "Findings", "paragraphs": [{"text": text, "cites": list(cites)}]}]}


class TestSynthCards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])

    def annotate_all(self):
        tasks, _ = contribute.make_tasks(self.target, self.cluster, self.papers)
        for t in tasks:
            contribute.apply_result(self.target, task_entry(t), _answer(), PROV)

    def test_synthesis_refuses_until_every_paper_is_annotated(self):
        with self.assertRaises(ValueError) as ctx:
            synth.make_tasks(self.target, self.cluster)
        self.assertIn(F1, str(ctx.exception))

    def test_a_small_cluster_gets_one_final_card_listing_papers_results_and_notes(self):
        self.annotate_all()
        tasks, _ = synth.make_tasks(self.target, self.cluster)
        self.assertEqual([t.id for t in tasks], ["synth-final"])
        t = tasks[0]
        self.assertIn("P1.R1", t.context)
        self.assertIn("attrition", t.context)
        self.assertEqual(sorted(t.subject["allowed"]), ["P1", "P2"])
        self.assertEqual(t.subject["must_cover"], ["P1", "P2"])

    def test_a_good_answer_is_applied_and_a_bad_one_bounces(self):
        self.annotate_all()
        entry = task_entry(synth.make_tasks(self.target, self.cluster)[0][0])
        self.assertTrue(synth.validate_result(entry, _doc("P1.R1"), self.target))  # P2 not cited
        good = {"sections": [{"heading": "Findings", "paragraphs": [
            {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]}
        self.assertEqual(synth.validate_result(entry, good, self.target), [])
        synth.apply_result(self.target, entry, good, PROV)
        self.assertEqual(synth.load_outputs(self.tmp.name, "demo")["synth-final"]["sections"], good["sections"])

    def test_a_large_cluster_is_chunked_then_merged(self):
        self.annotate_all()
        tasks, _ = synth.make_tasks(self.target, self.cluster, max_papers=1)
        self.assertEqual([t.id for t in tasks], ["synth-c1", "synth-c2"])
        with self.assertRaises(ValueError):
            synth.make_tasks(self.target, self.cluster, max_papers=1, merge=True)  # chunks not answered yet
        for t in tasks:
            pid = t.subject["must_cover"][0]
            synth.apply_result(self.target, task_entry(t), _doc(f"{pid}.R1"), PROV)
        merge, _ = synth.make_tasks(self.target, self.cluster, max_papers=1, merge=True)
        self.assertEqual([t.id for t in merge], ["synth-final"])
        self.assertIn("12%", merge[0].context)
        self.assertEqual(merge[0].subject["must_cover"], ["P1", "P2"])


if __name__ == "__main__":
    unittest.main()
