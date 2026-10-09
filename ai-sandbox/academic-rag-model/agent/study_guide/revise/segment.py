# agent/study_guide/revise/segment.py
"""Split a guide into heading-delimited blocks with stable ids, and check heading hygiene."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FRONT_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.S)
CONSTRUCTED = "constructed example (not from the sources)"


@dataclass(frozen=True)
class Block:
    id: str
    heading_path: tuple[str, ...]
    level: int
    start: int
    end: int
    text: str
    words: int
    equations: int
    constructed: bool


def split_frontmatter(markdown: str) -> tuple[str, str]:
    m = _FRONT_RE.match(markdown)
    return (markdown[:m.end()], markdown[m.end():]) if m else ("", markdown)


def segment(body: str) -> list[Block]:
    lines = body.split("\n")
    marks, fenced = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else _HEADING_RE.match(line)
        if m:
            marks.append((i, len(m.group(1)), m.group(2)))
    spans = []
    first = marks[0][0] if marks else len(lines)
    if first > 0 and "\n".join(lines[:first]).strip():
        spans.append((0, first, 0, ""))
    for k, (i, level, title) in enumerate(marks):
        spans.append((i, marks[k + 1][0] if k + 1 < len(marks) else len(lines), level, title))
    blocks, stack, seen = [], [], {}
    for start, end, level, title in spans:
        if level:
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        path = tuple(t for _, t in stack) if level else ()
        text = "\n".join(lines[start:end]).rstrip("\n")
        digest = hashlib.sha1((" > ".join(path) + "\n" + text[:200]).encode("utf-8")).hexdigest()[:10]
        seen[digest] = seen.get(digest, 0) + 1
        bid = "b" + digest + ("" if seen[digest] == 1 else f"-{seen[digest]}")
        blocks.append(Block(bid, path, level, start, end, text, len(text.split()), text.count("$$") // 2,
                            CONSTRUCTED in text.lower()))
    return blocks


def subtree_ids(blocks: list[Block], block_id: str) -> list[str]:
    """The block and every block beneath it (the following blocks with a deeper heading level)."""
    ids = [b.id for b in blocks]
    start = ids.index(block_id)
    head = blocks[start]
    if not head.level:
        return [head.id]
    out = [head.id]
    for b in blocks[start + 1:]:
        if b.level and b.level <= head.level:
            break
        out.append(b.id)
    return out


def check_headings(body: str) -> list[str]:
    problems, prev, h1s = [], 0, 0
    siblings: dict[tuple, set[str]] = {}
    for b in segment(body):
        if not b.level:
            continue
        title = b.heading_path[-1]
        if b.level == 1:
            h1s += 1
            if h1s > 1:
                problems.append(f"extra H1: {title!r}")
        if prev and b.level > prev + 1:
            problems.append(f"heading level jumps from H{prev} to H{b.level}: {title!r}")
        prev = b.level
        seen = siblings.setdefault(b.heading_path[:-1] + (b.level,), set())
        if title.casefold() in seen:
            problems.append(f"duplicate heading under {' > '.join(b.heading_path[:-1]) or 'top'}: {title!r}")
        seen.add(title.casefold())
        if not title.strip():
            problems.append("empty heading")
    return problems
