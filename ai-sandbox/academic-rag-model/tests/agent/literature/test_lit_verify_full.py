import tempfile
import unittest
from pathlib import Path

from agent.literature import stage, verify
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
FID = "0123456789abcdef"


def _different():
    b = good()
    b["core"]["intervention"][0]["vocab_id"] = "intervention.voucher"
    b["core"]["intervention"][0]["value"] = "vouchers"
    return b


def _env(root):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    for label, result in (("a", good()), ("b", _different())):
        tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
        stage.apply_result(target, task_entry(tasks[0]), result, PROV)
    return target, papers


def _first_pass_verdicts(target, papers, verdict):
    tasks, _ = verify.make_tasks(target, papers)
    entry = task_entry(tasks[0])
    rows = []
    for it in entry["subject"]["items"]:
        row = {"item": it["n"], "verdict": verdict, "reason": "checked"}
        if verdict == "supported":
            row.update(quote="We study cash transfers in rural Somalia", locator=1)
        rows.append(row)
    verify.apply_result(target, entry, {"verdicts": rows}, PROV)


class TestWholePaperPass(unittest.TestCase):
    def test_it_asks_only_about_facts_the_first_check_did_not_support_and_offers_every_page(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _first_pass_verdicts(target, papers, "unclear")
            tasks, skipped = verify.make_tasks(target, papers, full_paper=True)
        self.assertEqual(skipped, {})
        t = tasks[0]
        self.assertEqual(t.id, f"verifyfull-{FID}")
        self.assertEqual({p.ref for p in t.passages}, {f"page {n}" for n in PAGES})
        self.assertEqual(len(t.subject["items"]), 2)
        self.assertTrue(t.subject["full"])
        self.assertIn("whole paper", t.instructions)

    def test_facts_the_first_check_supported_are_not_asked_again(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _first_pass_verdicts(target, papers, "supported")
            tasks, skipped = verify.make_tasks(target, papers, full_paper=True)
        self.assertEqual(tasks, [])
        self.assertIn("nothing", skipped[FID])

    def test_a_supported_verdict_moves_the_fact_to_confirmed_and_the_first_verdict_is_kept(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _first_pass_verdicts(target, papers, "unclear")
            self.assertEqual(len(verify.silver_split(target.records, FID, VOCABS)["open"]), 2)
            tasks, _ = verify.make_tasks(target, papers, full_paper=True)
            entry = task_entry(tasks[0])
            rows = [{"item": 1, "verdict": "supported", "reason": "methods section", "quote": "using a panel of 1,200 households", "locator": 1},
                    {"item": 2, "verdict": "not_supported", "reason": "absent"}]
            self.assertEqual(verify.validate_result(entry, {"verdicts": rows}, target), [])
            verify.apply_result(target, entry, {"verdicts": rows}, PROV)
            rec = target.records.read(FID, "a")
            split = verify.silver_split(target.records, FID, VOCABS)
        self.assertEqual({i["verdict"] for i in rec["verification"]["items"]}, {"unclear"})
        self.assertEqual(len(rec["verification_full"]["items"]), 2)
        self.assertEqual((len(split["confirmed"]), len(split["open"])), (1, 1))

    def test_a_paper_already_checked_on_the_whole_text_is_skipped_unless_redone(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _env(root)
            _first_pass_verdicts(target, papers, "unclear")
            tasks, _ = verify.make_tasks(target, papers, full_paper=True)
            entry = task_entry(tasks[0])
            rows = [{"item": i["n"], "verdict": "unclear", "reason": "x"} for i in entry["subject"]["items"]]
            verify.apply_result(target, entry, {"verdicts": rows}, PROV)
            again, skipped = verify.make_tasks(target, papers, full_paper=True)
            redo, _ = verify.make_tasks(target, papers, full_paper=True, redo=True)
        self.assertEqual(again, [])
        self.assertIn("already", skipped[FID])
        self.assertEqual(len(redo), 1)


if __name__ == "__main__":
    unittest.main()


class TestFullPaperCli(unittest.TestCase):
    def test_verify_full_paper_writes_a_verifyfull_card(self):
        import contextlib
        import io

        from agent.literature import cli
        from lit_helpers import fill_card, write_vocab_dir

        def run(argv):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(argv)
            return code, out.getvalue()

        with tempfile.TemporaryDirectory() as root:
            vocabs = str(Path(root) / "vocabs")
            Path(vocabs).mkdir()
            write_vocab_dir(vocabs)
            make_index(root)
            base = ["--index-root", root, "--vocab-dir", vocabs]
            run(base + ["collect", "--run-id", "x1", "--double"])
            fill_card(Path(root) / ".agent_work" / "x1" / "cards" / f"extract-{FID}.md", good())
            fill_card(Path(root) / ".agent_work" / "x1" / "cards" / f"extract-{FID}-b.md", _different())
            run(base + ["submit", "x1"])
            run(base + ["verify", "--run-id", "v1"])
            fill_card(Path(root) / ".agent_work" / "v1" / "cards" / f"verify-{FID}.md",
                      {"verdicts": [{"item": 1, "verdict": "unclear", "reason": "x"}, {"item": 2, "verdict": "unclear", "reason": "x"}]})
            run(base + ["submit", "v1"])
            code, out = run(base + ["verify", "--full-paper", "--run-id", "v2"])
            card = Path(root) / ".agent_work" / "v2" / "cards" / f"verifyfull-{FID}.md"
            self.assertEqual(code, 0, out)
            self.assertTrue(card.is_file())
