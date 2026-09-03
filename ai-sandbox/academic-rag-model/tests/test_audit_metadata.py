import tempfile
import unittest
from pathlib import Path

from audit_metadata import check_authors, check_doi, check_title, resolve_paper_paths, select_audit_targets


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


class TestCheckTitle(unittest.TestCase):
    def test_none_when_title_found_in_text(self):
        entry = {"title": "Causal Inference from Hypothetical Evaluations"}
        text = "CAUSAL INFERENCE, FROM Hypothetical-Evaluations!! An abstract follows."
        self.assertIsNone(check_title(entry, text))

    def test_flags_when_title_not_found(self):
        entry = {"title": "A Title That Was Never Printed"}
        text = "This paper is actually about something completely different."
        flag = check_title(entry, text)
        self.assertEqual(flag["type"], "title_mismatch")
        self.assertIn("A Title That Was Never Printed", flag["detail"])

    def test_none_when_no_title_stored(self):
        self.assertIsNone(check_title({}, "any text"))


class TestCheckAuthors(unittest.TestCase):
    def test_none_when_an_author_surname_found(self):
        entry = {"authors": ["Daniel Bjorkegren", "Jane Smith"]}
        text = "This paper, by Bjorkegren and coauthors, studies mobile money."
        self.assertIsNone(check_authors(entry, text))

    def test_flags_when_no_author_found_at_all(self):
        entry = {"authors": ["A. Nobody", "B. Nobody"]}
        text = "This paper was actually written by someone else entirely."
        flag = check_authors(entry, text)
        self.assertEqual(flag["type"], "author_mismatch")

    def test_none_when_no_authors_stored(self):
        self.assertIsNone(check_authors({}, "any text"))


class TestCheckDoi(unittest.TestCase):
    def test_none_when_doi_found(self):
        self.assertIsNone(check_doi("10.1/abc", {}, "Some paper. DOI: 10.1/abc. More text."))

    def test_flags_when_doi_missing(self):
        flag = check_doi("10.1/abc", {}, "Completely unrelated text with no DOI mentioned.")
        self.assertEqual(flag["type"], "doi_mismatch")

    def test_none_for_non_doi_key(self):
        self.assertIsNone(check_doi("https://openalex.org/W1", {}, "any text"))


if __name__ == "__main__":
    unittest.main()
