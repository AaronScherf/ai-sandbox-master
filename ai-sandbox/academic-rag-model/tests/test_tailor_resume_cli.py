import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor_resume import run_tailoring

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [{
        "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
    }],
    "education": [], "awards": [], "publications": [], "skills": [],
}


class TestRunTailoring(unittest.TestCase):
    def _setup(self, tmp):
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        jd_path = os.path.join(tmp, "jd.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write("Looking for an engineer.")
        return resume_manager_dir, master_path, jd_path

    @patch("resume_manager.tailor_resume.render_resume_pdf")
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
    )
    def test_writes_all_application_outputs(self, mock_tailor, mock_render):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            run_tailoring(master_path, jd_path, "Acme Corp", resume_manager_dir)

            app_dirs = os.listdir(os.path.join(resume_manager_dir, "applications"))
            self.assertEqual(len(app_dirs), 1)
            self.assertTrue(app_dirs[0].endswith("-acme-corp"))
            app_dir = os.path.join(resume_manager_dir, "applications", app_dirs[0])
            self.assertTrue(os.path.exists(os.path.join(app_dir, "job_description.txt")))
            tailored_path = os.path.join(app_dir, "tailored_resume.yaml")
            self.assertTrue(os.path.exists(tailored_path))
            with open(tailored_path, encoding="utf-8") as f:
                tailored = yaml.safe_load(f)
            self.assertEqual(tailored["work_experience"][0]["bullets"], ["Did a rewritten thing"])
            self.assertEqual(tailored["work_experience"][0]["org"], "Acme")
            self.assertTrue(os.path.exists(os.path.join(app_dir, "validation_report.txt")))
            mock_render.assert_called_once()

    def test_missing_master_resume_raises_before_any_ollama_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = os.path.join(tmp, "resume-manager")
            jd_path = os.path.join(tmp, "jd.txt")
            with open(jd_path, "w", encoding="utf-8") as f:
                f.write("jd")

            with self.assertRaises(FileNotFoundError):
                run_tailoring(
                    os.path.join(resume_manager_dir, "resume_master.yaml"), jd_path, "acme", resume_manager_dir,
                )

    def test_missing_jd_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, _jd_path = self._setup(tmp)

            with self.assertRaises(FileNotFoundError):
                run_tailoring(master_path, os.path.join(tmp, "does_not_exist.txt"), "acme", resume_manager_dir)

    @patch("resume_manager.tailor_resume.tailor_resume", return_value=None)
    def test_ollama_failure_raises_runtime_error(self, mock_tailor):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            with self.assertRaises(RuntimeError):
                run_tailoring(master_path, jd_path, "acme", resume_manager_dir)
