import unittest
from unittest.mock import patch

from resume_manager.tailor import apply_tailoring, tailor_resume

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [
        {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
         "start_date": "2020", "end_date": "Present", "bullets": ["Grew revenue 30%"]},
        {"id": "globex-1", "org": "Globex", "role": "Analyst", "location": "LA",
         "start_date": "2015", "end_date": "2018", "bullets": ["Built reports"]},
    ],
    "education": [{"id": "school-1", "institution": "State U"}],
    "awards": [{"name": "Award"}],
    "publications": [],
    "skills": [{"category": "Programming", "items": ["Python"]}],
}


class TestTailorResume(unittest.TestCase):
    @patch("resume_manager.tailor.call_ollama")
    def test_prompt_includes_only_id_org_role_bullets_no_other_metadata(self, mock_call):
        mock_call.return_value = "included_ids: [acme-1]\nbullets_by_id:\n  acme-1: [rewritten bullet]"

        tailor_resume(_MASTER, "a job description")

        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("acme-1", prompt_arg)
        self.assertIn("Acme", prompt_arg)
        self.assertIn("Engineer", prompt_arg)
        self.assertIn("Grew revenue 30%", prompt_arg)
        self.assertNotIn("NYC", prompt_arg)
        self.assertNotIn("2020", prompt_arg)

    @patch("resume_manager.tailor.call_ollama", return_value="included_ids: [acme-1]\nbullets_by_id:\n  acme-1: [x]")
    def test_returns_parsed_yaml_dict(self, mock_call):
        result = tailor_resume(_MASTER, "jd")
        self.assertEqual(result, {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["x"]}})

    @patch("resume_manager.tailor.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))

    @patch("resume_manager.tailor.call_ollama", return_value="not valid: [yaml: at all")
    def test_returns_none_on_invalid_yaml(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))

    @patch("resume_manager.tailor.call_ollama", return_value="just_a_string_not_a_mapping")
    def test_returns_none_when_response_is_not_the_expected_shape(self, mock_call):
        self.assertIsNone(tailor_resume(_MASTER, "jd"))


class TestApplyTailoring(unittest.TestCase):
    def test_included_entry_gets_master_metadata_and_rewritten_bullets(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["Rewrote this bullet"]}}
        tailored, problems = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(problems, [])
        self.assertEqual(len(tailored["work_experience"]), 1)
        entry = tailored["work_experience"][0]
        self.assertEqual(entry["org"], "Acme")
        self.assertEqual(entry["location"], "NYC")
        self.assertEqual(entry["start_date"], "2020")
        self.assertEqual(entry["bullets"], ["Rewrote this bullet"])

    def test_excluded_entry_is_dropped(self):
        tailoring_result = {"included_ids": ["acme-1"], "bullets_by_id": {"acme-1": ["x"]}}
        tailored, _ = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual([e["id"] for e in tailored["work_experience"]], ["acme-1"])

    def test_other_categories_pass_through_unchanged(self):
        tailoring_result = {"included_ids": [], "bullets_by_id": {}}
        tailored, _ = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(tailored["contact"], _MASTER["contact"])
        self.assertEqual(tailored["education"], _MASTER["education"])
        self.assertEqual(tailored["awards"], _MASTER["awards"])
        self.assertEqual(tailored["publications"], _MASTER["publications"])
        self.assertEqual(tailored["skills"], _MASTER["skills"])

    def test_unknown_id_is_skipped_and_reported_not_crashed(self):
        tailoring_result = {"included_ids": ["nonexistent"], "bullets_by_id": {}}
        tailored, problems = apply_tailoring(_MASTER, tailoring_result)
        self.assertEqual(tailored["work_experience"], [])
        self.assertTrue(any("nonexistent" in p for p in problems))
