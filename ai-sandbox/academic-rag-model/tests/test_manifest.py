import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.manifest import (
    is_seen,
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
    skip_already_seen,
)


def _work(doi="10.1/abc", openalex_id="W1"):
    return Work(openalex_id=openalex_id, doi=doi, title="T", authors=[], year=2024, abstract=None)


class TestManifestPath(unittest.TestCase):
    def test_lives_under_dot_discovery(self):
        path = manifest_path("/some/articles/dir")
        self.assertEqual(path, Path("/some/articles/dir") / ".discovery" / "seen.json")


class TestLoadSaveManifest(unittest.TestCase):
    def test_load_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_manifest(Path(tmp) / "seen.json"), {})

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "seen.json"
            save_manifest(path, {"10.1/abc": {"status": "fetched"}})
            self.assertEqual(load_manifest(path), {"10.1/abc": {"status": "fetched"}})
            self.assertTrue(path.exists())


class TestManifestKey(unittest.TestCase):
    def test_prefers_doi(self):
        self.assertEqual(manifest_key(_work(doi="10.1/abc", openalex_id="W1")), "10.1/abc")

    def test_falls_back_to_openalex_id_without_doi(self):
        self.assertEqual(manifest_key(_work(doi=None, openalex_id="W1")), "W1")


class TestIsSeenAndRecordOutcome(unittest.TestCase):
    def test_is_seen(self):
        manifest = {"10.1/abc": {"status": "fetched"}}
        self.assertTrue(is_seen(manifest, "10.1/abc"))
        self.assertFalse(is_seen(manifest, "10.1/other"))

    def test_record_outcome_adds_entry_with_status_and_folder(self):
        manifest = {}
        record_outcome(manifest, "10.1/abc", "fetched", folder="climate-displacement")
        entry = manifest["10.1/abc"]
        self.assertEqual(entry["status"], "fetched")
        self.assertEqual(entry["folder"], "climate-displacement")
        self.assertIn("fetched_at", entry)

    def test_record_outcome_without_folder(self):
        manifest = {}
        record_outcome(manifest, "10.1/abc", "needs_manual")
        self.assertEqual(manifest["10.1/abc"]["status"], "needs_manual")
        self.assertNotIn("folder", manifest["10.1/abc"])

    def test_record_outcome_merges_metadata(self):
        # Per user request 2026-09-02: needs_manual entries should carry
        # enough info (title, link, folder) to build a click-through
        # worklist without re-querying OpenAlex later.
        manifest = {}
        record_outcome(
            manifest, "10.1/abc", "needs_manual", folder="mobile-money",
            metadata={"title": "A Paper", "authors": ["Jane Doe"], "year": 2024,
                      "doi_url": "https://doi.org/10.1/abc"},
        )
        entry = manifest["10.1/abc"]
        self.assertEqual(entry["title"], "A Paper")
        self.assertEqual(entry["authors"], ["Jane Doe"])
        self.assertEqual(entry["year"], 2024)
        self.assertEqual(entry["doi_url"], "https://doi.org/10.1/abc")
        self.assertEqual(entry["folder"], "mobile-money")

    def test_record_outcome_without_metadata_unaffected(self):
        manifest = {}
        record_outcome(manifest, "10.1/abc", "fetched", folder="mobile-money")
        self.assertNotIn("title", manifest["10.1/abc"])


class TestSkipAlreadySeen(unittest.TestCase):
    def test_filters_seen_and_counts_them(self):
        manifest = {"10.1/seen": {"status": "fetched"}}
        works = [_work(doi="10.1/seen"), _work(doi="10.1/new")]
        counts = {"already_seen": 0}
        result = list(skip_already_seen(works, manifest, counts))
        self.assertEqual([w.doi for w in result], ["10.1/new"])
        self.assertEqual(counts["already_seen"], 1)

    def test_proposed_status_also_treated_as_seen(self):
        manifest = {"10.1/proposed": {"status": "proposed"}}
        works = [_work(doi="10.1/proposed")]
        counts = {"already_seen": 0}
        result = list(skip_already_seen(works, manifest, counts))
        self.assertEqual(result, [])
        self.assertEqual(counts["already_seen"], 1)


if __name__ == "__main__":
    unittest.main()
