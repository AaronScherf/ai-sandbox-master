"""
llm_fallback.py
Local Ollama code-generation fallback for concepts with no matching
template (spec §4). Sends `concept`+`context` to a local Ollama model,
extracts the generated Plotly script, and runs it in a subprocess with
an execution timeout, a minimal/stripped environment (no inherited
secrets -- see _minimal_subprocess_env), and a scratch working
directory -- plotly/numpy are pre-imported into the script's own
preamble for convenience, but this does NOT restrict which modules the
generated code itself can import; it still has full network access.
Results are cached on disk keyed by a hash of (concept, context) -- a
repeated request for the same concept+context shouldn't re-invoke a
30-60s+ local-model call.

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
- Prefer simple, well-documented trace types: go.Scatter, go.Bar, go.Contour, go.Surface. Stick to
  basic layout options: fig.update_layout(title=...), axis labels via xaxis_title/yaxis_title.
- Do NOT use speculative or exotic Plotly properties you are not certain exist (e.g. text styling
  properties like "bold", or a "z" property on a trace type that does not support one). If unsure
  whether a property exists, leave it out rather than guessing.
- Respond with ONLY one fenced ```python code block, nothing else.
"""

_CODE_BLOCK_PATTERN = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def _cache_key(concept: str, context: str) -> str:
    return hashlib.sha256(f"{concept}\n{context}".encode("utf-8")).hexdigest()[:16]


def _extract_code(response_text: str) -> str | None:
    match = _CODE_BLOCK_PATTERN.search(response_text)
    return match.group(1).strip() if match else None


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


def _minimal_subprocess_env() -> dict[str, str]:
    """A fresh, explicit environment for the generated-code subprocess --
    deliberately NOT the parent's os.environ. The parent process may hold
    paid API credentials (GEMINI_API_KEY, loaded via
    load_dotenv_override() elsewhere in this project); generated code
    (from a small local model that can produce broken or untrusted
    output) must never see secrets or get full inherited network/env
    context. Only the handful of variables Python itself needs to start
    up and run on Windows are passed through -- no secrets among them."""
    keys = ("PATH", "SYSTEMROOT", "PATHEXT", "TEMP", "TMP", "COMSPEC")
    return {key: os.environ[key] for key in keys if key in os.environ}


def _run_generated_code(code: str, output_path: str, timeout: int = EXECUTION_TIMEOUT_SECONDS) -> bool:
    """Executes `code` in a fresh subprocess that pre-imports only
    plotly/numpy, then appends a fig.write_html(output_path) call and
    enforces `timeout`. The subprocess runs with a minimal, explicit
    environment (see _minimal_subprocess_env -- no inherited secrets)
    and a scratch working directory (the temp dir holding its own
    generated script), not the caller's cwd, so a stray file write from
    generated code can't land in the project tree. Returns True only if
    the file actually got written -- never raises past its caller
    (spec §4)."""
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
            print(f"WARNING: generated visualization script failed:\n{result.stderr[-500:]}")
            return False
        return os.path.exists(abs_output_path)
    except subprocess.TimeoutExpired:
        print(f"WARNING: generated visualization script timed out after {timeout}s")
        return False
    except Exception as err:
        print(f"WARNING: generated visualization script raised an unexpected error: {err}")
        return False
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def generate_via_llm(concept: str, context: str, output_path: str, cache_dir: str) -> VizResult | None:
    """Generates a visualization via the local Ollama fallback, or returns
    None on any failure -- never raises past its caller (spec §4)."""
    try:
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
    except Exception as err:
        print(f"WARNING: LLM fallback failed unexpectedly ({err})")
        return None
