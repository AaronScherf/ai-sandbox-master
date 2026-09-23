"""
academic_hub_paths.py
Path-mirroring helpers between academic_notes/ (lightweight: .md scene
files, processed_outputs/, each textbook's final .rag.md) and
academic_resources/ (heavy: PDFs, Excalidraw .svg/.png exports, a
textbook's raw .md/images/JSON sidecars). See
docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md.
Pure string/path manipulation -- no filesystem I/O, no network -- safe to
import at module scope anywhere.
"""
from __future__ import annotations

import os

_NOTES_ROOT_NAME = "academic_notes"
_RESOURCES_ROOT_NAME = "academic_resources"

# A course's textbook folder has been named both of these on disk (see
# indexer/index_search.py's own copy of this tuple). Since each book's
# .rag.md is mirrored into academic_notes/<course>/<textbook folder>/, a
# same-named academic_notes/ category now exists -- notes-PDF discovery
# must still never sweep academic_resources/<course>/textbooks/ into the
# notes-transcription pipeline because of it.
TEXTBOOK_FOLDER_NAMES = ("textbooks", "textbooks-and-papers")


def _swap_root(path: str, old_root: str, new_root: str) -> str:
    had_backslashes = "\\" in path
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    try:
        idx = parts.index(old_root)
    except ValueError:
        raise ValueError(f"path has no {old_root!r} segment: {path!r}")
    parts[idx] = new_root
    result = "/".join(parts)
    return result.replace("/", os.sep) if had_backslashes else result


def to_resources_root(path: str) -> str:
    """Rewrites a path's academic_notes/ segment to academic_resources/,
    preserving everything else (course/category/filename)."""
    return _swap_root(path, _NOTES_ROOT_NAME, _RESOURCES_ROOT_NAME)


def to_notes_root(path: str) -> str:
    """The inverse of to_resources_root."""
    return _swap_root(path, _RESOURCES_ROOT_NAME, _NOTES_ROOT_NAME)


def resolve_output_dir(source_path: str) -> str:
    """Given a source file's path (a PDF, or an Excalidraw scene/image
    file), returns the directory its processed_outputs/ should live
    under: mirrored into academic_notes/ if the source currently lives
    under academic_resources/ (the post-migration case for a PDF), or the
    source's own sibling processed_outputs/ otherwise -- covers both "not
    yet migrated" and "never moves at all" (an Excalidraw .excalidraw.md
    scene file), which is this project's convention from before this
    module existed."""
    normalized = source_path.replace("\\", "/")
    parts = normalized.split("/")
    if _RESOURCES_ROOT_NAME in parts:
        mirrored = to_notes_root(source_path)
        return os.path.join(os.path.dirname(mirrored), "processed_outputs")
    return os.path.join(os.path.dirname(source_path), "processed_outputs")


def textbook_rag_md_path(book_dir: str) -> str:
    """Where a converted textbook's final <Book>.rag.md lives, given its
    processed_outputs/<Book>/ directory. Everything else a book produces
    (raw .md, images/, _metadata.json, _image_descriptions.json) stays in
    academic_resources/ -- only the .rag.md, the one artifact meant for
    reading, is mirrored into academic_notes/ so it syncs to the tablet.
    Falls back to a sibling of the book's own files when book_dir isn't
    under academic_resources/ (tests, ad-hoc directories)."""
    folder_name = os.path.basename(os.path.normpath(book_dir))
    parts = book_dir.replace("\\", "/").split("/")
    target_dir = to_notes_root(book_dir) if _RESOURCES_ROOT_NAME in parts else book_dir
    return os.path.join(target_dir, f"{folder_name}.rag.md")
