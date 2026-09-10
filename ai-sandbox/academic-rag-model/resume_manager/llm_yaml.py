"""
llm_yaml.py
Parses YAML from an LLM's raw text response -- shared by normalize.py and
tailor.py, since both call a local Ollama model and expect a YAML-shaped
response back.

Confirmed real (2026-09-09, against the actual resume bootstrap), two
distinct failure modes:
1. The model sometimes emits a bare "-" as a placeholder for a missing/
   unknown scalar value (e.g. "location: -"), which raw yaml.safe_load
   rejects ("sequence entries are not allowed here") -- a bare "-" at
   that position is a sequence-item marker, not a scalar.
2. A scalar value that itself genuinely contains ": " (e.g. a real
   publication venue, "UC Berkeley: Data for Human Mobility Lab") is
   ambiguous when left unquoted -- YAML treats any unescaped ": " as
   introducing a nested mapping key, so raw yaml.safe_load rejects it
   ("mapping values are not allowed here"), even though the content
   itself was extracted correctly.
Both are sanitized before parsing rather than treated as unrecoverable
failures: retrying the whole slow, CPU-only Ollama call over a
narrow, unambiguous formatting slip is wasteful.
"""
from __future__ import annotations

import re

import yaml

_BARE_DASH_PLACEHOLDER_RE = re.compile(r"^(\s*[\w.-]+:)\s*-\s*$", re.MULTILINE)
_UNQUOTED_COLON_VALUE_RE = re.compile(
    r'^(\s*(?:-\s+)?[\w.-]+:)[ \t]+(?!["\'\[\{])([^\n]*:[ \t][^\n]*)$', re.MULTILINE,
)


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


def _quote_unquoted_colon_values(text: str) -> str:
    def _quote(match: re.Match) -> str:
        key, value = match.group(1), match.group(2)
        return f'{key} "{value.replace(chr(34), chr(92) + chr(34))}"'

    return _UNQUOTED_COLON_VALUE_RE.sub(_quote, text)


def parse_llm_yaml(text: str) -> object | None:
    """Strips a markdown code fence if present, sanitizes the two known
    LLM-YAML formatting slips (bare-dash placeholders, and an unquoted
    scalar that itself contains ": "), and safely parses the result as
    YAML. Returns None (never raises) if the result still isn't valid
    YAML."""
    cleaned = _strip_code_fence(text)
    cleaned = _quote_bare_dash_placeholders(cleaned)
    cleaned = _quote_unquoted_colon_values(cleaned)
    try:
        return yaml.safe_load(cleaned)
    except yaml.YAMLError:
        return None
