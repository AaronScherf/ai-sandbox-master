# agent/summary_enhance/schema.py
"""Typed shape of the enhancement model's JSON responses. The grounded /
external split is the whole point: grounded blocks must cite passage labels,
external blocks can never cite and are always rendered with an
(External context) tag (see render.py)."""
from __future__ import annotations

import re
from dataclasses import dataclass

BLOCK_TYPES = ("grounded", "external")


@dataclass
class Block:
    type: str
    text: str
    sources: list[str]


@dataclass
class Section:
    heading: str
    blocks: list[Block]


@dataclass
class Topic:
    title: str
    sections: list[Section]
    worked_example: str | None = None


@dataclass
class Enhanced:
    topics: list[Topic]


TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": list(BLOCK_TYPES)},
                                "text": {"type": "string"},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["type", "text", "sources"],
                        },
                    },
                },
                "required": ["heading", "blocks"],
            },
        },
    },
    "required": ["title", "sections"],
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"topics": {"type": "array", "items": {"type": "string"}}},
    "required": ["topics"],
}


def _norm_label(label: str) -> str:
    """The prompt tags passages as "[S1]", and models echo that spelling ("[S5]", "s5")
    in `sources`. Normalize to the bare "S5" so a harmless spelling difference does not
    cost a paid retry (first live v2 run, 2026-10-03: a whole topic failed twice on this)."""
    return label.strip().strip("[]").strip().upper()


_ESCAPE_CORRUPTION_RE = re.compile("\x08|\x0c|\t(?=[A-Za-z])|\r(?=[A-Za-z])")
_ESCAPE_REPAIR = {"\x08": "\\b", "\x0c": "\\f", "\t": "\\t", "\r": "\\r"}


def _repair_latex_escapes(text: str) -> str:
    """A LaTeX command written with ONE backslash in the model's JSON (\\beta, \\frac,
    \\theta, \\rho) is decoded by json.loads as a control character plus the rest of the
    word. Those characters only arise from the \\b \\f \\t \\r escapes, so reversing them
    restores exactly what the model meant. Backspace and form feed never occur in prose; a
    tab or carriage return is repaired only when a letter follows it (so CRLF line endings
    and tab-separated spacing are left alone). Anything else is rejected by validation.
    (Live v2 run, 2026-10-04: the model dropped a backslash twice in a row and a whole run
    was lost.)"""
    return _ESCAPE_CORRUPTION_RE.sub(lambda m: _ESCAPE_REPAIR[m.group(0)], text)


def parse_topic(data: object) -> Topic:
    """Converts one decoded topic response into dataclasses. Raises ValueError
    on any structural problem (wrong type, missing key, unknown block type)."""
    if (not isinstance(data, dict) or not isinstance(data.get("title"), str)
            or not isinstance(data.get("sections"), list)):
        raise ValueError("topic must be an object with a string 'title' and a 'sections' list")
    sections = []
    for s in data["sections"]:
        if (not isinstance(s, dict) or not isinstance(s.get("heading"), str)
                or not isinstance(s.get("blocks"), list)):
            raise ValueError("each section needs a string 'heading' and a 'blocks' list")
        blocks = []
        for b in s["blocks"]:
            if (not isinstance(b, dict) or b.get("type") not in BLOCK_TYPES
                    or not isinstance(b.get("text"), str) or not isinstance(b.get("sources"), list)
                    or not all(isinstance(x, str) for x in b["sources"])):
                raise ValueError(f"section {s['heading']!r}: malformed block")
            blocks.append(Block(b["type"], _repair_latex_escapes(b["text"]),
                                [_norm_label(x) for x in b["sources"]]))
        sections.append(Section(s["heading"], blocks))
    return Topic(data["title"], sections)


def parse_plan(data: object) -> list[str]:
    if (not isinstance(data, dict) or not isinstance(data.get("topics"), list)
            or not all(isinstance(t, str) for t in data["topics"])):
        raise ValueError("plan must be an object with a list of string 'topics'")
    return list(data["topics"])
