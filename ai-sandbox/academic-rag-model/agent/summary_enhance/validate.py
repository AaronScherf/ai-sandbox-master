"""Checks a parsed model response against the grounding contract. Proves
a cited label exists, NOT that the passage entails the claim (known
limitation, spec 'Grounding boundary')."""
from __future__ import annotations

import re

from agent.summary_enhance.schema import ELABORATION_KINDS, Enhanced

_LABEL_MARKER_RE = re.compile(r"\[S\d+")


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def validate(enhanced: Enhanced, valid_labels: set[str], requested_topics: list[str]) -> list[str]:
    errors: list[str] = []
    if not enhanced.topics:
        errors.append("response contains no topics")
    present = {_norm(t.title) for t in enhanced.topics}
    for requested in requested_topics:
        if _norm(requested) not in present:
            errors.append(f"requested topic missing: {requested!r}")
    for topic in enhanced.topics:
        name = topic.title
        if not topic.grounded:
            errors.append(f"topic {name!r} has no grounded blocks")
        for i, block in enumerate(topic.grounded, 1):
            if not block.text.strip():
                errors.append(f"topic {name!r} grounded block {i} is empty")
            if not block.sources:
                errors.append(f"topic {name!r} grounded block {i} has no sources")
            for label in block.sources:
                if label not in valid_labels:
                    errors.append(f"topic {name!r} grounded block {i} cites unknown label {label!r}")
        for i, block in enumerate(topic.elaboration, 1):
            if block.kind not in ELABORATION_KINDS:
                errors.append(f"topic {name!r} elaboration block {i} has bad kind {block.kind!r}")
            if not block.text.strip():
                errors.append(f"topic {name!r} elaboration block {i} is empty")
            if _LABEL_MARKER_RE.search(block.text):
                errors.append(f"topic {name!r} elaboration block {i} contains a source label; "
                              "elaboration must not cite the textbooks")
    return errors
