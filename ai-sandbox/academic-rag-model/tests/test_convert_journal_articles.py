import os
import tempfile
import unittest
from unittest.mock import patch

from journal_articles.convert_journal_articles import (
    _JOURNAL_DOC_TYPES,
    _page_count,
    discover_pdf_files,
)


def _write_fake_pdf(path: str, contents: bytes = b"fake pdf bytes") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(contents)


class TestDiscoverPdfFiles(unittest.TestCase):
    def test_finds_pdfs_in_thematic_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "economics", "a.pdf"))
            _write_fake_pdf(os.path.join(tmp, "misc", "b.pdf"))
            files = discover_pdf_files(tmp)
            self.assertEqual(
                sorted(os.path.basename(f) for f in files), ["a.pdf", "b.pdf"],
            )

    def test_finds_pdfs_nested_deeper_than_one_level(self):
        # The user explicitly noted subfolders may go deeper than the
        # current one-level thematic split (economics/, misc/) -- must
        # not assume a fixed depth.
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "economics", "development", "a.pdf"))
            files = discover_pdf_files(tmp)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith(os.path.join("development", "a.pdf")))

    def test_filters_to_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "economics", "a.pdf"))
            _write_fake_pdf(os.path.join(tmp, "misc", "b.pdf"))
            files = discover_pdf_files(tmp, file_filter="b.pdf")
            self.assertEqual([os.path.basename(f) for f in files], ["b.pdf"])

    def test_missing_directory_returns_empty_list(self):
        self.assertEqual(discover_pdf_files("/no/such/dir"), [])

    def test_ignores_non_pdf_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "economics", "notes.txt"))
            self.assertEqual(discover_pdf_files(tmp), [])

    def test_results_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "misc", "z.pdf"))
            _write_fake_pdf(os.path.join(tmp, "economics", "a.pdf"))
            files = discover_pdf_files(tmp)
            self.assertEqual(files, sorted(files))

    def test_excludes_zotero_storage_folder(self):
        # Confirmed real 2026-09-02: a Zotero library synced into this
        # same directory tree puts its own attachment copies under
        # zotero/storage/<hash>/ -- not a topic folder, and often a
        # duplicate of a PDF already converted elsewhere in the tree.
        # Recursive discovery must not treat Zotero's own storage as a
        # source of new papers to convert.
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "misc", "a.pdf"))
            _write_fake_pdf(os.path.join(tmp, "zotero", "storage", "ABCD1234", "a.pdf"))
            files = discover_pdf_files(tmp)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith(os.path.join("misc", "a.pdf")))

    def test_excludes_local_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_fake_pdf(os.path.join(tmp, "misc", "a.pdf"))
            _write_fake_pdf(os.path.join(tmp, "local", "a.pdf"))
            files = discover_pdf_files(tmp)
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith(os.path.join("misc", "a.pdf")))


class TestPageCount(unittest.TestCase):
    def test_counts_pages_of_a_real_pdf(self):
        try:
            from pypdf import PdfWriter
        except ImportError:
            self.skipTest("pypdf not installed")

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "a.pdf")
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            writer.add_blank_page(width=72, height=72)
            with open(pdf_path, "wb") as f:
                writer.write(f)
            self.assertEqual(_page_count(pdf_path), 2)

    def test_unreadable_pdf_returns_none_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "bad.pdf")
            _write_fake_pdf(pdf_path, b"not a real pdf")
            self.assertIsNone(_page_count(pdf_path))


class TestJournalDocTypes(unittest.TestCase):
    def test_is_a_frozenset_containing_journal_article(self):
        self.assertEqual(_JOURNAL_DOC_TYPES, frozenset({"journal_article"}))


class TestMainOversizedPageGate(unittest.TestCase):
    def test_oversized_pdf_is_flagged_and_process_pdf_is_never_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = os.path.join(tmp, "journal-articles")
            _write_fake_pdf(os.path.join(articles_dir, "misc", "book.pdf"))

            with patch("journal_articles.convert_journal_articles._page_count", return_value=402), \
                 patch("journal_articles.convert_journal_articles.process_pdf") as mock_process, \
                 patch("journal_articles.convert_journal_articles.get_gemini_client"), \
                 patch("journal_articles.convert_journal_articles.load_dotenv_override"), \
                 patch("sys.argv", [
                     "convert_journal_articles.py",
                     "--articles-dir", articles_dir, "--index-root", tmp, "--max-pages", "150",
                 ]):
                from journal_articles.convert_journal_articles import main
                main()
            mock_process.assert_not_called()

    def test_normal_sized_pdf_is_passed_to_process_pdf_with_journal_doc_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = os.path.join(tmp, "journal-articles")
            pdf_path = os.path.join(articles_dir, "economics", "paper.pdf")
            _write_fake_pdf(pdf_path)

            with patch("journal_articles.convert_journal_articles._page_count", return_value=21), \
                 patch("journal_articles.convert_journal_articles.process_pdf") as mock_process, \
                 patch("journal_articles.convert_journal_articles.get_gemini_client"), \
                 patch("journal_articles.convert_journal_articles.load_dotenv_override"), \
                 patch("sys.argv", [
                     "convert_journal_articles.py",
                     "--articles-dir", articles_dir, "--index-root", tmp, "--max-pages", "150",
                 ]):
                from journal_articles.convert_journal_articles import main
                main()
            mock_process.assert_called_once()
            args, kwargs = mock_process.call_args
            self.assertEqual(args[0], pdf_path)
            self.assertEqual(args[3], tmp)  # index-root passed as academic_hub_root
            self.assertEqual(kwargs["known_doc_types"], _JOURNAL_DOC_TYPES)


if __name__ == "__main__":
    unittest.main()
