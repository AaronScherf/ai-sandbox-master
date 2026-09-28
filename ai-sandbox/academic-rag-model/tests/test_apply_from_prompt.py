import unittest
from unittest.mock import MagicMock, patch

from resume_manager.apply_from_prompt import brainstorm_relevant_content, interpret_opportunity_prompt

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
