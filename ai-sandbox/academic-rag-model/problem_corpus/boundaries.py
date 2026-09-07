"""
boundaries.py
Pure, no-I/O detection of per-problem text spans in a file's body (spec:
docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 3). Regex patterns and the label-extraction logic are
duplicated from indexer/chunk_index.py's _detect_problem_boundaries /
_problem_label_at / _PROBLEM_BOUNDARY_PATTERNS, not imported -- same
precedent as rag/report_builder.py's _slugify (explicitly duplicated
from viz/viz_agent.py rather than imported), so this lower-level,
independently-testable module never reaches into another package's
underscore-prefixed internals for one piece of logic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),
    re.compile(r"(?m)^\*\*Practice Problem \d+"),
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same threshold and reasoning as chunk_index.py's
# own constant -- a weak/sparse match count isn't trusted as real structure.
_PROBLEM_LABEL_RE = re.compile(r"^\**\s*(?:Practice Problem|Problem|Question)?\s*(\d+)", re.IGNORECASE)


@dataclass
class ProblemSpan:
    text: str
    problem_label: str  # e.g. "Problem 1" -- falls back to the bare word
    # "Problem" (no number) if _PROBLEM_LABEL_RE finds no digit near the
    # boundary match, same as chunk_index.py's own _problem_label_at. Not
    # assumed unique within a file (two spans can both fall back to
    # "Problem") -- extractor.py's record-id hash includes the span's
    # index within the file specifically to stay collision-safe when
    # that happens, rather than relying on problem_label alone.


def _problem_label_at(body: str, start: int) -> str:
    first_line = body[start:start + 80].split("\n", 1)[0]
    m = _PROBLEM_LABEL_RE.match(first_line)
    return f"Problem {m.group(1)}" if m else "Problem"


def detect_spans(body: str) -> list[ProblemSpan]:
    """Returns one span per detected problem boundary (that problem's own
    text through the start of the next one, or end of document for the
    last one), or an empty list if fewer than _MIN_PROBLEM_MATCHES
    boundaries are found -- a file whose folder_category qualifies but
    whose content isn't actually numbered problems (e.g. a mini-lecture
    chapter intro) degrades to "nothing extracted here", not an error."""
    starts = set()
    for pattern in _PROBLEM_BOUNDARY_PATTERNS:
        starts.update(m.start() for m in pattern.finditer(body))
    if len(starts) < _MIN_PROBLEM_MATCHES:
        return []

    ordered = sorted(starts)
    spans = []
    for i, start in enumerate(ordered):
        end = ordered[i + 1] if i + 1 < len(ordered) else len(body)
        spans.append(ProblemSpan(text=body[start:end].strip(), problem_label=_problem_label_at(body, start)))
    return spans
