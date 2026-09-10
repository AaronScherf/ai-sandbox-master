"""
discovery.py
Finds every source .md file audio_generator should (re)generate audio for,
across the two in-scope content types (spec §5, §1): a course's own notes
(academic_notes/<course>/, all categories -- this already includes
video_notes's synthesized lecture notes, since those live in
academic_notes/<course>/lecture-notes/) and its converted textbooks
(academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/).

Returns one SourceFile per source .md -- not per chapter/section -- so a
future chapter-aware pipeline (spec §9's deferred follow-on) can change what
state.py tracks and how many .mp3s pipeline.py writes per source, without
needing to change discovery itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Mirrors indexer/index_search.py's _TEXTBOOK_FOLDER_NAMES (spec §5) --
# duplicated locally rather than imported, matching this project's existing
# pattern of each subproject owning its own small pieces of hub-layout
# knowledge (e.g. video_notes's own DEFAULT_ACADEMIC_HUB_ROOT) rather than a
# shared hub-layout module.
_TEXTBOOK_FOLDER_NAMES = ("textbooks", "textbooks-and-papers")

CONTENT_TYPES = ("notes", "textbook")


@dataclass
class SourceFile:
    course: str
    content_type: str  # "notes" | "textbook"
    rel_md_path: str  # hub-relative, e.g. "academic_notes/math-camp/ta_notes/processed_outputs/Aug 17 Analysis.md"
    abs_md_path: str
    rel_mp3_path: str  # same directory and basename, .mp3 extension (spec §5)
    abs_mp3_path: str


def _is_real_md_file(name: str) -> bool:
    """True for a real source .md -- excludes the textbook pipeline's
    `.rag.md` sibling variant, audio_generator's own `.narrated.md`
    sibling (spec §3.1, and its per-episode `__partNN.narrated.md` form,
    spec §3.2 -- already covered by the same `.narrated.md` suffix check),
    and the per-episode `__index.md` manifest (spec §3.2) -- each a
    separate, differently-formatted file that happens to also end in
    ".md"."""
    lower = name.lower()
    return lower.endswith(".md") and not lower.endswith((".rag.md", ".narrated.md", "__index.md"))


def _make_source_file(academic_hub_root: str, course: str, content_type: str, abs_md_path: str) -> SourceFile:
    rel_md_path = os.path.relpath(abs_md_path, academic_hub_root).replace(os.sep, "/")
    abs_mp3_path = os.path.splitext(abs_md_path)[0] + ".mp3"
    rel_mp3_path = os.path.splitext(rel_md_path)[0] + ".mp3"
    return SourceFile(
        course=course, content_type=content_type,
        rel_md_path=rel_md_path, abs_md_path=abs_md_path,
        rel_mp3_path=rel_mp3_path, abs_mp3_path=abs_mp3_path,
    )


def _discover_notes(academic_hub_root: str, course: str) -> list:
    course_dir = os.path.join(academic_hub_root, "academic_notes", course)
    if not os.path.isdir(course_dir):
        return []
    sources = []
    for category in sorted(os.listdir(course_dir)):
        category_dir = os.path.join(course_dir, category)
        if not os.path.isdir(category_dir):
            continue
        # A category holds its .md files either directly (plain markdown
        # notes, e.g. "markdown"/"lecture-notes") or under its own
        # processed_outputs/ (OCR'd/converted notes, e.g. "ta_notes") --
        # both are checked, non-recursively (spec §5).
        for scan_dir in (category_dir, os.path.join(category_dir, "processed_outputs")):
            if not os.path.isdir(scan_dir):
                continue
            for name in sorted(os.listdir(scan_dir)):
                candidate = os.path.join(scan_dir, name)
                if _is_real_md_file(name) and os.path.isfile(candidate):
                    sources.append(_make_source_file(academic_hub_root, course, "notes", candidate))
    return sources


def _discover_textbooks(academic_hub_root: str, course: str) -> list:
    sources = []
    for folder_name in _TEXTBOOK_FOLDER_NAMES:
        processed_outputs_dir = os.path.join(
            academic_hub_root, "academic_resources", course, folder_name, "processed_outputs",
        )
        if not os.path.isdir(processed_outputs_dir):
            continue
        for book_folder in sorted(os.listdir(processed_outputs_dir)):
            book_dir = os.path.join(processed_outputs_dir, book_folder)
            if not os.path.isdir(book_dir):
                continue
            md_path = os.path.join(book_dir, f"{book_folder}.md")
            if os.path.isfile(md_path):
                sources.append(_make_source_file(academic_hub_root, course, "textbook", md_path))
    return sources


def discover_source_files(academic_hub_root: str, course: str, content_types: list) -> list:
    for content_type in content_types:
        if content_type not in CONTENT_TYPES:
            raise ValueError(f"Unknown content type {content_type!r}, expected one of {CONTENT_TYPES}")
    sources = []
    if "notes" in content_types:
        sources.extend(_discover_notes(academic_hub_root, course))
    if "textbook" in content_types:
        sources.extend(_discover_textbooks(academic_hub_root, course))
    return sources
