"""
llm_yaml.py
Parses YAML from an LLM's raw text response -- shared by normalize.py and
tailor.py, since both call a local Ollama model and expect a YAML-shaped
response back.

Confirmed real (2026-09-09, against the actual resume bootstrap): the
model sometimes emits a bare "-" as a placeholder for a missing/unknown
scalar value (e.g. "location: -"), which raw yaml.safe_load rejects
("sequence entries are not allowed here") -- a bare "-" at that position
is a sequence-item marker, not a scalar. Sanitized before parsing rather
than treated as an unrecoverable failure: retrying the whole slow,
CPU-only Ollama call over a one-token placeholder pattern is wasteful,
and the fix is unambiguous.
"""
from __future__ import annotations

import re

import yaml

_BARE_DASH_PLACEHOLDER_RE = re.compile(r"^(\s*[\w.-]+:)\s*-\s*$", re.MULTILINE)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def _quote_bare_dash_placeholders(text: str) -> str:
    return _BARE_DASH_PLACEHOLDER_RE.sub(r'\1 "-"', text)


def parse_llm_yaml(text: str) -> object | None:
    """Strips a markdown code fence if present, sanitizes the known
    bare-dash-placeholder pattern, and safely parses the result as YAML.
    Returns None (never raises) if the result still isn't valid YAML."""
    cleaned = _quote_bare_dash_placeholders(_strip_code_fence(text))
    try:
        return yaml.safe_load(cleaned)
    except yaml.YAMLError:
        return None
