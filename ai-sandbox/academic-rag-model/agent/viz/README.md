# Visualization Sub-Agent

Generates interactive Plotly HTML visualizations for academic-hub concepts —
a keyword-matched template library first, an LLM fallback (Gemini by
default) for concepts with no template. Local Ollama is available as an
opt-in fallback backend — see `llm_fallback.py` below.

Run directly:

```powershell
.\.venv\Scripts\python.exe -c "from agent.viz.viz_agent import generate_visualization; print(generate_visualization('spectral decomposition', academic_hub_root='../academic-hub', course='math-camp'))"
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
- `llm_fallback.py` — sends the concept + retrieved context to the configured
  backend (`VIZ_BACKEND`, default `gemini`), extracts the generated Plotly
  script, and runs it in a subprocess with an execution timeout, a
  minimal/stripped environment (no inherited secrets — in particular, the
  subprocess never sees `GEMINI_API_KEY`), and a scratch working directory,
  then caches the result on disk keyed by a hash of (concept, context).
  Plotly/numpy are pre-imported into the generated script's own preamble for
  convenience, but generated code can still import anything else and has
  full network access — this is execution isolation (timeout, no secrets, no
  shared cwd), not a sandbox that restricts which modules it can import.
  Generation defaults to Gemini (`gemini-3.1-flash-lite`, override with
  `VIZ_GEMINI_MODEL`) — the same `GEMINI_API_KEY` this project already
  requires for retrieval, no extra setup. 2026-09-06, defaulted to Gemini
  after two real end-to-end trials of the problem-generation path's
  visualization request both failed on the local Ollama backend (two
  timeouts, then a broken script), then a follow-up real trial with Gemini
  succeeded 2/2 on the first attempt — the same reliability pattern (and
  same fix) as `problem_gen`'s own Gemini default; see
  [`../../docs/status/agent/viz/2026-09-02-visualization-agent-status.md`](../../docs/status/agent/viz/2026-09-02-visualization-agent-status.md)
  for the full comparison. Local Ollama generation is still available as an
  opt-in (`VIZ_BACKEND=ollama`, model `qwen2.5-coder:7b` by default, override
  with `VIZ_OLLAMA_MODEL`) for fully free/private generation — requires
  Ollama running locally (`ollama serve`) with the model pulled (`ollama
  pull qwen2.5-coder:7b`). Either backend degrades to returning `None` with
  a printed warning on failure, never a hard dependency.
- `example_store.py` — a local, free memory of past successful `llm_fallback.py`
  generations, used for few-shot prompting only (never rendered or matched
  directly). Before each Ollama call, looks up up to 2 past successes for a
  similar concept — via local embedding similarity (`nomic-embed-text`, high
  threshold) falling back to auto-derived-keyword overlap — and injects them
  into the prompt as worked examples. Every genuinely successful generation is
  appended to the store afterward. This is the **unverified** tier (only bar:
  "it ran without error") — deliberately kept separate from `templates/`'s
  **verified**, human-reviewed tier. Storage: a flat JSON file at
  `<root>/.viz/.examples/examples.json`, same gitignore posture as the cache.
  Requires a second local Ollama model (`ollama pull nomic-embed-text`),
  independent of the generation model.

Output goes to `<root>/.viz/<course>/<slug>.html`, gitignored by default
(see the root `.gitignore`) — same IP posture as `.index/chunks/`.

- `vault_emitter.py` — **Decoupled Asset Injection** (TODO-0053; design doc:
  `../../docs/brainstorms/agent/viz/2026-10-06-interactive-plotly-obsidian-pipeline.md`).
  Takes a `VizResult`'s already-produced `fragment_html` (or a raw fragment
  string via the lower-level `emit_vault_asset()`) and writes it unmodified
  to `<note_dir>/assets/<slug>_div.html` *inside the vault*, next to the
  note that will embed it — a different output location from `.viz/`
  above, which is a disposable render cache, not vault content. Returns a
  `VaultAsset` with the vault-relative path and a standardized, ready-to-paste
  DataviewJS mounting snippet (`app.vault.adapter.read` + script
  re-execution + an explicit pixel-height container). This sidesteps
  Pyodide's in-memory filesystem, the Webpage HTML Export plugin's
  iframe/transclusion deadlock, `file:///` CORS on embedded iframes, and
  0px container collapse — see the design doc for the full rationale. The
  caller (e.g. a future `agent/study_guide` `--visualize-interactive` flag)
  decides `note_dir` and inserts the returned snippet into the note; this
  module does no note-editing of its own.

See the design spec for the full reasoning:
`../../docs/superpowers/specs/agent/viz/2026-09-02-visualization-agent-design.md`.
