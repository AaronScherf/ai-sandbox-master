import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor_resume import build_guidance_text, collect_answers_interactively, run_tailoring

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

    @patch("resume_manager.tailor_resume.render_resume_pdf")
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
    )
    def test_guidance_is_passed_to_tailor_resume_and_persisted(self, mock_tailor, mock_render):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            run_tailoring(
                master_path, jd_path, "Acme Corp", resume_manager_dir,
                guidance="Q: Which role?\nA: emphasize leadership",
            )

            self.assertEqual(mock_tailor.call_args.kwargs["guidance"], "Q: Which role?\nA: emphasize leadership")
            app_dir = os.path.join(
                resume_manager_dir, "applications", os.listdir(os.path.join(resume_manager_dir, "applications"))[0],
            )
            guidance_path = os.path.join(app_dir, "guidance.txt")
            self.assertTrue(os.path.exists(guidance_path))
            with open(guidance_path, encoding="utf-8") as f:
                self.assertIn("emphasize leadership", f.read())

    @patch("resume_manager.tailor_resume.render_resume_pdf")
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
    )
    def test_no_guidance_writes_no_guidance_file(self, mock_tailor, mock_render):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir, master_path, jd_path = self._setup(tmp)

            run_tailoring(master_path, jd_path, "Acme Corp", resume_manager_dir)

            self.assertIsNone(mock_tailor.call_args.kwargs.get("guidance"))
            app_dir = os.path.join(
                resume_manager_dir, "applications", os.listdir(os.path.join(resume_manager_dir, "applications"))[0],
            )
            self.assertFalse(os.path.exists(os.path.join(app_dir, "guidance.txt")))


class TestBuildGuidanceText(unittest.TestCase):
    def test_pairs_each_question_with_its_answer(self):
        text = build_guidance_text(["Q1?", "Q2?"], ["Answer one", "Answer two"])
        self.assertIn("Q: Q1?\nA: Answer one", text)
        self.assertIn("Q: Q2?\nA: Answer two", text)


class TestCollectAnswersInteractively(unittest.TestCase):
    @patch("builtins.input", side_effect=["Answer one", "Answer two"])
    def test_collects_one_answer_per_question_in_order(self, mock_input):
        answers = collect_answers_interactively(["Q1?", "Q2?"])
        self.assertEqual(answers, ["Answer one", "Answer two"])
