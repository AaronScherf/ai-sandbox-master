"""
Detection-support and finding-management logic for postprocess_notes.py
-- see docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md.
Pure Python, no PyMuPDF/transformers/network import at module scope.
"""
from __future__ import annotations

from transcribe_notes import is_expected_char


def is_allowlisted_span(text: str) -> bool:
    """
    True if every non-whitespace character in this span is already
    covered by transcribe_notes.py's own is_expected_char allowlist --
    the suppression signal confirmed necessary in the design spike: a
    candidate whose actual character is a legitimate math-range symbol
    (e.g. a Greek letter) must never be flagged, regardless of how
    surprising a small local model finds it. Confirmed in the same spike
    that this does NOT help distinguish an ordinary-but-wrong ASCII
    character (the ALLOWED_MATH_RANGES/is_expected_char check treats all
    ASCII as expected) -- that class of error relies on the model-based
    signals in local_model_scoring.py instead, not this suppression
    layer.
    """
    stripped = text.strip()
    if not stripped:
        return True
    return all(is_expected_char(c) for c in stripped)


def find_isolated_candidate_spans(lines: list[list[dict]]) -> list[dict]:
    """
    Structural pre-filter: a line consisting of exactly one span, whose
    text (stripped) is exactly one character, is structurally what a
    stripped operator/delimiter glyph looks like once mis-mapped to an
    ordinary character (confirmed real case: Analysis_Exercises.pdf page
    6, a radical sign extracting as a standalone "p" on its own line).
    `lines` is a list of PyMuPDF dict-mode lines, each a list of span
    dicts (the same shape reconstruct_line_with_scripts() already
    consumes). Zero-cost, no model involved -- this is one of three
    complementary detection signals (see local_model_scoring.py for the
    other two), not expected to be the only one.
    """
    candidates = []
    for spans in lines:
        if len(spans) != 1:
            continue
        text = spans[0].get("text", "").strip()
        if len(text) == 1:
            candidates.append({"text": text, "origin": spans[0].get("origin")})
    return candidates


def group_findings_by_signature(findings: list[dict]) -> dict[str, list[dict]]:
    """
    Groups low-confidence findings by document + flagged text, so
    repeated instances of the same kind of thing in the same document
    cluster together rather than each counting as its own isolated data
    point.
    """
    groups: dict[str, list[dict]] = {}
    for finding in findings:
        key = f"{finding['document']}::{finding['flagged_text']}"
        groups.setdefault(key, []).append(finding)
    return groups


def documents_needing_review(grouped: dict[str, list[dict]], threshold: int) -> list[str]:
    """
    Documents where at least one finding signature recurs `threshold`+
    times -- a genuine pattern, not an isolated one-off. Below that, a
    finding is logged (see build_changelog_entry) but never surfaced --
    the explicit requirement this exists to satisfy: don't review every
    single potentially-corrupted character across hundreds of pages.
    """
    documents = set()
    for group_findings in grouped.values():
        if len(group_findings) >= threshold:
            documents.update(f["document"] for f in group_findings)
    return sorted(documents)


def search_reference_documents(
    term: str, reference_texts: dict[str, str], context_chars: int = 80,
) -> list[dict]:
    """
    Plain substring search for `term` across every reference document's
    text, returning each match's surrounding context -- deliberately not
    semantic/vector search, since RAG Analysis (this project's sibling
    for that) isn't built yet; see the design spec's explicit decision to
    keep this self-contained rather than depend on it. Case-insensitive,
    since the same term can legitimately vary in case across documents
    written by different people. `reference_texts` maps document path to
    its full text.
    """
    term_lower = term.lower()
    if not term_lower.strip():
        return []
    matches = []
    for doc_path, text in reference_texts.items():
        text_lower = text.lower()
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break
            ctx_start = max(0, idx - context_chars)
            ctx_end = min(len(text), idx + len(term) + context_chars)
            matches.append({"document": doc_path, "context": text[ctx_start:ctx_end]})
            start = idx + len(term)
    return matches
