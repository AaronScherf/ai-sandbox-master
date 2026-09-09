import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.convert_resume import bootstrap_resume
from resume_manager.extract import DefectivePageError


def _parsed_resume():
    return {
        "contact": {
            "name": "Aaron", "location": "USA", "email": "a@x.com",
            "linkedin_url": "l", "github_url": "g", "website_url": "w",
        },
        "work_experience": [
            {"org": "Acme", "role": "Engineer", "location": "NYC", "start_date": "2020",
             "end_date": "Present", "bullets": ["Did a thing"]},
            {"org": "Acme", "role": "Director", "location": "NYC", "start_date": "2018",
             "end_date": "2020", "bullets": ["Did another thing"]},
        ],
        "education": [], "awards": [], "publications": [], "skills": [],
    }


class TestBootstrapResume(unittest.TestCase):
    def _make_fake_pdf(self, tmp):
        path = os.path.join(tmp, "source.pdf")
        with open(path, "w", encoding="utf-8") as f:
            f.write("fake pdf bytes")
        return path

    @patch("resume_manager.convert_resume.verify_extraction", return_value=[])
    @patch("resume_manager.convert_resume.extract_resume_schema")
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_clean_pass_writes_master_yaml_with_assigned_ids(self, mock_extract, mock_schema, mock_verify):
        mock_schema.return_value = _parsed_resume()
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume.pdf")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
            self.assertTrue(os.path.exists(master_path))
            with open(master_path, encoding="utf-8") as f:
                written = yaml.safe_load(f)
            self.assertEqual([e["id"] for e in written["work_experience"]], ["acme-1", "acme-2"])
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.yaml")))

    @patch("resume_manager.convert_resume.verify_extraction", return_value=["some field problem"])
    @patch("resume_manager.convert_resume.extract_resume_schema")
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_flagged_mismatch_writes_review_not_master(self, mock_extract, mock_schema, mock_verify):
        mock_schema.return_value = _parsed_resume()
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.yaml")))
            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "resume_master.review.yaml")))

    @patch("resume_manager.convert_resume.extract_resume_text", side_effect=DefectivePageError("page 1 looks defective"))
    def test_defective_page_propagates(self, mock_extract):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            with self.assertRaises(DefectivePageError):
                bootstrap_resume(source_pdf, resume_manager_dir)

    @patch("resume_manager.convert_resume.extract_resume_schema", return_value=None)
    @patch("resume_manager.convert_resume.extract_resume_text", return_value="raw text")
    def test_ollama_failure_still_leaves_raw_extraction_on_disk(self, mock_extract, mock_schema):
        with tempfile.TemporaryDirectory() as tmp:
            source_pdf = self._make_fake_pdf(tmp)
            resume_manager_dir = os.path.join(tmp, "resume-manager")

            bootstrap_resume(source_pdf, resume_manager_dir)

            self.assertTrue(os.path.exists(os.path.join(resume_manager_dir, "processed_outputs", "resume_raw.md")))
            self.assertFalse(os.path.exists(os.path.join(resume_manager_dir, "resume_master.yaml")))
