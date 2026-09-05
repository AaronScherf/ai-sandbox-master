"""
rag/report_builder.py
Combines one answer_question() call's question, answer text, citations,
and (optional) visualization into a single self-contained HTML document
(spec: docs/superpowers/specs/2026-09-05-combined-report-design.md). No
external dependencies (no CDN, no template engine) -- plain string
interpolation, matching the style already used throughout viz/.

`citations` and `visualization` below are typed only as lazily-evaluated
string annotations (this module has `from __future__ import
annotations`) -- deliberately not imported at module level from
rag_agent.py/viz_agent.py, matching AnswerResult.visualization's own
existing precedent in rag_agent.py, so a report=True, visualize=False
caller never pulls in either module's heavier dependencies just for a
type hint.
"""
from __future__ import annotations

import html
import os
import re

_SLUG_MAX_LENGTH = 80


def _slugify(text: str) -> str:
    """Duplicated from viz.viz_agent._slugify rather than imported, per
    this module's own module-level-import ban above."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = slug[:_SLUG_MAX_LENGTH].strip("-")
    return slug or "report"


def report_path(question: str, reports_root: str, course: str | None) -> str:
    return os.path.join(reports_root, course or "uncategorized", f"{_slugify(question)}.html")


def build_report(
    question: str, answer: str, citations: list[Citation], visualization: VizResult | None,
    output_path: str,
) -> str | None:
    """Writes one self-contained HTML file combining question, answer,
    citations, and (if given) the visualization's embedded fragment.
    Never raises past its caller -- any failure is logged as a WARNING
    and this returns None, leaving the rest of the answer untouched
    (spec §6)."""
    try:
        citations_html = "\n".join(
            f"  <li>[{html.escape(c.root)}] {html.escape(c.path)} ({html.escape(c.citation)})</li>"
            for c in citations
        )
        visualization_block = ""
        if visualization is not None:
            visualization_block = f"<h2>Visualization</h2>\n{visualization.fragment_html}\n"
        document = (
            f"<h1>{html.escape(question)}</h1>\n"
            f"<p>{html.escape(answer)}</p>\n"
            f"<h2>Citations</h2>\n"
            f"<ul>\n{citations_html}\n</ul>\n"
            f"{visualization_block}"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(document)
        return output_path
    except Exception as err:
        print(f"WARNING: report generation failed ({err})")
        return None
