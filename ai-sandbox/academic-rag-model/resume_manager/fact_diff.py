"""
fact_diff.py
Shared fact-preservation checks used both to verify the bootstrap
conversion's LLM reformat step (convert_resume.py/normalize.py, spec
§3 step 4) and to flag possible fabrication in a tailored resume
(validate.py, spec §5). Two independent primitives: `### <Org> —
<Role> (<dates>)` entry headings (only meaningful once text is in the
master's structured convention) and free-text numeric metric tokens
(meaningful on any plain text, structured or not).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ENTRY_RE = re.compile(r"^###\s+(?P<org>.+?)\s+—\s+(?P<role>.+?)\s+\((?P<dates>.+?)\)\s*$", re.MULTILINE)
_METRIC_RE = re.compile(r"\$\d[\d,]*(?:\.\d+)?[MKBmkb]?|\d[\d,]*(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?x\b")


@dataclass(frozen=True)
class Entry:
    org: str
    role: str
    dates: str


def extract_entries(markdown_text: str) -> list[Entry]:
    """Every `### <Org> — <Role> (<dates>)` heading, in document order."""
    return [
        Entry(m.group("org").strip(), m.group("role").strip(), m.group("dates").strip())
        for m in _ENTRY_RE.finditer(markdown_text)
    ]


def extract_metrics(text: str) -> set[str]:
    """Every standalone numeric token with a $, %, or x suffix/prefix
    (e.g. '30%', '$2M', '10x') -- works on any text, markdown or raw
    (spec §5, and §3 step 4's identical use on raw extraction)."""
    return {m.group(0) for m in _METRIC_RE.finditer(text)}


def entries_not_traceable(candidate_text: str, source_text: str) -> list[Entry]:
    """Entries in `candidate_text` whose (org, role, dates) don't
    exactly match one in `source_text` -- possible fabrication. Only
    checks the candidate direction: a source entry missing from the
    candidate is never flagged (spec §5)."""
    source_entries = set(extract_entries(source_text))
    return [e for e in extract_entries(candidate_text) if e not in source_entries]


def metrics_not_traceable(candidate_text: str, source_text: str) -> list[str]:
    """Metric tokens in `candidate_text` that don't appear anywhere in
    `source_text` -- possible invented metric."""
    return sorted(m for m in extract_metrics(candidate_text) if m not in source_text)
