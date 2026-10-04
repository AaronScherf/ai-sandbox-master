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
import os
import re
from dataclasses import dataclass, field

from core.env.excalidraw_text import QUESTION_TAG_RE
from core.env.frontmatter import parse_frontmatter, render_frontmatter

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


SIDECAR_SUFFIX = ".excalidraw.questions.md"
_RAW_SUFFIX = ".excalidraw.md"
_RAG_SUFFIX = ".excalidraw.rag.md"


def sidecar_path_for(raw_path: str) -> str:
    if not raw_path.endswith(_RAW_SUFFIX):
        raise ValueError(f"not a raw Excalidraw transcript path: {raw_path!r}")
    return raw_path[: -len(_RAW_SUFFIX)] + SIDECAR_SUFFIX


def rag_path_for(raw_path: str) -> str:
    if not raw_path.endswith(_RAW_SUFFIX):
        raise ValueError(f"not a raw Excalidraw transcript path: {raw_path!r}")
    return raw_path[: -len(_RAW_SUFFIX)] + _RAG_SUFFIX


@dataclass
class Entry:
    qid: str
    question: str
    grounded: bool
    model: str
    resolved_at: str
    stale: bool = False
    context: str = ""
    answer: str = ""
    sources: list[str] = field(default_factory=list)


_NO_SOURCES = "none -- not sourced from your course materials."
_META_RE = re.compile(
    r"<!--\s*qid:\s*(?P<qid>[^;]+?);\s*grounded:\s*(?P<grounded>true|false);\s*model:\s*(?P<model>[^;]+?);\s*"
    r"resolved_at:\s*(?P<at>[^;]+?);\s*stale:\s*(?P<stale>true|false)\s*-->"
)
_SECTION_SPLIT_RE = re.compile(r"(?m)^## ")
_CONTEXT_RE = re.compile(r"\*\*Context:\*\*[ \t]*(.*)")


def render_entry(entry: Entry) -> str:
    # A line starting with "## " inside the answer would read as a new entry.
    answer = re.sub(r"(?m)^## ", "### ", entry.answer.strip())
    if entry.sources:
        sources = "**Sources:**\n" + "\n".join(f"- {s}" for s in entry.sources)
    else:
        sources = f"**Sources:** {_NO_SOURCES}"
    meta = (
        f"<!-- qid: {entry.qid}; grounded: {'true' if entry.grounded else 'false'}; model: {entry.model}; "
        f"resolved_at: {entry.resolved_at}; stale: {'true' if entry.stale else 'false'} -->"
    )
    return (
        f"## {entry.qid} - {_collapse(entry.question)}\n{meta}\n\n"
        f"**Context:** {_collapse(entry.context)}\n\n{answer}\n\n{sources}\n"
    )


def parse_entries(body: str) -> list[Entry]:
    """Reads entries back from the metadata comment and section boundaries
    only, so a user's prose edits inside an answer survive."""
    entries = []
    for section in _SECTION_SPLIT_RE.split(body)[1:]:
        heading, _, rest = section.partition("\n")
        meta = _META_RE.search(rest)
        if meta is None:
            continue
        question = heading.split(" - ", 1)[1].strip() if " - " in heading else ""
        after_meta = rest[meta.end():]
        sources_at = after_meta.rfind("**Sources:**")
        main_part = after_meta if sources_at == -1 else after_meta[:sources_at]
        sources_part = "" if sources_at == -1 else after_meta[sources_at + len("**Sources:**"):]
        context, answer = "", main_part
        context_match = _CONTEXT_RE.search(main_part)
        if context_match:
            context = context_match.group(1).strip()
            answer = main_part[context_match.end():]
        entries.append(Entry(
            qid=meta["qid"].strip(), question=question, grounded=meta["grounded"] == "true",
            model=meta["model"].strip(), resolved_at=meta["at"].strip(), stale=meta["stale"] == "true",
            context=context, answer=answer.strip(),
            sources=[ln[2:].strip() for ln in sources_part.splitlines() if ln.startswith("- ")],
        ))
    return entries


def read_sidecar(path: str) -> tuple[dict, list[Entry]]:
    if not os.path.exists(path):
        return {}, []
    with open(path, encoding="utf-8") as f:
        fields, body = parse_frontmatter(f.read())
    return fields, parse_entries(body)


def write_sidecar(path: str, fields: dict, entries: list[Entry]) -> None:
    """Atomic: the temp file is in the same folder so os.replace is a rename."""
    text = render_frontmatter(fields) + "\n".join(render_entry(e) for e in entries)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
