"""Checks a parsed model response against the grounding contract. Proves
a cited label exists, NOT that the passage entails the claim (known
limitation, spec 'Grounding boundary')."""
from __future__ import annotations

import re

from agent.summary_enhance.schema import ELABORATION_KINDS, Enhanced

# Label-like marker in free text, tolerant of case/space: "[S7", "[s1", "[ S1".
# Labels belong only in a block's `sources`; a marker inside text would render as
# a forged citation that looks exactly like a real one.
_LABEL_MARKER_RE = re.compile(r"\[\s*S\s*\d+", re.IGNORECASE)
# Every control character except newline (\x0a). A LaTeX command written with a
# single backslash in the model's JSON (\beta, \theta, \rho, \frac) is decoded by
# json.loads as a control character (backspace, tab, CR, form feed) followed by the
# rest of the word, silently corrupting the math (real finding, first live run,
# 2026-10-03).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x09\x0b-\x1f]")
_CONTROL_CHAR_HINT = "contains a control character (a LaTeX backslash was not doubled in the JSON)"
# \nu, \neq, \nabla ... with one backslash decode to a newline + "u"/"eq"/...;
# inline $...$ math never legitimately spans lines ($$...$$ display math may).
_INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)([^$]+?)(?<!\$)\$(?!\$)")
# A grounded line that starts a heading or blockquote, or names the callout, could
# forge a Sources section or pass grounded text off as labeled elaboration.
_FORGED_LINE_RE = re.compile(r"^[ \t]*[#>]", re.MULTILINE)
_CALLOUT_PHRASE = "not from the textbooks"


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def _text_errors(text: str, where: str, kind: str) -> list[str]:
    errors = []
    if not text.strip():
        errors.append(f"{where} is empty")
    if _CONTROL_CHAR_RE.search(text):
        errors.append(f"{where} {_CONTROL_CHAR_HINT}")
    if _LABEL_MARKER_RE.search(text):
        errors.append(f"{where} contains a source label in its text; "
                      + ("labels go only in 'sources'" if kind == "grounded"
                         else "elaboration must not cite the textbooks"))
    if any("\n" in m.group(1) for m in _INLINE_MATH_RE.finditer(text)):
        errors.append(f"{where} has a line break inside inline math "
                      "(a single-backslash \\nu, \\neq or \\nabla was decoded as a newline)")
    if kind == "grounded" and (_FORGED_LINE_RE.search(text) or _CALLOUT_PHRASE in text.lower()):
        errors.append(f"{where} would break the document structure "
                      "(heading/blockquote line or the 'Not from the textbooks' callout phrase)")
    return errors


def validate(enhanced: Enhanced, valid_labels: set[str], requested_topics: list[str]) -> list[str]:
    errors: list[str] = []
    if not enhanced.topics:
        errors.append("response contains no topics")
    present = {_norm(t.title) for t in enhanced.topics}
    for requested in requested_topics:
        if _norm(requested) not in present:
            errors.append(f"requested topic missing: {requested!r}")
    for topic in enhanced.topics:
        name = topic.title
        if not name.strip() or re.search(r"[\x00-\x1f]", name):
            errors.append(f"topic title {name!r} is empty or contains a line break/control character")
        if not topic.grounded:
            errors.append(f"topic {name!r} has no grounded blocks")
        for i, block in enumerate(topic.grounded, 1):
            where = f"topic {name!r} grounded block {i}"
            errors.extend(_text_errors(block.text, where, "grounded"))
            if not block.sources:
                errors.append(f"{where} has no sources")
            for label in block.sources:
                if label not in valid_labels:
                    errors.append(f"{where} cites unknown label {label!r}")
        for i, block in enumerate(topic.elaboration, 1):
            where = f"topic {name!r} elaboration block {i}"
            if block.kind not in ELABORATION_KINDS:
                errors.append(f"{where} has bad kind {block.kind!r}")
            errors.extend(_text_errors(block.text, where, "elaboration"))
    return errors
