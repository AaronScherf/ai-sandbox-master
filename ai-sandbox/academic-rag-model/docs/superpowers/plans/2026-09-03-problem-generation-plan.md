# Problem Generation Sub-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `problem_gen/`, a local-Ollama sub-agent that generates a new practice problem plus a worked solution — styled after the student's own problem sets/exams and grounded in their own textbooks — and wire it into `rag_agent.answer_question()` via automatic intent detection.

**Architecture:** Two retrieval calls into the existing source indexer (style examples from `doc_type="problem_set"`, content grounding from `doc_type="textbook"`), a two-call local-Ollama generate-then-verify loop with retry-on-failure, and a cheap regex intent check in `rag_agent.py` that routes a matching question to this subproject instead of the normal retrieval-and-answer flow, falling back to normal Q&A whenever generation is unavailable.

**Tech Stack:** Python 3, `unittest` + `unittest.mock` (this project's existing test stack, no pytest-specific features used), Ollama's local HTTP API (`urllib`, stdlib only), the existing `indexer`/`rag` packages.

**Spec:** `docs/superpowers/specs/2026-09-03-problem-generation-design.md`

## Global Constraints

- No paid API call for generation itself — local Ollama only. Default model `qwen2.5-math:7b`, overridable via `PROBLEMGEN_OLLAMA_MODEL` (spec §4).
- No on-disk caching of generated problems — every request generates fresh (spec §1, §7).
- One problem per request; no difficulty parameter — difficulty is implicit in the retrieved style examples and the student's own phrasing (spec §1).
- Generate+verify retry loop is capped at `MAX_ATTEMPTS = 3` (spec §4).
- An empty style pool (`doc_type="problem_set"`) makes `generate_problem()` return `None` immediately, without ever calling generation (spec §3).
- An empty content pool (`doc_type="textbook"`) is not a failure — generation proceeds on the style pool alone (spec §3).
- Course resolution: an explicit `course=` argument always wins; otherwise match the question text against the corpus's known course names before falling back to the existing similarity-based candidate selection (spec §3).
- `rag_agent.answer_question()` imports `problem_gen.generator` with a function-scoped import, keeping this subproject's Ollama dependency out of every plain Q&A caller's import path (spec §6).
- Intent detection (`_looks_like_problem_request`) checks the raw `question` text as typed, before follow-up reformulation (spec §5).
- Any failure anywhere in the generation path (Ollama unreachable, extraction fails, verification never passes) returns `None` and prints a `WARNING:`-prefixed message — never raises past its caller (spec §4).

---

### Task 1: Add a `doc_type` filter to `search_passages()`

**Files:**
- Modify: `indexer/index_search.py` (the `search_passages` function, currently lines 144–177)
- Test: `tests/test_index_search.py` (add to the existing `TestSearchPassages` class)

**Interfaces:**
- Consumes: nothing new — `search()` in the same file already accepts `doc_type: str | None = None` (used by `TestSearch.test_doc_type_filter_applies_before_truncation`).
- Produces: `search_passages(roots, query, client, course=None, top_k=5, file_top_k=5, doc_type=None) -> list[PassageResult]` — same `PassageResult` shape as before; the new `doc_type` kwarg is threaded straight into the internal `search()` call. Every later task in this plan calls `search_passages(..., doc_type="problem_set")` or `search_passages(..., doc_type="textbook")`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_index_search.py`, inside `class TestSearchPassages(unittest.TestCase):` (after the existing `test_multiple_roots_with_colliding_file_id_stay_separate` method):

```python
    def test_doc_type_filter_restricts_which_files_contribute_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                _card("p", [1.0, 0.0], doc_type="problem_set"),
                _card("t", [1.0, 0.0], doc_type="textbook"),
            ])
            recompute_course_entry(tmp, "math-camp")
            save_chunks(tmp, "math-camp", [
                {"chunk_id": "p-000", "file_id": "p", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "problem set chunk", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
                {"chunk_id": "t-000", "file_id": "t", "chunk_index": 0, "tier": "page",
                 "heading_path": None, "problem_label": None, "page_range": [1, 1],
                 "text": "textbook chunk", "embedding": [1.0, 0.0], "embedding_model": "m", "content_hash": "h"},
            ])
            results = search_passages([tmp], "query", client=_fake_query_client([1.0, 0.0]), doc_type="textbook")
            self.assertEqual([r.text for r in results], ["textbook chunk"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_index_search.TestSearchPassages.test_doc_type_filter_restricts_which_files_contribute_chunks -v`
Expected: FAIL with `TypeError: search_passages() got an unexpected keyword argument 'doc_type'`

- [ ] **Step 3: Implement the filter**

In `indexer/index_search.py`, change:

```python
def search_passages(
    roots: list[str], query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5,
) -> list[PassageResult]:
    """Three-stage funnel (spec §6): reuses search() for the file-level
    pass (100% of the existing course-then-file filtering, not
    duplicated), then ranks that shortlist's chunks by cosine similarity
    to the same query embedding. A file with no chunks yet (chunk
    hasn't been run against it) contributes nothing and is silently
    skipped, not an error -- degrades gracefully during the transition
    period before `chunk` has been run corpus-wide."""
    file_results = search(roots, query, client, course=course, top_k=file_top_k)
```

to:

```python
def search_passages(
    roots: list[str], query: str, client, course: str | None = None,
    top_k: int = 5, file_top_k: int = 5, doc_type: str | None = None,
) -> list[PassageResult]:
    """Three-stage funnel (spec §6): reuses search() for the file-level
    pass (100% of the existing course-then-file filtering, not
    duplicated), then ranks that shortlist's chunks by cosine similarity
    to the same query embedding. A file with no chunks yet (chunk
    hasn't been run against it) contributes nothing and is silently
    skipped, not an error -- degrades gracefully during the transition
    period before `chunk` has been run corpus-wide. doc_type filters
    which files are eligible at the file-level pass (e.g. "problem_set"
    vs "textbook" -- see problem_gen/generator.py's two-pool retrieval,
    docs/superpowers/specs/2026-09-03-problem-generation-design.md §3)."""
    file_results = search(roots, query, client, course=course, top_k=file_top_k, doc_type=doc_type)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_index_search.TestSearchPassages.test_doc_type_filter_restricts_which_files_contribute_chunks -v`
Expected: PASS

- [ ] **Step 5: Run the full file's test suite to check for regressions**

Run: `python -m unittest tests.test_index_search -v`
Expected: all PASS (existing `search_passages` callers all omit `doc_type`, which defaults to `None` — identical behavior to before)

- [ ] **Step 6: Commit**

```bash
git add indexer/index_search.py tests/test_index_search.py
git commit -m "$(cat <<'EOF'
feat(indexer): add a doc_type filter to search_passages()

Threads the existing doc_type filter (already on search()) through to
the passage-level funnel, so a caller can restrict retrieval to real
problems (doc_type="problem_set") or textbook content
(doc_type="textbook") -- needed by the upcoming problem-generation
sub-agent's two-pool retrieval.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 2: Extract a shared Ollama call helper into `common/ollama_utils.py`

**Files:**
- Create: `common/ollama_utils.py`
- Create: `tests/test_ollama_utils.py`
- Modify: `viz/llm_fallback.py`
- Modify: `tests/test_llm_fallback.py`

**Interfaces:**
- Produces: `common.ollama_utils.OllamaTimeout` (class), `common.ollama_utils.OLLAMA_TIMEOUT` (its one instance — a sentinel), `common.ollama_utils.call_ollama(prompt: str, model: str, request_timeout: int, url: str = OLLAMA_URL) -> str | None | OllamaTimeout`. Task 3's `problem_gen/llm_gen.py` imports all three of these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ollama_utils.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ollama_utils -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'common.ollama_utils'`

- [ ] **Step 3: Implement `common/ollama_utils.py`**

```python
"""
ollama_utils.py
Shared local-Ollama HTTP-call helper (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md §2).
Extracted from viz/llm_fallback.py's original _call_ollama/_OllamaTimeout
so viz/ and problem_gen/ each don't carry their own copy of the
HTTP-call/timeout-distinction logic.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"


class OllamaTimeout:
    """Sentinel returned by call_ollama when the HTTP request to Ollama
    itself times out -- distinct from None (a genuine connection
    failure/unreachable server). A live-but-slow Ollama call is
    plausibly worth a retry, unlike a server that isn't running at all;
    callers' retry loops treat the two differently."""


OLLAMA_TIMEOUT = OllamaTimeout()


def call_ollama(prompt: str, model: str, request_timeout: int, url: str = OLLAMA_URL) -> str | None | OllamaTimeout:
    """POSTs `prompt` to a local Ollama model's HTTP API (non-streaming).
    Returns the response text, None if the server is unreachable, or
    OLLAMA_TIMEOUT if the request itself timed out. Never raises."""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("response")
    except Exception as err:
        timed_out = isinstance(err, TimeoutError) or (
            isinstance(err, urllib.error.URLError) and isinstance(err.reason, TimeoutError)
        )
        if timed_out:
            print(f"WARNING: Ollama call to model '{model}' timed out after {request_timeout}s -- "
                  f"the model may just be slow on this request")
            return OLLAMA_TIMEOUT
        print(f"WARNING: Ollama call to model '{model}' failed ({err}) -- is `ollama serve` running and "
              f"has `ollama pull {model}` been run?")
        return None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_ollama_utils -v`
Expected: PASS

- [ ] **Step 5: Refactor `viz/llm_fallback.py` to use the shared helper**

In `viz/llm_fallback.py`, change the imports and constants block from:

```python
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from viz.viz_agent import VizResult

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("VIZ_OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_REQUEST_TIMEOUT_SECONDS = 180
EXECUTION_TIMEOUT_SECONDS = 60
MAX_GENERATION_ATTEMPTS = 3


class _OllamaTimeout:
    """Sentinel returned by _call_ollama when the HTTP request to Ollama
    itself times out -- distinct from None (a genuine connection
    failure/unreachable server). A live-but-slow Ollama call is
    plausibly worth a retry, unlike a server that isn't running at all;
    generate_via_llm's retry loop treats the two differently."""


_OLLAMA_TIMEOUT = _OllamaTimeout()
```

to:

```python
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

from common.ollama_utils import OLLAMA_TIMEOUT, call_ollama
from viz.viz_agent import VizResult

OLLAMA_MODEL = os.environ.get("VIZ_OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_REQUEST_TIMEOUT_SECONDS = 180
EXECUTION_TIMEOUT_SECONDS = 60
MAX_GENERATION_ATTEMPTS = 3
```

(`json`, `urllib.error`, `urllib.request` are no longer used directly in this file — only `_call_ollama`, which is being removed, used them.)

Delete the `_call_ollama` function entirely:

```python
def _call_ollama(prompt: str) -> str | None | _OllamaTimeout:
    print(f"Generating a visualization via the local Ollama model ({OLLAMA_MODEL}) -- "
          f"this can take up to a minute...")
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("response")
    except Exception as err:
        timed_out = isinstance(err, TimeoutError) or (
            isinstance(err, urllib.error.URLError) and isinstance(err.reason, TimeoutError)
        )
        if timed_out:
            print(f"WARNING: Ollama call timed out after {OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- "
                  f"the model may just be slow on this request")
            return _OLLAMA_TIMEOUT
        print(f"WARNING: Ollama call failed ({err}) -- is `ollama serve` running and "
              f"has `ollama pull {OLLAMA_MODEL}` been run?")
        return None
```

In `generate_via_llm`, change:

```python
            for _ in range(MAX_GENERATION_ATTEMPTS):
                prompt = _build_prompt(concept, context, previous_code, previous_error)
                response_text = _call_ollama(prompt)
                if response_text is None:
                    return None  # Ollama unreachable -- not worth retrying (spec §4)
                if response_text is _OLLAMA_TIMEOUT:
                    # A live-but-slow Ollama call is plausibly worth a retry, unlike a
                    # genuinely unreachable server -- see _OllamaTimeout's own docstring.
                    previous_code, previous_error = None, (
                        f"the request to Ollama itself timed out after "
                        f"{OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- the model may just be slow; "
                        f"try to respond more concisely"
                    )
                    continue
```

to:

```python
            for _ in range(MAX_GENERATION_ATTEMPTS):
                prompt = _build_prompt(concept, context, previous_code, previous_error)
                print(f"Generating a visualization via the local Ollama model ({OLLAMA_MODEL}) -- "
                      f"this can take up to a minute...")
                response_text = call_ollama(prompt, OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
                if response_text is None:
                    return None  # Ollama unreachable -- not worth retrying (spec §4)
                if response_text is OLLAMA_TIMEOUT:
                    # A live-but-slow Ollama call is plausibly worth a retry, unlike a
                    # genuinely unreachable server -- see OllamaTimeout's own docstring
                    # (common/ollama_utils.py).
                    previous_code, previous_error = None, (
                        f"the request to Ollama itself timed out after "
                        f"{OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- the model may just be slow; "
                        f"try to respond more concisely"
                    )
                    continue
```

- [ ] **Step 6: Update `tests/test_llm_fallback.py`**

Change the import block from:

```python
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.llm_fallback import (
    _cache_key, _extract_code, _build_prompt, _call_ollama, _run_generated_code,
    generate_via_llm, MAX_GENERATION_ATTEMPTS, _OLLAMA_TIMEOUT,
)
```

to:

```python
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from common.ollama_utils import OLLAMA_TIMEOUT
from viz.llm_fallback import (
    _cache_key, _extract_code, _build_prompt, _run_generated_code,
    generate_via_llm, MAX_GENERATION_ATTEMPTS,
)
```

(`json` is no longer used directly in this test file once `TestCallOllama` — which built JSON responses — moves to `test_ollama_utils.py`.)

Delete the entire `TestCallOllama` class (its three tests now live in `tests/test_ollama_utils.py`, Step 1 above):

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

    @patch("viz.llm_fallback.urllib.request.urlopen", side_effect=TimeoutError("timed out"))
    def test_returns_timeout_sentinel_on_timeout(self, mock_urlopen):
        """A live-but-slow Ollama call must be distinguishable from a
        genuinely unreachable one -- generate_via_llm's retry loop treats
        the two differently (retry vs. give up immediately)."""
        self.assertIs(_call_ollama("some composed prompt"), _OLLAMA_TIMEOUT)
```

In the remaining `TestGenerateViaLlm` class, replace every `"viz.llm_fallback._call_ollama"` patch target with `"viz.llm_fallback.call_ollama"`, and every `_OLLAMA_TIMEOUT` reference with `OLLAMA_TIMEOUT` (now imported from `common.ollama_utils`). Concretely, these seven patch/reference sites change:

| Before | After |
|---|---|
| `patch("viz.llm_fallback._call_ollama", return_value=None)` | `patch("viz.llm_fallback.call_ollama", return_value=None)` |
| `patch("viz.llm_fallback._call_ollama", return_value="no code here")` | `patch("viz.llm_fallback.call_ollama", return_value="no code here")` |
| `side_effect=[_OLLAMA_TIMEOUT, "\`\`\`python\nfig = go.Figure()\n\`\`\`"]` (with `patch("viz.llm_fallback._call_ollama", ...)`) | `side_effect=[OLLAMA_TIMEOUT, "\`\`\`python\nfig = go.Figure()\n\`\`\`"]` (with `patch("viz.llm_fallback.call_ollama", ...)`) |
| `patch("viz.llm_fallback._call_ollama", return_value=_OLLAMA_TIMEOUT)` | `patch("viz.llm_fallback.call_ollama", return_value=OLLAMA_TIMEOUT)` |
| `patch("viz.llm_fallback._call_ollama", return_value="\`\`\`python\nfig = go.Figure()\n\`\`\`")` | `patch("viz.llm_fallback.call_ollama", return_value="\`\`\`python\nfig = go.Figure()\n\`\`\`")` |
| `patch("viz.llm_fallback._call_ollama")` (in `test_cache_hit_skips_ollama_call`) | `patch("viz.llm_fallback.call_ollama")` |
| `patch("viz.llm_fallback._call_ollama", side_effect=responses)` (two occurrences, in `test_recovers_after_one_failed_attempt_then_succeeds` and `test_only_the_successful_attempt_is_cached`) | `patch("viz.llm_fallback.call_ollama", side_effect=responses)` |

No other lines in `TestGenerateViaLlm` change — the `responses` lists, `fake_run` helpers, and assertions are all unaffected by this rename.

- [ ] **Step 7: Run the full viz test suite to check for regressions**

Run: `python -m unittest tests.test_llm_fallback tests.test_viz_agent tests.test_viz_templates -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add common/ollama_utils.py tests/test_ollama_utils.py viz/llm_fallback.py tests/test_llm_fallback.py
git commit -m "$(cat <<'EOF'
refactor(viz,common): extract shared Ollama HTTP-call helper

viz/llm_fallback.py's _call_ollama/_OllamaTimeout become
common/ollama_utils.py's call_ollama/OllamaTimeout, parameterized by
model and timeout -- the upcoming problem-generation sub-agent needs
the exact same HTTP-call/timeout-distinction logic and shouldn't carry
its own copy. No behavior change to viz/.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 3: `problem_gen/llm_gen.py` — generation, extraction, verification, retry

**Files:**
- Create: `problem_gen/__init__.py` (empty — matches `viz/__init__.py`/`common/__init__.py`)
- Create: `problem_gen/llm_gen.py`
- Test: `tests/test_llm_gen.py`

**Interfaces:**
- Consumes: `common.ollama_utils.call_ollama`, `common.ollama_utils.OLLAMA_TIMEOUT` (Task 2).
- Produces: `generate_and_verify(topic: str, style_examples: list[str], content_excerpts: list[str]) -> tuple[str, str] | None` (the `(problem_text, solution_text)` pair once verified, or `None`). Task 4's `problem_gen/generator.py` calls this directly.

- [ ] **Step 1: Write the failing tests**

Create `problem_gen/__init__.py` (empty file).

Create `tests/test_llm_gen.py`:

```python
import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT
from problem_gen.llm_gen import (
    MAX_ATTEMPTS, _build_generation_prompt, _build_verification_prompt,
    _extract_problem_and_solution, _parse_verdict, generate_and_verify,
)


class TestBuildGenerationPrompt(unittest.TestCase):
    def test_first_attempt_has_no_retry_content(self):
        prompt = _build_generation_prompt("eigenvalues", [], [])
        self.assertNotIn("previous attempt", prompt)
        self.assertNotIn("That attempt failed", prompt)

    def test_includes_style_examples_with_do_not_copy_warning(self):
        prompt = _build_generation_prompt("eigenvalues", ["Find the eigenvalues of [[2,0],[0,3]]."], [])
        self.assertIn("Find the eigenvalues of [[2,0],[0,3]].", prompt)
        self.assertIn("do not copy them", prompt)

    def test_includes_content_excerpts_when_provided(self):
        prompt = _build_generation_prompt("eigenvalues", [], ["An eigenvalue satisfies Av = lv."])
        self.assertIn("An eigenvalue satisfies Av = lv.", prompt)

    def test_omits_content_block_when_empty(self):
        prompt = _build_generation_prompt("eigenvalues", ["example"], [])
        self.assertNotIn("Background from the student's own textbooks", prompt)

    def test_retry_includes_previous_problem_solution_and_error(self):
        prompt = _build_generation_prompt(
            "eigenvalues", ["example"], [],
            previous_problem="Find X.", previous_solution="X = 5.",
            previous_error="the solution never actually solves for X",
        )
        self.assertIn("Find X.", prompt)
        self.assertIn("X = 5.", prompt)
        self.assertIn("the solution never actually solves for X", prompt)

    def test_retry_without_previous_problem_still_includes_error(self):
        prompt = _build_generation_prompt(
            "eigenvalues", [], [], previous_problem=None, previous_solution=None,
            previous_error="the response did not contain both a '## Problem' and '## Solution' section",
        )
        self.assertIn("did not contain both", prompt)


class TestExtractProblemAndSolution(unittest.TestCase):
    def test_extracts_both_sections(self):
        text = "## Problem\nFind the eigenvalues.\n\n## Solution\nThey are 2 and 3."
        result = _extract_problem_and_solution(text)
        self.assertEqual(result, ("Find the eigenvalues.", "They are 2 and 3."))

    def test_case_insensitive_headings(self):
        text = "## problem\nFind X.\n\n## solution\nX = 1."
        self.assertEqual(_extract_problem_and_solution(text), ("Find X.", "X = 1."))

    def test_returns_none_when_solution_section_missing(self):
        self.assertIsNone(_extract_problem_and_solution("## Problem\nFind X."))

    def test_returns_none_when_problem_section_empty(self):
        self.assertIsNone(_extract_problem_and_solution("## Problem\n\n## Solution\nX = 1."))

    def test_returns_none_when_no_sections_at_all(self):
        self.assertIsNone(_extract_problem_and_solution("just some prose"))


class TestParseVerdict(unittest.TestCase):
    def test_valid_returns_none(self):
        self.assertIsNone(_parse_verdict("VALID"))

    def test_valid_case_insensitive(self):
        self.assertIsNone(_parse_verdict("valid"))

    def test_invalid_returns_reason(self):
        self.assertEqual(_parse_verdict("INVALID: the answer sign is wrong"), "the answer sign is wrong")

    def test_invalid_with_no_reason_gets_a_generic_one(self):
        self.assertEqual(_parse_verdict("INVALID:"), "the verification response gave no reason")

    def test_unparseable_response_treated_as_invalid(self):
        result = _parse_verdict("I think it's probably fine")
        self.assertIsNotNone(result)
        self.assertIn("not in the expected", result)


class TestGenerateAndVerify(unittest.TestCase):
    def test_returns_none_when_ollama_unreachable(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value=None) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, 1)  # unreachable Ollama isn't worth retrying

    def test_succeeds_on_first_attempt_when_verification_passes(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 2)

    def test_retries_after_extraction_failure_then_succeeds(self):
        responses = [
            "no sections here",                                    # attempt 1 generation
            "## Problem\nFind X.\n\n## Solution\nX = 1.",           # attempt 2 generation
            "VALID",                                                # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)
        second_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("did not contain both", second_prompt)

    def test_retries_after_invalid_verification_with_reason_fed_back(self):
        responses = [
            "## Problem\nFind X.\n\n## Solution\nX = 2.",           # attempt 1 generation
            "INVALID: X should equal 1, not 2",                     # attempt 1 verification
            "## Problem\nFind X.\n\n## Solution\nX = 1.",           # attempt 2 generation
            "VALID",                                                # attempt 2 verification
        ]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 4)
        third_prompt = mock_call.call_args_list[2].args[0]
        self.assertIn("X should equal 1, not 2", third_prompt)

    def test_retries_after_ollama_timeout(self):
        responses = [OLLAMA_TIMEOUT, "## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertEqual(result, ("Find X.", "X = 1."))
        self.assertEqual(mock_call.call_count, 3)

    def test_returns_none_when_max_attempts_exhausted(self):
        with patch("problem_gen.llm_gen.call_ollama", return_value="never valid sections") as mock_call:
            result = generate_and_verify("eigenvalues", ["example"], [])
        self.assertIsNone(result)
        self.assertEqual(mock_call.call_count, MAX_ATTEMPTS)

    def test_generation_and_verification_prompts_carry_the_expected_content(self):
        responses = ["## Problem\nFind X.\n\n## Solution\nX = 1.", "VALID"]
        with patch("problem_gen.llm_gen.call_ollama", side_effect=responses) as mock_call:
            generate_and_verify("eigenvalues", ["example"], [])
        first_call_prompt = mock_call.call_args_list[0].args[0]
        second_call_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("eigenvalues", first_call_prompt)
        self.assertIn("Find X.", second_call_prompt)
        self.assertIn("X = 1.", second_call_prompt)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_llm_gen -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_gen.llm_gen'`

- [ ] **Step 3: Implement `problem_gen/llm_gen.py`**

```python
"""
llm_gen.py
Local Ollama generation of a new practice problem plus a worked
solution, with self-verification and retry-with-feedback (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md §4).
Much simpler than viz/llm_fallback.py by design: the output here is
text (a problem and a solution), not executable code, so there is no
subprocess execution or sandboxing involved at all.
"""
from __future__ import annotations

import os
import re

from common.ollama_utils import OLLAMA_TIMEOUT, call_ollama

PROBLEMGEN_OLLAMA_MODEL = os.environ.get("PROBLEMGEN_OLLAMA_MODEL", "qwen2.5-math:7b")
OLLAMA_REQUEST_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 3

_GENERATION_PROMPT_TEMPLATE = """You are writing a NEW practice problem for a student studying {topic}, in \
the same style, notation, and difficulty as their own course's problem sets. Do NOT copy any of the example \
problems below verbatim -- write an original problem that tests the same kind of technique.
{style_block}{content_block}
Respond in exactly this format, with both sections present:

## Problem
<the new problem statement>

## Solution
<a full, correct, worked solution to the problem you just wrote>
"""

_VERIFICATION_PROMPT_TEMPLATE = """Check whether the solution below is actually correct and complete for the \
stated problem.

Problem:
{problem_text}

Solution:
{solution_text}

Respond with exactly "VALID" if the solution is correct and complete, or "INVALID: <short reason>" if it is \
wrong, incomplete, or the problem itself is ill-posed. Respond with nothing else."""

_SECTION_PATTERN = re.compile(r"##\s*Problem\s*\n(.*?)\n##\s*Solution\s*\n(.*)", re.IGNORECASE | re.DOTALL)
_INVALID_PATTERN = re.compile(r"INVALID:\s*(.*)", re.IGNORECASE | re.DOTALL)


def _build_generation_prompt(
    topic: str, style_examples: list[str], content_excerpts: list[str],
    previous_problem: str | None = None, previous_solution: str | None = None,
    previous_error: str | None = None,
) -> str:
    """Composes the prompt sent to Ollama to generate a new problem.
    First attempt (previous_error is None): topic + style examples +
    content excerpts only. Retry attempt (previous_error set): the same
    base prompt plus the previous attempt's problem/solution (if any --
    omitted when extraction itself failed, since there's nothing to
    show) and the exact failure reason, asking for a corrected pair."""
    style_block = ""
    if style_examples:
        examples = "\n\n".join(f"- {e}" for e in style_examples)
        style_block = (
            f"\nExample problems from the student's own course materials (for style and "
            f"difficulty only -- do not copy them):\n{examples}\n"
        )
    content_block = ""
    if content_excerpts:
        excerpts = "\n\n".join(content_excerpts)
        content_block = f"\nBackground from the student's own textbooks (for grounding correctness):\n{excerpts}\n"
    base = _GENERATION_PROMPT_TEMPLATE.format(topic=topic, style_block=style_block, content_block=content_block)
    if previous_error is None:
        return base
    previous_block = ""
    if previous_problem is not None:
        previous_block = (
            f"\nYour previous attempt produced:\n## Problem\n{previous_problem}\n\n"
            f"## Solution\n{previous_solution}\n"
        )
    return (
        f"{base}\n"
        f"{previous_block}"
        f"That attempt failed with: {previous_error}\n"
        f"Write a corrected problem and solution that fixes this specific issue. Respond in exactly the "
        f"same '## Problem' / '## Solution' format."
    )


def _build_verification_prompt(problem_text: str, solution_text: str) -> str:
    return _VERIFICATION_PROMPT_TEMPLATE.format(problem_text=problem_text, solution_text=solution_text)


def _extract_problem_and_solution(response_text: str) -> tuple[str, str] | None:
    match = _SECTION_PATTERN.search(response_text)
    if match is None:
        return None
    problem_text, solution_text = match.group(1).strip(), match.group(2).strip()
    if not problem_text or not solution_text:
        return None
    return problem_text, solution_text


def _parse_verdict(response_text: str) -> str | None:
    """Returns None when the solution is verified VALID, or a short
    reason string when INVALID -- the reason is fed back into the next
    generation attempt's prompt. An unparseable response is treated as
    invalid (fail closed) rather than silently trusted as valid."""
    stripped = response_text.strip()
    if stripped.upper().startswith("VALID"):
        return None
    match = _INVALID_PATTERN.match(stripped)
    if match:
        return match.group(1).strip() or "the verification response gave no reason"
    return "the verification response was not in the expected VALID/INVALID format"


def generate_and_verify(
    topic: str, style_examples: list[str], content_excerpts: list[str],
) -> tuple[str, str] | None:
    """Returns (problem_text, solution_text) once verification confirms
    the solution is correct, or None if Ollama is unreachable or
    verification never passes within MAX_ATTEMPTS. Never raises."""
    try:
        previous_problem, previous_solution, previous_error = None, None, None
        for _ in range(MAX_ATTEMPTS):
            prompt = _build_generation_prompt(
                topic, style_examples, content_excerpts, previous_problem, previous_solution, previous_error,
            )
            print(f"Generating a practice problem via the local Ollama model ({PROBLEMGEN_OLLAMA_MODEL}) -- "
                  f"this can take a while...")
            response = call_ollama(prompt, PROBLEMGEN_OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
            if response is None:
                return None  # Ollama unreachable -- not worth retrying
            if response is OLLAMA_TIMEOUT:
                previous_problem, previous_solution = None, None
                previous_error = (
                    f"the request to Ollama itself timed out after {OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- "
                    f"the model may just be slow; try to respond more concisely"
                )
                continue

            extracted = _extract_problem_and_solution(response)
            if extracted is None:
                previous_problem, previous_solution = None, None
                previous_error = "the response did not contain both a '## Problem' and '## Solution' section"
                continue
            problem_text, solution_text = extracted

            verify_prompt = _build_verification_prompt(problem_text, solution_text)
            verify_response = call_ollama(verify_prompt, PROBLEMGEN_OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
            if verify_response is None:
                return None
            if verify_response is OLLAMA_TIMEOUT:
                previous_problem, previous_solution = problem_text, solution_text
                previous_error = "the verification request itself timed out"
                continue

            invalid_reason = _parse_verdict(verify_response)
            if invalid_reason is None:
                return problem_text, solution_text
            previous_problem, previous_solution, previous_error = problem_text, solution_text, invalid_reason
        return None
    except Exception as err:
        print(f"WARNING: problem generation failed unexpectedly ({err})")
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_llm_gen -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add problem_gen/__init__.py problem_gen/llm_gen.py tests/test_llm_gen.py
git commit -m "$(cat <<'EOF'
feat(problem_gen): add local-Ollama generate+verify+retry loop

Generates a new problem/solution pair via a local math-tuned Ollama
model, then verifies the solution with a second call before returning
it -- retrying with the specific failure (extraction error or an
INVALID verdict) fed back, up to 3 attempts, mirroring viz's own
retry-hardening pattern.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 4: `problem_gen/generator.py` — retrieval, course scoping, assembly

**Files:**
- Create: `problem_gen/generator.py`
- Test: `tests/test_generator.py`

**Interfaces:**
- Consumes: `indexer.index_search.search_passages(roots, query, client, course=None, top_k=5, file_top_k=5, doc_type=None) -> list[PassageResult]` (Task 1) — `PassageResult` has `chunk_id, file_id, path, course, score, text, citation, root`; `indexer.index_card.load_courses(academic_hub_root: str) -> dict[str, dict]` (existing); `problem_gen.llm_gen.generate_and_verify(topic, style_examples, content_excerpts) -> tuple[str, str] | None` (Task 3).
- Produces: `ProblemSource` (dataclass: `chunk_id, file_id, path, citation, root, role`), `GeneratedProblem` (dataclass: `problem_text, solution_text, sources`), `generate_problem(query, roots, client, course=None, style_top_k=3, content_top_k=4) -> GeneratedProblem | None`. Task 5's `rag/rag_agent.py` calls `generate_problem` and reads `GeneratedProblem.problem_text`/`.solution_text`/`.sources` (each `ProblemSource`'s `chunk_id/file_id/path/citation/root` map directly onto `rag_agent.Citation`'s fields).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_generator.py`:

```python
import unittest
from unittest.mock import MagicMock, patch

from indexer.index_search import PassageResult
from problem_gen.generator import GeneratedProblem, ProblemSource, _match_known_course, generate_problem


def _passage(chunk_id, file_id, text="text", citation="Problem 1", root="/root"):
    return PassageResult(
        chunk_id=chunk_id, file_id=file_id, path=f"{file_id}.md", course="math-camp",
        score=1.0, text=text, citation=citation, root=root,
    )


class TestMatchKnownCourse(unittest.TestCase):
    def test_matches_a_plainly_named_course(self):
        with patch("problem_gen.generator.load_courses", return_value={"microeconomics": {}}):
            result = _match_known_course("generate a problem for my microeconomics course", ["/root"])
        self.assertEqual(result, "microeconomics")

    def test_matches_hyphen_space_variant(self):
        with patch("problem_gen.generator.load_courses", return_value={"math-camp": {}}):
            result = _match_known_course("give me a problem from math camp", ["/root"])
        self.assertEqual(result, "math-camp")

    def test_no_known_course_mentioned_returns_none(self):
        with patch("problem_gen.generator.load_courses", return_value={"microeconomics": {}}):
            result = _match_known_course("give me a problem on derivatives", ["/root"])
        self.assertIsNone(result)

    def test_checks_every_given_root(self):
        def fake_load_courses(root):
            return {"a-course": {}} if root == "/root-a" else {"b-course": {}}
        with patch("problem_gen.generator.load_courses", side_effect=fake_load_courses):
            result = _match_known_course("a problem for b-course", ["/root-a", "/root-b"])
        self.assertEqual(result, "b-course")


class TestGenerateProblem(unittest.TestCase):
    def test_empty_style_pool_returns_none_without_generating(self):
        client = MagicMock()
        with patch("problem_gen.generator.search_passages", return_value=[]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify") as mock_generate:
            result = generate_problem("q", ["/root"], client, course="math-camp")
        self.assertIsNone(result)
        mock_generate.assert_not_called()
        mock_search.assert_called_once_with(
            ["/root"], "q", client, course="math-camp", doc_type="problem_set", top_k=3,
        )

    def test_requests_problem_set_doc_type_for_style_pool(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertEqual(mock_search.call_args_list[0].kwargs["doc_type"], "problem_set")

    def test_requests_textbook_doc_type_for_content_pool(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]) as mock_search, \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertEqual(mock_search.call_args_list[1].kwargs["doc_type"], "textbook")

    def test_content_pool_empty_still_generates(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]), \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")) as mock_generate:
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertIsNotNone(result)
        mock_generate.assert_called_once_with("q", ["text"], [])

    def test_sources_tagged_by_role(self):
        style = [_passage("s-000", "s", text="style text")]
        content = [_passage("c-000", "c", text="content text")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, content]), \
             patch("problem_gen.generator.generate_and_verify", return_value=("P", "S")):
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        roles_by_chunk = {s.chunk_id: s.role for s in result.sources}
        self.assertEqual(roles_by_chunk, {"s-000": "style", "c-000": "content"})

    def test_generation_failure_returns_none(self):
        style = [_passage("s-000", "s")]
        with patch("problem_gen.generator.search_passages", side_effect=[style, []]), \
             patch("problem_gen.generator.generate_and_verify", return_value=None):
            result = generate_problem("q", ["/root"], MagicMock(), course="math-camp")
        self.assertIsNone(result)

    def test_explicit_course_skips_known_course_matching(self):
        with patch("problem_gen.generator._match_known_course") as mock_match, \
             patch("problem_gen.generator.search_passages", return_value=[]):
            generate_problem("q for microeconomics", ["/root"], MagicMock(), course="math-camp")
        mock_match.assert_not_called()

    def test_course_none_uses_known_course_matching(self):
        with patch("problem_gen.generator._match_known_course", return_value="microeconomics") as mock_match, \
             patch("problem_gen.generator.search_passages", return_value=[]) as mock_search:
            generate_problem("q", ["/root"], MagicMock())
        mock_match.assert_called_once()
        self.assertEqual(mock_search.call_args_list[0].kwargs["course"], "microeconomics")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_generator -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'problem_gen.generator'`

- [ ] **Step 3: Implement `problem_gen/generator.py`**

```python
"""
generator.py
Retrieves the student's own real problems (style anchor) and textbook
content (correctness anchor) for a topic, then generates a new,
self-verified practice problem via a local Ollama model (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md). One
public entry point, generate_problem().
"""
from __future__ import annotations

from dataclasses import dataclass

from indexer.index_card import load_courses
from indexer.index_search import search_passages
from problem_gen.llm_gen import generate_and_verify


@dataclass
class ProblemSource:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    root: str
    role: str  # "style" | "content"


@dataclass
class GeneratedProblem:
    problem_text: str
    solution_text: str
    sources: list[ProblemSource]


def _match_known_course(question: str, roots: list[str]) -> str | None:
    """Substring-matches the question against every known course name
    across the given roots (normalizing '-'/' ' so 'math camp' and
    'math-camp' both match) -- returns the first hit, or None if no
    known course name appears in the text, in which case
    generate_problem() falls through to search()'s own top-3
    similarity-based candidate selection unchanged."""
    known: set[str] = set()
    for root in roots:
        known.update(load_courses(root).keys())
    normalized_question = question.lower().replace("-", " ")
    for course in known:
        if course.lower().replace("-", " ") in normalized_question:
            return course
    return None


def generate_problem(
    query: str, roots: list[str], client, course: str | None = None,
    style_top_k: int = 3, content_top_k: int = 4,
) -> GeneratedProblem | None:
    """Returns None if there are no style examples to ground a new
    problem on this topic/course, or if generation+verification never
    succeeds (e.g. Ollama not running) -- callers must handle this
    being unavailable and fall back to normal Q&A, never treat problem
    generation as a hard dependency."""
    if course is None:
        course = _match_known_course(query, roots)

    style_passages = search_passages(
        roots, query, client, course=course, doc_type="problem_set", top_k=style_top_k,
    )
    if not style_passages:
        return None

    content_passages = search_passages(
        roots, query, client, course=course, doc_type="textbook", top_k=content_top_k,
    )

    generated = generate_and_verify(
        query, [p.text for p in style_passages], [p.text for p in content_passages],
    )
    if generated is None:
        return None
    problem_text, solution_text = generated

    sources = [
        ProblemSource(
            chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root, role="style",
        )
        for p in style_passages
    ] + [
        ProblemSource(
            chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root, role="content",
        )
        for p in content_passages
    ]
    return GeneratedProblem(problem_text=problem_text, solution_text=solution_text, sources=sources)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_generator -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add problem_gen/generator.py tests/test_generator.py
git commit -m "$(cat <<'EOF'
feat(problem_gen): add generate_problem() retrieval + assembly

Retrieves style examples (doc_type="problem_set") and textbook content
(doc_type="textbook") for a topic/course, resolving the course from
the question text against the corpus's known course list when not
given explicitly, then hands both pools to llm_gen.generate_and_verify().
Returns None (no hard failure) with no style examples or on generation
failure.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 5: Wire intent detection and routing into `rag/rag_agent.py`

**Files:**
- Modify: `rag/rag_agent.py`
- Test: `tests/test_rag_agent.py`

**Interfaces:**
- Consumes: `problem_gen.generator.generate_problem(query, roots, client, course=None) -> GeneratedProblem | None` (Task 4) — `GeneratedProblem.problem_text: str`, `.solution_text: str`, `.sources: list[ProblemSource]` (each with `chunk_id, file_id, path, citation, root`).
- Produces: `rag.rag_agent._looks_like_problem_request(question: str) -> bool`; `AnswerResult` gains `generated_problem: GeneratedProblem | None = None`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_rag_agent.py`, change the import block from:

```python
import unittest
from unittest.mock import MagicMock, patch

from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult
from rag.rag_agent import (
    Turn, Citation, AnswerResult, _diversify_by_file, _reformulate_query,
    TUTOR_MODEL, _generate_answer, answer_question,
)
```

to:

```python
import unittest
from unittest.mock import MagicMock, patch

from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult
from rag.rag_agent import (
    Turn, Citation, AnswerResult, _diversify_by_file, _reformulate_query,
    TUTOR_MODEL, _generate_answer, answer_question, _looks_like_problem_request,
)
```

Then add these two new test classes at the end of the file, before `if __name__ == "__main__":`:

```python
class TestLooksLikeProblemRequest(unittest.TestCase):
    def test_matches_practice_problem_phrasing(self):
        self.assertTrue(_looks_like_problem_request("Can you give me a practice problem on eigenvalues?"))

    def test_matches_give_me_a_problem(self):
        self.assertTrue(_looks_like_problem_request("give me a problem about convergence"))

    def test_matches_quiz_me(self):
        self.assertTrue(_looks_like_problem_request("quiz me on the spectral theorem"))

    def test_matches_another_exercise(self):
        self.assertTrue(_looks_like_problem_request("can I get another exercise like that"))

    def test_matches_test_my_understanding(self):
        self.assertTrue(_looks_like_problem_request("test my understanding of gradient descent"))

    def test_does_not_match_plain_question(self):
        self.assertFalse(_looks_like_problem_request("what is the spectral theorem"))

    def test_does_not_match_a_question_that_merely_contains_the_word_problem(self):
        self.assertFalse(_looks_like_problem_request("what's the problem with this proof"))


class TestAnswerQuestionProblemGeneration(unittest.TestCase):
    def test_matching_question_routes_to_generate_problem(self):
        client = _fake_generate_client("unused")
        fake_generated = MagicMock(problem_text="Find X.", sources=[])
        with patch("problem_gen.generator.generate_problem", return_value=fake_generated) as mock_generate, \
             patch("rag.rag_agent.search_passages") as mock_search:
            result = answer_question(["/root"], "give me a practice problem on eigenvalues", client)
        mock_generate.assert_called_once()
        mock_search.assert_not_called()
        self.assertEqual(result.answer, "Find X.")
        self.assertEqual(result.generated_problem, fake_generated)

    def test_non_matching_question_never_calls_generate_problem(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("problem_gen.generator.generate_problem") as mock_generate:
            result = answer_question(["/root"], "what is X", client)
        mock_generate.assert_not_called()
        self.assertIsNone(result.generated_problem)

    def test_matching_question_falls_back_to_qa_when_generation_returns_none(self):
        client = _fake_generate_client("The fallback answer.")
        with patch("problem_gen.generator.generate_problem", return_value=None) as mock_generate, \
             patch("rag.rag_agent.search_passages", return_value=[]) as mock_search:
            result = answer_question(["/root"], "give me a practice problem on eigenvalues", client)
        mock_generate.assert_called_once()
        mock_search.assert_called_once()
        self.assertEqual(result.answer, "The fallback answer.")
        self.assertIsNone(result.generated_problem)

    def test_generated_problem_citations_come_from_sources(self):
        client = _fake_generate_client("unused")
        source = MagicMock(chunk_id="s-000", file_id="s", path="s.md", citation="Problem 1", root="/root")
        fake_generated = MagicMock(problem_text="Find X.", sources=[source])
        with patch("problem_gen.generator.generate_problem", return_value=fake_generated):
            result = answer_question(["/root"], "give me a practice problem on eigenvalues", client)
        self.assertEqual(len(result.citations), 1)
        self.assertEqual(result.citations[0].chunk_id, "s-000")

    def test_history_appends_generated_problem_text(self):
        client = _fake_generate_client("unused")
        fake_generated = MagicMock(problem_text="Find X.", sources=[])
        with patch("problem_gen.generator.generate_problem", return_value=fake_generated):
            result = answer_question(["/root"], "give me a practice problem on eigenvalues", client)
        self.assertEqual(result.history[-1], Turn(role="assistant", text="Find X."))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_rag_agent -v`
Expected: `TestLooksLikeProblemRequest`/`TestAnswerQuestionProblemGeneration` FAIL with `ImportError: cannot import name '_looks_like_problem_request'`; all pre-existing tests still PASS.

- [ ] **Step 3: Implement the changes in `rag/rag_agent.py`**

Change the import block from:

```python
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from common.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult, search_passages
```

to:

```python
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass

from common.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from indexer.index_card import GENERATION_MODEL
from indexer.index_search import PassageResult, search_passages
```

Change the `AnswerResult` dataclass from:

```python
@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]
    visualization: VizResult | None = None  # viz.viz_agent.VizResult -- not imported at
    # module level (see answer_question()'s function-scoped import below); resolvable
    # here only because this file already has `from __future__ import annotations`,
    # which makes every annotation a lazily-evaluated string.
```

to:

```python
@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]
    visualization: VizResult | None = None  # viz.viz_agent.VizResult -- not imported at
    # module level (see answer_question()'s function-scoped import below); resolvable
    # here only because this file already has `from __future__ import annotations`,
    # which makes every annotation a lazily-evaluated string.
    generated_problem: GeneratedProblem | None = None  # problem_gen.generator.GeneratedProblem --
    # not imported at module level either, same reasoning as visualization above. No
    # import or alias is needed for this to resolve: `from __future__ import annotations`
    # (top of this file) makes every annotation a lazily-evaluated string, exactly like
    # `visualization: VizResult | None` above needs none either.
```

Add the intent-detection helper right after `_diversify_by_file`'s definition (i.e. immediately before `_REFORMULATE_PROMPT_TEMPLATE`):

```python
_PROBLEM_REQUEST_PATTERNS = [
    re.compile(r"\bpractice problem", re.IGNORECASE),
    re.compile(r"\bgive me a problem", re.IGNORECASE),
    re.compile(r"\bquiz me", re.IGNORECASE),
    re.compile(r"\banother (?:problem|exercise|question)\b", re.IGNORECASE),
    re.compile(r"\b(?:example|practice) (?:problem|question|exercise)", re.IGNORECASE),
    re.compile(r"\btest my (?:understanding|knowledge)", re.IGNORECASE),
]


def _looks_like_problem_request(question: str) -> bool:
    """Cheap keyword/regex intent check routing a question to
    problem_gen instead of the normal retrieval-and-answer flow (spec
    §5) -- checked against the raw question as typed, before any
    follow-up reformulation (reformulation exists to make a retrieval
    query standalone, which is orthogonal to classifying intent)."""
    return any(p.search(question) for p in _PROBLEM_REQUEST_PATTERNS)
```

Change `answer_question()` from:

```python
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
```

to:

```python
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    if _looks_like_problem_request(question):
        from problem_gen.generator import generate_problem  # function-scoped import,
        # same circular-import-avoidance / dependency-isolation pattern as viz's own
        # integration -- keeps this package's Ollama dependency out of every plain Q&A
        # caller's import path.
        generated = generate_problem(retrieval_query, roots, client, course=course)
        if generated is not None:
            problem_citations = [
                Citation(chunk_id=s.chunk_id, file_id=s.file_id, path=s.path, citation=s.citation, root=s.root)
                for s in generated.sources
            ]
            updated_history = history + [
                Turn(role="user", text=question), Turn(role="assistant", text=generated.problem_text),
            ]
            return AnswerResult(
                answer=generated.problem_text, citations=problem_citations,
                history=updated_history, generated_problem=generated,
            )
        # generated is None (no style examples on this topic/course, or Ollama
        # unavailable/never verified) -- fall through to the normal Q&A path below on
        # this same question, same graceful-degradation principle as visualize=None.

    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
```

Finally, in `main()`, change:

```python
        result = answer_question(
            roots, question, client, history=history, course=args.course, visualize=args.visualize,
        )
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        print()
        history = result.history
```

to:

```python
        result = answer_question(
            roots, question, client, history=history, course=args.course, visualize=args.visualize,
        )
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.generated_problem:
            print(f"\n--- Solution ---\n{result.generated_problem.solution_text}\n")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        print()
        history = result.history
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_rag_agent -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add rag/rag_agent.py tests/test_rag_agent.py
git commit -m "$(cat <<'EOF'
feat(rag): route problem-request questions to problem_gen

Adds a cheap regex intent check (_looks_like_problem_request) so
answer_question() automatically generates a practice problem instead
of doing normal retrieval-and-answer when the student's question reads
like a request for one. Falls back to normal Q&A whenever
generate_problem() is unavailable (no style examples, Ollama down, or
verification never passes) -- never a hard failure.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 6: Documentation — `problem_gen/README.md` and root `README.md`

**Files:**
- Create: `problem_gen/README.md`
- Modify: `README.md` (root)

**Interfaces:** none (docs only).

- [ ] **Step 1: Write `problem_gen/README.md`**

```markdown
# Problem Generation Sub-Agent

Generates a new practice problem plus a worked solution — styled after
the student's own problem sets and past exams, grounded in their own
textbooks. A local Ollama model does the generation itself; no paid
API call for that part (retrieval still uses the existing Gemini
client for embeddings, same as every other retrieval call in this
project).

Run directly:

```powershell
.\.venv\Scripts\python.exe -c "from problem_gen.generator import generate_problem; from common.gemini_utils import get_gemini_client, load_dotenv_override; load_dotenv_override(); print(generate_problem('a problem on eigenvalues', ['../academic-hub'], get_gemini_client(), course='math-camp'))"
```

Or via the tutor's own automatic intent detection — see
[`../rag/README.md`](../rag/README.md): asking the tutor something that
reads like a request for practice ("give me a practice problem on...",
"quiz me on...") routes to this sub-agent automatically, no flag
needed.

## Key files

- `generator.py` — the one public entry point, `generate_problem()`.
  Retrieves the student's own real problems on the topic
  (`doc_type="problem_set"`, the style/difficulty anchor) and, if
  available, their own textbook content on the topic
  (`doc_type="textbook"`, the correctness anchor) via the
  [Source Indexer](../indexer/)'s `search_passages()`, resolving which
  course to search by matching the question text against the corpus's
  known course names when a course isn't given explicitly. Returns
  `None` (no hard failure) when there are no style examples on this
  topic/course, or when generation never produces a verified problem.
- `llm_gen.py` — sends the topic plus both retrieved pools to a local
  Ollama model (`qwen2.5-math:7b` by default, override with
  `PROBLEMGEN_OLLAMA_MODEL`), extracts the generated problem and worked
  solution, then sends the pair back to the model a second time to
  verify the solution is actually correct — retrying with the specific
  failure fed back (an extraction failure or an `INVALID` verdict) up
  to 3 attempts before giving up. Requires Ollama running locally
  (`ollama serve`) with the model pulled
  (`ollama pull qwen2.5-math:7b`) — degrades to returning `None` with a
  printed warning if it isn't.

Nothing is written to disk — every request generates a fresh problem,
deliberately uncached (a repeated "give me another" should be a
genuinely different problem, not a cache hit).

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-03-problem-generation-design.md`.
```

- [ ] **Step 2: Update the root `README.md`**

Add a bullet to the "Repository layout" list, immediately after the `viz/` bullet:

```markdown
- [`viz/`](viz/README.md) — interactive Plotly HTML visualizations for concepts: a keyword-matched template library first, a local Ollama model (`qwen2.5-coder:7b`) as fallback for concepts with no template. No paid API calls anywhere in this package. Wired into `rag/` as an opt-in `--visualize` flag.
```

becomes:

```markdown
- [`viz/`](viz/README.md) — interactive Plotly HTML visualizations for concepts: a keyword-matched template library first, a local Ollama model (`qwen2.5-coder:7b`) as fallback for concepts with no template. No paid API calls anywhere in this package. Wired into `rag/` as an opt-in `--visualize` flag.
- [`problem_gen/`](problem_gen/README.md) — the problem-generation sub-agent: retrieves the student's own real problems and textbook content for a topic, then generates a new, self-verified practice problem via a local Ollama model (`qwen2.5-math:7b`). No paid API call for generation itself. Wired into `rag/` via automatic intent detection on the question text — no flag needed.
```

Add a bullet to the "Requirements" list, immediately after the "Visualization sub-agent only" bullet:

```markdown
- **Visualization sub-agent only** (`viz/`, reached via `rag/`'s opt-in `--visualize` flag): `plotly` installed in the venv. Its Ollama fallback tier additionally needs a local Ollama install (`ollama serve`) with `qwen2.5-coder:7b` pulled (`ollama pull qwen2.5-coder:7b`) — optional, and only reached when no template matches; degrades to returning `None` with a printed warning if unavailable, no `GEMINI_API_KEY` or other paid API involved either way.
```

becomes:

```markdown
- **Visualization sub-agent only** (`viz/`, reached via `rag/`'s opt-in `--visualize` flag): `plotly` installed in the venv. Its Ollama fallback tier additionally needs a local Ollama install (`ollama serve`) with `qwen2.5-coder:7b` pulled (`ollama pull qwen2.5-coder:7b`) — optional, and only reached when no template matches; degrades to returning `None` with a printed warning if unavailable, no `GEMINI_API_KEY` or other paid API involved either way.
- **Problem generation sub-agent only** (`problem_gen/`, reached via `rag/`'s automatic intent detection on the question text): a local Ollama install (`ollama serve`) with `qwen2.5-math:7b` pulled (`ollama pull qwen2.5-math:7b`) — optional, degrades to falling back to normal Q&A if unavailable, no `GEMINI_API_KEY` or other paid API involved for generation itself (retrieval still uses the existing Gemini client for embeddings, same as every other retrieval call in this project).
```

- [ ] **Step 3: Commit**

```bash
git add problem_gen/README.md README.md
git commit -m "$(cat <<'EOF'
docs(problem_gen): add subproject README and root README entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```

---

### Task 7: Real end-to-end validation with `qwen2.5-math:7b`

**Files:**
- Create: `docs/<YYYY-MM-DD>-problem-generation-status.md` (use the actual date this task is run)

**Interfaces:** none — this is a manual validation task, not code.

This project's established convention (see `viz/`'s own testing section, spec §8) is that a model-dependent capability's real quality gets a one-off manual check recorded in a narrative status doc, not a CI-run test that would need network access and real model inference. This task is that check for `problem_gen`.

- [ ] **Step 1: Pull the model**

Run: `ollama pull qwen2.5-math:7b`
Expected: completes without error. If Ollama itself isn't installed, install it first (same prerequisite `viz/`'s own Ollama fallback already documents).

- [ ] **Step 2: Confirm the math-camp corpus is indexed with `doc_type` populated**

Run (from `academic-rag-model/`):
```powershell
python -m indexer.index_search --root ../academic-hub query "eigenvalues" --doc-type problem_set --course math-camp
```
Expected: returns real problem-set files (e.g. `Linear Algebra Problem Set.md`, past exams). If this returns nothing, run `python -m indexer.index_search --root ../academic-hub rebuild --course math-camp` (and `chunk` if chunks aren't built yet) before proceeding — `generate_problem()` cannot do anything useful against an unindexed or unchunked corpus.

- [ ] **Step 3: Generate real problems for 2-3 real math-camp topics**

Run, once per topic (e.g. "eigenvalues and diagonalization", "epsilon-delta continuity", "Lagrangian optimization with equality constraints"):

```powershell
.\.venv\Scripts\python.exe -c "from problem_gen.generator import generate_problem; from common.gemini_utils import get_gemini_client, load_dotenv_override; load_dotenv_override(); r = generate_problem('a problem on <TOPIC>', ['../academic-hub'], get_gemini_client(), course='math-camp'); print(r.problem_text if r else 'GENERATION FAILED'); print('---'); print(r.solution_text if r else '')"
```

For each topic, record in your notes: how long generation took, whether it succeeded on the first attempt or needed a retry (watch the console — `llm_gen.py` prints a message each attempt), whether the problem is genuinely new (not a copy of a real problem-set entry you can find in `academic-hub/academic_notes/math-camp/problem_sets/`), and whether the worked solution is actually mathematically correct (check it by hand).

- [ ] **Step 4: Deliberately test the empty-style-pool path**

Run the same one-liner with a topic that has no real problem-set coverage in the corpus (e.g. a topic from a different subject entirely, like "supply and demand curves"). Expected: `generate_problem()` returns `None` immediately (near-instant — no Ollama call made at all), confirming the empty-style-pool short-circuit works against the real indexed corpus, not just the mocked test in Task 4.

- [ ] **Step 5: Write the status doc**

Create `docs/<YYYY-MM-DD>-problem-generation-status.md` (matching the narrative style of the existing dated status docs in `docs/`, e.g. `2026-09-02-visualization-agent-status.md`): what was validated, the real topics tried, whether the generated problems and solutions held up to a by-hand check, any retry behavior actually observed, and any follow-up work this surfaces (e.g. a prompt-wording tweak, a topic where the style pool was too thin to produce a good problem). If something is actually broken, fix it and note the fix in the same doc before moving on — don't file the finding away for later.

- [ ] **Step 6: Commit**

```bash
git add docs/<YYYY-MM-DD>-problem-generation-status.md
git commit -m "$(cat <<'EOF'
docs(problem_gen): record real end-to-end validation results

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014e9EKiax53st5ixeMK2576
EOF
)"
```
