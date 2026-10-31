import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        patcher = mock.patch("core.env.gemini_utils._resolve_env_path", lambda *a: Path(self.root) / "no.env")  # never read the real .env
        patcher.start()
        self.addCleanup(patcher.stop)
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


class TestGapProbeFlag(GapCliCase):
    WHERE = ("--where", "intervention=cash transfer", "--where", "countries=SO")

    def titles(self):
        import sqlite3
        conn = sqlite3.connect(str(db.db_path(self.root)))
        try:
            return [t for (t,) in conn.execute("SELECT title FROM papers ORDER BY file_id")]
        finally:
            conn.close()

    def works(self):
        from discovery.discover_journal_articles.discovery import Work
        titles = [self.titles()[0], "Not in the corpus", "Also absent"]
        return [Work(openalex_id=f"https://openalex.org/W{i}", doi=None, title=t, authors=[], year=2020, abstract=None)
                for i, t in enumerate(titles)]

    def probe_run(self, *extra, fetch=None):
        from unittest import mock
        spy = mock.MagicMock(side_effect=fetch or (lambda *a: iter(self.works())))
        with mock.patch("agent.literature.gap.probe.iter_topic_works", spy) as m:
            code, out = self.run_cli("gap", "run", "--run-id", "g1", *self.WHERE, *extra)
        return code, out, m

    def test_probe_without_a_contact_email_is_refused_before_anything_is_written(self):
        import os
        from unittest import mock
        self.build_db()
        with mock.patch.dict(os.environ, {}, clear=True):
            code, out, m = self.probe_run("--probe")
        self.assertEqual(code, 2)
        self.assertIn("--mailto", out)
        m.assert_not_called()
        self.assertFalse((Path(self.root) / "literature_gap" / "g1").exists())

    def test_probe_reports_k_of_n_and_fills_external(self):
        self.build_db()
        code, out, m = self.probe_run("--probe", "--mailto", "a@b.c")
        self.assertEqual(code, 0)
        self.assertIn("probe: 1 of 3 in the corpus", out)
        probe = self.report()["external"]["probe"]
        self.assertEqual((probe["in_corpus"], probe["retrieved"], probe["requested"]), (1, 3, 25))
        self.assertEqual(m.call_args.args[1:], ("a@b.c", 25))

    def test_probe_n_flag_and_env_email(self):
        import os
        from unittest import mock
        self.build_db()
        with mock.patch.dict(os.environ, {"OPENALEX_CONTACT_EMAIL": "env@b.c"}):
            code, _, m = self.probe_run("--probe", "--probe-n", "5")
        self.assertEqual(code, 0)
        self.assertEqual(m.call_args.args[1:], ("env@b.c", 5))

    def test_a_failing_search_still_writes_the_offline_report(self):
        def boom(*a):
            raise RuntimeError("boom")
        self.build_db()
        code, out, _ = self.probe_run("--probe", "--mailto", "a@b.c", fetch=boom)
        self.assertEqual(code, 0)
        self.assertIn("probe: not run", out)
        self.assertIn("boom", self.report()["external"]["probe"]["error"])
        self.assertEqual(self.report()["verdict"], "tried_directly")

    def test_without_probe_nothing_is_fetched(self):
        self.build_db()
        code, _, m = self.probe_run()
        self.assertEqual(code, 0)
        m.assert_not_called()
        self.assertIsNone(self.report()["external"])


if __name__ == "__main__":
    unittest.main()
