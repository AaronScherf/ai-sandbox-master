import time
import unittest
from unittest.mock import MagicMock, patch

from audio_generator.narrate import _call_gemini, _classify_chunk, narrate_for_speech

_LONG_PARAGRAPH_A = "Consider the random variable $X$. " * 60  # ~2100 chars, has math -> not skipped
_LONG_PARAGRAPH_B = "Its expectation $E[X]$ is written as follows. " * 60  # ~2900 chars


def _client_returning(text: str) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


class TestClassifyChunk(unittest.TestCase):
    def test_pure_prose_is_skip(self):
        self.assertEqual(_classify_chunk("Just plain prose, no math at all here."), "skip")

    def test_stray_greek_letter_outside_dollar_signs_is_not_skip(self):
        self.assertNotEqual(_classify_chunk("The parameter α controls the rate."), "skip")

    def test_sparse_simple_inline_math_is_light(self):
        chunk = "Consider the random variable X. " * 20 + "Its mean is $E[X]$."
        self.assertEqual(_classify_chunk(chunk), "light")

    def test_dense_dollar_spans_is_heavy(self):
        chunk = "$" + "x^2 + y^2 = z^2 " * 40 + "$"
        self.assertEqual(_classify_chunk(chunk), "heavy")

    def test_many_backslash_commands_is_heavy(self):
        chunk = r"Short text. $\mathbb{E}[X] = \sum_{x} x \mathbb{P}(X = x) \cdot \int f(x)$."
        self.assertEqual(_classify_chunk(chunk), "heavy")

    def test_begin_environment_is_always_heavy_regardless_of_ratio(self):
        chunk = r"Short lead-in. $\begin{align} x &= 1 \end{align}$"
        self.assertEqual(_classify_chunk(chunk), "heavy")


class TestCallGemini(unittest.TestCase):
    def test_returns_response_text_on_success(self):
        client = _client_returning("A rewritten passage.")
        result = _call_gemini("prompt", "gemini-3.1-flash-lite", client)
        self.assertEqual(result, "A rewritten passage.")

    def test_passes_the_given_model_and_prompt(self):
        client = _client_returning("response")
        _call_gemini("my specific prompt", "gemini-2.5-flash", client)
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-2.5-flash")
        self.assertEqual(kwargs["contents"], "my specific prompt")

    def test_strips_whitespace_from_response(self):
        client = _client_returning("  response with padding  \n")
        result = _call_gemini("prompt", "gemini-3.1-flash-lite", client)
        self.assertEqual(result, "response with padding")

    def test_returns_none_when_call_with_retries_raises(self):
        client = MagicMock()
        with patch("audio_generator.narrate.call_with_retries", side_effect=Exception("quota exceeded")):
            result = _call_gemini("prompt", "gemini-3.1-flash-lite", client)
        self.assertIsNone(result)


@patch("audio_generator.narrate.load_dotenv_override")
@patch("audio_generator.narrate.get_gemini_client")
class TestNarrateForSpeechChunking(unittest.TestCase):
    def test_calls_gemini_once_per_paragraph_when_short(self, mock_get_client, mock_dotenv):
        client = _client_returning("A rewritten sentence long enough to pass the sanity check easily here.")
        mock_get_client.return_value = client
        md_text = "First short paragraph with $x$.\n\nSecond short paragraph with $y$."
        narrate_for_speech(md_text)
        self.assertEqual(client.models.generate_content.call_count, 1)  # both paragraphs fit in one ~2-3K chunk together

    def test_splits_into_multiple_chunks_when_content_is_large(self, mock_get_client, mock_dotenv):
        client = _client_returning("A rewritten passage, long enough to pass the sanity check easily. " * 30)
        mock_get_client.return_value = client
        md_text = f"{_LONG_PARAGRAPH_A}\n\n{_LONG_PARAGRAPH_B}\n\n{_LONG_PARAGRAPH_A}"
        narrate_for_speech(md_text)
        self.assertGreater(client.models.generate_content.call_count, 1)

    def test_never_sends_a_code_block_to_gemini(self, mock_get_client, mock_dotenv):
        client = _client_returning("irrelevant")
        mock_get_client.return_value = client
        md_text = ("Before the code with $x$.\n\n```python\nprint('should never reach the LLM')\n```"
                   "\n\nAfter the code with $y$.")
        result = narrate_for_speech(md_text)
        for call_args in client.models.generate_content.call_args_list:
            self.assertNotIn("print(", call_args.kwargs["contents"])
        self.assertIn("print('should never reach the LLM')", result)  # passed through untouched

    def test_pure_prose_chunk_makes_no_api_call(self, mock_get_client, mock_dotenv):
        client = _client_returning("irrelevant")
        mock_get_client.return_value = client
        result = narrate_for_speech("Just plain prose, no math at all in this note.")
        client.models.generate_content.assert_not_called()
        self.assertEqual(result, "Just plain prose, no math at all in this note.")

    def test_no_client_falls_back_to_unmodified_text(self, mock_get_client, mock_dotenv):
        mock_get_client.return_value = None  # missing/invalid GEMINI_API_KEY
        original = "Some text with $E[X]$ in it that needs a client to rewrite."
        result = narrate_for_speech(original)
        self.assertEqual(result, original)


@patch("audio_generator.narrate.load_dotenv_override")
@patch("audio_generator.narrate.get_gemini_client")
class TestNarrateForSpeechFallback(unittest.TestCase):
    def test_successful_rewrite_is_used(self, mock_get_client, mock_dotenv):
        client = _client_returning("The expected value of X is written as follows, a nice long rewrite.")
        mock_get_client.return_value = client
        result = narrate_for_speech("Short original text with $E[X]$ in it.")
        self.assertEqual(result, "The expected value of X is written as follows, a nice long rewrite.")
        self.assertEqual(client.models.generate_content.call_count, 1)

    def test_gemini_call_failure_falls_back_to_unmodified_text(self, mock_get_client, mock_dotenv):
        client = MagicMock()
        mock_get_client.return_value = client
        original = "Some original text with $E[X]$ that the API can't reach."
        with patch("audio_generator.narrate.call_with_retries", side_effect=Exception("exhausted")):
            result = narrate_for_speech(original)
        self.assertEqual(result, original)

    def test_too_short_response_falls_back_with_no_second_call(self, mock_get_client, mock_dotenv):
        client = _client_returning("no")  # far too short relative to the original
        mock_get_client.return_value = client
        original = "A" * 200 + " with $E[X]$ in it"
        result = narrate_for_speech(original)
        self.assertEqual(result, original)
        self.assertEqual(client.models.generate_content.call_count, 1)  # no local retry -- call_with_retries already tried


@patch("audio_generator.narrate.load_dotenv_override")
@patch("audio_generator.narrate.get_gemini_client")
class TestNarrateForSpeechParallelDispatch(unittest.TestCase):
    def test_preserves_chunk_order_even_when_the_first_chunk_finishes_last(self, mock_get_client, mock_dotenv):
        client = MagicMock()

        def _side_effect(*, model, contents, config):
            if "FIRST-CHUNK-MARKER" in contents:
                time.sleep(0.05)  # finishes after the second chunk despite being submitted first
                return MagicMock(text="Rewritten first chunk, long enough to pass the sanity check. " * 20)
            return MagicMock(text="Rewritten second chunk, long enough to pass the sanity check. " * 20)

        client.models.generate_content.side_effect = _side_effect
        mock_get_client.return_value = client

        first_chunk = "FIRST-CHUNK-MARKER with $x$ in it. " * 60
        second_chunk = "SECOND-CHUNK-MARKER with $y$ in it. " * 60
        result = narrate_for_speech(f"{first_chunk}\n\n{second_chunk}")

        self.assertLess(result.index("Rewritten first"), result.index("Rewritten second"))

    def test_dispatches_chunks_concurrently_not_one_at_a_time(self, mock_get_client, mock_dotenv):
        client = MagicMock()

        def _side_effect(*, model, contents, config):
            time.sleep(0.15)
            return MagicMock(text="A rewritten passage long enough to pass the sanity check easily here yes.")

        client.models.generate_content.side_effect = _side_effect
        mock_get_client.return_value = client

        md_text = "\n\n".join(f"Chunk number {i} with $x_{i}$ in it. " * 60 for i in range(5))
        start = time.monotonic()
        narrate_for_speech(md_text)
        elapsed = time.monotonic() - start

        # 5 chunks x 0.15s each: sequential would take >= 0.75s; concurrent (up to
        # AUDIOGEN_NARRATE_MAX_WORKERS=5 at once, the default) should be well under that.
        self.assertLess(elapsed, 0.5)
