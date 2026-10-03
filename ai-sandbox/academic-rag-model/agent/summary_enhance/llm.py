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


class LLMClient(Protocol):
    model: str

    def generate_structured(self, prompt: str, schema: dict) -> dict: ...


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[A-Za-z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)
    return t.strip()


class GeminiClient:
    def __init__(self, client, model: str = DEFAULT_MODEL):
        self._client = client
        self.model = model

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        response = call_with_retries(lambda: self._client.models.generate_content(
            model=self.model, contents=prompt,
            config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        ))
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("model returned an empty response")
        try:
            return json.loads(_strip_fences(text))
        except json.JSONDecodeError as err:
            raise ValueError(f"model response was not valid JSON: {err}") from err
