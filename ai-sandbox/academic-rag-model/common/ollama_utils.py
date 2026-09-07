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

_CHARS_PER_TOKEN_ESTIMATE = 4
_NUM_CTX_STEP = 2048
_NUM_CTX_RESPONSE_HEADROOM = 2048


def _estimate_num_ctx(prompt: str) -> int:
    """Ollama silently defaults to ~2048 tokens of context when a
    request doesn't set `options.num_ctx` -- confirmed live: an
    ~88,000-char (~22,000-token) prompt was processed as just its last
    ~2,050 tokens (`prompt_eval_count` in the raw API response), no
    error or warning, because llama.cpp keeps the *tail* of a prompt
    that overflows num_ctx rather than rejecting it. For call_ollama's
    single-shot, non-conversational use (every caller sends one
    complete prompt, never a running chat history), the right context
    size is simply "big enough for this exact prompt plus room to
    respond" -- estimated at ~4 chars/token (a standard rough estimate,
    not a measured tokenizer count) and rounded up to a clean 2048-token
    step, since num_ctx allocation is inherently approximate anyway."""
    estimated_prompt_tokens = len(prompt) // _CHARS_PER_TOKEN_ESTIMATE
    needed = estimated_prompt_tokens + _NUM_CTX_RESPONSE_HEADROOM
    return ((needed // _NUM_CTX_STEP) + 1) * _NUM_CTX_STEP


def call_ollama(
    prompt: str, model: str, request_timeout: int, url: str = OLLAMA_URL, num_ctx: int | None = None,
) -> str | None | OllamaTimeout:
    """POSTs `prompt` to a local Ollama model's HTTP API (non-streaming).
    Returns the response text, None if the server is unreachable, or
    OLLAMA_TIMEOUT if the request itself timed out. Never raises.
    `num_ctx` defaults to an estimate sized to `prompt` itself (see
    _estimate_num_ctx) rather than Ollama's own much smaller default,
    so a long prompt's beginning (often exactly where formatting/task
    instructions live) doesn't silently fall outside the context
    window. Pass an explicit value to override (e.g. to match a specific
    model's known maximum)."""
    if num_ctx is None:
        num_ctx = _estimate_num_ctx(prompt)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False, "options": {"num_ctx": num_ctx},
    }).encode("utf-8")
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


OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/api/embeddings"


def call_ollama_embeddings(
    text: str, model: str, request_timeout: int, url: str = OLLAMA_EMBEDDINGS_URL, num_ctx: int | None = None,
) -> list[float] | None | OllamaTimeout:
    """Same error-handling contract as call_ollama (spec:
    docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md
    §7) -- POSTs to Ollama's embeddings endpoint instead of its
    generate endpoint. Same num_ctx auto-sizing as call_ollama, for the
    same reason (see _estimate_num_ctx)."""
    if num_ctx is None:
        num_ctx = _estimate_num_ctx(text)
    payload = json.dumps({"model": model, "prompt": text, "options": {"num_ctx": num_ctx}}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body.get("embedding")
    except Exception as err:
        timed_out = isinstance(err, TimeoutError) or (
            isinstance(err, urllib.error.URLError) and isinstance(err.reason, TimeoutError)
        )
        if timed_out:
            print(f"WARNING: Ollama embeddings call to model '{model}' timed out after {request_timeout}s -- "
                  f"the model may just be slow on this request")
            return OLLAMA_TIMEOUT
        print(f"WARNING: Ollama embeddings call to model '{model}' failed ({err}) -- is `ollama serve` running and "
              f"has `ollama pull {model}` been run?")
        return None
