import json
import tempfile
import unittest
from pathlib import Path

from agent.literature.gap.classify import classify
from agent.literature.gap.coverage import COMPLETENESS, Sidecar, coverage
from agent.literature.gap.match import Constraint
from agent.literature.gap.report import SCHEMA_VERSION, build_report, gap_dir, render_markdown, write_report
from agent.literature.gap.subregions import load_subregions
from gap_helpers import VOCABS, fx, make_corpus, write_toy_tables

CONSTRAINTS = [Constraint("intervention", "i.cash", "cash", "exact"), Constraint("countries", "SO", "Somalia", "user")]
PAPERS = {
    "p1": {"title": "Study One", "year": 2018, "facts": [fx("intervention", "i.cash_uncond"), fx("countries", "SO"),
                                                      fx("study_design", "d.panel")], "results": [("Cash raised food use", "positive")]},
    "p2": {"title": "Study Two", "year": 2020, "facts": [fx("intervention", "i.cash"), fx("countries", "KE")],
           "results": [("No change", "null")]},
    "p3": {"title": "Study Three", "year": 2015, "facts": [fx("intervention", "i.cash"), fx("sector", "s.social")]},
}


def side(stale=False):
    return Sidecar(eligible=4, excluded=0, without_record=1, open_tier_c=2, db_stale=stale, db_path="db.sqlite",
                   db_mtime=1.0, db_papers=3, scales={})


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmp:
            cls.toy = load_subregions(*write_toy_tables(tmp))

    def report(self, papers=PAPERS, constraints=CONSTRAINTS, stale=False, **kw):
        corpus = make_corpus(papers)
        result = classify(corpus, constraints, VOCABS, self.toy)
        cov = coverage(corpus, result, constraints, side(stale))
        return build_report("Has cash been tried in Somalia?", constraints, VOCABS, result, cov, corpus, **kw)

    def test_report_json_has_schema_version_and_null_external(self):
        r = self.report()
        self.assertEqual((r["schema_version"], r["external"]), (SCHEMA_VERSION, None))
        self.assertEqual(r["verdict"], "tried_directly")
        self.assertEqual(r["counts"], {"direct": 1, "adjacent": 1, "different_method": 0, "partial": 1})
        first = r["constraints"][0]
        self.assertEqual((first["phrase"], first["label"], first["level"], first["resolved_by"]), ("cash", "Cash transfers", 1, "exact"))
        self.assertEqual([e["file_id"] for e in r["evidence"]], ["p1", "p2"])
        self.assertEqual(r["evidence"][1]["labels"], ["different country (same subregion: Eastern Africa)"])
        json.dumps(r)

    def test_markdown_contains_verdict_rule_caveat_and_completeness_line(self):
        md = render_markdown(self.report())
        for needle in ("tried_directly", "Facets are per paper", COMPLETENESS, "Has cash been tried in Somalia?", "Study One"):
            self.assertIn(needle, md)

    def test_quotes_absent_by_default_and_present_with_flag(self):
        self.assertNotIn("quote p1-1", json.dumps(self.report()))
        self.assertNotIn("quote p1-1", render_markdown(self.report()))
        flagged = self.report(include_quotes=True)
        self.assertIn("quote p1-1", json.dumps(flagged))
        self.assertIn("quote p1-1", render_markdown(flagged))

    def test_stale_db_warning_leads_the_markdown(self):
        md = render_markdown(self.report(stale=True))
        self.assertTrue(md.lstrip().lower().startswith("> **warning"))
        self.assertNotIn("warning", render_markdown(self.report()).lower().split("# gap analysis")[0])

    def test_unmapped_phrases_are_printed_first(self):
        md = render_markdown(self.report(unmapped=["conflict settings"]))
        self.assertLess(md.index("conflict settings"), md.index("# Gap analysis"))

    def test_rendering_is_deterministic(self):
        self.assertEqual(render_markdown(self.report()), render_markdown(self.report()))

    def test_empty_corpus_report_still_renders(self):
        md = render_markdown(self.report(papers={}))
        self.assertIn("no_evidence_in_corpus", md)
        self.assertIn(COMPLETENESS, md)

    def test_write_report_creates_both_files_and_gap_dir_rejects_bad_run_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = gap_dir(tmp, "g1")
            js, md = write_report(self.report(), run_dir)
            self.assertEqual((js.name, md.name), ("report.json", "report.md"))
            self.assertEqual(json.loads(js.read_text(encoding="utf-8"))["verdict"], "tried_directly")
            self.assertTrue(md.read_text(encoding="utf-8").startswith("#") or "Gap analysis" in md.read_text(encoding="utf-8"))
        for bad in ("../x", "G1", "", "a b"):
            with self.assertRaises(ValueError):
                gap_dir("root", bad)

    def test_gitignore_lists_literature_gap(self):
        root = Path(__file__).resolve().parents[5]
        self.assertIn("ai-sandbox/research/literature_gap/", (root / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
