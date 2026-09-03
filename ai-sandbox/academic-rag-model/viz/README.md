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
  extracts the generated Plotly script, and runs it in a subprocess with an
  execution timeout, a minimal/stripped environment (no inherited secrets —
  in particular, the subprocess never sees `GEMINI_API_KEY`), and a scratch
  working directory, then caches the result on disk keyed by a hash of
  (concept, context). Plotly/numpy are pre-imported into the generated
  script's own preamble for convenience, but generated code can still import
  anything else and has full network access — this is execution isolation
  (timeout, no secrets, no shared cwd), not a sandbox that restricts which
  modules it can import. Requires Ollama running locally (`ollama serve`)
  with the model pulled (`ollama pull qwen2.5-coder:7b`) — degrades to
  returning `None` with a printed warning if it isn't.

Output goes to `<root>/.viz/<course>/<slug>.html`, gitignored by default
(see the root `.gitignore`) — same IP posture as `.index/chunks/`.

See the design spec for the full reasoning:
`../docs/superpowers/specs/2026-09-02-visualization-agent-design.md`.
