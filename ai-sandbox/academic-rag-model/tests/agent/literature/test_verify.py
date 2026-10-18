import tempfile
import unittest
from pathlib import Path

from agent.literature import stage, verify
from agent.literature.compare import single_pass_facts
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
    b["core"]["geography"]["countries"] = ["SO", "ET"]
    return b


def _setup(root, second):
    make_index(root)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    for label, result in (("a", good()), ("b", second)):
        tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
        stage.apply_result(target, task_entry(tasks[0]), result, PROV)
    return target, papers


def _record(result):
    return {"core": result["core"], "appraisal": result["appraisal"], "identity": {"file_id": "x"}}


class TestSinglePassFacts(unittest.TestCase):
    def test_lists_only_facts_one_pass_found_and_names_the_pass(self):
        items = single_pass_facts(_record(good()), _record(_different()), VOCABS)
        seen = {(i["facet"], i["shown"], i["pass"]) for i in items}
        self.assertEqual(seen, {("intervention", "intervention.cash_transfer", "a"),
                                ("intervention", "intervention.voucher", "b"),
                                ("countries", "ET", "b")})
        self.assertTrue(all(i["quote"] and i["locator"] for i in items))

    def test_agreeing_passes_give_nothing(self):
        self.assertEqual(single_pass_facts(_record(good()), _record(good()), VOCABS), [])


class TestVerifyCards(unittest.TestCase):
    def test_a_card_lists_the_disputed_facts_without_saying_which_pass_wrote_them(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root, _different())
            tasks, skipped = verify.make_tasks(target, papers)
        self.assertEqual(skipped, {})
        t = tasks[0]
        self.assertEqual((t.id, t.stage), (f"verify-{FID}", "verify"))
        self.assertEqual(len(t.subject["items"]), 3)
        self.assertIn("intervention.voucher", t.context)
        self.assertNotIn("pass b", t.context.lower())
        self.assertTrue({p.ref for p in t.passages} <= {f"page {n}" for n in PAGES})
        self.assertNotIn("We study cash transfers in rural Somalia", t.context)  # the original quote is not shown

    def test_agreeing_papers_are_skipped_with_a_reason(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root, good())
            tasks, skipped = verify.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("agree", skipped[FID])

    def test_a_paper_with_one_pass_is_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root)
            records = RecordStore(Path(root) / ".index" / "study_records")
            target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
            papers, _ = eligible_papers(str(root))
            tasks, skipped = verify.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("two", skipped[FID])


def _answer(entry, verdict="supported", **over):
    out = []
    for it in entry["subject"]["items"]:
        row = {"item": it["n"], "verdict": verdict, "reason": "the page says so"}
        if verdict == "supported":
            row.update(quote="We study cash transfers in rural Somalia", locator=1)
        row.update(over)
        out.append(row)
    return {"verdicts": out}


class TestVerifyResults(unittest.TestCase):
    def _entry(self, root):
        target, papers = _setup(root, _different())
        tasks, _ = verify.make_tasks(target, papers)
        return target, task_entry(tasks[0])

    def test_a_complete_answer_is_accepted_and_written_to_the_record(self):
        with tempfile.TemporaryDirectory() as root:
            target, entry = self._entry(root)
            result = _answer(entry)
            self.assertEqual(verify.validate_result(entry, result, target), [])
            verify.apply_result(target, entry, result, PROV)
            v = target.records.read(FID, "a")["verification"]
        self.assertEqual(len(v["items"]), 3)
        self.assertEqual({i["verdict"] for i in v["items"]}, {"supported"})
        self.assertEqual({i["pass"] for i in v["items"]}, {"a", "b"})

    def test_missing_unknown_and_bad_verdicts_bounce(self):
        with tempfile.TemporaryDirectory() as root:
            target, entry = self._entry(root)
            short = _answer(entry)
            short["verdicts"].pop()
            self.assertTrue(any("item 3" in m for m in verify.validate_result(entry, short, target)))
            bad = _answer(entry, verdict="maybe")
            self.assertTrue(any("verdict" in m for m in verify.validate_result(entry, bad, target)))
            extra = _answer(entry)
            extra["verdicts"].append({"item": 99, "verdict": "unclear", "reason": "x"})
            self.assertTrue(any("99" in m for m in verify.validate_result(entry, extra, target)))

    def test_supported_needs_a_quote_that_is_on_the_cited_page(self):
        with tempfile.TemporaryDirectory() as root:
            target, entry = self._entry(root)
            fake = _answer(entry, quote="Transfers cured all poverty everywhere", locator=1)
            msgs = verify.validate_result(entry, fake, target)
            self.assertTrue(any("quote" in m for m in msgs), msgs)
            self.assertEqual(verify.validate_result(entry, _answer(entry, verdict="not_supported"), target), [])


if __name__ == "__main__":
    unittest.main()


class TestSilver(unittest.TestCase):
    def test_agreed_confirmed_and_open_facts_are_split(self):
        from agent.literature.compare import agreed_facts
        agreed = agreed_facts(_record(good()), _record(_different()), VOCABS)
        self.assertEqual({(i["facet"], i["shown"]) for i in agreed if i["facet"] in ("outcome", "countries")},
                         {("outcome", "outcome.food_consumption"), ("countries", "SO")})
        self.assertNotIn("intervention.cash_transfer", {i["shown"] for i in agreed})

    def test_silver_set_combines_agreement_with_supported_verdicts(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root, _different())
            tasks, _ = verify.make_tasks(target, papers)
            entry = task_entry(tasks[0])
            result = _answer(entry)
            result["verdicts"][0]["verdict"] = "not_supported"
            result["verdicts"][0].pop("quote"), result["verdicts"][0].pop("locator")
            verify.apply_result(target, entry, result, PROV)
            split = verify.silver_split(target.records, FID, VOCABS)
        self.assertEqual(len(split["open"]), 1)
        self.assertEqual(len(split["confirmed"]), 2)
        self.assertTrue(any(i["shown"] == "outcome.food_consumption" for i in split["agreed"]))
