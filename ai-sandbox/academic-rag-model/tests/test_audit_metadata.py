import tempfile
import unittest
from pathlib import Path

from audit_metadata import check_authors, check_title, resolve_paper_paths, select_audit_targets


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


from unittest.mock import patch

from indexer.index_card import compute_file_id, load_courses, load_shard, save_shard
from audit_metadata import apply_folder_correction, check_folder


def _fake_work(concepts):
    from journal_discovery.discovery import Work
    return Work(openalex_id="https://openalex.org/W1", doi="10.1/abc", title="T",
                authors=[], year=2024, abstract=None, concepts=concepts)


class TestCheckFolder(unittest.TestCase):
    @patch("audit_metadata.resolve_work_by_doi")
    def test_no_mismatch_when_folder_already_matches(self, mock_resolve):
        mock_resolve.return_value = _fake_work(["Business"])
        result = check_folder("10.1/abc", {"folder": "business"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertEqual(result["new_folder"], "business")

    @patch("audit_metadata.resolve_work_by_doi")
    def test_mismatch_when_concept_now_differs(self, mock_resolve):
        mock_resolve.return_value = _fake_work(["Sociology"])
        result = check_folder("10.1/abc", {"folder": "grasp"}, "me@example.com")
        self.assertTrue(result["mismatch"])
        self.assertEqual(result["new_folder"], "sociology")

    def test_skipped_for_non_doi_key(self):
        result = check_folder("https://openalex.org/W1", {"folder": "misc"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertIsNotNone(result["error"])

    @patch("audit_metadata.resolve_work_by_doi")
    def test_error_when_lookup_fails(self, mock_resolve):
        mock_resolve.return_value = None
        result = check_folder("10.1/abc", {"folder": "misc"}, "me@example.com")
        self.assertFalse(result["mismatch"])
        self.assertIsNotNone(result["error"])


class TestApplyFolderCorrection(unittest.TestCase):
    def test_moves_files_and_updates_index_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "misc" / "paper.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            meta_path = pdf_path.with_suffix(".meta.json")
            meta_path.write_text("{}", encoding="utf-8")
            md_path = tmp / "misc" / "processed_outputs" / "paper.md"
            md_path.parent.mkdir(parents=True)
            md_path.write_text("content", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "path": "misc/processed_outputs/paper.md",
                                            "source_pdf_path": "misc/paper.pdf", "course": "misc",
                                            "embedding": [1.0], "tags": []}])

            entry = {"folder": "misc"}
            new_pdf, new_md = apply_folder_correction(tmp, str(tmp), entry, pdf_path, md_path, "business")

            self.assertTrue(new_pdf.exists())
            self.assertTrue(new_md.exists())
            self.assertFalse(pdf_path.exists())
            self.assertTrue((tmp / "business" / "paper.meta.json").exists())
            self.assertEqual(entry["folder"], "business")
            self.assertEqual(load_shard(str(tmp), "business")[0]["course"], "business")
            self.assertEqual(load_courses(str(tmp))["business"]["file_count"], 1)

    def test_moves_without_meta_json_for_manually_downloaded_papers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "misc" / "weird-name.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "misc" / "processed_outputs" / "weird-name.md"
            md_path.parent.mkdir(parents=True)
            md_path.write_text("content", encoding="utf-8")

            entry = {"folder": "misc"}
            new_pdf, new_md = apply_folder_correction(tmp, str(tmp), entry, pdf_path, md_path, "sociology")

            self.assertTrue(new_pdf.exists())
            self.assertTrue(new_md.exists())


from audit_metadata import apply_tag_sync, check_tag_sync


class TestCheckTagSync(unittest.TestCase):
    def test_no_mismatch_when_frontmatter_already_matches_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: [economics, mobile-money]\n---\n\nBody text.", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["economics", "mobile-money"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["mismatch"])
            self.assertTrue(result["found_card"])

    def test_mismatch_when_frontmatter_out_of_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: []\n---\n\nBody text.", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["real-tag"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertTrue(result["mismatch"])
            self.assertEqual(result["index_tags"], ["real-tag"])

    def test_no_card_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("---\ntags: []\n---\n\nBody text.", encoding="utf-8")

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["found_card"])
            self.assertFalse(result["mismatch"])

    def test_no_frontmatter_tags_line_skips_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pdf_path = tmp / "a.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake")
            md_path = tmp / "a.md"
            md_path.write_text("no frontmatter at all here", encoding="utf-8")

            file_id = compute_file_id(str(pdf_path))
            save_shard(str(tmp), "misc", [{"file_id": file_id, "tags": ["real-tag"]}])

            result = check_tag_sync(str(tmp), pdf_path, md_path)
            self.assertFalse(result["mismatch"])


class TestApplyTagSync(unittest.TestCase):
    def test_rewrites_frontmatter_tags_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "a.md"
            md_path.write_text("---\nsource_pdf: a.pdf\ntags: []\n---\n\nBody text.", encoding="utf-8")
            apply_tag_sync(md_path, ["economics", "mobile-money"])
            content = md_path.read_text(encoding="utf-8")
            self.assertIn("tags: [economics, mobile-money]", content)
            self.assertIn("Body text.", content)
            self.assertIn("source_pdf: a.pdf", content)


from journal_discovery.manifest import load_manifest, manifest_path, record_outcome, save_manifest
from audit_metadata import audit


def _write_pdf_and_md(folder: Path, stem: str, md_text: str) -> tuple[Path, Path]:
    pdf_path = folder / f"{stem}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    md_path = folder / "processed_outputs" / f"{stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md_text, encoding="utf-8")
    return pdf_path, md_path


class TestAudit(unittest.TestCase):
    @patch("audit_metadata.resolve_work_by_doi")
    def test_clean_paper_gets_audited_with_no_flags(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(
                tmp / "business", stem,
                "---\ntags: []\n---\n\nA Real Paper. DOI: 10.1/abc. By Jane Doe.",
            )
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "A Real Paper", "authors": ["Jane Doe"]})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Real Paper", authors=[], year=2024, abstract=None,
                                              concepts=["Business"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["audited"], 1)
            self.assertEqual(result["flagged"], 0)
            updated = load_manifest(manifest_file)
            self.assertIn("audited_at", updated["10.1/abc"])
            self.assertNotIn("audit_flags", updated["10.1/abc"])

    @patch("audit_metadata.resolve_work_by_doi")
    def test_title_mismatch_gets_flagged_and_written_to_worklist(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(
                tmp / "business", stem,
                "---\ntags: []\n---\n\nCompletely different content. DOI: 10.1/abc.",
            )
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "A Title Never Printed", "doi_url": "https://doi.org/10.1/abc"})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Title Never Printed", authors=[], year=2024,
                                              abstract=None, concepts=["Business"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["flagged"], 1)
            updated = load_manifest(manifest_file)
            self.assertEqual(updated["10.1/abc"]["audit_flags"][0]["type"], "title_mismatch")
            worklist = (tmp / "metadata_audit_flags.md").read_text(encoding="utf-8")
            self.assertIn("A Title Never Printed", worklist)

    def test_already_audited_paper_skipped_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="business",
                            metadata={"title": "X", "audited_at": "2026-09-01T00:00:00+00:00"})
            save_manifest(manifest_file, manifest)

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)
            self.assertEqual(result["audited"], 0)

    @patch("audit_metadata.resolve_work_by_doi")
    def test_folder_mismatch_moves_files_and_counts_correction(self, mock_resolve):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stem = "10-1-abc"
            _write_pdf_and_md(tmp / "grasp", stem, "---\ntags: []\n---\n\nA Real Paper. DOI: 10.1/abc.")
            manifest_file = manifest_path(tmp)
            manifest = load_manifest(manifest_file)
            record_outcome(manifest, "10.1/abc", "fetched", folder="grasp", metadata={"title": "A Real Paper"})
            save_manifest(manifest_file, manifest)

            from journal_discovery.discovery import Work
            mock_resolve.return_value = Work(openalex_id="https://openalex.org/W1", doi="10.1/abc",
                                              title="A Real Paper", authors=[], year=2024, abstract=None,
                                              concepts=["Sociology"])

            result = audit(tmp, str(tmp), "me@example.com", recheck_all=False)

            self.assertEqual(result["folder_corrections"], 1)
            self.assertTrue((tmp / "sociology" / f"{stem}.pdf").exists())
            updated = load_manifest(manifest_file)
            self.assertEqual(updated["10.1/abc"]["folder"], "sociology")


if __name__ == "__main__":
    unittest.main()
