import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent.literature import tiers, verify
from agent.literature.cli import main
from core.agent_tasks.work import task_entry
from test_lit_verify import PROV, FID, _answer, _different, _setup
from lit_helpers import VOCABS, good, write_vocab_dir


def _verified(root, verdicts):
    """Agree on everything but the intervention and ET; then the checker rules per the given verdicts, in card order."""
    target, papers = _setup(root, _different())
    tasks, _ = verify.make_tasks(target, papers)
    entry = task_entry(tasks[0])
    result = _answer(entry)
    for row, verdict in zip(result["verdicts"], verdicts):
        row["verdict"] = verdict
        if verdict != "supported":
            row.pop("quote", None), row.pop("locator", None)
    verify.apply_result(target, entry, result, PROV)
    return target


class TestTiers(unittest.TestCase):
    def test_agreed_facts_are_a_supported_single_pass_facts_b_and_the_rest_c(self):
        with tempfile.TemporaryDirectory() as root:
            target = _verified(root, ["supported", "not_supported", "unclear"])
            items = tiers.tiered_facts(target.records, FID, VOCABS)
        by_tier = {t: [i for i in items if i["tier"] == t] for t in "ABC"}
        self.assertTrue(by_tier["A"] and any(i["shown"] == "outcome.food_consumption" for i in by_tier["A"]))
        self.assertEqual(len(by_tier["B"]), 1)
        self.assertEqual(len(by_tier["C"]), 2)
        self.assertEqual(sum(len(v) for v in by_tier.values()), len(items))

    def test_a_paper_with_one_pass_has_no_tiers_yet(self):
        with tempfile.TemporaryDirectory() as root:
            target = _verified(root, ["supported"] * 3)
            target.records.path(FID, "b").unlink()
            self.assertEqual(tiers.tiered_facts(target.records, FID, VOCABS), [])

    def test_a_rejected_proposal_s_fact_is_dropped_when_proposals_is_given(self):
        with tempfile.TemporaryDirectory() as root:
            both = copy.deepcopy(good())
            both["core"]["outcome"].append(
                {"value": "too vague a topic", "proposed": True,
                 "quote": "given attrition between survey waves", "locator": 4})
            target, _ = _setup(root, both)
            items = tiers.tiered_facts(target.records, FID, VOCABS)
            self.assertIn("proposed:too vague a topic", {i["shown"] for i in items})
            # apply_result already auto-filed this as proposal P0001 (see stage.apply_result's _proposed_facts loop)
            target.proposals.reject("P0001", "triage: too vague")
            with_filter = tiers.tiered_facts(target.records, FID, VOCABS, target.proposals)
            self.assertNotIn("proposed:too vague a topic", {i["shown"] for i in with_filter})
            # an open (not yet decided) proposal for a different fact must not be dropped
            self.assertIn("outcome.food_consumption", {i["shown"] for i in with_filter})

    def test_floor_drops_the_lower_tiers(self):
        items = [{"tier": "A"}, {"tier": "B"}, {"tier": "C"}]
        self.assertEqual([i["tier"] for i in tiers.at_least(items, "B")], ["A", "B"])
        self.assertEqual([i["tier"] for i in tiers.at_least(items, "A")], ["A"])
        self.assertEqual(len(tiers.at_least(items, "C")), 3)

    def test_the_command_prints_counts_and_writes_the_derived_file(self):
        with tempfile.TemporaryDirectory() as root:
            target = _verified(root, ["supported", "not_supported", "unclear"])
            vocab_dir = Path(root) / "vocab"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                main(["--index-root", root, "--vocab-dir", str(vocab_dir), "tiers"])
            written = json.loads((Path(target.records.dir) / "_tiers.json").read_text(encoding="utf-8"))
        self.assertIn("tier A", out.getvalue())
        self.assertEqual(set(written["legend"]), {"A", "B", "C"})
        self.assertIn(FID, written["papers"])
        self.assertTrue(all(i["tier"] in "ABC" for i in written["papers"][FID]))


if __name__ == "__main__":
    unittest.main()
