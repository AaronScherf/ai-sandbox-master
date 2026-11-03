"""
discovery.py
Finds every source .md file audio_generator should (re)generate audio for,
across the two in-scope content types (spec §5, §1): a course's own notes
(academic_notes/<course>/, all categories -- this already includes
video_notes's synthesized lecture notes, since those live in
academic_notes/<course>/lecture_notes/) and its converted textbooks
(academic_resources/<course>/{textbooks,textbooks-and-papers}/processed_outputs/).

Returns one SourceFile per source .md -- not per chapter/section -- so a
future chapter-aware pipeline (spec §9's deferred follow-on) can change what
state.py tracks and how many .mp3s pipeline.py writes per source, without
needing to change discovery itself.

Each SourceFile's mp3 path (2026-09-22) is computed here, once, so both
pipeline.py's textbook and episode-splitting paths get it for free rather
than each re-deriving it: for "notes" content, mirrored into
academic_resources/ (heavy derived audio doesn't belong in the
git/tablet-synced academic_notes/ tree); for "textbook" content, a plain
sibling of the source .md, since that .md already lives in
academic_resources/ and there's nothing to mirror.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from core.env.academic_hub_paths import is_textbook_folder, textbook_folder_names, to_resources_root
from core.env.hub_vocabulary import parse_hub_path

# Textbook folder names and the part_N pattern come from the hub vocabulary
# (academic-hub/hub_config.json), shared with the indexer.

CONTENT_TYPES = ("notes", "textbook")


@dataclass
class SourceFile:
    course: str
    content_type: str  # "notes" | "textbook"
    rel_md_path: str  # hub-relative, e.g. "academic_notes/math-camp/ta_notes/processed_outputs/Aug 17 Analysis.md"
    abs_md_path: str
    rel_mp3_path: str  # same basename, .mp3 extension -- same directory for
                        # "textbook" (already under academic_resources/), the
                        # mirrored academic_resources/ path for "notes"
                        # (2026-09-22: audio is heavy derived content, kept
                        # out of the git/tablet-synced academic_notes/ tree
                        # the same way PDFs/svgs/docx/pptx are)
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
    if content_type == "notes":
        # notes .md lives in academic_notes/ (kept lightweight for
        # git/tablet sync); its .mp3 is heavy derived audio and belongs in
        # the mirrored academic_resources/ location instead, same
        # convention common/academic_hub_paths.py already uses for
        # PDFs/svgs/docx/pptx.
        abs_mp3_path = os.path.splitext(to_resources_root(abs_md_path))[0] + ".mp3"
    else:
        # textbook .md already lives in academic_resources/ -- sibling is
        # already the right place; to_resources_root() would raise on a
        # path with no academic_notes/ segment to mirror from.
        abs_mp3_path = os.path.splitext(abs_md_path)[0] + ".mp3"
    rel_mp3_path = os.path.relpath(abs_mp3_path, academic_hub_root).replace(os.sep, "/")
    return SourceFile(
        course=course, content_type=content_type,
        rel_md_path=rel_md_path, abs_md_path=abs_md_path,
        rel_mp3_path=rel_mp3_path, abs_mp3_path=abs_mp3_path,
    )


def _walk_layout_dirs(course_dir: str):
    """Yield (parent_depth, parent_rel, name, path) for every directory below the course, depth-first,
    skipping hidden folders and processed_outputs. Textbook folders are yielded but not descended into."""
    if not os.path.isdir(course_dir):
        return
    for dirpath, dirnames, _ in os.walk(course_dir):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "processed_outputs")
        rel = os.path.relpath(dirpath, course_dir)
        parent_rel = "" if rel == "." else rel.replace(os.sep, "/")
        depth = 0 if not parent_rel else parent_rel.count("/") + 1
        for name in list(dirnames):
            yield depth, parent_rel, name, os.path.join(dirpath, name)
            if is_textbook_folder(name):
                dirnames.remove(name)


def _discover_notes(academic_hub_root: str, course: str) -> list:
    """A category directory is one the hub vocabulary names the category of its own contents (or, with no
    known category, the legacy first folder), at any group-layer depth."""
    course_dir = os.path.join(academic_hub_root, "academic_notes", course)
    category_dirs = []
    for depth, parent_rel, name, path in _walk_layout_dirs(course_dir):
        if is_textbook_folder(name):
            continue
        parsed = parse_hub_path(os.path.join(path, "placeholder.md"))
        if parsed is not None and parsed.folder == name:
            category_dirs.append((depth, parent_rel, name, path))
    sources = []
    for _, _, _, category_dir in sorted(category_dirs, key=lambda item: item[:3]):
        for scan_dir in (category_dir, os.path.join(category_dir, "processed_outputs")):
            if not os.path.isdir(scan_dir):
                continue
            for name in sorted(os.listdir(scan_dir)):
                candidate = os.path.join(scan_dir, name)
                if not name.startswith(".") and _is_real_md_file(name) and os.path.isfile(candidate):
                    sources.append(_make_source_file(academic_hub_root, course, "notes", candidate))
    return sources


def _discover_textbooks(academic_hub_root: str, course: str) -> list:
    sources = []
    course_dir = os.path.join(academic_hub_root, "academic_resources", course)
    order = textbook_folder_names()
    found = sorted(((depth, parent_rel, order.index(name.casefold()), path)
                    for depth, parent_rel, name, path in _walk_layout_dirs(course_dir) if is_textbook_folder(name)),
                   key=lambda item: item[:3])
    for _, _, _, textbook_dir in found:
        processed_outputs_dir = os.path.join(textbook_dir, "processed_outputs")
        if not os.path.isdir(processed_outputs_dir):
            continue
        for book_folder in sorted(os.listdir(processed_outputs_dir)):
            book_dir = os.path.join(processed_outputs_dir, book_folder)
            if book_folder.startswith(".") or not os.path.isdir(book_dir):
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
