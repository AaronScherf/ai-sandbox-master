# Visualization Sub-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `viz/` package that generates interactive Plotly HTML visualizations for academic-hub concepts — a keyword-matched template library first, a local Ollama model as fallback — wired into `rag_agent.answer_question()` as an opt-in step.

**Architecture:** New package `viz/`, peer to `rag/`/`indexer/`/`postprocessing/`. One public entry point, `viz.viz_agent.generate_visualization(concept, context, academic_hub_root, course)`, which tries `viz.templates.match_template()` (pure keyword lookup against a registry of hand-written Plotly-rendering functions) and only falls back to `viz.llm_fallback.generate_via_llm()` (a local Ollama HTTP call → extracted code → subprocess execution → disk cache) when no template matches. `rag_agent.answer_question()` gains one new `visualize: bool = False` parameter that calls this and attaches the result to `AnswerResult`.

**Tech Stack:** Python 3, `plotly` (new dependency), `numpy` (already in use), Ollama (local, external process — no new Python dependency, called over its local HTTP API), `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-02-visualization-agent-design.md`

## Global Constraints

- **No new paid API calls anywhere in this subproject.** Template matching is pure keyword/substring lookup (no embedding call); the fallback code-gen path uses a local Ollama model, never Gemini. This is the one constraint every other decision in the spec traces back to.
- Output is a standalone, fully offline interactive HTML file per visualization (`Figure.write_html(..., include_plotlyjs="inline")`) — never a Jupyter notebook.
- Generated output lives under `<root>/.viz/` and is gitignored by default, matching this project's existing IP posture for corpus-derived artifacts (`.index/chunks/` is the precedent).
- `viz/` follows this project's existing per-subproject package convention: own `__init__.py`, own `README.md`, run via `python -m viz.<module>`, package-qualified absolute imports (`from viz.templates import ...`), never relative imports.
- The Ollama fallback never raises past its own caller — a missing/unreachable Ollama, bad generated code, or a timeout all degrade to returning `None` with a printed warning, matching `index_card.py`'s existing failure-isolation convention for optional capabilities.
- `answer_question(visualize=False)` by default — existing callers (the REPL, `index_search.py ask`, any other code already calling `answer_question()`) are unaffected unless they opt in.
- Test runner: `./.venv/Scripts/python.exe -m unittest discover -s tests` (run from `ai-sandbox/academic-rag-model/`). Every task's failing-test step must actually be run and confirmed failing before implementing (TDD, per this repo's established practice).
- `main()` (the interactive REPL) and CLI subcommand wiring are not unit-tested, matching this project's existing convention — thin glue over fully-tested functions, verified by a real manual run instead (Task 11).

---

## File Structure

```
ai-sandbox/academic-rag-model/
  viz/                                  # NEW package
    __init__.py                         # NEW -- empty, matches indexer/__init__.py convention
    README.md                           # NEW
    viz_agent.py                        # NEW -- VizResult, generate_visualization()
    llm_fallback.py                     # NEW -- Ollama call, code extraction, subprocess execution, caching
    templates/
      __init__.py                       # NEW -- Template, TEMPLATE_REGISTRY, match_template()
      spectral_decomposition.py         # NEW
      gradient_descent.py               # NEW
      distributions.py                  # NEW
      convergence.py                    # NEW
  rag/
    rag_agent.py                        # MODIFIED -- visualize param, AnswerResult.visualization, main() --visualize flag
  indexer/
    index_search.py                     # MODIFIED -- `ask` subcommand --visualize flag
  tests/
    test_viz_templates.py               # NEW
    test_viz_agent.py                   # NEW
    test_llm_fallback.py                # NEW
    test_rag_agent.py                   # MODIFIED -- visualize-integration tests
  docs/2026-09-02-visualization-agent-status.md  # NEW (Task 11)
.gitignore                              # MODIFIED (repo root) -- .viz/ entries
```

**A real interface note, caught while planning, not left implicit:** the design spec (written before this plan) assumed `rag_agent.answer_question()` took a single `academic_hub_root: str`. The actual shipped code takes `roots: list[str]` (multi-root support added after the spec's original draft). Task 9 below passes `roots[0]` to `generate_visualization()` — visualizing against the first/primary root — rather than trying to visualize across every root, since a single concept's illustrative example doesn't need multi-root grounding the way citation retrieval does.

---

## Task 1: Install Ollama and pull a code-capable model

**Files:** None — this task changes local machine state (installed software, a downloaded model), not repo content. No commit.

**Interfaces:**
- Produces: a running Ollama server reachable at `http://localhost:11434`, with the `qwen2.5-coder:7b` model pulled and available — consumed by Task 6's `viz/llm_fallback.py`.

- [ ] **Step 1: Install Ollama via winget**

Run (PowerShell):
```powershell
winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
```
Expected: installer completes without error. Ollama's installer also registers it to run as a background service, so it should be reachable without a separate manual start — verified in the next step.

- [ ] **Step 2: Verify the server is reachable**

Run (PowerShell):
```powershell
Invoke-RestMethod http://localhost:11434/api/version
```
Expected: a JSON response like `{"version":"0.x.x"}`. If this fails with a connection error, start it manually with `ollama serve` in a background terminal, then re-run this check.

- [ ] **Step 3: Pull the code-generation model**

Run (PowerShell):
```powershell
ollama pull qwen2.5-coder:7b
```
Expected: a progress bar, then `success`. This downloads ~4.7GB — expect several minutes depending on connection speed.

- [ ] **Step 4: Verify the model is available**

Run (PowerShell):
```powershell
ollama list
```
Expected: output includes a row for `qwen2.5-coder:7b`.

---

## Task 2: `viz` package skeleton — `Template` dataclass and keyword matcher

**Files:**
- Create: `ai-sandbox/academic-rag-model/viz/__init__.py`
- Create: `ai-sandbox/academic-rag-model/viz/templates/__init__.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_viz_templates.py`

**Interfaces:**
- Produces: `Template` (dataclass: `name: str, keywords: list[str], render: Callable[[], plotly.graph_objects.Figure]`), `TEMPLATE_REGISTRY: list[Template]` (starts empty, populated by Tasks 3-4), `match_template(concept: str) -> Template | None`.

- [ ] **Step 1: Install plotly and add it to the venv**

Run (PowerShell, from `ai-sandbox/academic-rag-model/`):
```powershell
.\.venv\Scripts\python.exe -m pip install plotly
```
Expected: `Successfully installed plotly-...`.

- [ ] **Step 2: Create the empty package marker**

```python
# ai-sandbox/academic-rag-model/viz/__init__.py
```
(Empty file — matches `indexer/__init__.py`'s own convention in this repo.)

- [ ] **Step 3: Write the failing test**

```python
# ai-sandbox/academic-rag-model/tests/test_viz_templates.py
import unittest
from unittest.mock import patch

from viz.templates import Template, match_template


def _fake_template(name="Fake", keywords=("fake concept", "fake alias")):
    return Template(name=name, keywords=list(keywords), render=lambda: "figure")


class TestMatchTemplate(unittest.TestCase):
    def test_matches_exact_keyword(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("fake concept"), template)

    def test_matches_keyword_as_substring_case_insensitively(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("Teach me about Fake Concept please"), template)

    def test_matches_alias_keyword(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("what is a fake alias"), template)

    def test_no_match_returns_none(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIsNone(match_template("totally unrelated topic"))

    def test_empty_registry_returns_none(self):
        with patch("viz.templates.TEMPLATE_REGISTRY", []):
            self.assertIsNone(match_template("anything"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: FAIL — `viz.templates` module doesn't exist yet.

- [ ] **Step 5: Implement**

```python
# ai-sandbox/academic-rag-model/viz/templates/__init__.py
"""
viz/templates/__init__.py
Registry of keyword-matched visualization templates (spec:
docs/superpowers/specs/2026-09-02-visualization-agent-design.md, §3).
Each template module exports one Template; importing this package
builds TEMPLATE_REGISTRY by importing every template module explicitly
-- adding a new concept is one new file plus one import at the bottom
of this file, no separate registration step to remember.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import plotly.graph_objects as go


@dataclass
class Template:
    name: str
    keywords: list[str]
    render: Callable[[], go.Figure]


TEMPLATE_REGISTRY: list[Template] = []


def match_template(concept: str) -> Template | None:
    """First-match keyword/alias substring lookup against `concept`,
    case-insensitive -- deliberately not semantic/embedding matching
    (spec §3), which keeps this path free and instant with only a
    handful of templates to search."""
    lowered = concept.lower()
    for template in TEMPLATE_REGISTRY:
        for keyword in template.keywords:
            if keyword in lowered:
                return template
    return None
```

- [ ] **Step 6: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/__init__.py ai-sandbox/academic-rag-model/viz/templates/__init__.py ai-sandbox/academic-rag-model/tests/test_viz_templates.py
git commit -m "feat(viz): add Template dataclass and keyword-based template matcher"
```

---

## Task 3: First template — spectral decomposition

**Files:**
- Create: `ai-sandbox/academic-rag-model/viz/templates/spectral_decomposition.py`
- Modify: `ai-sandbox/academic-rag-model/viz/templates/__init__.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_viz_templates.py`

**Interfaces:**
- Consumes: `Template` from `viz.templates` (Task 2).
- Produces: `viz.templates.spectral_decomposition.render() -> go.Figure`, `viz.templates.spectral_decomposition.TEMPLATE: Template`, registered into `TEMPLATE_REGISTRY`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_viz_templates.py`:

```python
from viz.templates import spectral_decomposition


class TestSpectralDecompositionTemplate(unittest.TestCase):
    def test_render_returns_four_traces(self):
        fig = spectral_decomposition.render()
        self.assertEqual(len(fig.data), 4)  # 2 eigenvectors x (original + transformed)

    def test_template_metadata(self):
        self.assertIn("spectral decomposition", spectral_decomposition.TEMPLATE.keywords)
        self.assertIs(spectral_decomposition.TEMPLATE.render, spectral_decomposition.render)

    def test_registered_in_global_registry(self):
        from viz.templates import TEMPLATE_REGISTRY
        self.assertIn(spectral_decomposition.TEMPLATE, TEMPLATE_REGISTRY)

    def test_matches_via_full_registry(self):
        from viz.templates import match_template
        self.assertIs(match_template("teach me about spectral decomposition"), spectral_decomposition.TEMPLATE)
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: FAIL — `viz.templates.spectral_decomposition` doesn't exist.

- [ ] **Step 3: Implement the template**

```python
# ai-sandbox/academic-rag-model/viz/templates/spectral_decomposition.py
"""
viz/templates/spectral_decomposition.py
Illustrates the spectral theorem: a symmetric matrix's eigenvectors
form an orthogonal basis, and applying the matrix to an eigenvector
only stretches it along its own line -- no rotation. Plotting each
eigenvector alongside its own image under the matrix makes that
"stays on its own line" property directly visible.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def render() -> go.Figure:
    matrix = np.array([[3.0, 1.0], [1.0, 2.0]])  # symmetric -> real eigenvalues, orthogonal eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)

    fig = go.Figure()
    colors = ["#1f77b4", "#d62728"]
    for i in range(2):
        v = eigenvectors[:, i]
        transformed = matrix @ v
        fig.add_trace(go.Scatter(
            x=[0, v[0]], y=[0, v[1]], mode="lines+markers",
            name=f"eigenvector {i + 1} (λ={eigenvalues[i]:.2f})",
            line=dict(color=colors[i], dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=[0, transformed[0]], y=[0, transformed[1]], mode="lines+markers",
            name=f"A · eigenvector {i + 1}",
            line=dict(color=colors[i]),
        ))
    fig.update_layout(
        title="Spectral decomposition: eigenvectors of a symmetric matrix stay on their own line under A",
        xaxis=dict(scaleanchor="y", range=[-4, 4]), yaxis=dict(range=[-4, 4]),
    )
    return fig


TEMPLATE = Template(
    name="Spectral decomposition",
    keywords=["spectral decomposition", "spectral theorem", "eigendecomposition"],
    render=render,
)
```

- [ ] **Step 4: Register it in the package**

Add to the end of `viz/templates/__init__.py`:

```python
from viz.templates.spectral_decomposition import TEMPLATE as _spectral_decomposition

TEMPLATE_REGISTRY.append(_spectral_decomposition)
```

- [ ] **Step 5: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: PASS (9 tests).

- [ ] **Step 6: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/templates/spectral_decomposition.py ai-sandbox/academic-rag-model/viz/templates/__init__.py ai-sandbox/academic-rag-model/tests/test_viz_templates.py
git commit -m "feat(viz): add spectral decomposition template"
```

---

## Task 4: Remaining templates — gradient descent, distributions, convergence

**Files:**
- Create: `ai-sandbox/academic-rag-model/viz/templates/gradient_descent.py`
- Create: `ai-sandbox/academic-rag-model/viz/templates/distributions.py`
- Create: `ai-sandbox/academic-rag-model/viz/templates/convergence.py`
- Modify: `ai-sandbox/academic-rag-model/viz/templates/__init__.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_viz_templates.py`

**Interfaces:**
- Consumes: `Template` from `viz.templates` (Task 2), same pattern as Task 3.
- Produces: `viz.templates.gradient_descent.{render, TEMPLATE}`, `viz.templates.distributions.{render, TEMPLATE}`, `viz.templates.convergence.{render, TEMPLATE}`, all three registered into `TEMPLATE_REGISTRY`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_viz_templates.py`:

```python
import math

from viz.templates import gradient_descent, distributions, convergence


class TestGradientDescentTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = gradient_descent.render()
        self.assertEqual(len(fig.data), 2)  # contour surface + descent path

    def test_template_metadata(self):
        self.assertIn("gradient descent", gradient_descent.TEMPLATE.keywords)


class TestDistributionsTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = distributions.render()
        self.assertEqual(len(fig.data), 2)  # binomial bars + normal curve

    def test_binomial_pmf_sums_to_one(self):
        _, pmf = distributions._binomial_pmf(n=40, p=0.5)
        self.assertAlmostEqual(sum(pmf), 1.0, places=6)

    def test_template_metadata(self):
        self.assertIn("central limit theorem", distributions.TEMPLATE.keywords)


class TestConvergenceTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = convergence.render()
        self.assertEqual(len(fig.data), 2)  # partial sums + limit line

    def test_template_metadata(self):
        self.assertIn("convergence", convergence.TEMPLATE.keywords)


class TestAllTemplatesRegistered(unittest.TestCase):
    def test_registry_has_four_templates(self):
        from viz.templates import TEMPLATE_REGISTRY
        self.assertEqual(len(TEMPLATE_REGISTRY), 4)
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: FAIL — the three modules don't exist yet.

- [ ] **Step 3: Implement `gradient_descent.py`**

```python
# ai-sandbox/academic-rag-model/viz/templates/gradient_descent.py
"""
viz/templates/gradient_descent.py
Illustrates gradient descent on a 2D bowl-shaped surface,
f(x, y) = x^2 + 2y^2: a contour plot of the surface plus the actual
descent path taken from a fixed starting point, so the path visibly
curves toward, then converges on, the minimum at the origin.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def _f(x, y):
    return x ** 2 + 2 * y ** 2


def _grad(x, y):
    return np.array([2 * x, 4 * y])


def render() -> go.Figure:
    xs = np.linspace(-4, 4, 100)
    ys = np.linspace(-4, 4, 100)
    zs = np.array([[_f(x, y) for x in xs] for y in ys])

    point = np.array([3.5, 3.0])
    learning_rate = 0.15
    path = [point.copy()]
    for _ in range(30):
        point = point - learning_rate * _grad(*point)
        path.append(point.copy())
    path = np.array(path)

    fig = go.Figure()
    fig.add_trace(go.Contour(x=xs, y=ys, z=zs, showscale=False, opacity=0.6, contours_coloring="lines"))
    fig.add_trace(go.Scatter(
        x=path[:, 0], y=path[:, 1], mode="lines+markers", name="gradient descent path",
        marker=dict(size=5, color="#d62728"),
    ))
    fig.update_layout(title="Gradient descent on f(x, y) = x² + 2y²: the path curves toward the minimum")
    return fig


TEMPLATE = Template(
    name="Gradient descent",
    keywords=["gradient descent", "steepest descent"],
    render=render,
)
```

- [ ] **Step 4: Implement `distributions.py`**

```python
# ai-sandbox/academic-rag-model/viz/templates/distributions.py
"""
viz/templates/distributions.py
Compares a binomial distribution against its normal approximation --
the central visual intuition behind the central limit theorem /
de Moivre-Laplace theorem: Binomial(n, p) looks increasingly
bell-shaped and normal as n grows. Implemented with plain numpy/math
(no scipy) to avoid adding a dependency this project doesn't otherwise
use.
"""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def _binomial_pmf(n: int, p: float) -> tuple[np.ndarray, np.ndarray]:
    ks = np.arange(0, n + 1)
    pmf = np.array([math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in ks])
    return ks, pmf


def _normal_pdf(xs: np.ndarray, mean: float, std: float) -> np.ndarray:
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((xs - mean) / std) ** 2)


def render() -> go.Figure:
    n, p = 40, 0.5
    ks, pmf = _binomial_pmf(n, p)
    mean, std = n * p, math.sqrt(n * p * (1 - p))
    xs = np.linspace(0, n, 200)
    normal = _normal_pdf(xs, mean, std)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=ks, y=pmf, name=f"Binomial(n={n}, p={p})", opacity=0.6))
    fig.add_trace(go.Scatter(x=xs, y=normal, mode="lines", name="Normal approximation"))
    fig.update_layout(title=f"Binomial(n={n}, p={p}) vs. its normal approximation -- CLT in action")
    return fig


TEMPLATE = Template(
    name="Distributions",
    keywords=["central limit theorem", "normal approximation", "binomial distribution", "distribution shape"],
    render=render,
)
```

- [ ] **Step 5: Implement `convergence.py`**

```python
# ai-sandbox/academic-rag-model/viz/templates/convergence.py
"""
viz/templates/convergence.py
Plots partial sums of the alternating harmonic series
(1 - 1/2 + 1/3 - 1/4 + ...) against n, illustrating visually that the
sequence of partial sums converges (to ln 2) even though no finite
prefix of terms sums to it exactly -- the core intuition behind
convergence of an infinite series.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def render() -> go.Figure:
    n_terms = 200
    ns = np.arange(1, n_terms + 1)
    terms = ((-1.0) ** (ns + 1)) / ns
    partial_sums = np.cumsum(terms)
    limit = np.log(2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ns, y=partial_sums, mode="lines", name="partial sum"))
    fig.add_trace(go.Scatter(
        x=[1, n_terms], y=[limit, limit], mode="lines", name="limit (ln 2)",
        line=dict(dash="dash", color="#d62728"),
    ))
    fig.update_layout(title="Partial sums of the alternating harmonic series converge to ln 2")
    return fig


TEMPLATE = Template(
    name="Series convergence",
    keywords=["convergence", "divergence", "partial sum", "alternating series", "series converges"],
    render=render,
)
```

- [ ] **Step 6: Register all three**

Add to the end of `viz/templates/__init__.py`:

```python
from viz.templates.gradient_descent import TEMPLATE as _gradient_descent
from viz.templates.distributions import TEMPLATE as _distributions
from viz.templates.convergence import TEMPLATE as _convergence

TEMPLATE_REGISTRY.extend([_gradient_descent, _distributions, _convergence])
```

- [ ] **Step 7: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_templates -v`
Expected: PASS (16 tests).

- [ ] **Step 8: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/templates/gradient_descent.py ai-sandbox/academic-rag-model/viz/templates/distributions.py ai-sandbox/academic-rag-model/viz/templates/convergence.py ai-sandbox/academic-rag-model/viz/templates/__init__.py ai-sandbox/academic-rag-model/tests/test_viz_templates.py
git commit -m "feat(viz): add gradient descent, distributions, and convergence templates"
```

---

## Task 5: `viz_agent.py` — `generate_visualization()`, template path only

**Files:**
- Create: `ai-sandbox/academic-rag-model/viz/viz_agent.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_viz_agent.py`

**Interfaces:**
- Consumes: `match_template` from `viz.templates` (Task 2).
- Produces: `VizResult` (dataclass: `html_path: str, title: str, source: str`), `generate_visualization(concept: str, context: str = "", academic_hub_root: str = "..", course: str | None = None) -> VizResult | None`. For this task, the no-template-match branch returns `None` directly — Task 7 replaces that with the LLM fallback call.

- [ ] **Step 1: Write the failing tests**

```python
# ai-sandbox/academic-rag-model/tests/test_viz_agent.py
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.templates import Template
from viz.viz_agent import VizResult, generate_visualization


def _fake_template(fig, keywords=("fake concept",)):
    return Template(name="Fake", keywords=list(keywords), render=lambda: fig)


class TestGenerateVisualizationTemplatePath(unittest.TestCase):
    def test_template_match_writes_html_and_returns_result(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course="math-camp")
        fake_fig.write_html.assert_called_once()
        self.assertEqual(result.source, "template")
        self.assertEqual(result.title, "Fake")
        self.assertTrue(result.html_path.startswith(os.path.join(tmp, ".viz", "math-camp")))
        self.assertTrue(result.html_path.endswith(".html"))

    def test_write_html_called_with_inline_plotlyjs(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                generate_visualization("fake concept", academic_hub_root=tmp)
        _, kwargs = fake_fig.write_html.call_args
        self.assertEqual(kwargs["include_plotlyjs"], "inline")

    def test_course_none_uses_uncategorized_folder(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course=None)
        self.assertIn("uncategorized", result.html_path)

    def test_slug_derived_from_concept(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig, keywords=("spectral decomposition",))
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("Spectral Decomposition!", academic_hub_root=tmp)
        self.assertTrue(os.path.basename(result.html_path).startswith("spectral-decomposition"))

    def test_no_template_match_returns_none_for_now(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None):
                result = generate_visualization("unmatched concept", academic_hub_root=tmp)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_agent -v`
Expected: FAIL — `viz.viz_agent` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# ai-sandbox/academic-rag-model/viz/viz_agent.py
"""
viz_agent.py
Generates interactive Plotly HTML visualizations for academic-hub
concepts (spec: docs/superpowers/specs/2026-09-02-visualization-agent-design.md).
One public entry point, generate_visualization() -- tries the
keyword-matched template library (viz.templates) first; falls back to
a local Ollama model (viz.llm_fallback) only when no template matches.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from viz.templates import match_template


@dataclass
class VizResult:
    html_path: str
    title: str
    source: str  # "template" | "llm_fallback"


def _slugify(concept: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", concept.lower()).strip("-")
    return slug or "concept"


def generate_visualization(
    concept: str, context: str = "", academic_hub_root: str = "..", course: str | None = None,
) -> VizResult | None:
    """Returns None if no template matches and the LLM fallback also
    fails -- callers must treat a missing visualization as a normal,
    expected outcome, never a hard dependency (spec §2)."""
    viz_root = os.path.join(academic_hub_root, ".viz")
    output_dir = os.path.join(viz_root, course or "uncategorized")
    output_path = os.path.join(output_dir, f"{_slugify(concept)}.html")

    template = match_template(concept)
    if template is not None:
        os.makedirs(output_dir, exist_ok=True)
        fig = template.render()
        fig.write_html(output_path, include_plotlyjs="inline")
        return VizResult(html_path=output_path, title=template.name, source="template")

    return None  # Task 7 replaces this with the Ollama fallback call
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_agent -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/viz_agent.py ai-sandbox/academic-rag-model/tests/test_viz_agent.py
git commit -m "feat(viz): add generate_visualization() with the template-match path"
```

---

## Task 6: `llm_fallback.py` — Ollama call, code extraction, subprocess execution, caching

**Files:**
- Create: `ai-sandbox/academic-rag-model/viz/llm_fallback.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_llm_fallback.py`

**Interfaces:**
- Consumes: `VizResult` from `viz.viz_agent` (Task 5).
- Produces: `generate_via_llm(concept: str, context: str, output_path: str, cache_dir: str) -> VizResult | None` — consumed by Task 7's `viz_agent.py`. Internal helpers `_cache_key`, `_extract_code`, `_call_ollama`, `_run_generated_code` are each independently tested below.

- [ ] **Step 1: Write the failing tests**

```python
# ai-sandbox/academic-rag-model/tests/test_llm_fallback.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: FAIL — `viz.llm_fallback` doesn't exist yet.

- [ ] **Step 3: Implement**

```python
# ai-sandbox/academic-rag-model/viz/llm_fallback.py
"""
llm_fallback.py
Local Ollama code-generation fallback for concepts with no matching
template (spec §4). Sends `concept`+`context` to a local Ollama model,
extracts the generated Plotly script, and runs it in a subprocess with
a timeout and a restricted set of pre-importable modules. Results are
cached on disk keyed by a hash of (concept, context) -- a repeated
request for the same concept+context shouldn't re-invoke a 30-60s+
local-model call.

Touches network (Ollama's local HTTP API) and subprocess execution --
_call_ollama itself is tested only with the network call mocked,
matching this project's established split for network-dependent code
(the real Gemini calls elsewhere in this project are the same way);
_run_generated_code and generate_via_llm's orchestration logic ARE
exercised for real (no network involved, fast, deterministic) -- see
this module's own tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

from viz.viz_agent import VizResult

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("VIZ_OLLAMA_MODEL", "qwen2.5-coder:7b")
EXECUTION_TIMEOUT_SECONDS = 60

_PROMPT_TEMPLATE = """Write a single self-contained Python script that uses the `plotly` and \
`numpy` libraries to create an interactive visualization illustrating this concept: {concept}

{context_block}
Requirements:
- Assign the finished figure to a variable named exactly `fig` (a plotly.graph_objects.Figure).
- Do not call fig.show(), fig.write_html(), or write any file yourself -- the caller handles that.
- Do not import anything other than plotly (as go or px) and numpy.
- Respond with ONLY one fenced ```python code block, nothing else.
"""

_CODE_BLOCK_PATTERN = re.compile(r"```python\s*(.*?)```", re.DOTALL)


def _cache_key(concept: str, context: str) -> str:
    return hashlib.sha256(f"{concept}\n{context}".encode("utf-8")).hexdigest()[:16]


def _extract_code(response_text: str) -> str | None:
    match = _CODE_BLOCK_PATTERN.search(response_text)
    return match.group(1).strip() if match else None


def _call_ollama(concept: str, context: str) -> str | None:
    context_block = f"Background from the student's own course materials:\n{context}\n" if context else ""
    prompt = _PROMPT_TEMPLATE.format(concept=concept, context_block=context_block)
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


def _run_generated_code(code: str, output_path: str, timeout: int = EXECUTION_TIMEOUT_SECONDS) -> bool:
    """Executes `code` in a fresh subprocess that pre-imports only
    plotly/numpy, then appends a fig.write_html(output_path) call and
    enforces `timeout`. Returns True only if the file actually got
    written -- never raises past its caller (spec §4)."""
    script = (
        "import plotly.graph_objects as go\n"
        "import plotly.express as px\n"
        "import numpy as np\n"
        f"{code}\n"
        f"fig.write_html({output_path!r}, include_plotlyjs='inline')\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        script_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"WARNING: generated visualization script failed:\n{result.stderr[-500:]}")
            return False
        return os.path.exists(output_path)
    except subprocess.TimeoutExpired:
        print(f"WARNING: generated visualization script timed out after {timeout}s")
        return False
    finally:
        os.unlink(script_path)


def generate_via_llm(concept: str, context: str, output_path: str, cache_dir: str) -> VizResult | None:
    os.makedirs(cache_dir, exist_ok=True)
    cached_path = os.path.join(cache_dir, f"{_cache_key(concept, context)}.html")

    if not os.path.exists(cached_path):
        response_text = _call_ollama(concept, context)
        if response_text is None:
            return None
        code = _extract_code(response_text)
        if code is None:
            print("WARNING: Ollama response contained no ```python code block")
            return None
        if not _run_generated_code(code, cached_path):
            return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copyfile(cached_path, output_path)
    return VizResult(html_path=output_path, title=concept, source="llm_fallback")
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_llm_fallback -v`
Expected: PASS (13 tests). The timeout test takes ~1 second (deliberately short via the `timeout=1` override) — the suite overall should still finish in a few seconds, not minutes.

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/llm_fallback.py ai-sandbox/academic-rag-model/tests/test_llm_fallback.py
git commit -m "feat(viz): add Ollama code-gen fallback with subprocess execution and disk caching"
```

---

## Task 7: Wire the LLM fallback into `generate_visualization()`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/viz/viz_agent.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_viz_agent.py`

**Interfaces:**
- Consumes: `generate_via_llm` from `viz.llm_fallback` (Task 6), imported function-scoped inside `generate_visualization()`.
- Produces: no new public names — `generate_visualization()`'s no-template-match branch now calls the fallback instead of returning `None` directly.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_viz_agent.py`:

```python
class TestGenerateVisualizationFallbackPath(unittest.TestCase):
    def test_no_template_match_falls_back_to_llm(self):
        fake_result = VizResult(html_path="/x/y.html", title="unknown concept", source="llm_fallback")
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=fake_result) as mock_llm:
                result = generate_visualization("unknown concept", context="ctx", academic_hub_root=tmp, course="math-camp")
        mock_llm.assert_called_once()
        args, kwargs = mock_llm.call_args
        self.assertEqual(args[0], "unknown concept")
        self.assertEqual(args[1], "ctx")
        self.assertEqual(result, fake_result)

    def test_fallback_receives_the_same_output_path_the_template_path_would_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=None) as mock_llm:
                generate_visualization("unknown concept", academic_hub_root=tmp, course="math-camp")
        args, kwargs = mock_llm.call_args
        output_path = args[2]
        self.assertTrue(output_path.startswith(os.path.join(tmp, ".viz", "math-camp")))

    def test_fallback_failure_propagates_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=None):
                result = generate_visualization("unknown concept", academic_hub_root=tmp)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_agent -v`
Expected: FAIL — `test_no_template_match_falls_back_to_llm` and its siblings fail because `generate_visualization()` still returns `None` directly (Task 5's stub), never calling `viz.llm_fallback.generate_via_llm`.

- [ ] **Step 3: Implement**

Replace the final line of `generate_visualization()` in `viz/viz_agent.py`:

```python
    return None  # Task 7 replaces this with the Ollama fallback call
```

with:

```python
    from viz.llm_fallback import generate_via_llm  # function-scoped: keeps the Ollama/
    # subprocess-dependent module out of the import path for callers that only ever hit
    # the template path (e.g. plain-Q&A callers of answer_question() that never set
    # visualize=True at all -- see Task 9)
    return generate_via_llm(concept, context, output_path, os.path.join(viz_root, ".cache"))
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_viz_agent -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Run the full viz test suite together**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_viz_*.py" -v`
Expected: PASS (all tests across `test_viz_templates.py`, `test_viz_agent.py`, `test_llm_fallback.py`).

- [ ] **Step 6: Commit**

```powershell
git add ai-sandbox/academic-rag-model/viz/viz_agent.py ai-sandbox/academic-rag-model/tests/test_viz_agent.py
git commit -m "feat(viz): wire the Ollama fallback into generate_visualization()"
```

---

## Task 8: `.gitignore` entry and `viz/README.md`

**Files:**
- Modify: `.gitignore` (repo root)
- Create: `ai-sandbox/academic-rag-model/viz/README.md`

**Interfaces:** None — documentation and repo hygiene only.

- [ ] **Step 1: Add the gitignore entries**

Open `.gitignore` and add, near the existing `.index/chunks/` entries (the file already groups related corpus-derived-artifact rules together with comments — add these alongside that group):

```gitignore
# Visualization sub-agent output (.viz/) is derivative of corpus content the
# same way .index/chunks/ is -- gitignored by default rather than judging
# verbatim-reproduction risk per template/concept (academic-hub-status doc's
# IP posture).
ai-sandbox/academic-hub/.viz/
ai-sandbox/research/.viz/
```

- [ ] **Step 2: Verify the pattern actually matches**

Run (PowerShell, from the repo root):
```powershell
New-Item -ItemType Directory -Force ai-sandbox/academic-hub/.viz/math-camp | Out-Null
New-Item -ItemType File -Force ai-sandbox/academic-hub/.viz/math-camp/test.html | Out-Null
git status --porcelain ai-sandbox/academic-hub/.viz/
Remove-Item -Recurse -Force ai-sandbox/academic-hub/.viz
```
Expected: `git status` prints nothing for that path (ignored) — if it lists the file as untracked, the gitignore pattern doesn't match and needs fixing before proceeding.

- [ ] **Step 3: Write `viz/README.md`**

```markdown
# Visualization Sub-Agent

Generates interactive Plotly HTML visualizations for academic-hub concepts —
a keyword-matched template library first, a local Ollama model as fallback
for concepts with no template. No paid API calls anywhere in this package.

Run directly:

```powershell
.\.venv\Scripts\python.exe -c "from viz.viz_agent import generate_visualization; print(generate_visualization('spectral decomposition', academic_hub_root='../academic-hub', course='math-camp'))"
```

Or via the tutor's own `--visualize` flag — see [`../rag/README.md`](../rag/README.md).

## Key files

- `viz_agent.py` — the one public entry point, `generate_visualization()`.
  Tries `templates.match_template()` first; falls back to `llm_fallback.generate_via_llm()`
  only when no template matches.
- `templates/` — one file per concept, each exporting a `Template` (name,
  keyword/alias list, a `render() -> plotly.graph_objects.Figure`). Adding a
  new concept is one new file plus one import at the bottom of
  `templates/__init__.py`.
- `llm_fallback.py` — sends the concept + retrieved context to a local Ollama
  model (`qwen2.5-coder:7b` by default, override with `VIZ_OLLAMA_MODEL`),
  extracts the generated Plotly script, runs it in a subprocess with a
  timeout and a restricted import set, and caches the result on disk keyed
  by a hash of (concept, context). Requires Ollama running locally
  (`ollama serve`) with the model pulled (`ollama pull qwen2.5-coder:7b`) —
  degrades to returning `None` with a printed warning if it isn't.

Output goes to `<root>/.viz/<course>/<slug>.html`, gitignored by default
(see the root `.gitignore`) — same IP posture as `.index/chunks/`.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-02-visualization-agent-design.md`.
```

- [ ] **Step 4: Commit**

```powershell
git add .gitignore ai-sandbox/academic-rag-model/viz/README.md
git commit -m "chore(viz): gitignore generated output and document the viz package"
```

---

## Task 9: Integrate into `rag_agent.answer_question()`

**Files:**
- Modify: `ai-sandbox/academic-rag-model/rag/rag_agent.py`
- Test: `ai-sandbox/academic-rag-model/tests/test_rag_agent.py`

**Interfaces:**
- Consumes: `generate_visualization` from `viz.viz_agent` (Task 7), imported function-scoped (mirrors the existing function-scoped `from rag.rag_agent import answer_question` pattern already used in `indexer/index_search.py`'s `ask` subcommand, for the same reason: avoiding an always-on dependency for callers that don't need it).
- Produces: `AnswerResult.visualization: VizResult | None` (new field, defaults to `None`), `answer_question(..., visualize: bool = False)` (new parameter).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rag_agent.py`:

```python
class TestAnswerQuestionVisualize(unittest.TestCase):
    def test_visualize_false_never_calls_generate_visualization(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization") as mock_viz:
            result = answer_question(["/root"], "q", client)
        mock_viz.assert_not_called()
        self.assertIsNone(result.visualization)

    def test_visualize_true_calls_generate_visualization_with_passage_text(self):
        client = _fake_generate_client("answer")
        passages = [_passage("a-000", "a", text="eigenvalue content", root="/root")]
        fake_result = MagicMock()
        with patch("rag.rag_agent.search_passages", return_value=passages), \
             patch("viz.viz_agent.generate_visualization", return_value=fake_result) as mock_viz:
            result = answer_question(["/root"], "what is X", client, visualize=True)
        mock_viz.assert_called_once()
        args, kwargs = mock_viz.call_args
        self.assertEqual(args[0], "what is X")
        self.assertIn("eigenvalue content", kwargs["context"])
        self.assertEqual(kwargs["academic_hub_root"], "/root")
        self.assertEqual(result.visualization, fake_result)

    def test_visualize_true_passes_course_through(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization", return_value=None) as mock_viz:
            answer_question(["/root"], "q", client, course="math-camp", visualize=True)
        self.assertEqual(mock_viz.call_args.kwargs["course"], "math-camp")

    def test_visualize_true_with_no_visualization_result_is_none(self):
        client = _fake_generate_client("answer")
        with patch("rag.rag_agent.search_passages", return_value=[]), \
             patch("viz.viz_agent.generate_visualization", return_value=None):
            result = answer_question(["/root"], "q", client, visualize=True)
        self.assertIsNone(result.visualization)
```

- [ ] **Step 2: Run to verify failure**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_rag_agent -v`
Expected: FAIL — `answer_question()` doesn't accept `visualize`, and `AnswerResult` has no `visualization` field.

- [ ] **Step 3: Implement**

In `rag/rag_agent.py`, modify the `AnswerResult` dataclass:

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

Modify `answer_question()`'s signature and body:

```python
def answer_question(
    roots: list[str], question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3, visualize: bool = False,
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
    citation retrieval does."""
    history = history or []
    retrieval_query = _reformulate_query(question, history, client) if history else question

    passages = search_passages(roots, retrieval_query, client, course=course, top_k=top_k * 2)
    passages = _diversify_by_file(passages, max_per_file)[:top_k]

    answer = _generate_answer(question, history, passages, client)
    citations = [
        Citation(chunk_id=p.chunk_id, file_id=p.file_id, path=p.path, citation=p.citation, root=p.root)
        for p in passages
    ]
    updated_history = history + [Turn(role="user", text=question), Turn(role="assistant", text=answer)]

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

    return AnswerResult(answer=answer, citations=citations, history=updated_history, visualization=visualization)
```

- [ ] **Step 4: Run to verify pass**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_rag_agent -v`
Expected: PASS (all tests, including the 4 new ones and every pre-existing test still passing).

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/rag/rag_agent.py ai-sandbox/academic-rag-model/tests/test_rag_agent.py
git commit -m "feat(rag): add opt-in visualize parameter to answer_question()"
```

---

## Task 10: CLI wiring — `--visualize` on `ask` and the REPL

**Files:**
- Modify: `ai-sandbox/academic-rag-model/indexer/index_search.py`
- Modify: `ai-sandbox/academic-rag-model/rag/rag_agent.py`

**Interfaces:** None new — thin CLI glue over `answer_question(visualize=...)` (Task 9), untested per this project's existing `main()` convention (Global Constraints).

- [ ] **Step 1: Add the flag to `index_search.py`'s `ask` subcommand**

In `build_arg_parser()`, change:

```python
    ask_p = subparsers.add_parser("ask", help="Ask a single grounded question (no conversation memory).")
    ask_p.add_argument("question")
    ask_p.add_argument("--course", default=None)
```

to:

```python
    ask_p = subparsers.add_parser("ask", help="Ask a single grounded question (no conversation memory).")
    ask_p.add_argument("question")
    ask_p.add_argument("--course", default=None)
    ask_p.add_argument("--visualize", action="store_true",
                        help="Also generate an interactive visualization for the question's concept.")
```

In `main()`, change the `ask` branch:

```python
    elif args.command == "ask":
        from rag.rag_agent import answer_question
        result = answer_question(roots, args.question, client, course=args.course)
        print(result.answer)
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
```

to:

```python
    elif args.command == "ask":
        from rag.rag_agent import answer_question
        result = answer_question(roots, args.question, client, course=args.course, visualize=args.visualize)
        print(result.answer)
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
```

- [ ] **Step 2: Add the flag to `rag_agent.py`'s REPL**

In `main()`, change:

```python
    parser.add_argument("--course", default=None)
    args = parser.parse_args()
```

to:

```python
    parser.add_argument("--course", default=None)
    parser.add_argument("--visualize", action="store_true",
                         help="Also generate an interactive visualization for each question's concept.")
    args = parser.parse_args()
```

And change the loop body:

```python
        result = answer_question(roots, question, client, history=history, course=args.course)
        print(f"\n{result.answer}\n")
        for c in result.citations:
            print(f"  - [{c.root}] {c.path} ({c.citation})")
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
        if result.visualization:
            print(f"  visualization: {result.visualization.html_path}")
        print()
        history = result.history
```

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, same total count as before this task (no new tests here, per Global Constraints).

- [ ] **Step 4: Commit**

```powershell
git add ai-sandbox/academic-rag-model/indexer/index_search.py ai-sandbox/academic-rag-model/rag/rag_agent.py
git commit -m "feat(cli): add --visualize flag to ask and the tutor REPL"
```

---

## Task 11: Real-corpus validation and status doc

**Files:**
- Create: `ai-sandbox/academic-rag-model/docs/2026-09-02-visualization-agent-status.md`

**Interfaces:** None — manual validation and documentation, closing out this plan the same way every other subproject in this repo has (see `docs/2026-08-30-rag-agent-status.md` for the precedent this follows).

- [ ] **Step 1: Run the full automated test suite one more time**

Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: PASS, full suite (this project's existing tests plus every test added in Tasks 2-9).

- [ ] **Step 2: Real query against a template-covered concept**

Run (PowerShell, from `ai-sandbox/academic-rag-model/`):
```powershell
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "teach me about spectral decomposition" --course math-camp --visualize
```
Expected: a grounded, cited answer prints, followed by a `visualization: ...` line pointing at an `.html` file under `academic-hub/.viz/math-camp/`. Open that file in a browser and confirm it renders an interactive plot (not a blank page or an error).

- [ ] **Step 3: Real query against a concept with no template (exercises the Ollama fallback)**

Run:
```powershell
.\.venv\Scripts\python.exe -m indexer.index_search --root ../academic-hub ask "explain the intermediate value theorem" --course math-camp --visualize
```
Expected: this concept has no template (§3's initial coverage list doesn't include it), so this exercises `llm_fallback.generate_via_llm()` for real against the locally running Ollama model — expect a longer wait (up to a couple of minutes on CPU) before either a `visualization:` line appears, or a `WARNING:` prints and the answer still comes back with `result.visualization` being `None` (acceptable — spec §1 explicitly treats a missing visualization as a normal, non-blocking outcome, not a failure of the tutor itself).

- [ ] **Step 4: Write the status doc**

```markdown
# Visualization Sub-Agent: Status Summary

Start here for "what happened and where do we stand" on the
visualization sub-agent -- `viz/`, which generates interactive Plotly
HTML visualizations for academic-hub concepts via a keyword-matched
template library (primary) and a local Ollama fallback (secondary).
Design reference: `docs/superpowers/specs/2026-09-02-visualization-agent-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-02-visualization-agent.md`.

## What shipped

One public entry point, `viz.viz_agent.generate_visualization(concept,
context, academic_hub_root, course)`, wired into
`rag_agent.answer_question()` as an opt-in `visualize: bool = False`
parameter -- off by default, so every existing caller (the REPL,
`index_search.py ask`, anything else already calling
`answer_question()`) is unaffected unless it opts in.

Two-tier resolution, both free of any paid API call:
1. **Template match** (`viz.templates.match_template()`) -- pure
   keyword/alias substring lookup against four initial templates
   (spectral decomposition, gradient descent, distributions/CLT,
   series convergence), each a hand-written Plotly-rendering function
   with a generic, well-chosen illustrative example.
2. **Ollama fallback** (`viz.llm_fallback.generate_via_llm()`) -- only
   reached when no template matches. Sends the concept plus retrieved
   passage context to a local `qwen2.5-coder:7b` model, extracts the
   generated Plotly script, runs it in a subprocess with a timeout and
   a restricted pre-imported module set, and caches the result on disk
   keyed by a hash of (concept, context).

## Real-corpus validation

Record here, after actually running Steps 2-3 above (do not write this
section until both have really been run): for the template path,
whether the "spectral decomposition" query's resulting `.html`
rendered a correct interactive plot when opened directly in a browser,
not just that the file was created. For the Ollama fallback path,
either confirm the "intermediate value theorem" query's `.html`
rendered correctly too, or -- if it didn't -- the exact `WARNING:` text
that printed and the wall-clock time the fallback call took, so a
future session has a real number to compare against rather than this
plan's own estimate.

## Specific limitations, honestly assessed

- **No parameter extraction from retrieved content.** Templates render
  a generic illustrative example (a representative matrix, a
  representative distribution), not the specific numbers from whatever
  passage was actually retrieved -- explicitly deferred in the spec
  (§1, §7): reliably parsing LaTeX/markdown math out of corpus text is
  a real, separate problem.
- **Only four template-covered concepts today.** Every other concept
  falls through to the slower, less reliable Ollama path. Growing
  coverage is adding one file to `viz/templates/` plus one import --
  cheap, but only done reactively as real questions hit the fallback
  path, not speculatively.
- **The Ollama fallback's real-world reliability is only as validated
  as Task 11 Step 3 above shows.** A small local model writing correct
  Plotly code unsupervised is a real risk area -- broken code, wrong
  concept coverage, or a slow response are all plausible failure
  modes this design tolerates (degrades to `None`, never blocks the
  tutor) but doesn't eliminate.
- **No automatic "does this question deserve a visualization" logic.**
  `visualize` is caller-set; nothing decides this automatically yet.

## What's next

Not spec'd, in rough order a future session might pick up:
1. Grow template coverage as real usage surfaces concepts that keep
   falling through to the slower Ollama path.
2. Revisit whether a heuristic (or the tutor's own generation call)
   should decide `visualize` automatically for certain question
   shapes, once there's real usage data on which questions actually
   benefit from a plot.
3. Parameter extraction from retrieved content, if generic illustrative
   examples turn out to be a real limitation in practice rather than a
   theoretical one.
```

- [ ] **Step 5: Commit**

```powershell
git add ai-sandbox/academic-rag-model/docs/2026-09-02-visualization-agent-status.md
git commit -m "docs(viz): add status summary after real-corpus validation"
```
