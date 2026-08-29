"""
chunk_index.py
Passage-level chunking, embedding, and storage for the academic-hub
source indexer (spec: docs/superpowers/specs/2026-08-29-passage-embeddings-design.md).

Deliberately separate from index_card.py (per-file cards) and
retag.py (corpus-wide tag mining) -- chunking is per-file like cards,
but runs on its own explicit schedule (index_search.py's `chunk`
subcommand), not automatically inside a pipeline hook, for the same
reason retag stays a separate pass: a first-time capability like this
is lower-risk built and proven standalone first, and hook-time
chunking would mean a single textbook conversion run also pays for
potentially hundreds of chunk-embedding calls inline with no separate
control over when that cost is paid.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


def chunks_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "chunks")


def chunks_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(chunks_dir(academic_hub_root), f"{course}.json")


def load_chunks(academic_hub_root: str, course: str) -> list[dict]:
    path = chunks_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chunks(academic_hub_root: str, course: str, chunks: list[dict]) -> None:
    path = chunks_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)


_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n\n?", re.DOTALL)
_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


def _strip_yaml_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def _page_markers(body: str) -> list[tuple[int, int]]:
    return [(int(m.group(1)), m.start()) for m in _PAGE_MARKER_RE.finditer(body)]


def _strip_front_matter_by_page(body: str, front_matter_end: int) -> str:
    """Drops everything up to and including the last front-matter page
    (title page, author, table of contents) for a textbook -- confirmed
    live that Marker's conversion marks front-matter lines with `#`
    (e.g. a bare author name), which would otherwise produce garbage
    heading-tier chunks. front_matter_end is the same boundary
    describe_images.py's load_front_matter_end() already reads from
    run_config.json for exactly this purpose on the image-description
    side."""
    for page, offset in _page_markers(body):
        if page > front_matter_end:
            return body[offset:]
    return body  # nothing past the boundary was found -- keep everything


@dataclass
class _Span:
    start: int
    end: int
    tier: str
    heading_path: list[str] | None = None
    problem_label: str | None = None


_HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.*)$")
_MIN_HEADING_MATCHES = 2  # confirmed live: old_exam_2021.md has exactly 1
# real heading in 22 pages -- not real document structure. 2+ is the
# floor for "this file is actually organized into headed sections."


def _split_by_headings(body: str) -> list[_Span] | None:
    matches = list(_HEADING_RE.finditer(body))
    if len(matches) < _MIN_HEADING_MATCHES:
        return None

    spans = []
    stack: list[tuple[int, str]] = []  # (heading level, heading text)
    for i, m in enumerate(matches):
        level = len(m.group(1))
        heading_text = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)

        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading_text))

        spans.append(_Span(
            start=start, end=end, tier="heading",
            heading_path=[h for _, h in stack],
        ))
    return spans


_PROBLEM_BOUNDARY_PATTERNS = [
    re.compile(r"(?m)^\d+\.\s"),
    re.compile(r"(?m)^\*\*Practice Problem \d+"),
    re.compile(r"(?m)^Problem \d+"),
    re.compile(r"(?m)^Question \d+"),
]
_MIN_PROBLEM_MATCHES = 3  # same reasoning as retag.py's MIN_TAG_CLUSTER_SIZE:
# a weak/sparse match count isn't trusted as real document structure.
_PROBLEM_LABEL_RE = re.compile(r"^\**\s*(?:Practice Problem|Problem|Question)?\s*(\d+)", re.IGNORECASE)


def _problem_label_at(body: str, start: int) -> str:
    first_line = body[start:start + 80].split("\n", 1)[0]
    m = _PROBLEM_LABEL_RE.match(first_line)
    return f"Problem {m.group(1)}" if m else "Problem"


def _detect_problem_boundaries(body: str) -> list[_Span] | None:
    starts = set()
    for pattern in _PROBLEM_BOUNDARY_PATTERNS:
        starts.update(m.start() for m in pattern.finditer(body))
    if len(starts) < _MIN_PROBLEM_MATCHES:
        return None

    ordered = sorted(starts)
    spans = []
    for i, start in enumerate(ordered):
        end = ordered[i + 1] if i + 1 < len(ordered) else len(body)
        spans.append(_Span(
            start=start, end=end, tier="problem_number",
            problem_label=_problem_label_at(body, start),
        ))
    return spans
