import unittest
from unittest.mock import patch

from resume_manager.tailor import tailor_resume


class TestTailorResume(unittest.TestCase):
    @patch("resume_manager.tailor.call_ollama")
    def test_prompt_includes_master_and_jd_and_rules(self, mock_call):
        mock_call.return_value = "## Experience\n..."

        tailor_resume("MASTER CONTENT HERE", "JOB DESCRIPTION HERE", model="qwen2.5:7b-instruct")

        prompt_arg = mock_call.call_args[0][0]
        self.assertIn("MASTER CONTENT HERE", prompt_arg)
        self.assertIn("JOB DESCRIPTION HERE", prompt_arg)
        self.assertIn("Do NOT invent", prompt_arg)
        mock_call.assert_called_once_with(prompt_arg, "qwen2.5:7b-instruct", 300)

    @patch("resume_manager.tailor.call_ollama")
    def test_returns_ollama_response_text(self, mock_call):
        mock_call.return_value = "tailored markdown"
        self.assertEqual(tailor_resume("master", "jd"), "tailored markdown")

    @patch("resume_manager.tailor.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(tailor_resume("master", "jd"))
