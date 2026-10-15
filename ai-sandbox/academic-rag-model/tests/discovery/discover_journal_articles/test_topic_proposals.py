import json
import tempfile
import unittest
from pathlib import Path

from discovery.discover_journal_articles.topic_proposals import (
    build_proposals_ledger,
    proposals_ledger_path,
    topics_fingerprint,
    write_proposals_ledger,
)
from discovery.discover_journal_articles.discovery import Topic


def _write_sidecar(folder_dir: Path, stem: str, title: str, topics: list[dict]) -> None:
    folder_dir.mkdir(parents=True, exist_ok=True)
    (folder_dir / f"{stem}.meta.json").write_text(json.dumps({"title": title, "topics": topics}), encoding="utf-8")


class TestTopicsFingerprint(unittest.TestCase):
    def test_same_topics_same_fingerprint_regardless_of_order(self):
        a = [Topic(id="T1", display_name="X", score=0.5), Topic(id="T2", display_name="Y", score=0.9)]
        b = [Topic(id="T2", display_name="Y", score=0.9), Topic(id="T1", display_name="X", score=0.5)]
        self.assertEqual(topics_fingerprint(a), topics_fingerprint(b))

    def test_different_scores_different_fingerprint(self):
        a = [Topic(id="T1", display_name="X", score=0.5)]
        b = [Topic(id="T1", display_name="X", score=0.6)]
        self.assertNotEqual(topics_fingerprint(a), topics_fingerprint(b))


class TestBuildProposalsLedger(unittest.TestCase):
    def test_builds_one_entry_per_paper_with_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "business", "10-1-abc", "Carbon Farming",
                [{"id": "T1", "display_name": "Business", "score": 0.39},
                 {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["key"], "10.1/abc")
            self.assertEqual(entry["title"], "Carbon Farming")
            self.assertEqual(entry["current_folder"], "business")
            self.assertEqual(entry["candidates"][0]["folder"], "soil-carbon-and-nitrogen-dynamics")
            self.assertFalse(entry["stale"])

    def test_skips_a_paper_with_no_stored_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(articles_dir / "misc", "10-1-def", "Not Backfilled Yet", [])
            manifest = {"10.1/def": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_skips_an_entry_whose_sidecar_no_longer_exists_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/ghost": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_skips_a_needs_manual_entry_with_no_pdf_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/pending": {"status": "needs_manual", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_marks_stale_when_manifest_fingerprint_differs_from_current_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            topics_data = [{"id": "T1", "display_name": "Business", "score": 0.39}]
            _write_sidecar(articles_dir / "business", "10-1-abc", "Carbon Farming", topics_data)
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business", "topic_decision_fingerprint": "stale-value"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertTrue(entries[0]["stale"])


class TestWriteProposalsLedger(unittest.TestCase):
    def test_writes_ledger_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "misc", "10-1-abc", "A Paper",
                [{"id": "T1", "display_name": "Economics", "score": 0.8}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}

            path = write_proposals_ledger(manifest, articles_dir)

            self.assertEqual(path, proposals_ledger_path(articles_dir))
            entries = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)


if __name__ == "__main__":
    unittest.main()
