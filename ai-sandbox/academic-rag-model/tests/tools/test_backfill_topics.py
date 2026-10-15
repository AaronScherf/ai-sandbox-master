import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery.discover_journal_articles.discovery import Topic, Work
from tools.backfill_topics import backfill_topics


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

    def test_skips_an_openalex_id_only_key_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _sidecar(articles_dir / "misc", "https-openalex-org-w1"[:80])
            manifest = {"https://openalex.org/W1": {"status": "fetched", "folder": "misc"}}

            counts = backfill_topics(manifest, articles_dir, "me@example.com")

            self.assertEqual(counts["skipped_no_doi"], 1)

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
