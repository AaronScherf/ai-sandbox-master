import json
import unittest
from unittest.mock import MagicMock, patch

from common.ollama_utils import call_ollama, OLLAMA_TIMEOUT


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
        call_ollama("my prompt", "qwen2.5-math:7b", 30)
        request_arg = mock_urlopen.call_args.args[0]
        body = json.loads(request_arg.data.decode("utf-8"))
        self.assertEqual(body["model"], "qwen2.5-math:7b")
        self.assertEqual(body["prompt"], "my prompt")


if __name__ == "__main__":
    unittest.main()
