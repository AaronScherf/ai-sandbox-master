import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.access import AccessResult
from discovery.discover_journal_articles.discovery import Work
from discovery.discover_journal_articles.fetch_dois import _clean_doi, parse_doi_text, run
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path, record_outcome, save_manifest


def _args(tmp, **overrides):
    defaults = dict(
        doi=[], doi_file=None, folder=None, dry_run=False, pace_per_hour=25.0, time_budget_seconds=None,
        articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, core_api_key=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _work(doi, idx=1, is_oa=True):
    return Work(
        openalex_id=f"W{idx}", doi=doi.lower(), title=f"Paper {idx}", authors=["A"], year=2024,
        abstract=None, concepts=["Economics"], is_oa=is_oa,
    )


class TestParsing(unittest.TestCase):
    def test_parentheses_and_colons_survive(self):
        for doi in ("10.1016/s0167-6296(98)00039-3", "10.1093/acprof:oso/9780199534081.003.0015"):
            self.assertEqual(_clean_doi(doi), doi)

    def test_prefixes_and_trailing_punctuation(self):
        self.assertEqual(_clean_doi("doi:10.1257/aer.p20151016."), "10.1257/aer.p20151016")
        self.assertEqual(_clean_doi("https://doi.org/10.1257/aer.p20151016,"), "10.1257/aer.p20151016")
        self.assertEqual(_clean_doi("http://dx.doi.org/10.1/x.y"), None)  # too-short registrant is not a DOI

    def test_unbalanced_closing_parenthesis_is_stripped(self):
        self.assertEqual(_clean_doi("10.1234/abc.def)"), "10.1234/abc.def")

    def test_not_a_doi(self):
        self.assertIsNone(_clean_doi("Smith 2020"))

    def test_file_text_comments_blanks_crlf_and_duplicates(self):
        text = "# header\r\n\r\n10.1257/pandp.20251021  # Brown et al. [RQ1, P1]\r\n10.1257/PANDP.20251021\r\nnot a doi\r\n"
        entries, rejected = parse_doi_text(text)
        self.assertEqual(entries, [("10.1257/pandp.20251021", "Brown et al. [RQ1, P1]")])
        self.assertEqual(rejected, ["not a doi"])


class TestRun(unittest.TestCase):
    @patch("discovery.discover_journal_articles.fetch_dois.resolve_full_text")
    @patch("discovery.discover_journal_articles.fetch_dois.resolve_work_by_doi")
    def test_fetched_needs_manual_and_not_in_openalex(self, mock_resolve, mock_access):
        works = {"10.1234/a": _work("10.1234/a", 1), "10.1234/b": _work("10.1234/b", 2)}
        mock_resolve.side_effect = lambda doi, mailto: works.get(doi)
        mock_access.side_effect = [
            AccessResult(status="fetched", content=b"%PDF-1.4", tier="unpaywall"),
            AccessResult(status="needs_manual"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            results = run(_args(tmp, doi=["10.1234/a", "10.1234/b", "10.1234/zzzz"], folder="Novelty Check"))
            outcomes = {r["doi"]: r["outcome"] for r in results}
            self.assertEqual(outcomes, {"10.1234/a": "fetched", "10.1234/b": "needs_manual", "10.1234/zzzz": "not_in_openalex"})

            folder = Path(tmp) / "novelty-check"
            self.assertEqual(len(list(folder.glob("*.pdf"))), 1)
            self.assertEqual(len(list(folder.glob("*.meta.json"))), 1)

            manifest = load_manifest(manifest_path(tmp))
            self.assertEqual(manifest["10.1234/a"]["status"], "fetched")
            self.assertEqual(manifest["10.1234/b"]["status"], "needs_manual")
            self.assertNotIn("10.1234/zzzz", manifest)  # no fake entry for an unknown DOI

            self.assertIn("10.1234/b", (Path(tmp) / "needs_manual_downloads.md").read_text(encoding="utf-8"))
            self.assertIn("not_in_openalex", (Path(tmp) / ".discovery" / "doi_fetch_report.md").read_text(encoding="utf-8"))

    @patch("discovery.discover_journal_articles.fetch_dois.resolve_full_text")
    @patch("discovery.discover_journal_articles.fetch_dois.resolve_work_by_doi")
    def test_already_fetched_skipped_but_needs_manual_retried(self, mock_resolve, mock_access):
        mock_resolve.return_value = _work("10.1234/b", 2)
        mock_access.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="core")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {}
            record_outcome(manifest, "10.1234/a", "fetched", folder="economics")
            record_outcome(manifest, "10.1234/b", "needs_manual", folder="economics")
            save_manifest(manifest_path(tmp), manifest)

            results = run(_args(tmp, doi=["10.1234/a", "10.1234/B"]))
            self.assertEqual([r["outcome"] for r in results], ["already_seen", "fetched"])
            mock_resolve.assert_called_once()  # no network lookup for the DOI already on disk
            self.assertEqual(load_manifest(manifest_path(tmp))["10.1234/b"]["status"], "fetched")

    @patch("discovery.discover_journal_articles.fetch_dois.resolve_full_text")
    @patch("discovery.discover_journal_articles.fetch_dois.resolve_work_by_doi")
    def test_dry_run_downloads_and_writes_nothing(self, mock_resolve, mock_access):
        mock_resolve.return_value = _work("10.1234/a", 1, is_oa=False)
        with tempfile.TemporaryDirectory() as tmp:
            results = run(_args(tmp, doi=["10.1234/a"], dry_run=True))
            self.assertEqual(results[0]["outcome"], "would_try")
            self.assertEqual(results[0]["tier"], "no_open_access_listed")
            mock_access.assert_not_called()
            self.assertEqual(list(Path(tmp).rglob("*")), [])

    @patch("discovery.discover_journal_articles.fetch_dois.resolve_work_by_doi")
    def test_doi_file_and_rejected_lines_reported(self, mock_resolve):
        mock_resolve.return_value = None
        with tempfile.TemporaryDirectory() as tmp:
            doi_file = Path(tmp) / "list.txt"
            doi_file.write_text("10.1234/a  # first\nnonsense\n", encoding="utf-8")
            results = run(_args(tmp, doi_file=str(doi_file)))
            self.assertEqual({r["outcome"] for r in results}, {"not_in_openalex", "not_a_doi"})


if __name__ == "__main__":
    unittest.main()
