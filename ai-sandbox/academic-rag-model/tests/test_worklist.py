import tempfile
import unittest
from pathlib import Path

from journal_discovery.worklist import write_needs_manual_worklist, write_snowball_candidates_worklist


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

    def test_excludes_stale_dataset_type_entries(self):
        # Entries recorded before the discovery.py dataset-type filter
        # existed (RCT registrations, replication-data records) may still
        # carry a backfilled work_type -- these were never real papers
        # and shouldn't clutter a click-through worklist.
        manifest = {
            "10.1/rct": {"status": "needs_manual", "title": "A Trial Registration", "work_type": "dataset"},
            "10.1/real": {"status": "needs_manual", "title": "A Real Paper", "work_type": "article"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("A Trial Registration", content)
            self.assertIn("A Real Paper", content)

    def test_empty_manifest_still_writes_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist({}, tmp)
            self.assertTrue(path.exists())

    def test_writes_unchecked_checkbox_by_default(self):
        manifest = {"10.1/abc": {"status": "needs_manual", "title": "A Paper", "doi_url": "https://doi.org/10.1/abc"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("- [ ] [A Paper](https://doi.org/10.1/abc)", content)

    def test_preserves_checked_state_across_regeneration(self):
        # Per user request 2026-09-02: the worklist is regenerated on
        # every discover run, so a user manually checking a box (to track
        # "I've downloaded this one" before conversion confirms it) must
        # survive the next regeneration, not get silently wiped.
        manifest = {"10.1/abc": {"status": "needs_manual", "title": "A Paper", "doi_url": "https://doi.org/10.1/abc"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            checked_content = path.read_text(encoding="utf-8").replace(
                "- [ ] [A Paper]", "- [x] [A Paper]"
            )
            path.write_text(checked_content, encoding="utf-8")

            write_needs_manual_worklist(manifest, tmp)

            self.assertIn("- [x] [A Paper](https://doi.org/10.1/abc)", path.read_text(encoding="utf-8"))

    def test_new_entry_defaults_unchecked_even_when_others_are_checked(self):
        manifest = {"10.1/abc": {"status": "needs_manual", "title": "A Paper", "doi_url": "https://doi.org/10.1/abc"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = write_needs_manual_worklist(manifest, tmp)
            path.write_text(
                path.read_text(encoding="utf-8").replace("- [ ] [A Paper]", "- [x] [A Paper]"),
                encoding="utf-8",
            )

            manifest["10.1/new"] = {"status": "needs_manual", "title": "New Paper", "doi_url": "https://doi.org/10.1/new"}
            write_needs_manual_worklist(manifest, tmp)

            content = path.read_text(encoding="utf-8")
            self.assertIn("- [x] [A Paper](https://doi.org/10.1/abc)", content)
            self.assertIn("- [ ] [New Paper](https://doi.org/10.1/new)", content)


class TestWriteSnowballCandidatesWorklist(unittest.TestCase):
    def test_writes_titled_links_with_target_folder(self):
        manifest = {
            "10.1/abc": {
                "status": "proposed", "title": "A Candidate", "folder": "business",
                "doi_url": "https://doi.org/10.1/abc",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)

            self.assertEqual(path, Path(tmp) / "snowball_candidates.md")
            content = path.read_text(encoding="utf-8")
            self.assertIn("- [ ] [A Candidate](https://doi.org/10.1/abc)", content)
            self.assertIn("research/journal-articles/business/", content)

    def test_shows_relevance_score_and_cited_seed_when_present(self):
        manifest = {
            "10.1/abc": {
                "status": "proposed", "title": "A Candidate", "folder": "business",
                "doi_url": "https://doi.org/10.1/abc", "relevance_score": 0.62,
                "cites_seed": "10.1/seed-paper",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertIn("0.62", content)
            self.assertIn("10.1/seed-paper", content)

    def test_excludes_needs_manual_entries(self):
        manifest = {
            "10.1/manual": {"status": "needs_manual", "title": "Not This One"},
            "10.1/proposed": {"status": "proposed", "title": "This One"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("Not This One", content)
            self.assertIn("This One", content)

    def test_preserves_checked_state_across_regeneration(self):
        manifest = {
            "10.1/abc": {"status": "proposed", "title": "A Candidate", "doi_url": "https://doi.org/10.1/abc"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = write_snowball_candidates_worklist(manifest, tmp)
            path.write_text(
                path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            write_snowball_candidates_worklist(manifest, tmp)

            self.assertIn("- [x] [A Candidate](https://doi.org/10.1/abc)", path.read_text(encoding="utf-8"))

    def test_needs_manual_and_snowball_worklists_track_checks_independently(self):
        manifest = {
            "10.1/manual": {"status": "needs_manual", "title": "Manual One", "doi_url": "https://doi.org/10.1/manual"},
            "10.1/proposed": {"status": "proposed", "title": "Proposed One", "doi_url": "https://doi.org/10.1/proposed"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            manual_path = write_needs_manual_worklist(manifest, tmp)
            snowball_path = write_snowball_candidates_worklist(manifest, tmp)

            manual_path.write_text(
                manual_path.read_text(encoding="utf-8").replace("- [ ] [Manual One]", "- [x] [Manual One]"),
                encoding="utf-8",
            )

            write_needs_manual_worklist(manifest, tmp)
            write_snowball_candidates_worklist(manifest, tmp)

            self.assertIn("- [x] [Manual One]", manual_path.read_text(encoding="utf-8"))
            self.assertIn("- [ ] [Proposed One]", snowball_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
