import tempfile
import unittest
from pathlib import Path

from audit_metadata import resolve_paper_paths, select_audit_targets


class TestSelectAuditTargets(unittest.TestCase):
    def test_includes_fetched_and_downloaded_without_audited_at(self):
        manifest = {
            "10.1/a": {"status": "fetched"},
            "10.1/b": {"status": "downloaded"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual({k for k, _ in targets}, {"10.1/a", "10.1/b"})

    def test_excludes_needs_manual_and_proposed(self):
        manifest = {
            "10.1/a": {"status": "needs_manual"},
            "10.1/b": {"status": "proposed"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual(targets, [])

    def test_skips_already_audited_by_default(self):
        manifest = {
            "10.1/a": {"status": "fetched", "audited_at": "2026-09-01T00:00:00+00:00"},
            "10.1/b": {"status": "fetched"},
        }
        targets = select_audit_targets(manifest, recheck_all=False)
        self.assertEqual([k for k, _ in targets], ["10.1/b"])

    def test_recheck_all_includes_already_audited(self):
        manifest = {"10.1/a": {"status": "fetched", "audited_at": "2026-09-01T00:00:00+00:00"}}
        targets = select_audit_targets(manifest, recheck_all=True)
        self.assertEqual([k for k, _ in targets], ["10.1/a"])


class TestResolvePaperPaths(unittest.TestCase):
    def test_fetched_entry_derives_deterministic_paths(self):
        entry = {"status": "fetched", "folder": "business"}
        pdf_path, md_path = resolve_paper_paths("/articles", "10.1/some-paper", entry)
        self.assertEqual(pdf_path, Path("/articles/business/10-1-some-paper.pdf"))
        self.assertEqual(md_path, Path("/articles/business/processed_outputs/10-1-some-paper.md"))

    def test_fetched_entry_without_folder_returns_none_none(self):
        entry = {"status": "fetched"}
        self.assertEqual(resolve_paper_paths("/articles", "10.1/x", entry), (None, None))

    def test_downloaded_entry_uses_matched_md_path(self):
        entry = {"status": "downloaded", "matched_md_path": "/articles/physics/processed_outputs/weird-name.md"}
        pdf_path, md_path = resolve_paper_paths("/articles", "10.1/x", entry)
        self.assertEqual(md_path, Path("/articles/physics/processed_outputs/weird-name.md"))
        self.assertEqual(pdf_path, Path("/articles/physics/weird-name.pdf"))

    def test_downloaded_entry_without_matched_md_path_returns_none_none(self):
        entry = {"status": "downloaded"}
        self.assertEqual(resolve_paper_paths("/articles", "10.1/x", entry), (None, None))


if __name__ == "__main__":
    unittest.main()
