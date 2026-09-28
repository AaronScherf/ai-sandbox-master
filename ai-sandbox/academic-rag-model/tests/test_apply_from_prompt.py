import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

from resume_manager.apply_from_prompt import (
    brainstorm_relevant_content, create_application_from_prompt, interpret_opportunity_prompt,
)

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [{
        "id": "acme-1", "org": "Acme", "role": "Fraud Analyst", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Reduced fraud losses 20%"],
    }],
    "education": [], "awards": [], "publications": [], "skills": [],
}


def _fake_gemini_response(text):
    response = MagicMock()
    response.text = text
    return response


class TestInterpretOpportunityPrompt(unittest.TestCase):
    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_well_formed_response_returns_job_description_and_name(self, mock_call):
        mock_call.return_value = (
            "job_description: A senior data analyst role focused on fraud detection at a mid-size fintech.\n"
            "application_name: Fintech Co Senior Data Analyst"
        )
        result = interpret_opportunity_prompt("senior data analyst, fraud detection, mid-size fintech")
        self.assertEqual(
            result,
            {
                "job_description": "A senior data analyst role focused on fraud detection at a mid-size fintech.",
                "application_name": "Fintech Co Senior Data Analyst",
            },
        )

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_prompt_includes_the_rough_description(self, mock_call):
        mock_call.return_value = "job_description: JD text\napplication_name: A Name"
        interpret_opportunity_prompt("a rough one-line description of the role")
        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("a rough one-line description of the role", prompt_arg)

    @patch("resume_manager.apply_from_prompt.call_ollama", return_value=None)
    def test_unreachable_ollama_returns_none(self, mock_call):
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_multiline_plain_scalar_with_stray_keys_returns_none(self, mock_call):
        # Real, confirmed bug (found in code review 2026-09-28): a model
        # that writes job_description as an unindented multi-paragraph
        # plain YAML scalar (very natural for a real job description --
        # a "Responsibilities:" section, blank lines) gets it silently
        # truncated to just the first line, with the rest landing in
        # unrelated top-level keys this function never reads -- no error,
        # just a badly-targeted job description with no warning. Detected
        # by rejecting any response with keys beyond the two expected
        # ones, converting a silent truncation into an explicit None.
        mock_call.return_value = (
            "job_description: Senior Data Analyst at Fintech Co.\n\n"
            "Responsibilities:\n- Build fraud models\n- Monitor transactions\n\n"
            "application_name: Fintech Co Senior Data Analyst"
        )
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_well_formed_block_scalar_job_description_captures_full_text(self, mock_call):
        # The correctly-formatted counterpart to the test above -- when
        # the model does use a YAML block scalar for a multi-paragraph
        # job description, the full text must come through intact.
        mock_call.return_value = (
            "application_name: Fintech Co Senior Data Analyst\n"
            "job_description: |\n"
            "  Senior Data Analyst at Fintech Co.\n"
            "\n"
            "  Responsibilities:\n"
            "  - Build fraud models\n"
            "  - Monitor transactions\n"
        )
        result = interpret_opportunity_prompt("a description")
        self.assertEqual(
            result["job_description"],
            "Senior Data Analyst at Fintech Co.\n\nResponsibilities:\n- Build fraud models\n- Monitor transactions",
        )
        self.assertEqual(result["application_name"], "Fintech Co Senior Data Analyst")

    @patch("resume_manager.apply_from_prompt.call_ollama", return_value="not: [valid: yaml: at all")
    def test_malformed_yaml_returns_none(self, mock_call):
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_missing_application_name_key_returns_none(self, mock_call):
        mock_call.return_value = "job_description: Some JD text"
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_missing_job_description_key_returns_none(self, mock_call):
        mock_call.return_value = "application_name: A Name"
        self.assertIsNone(interpret_opportunity_prompt("a description"))

    @patch("resume_manager.apply_from_prompt.call_ollama")
    def test_blank_application_name_returns_none(self, mock_call):
        # Real failure mode this guards against: a technically-present but
        # empty/whitespace-only field would otherwise flow through to
        # run_tailoring() as a blank application folder name.
        mock_call.return_value = 'job_description: Some JD text\napplication_name: "   "'
        self.assertIsNone(interpret_opportunity_prompt("a description"))


class TestBrainstormRelevantContent(unittest.TestCase):
    def test_well_formed_response_is_returned_stripped(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response(
            "  Your Acme fraud analyst role is directly relevant -- lead with it.  \n"
        )
        result = brainstorm_relevant_content(client, _MASTER, "A fraud detection analyst role.")
        self.assertEqual(result, "Your Acme fraud analyst role is directly relevant -- lead with it.")

    def test_prompt_includes_master_resume_and_job_description(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response("guidance text")
        brainstorm_relevant_content(client, _MASTER, "A fraud detection analyst role.")
        call_kwargs = client.models.generate_content.call_args.kwargs
        self.assertIn("Fraud Analyst", call_kwargs["contents"])
        self.assertIn("A fraud detection analyst role.", call_kwargs["contents"])

    def test_exception_from_generate_content_returns_none(self):
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        self.assertIsNone(brainstorm_relevant_content(client, _MASTER, "A job description."))

    def test_blank_response_text_returns_none(self):
        client = MagicMock()
        client.models.generate_content.return_value = _fake_gemini_response("   ")
        self.assertIsNone(brainstorm_relevant_content(client, _MASTER, "A job description."))


class TestCreateApplicationFromPrompt(unittest.TestCase):
    def _write_master(self, tmp):
        resume_manager_dir = os.path.join(tmp, "resume-manager")
        os.makedirs(resume_manager_dir, exist_ok=True)
        with open(os.path.join(resume_manager_dir, "resume_master.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        return resume_manager_dir

    @patch("resume_manager.apply_from_prompt.brainstorm_relevant_content", return_value="Lead with Acme.")
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    @patch("resume_manager.apply_from_prompt.run_tailoring")
    def test_full_pipeline_calls_run_tailoring_with_derived_args(self, mock_run, mock_interpret, mock_brainstorm):
        # jd_path is inside a `with tempfile.TemporaryDirectory()` block
        # that's cleaned up before create_application_from_prompt()
        # returns, so its content must be captured *during* the mocked
        # call (via side_effect), not read afterward -- reading it after
        # the fact would hit a deleted file.
        captured = {}

        def _capture_jd_and_return(master_resume_path, jd_path, application_name, resume_manager_dir_arg, guidance=None):
            with open(jd_path, encoding="utf-8") as f:
                captured["job_description"] = f.read()
            return "Wrote a PDF."

        mock_run.side_effect = _capture_jd_and_return

        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)

            self.assertEqual(result, "Wrote a PDF.")
            mock_run.assert_called_once()
            call_args = mock_run.call_args.args
            self.assertEqual(call_args[2], "Acme Fraud Analyst")  # application_name
            self.assertEqual(call_args[3], resume_manager_dir)
            self.assertEqual(mock_run.call_args.kwargs["guidance"], "Lead with Acme.")
            self.assertEqual(captured["job_description"], "A fraud analyst role.")
            mock_brainstorm.assert_called_once()

    @patch("resume_manager.apply_from_prompt.interpret_opportunity_prompt", return_value=None)
    def test_stage_1_failure_raises_and_never_calls_gemini_or_run_tailoring(self, mock_interpret):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()
            with self.assertRaises(RuntimeError):
                create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)
            client.models.generate_content.assert_not_called()

    @patch("resume_manager.apply_from_prompt.run_tailoring", return_value="Wrote a PDF.")
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    def test_no_gemini_client_skips_stage_2_but_still_tailors(self, mock_interpret, mock_run):
        # Real, expected case: no GEMINI_API_KEY configured yet.
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=None)

            self.assertEqual(result, "Wrote a PDF.")
            self.assertIsNone(mock_run.call_args.kwargs["guidance"])

    @patch("resume_manager.apply_from_prompt.run_tailoring", return_value="Wrote a PDF.")
    @patch("resume_manager.apply_from_prompt.brainstorm_relevant_content", return_value=None)
    @patch(
        "resume_manager.apply_from_prompt.interpret_opportunity_prompt",
        return_value={"job_description": "A fraud analyst role.", "application_name": "Acme Fraud Analyst"},
    )
    def test_stage_2_failure_still_tailors_with_no_guidance(self, mock_interpret, mock_brainstorm, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            resume_manager_dir = self._write_master(tmp)
            client = MagicMock()

            result = create_application_from_prompt("a rough description", resume_manager_dir, gemini_client=client)

            self.assertEqual(result, "Wrote a PDF.")
            self.assertIsNone(mock_run.call_args.kwargs["guidance"])
