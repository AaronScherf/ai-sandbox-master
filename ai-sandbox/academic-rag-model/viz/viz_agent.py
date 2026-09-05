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
    fragment_html: str  # the raw embeddable <div>/<script> fragment (plotly.js inlined,
    # no surrounding document tags) -- html_path's file is this fragment wrapped via
    # _wrap_fragment(); report_builder.py embeds this field directly, never html_path's file


_SLUG_MAX_LENGTH = 80


def _slugify(concept: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", concept.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LENGTH].strip("-")
    return slug or "concept"


def _wrap_fragment(fragment: str) -> str:
    """Wraps an embeddable Plotly fragment (a <div>/<script> pair, no
    surrounding document tags) in a minimal standalone document, for the
    direct-open .html files this module and llm_fallback.py both write
    to their `output_path` -- the fragment itself (not this wrapped
    form) is what report_builder.py embeds into a combined report
    (spec: docs/superpowers/specs/2026-09-05-combined-report-design.md
    §3)."""
    return f"<html><body>{fragment}</body></html>"


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
        try:
            os.makedirs(output_dir, exist_ok=True)
            fig = template.render()
            fragment = fig.to_html(include_plotlyjs="inline", full_html=False)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(_wrap_fragment(fragment))
            return VizResult(html_path=output_path, title=template.name, source="template", fragment_html=fragment)
        except Exception as err:
            print(f"WARNING: template visualization failed unexpectedly ({err})")
            return None

    from viz.llm_fallback import generate_via_llm  # function-scoped: keeps the Ollama/
    # subprocess-dependent module out of the import path for callers that only ever hit
    # the template path (e.g. plain-Q&A callers of answer_question() that never set
    # visualize=True at all -- see Task 9)
    return generate_via_llm(
        concept, context, output_path,
        os.path.join(viz_root, ".cache"), os.path.join(viz_root, ".examples"),
    )
