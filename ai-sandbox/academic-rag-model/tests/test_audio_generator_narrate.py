import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT

from audio_generator.narrate import narrate_for_speech

_LONG_PARAGRAPH_A = "Consider the random variable X. " * 60  # ~2000 chars
_LONG_PARAGRAPH_B = "Its expectation is written as follows. " * 60  # ~2400 chars


class TestNarrateForSpeechChunking(unittest.TestCase):
    @patch("audio_generator.narrate.call_ollama")
    def test_calls_ollama_once_per_paragraph_when_short(self, mock_call):
        mock_call.return_value = "A rewritten sentence long enough to pass the sanity check easily here."
        md_text = "First short paragraph.\n\nSecond short paragraph."
        narrate_for_speech(md_text)
        self.assertEqual(mock_call.call_count, 1)  # both paragraphs fit in one ~2-3K chunk together

    @patch("audio_generator.narrate.call_ollama")
    def test_splits_into_multiple_chunks_when_content_is_large(self, mock_call):
        mock_call.return_value = "A rewritten passage, long enough to pass the sanity check easily. " * 30
        md_text = f"{_LONG_PARAGRAPH_A}\n\n{_LONG_PARAGRAPH_B}\n\n{_LONG_PARAGRAPH_A}"
        narrate_for_speech(md_text)
        self.assertGreater(mock_call.call_count, 1)

    @patch("audio_generator.narrate.call_ollama")
    def test_never_sends_a_code_block_to_the_llm(self, mock_call):
        mock_call.return_value = None  # doesn't matter -- assert it's never called with code content
        md_text = "Before the code.\n\n```python\nprint('should never reach the LLM')\n```\n\nAfter the code."
        result = narrate_for_speech(md_text)
        for call_args in mock_call.call_args_list:
            self.assertNotIn("print(", call_args[0][0])
        self.assertIn("print('should never reach the LLM')", result)  # passed through untouched


class TestNarrateForSpeechRetryAndFallback(unittest.TestCase):
    @patch("audio_generator.narrate.call_ollama")
    def test_successful_rewrite_is_used(self, mock_call):
        mock_call.return_value = "The expected value of X is written as follows, a nice long rewrite."
        result = narrate_for_speech("Short original text with $E[X]$ in it.")
        self.assertEqual(result, mock_call.return_value)
        self.assertEqual(mock_call.call_count, 1)

    @patch("audio_generator.narrate.call_ollama")
    def test_none_response_falls_back_immediately_with_no_retry(self, mock_call):
        mock_call.return_value = None
        original = "Some original text with $E[X]$ that the LLM can't reach."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 1)  # no retry against an unreachable server

    @patch("audio_generator.narrate.call_ollama")
    def test_timeout_retries_once_then_succeeds(self, mock_call):
        mock_call.side_effect = [OLLAMA_TIMEOUT, "The rewritten version, long enough to pass the sanity check."]
        result = narrate_for_speech("Some original text with $E[X]$ in it, long enough for a ratio check.")
        self.assertEqual(result, "The rewritten version, long enough to pass the sanity check.")
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_timeout_retries_once_then_falls_back(self, mock_call):
        mock_call.side_effect = [OLLAMA_TIMEOUT, OLLAMA_TIMEOUT]
        original = "Some original text with $E[X]$ that keeps timing out on every attempt made."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_too_short_response_retries_once_then_falls_back(self, mock_call):
        original = "A" * 200  # long original
        mock_call.side_effect = ["no", "no"]  # both far too short relative to `original`
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(mock_call.call_count, 2)

    @patch("audio_generator.narrate.call_ollama")
    def test_too_short_response_retries_once_then_succeeds(self, mock_call):
        original = "A" * 200
        mock_call.side_effect = ["no", "B" * 150]  # second attempt passes the ratio check
        result = narrate_for_speech(original)
        self.assertEqual(result, "B" * 150)
        self.assertEqual(mock_call.call_count, 2)
