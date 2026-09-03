import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reconcile_needs_manual import (
    extract_preview,
    find_converted_md_files,
    is_confirmed_downloaded,
    reconcile,
)


def _write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestFindConvertedMdFiles(unittest.TestCase):
    def test_finds_md_under_processed_outputs_anywhere_in_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _write_md(tmp / "business" / "processed_outputs" / "a.md", "content")
            _write_md(tmp / "business" / "processed_outputs" / "a_pages_cache.json", "{}")
            files = find_converted_md_files(tmp)
            self.assertEqual([f.name for f in files], ["a.md"])

    def test_empty_tree_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(find_converted_md_files(tmp), [])


class TestIsConfirmedDownloaded(unittest.TestCase):
    def test_matches_by_doi_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "Some paper. DOI: 10.1257/pandp.20181032. More text.")
            result = is_confirmed_downloaded("10.1257/pandp.20181032", "Some Title", [md_path])
            self.assertEqual(result, md_path)

    def test_matches_by_normalized_title_when_no_doi_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "**Nostalgic Demand**\n\nAn abstract about consumer behavior.")
            result = is_confirmed_downloaded(None, "Nostalgic Demand", [md_path])
            self.assertEqual(result, md_path)

    def test_title_match_tolerant_of_punctuation_and_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "CAUSAL INFERENCE, FROM Hypothetical-Evaluations!!")
            result = is_confirmed_downloaded(None, "Causal Inference from Hypothetical Evaluations", [md_path])
            self.assertEqual(result, md_path)

    def test_none_when_no_file_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "A completely unrelated paper about something else entirely.")
            result = is_confirmed_downloaded("10.1257/pandp.20181032", "Some Title", [md_path])
            self.assertIsNone(result)

    def test_empty_file_list_returns_none(self):
        self.assertIsNone(is_confirmed_downloaded("10.1/abc", "Title", []))


class TestExtractPreview(unittest.TestCase):
    def test_strips_frontmatter_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "---\nsource_pdf: x.pdf\n---\n\n<!-- page 1 -->\n\nActual paper content starts here.")
            preview = extract_preview(md_path, max_chars=200)
            self.assertNotIn("source_pdf", preview)
            self.assertNotIn("<!--", preview)
            self.assertIn("Actual paper content starts here.", preview)

    def test_truncates_to_max_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            _write_md(md_path, "x" * 500)
            preview = extract_preview(md_path, max_chars=50)
            self.assertEqual(len(preview), 50)


class TestReconcile(unittest.TestCase):
    def test_confirmed_download_marked_and_removed_from_worklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/abc", "needs_manual", folder="business", metadata={
                "title": "A Real Paper", "doi_url": "https://doi.org/10.1/abc",
            })
            save_manifest(path, manifest)

            _write_md(tmp / "business" / "processed_outputs" / "a.md", "Text mentioning 10.1/abc somewhere.")

            result = reconcile(tmp)

            self.assertEqual(len(result["confirmed"]), 1)
            self.assertEqual(result["still_pending"], [])

            updated = load_manifest(path)
            self.assertEqual(updated["10.1/abc"]["status"], "downloaded")

            worklist = (tmp / "needs_manual_downloads.md").read_text(encoding="utf-8")
            self.assertNotIn("A Real Paper", worklist)

    def test_unmatched_entry_stays_pending_and_in_worklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/xyz", "needs_manual", folder="physics", metadata={
                "title": "Not Yet Downloaded", "doi_url": "https://doi.org/10.1/xyz",
            })
            save_manifest(path, manifest)

            result = reconcile(tmp)

            self.assertEqual(result["confirmed"], [])
            self.assertEqual(len(result["still_pending"]), 1)

            worklist = (tmp / "needs_manual_downloads.md").read_text(encoding="utf-8")
            self.assertIn("Not Yet Downloaded", worklist)

    def test_dataset_type_entries_never_considered(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/dataset", "needs_manual", metadata={
                "title": "A Trial Registration", "work_type": "dataset",
            })
            save_manifest(path, manifest)

            result = reconcile(tmp)

            self.assertEqual(result["confirmed"], [])
            self.assertEqual(result["still_pending"], [])


class TestMainChainsAudit(unittest.TestCase):
    def test_main_calls_audit_when_mailto_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "argv", ["reconcile_needs_manual", "--articles-dir", tmp,
                                             "--index-root", tmp]), \
                 patch.dict(os.environ, {"OPENALEX_CONTACT_EMAIL": "me@example.com"}), \
                 patch("reconcile_needs_manual.audit_metadata.audit") as mock_audit:
                mock_audit.return_value = {
                    "audited": 0, "folder_corrections": 0, "tag_syncs": 0, "flagged": 0, "skipped": 0,
                }
                import reconcile_needs_manual
                reconcile_needs_manual.main()
                mock_audit.assert_called_once_with(tmp, tmp, "me@example.com", recheck_all=False)

    def test_main_skips_audit_and_still_succeeds_without_mailto(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_without_mailto = {k: v for k, v in os.environ.items() if k != "OPENALEX_CONTACT_EMAIL"}
            with patch.object(sys, "argv", ["reconcile_needs_manual", "--articles-dir", tmp]), \
                 patch.dict(os.environ, env_without_mailto, clear=True), \
                 patch("reconcile_needs_manual.audit_metadata.audit") as mock_audit:
                import reconcile_needs_manual
                reconcile_needs_manual.main()
                mock_audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
