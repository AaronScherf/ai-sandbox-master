import tempfile
import unittest
from pathlib import Path

from journal_discovery.worklist import write_needs_manual_worklist


class TestWriteNeedsManualWorklist(unittest.TestCase):
    def test_writes_titled_links_with_target_folder(self):
        manifest = {
            "10.1/abc": {
                "status": "needs_manual", "title": "A Paper", "folder": "mobile-money",
                "doi_url": "https://doi.org/10.1/abc",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)

            self.assertEqual(path, Path(tmp) / "needs_manual_downloads.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("[A Paper](https://doi.org/10.1/abc)", content)
            self.assertIn("research/journal-articles/mobile-money/", content)

    def test_excludes_fetched_entries(self):
        manifest = {
            "10.1/fetched": {"status": "fetched", "title": "Already Got This", "folder": "x"},
            "10.1/manual": {"status": "needs_manual", "title": "Still Need This", "folder": "x"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("Already Got This", content)
            self.assertIn("Still Need This", content)

    def test_falls_back_to_doi_link_without_stored_metadata(self):
        # Entries recorded before metadata capture existed -- no title,
        # no doi_url, no folder stored. Must still produce a usable link.
        manifest = {"10.1/bare": {"status": "needs_manual"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("[10.1/bare](https://doi.org/10.1/bare)", content)

    def test_falls_back_to_openalex_link_for_non_doi_key(self):
        manifest = {"https://openalex.org/W1": {"status": "needs_manual"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("[https://openalex.org/W1](https://openalex.org/W1)", content)

    def test_no_folder_recorded_shows_placeholder(self):
        manifest = {"10.1/abc": {"status": "needs_manual", "title": "A Paper"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("no folder recorded yet", content)

    def test_empty_manifest_still_writes_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist({}, tmp)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
