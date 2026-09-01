import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from journal_discovery.access import AccessResult
from journal_discovery.discover import run
from journal_discovery.discovery import Work
from journal_discovery.relevance import ScoredWork


def _args(**overrides):
    defaults = dict(
        faculty=["Jane Doe"], topic=[], relevance_prompt="climate", relevance_threshold=0.5,
        batch_size=25, max_results=100, max_examined=300, pace_per_hour=25.0, zotero=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _work(idx, doi="10.1/abc"):
    return Work(
        openalex_id=f"W{idx}", doi=doi, title=f"Paper {idx}", authors=[], year=2024,
        abstract="x", concepts=["Climate change"],
    )


class TestRun(unittest.TestCase):
    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_fetched_work_writes_pdf_and_sidecar_and_updates_manifest(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["fetched"], 1)
            self.assertEqual(counts["needs_manual"], 0)
            self.assertEqual(counts["already_seen"], 0)

            climate_dir = Path(tmp) / "climate-change"
            pdfs = list(climate_dir.glob("*.pdf"))
            self.assertEqual(len(pdfs), 1)
            self.assertTrue(pdfs[0].with_suffix(".meta.json").exists())

            manifest = (Path(tmp) / ".discovery" / "seen.json")
            self.assertTrue(manifest.exists())

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_needs_manual_work_recorded_without_pdf(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(2)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="needs_manual")

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["needs_manual"], 1)
            self.assertEqual(counts["fetched"], 0)
            self.assertEqual(list(Path(tmp).rglob("*.pdf")), [])

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    def test_already_seen_work_is_skipped_without_fetch_attempt(
        self, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(3)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]

            from journal_discovery.manifest import manifest_path, record_outcome, save_manifest, load_manifest
            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/abc", "fetched", folder="climate-change")
            save_manifest(path, manifest)

            counts = run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["already_seen"], 1)
            mock_resolve_full_text.assert_not_called()

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    @patch("journal_discovery.discover.sync_to_zotero")
    def test_zotero_sync_called_only_when_flag_set_and_configured(
        self, mock_sync, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(4)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            run(_args(
                articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, zotero=True,
                zotero_library_id="12345", zotero_api_key="apikey",
            ))

            mock_sync.assert_called_once()

    @patch("journal_discovery.discover.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.discover.resolve_works", return_value=iter([]))
    @patch("journal_discovery.discover.select_relevant_works")
    @patch("journal_discovery.discover.resolve_full_text")
    @patch("journal_discovery.discover.sync_to_zotero")
    def test_zotero_sync_skipped_without_flag(
        self, mock_sync, mock_resolve_full_text, mock_select, mock_resolve_works, mock_load_model
    ):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(5)
            mock_select.return_value = [ScoredWork(work=work, score=0.9)]
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            run(_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None, zotero=False))

            mock_sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
