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

    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.page_looks_defective", return_value=False)
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_math_notation_check_is_disabled(self, mock_extract_pages, mock_defective, mock_reader_cls):
        # Real, confirmed false positive (2026-09-26): a resume's own "C3
        # Program Officer" job classification code was flagged as a lost
        # math exponent ("C^3") -- a signal that can only ever be a false
        # positive on prose, never a real lost exponent, since a resume
        # never contains actual math notation to lose in the first place.
        mock_reader_cls.return_value.pages = [object()]
        mock_extract_pages.return_value = ["Program Officer (C3)"]

        extract_resume_text("fake_resume.pdf")

        mock_defective.assert_called_once_with("Program Officer (C3)", check_math_notation=False)

    @patch("resume_manager.extract.PdfReader")
    @patch("resume_manager.extract.extract_all_page_texts")
    def test_real_job_classification_code_is_not_flagged_defective(self, mock_extract_pages, mock_reader_cls):
        # End-to-end regression against the actual real text (not mocked
        # page_looks_defective) from the real failing source document.
        mock_reader_cls.return_value.pages = [object()]
        mock_extract_pages.return_value = [
            "AID/Colombia Program Office – C3 Program Officer (FS 4-9)\n\n"
            "USAID/W Rotations – C3 Program Officer (FS 5-12)"
        ]

        result = extract_resume_text("fake_resume.pdf")

        self.assertIn("C3 Program Officer", result)
