"""
viz/templates/__init__.py
Registry of keyword-matched visualization templates (spec:
docs/superpowers/specs/2026-09-02-visualization-agent-design.md, §3).
Each template module exports one Template; importing this package
builds TEMPLATE_REGISTRY by importing every template module explicitly
-- adding a new concept is one new file plus one import at the bottom
of this file, no separate registration step to remember.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import plotly.graph_objects as go


@dataclass
class Template:
    name: str
    keywords: list[str]
    render: Callable[[], go.Figure]


TEMPLATE_REGISTRY: list[Template] = []


def match_template(concept: str) -> Template | None:
    """First-match keyword/alias substring lookup against `concept`,
    case-insensitive -- deliberately not semantic/embedding matching
    (spec §3), which keeps this path free and instant with only a
    handful of templates to search."""
    lowered = concept.lower()
    for template in TEMPLATE_REGISTRY:
        for keyword in template.keywords:
            if keyword in lowered:
                return template
    return None
