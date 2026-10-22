import tempfile
import unittest

from agent.literature import contribute, review, synth
from agent.literature.cluster import define_cluster, save_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS
from synth_helpers import PROV, _answer, build, three_papers


class TestRender(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])
        save_cluster(self.tmp.name, self.cluster)

    def annotate(self):
        for t in contribute.make_tasks(self.target, self.cluster, self.papers)[0]:
            contribute.apply_result(self.target, task_entry(t), _answer(), PROV)

    def finish(self):
        self.annotate()
        entry = task_entry(synth.make_tasks(self.target, self.cluster)[0][0])
        doc = {"sections": [{"heading": "Findings", "paragraphs": [
            {"text": "Transfers raised food consumption by 12% in treated districts.", "cites": ["P1.R1", "P2.R1"]}]}]}
        synth.apply_result(self.target, entry, doc, PROV)

    def test_render_refuses_without_a_final_synthesis(self):
        self.annotate()
        with self.assertRaises(ValueError) as ctx:
            review.render(self.target, "demo")
        self.assertIn("synth-final", str(ctx.exception))

    def test_review_cites_by_key_and_bibliography_has_every_paper(self):
        self.finish()
        review_path, bib_path = review.render(self.target, "demo")
        text, bib = review_path.read_text(encoding="utf-8"), bib_path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("tags: [literature-review]", text)
        self.assertIn("12%", text)
        self.assertIn("](bibliography.md#", text)
        self.assertNotIn("P1.R1", text)
        self.assertEqual(bib.count("\n## "), 2)
        self.assertIn("attrition", bib)
        self.assertIn("12%", bib)

    def test_rendering_twice_gives_the_same_files(self):
        self.finish()
        first = [p.read_text(encoding="utf-8") for p in review.render(self.target, "demo")]
        second = [p.read_text(encoding="utf-8") for p in review.render(self.target, "demo")]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
