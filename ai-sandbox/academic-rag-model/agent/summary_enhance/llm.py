# agent/summary_enhance/llm.py
"""LLM boundary for the enhancement pipeline. Only GeminiClient touches the
network; everything else (and every test) depends on the LLMClient protocol."""
from __future__ import annotations

import json
import re
from typing import Protocol

from core.env.gemini_utils import call_with_retries

# Verified present on the paid key's model list 2026-10-03. Newest flash tier:
# one step above the tutor's gemini-3.6-flash, flash-priced.
DEFAULT_MODEL = "gemini-3.8-flash"
MAX_OUTPUT_TOKENS = 32768


class UnusableResponse(ValueError):
    """The call succeeded but its output cannot be used (truncated, empty, not JSON).
    A distinct type so callers retry only these, not unrelated ValueErrors (bad SDK
    config, a bug while building the prompt)."""


class LLMClient(Protocol):
    model: str

    def generate_structured(self, prompt: str, schema: dict) -> dict: ...

    def generate_text(self, prompt: str, *, code_execution: bool = False) -> str: ...


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t.strip()


def _truncated(response) -> bool:
    for cand in getattr(response, "candidates", None) or []:
        reason = getattr(cand, "finish_reason", None)
        name = getattr(reason, "name", None) or str(reason or "")
        if "MAX_TOKENS" in name:
            return True
    return False


class GeminiClient:
    def __init__(self, client, model: str = DEFAULT_MODEL):
        self._client = client
        self.model = model

    def _generate(self, prompt: str, config: dict) -> str:
        response = call_with_retries(lambda: self._client.models.generate_content(
            model=self.model, contents=prompt, config=config))
        if _truncated(response):
            raise UnusableResponse("response truncated (hit the output token limit)")
        text = getattr(response, "text", None)
        if not text:
            raise UnusableResponse("model returned an empty response")
        return text

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        text = self._generate(prompt, {
            "temperature": 0.2,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        })
        try:
            return json.loads(_strip_fences(text))
        except json.JSONDecodeError as err:
            raise UnusableResponse(f"model response was not valid JSON: {err}") from err

    def generate_text(self, prompt: str, *, code_execution: bool = False) -> str:
        config: dict = {"temperature": 0.2, "max_output_tokens": MAX_OUTPUT_TOKENS}
        if code_execution:
            from google.genai import types
            config["tools"] = [types.Tool(code_execution=types.ToolCodeExecution())]
        return self._generate(prompt, config).strip()
