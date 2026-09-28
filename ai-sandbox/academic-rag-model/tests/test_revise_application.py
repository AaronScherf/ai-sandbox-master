import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor_resume import run_tailoring
from resume_manager.revise_application import remove_work_experience_entry

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [
        {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
        },
        {
            "id": "bloomfield-1", "org": "Bloomfield Community Empowerment Center", "role": "Economic Analyst",
            "location": "Macon, GA", "start_date": "2015", "end_date": "2016", "bullets": ["Collected data"],
        },
    ],
    "education": [], "awards": [], "publications": [], "skills": [],
}

_TAILORING_RESULT = {
    "ranked_ids": ["acme-1", "bloomfield-1"],
    "bullets_by_id": {
        "acme-1": ["Did a rewritten thing"],
        "bloomfield-1": ["Collected data for the region"],
    },
}


def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestRemoveWorkExperienceEntry(unittest.TestCase):
    def _build_application(self, tmp, guidance=None, user_facts=None, brainstorm_status="not used"):
        """Creates a real tailored application directory the same way the
        live pipeline would (mocking only the LLM/render calls), so tests
        exercise the actual on-disk file formats rather than hand-built
        fixtures."""
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        jd_path = os.path.join(tmp, "jd.txt")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write("Looking for a monitoring and evaluation consultant.")

        with patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1), \
             patch("resume_manager.tailor_resume.tailor_resume", return_value=_TAILORING_RESULT):
            run_tailoring(
                master_path, jd_path, "Acme Corp", resume_manager_dir,
                guidance=guidance, user_facts=user_facts, brainstorm_status=brainstorm_status,
            )

        app_dirs = os.listdir(os.path.join(resume_manager_dir, "applications"))
        app_dir = os.path.join(resume_manager_dir, "applications", app_dirs[0])
        return resume_manager_dir, master_path, app_dir

    def test_entry_is_removed_from_tailored_yaml_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp)

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            with open(os.path.join(app_dir, "tailored_resume.yaml"), encoding="utf-8") as f:
                tailored = yaml.safe_load(f)
            ids = [e["id"] for e in tailored["work_experience"]]
            self.assertEqual(ids, ["acme-1"])

            with open(os.path.join(app_dir, "tailored_resume.md"), encoding="utf-8") as f:
                md = f.read()
            self.assertIn("Did a rewritten thing", md)
            self.assertNotIn("Bloomfield", md)

    def test_master_resume_file_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp)
            before = _sha256(master_path)

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            self.assertEqual(_sha256(master_path), before)

    def test_job_description_and_guidance_are_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp, guidance="Prioritize Acme.")
            jd_before = _sha256(os.path.join(app_dir, "job_description.txt"))
            guidance_before = _sha256(os.path.join(app_dir, "guidance.txt"))

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            self.assertEqual(_sha256(os.path.join(app_dir, "job_description.txt")), jd_before)
            self.assertEqual(_sha256(os.path.join(app_dir, "guidance.txt")), guidance_before)

    def test_pdf_is_rerendered_with_the_reduced_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp)

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1) as mock_render:
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            mock_render.assert_called_once()
            rendered_resume = mock_render.call_args.args[0]
            ids = [e["id"] for e in rendered_resume["work_experience"]]
            self.assertEqual(ids, ["acme-1"])

    def test_validation_report_is_refreshed_and_preserves_brainstorm_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(
                tmp, brainstorm_status="failed; local tailoring continued without Gemini brainstorm",
            )

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            with open(os.path.join(app_dir, "validation_report.txt"), encoding="utf-8") as f:
                report = f.read()
            self.assertIn("Relevance brainstorm: failed; local tailoring continued without Gemini brainstorm.", report)

    def test_removed_entrys_tagged_fact_is_now_reported_as_unreflected(self):
        facts = [{
            "entry_id": "bloomfield-1", "fact": "Collected data for the region.",
            "required_concepts": [["region"]],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp, user_facts=facts)

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            with open(os.path.join(app_dir, "validation_report.txt"), encoding="utf-8") as f:
                report = f.read()
            self.assertIn("bloomfield-1: user-provided fact not fully reflected", report)

    def test_old_style_report_without_brainstorm_line_falls_back_to_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp)
            with open(os.path.join(app_dir, "validation_report.txt"), "w", encoding="utf-8") as f:
                f.write("Validation: no discrepancies flagged.")

            with patch("resume_manager.revise_application.render_resume_pdf", return_value=1):
                remove_work_experience_entry(app_dir, "bloomfield-1", resume_manager_dir)

            with open(os.path.join(app_dir, "validation_report.txt"), encoding="utf-8") as f:
                report = f.read()
            self.assertIn("Relevance brainstorm: unknown", report)

    def test_unknown_entry_id_raises_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, app_dir = self._build_application(tmp)
            tailored_path = os.path.join(app_dir, "tailored_resume.yaml")
            before = _sha256(tailored_path)

            with self.assertRaisesRegex(ValueError, "not found"):
                remove_work_experience_entry(app_dir, "does-not-exist", resume_manager_dir)

            self.assertEqual(_sha256(tailored_path), before)

    def test_missing_application_directory_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                remove_work_experience_entry(os.path.join(tmp, "no-such-app"), "acme-1")

    def test_application_directory_missing_tailored_yaml_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = os.path.join(tmp, "resume-manager", "applications", "empty-app")
            os.makedirs(app_dir)
            with self.assertRaises(FileNotFoundError):
                remove_work_experience_entry(app_dir, "acme-1")


if __name__ == "__main__":
    unittest.main()
