import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent.literature import db
from agent.literature.cli import main
from lit_helpers import write_vocab_dir
from synth_helpers import build, three_papers


class GapCliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.target, _ = build(self.root, three_papers())
        self.vocab_dir = Path(self.root) / "vocab"
        self.vocab_dir.mkdir()
        write_vocab_dir(self.vocab_dir)

    def build_db(self):
        db.build(self.target, db.db_path(self.root))

    def run_cli(self, *args, root_flags=True):
        out = io.StringIO()
        flags = ["--index-root", self.root, "--vocab-dir", str(self.vocab_dir)] if root_flags else []
        with contextlib.redirect_stdout(out):
            code = main([*flags, *args])
        return code, out.getvalue()

    def report(self, run_id="g1"):
        return json.loads((Path(self.root) / "literature_gap" / run_id / "report.json").read_text(encoding="utf-8"))


class TestGapRun(GapCliCase):
    def test_run_writes_report_and_prints_verdict(self):
        self.build_db()
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "intervention=cash transfer", "--where", "countries=SO")
        self.assertEqual(code, 0)
        self.assertIn("verdict: tried_directly", out)
        report = self.report()
        self.assertEqual(report["counts"]["direct"], 2)
        self.assertTrue((Path(self.root) / "literature_gap" / "g1" / "report.md").is_file())

    def test_ambiguous_phrase_stops_with_candidates_json_and_exit_2(self):
        self.build_db()
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "intervention=transfer")
        self.assertEqual(code, 2)
        self.assertIn("--pick intervention=intervention.cash_transfer", out)
        stopped = json.loads((Path(self.root) / "literature_gap" / "g1" / "candidates.json").read_text(encoding="utf-8"))
        self.assertEqual(stopped["constraints"][0]["candidates"][0]["term_id"], "intervention.cash_transfer")
        self.assertFalse((Path(self.root) / "literature_gap" / "g1" / "report.json").exists())
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "intervention=transfer",
                                 "--pick", "intervention=intervention.cash_transfer")
        self.assertEqual(code, 0)
        first = self.report()["constraints"][0]
        self.assertEqual((first["phrase"], first["value"], first["resolved_by"]), ("transfer", "intervention.cash_transfer", "user"))

    def test_phrase_with_no_candidates_exits_2_with_a_message(self):
        self.build_db()
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "intervention=zzz")
        self.assertEqual(code, 2)
        self.assertIn("no candidate", out.lower())

    def test_no_database_exits_2(self):
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "countries=SO")
        self.assertEqual(code, 2)
        self.assertIn("db build", out)

    def test_unknown_facet_in_where_exits_2_without_traceback(self):
        self.build_db()
        code, out = self.run_cli("gap", "run", "--run-id", "g1", "--where", "nonsense=x")
        self.assertEqual(code, 2)
        self.assertIn("gap:", out)

    def test_no_constraints_at_all_exits_2(self):
        self.build_db()
        code, out = self.run_cli("gap", "run", "--run-id", "g1")
        self.assertEqual(code, 2)
        self.assertIn("constraint", out)

    def test_report_root_flag_redirects_output(self):
        self.build_db()
        elsewhere = Path(self.root) / "elsewhere"
        code, _ = self.run_cli("gap", "run", "--run-id", "g1", "--where", "countries=SO", "--report-root", str(elsewhere))
        self.assertEqual(code, 0)
        self.assertTrue((elsewhere / "g1" / "report.json").is_file())
        self.assertFalse((Path(self.root) / "literature_gap").exists())

    def test_quotes_flag_adds_quotes_to_the_report(self):
        self.build_db()
        self.run_cli("gap", "run", "--run-id", "g1", "--where", "countries=SO")
        self.assertNotIn('"quote"', json.dumps(self.report()))
        self.run_cli("gap", "run", "--run-id", "g2", "--where", "countries=SO", "--quotes")
        self.assertIn('"quote"', json.dumps(self.report("g2")))


if __name__ == "__main__":
    unittest.main()
