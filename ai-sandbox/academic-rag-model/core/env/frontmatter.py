"""
frontmatter.py
Minimal round-trip parser/renderer for this project's own flat YAML
frontmatter convention (as written by notes/transcribe_notes.py's
build_frontmatter): a "---" block of "key: value" lines, each value kept
as its original raw text rather than re-interpreted -- so a field the
caller doesn't touch (tags, routing, model, ...) round-trips exactly
byte-for-byte instead of risking a subtly different re-render through a
generic YAML scalar encoder. Not a general-purpose YAML parser -- same
narrow-scope rationale as build_frontmatter's own docstring.
"""
from __future__ import annotations

import re

_FRONTMATTER_BLOCK_RE = re.compile(r"\A---\n(.*?)\n---\n\n?", re.DOTALL)
_FRONTMATTER_LINE_RE = re.compile(r"^([A-Za-z0-9_]+):\s?(.*)$")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Splits a rendered .md's leading frontmatter block from its body.
    Returns ({}, content) unchanged if content has no frontmatter block at
    all, rather than raising -- a caller can always treat the result as
    "whatever fields were found" without a separate existence check."""
    match = _FRONTMATTER_BLOCK_RE.match(content)
    if not match:
        return {}, content
    fields: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        line_match = _FRONTMATTER_LINE_RE.match(line)
        if line_match:
            fields[line_match.group(1)] = line_match.group(2)
    return fields, content[match.end():]


def render_frontmatter(fields: dict) -> str:
    """Inverse of parse_frontmatter's field extraction -- values are
    written back exactly as given (already-raw strings), so this is safe
    to call with a dict built from parse_frontmatter's own output plus a
    few overridden/added keys, without needing build_frontmatter's
    scalar-quoting logic again."""
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"
