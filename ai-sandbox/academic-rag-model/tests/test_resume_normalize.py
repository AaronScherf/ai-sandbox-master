import unittest
from unittest.mock import patch

from resume_manager.normalize import normalize_resume_text, verify_normalization


class TestNormalizeResumeText(unittest.TestCase):
    @patch("resume_manager.normalize.call_ollama")
    def test_returns_ollama_response_text(self, mock_call):
        mock_call.return_value = "## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing"
        result = normalize_resume_text("raw text here", model="qwen2.5:7b-instruct")
        self.assertEqual(result, "## Experience\n### Acme — Engineer (2020 – Present)\n- Did a thing")
        mock_call.assert_called_once()
        self.assertEqual(mock_call.call_args[0][1], "qwen2.5:7b-instruct")

    @patch("resume_manager.normalize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(normalize_resume_text("raw text here"))


class TestVerifyNormalization(unittest.TestCase):
    def test_clean_reformat_has_no_problems(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue 30%"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%"
        self.assertEqual(verify_normalization(raw, normalized), [])

    def test_dropped_metric_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue 30%"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue"
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("30%" in p for p in problems))

    def test_invented_metric_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue"
        normalized = "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue 30%"
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("30%" in p for p in problems))

    def test_invented_entry_is_flagged(self):
        raw = "Acme Corp 2020 - Present\nEngineer\n- Grew revenue"
        normalized = (
            "## Experience\n### Acme Corp — Engineer (2020 – Present)\n- Grew revenue\n\n"
            "### Globex — CTO (2018 – 2020)\n- Ran things"
        )
        problems = verify_normalization(raw, normalized)
        self.assertTrue(any("Globex" in p for p in problems))
