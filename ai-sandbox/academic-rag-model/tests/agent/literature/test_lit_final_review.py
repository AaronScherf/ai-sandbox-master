import tempfile
import unittest
from pathlib import Path

from agent.literature import stage, verify
from agent.literature.compare import reconcile
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from agent.literature.transcript import check_quote, normalize
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
FID = "0123456789abcdef"


class TestSignsSurviveNormalization(unittest.TestCase):
    PAGES = {1: "The estimated effect was -0.12 percentage points in treated districts, and 10-20 percent elsewhere."}

    def test_a_dropped_minus_sign_does_not_verify(self):
        self.assertIsNotNone(check_quote("The estimated effect was 0.12 percentage points", 1, self.PAGES))
        self.assertIsNone(check_quote("The estimated effect was -0.12 percentage points", 1, self.PAGES))

    def test_a_range_dash_is_kept_and_line_break_hyphenation_still_folds(self):
        self.assertIsNone(check_quote("and 10-20 percent elsewhere", 1, self.PAGES))
        self.assertIsNotNone(check_quote("and 1020 percent elsewhere", 1, self.PAGES))
        self.assertEqual(normalize("cash trans-\nfers"), normalize("cash transfers"))


def _env(root):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _apply(target, papers, result, label, **kw):
    tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True, **kw)
    stage.apply_result(target, task_entry(tasks[0]), result, PROV)


class TestStaleState(unittest.TestCase):
    def test_re_extracting_pass_a_keeps_a_verification_made_on_the_same_transcript(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            b = good()
            b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
            _apply(target, papers, good(), "a")
            _apply(target, papers, b, "b")
            tasks, _ = verify.make_tasks(target, papers)
            entry = task_entry(tasks[0])
            rows = [{"item": i["n"], "verdict": "unclear", "reason": "x"} for i in entry["subject"]["items"]]
            verify.apply_result(target, entry, {"verdicts": rows}, PROV)
            _apply(target, papers, good(), "a")
            self.assertIn("verification", target.records.read(FID, "a"))

    def test_passes_from_different_transcripts_are_flagged_not_compared(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _apply(target, papers, good(), "a")
            _apply(target, papers, good(), "b")
            rec = target.records.read(FID, "b")
            rec["transcript_sha"] = "0000000000000000"
            target.records.write(rec, "b")
            reconcile(target.records, FID, VOCABS)
            review = target.records.read(FID, "a")["review"]
        self.assertEqual(review["status"], "needs_review")
        self.assertTrue(any("different transcript" in m for m in review["items_flagged"]), review)


if __name__ == "__main__":
    unittest.main()
