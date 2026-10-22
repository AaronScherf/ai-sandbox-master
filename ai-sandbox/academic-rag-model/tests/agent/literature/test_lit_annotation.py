import tempfile
import unittest

from agent.literature.annotation import annotation_of, cite_keys, render_annotation_md
from lit_helpers import VOCABS
from synth_helpers import F1, F2, build, three_papers


class TestAnnotation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, _ = build(self.tmp.name, three_papers())

    def test_annotation_lists_tier_a_b_facts_and_numbered_results(self):
        ann = annotation_of(self.target.records, F1, VOCABS)
        self.assertEqual(ann["file_id"], F1)
        self.assertTrue(all(f["tier"] in "AB" for fs in ann["facts"].values() for f in fs))
        self.assertEqual([r["id"] for r in ann["results"]], ["R1"])
        self.assertEqual(ann["results"][0]["magnitude"], "12%")
        self.assertIn("intervention", ann["facts"])

    def test_the_markdown_names_each_result_with_the_label_given(self):
        ann = annotation_of(self.target.records, F1, VOCABS)
        text = render_annotation_md(ann, "P1")
        self.assertIn("P1.R1", text)
        self.assertIn("12%", text)
        self.assertIn("cash transfer", text.lower())

    def test_same_title_and_year_still_get_different_keys(self):
        ids = {F1: {"title": "Cash transfers in Somalia: an evaluation", "publication_year": 2019},
               F2: {"title": "Cash transfers in Somalia: an evaluation", "publication_year": 2019}}
        keys = cite_keys(ids)
        self.assertEqual(len(set(keys.values())), 2)
        self.assertTrue(all("2019" in k for k in keys.values()))
        self.assertEqual(keys[F1], "Cash transfers in Somalia 2019")


if __name__ == "__main__":
    unittest.main()
