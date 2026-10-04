"""
questions.py
Pure logic (no network) for resolving the `[Question]` tags in Excalidraw
notes: tag discovery and stable ids, the per-note sidecar of answers, and the
deterministic step that rewrites tags in the `.rag.md` into "resolved" markers.
The resolver itself (retrieval + generation + CLI) is agent/rag/resolve_questions.py.

Spec: docs/superpowers/specs/agent/rag/2026-10-03-question-resolver-design.md
"""
from __future__ import annotations

import difflib
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


_PAIR_SIMILARITY_MIN = 0.8


def _hash_part(qid: str) -> str:
    return qid.split("-", 1)[1] if "-" in qid else qid


def rekey_entries(tags: list[Tag], entries: list[Entry]) -> bool:
    """Moves an entry onto the id its question now has. An id embeds the
    question's ordinal, so re-transcribing a note after an earlier question was
    removed or reordered shifts every later ordinal, while the text hash -- the
    part that actually identifies the question -- is unchanged. An entry whose
    id no longer appears among `tags` but whose hash matches a tag that has no
    entry yet is renamed to that tag's id (no model call needed). Entries whose
    id is still current are never touched. Returns True if any id changed."""
    current = {t.qid for t in tags}
    answered = {e.qid for e in entries}
    waiting: dict[str, list[str]] = {}
    for tag in tags:
        if tag.qid not in answered:
            waiting.setdefault(_hash_part(tag.qid), []).append(tag.qid)
    changed = False
    for entry in entries:
        if entry.qid in current:
            continue
        targets = waiting.get(_hash_part(entry.qid))
        if targets:
            entry.qid = targets.pop(0)
            changed = True
    return changed


def marker_for(entry: Entry, sidecar_filename: str) -> str:
    label = "answered" if entry.grounded else "answered (ungrounded)"
    return f"[Question: {label} -> {sidecar_filename}#{entry.qid}]"


def _pair_tags(raw: list[Tag], rag: list[Tag]) -> dict[int, int]:
    """raw index -> rag index. By position when the counts agree (the
    expansion reworded the text but kept the tags); otherwise greedily by
    text similarity, leaving anything below the threshold unpaired."""
    if len(raw) == len(rag):
        return {i: i for i in range(len(raw))}
    pairs: dict[int, int] = {}
    used: set[int] = set()
    for i, raw_tag in enumerate(raw):
        best, best_ratio = None, 0.0
        for j, rag_tag in enumerate(rag):
            if j in used:
                continue
            ratio = difflib.SequenceMatcher(None, normalize(raw_tag.text), normalize(rag_tag.text)).ratio()
            if ratio > best_ratio:
                best, best_ratio = j, ratio
        if best is not None and best_ratio >= _PAIR_SIMILARITY_MIN:
            pairs[i] = best
            used.add(best)
    return pairs


def apply_markers(raw_path: str, rag_path: str) -> bool:
    """Makes every tag in the .rag.md reflect the sidecar: an answered
    question gets its resolved marker, anything else is (re)set to an open
    `[Question]`. Deterministic, no model call, idempotent. Also flags sidecar
    entries stale when their raw tag has no counterpart in the .rag.md, and
    clears the flag when one is found again. Returns True if either file
    changed."""
    if not os.path.exists(rag_path):
        return False
    sidecar = sidecar_path_for(raw_path)
    with open(raw_path, encoding="utf-8") as f:
        raw = raw_tags(f.read())
    with open(rag_path, encoding="utf-8") as f:
        rag_text = f.read()
    fields, entries = read_sidecar(sidecar)
    rekeyed = rekey_entries(raw, entries)
    by_id = {e.qid: e for e in entries}

    rag = find_tags(rag_text)
    replacement = {j: "[Question]" for j in range(len(rag))}
    matched: set[str] = set()
    for i, j in _pair_tags(raw, rag).items():
        entry = by_id.get(raw[i].qid)
        if entry is not None:
            replacement[j] = marker_for(entry, os.path.basename(sidecar))
            matched.add(entry.qid)

    new_text = rag_text
    for j in range(len(rag) - 1, -1, -1):
        new_text = new_text[: rag[j].start] + replacement[j] + new_text[rag[j].end:]
    changed = new_text != rag_text
    if changed:
        with open(rag_path, "w", encoding="utf-8") as f:
            f.write(new_text)

    stale_changed = False
    for entry in entries:
        should_be_stale = entry.qid not in matched
        if entry.stale != should_be_stale:
            entry.stale = should_be_stale
            stale_changed = True
    if stale_changed or rekeyed:
        write_sidecar(sidecar, fields, entries)
    return changed or stale_changed or rekeyed
