# agent/summary_enhance/mathfmt.py
"""Moves long inline formulas onto their own display-math block.

Done in the renderer (not left to the model) so the reading experience does not
depend on the model following a style instruction."""
from __future__ import annotations

import re

SYMBOL_LIMIT = 10

# Pandoc/Obsidian rules for inline math, so currency and escaped dollars are not math:
# the opening $ is not escaped and not followed by whitespace; the closing $ is not
# preceded by whitespace and not followed by a digit; an escaped dollar inside the span
# is a literal.
_INLINE_RE = re.compile(
    r"(?<![\\$])\$(?![\s$])((?:[^$\n\\]|\\.)+?)(?<![\s\\])\$(?![\d$])([.,;:]?)")
_SKIP_LINE_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||>|#{1,6}\s)")
_FENCE_RE = re.compile(r"^\s*```")
_CODE_SPAN_RE = re.compile(r"(`[^`\n]*`)")


def symbol_count(formula: str) -> int:
    """Each \\command is one symbol; so is each other non-space character except braces."""
    f = re.sub(r"\\[A-Za-z]+", "X", formula)
    f = re.sub(r"\\.", "X", f)
    return len(re.sub(r"[\s{}]", "", f))


def _convert_line(line: str) -> str:
    def repl(m: re.Match) -> str:
        formula = m.group(1).strip()
        if symbol_count(formula) <= SYMBOL_LIMIT:
            return m.group(0)
        return f"\n\n$$\n{formula}{m.group(2)}\n$$\n\n"

    parts = _CODE_SPAN_RE.split(line)  # odd indexes are `code spans`, left alone
    for i in range(0, len(parts), 2):
        parts[i] = _INLINE_RE.sub(repl, parts[i])
    return "".join(parts)


def split_display_math(text: str) -> str:
    out: list[str] = []
    in_fence = in_display = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        toggles = line.count("$$") % 2 == 1
        if in_display or toggles or _SKIP_LINE_RE.match(line):
            out.append(line)
            if toggles:
                in_display = not in_display
            continue
        out.append(_convert_line(line))
    result = "\n".join(out)
    result = re.sub(r"[ \t]+\n\n", "\n\n", result)
    result = re.sub(r"\n\n[ \t]+", "\n\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    if not text.endswith("\n"):
        result = result.rstrip("\n")
    if not text.startswith("\n"):
        result = result.lstrip("\n")
    return result
