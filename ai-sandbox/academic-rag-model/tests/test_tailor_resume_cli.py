import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor_resume import (
    _select_work_experience_bullets, build_guidance_text, collect_answers_interactively, run_tailoring,
)

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

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"ranked_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
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
            tailored_md_path = os.path.join(app_dir, "tailored_resume.md")
            self.assertTrue(os.path.exists(tailored_md_path))
            with open(tailored_md_path, encoding="utf-8") as f:
                self.assertIn("Did a rewritten thing", f.read())
            # Called once by the fill-loop search (scratch path) and once
            # more for the final authoritative render (spec §13b).
            self.assertEqual(mock_render.call_count, 2)
            final_call = mock_render.call_args_list[-1]
            self.assertEqual(final_call.args[1], os.path.join(app_dir, "Tailored_Resume.pdf"))

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

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"ranked_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
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

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    @patch(
        "resume_manager.tailor_resume.tailor_resume",
        return_value={"ranked_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Did a rewritten thing"]}},
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


class TestSelectWorkExperienceBullets(unittest.TestCase):
    _MULTI_ENTRY_MASTER = {
        "work_experience": [
            {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
             "start_date": "2020", "end_date": "Present", "bullets": ["a1", "a2"]},
            {"id": "globex-1", "org": "Globex", "role": "Analyst", "location": "LA",
             "start_date": "2015", "end_date": "2018", "bullets": ["b1", "b2"]},
            {"id": "initech-1", "org": "Initech", "role": "Consultant", "location": "Austin",
             "start_date": "2010", "end_date": "2014", "bullets": ["c1"]},
        ],
        "education": [], "awards": [], "publications": [], "skills": [],
    }

    def test_no_ranked_ids_returns_empty_budget(self):
        tailoring_result = {"ranked_ids": [], "bullets_by_id": {}}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {})

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    def test_entry_missing_from_bullets_by_id_falls_back_to_master_bullets(self, mock_render):
        # Real, confirmed bug (2026-09-26): a lower-ranked entry the LLM
        # ranked but forgot to rewrite bullets for was treated as having
        # zero bullets and silently skipped with no attempt at all, even
        # when there was clearly still room for more content on the page.
        tailoring_result = {
            "ranked_ids": ["acme-1", "initech-1"],
            "bullets_by_id": {"acme-1": ["a1", "a2"]},  # initech-1 missing entirely
        }
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {"acme-1": 2, "initech-1": 1})

    def test_ranked_id_unknown_to_master_is_skipped_without_crashing(self):
        tailoring_result = {"ranked_ids": ["nonexistent"], "bullets_by_id": {}}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {})

    @patch("resume_manager.tailor_resume.render_resume_pdf", side_effect=[1, 3])
    def test_stops_mid_entry_at_the_last_bullet_that_still_fits(self, mock_render):
        # Real gap this fixes (2026-09-26): a whole-entry-only fill loop
        # would drop this entire entry if its 2nd bullet overflowed, even
        # though the 1st bullet alone left room to spare. Bullet-level
        # granularity keeps that 1st bullet instead of leaving it blank.
        tailoring_result = {"ranked_ids": ["acme-1", "globex-1"], "bullets_by_id": {
            "acme-1": ["a1", "a2"], "globex-1": ["b1", "b2"],
        }}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {"acme-1": 1})
        self.assertEqual(mock_render.call_count, 2)

    @patch("resume_manager.tailor_resume.render_resume_pdf", side_effect=[1, 1, 3])
    def test_moves_to_the_next_entry_once_the_current_one_is_exhausted(self, mock_render):
        tailoring_result = {"ranked_ids": ["acme-1", "globex-1"], "bullets_by_id": {
            "acme-1": ["a1"], "globex-1": ["b1", "b2"],
        }}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {"acme-1": 1, "globex-1": 1})

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=1)
    def test_uses_every_bullet_of_every_entry_when_all_fit(self, mock_render):
        tailoring_result = {"ranked_ids": ["acme-1", "globex-1", "initech-1"], "bullets_by_id": {
            "acme-1": ["a1", "a2"], "globex-1": ["b1", "b2"], "initech-1": ["c1"],
        }}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {"acme-1": 2, "globex-1": 2, "initech-1": 1})

    @patch("resume_manager.tailor_resume.render_resume_pdf", return_value=5)
    def test_top_entrys_first_bullet_is_included_even_if_it_overflows(self, mock_render):
        # Even the smallest possible candidate (one bullet) overflows
        # target_pages here -- still returns one bullet of the top entry
        # rather than an empty budget, matching render_resume_pdf's own
        # "accept overflow at the readable floor" philosophy (spec §6).
        tailoring_result = {"ranked_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["a1", "a2"]}}
        budget = _select_work_experience_bullets(self._MULTI_ENTRY_MASTER, tailoring_result, 2, "scratch.pdf")
        self.assertEqual(budget, {"acme-1": 1})


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
