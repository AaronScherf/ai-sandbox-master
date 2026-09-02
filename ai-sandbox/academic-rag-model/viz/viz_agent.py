"""
viz_agent.py
Generates interactive Plotly HTML visualizations for academic-hub
concepts (spec: docs/superpowers/specs/2026-09-02-visualization-agent-design.md).
One public entry point, generate_visualization() -- tries the
keyword-matched template library (viz.templates) first; falls back to
a local Ollama model (viz.llm_fallback) only when no template matches.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from viz.templates import match_template


@dataclass
class VizResult:
    html_path: str
    title: str
    source: str  # "template" | "llm_fallback"


def _slugify(concept: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", concept.lower()).strip("-")
    return slug or "concept"


def generate_visualization(
    concept: str, context: str = "", academic_hub_root: str = "..", course: str | None = None,
) -> VizResult | None:
    """Returns None if no template matches and the LLM fallback also
    fails -- callers must treat a missing visualization as a normal,
    expected outcome, never a hard dependency (spec §2)."""
    viz_root = os.path.join(academic_hub_root, ".viz")
    output_dir = os.path.join(viz_root, course or "uncategorized")
    output_path = os.path.join(output_dir, f"{_slugify(concept)}.html")

    template = match_template(concept)
    if template is not None:
        os.makedirs(output_dir, exist_ok=True)
        fig = template.render()
        fig.write_html(output_path, include_plotlyjs="inline")
        return VizResult(html_path=output_path, title=template.name, source="template")

    return None  # Task 7 replaces this with the Ollama fallback call
