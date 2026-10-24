"""
fact_diff.py
Free-text numeric-metric primitives (spec §5) -- the only fact-diff
mechanism Revision 2 still needs. Entry-heading extraction/diffing was
removed: master entries are now structured dicts (schema.py), not
Markdown headings, so there's no heading string left to regex-parse.
Metrics stay here (not schema.py) because they're meaningful on any
plain text regardless of schema -- used to scope validate.py's
per-entry bullet check to that entry's own original bullets.

Named-entity preservation (TODO-0044) extends this to award names,
degrees, and skill/tool names -- but unlike metrics these have no
generic regex shape, so they're not extracted from free text at all.
Instead the caller (validate.py) supplies a `vocabulary`: the literal
strings already sitting in the master resume's structured
`awards[].name`/`education[].degree`/`skills[].items` fields
(schema.py). `extract_known_entities` just checks which of those exact
terms appear as a whole word/phrase somewhere in a given text -- a
direct membership check against known structured values, not freeform
NER, since the data model already names these things explicitly and
there's no reason to guess at them from prose.
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


def extract_known_entities(text: str, vocabulary: list[str]) -> set[str]:
    """Every term from `vocabulary` that appears as a whole word/phrase
    somewhere in `text`, case-insensitively. Word-boundaried so a short
    term (e.g. an abbreviation like 'R') doesn't match as a substring
    inside an unrelated word (e.g. 'Grew'). Blank vocabulary entries are
    ignored. Does not attempt to recognize a paraphrase, rename, or
    consolidation of a term (spec §10-style known limitation, same as
    the metrics heuristic) -- only this exact string, case-insensitively."""
    found: set[str] = set()
    for term in vocabulary:
        if not term:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, text.lower()):
            found.add(term)
    return found


def entities_not_traceable(candidate_text: str, source_text: str, vocabulary: list[str]) -> list[str]:
    """Vocabulary terms present in `source_text` but missing from
    `candidate_text` -- a possible dropped award name, degree, or
    tool/technology. Only flags a term that was actually present in
    `source_text` to begin with, so an entity that was never mentioned
    for this entry in the first place is never reported as "dropped"."""
    in_source = extract_known_entities(source_text, vocabulary)
    in_candidate = extract_known_entities(candidate_text, vocabulary)
    return sorted(in_source - in_candidate)
