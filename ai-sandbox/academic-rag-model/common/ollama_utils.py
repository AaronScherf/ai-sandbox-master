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


OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/api/embeddings"


def call_ollama_embeddings(
    text: str, model: str, request_timeout: int, url: str = OLLAMA_EMBEDDINGS_URL,
) -> list[float] | None | OllamaTimeout:
    """Same error-handling contract as call_ollama (spec:
    docs/superpowers/specs/2026-09-06-video-lecture-notes-design.md
    §7) -- POSTs to Ollama's embeddings endpoint instead of its
    generate endpoint."""
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
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
