import copy
import tempfile
import unittest
from pathlib import Path

from agent.literature import stage
from agent.literature.compare import diff_records, reconcile
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index, rewritten

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


class TestDiff(unittest.TestCase):
    def test_identical_records_agree(self):
        self.assertEqual(diff_records(_record(good()), _record(good())), [])

    def test_a_missing_or_different_fact_is_reported_with_both_sides(self):
        b = good()
        b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
        msgs = diff_records(_record(good()), _record(b))
        self.assertEqual(len(msgs), 1)
        self.assertIn("core.intervention", msgs[0])
        self.assertIn("intervention.cash_transfer", msgs[0])
        self.assertIn("intervention.voucher", msgs[0])

    def test_proposed_and_vocabulary_versions_of_a_fact_are_different_identities(self):
        b = good()
        b["core"]["study_design"] = [{"value": "panel", "proposed": True, "quote": "using a panel of 1,200 households", "locator": 1}]
        self.assertTrue(any("core.study_design" in m for m in diff_records(_record(good()), _record(b))))

    def test_two_correct_quotes_for_one_fact_are_not_a_disagreement(self):
        b = good()
        b["core"]["outcome"][0]["quote"] = "food consumption by twelve percent"
        b["core"]["outcome"][0]["locator"] = [3]
        self.assertEqual(diff_records(_record(good()), _record(b)), [])

    def test_geography_results_and_appraisal(self):
        b = good()
        b["core"]["geography"]["countries"] = ["SO", "ET"]
        b["core"]["results"][0]["effect_direction"] = "negative"
        b["appraisal"]["confidence"] = "high"
        text = " | ".join(diff_records(_record(good()), _record(b)))
        for needle in ("geography.countries", "core.results", "appraisal.confidence"):
            self.assertIn(needle, text)


def _setup(root):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _apply(target, papers, result, label):
    tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
    stage.apply_result(target, task_entry(tasks[0]), result, PROV)


def _different():
    b = good()
    b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
    return b


class TestReconcile(unittest.TestCase):
    def test_disagreement_is_flagged_on_pass_a_in_either_order(self):
        flagged = []
        for order in (("a", "b"), ("b", "a")):
            with tempfile.TemporaryDirectory() as root:
                target, papers = _setup(root)
                for label in order:
                    _apply(target, papers, good() if label == "a" else _different(), label)
                review = target.records.read("0123456789abcdef", "a")["review"]
                self.assertEqual(review["status"], "needs_review")
                flagged.append(review["items_flagged"])
        self.assertEqual(flagged[0], flagged[1])

    def test_agreement_is_recorded_and_leaves_status_alone(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, rewritten(), "b")
            review = target.records.read("0123456789abcdef", "a")["review"]
        self.assertEqual(review, {"status": "unreviewed", "items_flagged": [], "double_pass": "agreed"})

    def test_one_pass_only_changes_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["review"],
                             {"status": "unreviewed", "items_flagged": []})

    def test_reconcile_is_idempotent_and_never_touches_pass_b(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, _different(), "b")
            path_b = target.records.path("0123456789abcdef", "b")
            before_a, before_b = target.records.path("0123456789abcdef", "a").read_bytes(), path_b.read_bytes()
            reconcile(target.records, "0123456789abcdef")
            self.assertEqual(target.records.path("0123456789abcdef", "a").read_bytes(), before_a)
            self.assertEqual(path_b.read_bytes(), before_b)

    def test_a_human_review_is_never_overridden(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, _different(), "b")
            rec = target.records.read("0123456789abcdef", "a")
            rec["review"] = {"status": "accepted", "items_flagged": []}
            target.records.write(rec, "a")
            reconcile(target.records, "0123456789abcdef")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["review"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
