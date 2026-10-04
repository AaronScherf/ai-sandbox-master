"""
questions.py
Pure logic (no network) for resolving the `[Question]` tags in Excalidraw
notes: tag discovery and stable ids, the per-note sidecar of answers, and the
deterministic step that rewrites tags in the `.rag.md` into "resolved" markers.
The resolver itself (retrieval + generation + CLI) is agent/rag/resolve_questions.py.

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from core.env.excalidraw_text import QUESTION_TAG_RE
from core.env.frontmatter import parse_frontmatter

_QUESTION_TEXT_CAP = 200
_WS_RE = re.compile(r"\s+")


def _collapse(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def normalize(text: str) -> str:
    return _collapse(text).lower()


def question_id(ordinal: int, text: str) -> str:
    digest = hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:8]
    return f"q{ordinal}-{digest}"


def question_text_after(text: str, tag_end: int) -> str:
    """The question a tag asks: the rest of the tag's line up to and including
    the first '?', else the whole line; if that line is blank, the next
    non-blank line. Whitespace-collapsed and capped."""
    for line in text[tag_end:].split("\n"):
        collapsed = _collapse(line)
        if collapsed:
            mark = collapsed.find("?")
            if mark != -1:
                collapsed = collapsed[: mark + 1]
            return collapsed[:_QUESTION_TEXT_CAP]
    return ""


@dataclass(frozen=True)
class Tag:
    ordinal: int  # 1-based, document order
    qid: str
    text: str
    start: int  # span of the whole tag token (open tag or resolved marker)
    end: int


def find_tags(markdown: str) -> list[Tag]:
    tags = []
    for ordinal, match in enumerate(QUESTION_TAG_RE.finditer(markdown), start=1):
        text = question_text_after(markdown, match.end())
        tags.append(Tag(ordinal, question_id(ordinal, text), text, match.start(), match.end()))
    return tags


def raw_tags(raw_text: str) -> list[Tag]:
    """Tags of a raw transcript, the stable source of ids (the .rag.md is
    regenerated and its wording can change; the raw transcript cannot)."""
    return find_tags(parse_frontmatter(raw_text)[1])
