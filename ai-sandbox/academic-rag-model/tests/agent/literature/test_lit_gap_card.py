import json
import unittest
from pathlib import Path

from core.agent_tasks.work import load_run
from lit_helpers import fill_card
from synth_helpers import _answer
from test_lit_gap_cli import GapCliCase

QUESTION = "Do cash transfers raise food consumption in Somalia amid conflict?"
GOOD = {"constraints": [
    {"facet": "intervention", "term_id": "intervention.cash_transfer", "phrase": "cash transfers"},
    {"facet": "countries", "term_id": "SO", "phrase": "Somalia"}], "unmapped": ["conflict settings"]}
HINT = "next: python -m agent.literature gap run --run-id"


class TestGapCard(GapCliCase):
    def fill(self, run_id, answer):
        run = load_run(Path(self.root) / ".agent_work", run_id)
        fill_card(run.card_path(f"gap-{run_id}"), answer)

    def constraints_file(self, run_id):
        return Path(self.root) / "literature_gap" / run_id / "constraints.json"

    def test_card_context_includes_a_shortlist_for_the_question_words(self):
        self.build_db()
        code, _ = self.run_cli("gap", "question", QUESTION, "--run-id", "g1")
        self.assertEqual(code, 0)
        run = load_run(Path(self.root) / ".agent_work", "g1")
        text = run.card_path("gap-g1").read_text(encoding="utf-8")
        self.assertIn("intervention.cash_transfer", text)
        self.assertIn(QUESTION, text)

    def test_valid_answer_writes_constraints_json_and_gap_run_uses_it(self):
        self.build_db()
        self.run_cli("gap", "question", QUESTION, "--run-id", "g1")
        self.fill("g1", GOOD)
        code, out = self.run_cli("submit", "g1")
        self.assertEqual(code, 0)
        self.assertIn(f"{HINT} g1", out)
        saved = json.loads(self.constraints_file("g1").read_text(encoding="utf-8"))
        self.assertEqual((saved["question"], saved["unmapped"]), (QUESTION, ["conflict settings"]))
        code, out = self.run_cli("gap", "run", "--run-id", "g1")
        self.assertEqual(code, 0)
        report = self.report()
        self.assertEqual([c["resolved_by"] for c in report["constraints"]], ["card", "card"])
        self.assertEqual(report["question"], QUESTION)
        md = (Path(self.root) / "literature_gap" / "g1" / "report.md").read_text(encoding="utf-8")
        self.assertLess(md.index("conflict settings"), md.index("# Gap analysis"))

    def test_bad_answers_bounce_and_print_no_hint(self):
        self.build_db()
        bad = {
            "unknown term": {"constraints": [{"facet": "intervention", "term_id": "intervention.nope", "phrase": "x"}], "unmapped": []},
            "wrong facet": {"constraints": [{"facet": "intervention", "term_id": "outcome.food_consumption", "phrase": "x"}], "unmapped": []},
            "invalid country": {"constraints": [{"facet": "countries", "term_id": "XX", "phrase": "x"}], "unmapped": []},
            "no constraints": {"constraints": [], "unmapped": []},
            "missing phrase": {"constraints": [{"facet": "intervention", "term_id": "intervention.voucher"}], "unmapped": []},
            "unknown facet": {"constraints": [{"facet": "nonsense", "term_id": "x", "phrase": "x"}], "unmapped": []},
            "unmapped not a list": {"constraints": GOOD["constraints"], "unmapped": "conflict"},
        }
        for n, (name, answer) in enumerate(bad.items(), 1):
            with self.subTest(name):
                run_id = f"bad{n}"
                self.run_cli("gap", "question", QUESTION, "--run-id", run_id)
                self.fill(run_id, answer)
                code, out = self.run_cli("submit", run_id)
                self.assertIn("bounced 1", out)
                self.assertNotIn("next:", out)
                self.assertFalse(self.constraints_file(run_id).exists())

    def test_submit_of_another_stage_prints_no_hint(self):
        self.run_cli("cluster", "define", "demo", "--where", "sector=social protection")
        self.run_cli("annotate", "demo", "--run-id", "ann1")
        run = load_run(Path(self.root) / ".agent_work", "ann1")
        for entry in run.tasks:
            fill_card(run.card_path(entry["id"]), _answer())
        code, out = self.run_cli("submit", "ann1")
        self.assertEqual(code, 0)
        self.assertNotIn("next:", out)

    def test_question_with_no_database_still_writes_a_card(self):
        code, out = self.run_cli("gap", "question", QUESTION, "--run-id", "g1")
        self.assertEqual(code, 0)
        self.assertIn("no database", out)
        self.assertTrue(load_run(Path(self.root) / ".agent_work", "g1").card_path("gap-g1").is_file())

    def test_question_needs_text(self):
        code, out = self.run_cli("gap", "question", "--run-id", "g1")
        self.assertEqual(code, 2)
        self.assertIn("question", out)


if __name__ == "__main__":
    unittest.main()
