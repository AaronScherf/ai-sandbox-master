import os
import tempfile
import unittest
from unittest.mock import patch

from resume_manager.convert_resume import bootstrap_resume
from resume_manager.extract import DefectivePageError


class TestBootstrapResume(unittest.TestCase):
    def _make_fake_pdf(self, tmp):
        path = os.path.join(tmp, "source.pdf")
        with open(path, "w", encoding="utf-8") as f:
            f.write("fake pdf bytes")
        return path

    @patch("resume_manager.convert_resume.verify_normalization", return_value=[])
    @patch(
        "resume_manager.convert_resume.normalize_resume_text",
        return_value="## Experience\n### Acme — Eng (2020 – Present)\n- Did a thing",
    )
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_clean_pass_writes_master_not_review(self, mock_extract, mock_normalize, mock_verify):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume.pdf")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            master_path = os.path.join(resume_manager_dir, "resume_master.md")
            self.assertTrue(os.path.exists(master_path))
            with open(master_path, encoding="utf-8") as f:
                self.assertIn("Acme", f.read())
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.md")))

    @patch(
        "resume_manager.convert_resume.verify_normalization",
        return_value=["metric '30%' found in raw extraction but missing from normalized output"],
    )
    @patch(
        "resume_manager.convert_resume.normalize_resume_text",
        return_value="## Experience\n### Acme — Eng (2020 – Present)\n- Did a thing",
    )
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text with 30%")
    def test_flagged_mismatch_writes_review_not_master(self, mock_extract, mock_normalize, mock_verify):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.md")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.md")))

    @patch("resume_manager.convert_resume.extract_resume_text", side_effect=DefectivePageError("page 1 looks defective"))
    def test_defective_page_propagates(self, mock_extract):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            with self.assertRaises(DefectivePageError):
                bootstrap_resume(source_pdf, resume_manager_dir)

    @patch("resume_manager.convert_resume.normalize_resume_text", return_value=None)
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_ollama_failure_still_leaves_raw_extraction_on_disk(self, mock_extract, mock_normalize):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.md")))
