import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.discovery import Topic, Work
from tools.backfill_topics import _default_articles_dir, backfill_topics


def _sidecar(folder_dir: Path, stem: str, extra: dict | None = None) -> None:
    folder_dir.mkdir(parents=True, exist_ok=True)
    data = {"title": "A Paper", "doi": None, "topics": []}
    data.update(extra or {})
    (folder_dir / f"{stem}.meta.json").write_text(json.dumps(data), encoding="utf-8")


def _work_with_topics():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=[], year=2024, abstract=None,
        topics=[Topic(id="https://openalex.org/T1", display_name="Climate Adaptation", score=0.9)],
    )


class TestDefaultArticlesDir(unittest.TestCase):
    def test_matches_sibling_tools_default(self):
        # Confirmed real (code review finding, 2026-10-15): this file lives
        # at the same depth under academic-rag-model/ as audit_metadata.py
        # and reconcile_needs_manual.py (both tools/<file>.py), so it must
        # resolve the same number of parents up to <ai-sandbox>/research/
        # journal-articles/. The original code used one fewer parent,
        # landing inside academic-rag-model/ where that folder doesn't
        # exist -- load_manifest() then silently returns {} and the script
        # reports "Updated: 0" with no error.
        import tools.audit_metadata as audit_metadata
        sibling_default = Path(audit_metadata.__file__).resolve().parent.parent.parent / "research" / "journal-articles"
        self.assertEqual(_default_articles_dir(), sibling_default)


class TestBackfillTopics(unittest.TestCase):
    @patch("tools.backfill_topics.resolve_work_by_doi")
    def test_updates_sidecar_with_fetched_topics(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "10-1-abc")
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}
            mock_resolve.return_value = _work_with_topics()

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["updated"], 1)
            sidecar = json.loads((articles_dir / "misc" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["topics"], [{"id": "https://openalex.org/T1", "display_name": "Climate Adaptation", "score": 0.9}])

    def test_skips_entry_without_a_folder(self):
        manifest = {"10.1/abc": {"status": "needs_manual"}}
        counts = backfill_topics(manifest, tempfile.mkdtemp(), "me@example.com")
        self.assertEqual(counts["skipped_no_folder"], 1)

    def test_skips_entry_whose_sidecar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}
            counts = backfill_topics(manifest, tmp, "me@example.com")
            self.assertEqual(counts["skipped_no_folder"], 1)

    @patch("tools.backfill_topics.resolve_work_by_openalex_id")
    def test_resolves_an_openalex_id_only_key_by_direct_lookup(self, mock_resolve_by_id):
        # Confirmed real (code review finding, 2026-10-15): an
        # OpenAlex-id-only manifest key was unconditionally skipped as
        # "no DOI", even though OpenAlex's GET /works/{id} resolves that
        # exact ID directly -- the plan scoped this out deliberately,
        # but it's a real, if narrow, coverage gap.
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "https-openalex-org-w1"[:80])
            manifest = {"https://openalex.org/W1": {"status": "fetched", "folder": "misc"}}
            mock_resolve_by_id.return_value = _work_with_topics()

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["updated"], 1)
            mock_resolve_by_id.assert_called_once_with("https://openalex.org/W1", "me@example.com")

    @patch("tools.backfill_topics.resolve_work_by_openalex_id", return_value=None)
    def test_skips_an_openalex_id_only_key_not_found_in_openalex(self, mock_resolve_by_id):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "https-openalex-org-w1"[:80])
            manifest = {"https://openalex.org/W1": {"status": "fetched", "folder": "misc"}}

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["skipped_not_found"], 1)

    @patch("tools.backfill_topics.resolve_work_by_doi", return_value=None)
    def test_skips_a_doi_not_found_in_openalex(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "10-1-abc")
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["skipped_not_found"], 1)


if __name__ == "__main__":
    unittest.main()
