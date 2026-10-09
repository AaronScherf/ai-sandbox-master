"""Read-only freshness checks for explicitly selected indexed Markdown files.

This module is the supported audit surface for tools that need to report
index state without invoking rebuild, creating a model client, or depending on
the index's on-disk JSON layout.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.indexer.chunk_index import load_chunks
from core.indexer.index_card import compute_content_hash, list_courses, load_shard


@dataclass(frozen=True)
class MarkdownIndexTarget:
    """A Markdown file and the path used for its card in this corpus index."""

    file_path: Path
    index_path: str


@dataclass(frozen=True)
class IndexAuditRecord:
    index_path: str
    course: str
    card_status: str
    chunks_status: str
    content_hash: str | None
    evidence: str


@dataclass(frozen=True)
class IndexAuditResult:
    records: tuple[IndexAuditRecord, ...]
    complete: bool
    errors: tuple[str, ...] = ()


def audit_markdown_index(
    corpus_root: str | Path,
    targets: list[MarkdownIndexTarget],
    *,
    max_hash_bytes: int = 8 * 1024 * 1024,
) -> IndexAuditResult:
    """Compare selected Markdown files to card and chunk state, without writes.

    Files over ``max_hash_bytes`` are deliberately not read in full. Their card
    and chunk presence is still reported, but content freshness remains
    ``unverified_large`` until a caller requests a deeper audit.
    """
    root = Path(corpus_root)
    index_dir = root / ".index"
    if not index_dir.is_dir():
        return IndexAuditResult((), False, (f"index directory unavailable: {index_dir}",))

    errors: list[str] = []
    cards_by_path: dict[str, tuple[str, dict]] = {}
    conflicting_paths: set[str] = set()
    chunks_by_course: dict[str, list[dict]] = {}
    unreadable_card_courses: set[str] = set()
    unreadable_chunk_courses: set[str] = set()
    try:
        courses = list_courses(str(root))
    except (OSError, ValueError) as exc:
        return IndexAuditResult((), False, (f"cannot list index courses: {exc}",))

    for course in courses:
        try:
            for card in load_shard(str(root), course):
                # A rebuild can preserve an old card as an orphan when its
                # source identity changes. If the same path now has a current
                # card, only the live card participates in path uniqueness;
                # treating the historical orphan as a conflict makes the
                # read-only health scan report a false duplicate.
                if card.get("orphaned"):
                    continue
                path = card.get("path")
                if isinstance(path, str):
                    normalized = path.replace("\\", "/")
                    previous = cards_by_path.get(normalized)
                    if previous and previous[1].get("file_id") != card.get("file_id"):
                        conflicting_paths.add(normalized)
                        errors.append(f"multiple index cards claim path {normalized!r}")
                    else:
                        cards_by_path[normalized] = (course, card)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            unreadable_card_courses.add(course)
            errors.append(f"cannot read index cards for {course}: {exc}")
        try:
            chunks_by_course[course] = load_chunks(str(root), course)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            unreadable_chunk_courses.add(course)
            errors.append(f"cannot read index chunks for {course}: {exc}")

    records: list[IndexAuditRecord] = []
    for target in targets:
        index_path = target.index_path.replace("\\", "/")
        parts = index_path.split("/")
        course = parts[1] if len(parts) > 2 and parts[0] in {"academic_notes", "academic_resources"} else ""
        if not course:
            records.append(IndexAuditRecord(index_path, "", "unknown", "unknown", None,
                                            "index path is outside a recognized course root"))
            continue
        if index_path in conflicting_paths:
            records.append(IndexAuditRecord(index_path, course, "unreadable", "unknown", None,
                                            "multiple cards claim this path"))
            continue
        if course not in courses:
            errors.append(f"index shard unavailable for eligible course {course!r}")

        card_entry = cards_by_path.get(index_path)
        try:
            size = target.file_path.stat().st_size
            current_hash = (compute_content_hash(str(target.file_path))
                            if size <= max_hash_bytes else None)
        except OSError as exc:
            records.append(IndexAuditRecord(index_path, course, "unreadable", "unknown", None,
                                            f"cannot read Markdown file: {exc}"))
            errors.append(f"cannot read Markdown file {target.file_path}: {exc}")
            continue

        if card_entry is None:
            if course in unreadable_card_courses:
                card_status = "unreadable"
                chunks_status = "unknown"
                evidence = "course card shard is unreadable"
            else:
                card_status = "missing_card"
                chunks_status = "not_applicable"
                evidence = "no index card has this path"
        else:
            card_course, card = card_entry
            stored_hash = card.get("content_hash")
            if card.get("needs_indexing"):
                card_status = "needs_indexing"
            elif card_course != course:
                card_status = "course_mismatch"
            elif current_hash is None:
                card_status = "unverified_large"
            elif not stored_hash:
                card_status = "unverified_legacy"
            elif stored_hash == current_hash:
                card_status = "current"
            else:
                card_status = "stale_card"

            chunks = [chunk for chunk in chunks_by_course.get(card_course, [])
                      if chunk.get("file_id") == card.get("file_id")]
            if card_course in unreadable_chunk_courses:
                chunks_status = "unreadable"
            elif not chunks:
                chunks_status = "missing_chunks"
            elif current_hash is None:
                chunks_status = "unverified_large"
            elif all(chunk.get("content_hash") == current_hash for chunk in chunks):
                chunks_status = "current"
            else:
                chunks_status = "stale_chunks"
            evidence = f"card={card_status}; chunks={chunks_status}"

        records.append(IndexAuditRecord(index_path, course, card_status, chunks_status,
                                        current_hash, evidence))

    return IndexAuditResult(tuple(records), not errors, tuple(errors))
