# Viz Ollama Fallback Retry-Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden `viz/llm_fallback.py`'s Ollama code-generation fallback with a bounded validate-and-retry loop, so a generated script that fails (as observed twice in real usage — invalid Plotly properties) gets fed its own error back and a chance to fix it, instead of failing outright on the first try.

**Architecture:** Split `_call_ollama`'s prompt-building out into a new `_build_prompt()` function that can compose either a first-attempt prompt or a retry prompt (previous code + previous error folded in); change `_run_generated_code()` to return its failure reason alongside success/failure so the retry loop has something concrete to feed back; wrap `generate_via_llm()`'s single-shot flow in a `MAX_GENERATION_ATTEMPTS = 3` loop built from those two pieces. All three changes are internal to `viz/llm_fallback.py` — no other file's interface changes.

**Tech Stack:** Python 3, existing `viz/` dependencies only (no new ones), `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`

## Global Constraints

- **No new paid API calls.** This change touches only the free, local Ollama path — unchanged from the original visualization-agent spec's constraint.
- **The "never raises past its caller" contract is unchanged and must hold for every failure path**, new or old: a bad/missing code block, a non-zero exit code, a timeout, an unreachable Ollama server, and now an exhausted retry budget — every one of these degrades to `None` (or `(False, <error text>)` for the lower-level `_run_generated_code`), never an uncaught exception.
- `MAX_GENERATION_ATTEMPTS = 3` is a plain module-level constant, **not** env-overridable — matches `EXECUTION_TIMEOUT_SECONDS`'s existing precedent in this file (only `OLLAMA_MODEL` is env-overridable, via `VIZ_OLLAMA_MODEL`, because swapping models is a real per-machine need; a retry budget isn't).
- **Only a genuinely successful generation attempt is ever written to the disk cache** — a failed intermediate attempt must never leave a file behind at the cache path.
- Test runner: `./.venv/Scripts/python.exe -m unittest discover -s tests` (run from `ai-sandbox/academic-rag-model/`). Every task's failing-test step must actually be run and confirmed failing before implementing (TDD, per this repo's established practice).
- Package-qualified absolute imports only, never relative imports (existing `viz/` convention, unaffected by this change but binding on any new code).

---

## File Structure

```
ai-sandbox/academic-rag-model/
  viz/
    llm_fallback.py                                # MODIFIED -- _build_prompt() (new),
                                                     # _call_ollama(prompt) (signature change),
                                                     # _run_generated_code() -> tuple[bool, str|None]
                                                     # (return type change), generate_via_llm()
                                                     # retry loop (body rewrite), MAX_GENERATION_ATTEMPTS
                                                     # (new constant), tightened _PROMPT_TEMPLATE
  tests/
    test_llm_fallback.py                            # MODIFIED -- new TestBuildPrompt class; updated
                                                     # TestCallOllama, TestRunGeneratedCode,
                                                     # TestGenerateViaLlm tests
  docs/2026-09-02-visualization-agent-status.md      # MODIFIED (Task 4) -- retry-hardening
                                                     # real-corpus validation section appended
```

No other file changes. `viz/viz_agent.py`, the template tier, and the tutor integration (`rag/rag_agent.py`, CLI wiring) are all explicitly out of scope per the spec's non-goals.

---

## Task 1: `_build_prompt()` + `_call_ollama(prompt)` refactor + tightened base prompt

**Files:**
- Modify: `ai-sandbox/academic-rag-model/viz/llm_fallback.py`
- Modify: `ai-sandbox/academic-rag-model/tests/test_llm_fallback.py`

**Interfaces:**
- Produces: `_build_prompt(concept: str, context: str, previous_code: str | None = None, previous_error: str | None = None) -> str` — consumed by Task 3's retry loop.
- Modifies: `_call_ollama(prompt: str) -> str | None` — signature changes from `(concept, context)` to `(prompt)`. Consumed by Task 3.

This task does **not** touch `generate_via_llm()` — its existing (pre-Task-3) call site, `_call_ollama(concept, context)`, is left as-is for now. Every existing test that reaches it does so with `_call_ollama` mocked (via `unittest.mock.patch`), so a mismatched call signature there doesn't fail any test until Task 3 rewrites that call site for real. This mirrors this project's own established pattern of an intentionally not-yet-wired call site between tasks (see the original visualization-agent plan's Task 5, which left `generate_visualization()`'s no-match branch as a stub for Task 7 to wire up).

- [ ] **Step 1: Write the failing tests**

In `tests/test_llm_fallback.py`, change the import line at the top from:

```python
from viz.llm_fallback import (
    _cache_key, _extract_code, _call_ollama, _run_generated_code, generate_via_llm,
)
```

to:

```python
from viz.llm_fallback import (
    _cache_key, _extract_code, _build_prompt, _call_ollama, _run_generated_code, generate_via_llm,
)
```

Insert a new `TestBuildPrompt` class right after `TestExtractCode` (before `TestCallOllama`):

```python
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
```

Change `TestCallOllama`'s two existing tests to call `_call_ollama` with the new single-argument signature:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: FAIL — the whole module fails to import (`ImportError: cannot import name '_build_prompt' from 'viz.llm_fallback'`), since `_build_prompt` doesn't exist yet.

- [ ] **Step 3: Implement**

In `viz/llm_fallback.py`, replace the `_PROMPT_TEMPLATE` definition:

```python
_PROMPT_TEMPLATE = """Write a single self-contained Python script that uses the `plotly` and \
`numpy` libraries to create an interactive visualization illustrating this concept: {concept}

{context_block}
Requirements:
- Assign the finished figure to a variable named exactly `fig` (a plotly.graph_objects.Figure).
- Do not call fig.show(), fig.write_html(), or write any file yourself -- the caller handles that.
- Do not import anything other than plotly (as go or px) and numpy.
- Prefer simple, well-documented trace types: go.Scatter, go.Bar, go.Contour, go.Surface. Stick to
  basic layout options: fig.update_layout(title=...), axis labels via xaxis_title/yaxis_title.
- Do NOT use speculative or exotic Plotly properties you are not certain exist (e.g. text styling
  properties like "bold", or a "z" property on a trace type that does not support one). If unsure
  whether a property exists, leave it out rather than guessing.
- Respond with ONLY one fenced ```python code block, nothing else.
"""
```

Add `_build_prompt()` right before `_call_ollama()`, and replace `_call_ollama()` itself:

```python
def _build_prompt(
    concept: str, context: str,
    previous_code: str | None = None, previous_error: str | None = None,
) -> str:
    """Composes the prompt sent to Ollama. First attempt (previous_error
    is None): the base concept+context prompt. Retry attempt
    (previous_error set): the same base prompt plus the previous
    attempt's code (if any -- omitted when extraction itself failed,
    since there's no code to show) and the exact error it produced,
    asking for a corrected script (spec:
    docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md
    §3)."""
    context_block = f"Background from the student's own course materials:\n{context}\n" if context else ""
    base = _PROMPT_TEMPLATE.format(concept=concept, context_block=context_block)
    if previous_error is None:
        return base
    previous_code_block = (
        f"Your previous attempt produced this script:\n```python\n{previous_code}\n```\n"
        if previous_code else ""
    )
    return (
        f"{base}\n"
        f"{previous_code_block}"
        f"That failed with:\n{previous_error}\n"
        f"Write a corrected script that fixes this specific problem. Respond with ONLY one "
        f"fenced ```python code block, nothing else."
    )


def _call_ollama(prompt: str) -> str | None:
    print(f"Generating a visualization via the local Ollama model ({OLLAMA_MODEL}) -- "
          f"this can take up to a minute...")
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("response")
    except Exception as err:
        print(f"WARNING: Ollama call failed ({err}) -- is `ollama serve` running and "
              f"has `ollama pull {OLLAMA_MODEL}` been run?")
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: PASS (all tests in the file — the new `TestBuildPrompt` tests, `TestCallOllama`'s two updated tests, and every other existing test in the file, since nothing else in this file changed behavior).

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/llm_fallback.py ai-sandbox/academic-rag-model/tests/test_llm_fallback.py
git commit -m "feat(viz): split prompt-building into _build_prompt(), tighten base prompt"
```

---

## Task 2: `_run_generated_code()` returns `(success, error)` instead of a bare bool

**Files:**
- Modify: `ai-sandbox/academic-rag-model/viz/llm_fallback.py`
- Modify: `ai-sandbox/academic-rag-model/tests/test_llm_fallback.py`

**Interfaces:**
- Modifies: `_run_generated_code(code: str, output_path: str, timeout: int = EXECUTION_TIMEOUT_SECONDS) -> tuple[bool, str | None]` — previously returned a bare `bool`. Consumed by Task 3's retry loop, which needs the error text to feed back to the model.

This task does **not** touch `generate_via_llm()`'s call site either — same reasoning as Task 1: every test that reaches `generate_via_llm()`'s call to `_run_generated_code()` today mocks `_run_generated_code` directly (via `patch(..., side_effect=fake_run)`), so the mock's return shape — not the real function's — is what those tests actually see. The real call site's tuple-unpacking is fixed in Task 3, alongside the retry loop that needs it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_llm_fallback.py`, replace the entire `TestRunGeneratedCode` class body with:

```python
class TestRunGeneratedCode(unittest.TestCase):
    def test_successful_script_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])"
            success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            self.assertIsNone(error)
            self.assertTrue(os.path.exists(output_path))

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
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback.TestRunGeneratedCode -v`
Expected: FAIL — every test in this class fails with a `TypeError` on the `success, error = _run_generated_code(...)` unpacking line (`cannot unpack non-iterable bool object`), since `_run_generated_code` still returns a bare `bool`.

- [ ] **Step 3: Implement**

Replace `_run_generated_code()` in `viz/llm_fallback.py` with:

```python
def _run_generated_code(
    code: str, output_path: str, timeout: int = EXECUTION_TIMEOUT_SECONDS,
) -> tuple[bool, str | None]:
    """Executes `code` in a fresh subprocess that pre-imports only
    plotly/numpy, then appends a fig.write_html(output_path) call and
    enforces `timeout`. The subprocess runs with a minimal, explicit
    environment (see _minimal_subprocess_env -- no inherited secrets)
    and a scratch working directory (the temp dir holding its own
    generated script), not the caller's cwd, so a stray file write from
    generated code can't land in the project tree. Returns (True, None)
    only if the file actually got written; otherwise (False, <error
    text>) -- the error is fed back to the model on a retry (see
    generate_via_llm) in addition to being printed as a WARNING here.
    Never raises past its caller (spec §4)."""
    abs_output_path = os.path.abspath(output_path)
    script = (
        "import plotly.graph_objects as go\n"
        "import plotly.express as px\n"
        "import numpy as np\n"
        f"{code}\n"
        f"fig.write_html({abs_output_path!r}, include_plotlyjs='inline')\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        script_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True, timeout=timeout,
            env=_minimal_subprocess_env(), cwd=os.path.dirname(script_path),
        )
        if result.returncode != 0:
            error = f"the script failed:\n{result.stderr[-500:]}"
            print(f"WARNING: generated visualization script failed:\n{result.stderr[-500:]}")
            return False, error
        if not os.path.exists(abs_output_path):
            error = "the script ran without error but never produced the output file -- was `fig` assigned?"
            print(f"WARNING: {error}")
            return False, error
        return True, None
    except subprocess.TimeoutExpired:
        error = f"the script timed out after {timeout}s -- avoid expensive computation or infinite loops"
        print(f"WARNING: generated visualization script timed out after {timeout}s")
        return False, error
    except Exception as err:
        error = f"the script raised an unexpected error before it could run: {err}"
        print(f"WARNING: generated visualization script raised an unexpected error: {err}")
        return False, error
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: PASS (all tests in the file — `TestRunGeneratedCode`'s updated tests, and every other existing test, since `generate_via_llm`'s tests all mock `_run_generated_code` and are unaffected by this real-implementation change).

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/llm_fallback.py ai-sandbox/academic-rag-model/tests/test_llm_fallback.py
git commit -m "feat(viz): _run_generated_code returns its failure reason alongside success/failure"
```

---

## Task 3: Wire the `MAX_GENERATION_ATTEMPTS` retry loop into `generate_via_llm()`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/viz/llm_fallback.py`
- Modify: `ai-sandbox/academic-rag-model/tests/test_llm_fallback.py`

**Interfaces:**
- Consumes: `_build_prompt` and `_call_ollama(prompt)` (Task 1), `_run_generated_code(...) -> tuple[bool, str | None]` (Task 2).
- Produces: `MAX_GENERATION_ATTEMPTS = 3` (new module-level constant). No new public names on `generate_via_llm()` itself — its signature is unchanged, only its internal orchestration changes to a bounded retry loop.

This task rewrites `generate_via_llm()`'s **entire** body — do not attempt an incremental diff against the current (pre-Task-1/2) code. The version below is the target; replace the whole function.

- [ ] **Step 1: Write the failing tests**

In `tests/test_llm_fallback.py`, update the import line at the top (from Task 1's version) to also import `MAX_GENERATION_ATTEMPTS`:

```python
from viz.llm_fallback import (
    _cache_key, _extract_code, _build_prompt, _call_ollama, _run_generated_code,
    generate_via_llm, MAX_GENERATION_ATTEMPTS,
)
```

Replace the entire `TestGenerateViaLlm` class with:

```python
class TestGenerateViaLlm(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback._call_ollama", return_value=None) as mock_call:
                result = generate_via_llm("concept", "", os.path.join(tmp, "out.html"), os.path.join(tmp, "cache"))
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying (spec §4)

    def test_returns_none_when_no_code_block_extracted_after_exhausting_all_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.llm_fallback._call_ollama", return_value="no code here") as mock_call:
                result = generate_via_llm("concept", "", os.path.join(tmp, "out.html"), os.path.join(tmp, "cache"))
            self.assertIsNone(result)
            self.assertEqual(mock_call.call_count, MAX_GENERATION_ATTEMPTS)

    def test_success_copies_cached_file_to_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
            output_path = os.path.join(tmp, "course", "concept.html")

            def fake_run(code, path, timeout=60):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("<html>fake</html>")
                return True, None

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

    def test_recovers_after_one_failed_attempt_then_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
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

            with patch("viz.llm_fallback._call_ollama", side_effect=responses) as mock_call, \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir)

            self.assertIsNotNone(result)
            self.assertEqual(result.source, "llm_fallback")
            self.assertEqual(mock_call.call_count, 2)
            second_prompt = mock_call.call_args_list[1].args[0]
            self.assertIn("Bad property path", second_prompt)
            self.assertIn("bold=True", second_prompt)

    def test_only_the_successful_attempt_is_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = os.path.join(tmp, "cache")
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

            with patch("viz.llm_fallback._call_ollama", side_effect=responses), \
                 patch("viz.llm_fallback._run_generated_code", side_effect=fake_run):
                result = generate_via_llm("concept", "", output_path, cache_dir)

            self.assertIsNotNone(result)
            cache_key = _cache_key("concept", "")
            cached_path = os.path.join(cache_dir, f"{cache_key}.html")
            self.assertTrue(os.path.exists(cached_path))
            with open(cached_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), "<html>fake</html>")
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback.TestGenerateViaLlm -v`
Expected: FAIL — the whole module fails to import (`ImportError: cannot import name 'MAX_GENERATION_ATTEMPTS'`), since the constant doesn't exist yet. (Once that's fixed, several individual tests would also fail on their own — the call-count assertions, and `test_success_copies_cached_file_to_output_path`'s `fake_run` returning a 2-tuple that the current, pre-Task-3 `generate_via_llm` doesn't unpack — but the import error is what you'll actually see first; that's the expected RED state.)

- [ ] **Step 3: Implement**

Add the new constant near the top of `viz/llm_fallback.py`, alongside the existing `OLLAMA_URL`/`OLLAMA_MODEL`/`EXECUTION_TIMEOUT_SECONDS`:

```python
MAX_GENERATION_ATTEMPTS = 3
```

Replace `generate_via_llm()`'s entire body with:

```python
def generate_via_llm(concept: str, context: str, output_path: str, cache_dir: str) -> VizResult | None:
    """Generates a visualization via the local Ollama fallback, retrying
    up to MAX_GENERATION_ATTEMPTS times with the previous failure fed
    back to the model as a corrective prompt, or returns None on any
    failure -- never raises past its caller (spec §4, hardened per
    docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md
    §2/§4)."""
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cached_path = os.path.join(cache_dir, f"{_cache_key(concept, context)}.html")

        if not os.path.exists(cached_path):
            previous_code, previous_error = None, None
            succeeded = False
            for _ in range(MAX_GENERATION_ATTEMPTS):
                prompt = _build_prompt(concept, context, previous_code, previous_error)
                response_text = _call_ollama(prompt)
                if response_text is None:
                    return None  # Ollama unreachable -- not worth retrying (spec §4)
                code = _extract_code(response_text)
                if code is None:
                    previous_code, previous_error = None, "the response contained no ```python code block"
                    continue
                success, error = _run_generated_code(code, cached_path)
                if success:
                    succeeded = True
                    break
                previous_code, previous_error = code, error
            if not succeeded:
                return None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copyfile(cached_path, output_path)
        return VizResult(html_path=output_path, title=concept, source="llm_fallback")
    except Exception as err:
        print(f"WARNING: LLM fallback failed unexpectedly ({err})")
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: PASS (all tests in the file).

Then run the full project suite to confirm nothing elsewhere regressed:

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, full suite (this project's existing 715 tests as of the visualization-agent merge, plus this plan's new/changed tests in `test_llm_fallback.py` — `TestBuildPrompt`'s 6 tests are net-new; `TestRunGeneratedCode` and `TestGenerateViaLlm`'s test counts are roughly the same as before, since most changes are in-place updates to existing tests rather than pure additions, plus 2 new `TestGenerateViaLlm` tests for the recovery/caching behavior).

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/llm_fallback.py ai-sandbox/academic-rag-model/tests/test_llm_fallback.py
git commit -m "feat(viz): wire a bounded validate-and-retry loop into generate_via_llm()"
```

---

## Task 4: Real-corpus validation and status doc update

**Files:**
- Modify: `ai-sandbox/academic-rag-model/docs/2026-09-02-visualization-agent-status.md`

**Interfaces:** None — manual validation and documentation, closing out this plan the same way the original visualization-agent plan's Task 11 did.

- [ ] **Step 1: Run the full automated test suite one more time**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, full suite.

- [ ] **Step 2: Re-run the previously-failing "intermediate value theorem" query for real**

Run (PowerShell, from `ai-sandbox/academic-rag-model/`):
```powershell
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the intermediate value theorem" --course math-camp --visualize
```
This is the exact query that failed in the original visualization-agent plan's Task 11 real-corpus validation ("Bad property path: bold", after ~67.6s). Record: does it succeed now (and if so, on which attempt — check the console output for how many "Generating a visualization via the local Ollama model" lines print, since each retry re-triggers that message), or does it still fail after all 3 attempts? Record the exact wall-clock time and, if it still fails, the exact final `WARNING:` text.

- [ ] **Step 3: Re-run the "eigenvectors and eigenvalues" query that failed in this session**

Run:
```powershell
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "Give me a lesson summarizing eigenvectors and eigenvalues: what they are, geometric intuition, and how to compute them." --course math-camp --visualize
```
This phrasing doesn't match the `spectral_decomposition` template's keywords, so it exercises the Ollama fallback the same way it did earlier in this session (where it failed with "Bad property path: z"). Record the same details as Step 2.

- [ ] **Step 4: Append findings to the status doc**

Add a new section to the end of `docs/2026-09-02-visualization-agent-status.md`:

```markdown
## Retry-hardening validation (2026-09-XX)

Following real-usage failures on 2026-09-02/03 (two Ollama-fallback
generations both failed with invalid Plotly properties -- "Bad property
path: bold" and "Bad property path: z"), `viz/llm_fallback.py`'s
`generate_via_llm()` was hardened with a bounded validate-and-retry loop
(design: `docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`)
-- up to 3 attempts, each retry given the previous attempt's exact
failure to fix, plus a tightened base prompt steering away from the
specific class of property mistake both real failures hit.

Record here, after actually re-running both previously-failing real
queries (do not write this section until both have really been
re-run): for each of the two queries, whether it now succeeds (and on
which attempt -- 1st/2nd/3rd), the wall-clock time, and if it still
fails after all 3 attempts, the exact final WARNING text -- honestly,
whichever the real outcome turns out to be, matching this project's
established practice of recording real validation results rather than
assumed ones.
```

Fill in the `## Retry-hardening validation` section's body with what Steps 2-3 actually showed — do not leave the placeholder paragraph in place.

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/docs/2026-09-02-visualization-agent-status.md
git commit -m "docs(viz): record retry-hardening real-corpus validation results"
```
