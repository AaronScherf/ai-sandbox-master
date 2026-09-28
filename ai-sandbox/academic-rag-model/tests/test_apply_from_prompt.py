import unittest
from unittest.mock import patch

from resume_manager.apply_from_prompt import interpret_opportunity_prompt


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
