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


if __name__ == "__main__":
    unittest.main()
