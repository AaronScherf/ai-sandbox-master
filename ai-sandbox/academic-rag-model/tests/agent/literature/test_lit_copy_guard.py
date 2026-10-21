import tempfile
import unittest
from pathlib import Path

from agent.literature import stage
from agent.literature.compare import copy_ratio, reconcile
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index, rewritten

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
FID = "0123456789abcdef"


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


class TestCopyRatio(unittest.TestCase):
    def test_identical_passes_score_one_and_rewritten_support_scores_low(self):
        self.assertEqual(copy_ratio(_record(good()), _record(good())), 1.0)
        self.assertLess(copy_ratio(_record(good()), _record(rewritten())), 0.5)


def _env(root):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _apply(target, papers, result, label):
    tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
    stage.apply_result(target, task_entry(tasks[0]), result, PROV)


class TestReconcileFlagsCopies(unittest.TestCase):
    def test_a_pass_b_that_repeats_pass_a_quote_for_quote_is_flagged_even_when_the_facts_agree(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, good(), "b")
            review = target.records.read(FID, "a")["review"]
        self.assertEqual(review["status"], "needs_review")
        self.assertTrue(any("not be independent" in m for m in review["items_flagged"]), review)

    def test_independently_supported_agreement_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, rewritten(), "b")
            review = target.records.read(FID, "a")["review"]
        self.assertEqual(review, {"status": "unreviewed", "items_flagged": [], "double_pass": "agreed"})

    def test_a_human_review_still_wins(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, good(), "b")
            rec = target.records.read(FID, "a")
            rec["review"] = {"status": "accepted", "items_flagged": []}
            target.records.write(rec, "a")
            reconcile(target.records, FID, VOCABS)
            self.assertEqual(target.records.read(FID, "a")["review"]["status"], "accepted")


if __name__ == "__main__":
    unittest.main()


class TestStatusReportsCopies(unittest.TestCase):
    def test_status_counts_pairs_that_may_not_be_independent(self):
        import contextlib
        import io

        from agent.literature import cli
        from lit_helpers import write_vocab_dir

        with tempfile.TemporaryDirectory() as root:
            vocabs = str(Path(root) / "vocabs")
            Path(vocabs).mkdir()
            write_vocab_dir(vocabs)
            target, papers = _env(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, good(), "b")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                cli.main(["--index-root", root, "--vocab-dir", vocabs, "status"])
        self.assertIn("pairs that may not be independent: 1", out.getvalue())
