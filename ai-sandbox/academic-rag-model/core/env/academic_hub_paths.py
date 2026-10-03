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

import json
import os

_NOTES_ROOT_NAME = "academic_notes"
_RESOURCES_ROOT_NAME = "academic_resources"
_SUBSET_MARKER_FILENAME = ".notes_subset.json"

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


def read_subset_marker(dir_path: str) -> dict | None:
    """Reads this directory's prior-offering subset marker, if any.
    Returns None for a missing file (not marked) or a malformed one
    (logged, treated as not marked) -- never raises, so one bad marker
    can't take down a caller scanning many directories."""
    marker_path = os.path.join(dir_path, _SUBSET_MARKER_FILENAME)
    if not os.path.isfile(marker_path):
        return None
    try:
        with open(marker_path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as err:
        print(f"WARNING: malformed subset marker, ignoring: {marker_path} ({err})")
        return None
    if not isinstance(data, dict):
        print(
            f"WARNING: malformed subset marker, ignoring: {marker_path} "
            f"(expected a JSON object, got {type(data).__name__})"
        )
        return None
    return data


def find_containing_offering_label(path: str) -> str | None:
    """The label of the subset marker governing `path`, or None if path
    isn't under academic_resources/ at all, or no ancestor up to its
    course directory carries a valid marker. Checks ancestors from the
    course directory downward to path's own parent (top-down,
    first-match-wins) -- the same order find_subset_roots() walks in
    (route_notes_transcribe.py), so this always agrees with which
    directory that function would have returned as the subset root
    governing this exact file."""
    had_backslashes = "\\" in path
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    try:
        idx = parts.index(_RESOURCES_ROOT_NAME)
    except ValueError:
        return None
    course_depth = idx + 2
    if len(parts) <= course_depth:
        return None
    for depth in range(course_depth, len(parts)):
        candidate = "/".join(parts[:depth])
        if had_backslashes:
            candidate = candidate.replace("/", os.sep)
        marker = read_subset_marker(candidate)
        if marker is not None:
            label = marker.get("label")
            return str(label) if label is not None else None
    return None
