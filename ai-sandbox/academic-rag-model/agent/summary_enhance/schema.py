"""Typed shape of the enhancement model's JSON response. The grounded /
elaboration split is the whole point: grounded blocks must cite passage
labels, elaboration blocks can never cite and are always rendered under
a "Not from the textbooks" callout (see render.py)."""
from __future__ import annotations

from dataclasses import dataclass, field

ELABORATION_KINDS = ("intuition", "example", "background")


@dataclass
class GroundedBlock:
    text: str
    sources: list[str]


@dataclass
class ElaborationBlock:
    kind: str
    text: str


@dataclass
class Topic:
    title: str
    grounded: list[GroundedBlock] = field(default_factory=list)
    elaboration: list[ElaborationBlock] = field(default_factory=list)


@dataclass
class Enhanced:
    topics: list[Topic]


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "grounded": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "sources": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "sources"],
                        },
                    },
                    "elaboration": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "string", "enum": list(ELABORATION_KINDS)},
                                "text": {"type": "string"},
                            },
                            "required": ["kind", "text"],
                        },
                    },
                },
                "required": ["title", "grounded", "elaboration"],
            },
        }
    },
    "required": ["topics"],
}


def parse_enhanced(data: object) -> Enhanced:
    """Converts the model's decoded JSON into dataclasses. Raises
    ValueError on any structural problem (wrong type, missing key)."""
    if not isinstance(data, dict) or not isinstance(data.get("topics"), list):
        raise ValueError("response must be an object with a 'topics' list")
    topics = []
    for t in data["topics"]:
        if not isinstance(t, dict) or not isinstance(t.get("title"), str):
            raise ValueError("each topic needs a string 'title'")
        grounded_raw, elab_raw = t.get("grounded"), t.get("elaboration")
        if not isinstance(grounded_raw, list) or not isinstance(elab_raw, list):
            raise ValueError(f"topic {t['title']!r} needs 'grounded' and 'elaboration' lists")
        grounded = []
        for g in grounded_raw:
            if (not isinstance(g, dict) or not isinstance(g.get("text"), str)
                    or not isinstance(g.get("sources"), list)
                    or not all(isinstance(s, str) for s in g["sources"])):
                raise ValueError(f"topic {t['title']!r}: malformed grounded block")
            grounded.append(GroundedBlock(g["text"], list(g["sources"])))
        elaboration = []
        for e in elab_raw:
            if (not isinstance(e, dict) or not isinstance(e.get("kind"), str)
                    or not isinstance(e.get("text"), str)):
                raise ValueError(f"topic {t['title']!r}: malformed elaboration block")
            elaboration.append(ElaborationBlock(e["kind"], e["text"]))
        topics.append(Topic(t["title"], grounded, elaboration))
    return Enhanced(topics)
