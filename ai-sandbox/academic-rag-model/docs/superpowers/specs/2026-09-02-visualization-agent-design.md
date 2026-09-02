# Visualization Sub-Agent Design

Brainstormed and approved with the user 2026-09-02. Direct consumer of
the source indexer's retrieval (`indexer/index_search.py`'s
`search_passages()`) and a new peer of the RAG tutoring agent
(`rag/rag_agent.py`, `docs/superpowers/specs/2026-08-30-rag-agent-design.md`).

## 1. Problem & goals

The tutor (`answer_question()`) answers a question with cited text
grounded in retrieved passages. For concepts that are genuinely easier
to understand visually — spectral decomposition, gradient descent,
distribution shapes, convergence of a sequence — a static text
explanation is a weaker lesson than the same explanation plus an
interactive plot the student can manipulate. This spec builds a
**visualization sub-agent**: given a concept and (optionally) retrieved
context, it produces a standalone interactive HTML visualization, on
its own or as an opt-in step inside the tutor's existing pipeline.

**Explicit constraint carried through every decision below, set by the
user 2026-09-02:** no *new* paid API usage for this subproject. The
rest of the project accepts Gemini's cost for retrieval/generation;
this sub-agent's own code-generation and concept-matching paths are
deliberately kept free (keyword matching, a local Ollama model) rather
than adding incremental Gemini spend for a feature whose call volume
and prompt sizes are both much harder to bound in advance than the
tutor's fixed-shape single-question calls.

**Goals**
- Given a concept string (and optional retrieved-passage context),
  produce an interactive HTML visualization file, returned as a path
  plus lightweight metadata.
- Cover the common concept types in the current corpus (linear algebra,
  probability, optimization, analysis) via fast, free, deterministic
  templates; fall back to a local LLM for concepts with no template,
  rather than failing outright.
- Integrate into `rag_agent.answer_question()` as an explicit opt-in,
  not a behavior change to existing plain Q&A.
- Stay consistent with this project's existing IP posture — generated
  output is treated as a git-out artifact by default, same as every
  other corpus-derived intermediate file.

**Non-goals**
- Extracting the *exact* numbers/matrices/data from a specific
  retrieved passage to visualize that precise example. Templates render
  a generic, well-chosen illustrative instance of the concept instead —
  reliably parsing LaTeX/markdown math out of corpus text is a real,
  separate problem, not solved here (§7).
- Jupyter notebooks. Decided with the user 2026-09-02: standalone
  interactive HTML (Plotly) needs no runtime to view and is simpler to
  link to from a text answer than a notebook would be.
- A general-purpose sandboxed code execution environment (Docker,
  gVisor, etc.) for the LLM-fallback path. This is a single-user local
  tool the user themselves triggers — a subprocess timeout and a
  restricted pre-imported module set (§4) is the right amount of
  caution for that threat model, not container-grade isolation.
- Automatic decision-making about *when* a question warrants a
  visualization. The tutor pipeline exposes this as an opt-in parameter
  (§6); deciding when to set it is left to the caller.

## 2. Architecture

New package `viz/`, alongside `rag/`/`indexer/`/`postprocessing/` —
matching this project's existing per-subproject package convention
(own `__init__.py`, own `README.md`, run via `python -m viz.viz_agent`).

```
academic-rag-model/
  viz/
    __init__.py
    README.md
    viz_agent.py       # generate_visualization(), the one public entry point
    templates/
      __init__.py       # TEMPLATE_REGISTRY: dict[str, Template]
      spectral_decomposition.py
      gradient_descent.py
      distributions.py
      convergence.py
      ...
    llm_fallback.py     # Ollama code-gen + subprocess execution + caching
```

One public function, `viz/viz_agent.py`:

```python
from dataclasses import dataclass

@dataclass
class VizResult:
    html_path: str
    title: str
    source: str  # "template" | "llm_fallback"

def generate_visualization(
    concept: str, context: str = "", academic_hub_root: str = "..", course: str | None = None,
) -> VizResult | None:
    """Returns None if no template matches and the LLM fallback also
    fails (e.g. Ollama not running) -- callers must handle a viz being
    unavailable, never treat it as a hard dependency for the tutor to
    keep working."""
```

## 3. Template library (primary path)

Each template lives in its own file under `viz/templates/`, exporting
one `Template`:

```python
@dataclass
class Template:
    name: str
    keywords: list[str]  # e.g. ["spectral decomposition", "spectral theorem", "eigendecomposition"]
    render: Callable[[], go.Figure]  # a plotly.graph_objects.Figure, no arguments -- see below
```

**Matching is pure keyword/alias lookup against `concept`** — lowercase
substring match against each template's `keywords` list, first match
wins. Deliberately not embedding similarity or an LLM call: a few dozen
templates don't need semantic search, and this keeps the common path
free and instant, consistent with §1's constraint. `TEMPLATE_REGISTRY`
in `templates/__init__.py` is a flat list built by importing each
template module — adding a new concept is adding one file plus one
import, no separate registration step to remember.

`render()` takes no arguments by design — each template hand-picks its
own illustrative example (a representative 3×3 symmetric matrix for
spectral decomposition, a representative bimodal-vs-normal comparison
for distributions) rather than accepting parameters derived from
`context`. This is the direct consequence of §1's non-goal: extracting
a *specific* retrieved example's numbers reliably is out of scope, so
templates don't have a parameter contract that implies they could.
`context` is currently unused by the template path — kept as a
forward-looking parameter on `generate_visualization()` so a future
parameter-extraction capability (§7) doesn't need a signature change to
land.

**Initial template coverage**, chosen against the real corpus's four
subject areas (linear algebra, real analysis, probability,
optimization):
- `spectral_decomposition` — eigenvectors of a symmetric matrix shown
  as basis vectors, before/after a linear transformation.
- `gradient_descent` — descent path on a 2D contour surface, step count
  as a slider.
- `distributions` — normal/binomial/uniform shape comparison, with a
  parameter (mean, variance, n) as a slider.
- `convergence` — partial sums of a series or terms of a sequence
  plotted against n, illustrating convergence/divergence visually.

Each template renders via **Plotly** (`plotly.graph_objects`) —
interactive out of the box (zoom, rotate for 3D, hover tooltips,
sliders via `frames`), and its `Figure.write_html()` produces a fully
self-contained HTML file (Plotly's JS bundle inlined via
`include_plotlyjs="inline"` rather than `"cdn"`, so the file works
fully offline with no network dependency at view time, consistent with
this being a local-only tool).

## 4. LLM fallback (Ollama)

Invoked only when no template's keywords match `concept`. Confirmed
live 2026-09-02: **Ollama is not currently installed on this machine**
— installing it and pulling a code-capable model (`qwen2.5-coder`,
chosen for being a small, actively-maintained, code-focused open model)
is a setup prerequisite for this path, done once as part of the
implementation plan, not assumed to already exist.

```python
def generate_via_llm(concept: str, context: str, output_dir: str) -> VizResult | None:
    """Returns None (logged as a warning) if Ollama isn't reachable,
    generation fails, or the generated code errors/times out --
    matches index_card.py's own failure-isolation convention (§4.2 of
    the source-indexer spec): a missing/broken optional capability
    degrades gracefully, never raises past its caller."""
```

Flow:
1. Prompt the local model (via Ollama's HTTP API, `localhost:11434`) to
   write a self-contained Plotly Python script for `concept`, given
   `context` as background, that assigns its finished figure to a
   variable named `fig` and calls `fig.write_html(OUTPUT_PATH)` (path
   injected into the prompt/script, not hardcoded by the model).
2. Extract the code block from the response (regex for a fenced
   ```python block, same pattern this project already uses elsewhere
   for structured-text extraction from LLM output).
3. Run it in a **subprocess with a timeout** (default 60s — generous
   for a plotting script, generous enough that Ollama's slower
   CPU-bound generation doesn't itself need to race the execution
   timeout, since those are two separate steps) and a restricted
   `PYTHONPATH`/pre-imported namespace: only `plotly`, `numpy`, and
   `math` importable, nothing else. This is not a security sandbox
   against a malicious actor — it's a correctness guard against a
   broken generation (an infinite loop, an accidental `import os` doing
   something unintended) for a tool only the user themselves ever
   triggers, matching the "no paid API, personal local tool" threat
   model set for this whole subproject.
4. On success, return a `VizResult(source="llm_fallback")`. On any
   failure (bad code, timeout, non-zero exit, no `fig` produced), log a
   warning and return `None` — same failure-isolation principle as
   `index_card.py`'s minimal-card fallback.

**Caching.** Keyed by a truncated SHA-256 hash of `(concept, context)`,
stored as `academic-hub/.viz/.cache/<hash>.html` with the *served*
result symlinked/copied to the real output path — a repeated request
for the same concept+context doesn't re-invoke the local model (30-60s+
on CPU) or re-run the generated code. Mirrors this project's existing
`_pages_cache.json` pattern (transcription pipeline) and passage-chunk
caching: expensive, deterministic-given-input work gets cached by a
content hash of its own inputs.

## 5. Storage & IP policy

Output goes to `academic-hub/.viz/<course>/<slug>.html` (`slug` derived
from `concept`, collision-suffixed if needed), **gitignored by
default** — added to the existing deny-list `.gitignore` alongside
`.index/chunks/`. This project's IP policy (per the
`2026-08-30-academic-hub-status.md` doc) draws the line at
verbatim-reproduction risk vs. LLM-authored/derived description;
template output is generic and shouldn't contain verbatim corpus text,
but the LLM-fallback path's `context` input and any accompanying label
text plausibly could quote a retrieved passage — treating the whole
`.viz/` directory as git-out by default is the same conservative
default this project has applied consistently rather than relitigating
the verbatim-risk judgment call per template.

## 6. Integration with the tutor

`rag/rag_agent.py`'s `answer_question()` gains one new parameter,
`visualize: bool = False` — default off, so existing callers and the
existing REPL behavior are completely unchanged unless a caller opts
in:

```python
def answer_question(
    academic_hub_root: str, question: str, client,
    history: list[Turn] | None = None, course: str | None = None,
    top_k: int = 6, max_per_file: int = 3, visualize: bool = False,
) -> AnswerResult:
    ...
    if visualize:
        from viz.viz_agent import generate_visualization  # function-scoped import,
        # same circular-import-avoidance pattern already used for the `ask` subcommand's
        # import of rag_agent in index_search.py (§ "Corrections" in the rag-agent status doc)
        viz_context = "\n\n".join(p.text for p in passages)
        viz = generate_visualization(question, context=viz_context, academic_hub_root=academic_hub_root, course=course)
    else:
        viz = None
    ...
    return AnswerResult(answer=answer, citations=citations, history=updated_history, visualization=viz)
```

`AnswerResult` gains one new field, `visualization: VizResult | None`.
`concept` is passed as the raw `question` string, not a separately
LLM-extracted topic — the template keyword matcher (§3) does
substring matching, so "teach me about spectral decomposition" still
matches the `spectral_decomposition` template's keyword list without
needing an extra call to isolate "spectral decomposition" out of the
full sentence. A future refinement could extract a cleaner concept
string if template match rates in practice turn out too strict, but
that's a real-corpus-evidence-driven change (this project's established
pattern per the status doc), not a speculative one made now.

`main()`'s REPL and `index_search.py`'s `ask` subcommand both gain a
`--visualize` flag threading through to this parameter — when a
`VizResult` comes back, print its `html_path` alongside the existing
citation list.

## 7. Testing

`viz/templates/*.py` — each template's `render()` is pure (no
arguments, no I/O), tested by calling it and asserting a `go.Figure` is
returned with the expected number of traces — cheap, no mocking needed,
matches this project's existing "dependency-free core modules" pattern
(the cross-cutting pattern called out in the academic-hub status doc).

`viz/templates/__init__.py`'s keyword matcher — pure logic, tested with
a table of `(concept string, expected template name or None)` cases,
including near-miss strings that should *not* match, to catch
over-eager substring matches early (e.g. "eigenvalue" alone shouldn't
accidentally match every linear-algebra template).

`viz/llm_fallback.py` — the Ollama HTTP call and subprocess execution
are both network/process-dependent, so tested the same way this
project already handles that class of code (`transcribe_page_via_gemini`,
`render_page_to_image_bytes`): unit-tested with the Ollama call and
subprocess execution both mocked (assert the right prompt is built,
assert a non-zero exit or timeout returns `None` rather than raising),
not tested end-to-end in CI. Real end-to-end validation (does
`qwen2.5-coder` actually produce working Plotly code for a real
concept) happens as a one-off manual check during implementation,
consistent with how this project has validated every other
model-dependent capability — recorded in the status doc, not asserted
in a test that would otherwise need network access and real model
inference in CI.

`rag_agent.answer_question(visualize=True)` — tested with
`generate_visualization` mocked, asserting: `visualize=False` (default)
never imports or calls it; `visualize=True` calls it with the
concatenated passage text as `context` and attaches the returned
`VizResult` (or `None`) to `AnswerResult.visualization`.

## 8. Explicitly not built here

- **Parameter extraction from retrieved content** (§1, §3) — templates
  render a generic illustrative example, not the exact matrix/data from
  a specific retrieved passage. A real, separate capability (reliable
  math/data extraction from markdown/LaTeX) would need its own design,
  not assumed here.
- **Jupyter notebook output** (§1) — standalone HTML only, per the
  2026-09-02 decision with the user.
- **Automatic "should this question get a visualization" decision**
  (§1, §6) — `visualize` is caller-set; no heuristic or LLM call
  decides this automatically.
- **A general sandboxed execution environment** for LLM-generated code
  (§1, §4) — subprocess timeout + restricted imports only, matching
  this tool's single-user local threat model.
- **Semantic (embedding-based) template matching** (§3) — keyword/alias
  substring matching only; would only be revisited if real usage shows
  the keyword approach missing matches embedding similarity would catch
  (real-evidence-driven, not built speculatively).
- **A hosted/network-facing wrapper** — same reasoning as the RAG
  agent's own spec (§8 there): `generate_visualization()` is directly
  importable by anything in this environment; no server until a real
  cross-process caller needs one.
