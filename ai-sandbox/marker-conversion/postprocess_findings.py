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
