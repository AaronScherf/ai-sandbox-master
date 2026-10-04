# agent/summary_enhance/validate.py
"""Checks parsed model output against the grounding and formatting contract.
Proves a cited label exists, NOT that the passage entails the claim (known
limitation, spec 'Grounding boundary')."""
from __future__ import annotations

import re

from agent.summary_enhance.schema import Topic

MIN_SECTIONS = 3
GROUNDED_SHARE = 0.5
MIN_WORKED_WORDS = 150
PLAN_MIN, PLAN_MAX = 3, 8

# Label-like marker in free text, tolerant of case/space: "[S7", "[s1", "[ S1".
# Labels belong only in a block's `sources`; a marker inside text would be a forged citation.
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
# Same Pandoc/Obsidian pairing rules as mathfmt, so currency ("$12 ... $15") is not math.
_INLINE_MATH_RE = re.compile(r"(?<![\\$])\$(?![\s$])((?:[^$\\]|\\.)+?)(?<![\s\\])\$(?![\d$])", re.DOTALL)
# A line that starts a heading or blockquote would forge document structure, except
# inside a code fence or a $$ display block.
_FORGED_LINE_RE = re.compile(r"^[ \t]*[#>]")
_FENCE_LINE_RE = re.compile(r"^\s*(?:```|~~~)")
# Worked examples are free text, not decoded JSON: tabs and newlines are legitimate.
_PLAIN_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x1f]")
# The renderer adds these tags itself; model text must not contain them.
_TAG_PHRASES = ("(external context)", "(worked example")


def _norm(title: str) -> str:
    return " ".join(title.split()).casefold()


def _single_line(text: str) -> bool:
    return bool(text.strip()) and not re.search(r"[\x00-\x1f]", text)


def _structure_forged(text: str) -> bool:
    """A line starting with # or > outside code fences and $$ display blocks."""
    in_fence = in_display = False
    for line in text.split("\n"):
        if _FENCE_LINE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_display:
            if line.count("$$") % 2 == 1:
                in_display = False
            continue
        if line.count("$$") % 2 == 1:
            in_display = True
            continue
        if _FORGED_LINE_RE.match(line):
            return True
    return False


def _text_errors(text: str, where: str, kind: str) -> list[str]:
    """kind: "grounded"/"external" (text decoded from the model's JSON) or "worked"
    (free text from the code-execution call). The JSON-corruption checks (control
    characters, a newline inside inline math) only make sense for the former."""
    from_json = kind != "worked"
    errors = []
    if not text.strip():
        errors.append(f"{where} is empty")
    if from_json and _CONTROL_CHAR_RE.search(text):
        errors.append(f"{where} {_CONTROL_CHAR_HINT}")
    elif not from_json and _PLAIN_CONTROL_CHAR_RE.search(text):
        errors.append(f"{where} contains a control character")
    if _LABEL_MARKER_RE.search(text):
        errors.append(f"{where} contains a source label in its text; "
                      + ("labels go only in 'sources'" if kind == "grounded"
                         else "external text must not cite the textbooks"))
    if from_json and any("\n" in m.group(1) for m in _INLINE_MATH_RE.finditer(text)):
        errors.append(f"{where} has a line break inside inline math "
                      "(a single-backslash \\nu, \\neq or \\nabla was decoded as a newline)")
    if _structure_forged(text):
        errors.append(f"{where} would break the document structure (a line starting with # or >)")
    low = text.lower()
    if any(p in low for p in _TAG_PHRASES):
        errors.append(f"{where} contains a context tag; the renderer adds those")
    return errors


def validate_topic(topic: Topic, valid_labels: set[str], requested_title: str, min_words: int) -> list[str]:
    errors: list[str] = []
    name = requested_title
    if _norm(topic.title) != _norm(requested_title):
        errors.append(f"topic title {topic.title!r} does not match the requested {requested_title!r}")
    if len(topic.sections) < MIN_SECTIONS:
        errors.append(f"topic {name!r} has {len(topic.sections)} sections; at least {MIN_SECTIONS} are required")
    total = grounded = 0
    for si, section in enumerate(topic.sections, 1):
        where_s = f"topic {name!r} section {si}"
        if not _single_line(section.heading):
            errors.append(f"{where_s} heading {section.heading!r} is empty or contains a line break/control character")
        if not section.blocks:
            errors.append(f"{where_s} has no blocks")
        for bi, block in enumerate(section.blocks, 1):
            where = f"{where_s} block {bi}"
            errors.extend(_text_errors(block.text, where, block.type))
            n = len(block.text.split())
            total += n
            if block.type == "grounded":
                grounded += n
                if not block.sources:
                    errors.append(f"{where} has no sources")
                for label in block.sources:
                    if label not in valid_labels:
                        errors.append(f"{where} cites unknown label {label!r}")
            elif block.sources:
                errors.append(f"{where} is external but lists sources")
    if total < min_words:
        errors.append(f"topic {name!r} has {total} words; at least {min_words} are required")
    if total and grounded < GROUNDED_SHARE * total:
        errors.append(f"topic {name!r}: at least half of the words must be in grounded blocks "
                      f"({grounded} of {total})")
    return errors


def validate_plan(titles: list[str]) -> list[str]:
    errors: list[str] = []
    if not PLAN_MIN <= len(titles) <= PLAN_MAX:
        errors.append(f"plan has {len(titles)} topics; it must have {PLAN_MIN} to {PLAN_MAX}")
    seen: set[str] = set()
    for title in titles:
        if not _single_line(title):
            errors.append(f"topic title {title!r} is empty or contains a line break/control character")
            continue
        key = _norm(title)
        if key in seen:
            errors.append(f"duplicate topic title {title!r}")
        seen.add(key)
    return errors


def validate_worked_example(text: str) -> list[str]:
    errors = _text_errors(text, "worked example", "worked")
    if len(text.split()) < MIN_WORKED_WORDS:
        errors.append(f"worked example has {len(text.split())} words; at least {MIN_WORKED_WORDS} are required")
    if "$" not in text:
        errors.append("worked example contains no math ($...$)")
    return errors
