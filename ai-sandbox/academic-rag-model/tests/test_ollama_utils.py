import json
import unittest
from unittest.mock import MagicMock, patch

from common.ollama_utils import call_ollama, call_ollama_embeddings, OLLAMA_TIMEOUT, _estimate_num_ctx


class TestCallOllama(unittest.TestCase):
    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_returns_response_text_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "some text"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = call_ollama("some prompt", "some-model", 30)
        self.assertEqual(result, "some text")

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(call_ollama("some prompt", "some-model", 30))

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=TimeoutError("timed out"))
    def test_returns_timeout_sentinel_on_timeout(self, mock_urlopen):
        """A live-but-slow Ollama call must be distinguishable from a
        genuinely unreachable one -- callers' retry loops treat the two
        differently (retry vs. give up immediately)."""
        self.assertIs(call_ollama("some prompt", "some-model", 30), OLLAMA_TIMEOUT)

    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_request_body_uses_the_given_model_and_prompt(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "ok"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        call_ollama("my prompt", "qwen2-math:7b", 30)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertEqual(body["model"], "qwen2-math:7b")
        self.assertEqual(body["prompt"], "my prompt")

    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_request_sets_num_ctx_large_enough_for_a_long_prompt(self, mock_urlopen):
        # Real finding: Ollama silently defaults to ~2048 tokens of
        # context and keeps only the *tail* of a longer prompt with no
        # error -- confirmed live against a real ~22,000-token, 3-video
        # synthesis prompt (prompt_eval_count came back 2050). A prompt
        # this long must request a correspondingly large num_ctx.
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "ok"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        long_prompt = "x" * 88000  # ~22,000 estimated tokens
        call_ollama(long_prompt, "qwen2.5:7b-instruct", 30)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertGreater(body["options"]["num_ctx"], 22000)

    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_request_num_ctx_floors_at_4096_for_a_short_prompt(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "ok"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        call_ollama("short prompt", "qwen2.5:7b-instruct", 30)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertEqual(body["options"]["num_ctx"], 4096)

    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_explicit_num_ctx_overrides_the_estimate(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "ok"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        call_ollama("short prompt", "qwen2.5:7b-instruct", 30, num_ctx=4096)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertEqual(body["options"]["num_ctx"], 4096)


class TestEstimateNumCtx(unittest.TestCase):
    def test_scales_with_prompt_length(self):
        self.assertLess(_estimate_num_ctx("x" * 100), _estimate_num_ctx("x" * 100000))

    def test_rounds_up_to_a_2048_step(self):
        self.assertEqual(_estimate_num_ctx("x" * 100) % 2048, 0)


class TestCallOllamaEmbeddings(unittest.TestCase):
    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_returns_embedding_vector_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = call_ollama_embeddings("some text", "nomic-embed-text", 30)
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(call_ollama_embeddings("some text", "nomic-embed-text", 30))

    @patch("common.ollama_utils.urllib.request.urlopen", side_effect=TimeoutError("timed out"))
    def test_returns_timeout_sentinel_on_timeout(self, mock_urlopen):
        self.assertIs(call_ollama_embeddings("some text", "nomic-embed-text", 30), OLLAMA_TIMEOUT)

    @patch("common.ollama_utils.urllib.request.urlopen")
    def test_request_sets_num_ctx_from_text_length(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"embedding": [0.1]}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        call_ollama_embeddings("short text", "nomic-embed-text", 30)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertEqual(body["options"]["num_ctx"], 4096)


if __name__ == "__main__":
    unittest.main()
