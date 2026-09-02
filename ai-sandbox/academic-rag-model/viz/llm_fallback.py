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
