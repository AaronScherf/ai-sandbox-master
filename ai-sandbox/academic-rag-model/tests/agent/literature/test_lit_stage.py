import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.literature import stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import PAGES, VOCABS, good, make_index, vocab

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}


def _setup(root, **index_kw):
    make_index(root, **index_kw)
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(index_root=str(root), records=records, vocabs=VOCABS, proposals=Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    return target, papers


def _task(target, papers, **kw):
    tasks, skipped = stage.make_tasks(target, papers, **kw)
    assert len(tasks) == 1, skipped
    return tasks[0]


class TestMakeTasks(unittest.TestCase):
    def test_one_passage_per_page_and_the_vocabularies_are_listed(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            task = _task(target, papers)
        self.assertEqual(task.id, "extract-0123456789abcdef")
        self.assertEqual(task.stage, "extract")
        self.assertEqual([p.ref for p in task.passages], [f"page {n}" for n in sorted(PAGES)])
        self.assertEqual([p.id for p in task.passages], [f"P{n}" for n in sorted(PAGES)])
        self.assertIn("intervention.cash_transfer", task.context)
        self.assertIn("Cash transfers in Somalia", task.context)
        subj = task.subject
        self.assertEqual((subj["file_id"], subj["pass"]), ("0123456789abcdef", "a"))
        self.assertEqual(subj["identity"]["title"], "Cash transfers in Somalia")
        self.assertEqual(subj["vocab_versions"]["intervention"], 1)
        self.assertEqual(len(subj["transcript_sha"]), 16)

    def test_pass_b_has_its_own_task_id(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            self.assertEqual(_task(target, papers, pass_label="b").id, "extract-0123456789abcdef-b")

    def test_an_oversize_transcript_is_skipped_naming_the_limit(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            with patch.object(stage, "MAX_CARD_CHARS", 10):
                tasks, skipped = stage.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("limit", skipped["0123456789abcdef"])

    def test_a_current_record_is_skipped_unless_redo(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            tasks, skipped = stage.make_tasks(target, papers)
            self.assertEqual(tasks, [])
            self.assertIn("current record", skipped["0123456789abcdef"])
            self.assertEqual(len(stage.make_tasks(target, papers, redo=True)[0]), 1)

    def test_a_changed_transcript_is_extracted_again(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            md = Path(root) / papers[0].path
            md.write_text(md.read_text(encoding="utf-8") + "\n\nA new sentence added later.", encoding="utf-8")
            self.assertEqual(len(stage.make_tasks(target, papers)[0]), 1)

    def test_a_transcript_that_vanished_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            (Path(root) / papers[0].path).unlink()
            tasks, skipped = stage.make_tasks(target, papers)
        self.assertEqual(tasks, [])
        self.assertIn("transcript", skipped["0123456789abcdef"])


class TestValidate(unittest.TestCase):
    def test_a_good_result_passes_and_a_fabricated_quote_bounces(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            entry = task_entry(_task(target, papers))
            self.assertEqual(stage.validate_result(entry, good(), target), [])
            bad = good()
            bad["core"]["outcome"][0]["quote"] = "hunger fell by forty percent everywhere"
            self.assertTrue(any("core.outcome[0].quote" in p for p in stage.validate_result(entry, bad, target)))

    def test_a_term_removed_since_the_card_was_made_bounces_and_says_the_vocabulary_changed(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            entry = task_entry(_task(target, papers))
            changed = dict(VOCABS, outcome=vocab("outcome", "outcome.something_else", version=2))
            moved = stage.Target(target.index_root, target.records, changed, target.proposals)
            msgs = stage.validate_result(entry, good(), moved)
        self.assertTrue(any("core.outcome[0].vocab_id" in m for m in msgs), msgs)
        self.assertTrue(any("vocabulary changed" in m for m in msgs), msgs)


class TestApply(unittest.TestCase):
    def test_record_shape_provenance_and_identity(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root, card_extra={"doi": "10.1/x"})
            task = _task(target, papers)
            self.assertIsNone(stage.apply_result(target, task_entry(task), good(), PROV))
            rec = target.records.read("0123456789abcdef")
        self.assertEqual(rec["schema_version"], 1)
        self.assertEqual(rec["identity"]["doi"], "10.1/x")
        self.assertEqual(rec["transcript_sha"], task.subject["transcript_sha"])
        self.assertEqual(rec["core"]["geography"]["countries"], ["SO"])
        self.assertNotIn("modules", rec)
        self.assertEqual(rec["extractor"]["agent_name"], "antigravity")
        self.assertEqual(rec["extractor"]["run_id"], "r1")
        self.assertEqual(rec["extractor"]["prompt_version"], "extract-v3")
        self.assertEqual(rec["extractor"]["pass"], "a")
        self.assertEqual(rec["review"], {"status": "unreviewed", "items_flagged": []})

    def test_modules_are_kept_when_present(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            result = good()
            result["modules"] = {"disaster_conflict": {"hazard_types": [], "conflict_setting": None,
                                                       "social_protection_modality": "cash"}}
            stage.apply_result(target, task_entry(_task(target, papers)), result, PROV)
            self.assertEqual(target.records.read("0123456789abcdef")["modules"], result["modules"])

    def test_pass_b_goes_to_its_own_file(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            stage.apply_result(target, task_entry(_task(target, papers)), good(), PROV)
            stage.apply_result(target, task_entry(_task(target, papers, pass_label="b", redo=True)), good(), PROV)
            self.assertEqual(target.records.read("0123456789abcdef", "b")["extractor"]["pass"], "b")
            self.assertEqual(target.records.read("0123456789abcdef", "a")["extractor"]["pass"], "a")

    def test_proposed_terms_are_ledgered_once_even_if_the_paper_is_extracted_again(self):
        with tempfile.TemporaryDirectory() as root:
            target, papers = _setup(root)
            result = good()
            result["core"]["study_design"] = [{"value": "synthetic control", "proposed": True,
                                               "quote": "using a panel of 1,200 households", "locator": 1}]
            stage.apply_result(target, task_entry(_task(target, papers)), result, PROV)
            stage.apply_result(target, task_entry(_task(target, papers, redo=True)), result, PROV)
            stage.apply_result(target, task_entry(_task(target, papers, pass_label="b", redo=True)), result, PROV)
            items = target.proposals.all()
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["vocabulary"], items[0]["value"], items[0]["status"]),
                         ("study_design", "synthetic control", "open"))
        self.assertEqual(items[0]["locator"], 1)


if __name__ == "__main__":
    unittest.main()
