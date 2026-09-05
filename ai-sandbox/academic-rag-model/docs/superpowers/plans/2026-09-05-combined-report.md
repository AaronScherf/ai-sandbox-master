# Combined Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `answer_question()` an opt-in way to combine the answer text, citations, and (if present) the interactive Plotly visualization into one self-contained HTML report file.

**Architecture:** Both viz tiers switch from rendering a full standalone Plotly document to rendering an embeddable fragment (`full_html=False`) as their canonical output, with a small `_wrap_fragment()` helper recreating today's standalone-file behavior for direct-open use. A new `rag/report_builder.py` module stitches question + answer + citations + the fragment (when present) into one document. `answer_question()` gains an independent `report: bool = False` parameter; both existing CLI consumers get a matching `--report` flag.

**Tech Stack:** Python 3, stdlib only (`html.escape`, `os`, `re`) for the new module; Plotly's existing `to_html()`/`write_html()` `full_html` parameter for the fragment switch. No new pip dependency.

**Spec:** `docs/superpowers/specs/2026-09-05-combined-report-design.md`

## Global Constraints

- Both viz tiers render an embeddable **fragment** as their canonical output (`include_plotlyjs="inline", full_html=False`) -- the on-disk standalone `.html` file at `html_path` is always `_wrap_fragment(fragment)`, never the fragment itself written raw.
- `VizResult` gains a **required** `fragment_html: str` field (no default) -- every construction site must supply it; the one direct `VizResult(...)` construction in `tests/test_viz_agent.py` must be updated too.
- A cache hit in `viz/llm_fallback.py`'s `generate_via_llm()` must populate `fragment_html` from the cached file's own content, not leave it empty -- the cache now stores fragments, and `fragment_html` must be correct on every success path, cache hit or fresh generation alike.
- `rag/report_builder.py` never imports `viz/` or `rag/rag_agent.py` at module level -- `citations`/`visualization` are typed only as lazily-evaluated string annotations (the module has `from __future__ import annotations`), duck-typed at runtime, matching `AnswerResult.visualization`'s own existing precedent in `rag_agent.py`. This keeps a `report=True, visualize=False` caller from pulling in either module's heavier dependencies just for a type hint.
- `build_report()` never raises past its caller -- any failure is caught, logged as `WARNING: report generation failed (...)`, and it returns `None`.
- `report: bool = False` on `answer_question()` is independent of `visualize` -- a report can be text+citations-only when no visualization exists (not requested, or the fallback degraded to `None`). Every existing caller defaults to `report=False` with zero behavior change.
- Report files live at `<roots[0]>/.reports/<course or "uncategorized">/<slug>.html` -- a new sibling tree to the existing `.viz/` tree, filename slug reusing the same slugification rules as `viz_agent.py`'s `_slugify` (duplicated as a private helper in `report_builder.py`, not imported, per the module-boundary constraint above).
- No external CDN, template engine, or new pip dependency in `report_builder.py` -- plain f-string interpolation, matching the existing style in `viz/`.
- Test runner: `./.venv/Scripts/python.exe -m unittest discover -s tests`, run from `ai-sandbox/academic-rag-model/`.

---

### Task 1: Fragment rendering in `viz_agent.py` (`_wrap_fragment`, `VizResult.fragment_html`)

**Files:**
- Modify: `viz/viz_agent.py`
- Modify: `tests/test_viz_agent.py`

**Interfaces:**
- Produces: `VizResult` gains `fragment_html: str` (required, no default). New `_wrap_fragment(fragment: str) -> str`. Task 2 imports `_wrap_fragment` from this module.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_viz_agent.py`, replacing the two existing tests named in the diff below and adding one new test and one new test class. First, update `test_template_match_writes_html_and_returns_result` and `test_write_html_called_with_inline_plotlyjs`:

```python
    def test_template_match_writes_html_and_returns_result(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course="math-camp")
        fake_fig.to_html.assert_called_once()
        self.assertEqual(result.source, "template")
        self.assertEqual(result.title, "Fake")
        self.assertEqual(result.fragment_html, "<div>fake plot</div>")
        self.assertTrue(result.html_path.startswith(os.path.join(tmp, ".viz", "math-camp")))
        self.assertTrue(result.html_path.endswith(".html"))

    def test_to_html_called_with_inline_plotlyjs_and_fragment_mode(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                generate_visualization("fake concept", academic_hub_root=tmp)
        _, kwargs = fake_fig.to_html.call_args
        self.assertEqual(kwargs["include_plotlyjs"], "inline")
        self.assertFalse(kwargs["full_html"])

    def test_output_file_is_wrapped_but_fragment_html_is_not(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp)
            with open(result.html_path, "r", encoding="utf-8") as f:
                written = f.read()
        self.assertIn("<html>", written)
        self.assertIn("<div>fake plot</div>", written)
        self.assertNotIn("<html>", result.fragment_html)
```

Then update the one direct `VizResult(...)` construction in `TestGenerateVisualizationFallbackPath.test_no_template_match_falls_back_to_llm`:

```python
    def test_no_template_match_falls_back_to_llm(self):
        fake_result = VizResult(
            html_path="/x/y.html", title="unknown concept", source="llm_fallback",
            fragment_html="<div>x</div>",
        )
```

Then add a new, standalone test class at the end of the file (before `if __name__ == "__main__":`):

```python
class TestWrapFragment(unittest.TestCase):
    def test_wraps_fragment_in_minimal_html_shell(self):
        from viz.viz_agent import _wrap_fragment
        wrapped = _wrap_fragment("<div>plot</div>")
        self.assertIn("<html>", wrapped)
        self.assertIn("<div>plot</div>", wrapped)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_viz_agent -v` (from `ai-sandbox/academic-rag-model/`)
Expected: `TypeError: VizResult.__init__() got an unexpected keyword argument 'fragment_html'`, plus an `AttributeError`/`ImportError` for `_wrap_fragment` not existing yet.

- [ ] **Step 3: Write the minimal implementation**

In `viz/viz_agent.py`, update the `VizResult` dataclass:

```python
@dataclass
class VizResult:
    html_path: str
    title: str
    source: str  # "template" | "llm_fallback"
    fragment_html: str  # the raw embeddable <div>/<script> fragment (plotly.js inlined,
    # no surrounding document tags) -- html_path's file is this fragment wrapped via
    # _wrap_fragment(); report_builder.py embeds this field directly, never html_path's file
```

Add `_wrap_fragment` (right after `_slugify`):

```python
def _wrap_fragment(fragment: str) -> str:
    """Wraps an embeddable Plotly fragment (a <div>/<script> pair, no
    surrounding document tags) in a minimal standalone document, for the
    direct-open .html files this module and llm_fallback.py both write
    to their `output_path` -- the fragment itself (not this wrapped
    form) is what report_builder.py embeds into a combined report
    (spec: docs/superpowers/specs/2026-09-05-combined-report-design.md
    §3)."""
    return f"<html><body>{fragment}</body></html>"
```

Replace the template-match branch inside `generate_visualization`:

```python
    template = match_template(concept)
    if template is not None:
        try:
            os.makedirs(output_dir, exist_ok=True)
            fig = template.render()
            fragment = fig.to_html(include_plotlyjs="inline", full_html=False)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(_wrap_fragment(fragment))
            return VizResult(html_path=output_path, title=template.name, source="template", fragment_html=fragment)
        except Exception as err:
            print(f"WARNING: template visualization failed unexpectedly ({err})")
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_viz_agent -v`
Expected: all tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add viz/viz_agent.py tests/test_viz_agent.py
git commit -m "feat(viz): render template visualizations as embeddable fragments"
```

---

### Task 2: Fragment caching and `fragment_html` in `llm_fallback.py`

**Files:**
- Modify: `viz/llm_fallback.py`
- Modify: `tests/test_llm_fallback.py`

**Interfaces:**
- Consumes: `_wrap_fragment` from `viz.viz_agent` (Task 1).
- Produces: `generate_via_llm()`'s success path (both cache-hit and fresh-generation) returns a `VizResult` with `fragment_html` populated from the cached file's own content.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_llm_fallback.py`'s `TestRunGeneratedCode` class:

```python
    def test_successful_script_writes_fragment_not_full_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.html")
            code = "import plotly.graph_objects as go\nfig = go.Figure(data=[go.Scatter(x=[1, 2], y=[1, 2])])"
            success, error = _run_generated_code(code, output_path)
            self.assertTrue(success)
            with open(output_path, "r", encoding="utf-8") as f:
                written = f.read()
            self.assertNotIn("<html", written.lower())
```

Add to `tests/test_llm_fallback.py`'s `TestGenerateViaLlm` class:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_llm_fallback -v`
Expected: `TypeError: VizResult.__init__() missing 1 required positional argument: 'fragment_html'` on the two new `TestGenerateViaLlm` tests (and every other existing success-path test in this file, until Step 3 is done); `test_successful_script_writes_fragment_not_full_document` FAILs because the file still contains `<html`.

- [ ] **Step 3: Write the minimal implementation**

In `viz/llm_fallback.py`, update the import line and remove the now-unused `shutil` import:

```python
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from viz import example_store
from viz.example_store import ExampleRecord
from viz.viz_agent import VizResult, _wrap_fragment
```

In `_run_generated_code`, change the postamble line:

```python
    script = (
        "import plotly.graph_objects as go\n"
        "import plotly.express as px\n"
        "import numpy as np\n"
        f"{code}\n"
        f"fig.write_html({abs_output_path!r}, include_plotlyjs='inline', full_html=False)\n"
    )
```

In `generate_via_llm`, replace the tail (everything after the `if not succeeded: return None` / `example_store.save(...)` block):

```python
        with open(cached_path, "r", encoding="utf-8") as f:
            fragment = f.read()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(_wrap_fragment(fragment))
        return VizResult(html_path=output_path, title=concept, source="llm_fallback", fragment_html=fragment)
    except Exception as err:
        print(f"WARNING: LLM fallback failed unexpectedly ({err})")
        return None
```

(This replaces the previous `os.makedirs(os.path.dirname(output_path), exist_ok=True)` / `shutil.copyfile(cached_path, output_path)` / `return VizResult(html_path=output_path, title=concept, source="llm_fallback")` lines -- the read-fragment-and-wrap logic now runs unconditionally after the cache-fill block, covering both a cache hit and a fresh generation with the same code path.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_llm_fallback -v`
Expected: all tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add viz/llm_fallback.py tests/test_llm_fallback.py
git commit -m "feat(viz): cache and return fragments instead of full documents"
```

---

### Task 3: `rag/report_builder.py`

**Files:**
- Create: `rag/report_builder.py`
- Test: `tests/test_report_builder.py`

**Interfaces:**
- Produces: `build_report(question: str, answer: str, citations: list, visualization, output_path: str) -> str | None`, `report_path(question: str, reports_root: str, course: str | None) -> str`. Task 4 imports both by these exact names and signatures.

- [ ] **Step 1: Write the failing test**

Create `tests/test_report_builder.py`:

```python
import html
import os
import tempfile
import unittest
from dataclasses import dataclass

from rag.report_builder import build_report, report_path, _slugify


@dataclass
class _FakeCitation:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    root: str


@dataclass
class _FakeViz:
    html_path: str
    title: str
    source: str
    fragment_html: str


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_replaces_punctuation(self):
        self.assertEqual(_slugify("What is the Spectral Theorem?"), "what-is-the-spectral-theorem")

    def test_empty_text_returns_fallback(self):
        self.assertEqual(_slugify(""), "report")


class TestReportPath(unittest.TestCase):
    def test_joins_reports_root_course_and_slug(self):
        path = report_path("What is X?", "/root/.reports", "math-camp")
        self.assertEqual(path, os.path.join("/root/.reports", "math-camp", "what-is-x.html"))

    def test_course_none_uses_uncategorized(self):
        path = report_path("What is X?", "/root/.reports", None)
        self.assertIn("uncategorized", path)


class TestBuildReport(unittest.TestCase):
    def test_all_three_pieces_present(self):
        citations = [_FakeCitation(chunk_id="a-0", file_id="a", path="a.md", citation="p. 1", root="/root")]
        viz = _FakeViz(html_path="/x/y.html", title="t", source="template", fragment_html="<div>PLOT-MARKER</div>")
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            result = build_report("What is X?", "X is Y.", citations, viz, output_path)
            self.assertEqual(result, output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertIn("What is X?", content)
        self.assertIn("X is Y.", content)
        self.assertIn("a.md", content)
        self.assertIn("p. 1", content)
        self.assertIn("PLOT-MARKER", content)

    def test_visualization_none_omits_visualization_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            build_report("What is X?", "X is Y.", [], None, output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertNotIn("Visualization", content)

    def test_html_special_characters_are_escaped(self):
        citations = [_FakeCitation(
            chunk_id="a-0", file_id="a", path="a.md", citation="<script>bad</script>", root="/root",
        )]
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            build_report(
                "A <b>question</b>?", "An answer with <em>markup</em> & an ampersand.",
                citations, None, output_path,
            )
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertNotIn("<b>question</b>", content)
        self.assertNotIn("<em>markup</em>", content)
        self.assertNotIn("<script>bad</script>", content)
        self.assertIn(html.escape("A <b>question</b>?"), content)

    def test_write_failure_returns_none_without_raising(self):
        # A path containing a null byte is invalid on every platform and
        # always fails inside open() -- a reliable, portable way to force
        # a write failure without depending on filesystem permissions.
        bad_path = "\0invalid.html"
        result = build_report("q", "a", [], None, bad_path)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_report_builder -v`
Expected: `ModuleNotFoundError: No module named 'rag.report_builder'`

- [ ] **Step 3: Write the minimal implementation**

Create `rag/report_builder.py`:

```python
"""
rag/report_builder.py
Combines one answer_question() call's question, answer text, citations,
and (optional) visualization into a single self-contained HTML document
(spec: docs/superpowers/specs/2026-09-05-combined-report-design.md). No
external dependencies (no CDN, no template engine) -- plain string
interpolation, matching the style already used throughout viz/.

`citations` and `visualization` below are typed only as lazily-evaluated
string annotations (this module has `from __future__ import
annotations`) -- deliberately not imported at module level from
rag_agent.py/viz_agent.py, matching AnswerResult.visualization's own
existing precedent in rag_agent.py, so a report=True, visualize=False
caller never pulls in either module's heavier dependencies just for a
type hint.
"""
from __future__ import annotations

import html
import os
import re

_SLUG_MAX_LENGTH = 80


def _slugify(text: str) -> str:
    """Duplicated from viz.viz_agent._slugify rather than imported, per
    this module's own module-level-import ban above."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LENGTH].strip("-")
    return slug or "report"


def report_path(question: str, reports_root: str, course: str | None) -> str:
    return os.path.join(reports_root, course or "uncategorized", f"{_slugify(question)}.html")


def build_report(
    question: str, answer: str, citations: list[Citation], visualization: VizResult | None,
    output_path: str,
) -> str | None:
    """Writes one self-contained HTML file combining question, answer,
    citations, and (if given) the visualization's embedded fragment.
    Never raises past its caller -- any failure is logged as a WARNING
    and this returns None, leaving the rest of the answer untouched
    (spec §6)."""
    try:
        citations_html = "\n".join(
            f"  <li>[{html.escape(c.root)}] {html.escape(c.path)} ({html.escape(c.citation)})</li>"
            for c in citations
        )
        visualization_block = ""
        if visualization is not None:
            visualization_block = f"<h2>Visualization</h2>\n{visualization.fragment_html}\n"
        document = (
            f"<h1>{html.escape(question)}</h1>\n"
            f"<p>{html.escape(answer)}</p>\n"
            f"<h2>Citations</h2>\n"
            f"<ul>\n{citations_html}\n</ul>\n"
            f"{visualization_block}"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(document)
        return output_path
    except Exception as err:
        print(f"WARNING: report generation failed ({err})")
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_report_builder -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rag/report_builder.py tests/test_report_builder.py
git commit -m "feat(rag): add report_builder to combine answer, citations, and viz into one document"
```

---

### Task 4: Wire `report` into `answer_question()` and `AnswerResult`

**Files:**
- Modify: `rag/rag_agent.py`
- Modify: `tests/test_rag_agent.py`
- Modify: `.gitignore` (repo root, `C:\Users\theaa\ai-sandbox-master\.gitignore`)

**Interfaces:**
- Consumes: `rag.report_builder.build_report`, `rag.report_builder.report_path` (Task 3).
- Produces: `AnswerResult.report_path: str | None`, `answer_question(..., report: bool = False)`. Task 5 (CLI) uses this new parameter and field.

- [ ] **Step 1: Write the failing tests**

Add `import os` to the top of `tests/test_rag_agent.py` (it isn't imported there today). Then add a new test class after `TestAnswerQuestionVisualize`:

```python
class TestAnswerQuestionReport(unittest.TestCase):
    def test_report_false_never_calls_build_report(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("rag.report_builder.build_report") as mock_build:
            result = answer_question(["/root"], "q", client)
        mock_build.assert_not_called()
        self.assertIsNone(result.report_path)

    def test_report_true_without_visualize_still_builds_report(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("rag.report_builder.build_report", return_value="/x/report.html") as mock_build:
            result = answer_question(["/root"], "q", client, report=True)
        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        self.assertEqual(args[0], "q")
        self.assertIsNone(args[3])  # visualization
        self.assertEqual(result.report_path, "/x/report.html")

    def test_report_true_with_visualize_passes_visualization_through(self):
        client = _fake_generate_client("answer")
        fake_viz = MagicMock()
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization", return_value=fake_viz), \
             patch("rag.report_builder.build_report", return_value="/x/report.html") as mock_build:
            answer_question(["/root"], "q", client, visualize=True, report=True)
        args, kwargs = mock_build.call_args
        self.assertEqual(args[3], fake_viz)

    def test_report_path_uses_reports_root_under_first_given_root(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("rag.report_builder.build_report", return_value=None), \
             patch("rag.report_builder.report_path") as mock_path:
            mock_path.return_value = "/root-a/.reports/math-camp/q.html"
            answer_question(["/root-a", "/root-b"], "q", client, course="math-camp", report=True)
        mock_path.assert_called_once_with("q", os.path.join("/root-a", ".reports"), "math-camp")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_rag_agent -v`
Expected: `TypeError: answer_question() got an unexpected keyword argument 'report'`

- [ ] **Step 3: Write the minimal implementation**

In `rag/rag_agent.py`, update `AnswerResult`:

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
    report_path: str | None = None  # rag.report_builder.build_report()'s return value --
    # None whenever report=False (default) or report generation itself failed
```

Update `answer_question()`'s signature and docstring:

```python
def answer_question(
    roots: list[str], question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3, visualize: bool = False, report: bool = False,
) -> AnswerResult:
    """The core function serving both usage modes (spec §3/§6): a
    callable utility (call once, use the AnswerResult, done) and the
    interactive chat below (thread .history back in on the next call).
    Stateless per call -- history is an explicit input/output, not
    owned internally, which is what lets both modes share this one
    function without a database or session files. roots is a list so a
    tutoring question can be grounded in passages from more than one
    corpus at once (e.g. academic-hub and research/ together).
    visualize=True additionally generates an interactive visualization
    for the question's concept (viz/, spec:
    docs/superpowers/specs/2026-09-02-visualization-agent-design.md) --
    grounded in the first root in `roots`, since a single concept's
    illustrative example doesn't need multi-root grounding the way
    citation retrieval does. report=True additionally combines the
    answer, citations, and (if present) the visualization into one
    self-contained HTML document (rag/report_builder.py, spec:
    docs/superpowers/specs/2026-09-05-combined-report-design.md) --
    independent of visualize: a report can be text+citations-only if no
    visualization exists, whether that's because it wasn't requested or
    the fallback degraded to None."""
```

Replace the function's tail (from `visualization = None` through the `return`):

```python
    visualization = None
    if visualize:
        from viz.viz_agent import generate_visualization  # function-scoped: keeps viz/'s
        # plotly (and, transitively on the fallback path, subprocess/network) dependency
        # out of every plain-Q&A caller's import path, matching index_search.py's own
        # function-scoped import of answer_question() for the same reason.
        viz_context = "\n\n".join(p.text for p in passages)
        visualization = generate_visualization(
            question, context=viz_context, academic_hub_root=roots[0], course=course,
        )

    report_path_value = None
    if report:
        from rag.report_builder import build_report, report_path  # function-scoped: keeps
        # report_builder.py's (and, when a visualization exists, transitively viz/'s) import
        # surface out of every caller that never sets report=True, matching this file's own
        # existing function-scoped import of generate_visualization above for the same reason.
        reports_root = os.path.join(roots[0], ".reports")
        output_path = report_path(question, reports_root, course)
        report_path_value = build_report(question, answer, citations, visualization, output_path)

    return AnswerResult(
        answer=answer, citations=citations, history=updated_history,
        visualization=visualization, report_path=report_path_value,
    )
```

In `C:\Users\theaa\ai-sandbox-master\.gitignore`, add a new pattern right after the existing `**/.viz/` line (line 87):

```
**/.viz/
# Combined-report output (.reports/) is the same kind of derivative,
# corpus-grounded generated content as .viz/ -- same IP posture, same
# any-root coverage rationale.
**/.reports/
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_rag_agent -v`
Expected: all tests PASS.

Then run the full suite to confirm no regressions:

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rag/rag_agent.py tests/test_rag_agent.py ../../.gitignore
git commit -m "feat(rag): wire report generation into answer_question()"
```

(Run this `git add`/`git commit` from `ai-sandbox/academic-rag-model/` -- the relative `../../.gitignore` path reaches the repo root's `.gitignore` from there.)

---

### Task 5: `--report` CLI flag on both consumers, and real-corpus validation

**Files:**
- Modify: `rag/rag_agent.py` (`main()`)
- Modify: `indexer/index_search.py` (`ask` subcommand)

**Interfaces:**
- Consumes: `answer_question(..., report: bool)`, `AnswerResult.report_path` (Task 4).
- Produces: nothing new for later tasks -- this is the last task. Verified by the full suite plus a manual real-environment run (Step 4).

- [ ] **Step 1: Add the flag and print line to `rag/rag_agent.py`'s `main()`**

Replace the `--visualize` argument block and the call/print block:

```python
    parser.add_argument("--visualize", action="store_true",
                         help="Also generate an interactive visualization for each question's concept.")
    parser.add_argument("--report", action="store_true",
                         help="Also combine the answer, citations, and visualization (if any) into one "
                              "self-contained HTML report.")
    args = parser.parse_args()
```

```python
        result = answer_question(
            roots, question, client, history=history, course=args.course,
            visualize=args.visualize, report=args.report,
        )
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        if result.report_path:
            print(f"  report: {result.report_path}")
        print()
```

- [ ] **Step 2: Add the flag and print line to `indexer/index_search.py`'s `ask` subcommand**

Replace the `ask_p` argument block and the `ask` command handler:

```python
    ask_p = subparsers.add_parser("ask", help="Ask a single grounded question (no conversation memory).")
    ask_p.add_argument("question")
    ask_p.add_argument("--course", default=None)
    ask_p.add_argument("--visualize", action="store_true",
                        help="Also generate an interactive visualization for the question's concept.")
    ask_p.add_argument("--report", action="store_true",
                        help="Also combine the answer, citations, and visualization (if any) into one "
                             "self-contained HTML report.")
```

```python
    elif args.command == "ask":
        from rag.rag_agent import answer_question
        result = answer_question(
            roots, args.question, client, course=args.course,
            visualize=args.visualize, report=args.report,
        )
        print(result.answer)
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        if result.report_path:
            print(f"  report: {result.report_path}")
```

No new automated test is needed for this argparse wiring -- consistent with the existing `--visualize` flag, which is likewise untested at the CLI-argument layer (only `answer_question()`'s own behavior is unit-tested; Task 4 already covers that fully).

- [ ] **Step 3: Run the full suite**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests` (from `ai-sandbox/academic-rag-model/`)
Expected: all tests PASS.

- [ ] **Step 4: Manual real-corpus validation**

Requires `ollama serve` running with `qwen2.5-coder:7b` and `nomic-embed-text` both pulled (confirm with `GET http://localhost:11434/api/tags` first).

```powershell
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the mean value theorem" --course math-camp --visualize --report
```

Expected: a `report: ...` line is printed alongside the existing `visualization: ...` line (or, if the Ollama fallback fails on this particular run -- a known, pre-existing, unrelated reliability issue documented in `docs/2026-09-02-visualization-agent-status.md` -- the report should still be produced with just the answer and citations, no visualization section, and no crash). Open the resulting `.reports/<course>/<slug>.html` file directly in a browser and confirm: the question and answer text render, the citation list appears, and -- if a visualization was generated -- the embedded plot is present and interactive (zoom/pan/hover all work). Record the actual outcome honestly in a status-doc update afterward (this is a manual check, not asserted in CI, per this project's established convention).

- [ ] **Step 5: Commit**

```bash
git add rag/rag_agent.py indexer/index_search.py
git commit -m "feat(rag): add --report flag to both CLI consumers"
```
