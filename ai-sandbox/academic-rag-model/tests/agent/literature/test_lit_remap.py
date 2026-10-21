import copy
import tempfile
import unittest
from pathlib import Path

from agent.literature.proposals import Proposals
from agent.literature.remap import remap_record
from agent.literature.store import RecordStore
from lit_helpers import VOCABS, good

FID = "0123456789abcdef"


def _proposed(value, quote="Cash transfers raised household food consumption by twelve percent"):
    return {"value": value, "proposed": True, "quote": quote, "locator": 3}


class TestRemap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.records = RecordStore(Path(self.tmp.name) / "study_records")
        self.proposals = Proposals(self.records.dir)
        rec = {"identity": {"file_id": FID}, "transcript_sha": "s", **copy.deepcopy(good())}
        rec["core"]["outcome"] = [_proposed("net welfare")]
        rec["verification"] = {"transcript_sha": "s", "items": [
            {"facet": "outcome", "shown": "proposed:net welfare", "label": "net welfare", "pass": "a", "verdict": "supported"}]}
        self.records.write(rec, "a")
        self.proposals.add(FID, "outcome", "net welfare", "q", 3, "a")

    def test_a_proposed_fact_becomes_the_term_it_was_merged_into(self):
        self.proposals.merge("P0001", "outcome.food_consumption")
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 1)
        fact = self.records.read(FID, "a")["core"]["outcome"][0]
        self.assertEqual(fact["vocab_id"], "outcome.food_consumption")
        self.assertNotIn("proposed", fact)
        self.assertEqual(fact["value"], "net welfare")

    def test_the_checkers_verdict_follows_the_fact_to_its_new_name(self):
        self.proposals.accept("P0001", "outcome.net_welfare", "Net welfare", vocab_dir=self._vocab_dir(),)
        remap_record(self.records, self.proposals, self._reloaded(), FID)
        item = self.records.read(FID, "a")["verification"]["items"][0]
        self.assertEqual(item["shown"], "outcome.net_welfare")
        self.assertEqual(item["verdict"], "supported")

    def test_open_and_rejected_proposals_leave_the_fact_alone(self):
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 0)
        self.proposals.reject("P0001", "too vague")
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 0)
        self.assertTrue(self.records.read(FID, "a")["core"]["outcome"][0]["proposed"])

    def test_a_term_missing_from_the_vocabulary_is_left_alone(self):
        self.proposals.merge("P0001", "outcome.no_such_term")
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 0)
        self.assertTrue(self.records.read(FID, "a")["core"]["outcome"][0]["proposed"])

    def test_two_wordings_mapped_to_one_term_leave_one_fact_and_a_second_run_changes_nothing(self):
        rec = self.records.read(FID, "a")
        rec["core"]["outcome"].append(_proposed("welfare gains"))
        self.records.write(rec, "a")
        self.proposals.add(FID, "outcome", "welfare gains", "q", 3, "a")
        self.proposals.merge("P0001", "outcome.food_consumption")
        self.proposals.merge("P0002", "outcome.food_consumption")
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 2)
        self.assertEqual(len(self.records.read(FID, "a")["core"]["outcome"]), 1)
        self.assertEqual(remap_record(self.records, self.proposals, VOCABS, FID), 0)

    def _vocab_dir(self):
        from lit_helpers import write_vocab_dir
        d = Path(self.tmp.name) / "vocab"
        d.mkdir()
        write_vocab_dir(d)
        return d

    def _reloaded(self):
        from agent.literature.vocab import load_vocabularies
        return load_vocabularies(str(Path(self.tmp.name) / "vocab"))


if __name__ == "__main__":
    unittest.main()


class TestRemapCommand(unittest.TestCase):
    def test_the_command_repoints_facts_across_all_papers(self):
        import contextlib
        import io
        from agent.literature.cli import main
        from lit_helpers import make_index, write_vocab_dir
        with tempfile.TemporaryDirectory() as tmp:
            make_index(tmp, FID)
            vocab_dir = Path(tmp) / "vocab"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir)
            records = RecordStore(Path(tmp) / ".index" / "study_records")
            rec = {"identity": {"file_id": FID}, "transcript_sha": "s", **copy.deepcopy(good())}
            rec["core"]["outcome"] = [_proposed("net welfare")]
            records.write(rec, "a")
            props = Proposals(records.dir)
            props.add(FID, "outcome", "net welfare", "q", 3, "a")
            props.merge("P0001", "outcome.food_consumption")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                main(["--index-root", tmp, "--vocab-dir", str(vocab_dir), "remap"])
            self.assertIn("1 in 1 papers", out.getvalue())
            self.assertEqual(records.read(FID, "a")["core"]["outcome"][0]["vocab_id"], "outcome.food_consumption")


class TestVerdictOnPassBFact(unittest.TestCase):
    def test_a_verdict_stored_with_pass_a_follows_a_fact_renamed_in_pass_b(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = RecordStore(Path(tmp) / "study_records")
            props = Proposals(records.dir)
            a = {"identity": {"file_id": FID}, "transcript_sha": "s", **copy.deepcopy(good())}
            b = {"identity": {"file_id": FID}, "transcript_sha": "s", **copy.deepcopy(good())}
            b["core"]["outcome"] = [_proposed("net welfare")]
            a["verification"] = {"transcript_sha": "s", "items": [
                {"facet": "outcome", "shown": "proposed:net welfare", "label": "net welfare", "pass": "b", "verdict": "supported"}]}
            records.write(a, "a")
            records.write(b, "b")
            props.add(FID, "outcome", "net welfare", "q", 3, "b")
            props.merge("P0001", "outcome.food_consumption")
            remap_record(records, props, VOCABS, FID)
            self.assertEqual(records.read(FID, "a")["verification"]["items"][0]["shown"], "outcome.food_consumption")
