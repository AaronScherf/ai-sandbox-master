"""
fact_diff.py
Free-text numeric-metric primitives (spec §5) -- the only fact-diff
mechanism Revision 2 still needs. Entry-heading extraction/diffing was
removed: master entries are now structured dicts (schema.py), not
Markdown headings, so there's no heading string left to regex-parse.
Metrics stay here (not schema.py) because they're meaningful on any
plain text regardless of schema -- used to scope validate.py's
per-entry bullet check to that entry's own original bullets.
"""
from __future__ import annotations

import re

_METRIC_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[MKBmkb]?|\d[\d,]*(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?x\b")


def extract_metrics(text: str) -> set[str]:
    """Every standalone numeric token with a $, %, or x suffix/prefix
    (e.g. '30%', '$2M', '10x')."""
    return {m.group(0) for m in _METRIC_RE.finditer(text)}


def metrics_not_traceable(candidate_text: str, source_text: str) -> list[str]:
    """Metric tokens in `candidate_text` that don't appear anywhere in
    `source_text` -- possible invented metric."""
    return sorted(m for m in extract_metrics(candidate_text) if m not in source_text)
