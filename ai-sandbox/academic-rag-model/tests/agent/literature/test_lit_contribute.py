import tempfile
import unittest

from agent.literature import contribute
from agent.literature.cluster import define_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS
from synth_helpers import F1, F2, PROV, _answer, build, three_papers


class TestAnnotateStage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        self.cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])

    def tasks(self, **kw):
        return contribute.make_tasks(self.target, self.cluster, self.papers, **kw)

    def test_one_card_per_cluster_paper_with_the_cited_pages_offered(self):
        tasks, skipped = self.tasks()
        self.assertEqual(sorted(t.subject["file_id"] for t in tasks), [F1, "c" * 16])
        t = tasks[0]
        self.assertEqual((t.stage, t.subject["topic"]), ("annotate", "demo"))
        refs = {p.ref for p in t.passages}
        self.assertIn("page 3", refs)
        self.assertIn("12%", t.context)
        self.assertNotIn(F2, {x.subject["file_id"] for x in tasks})

    def test_a_good_answer_is_accepted_and_written_under_the_topic(self):
        entry = task_entry(self.tasks()[0][0])
        self.assertEqual(contribute.validate_result(entry, _answer(), self.target), [])
        contribute.apply_result(self.target, entry, _answer(), PROV)
        notes = contribute.load_annotations(self.tmp.name, "demo")
        self.assertEqual(notes[entry["subject"]["file_id"]]["contribution"]["locator"], 3)
        self.assertEqual(notes[entry["subject"]["file_id"]]["run_id"], "r1")

    def test_a_quote_that_is_not_on_the_page_or_a_missing_part_bounces(self):
        entry = task_entry(self.tasks()[0][0])
        bad = _answer(contribution={"text": "It shows a large effect on everything measured.",
                                    "quote": "Transfers cured all poverty", "locator": 3})
        self.assertTrue(any("quote" in m for m in contribute.validate_result(entry, bad, self.target)))
        self.assertTrue(contribute.validate_result(entry, {"contribution": _answer()["contribution"]}, self.target))
        short = _answer(limitations={"text": "ok", "quote": "given attrition between survey waves", "locator": 4})
        self.assertTrue(any("text" in m for m in contribute.validate_result(entry, short, self.target)))

    def test_papers_already_annotated_are_skipped_unless_redo(self):
        entry = task_entry(self.tasks()[0][0])
        contribute.apply_result(self.target, entry, _answer(), PROV)
        tasks, skipped = self.tasks()
        self.assertEqual(len(tasks), 1)
        self.assertIn("already annotated", skipped[entry["subject"]["file_id"]])
        self.assertEqual(len(self.tasks(redo=True)[0]), 2)

    def test_a_result_quoted_across_pages_still_offers_its_pages(self):
        rec = self.target.records.read(F1, "a")
        rec["core"]["results"][0]["locator"] = [3, 4]
        rec["appraisal"]["locator"] = None
        self.target.records.write(rec, "a")
        tasks, skipped = self.tasks()
        t = next(x for x in tasks if x.subject["file_id"] == F1)
        self.assertEqual({p.ref for p in t.passages}, {"page 3", "page 4"})

    def test_limit_caps_the_cards_and_the_rest_stay_for_the_next_run(self):
        first = self.tasks(limit=1)[0]
        self.assertEqual(len(first), 1)
        contribute.apply_result(self.target, task_entry(first[0]), _answer(), PROV)
        second = self.tasks(limit=1)[0]
        self.assertEqual(len(second), 1)
        self.assertNotEqual(first[0].subject["file_id"], second[0].subject["file_id"])


if __name__ == "__main__":
    unittest.main()
