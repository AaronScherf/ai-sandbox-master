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
