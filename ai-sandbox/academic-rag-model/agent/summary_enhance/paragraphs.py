"""Paragraph handling shared by the renderer and the restyler: fence/display-aware
paragraph splitting, and a simple readability rule that cuts any prose paragraph of
more than MAX_SENTENCES sentences into roughly equal paragraphs. The text itself is
never changed, only where the blank lines fall."""
from __future__ import annotations

import re

MAX_SENTENCES = 5

_FENCE_LINE_RE = re.compile(r"^\s*(?:```|~~~)")
# Headings, list items, tables, blockquotes, code fences and display math are not prose.
_NON_PROSE_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>|```|~~~|\$\$)")
# Inline code and math are masked (same length) before looking for sentence ends, so a
# period inside a formula is never a boundary.
_MASK_RE = re.compile(
    r"`[^`\n]*`|\$\$.+?\$\$|(?<![\\$])\$(?![\s$])(?:[^$\n\\]|\\.)+?(?<![\s\\])\$(?![\d$])", re.S)
# A sentence end: . ! or ? (plus closing punctuation), whitespace, then a capital letter or
# an opening symbol. A lowercase continuation or a digit ("p. 249", "5.99") is not a boundary.
_BOUNDARY_RE = re.compile(r"([.!?])([)\]\"'*_]*)(\s+)(?=[A-Z$\\(\[\"*])")
_ABBREVIATIONS = {"e.g", "i.e", "al", "vs", "cf", "fig", "figs", "eq", "eqs", "sec", "ch",
                  "chap", "p", "pp", "dr", "prof", "approx", "resp", "viz", "ca"}


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines, except inside code fences and $$ display blocks."""
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = in_display = False
    for line in text.strip().split("\n"):
        if not in_fence and not in_display and not line.strip():
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
        if _FENCE_LINE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.count("$$") % 2 == 1:
            in_display = not in_display
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def is_prose(paragraph: str) -> bool:
    return bool(paragraph.strip()) and not _NON_PROSE_RE.match(paragraph)


def split_sentences(text: str) -> list[str]:
    masked = _MASK_RE.sub(lambda m: "x" * len(m.group(0)), text)
    cuts: list[int] = []
    for m in _BOUNDARY_RE.finditer(masked):
        if m.group(1) == ".":
            token = re.search(r"([A-Za-z]+(?:\.[A-Za-z]+)*)$", masked[:m.start(1)])
            word = token.group(1) if token else ""
            # an abbreviation ("e.g.", "et al.", "p.") or a single-letter initial ("T. W.")
            if word.lower() in _ABBREVIATIONS or len(word) == 1:
                continue
        cuts.append(m.end())
    pieces, start = [], 0
    for cut in cuts:
        pieces.append(text[start:cut].strip())
        start = cut
    pieces.append(text[start:].strip())
    return [p for p in pieces if p]


def split_long_paragraph(paragraph: str, limit: int = MAX_SENTENCES) -> list[str]:
    """A prose paragraph of more than `limit` sentences becomes ceil(n / limit) paragraphs
    of as equal a size as possible (7 sentences -> 4 + 3). Anything else is returned as is."""
    if not is_prose(paragraph):
        return [paragraph]
    sentences = split_sentences(paragraph)
    n = len(sentences)
    if n <= limit:
        return [paragraph]
    groups = -(-n // limit)
    base, extra = divmod(n, groups)
    out, i = [], 0
    for g in range(groups):
        size = base + (1 if g < extra else 0)
        out.append(" ".join(sentences[i:i + size]))
        i += size
    return out


def split_long_paragraphs(paragraphs: list[str], limit: int = MAX_SENTENCES) -> list[str]:
    return [piece for p in paragraphs for piece in split_long_paragraph(p, limit)]
