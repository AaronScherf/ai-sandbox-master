import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.example_store import ExampleRecord
from viz.llm_fallback import (
    _cache_key, _extract_code, _build_prompt, _call_ollama, _run_generated_code,
    generate_via_llm, MAX_GENERATION_ATTEMPTS, _OLLAMA_TIMEOUT,
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

    def test_extracts_bare_fenced_block_with_no_language_tag(self):
        """Task 11's real trial showed this small local model can be
        unreliable -- a response using a bare ``` fence (no `python` tag)
        should still have its code extracted, not silently fail."""
        text = "Here you go:\n```\nfig = go.Figure()\n```\nEnjoy."
        self.assertEqual(_extract_code(text), "fig = go.Figure()")

    def test_returns_none_when_no_code_block(self):
        self.assertIsNone(_extract_code("no code here"))


class TestBuildPrompt(unittest.TestCase):
    def test_first_attempt_has_no_retry_content(self):
        prompt = _build_prompt("spectral decomposition", "")
        self.assertNotIn("previous attempt", prompt)
        self.assertNotIn("That failed with", prompt)

    def test_retry_attempt_includes_previous_code_and_error(self):
        prompt = _build_prompt(
            "spectral decomposition", "",
            previous_code="fig = go.Figure(layout=dict(bold=True))",
            previous_error="Bad property path:\nbold",
        )
        self.assertIn("fig = go.Figure(layout=dict(bold=True))", prompt)
        self.assertIn("Bad property path:\nbold", prompt)

    def test_retry_without_previous_code_still_includes_error(self):
        prompt = _build_prompt(
            "spectral decomposition", "",
            previous_code=None,
            previous_error="the response contained no ```python code block",
        )
        self.assertIn("no ```python code block", prompt)

    def test_context_included_when_provided(self):
        prompt = _build_prompt("concept", "some course context")
        self.assertIn("some course context", prompt)

    def test_context_omitted_when_empty(self):
        prompt = _build_prompt("concept", "")
        self.assertNotIn("Background from the student", prompt)

    def test_base_prompt_warns_against_exotic_properties(self):
        prompt = _build_prompt("concept", "")
        self.assertIn("Do NOT use speculative or exotic Plotly properties", prompt)

    def test_examples_block_included_when_examples_given(self):
        example = ExampleRecord(
            concept="spectral decomposition", context="", keywords=["spectral"],
            embedding=[0.1], script="fig = go.Figure()  # prior success",
            created_at="2026-09-03T00:00:00+00:00",
        )
        prompt = _build_prompt("eigenvalues", "", examples=[example])
        self.assertIn("fig = go.Figure()  # prior success", prompt)
        self.assertIn("spectral decomposition", prompt)
        self.assertIn("successfully", prompt)

    def test_examples_block_absent_when_examples_none(self):
        prompt = _build_prompt("eigenvalues", "", examples=None)
        self.assertNotIn("generated successfully", prompt)

    def test_examples_block_absent_when_examples_empty_list(self):
        prompt = _build_prompt("eigenvalues", "", examples=[])
        self.assertNotIn("generated successfully", prompt)


class TestCallOllama(unittest.TestCase):
    @patch("viz.llm_fallback.urllib.request.urlopen")
    def test_returns_response_text_on_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "```python\nfig = go.Figure()\n```"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        result = _call_ollama("some composed prompt")
        self.assertIn("fig = go.Figure()", result)

    @patch("viz.llm_fallback.urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_returns_none_on_connection_failure(self, mock_urlopen):
        self.assertIsNone(_call_ollama("some composed prompt"))

    @patch("viz.llm_fallback.urllib.request.urlopen", side_effect=TimeoutError("timed out"))
    def test_returns_timeout_sentinel_on_timeout(self, mock_urlopen):
        """A live-but-slow Ollama call must be distinguishable from a
        genuinely unreachable one -- generate_via_llm's retry loop treats
        the two differently (retry vs. give up immediately)."""
        self.assertIs(_call_ollama("some composed prompt"), _OLLAMA_TIMEOUT)


class TestRunGeneratedCode(unittest.TestCase):
    def test_successful_script_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])"
            success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            self.assertIsNone(error)
            self.assertTrue(os.path.exists(output_path))

    def test_successful_script_writes_fragment_not_full_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])"
            success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            with open(output_path, "r", encoding="utf-8") as f:
                written = f.read()
            self.assertNotIn("<html", written.lower())

    def test_broken_code_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            success, error = _run_generated_code("this is not valid python(((", output_path)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertFalse(os.path.exists(output_path))

    def test_code_with_no_fig_variable_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            success, error = _run_generated_code("x = 1 + 1", output_path)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertFalse(os.path.exists(output_path))

    def test_timeout_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import time\ntime.sleep(5)\nimport plotly.graph_objects as go\nfig = go.Figure()"
            success, error = _run_generated_code(code, output_path, timeout=1)
            self.assertFalse(success)
            self.assertIn("timed out", error)

    @patch("viz.llm_fallback.subprocess.run", side_effect=OSError("spawn failed"))
    def test_subprocess_spawn_failure_returns_false(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure()"
            success, error = _run_generated_code(code, output_path)
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertFalse(os.path.exists(output_path))

    def test_generated_code_cannot_see_a_secret_env_var_present_in_the_test_process(self):
        """A paid API key (GEMINI_API_KEY, loaded via load_dotenv_override()
        elsewhere in this project) must never reach LLM-generated code's
        subprocess. Sets a marker env var in THIS test process's own
        os.environ, then has the generated script report (via a real
        plotly figure's title, inspected by reading the written HTML)
        whether it can see that var -- confirming the subprocess does
        not inherit the parent's environment."""
        marker_name = "VIZ_TEST_SECRET_MARKER"
        os.environ[marker_name] = "leaked-if-inherited"
        self.addCleanup(os.environ.pop, marker_name, None)
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = (
                "import os\n"
                "import plotly.graph_objects as go\n"
                f"seen = os.environ.get({marker_name!r})\n"
                "title = 'ABSENT' if seen is None else f'LEAKED:{seen}'\n"
                "fig = go.Figure(layout=dict(title=title))\n"
            )
            success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            self.assertIsNone(error)
            with open(output_path, "r", encoding="utf-8") as f:
                html = f.read()
            self.assertIn("ABSENT", html)
            self.assertNotIn("leaked-if-inherited", html)

    def test_subprocess_runs_with_a_minimal_env_not_the_full_os_environ(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure()"
            with patch("viz.llm_fallback.subprocess.run", wraps=__import__("subprocess").run) as mock_run:
                success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            _, kwargs = mock_run.call_args
            self.assertIn("env", kwargs)
            self.assertNotEqual(kwargs["env"], dict(os.environ))
            self.assertNotIn("GEMINI_API_KEY", kwargs["env"])

    def test_subprocess_runs_with_a_scratch_cwd_not_the_caller_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure()"
            with patch("viz.llm_fallback.subprocess.run", wraps=__import__("subprocess").run) as mock_run:
                success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            _, kwargs = mock_run.call_args
            self.assertIn("cwd", kwargs)
            self.assertNotEqual(os.path.abspath(kwargs["cwd"]), os.path.abspath(os.getcwd()))


class TestGenerateViaLlm(unittest.TestCase):
    def test_output_file_is_wrapped_and_fragment_html_is_the_raw_cached_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<div>fake plot</div>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="```python\nfig = go.Figure()\n```"), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.fragment_html, "<div>fake plot</div>")
            with open(output_path, "r", encoding="utf-8") as f:
                written = f.read()
            self.assertIn("<html>", written)
            self.assertIn("<div>fake plot</div>", written)

    def test_cache_hit_populates_fragment_html_from_cached_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            os.makedirs(cache_dir)
            key = _cache_key("concept", "")
            with open(os.path.join(cache_dir, f"{key}.html"), "w", encoding="utf-8") as f:
                f.write("<div>cached plot</div>")
            output_path = os.path.join(tmp, "out.html")

            with patch("viz.llm_fallback.example_store.find_examples") as mock_find, \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama") as mock_call:
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            mock_call.assert_not_called()
            mock_find.assert_not_called()
            mock_save.assert_not_called()
            self.assertEqual(result.fragment_html, "<div>cached plot</div>")
            with open(output_path, "r", encoding="utf-8") as f:
                written = f.read()
            self.assertIn("<html>", written)
            self.assertIn("<div>cached plot</div>", written)

    def test_returns_none_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value=None) as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying (spec §4)

    def test_returns_none_when_no_code_block_extracted_after_exhausting_all_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="no code here") as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, MAX_GENERATION_ATTEMPTS)

    def test_retries_after_ollama_timeout_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch(
                    "viz.llm_fallback._call_ollama",
                    side_effect=[_OLLAMA_TIMEOUT, "```python\nfig = go.Figure()\n```"],
                 ) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertEqual(mock_call.call_count, 2)
            second_prompt = mock_call.call_args_list[1].args[0]
            self.assertIn("timed out", second_prompt)

    def test_returns_none_when_ollama_times_out_on_every_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value=_OLLAMA_TIMEOUT) as mock_call:
                result = generate_via_llm(
                    "concept", "", os.path.join(tmp, "out.html"),
                    os.path.join(tmp, "cache"), os.path.join(tmp, "examples"),
                )
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, MAX_GENERATION_ATTEMPTS)

    def test_success_copies_cached_file_to_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "course", "concept.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", return_value="```python\nfig = go.Figure()\n```"), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))

    def test_cache_hit_skips_ollama_call_and_example_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            os.makedirs(cache_dir)
            key = _cache_key("concept", "")
            with open(os.path.join(cache_dir, f"{key}.html"), "w", encoding="utf-8") as f:
                f.write("<html>cached</html>")
            output_path = os.path.join(tmp, "out.html")

            with patch("viz.llm_fallback.example_store.find_examples") as mock_find, \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama") as mock_call:
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            mock_call.assert_not_called()
            mock_find.assert_not_called()
            mock_save.assert_not_called()
            self.assertEqual(result.source, "llm_fallback")
            self.assertTrue(os.path.exists(output_path))

    def test_recovers_after_one_failed_attempt_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",  # attempt 1: bad property
                "```python\nfig = go.Figure()\n```",                        # attempt 2: fixed
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertEqual(mock_call.call_count, 2)
            second_prompt = mock_call.call_args_list[1].args[0]
            self.assertIn("Bad property path", second_prompt)
            self.assertIn("bold=True", second_prompt)

    def test_only_the_successful_attempt_is_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    self.assertFalse(os.path.exists(path))  # nothing cached from the failed attempt
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            cache_key = _cache_key("concept", "")
            cached_path = os.path.join(cache_dir, f"{cache_key}.html")
            self.assertTrue(os.path.exists(cached_path))
            with open(cached_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "<html>fake</html>")

    def test_examples_are_injected_into_the_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            example = ExampleRecord(
                concept="spectral decomposition", context="", keywords=["spectral"],
                embedding=[0.1], script="fig = go.Figure()  # prior success",
                created_at="2026-09-03T00:00:00+00:00",
            )

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[example]), \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch(
                    "viz.llm_fallback._call_ollama",
                    return_value="```python\nfig = go.Figure()\n```",
                 ) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertIsNotNone(result)
            prompt = mock_call.call_args_list[0].args[0]
            self.assertIn("fig = go.Figure()  # prior success", prompt)

    def test_find_examples_called_once_across_multiple_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]) as mock_find, \
                 patch("viz.llm_fallback.example_store.save"), \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            self.assertEqual(mock_find.call_count, 1)

    def test_save_called_once_with_final_successful_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")

            responses = [
                "```python\nfig = go.Figure(layout=dict(bold=True))\n```",
                "```python\nfig = go.Figure()\n```",
            ]

            def fake_run(code, path, timeout=60):
                if "bold=True" in code:
                    return False, "Bad property path:\nbold"
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)

            mock_save.assert_called_once_with("concept", "", "fig = go.Figure()", examples_dir)

    def test_save_not_called_when_every_attempt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            examples_dir = os.path.join(tmp, "examples")
            output_path = os.path.join(tmp, "out.html")
            with patch("viz.llm_fallback.example_store.find_examples", return_value=[]), \
                 patch("viz.llm_fallback.example_store.save") as mock_save, \
                 patch("viz.llm_fallback._call_ollama", return_value="no code here"):
                generate_via_llm("concept", "", output_path, cache_dir, examples_dir)
            mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
