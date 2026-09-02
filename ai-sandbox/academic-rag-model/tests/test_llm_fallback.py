import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.llm_fallback import (
    _cache_key, _extract_code, _call_ollama, _run_generated_code, generate_via_llm,
)


class TestCacheKey(unittest.TestCase):
    def test_same_inputs_produce_same_key(self):
        self.assertEqual(_cache_key("concept", "context"), _cache_key("concept", "context"))

    def test_different_inputs_produce_different_keys(self):
        self.assertNotEqual(_cache_key("concept a", "x"), _cache_key("concept b", "x"))


class TestExtractCode(unittest.TestCase):
    def test_extracts_fenced_python_block(self):
        text = "Here you go:\n```python\nfig = go.Figure()\n```\nEnjoy."
        self.assertEqual(_extract_code(text), "fig = go.Figure()")

    def test_returns_none_when_no_code_block(self):
        self.assertIsNone(_extract_code("no code here"))


class TestCallOllama(unittest.TestCase):
    @patch("viz.llm_fallback.urllib.request.urlopen")
    def test_returns_response_text_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "```python\nfig = go.Figure()\n```"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = _call_ollama("spectral decomposition", "")
        self.assertIn("fig = go.Figure()", result)

    @patch("viz.llm_fallback.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(_call_ollama("concept", ""))


class TestRunGeneratedCode(unittest.TestCase):
    def test_successful_script_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])"
            self.assertTrue(_run_generated_code(code, output_path))
            self.assertTrue(os.path.exists(output_path))

    def test_broken_code_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            self.assertFalse(_run_generated_code("this is not valid python(((", output_path))
            self.assertFalse(os.path.exists(output_path))

    def test_code_with_no_fig_variable_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            self.assertFalse(_run_generated_code("x = 1 + 1", output_path))
            self.assertFalse(os.path.exists(output_path))

    def test_timeout_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import time\ntime.sleep(5)\nimport plotly.graph_objects as go\nfig = go.Figure()"
            self.assertFalse(_run_generated_code(code, output_path, timeout=1))


class TestGenerateViaLlm(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback._call_ollama", return_value=None):
                result = generate_via_llm("concept", "", os.path.join(tmp, "out.html"), os.path.join(tmp, "cache"))
        self.assertIsNone(result)

    def test_returns_none_when_no_code_block_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback._call_ollama", return_value="no code here"):
                result = generate_via_llm("concept", "", os.path.join(tmp, "out.html"), os.path.join(tmp, "cache"))
        self.assertIsNone(result)

    def test_success_copies_cached_file_to_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            output_path = os.path.join(tmp, "course", "concept.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True

            with patch("viz.llm_fallback._call_ollama", return_value="```python\nfig = go.Figure()\n```"), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))

    def test_cache_hit_skips_ollama_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            os.makedirs(cache_dir)
            key = _cache_key("concept", "")
            with open(os.path.join(cache_dir, f"{key}.html"), "w", encoding="utf-8") as f:
                f.write("<html>cached</html>")
            output_path = os.path.join(tmp, "out.html")

            with patch("viz.llm_fallback._call_ollama") as mock_call:
                result = generate_via_llm("concept", "", output_path, cache_dir)
            mock_call.assert_not_called()
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))


if __name__ == "__main__":
    unittest.main()
