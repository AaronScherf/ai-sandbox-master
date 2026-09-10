import unittest
from unittest.mock import patch

from resume_manager.extract import DefectivePageError, extract_resume_text


class TestExtractResumeText(unittest.TestCase):
    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.page_looks_defective", return_value=False)
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_builds_page_tagged_markdown_when_clean(self, mock_extract_pages, mock_defective, mock_reader_cls):
        mock_reader_cls.return_value.pages = [object(), object()]
        mock_extract_pages.return_value = ["Page one text", "Page two text"]

        result = extract_resume_text("fake_resume.pdf")

        self.assertIn("<!-- page 1 -->", result)
        self.assertIn("Page one text", result)
        self.assertIn("<!-- page 2 -->", result)
        self.assertIn("Page two text", result)
        self.assertIn("source_pdf: fake_resume.pdf", result)
        self.assertIn("routing: local", result)

    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.page_looks_defective")
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_raises_on_defective_page_instead_of_falling_back(self, mock_extract_pages, mock_defective, mock_reader_cls):
        mock_reader_cls.return_value.pages = [object()]
        mock_extract_pages.return_value = ["garbled"]
        mock_defective.return_value = True

        with self.assertRaises(DefectivePageError):
            extract_resume_text("fake_resume.pdf")
