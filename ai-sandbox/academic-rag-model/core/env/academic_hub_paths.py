"""
academic_hub_paths.py
Path-mirroring helpers between academic_notes/ (lightweight: .md scene
files, processed_outputs/, each textbook's final .rag.md) and
academic_resources/ (heavy: PDFs, Excalidraw .svg/.png exports, a
textbook's raw .md/images/JSON sidecars). See
docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md.
Path parsing is pure; eligibility checks only local directory existence.
No network access is used.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from core.env.frontmatter import parse_frontmatter
from core.env.hub_vocabulary import is_part_name, load_vocabulary, parse_hub_path

_NOTES_ROOT_NAME = "academic_notes"
_RESOURCES_ROOT_NAME = "academic_resources"
_SUBSET_MARKER_FILENAME = ".notes_subset.json"

# A course's textbook folder has been named both of these on disk (see
# indexer/index_search.py's own copy of this tuple). Since each book's
# .rag.md is mirrored into academic_notes/<course>/<textbook folder>/, a
# same-named academic_notes/ category now exists -- notes-PDF discovery
# must still never sweep academic_resources/<course>/textbooks/ into the
# notes-transcription pipeline because of it.
# The names now live in the hub vocabulary (academic-hub/hub_config.json, `textbook_folders`).
def textbook_folder_names() -> tuple[str, ...]:
    return load_vocabulary().textbook_folders


def is_textbook_folder(name: str) -> bool:
    return name.casefold() in textbook_folder_names()


def course_part_category(path: str) -> tuple[str, str | None, str | None] | None:
    """Parse a file path below either hub root: (course, first group layer, category).

    Delegates to the hub vocabulary (core.env.hub_vocabulary.parse_hub_path); a path with no known
    category keeps the legacy part_N parse."""
    parsed = parse_hub_path(path)
    if parsed is None:
        return None
    return parsed.course, parsed.groups[0] if parsed.groups else None, parsed.category


def course_output_dir(hub_root: str | Path, course: str, category: str, part: str | None = None) -> Path:
    """Resolve an output category, requiring a part when the layout is ambiguous."""
    course_dir = Path(hub_root) / "academic_notes" / course
    parts = sorted(p.name for p in course_dir.iterdir() if p.is_dir() and is_part_name(p.name)) if course_dir.is_dir() else []
    if part is not None:
        if not is_part_name(part):
            raise ValueError(f"invalid part {part!r}; expected part_N")
        if parts and part not in parts:
            raise ValueError(f"part {part!r} does not exist for {course}")
        if not parts:
            raise ValueError(f"course {course!r} has no part folders")
        return course_dir / part / category
    if len(parts) > 1:
        raise ValueError(f"course {course!r} has multiple parts; specify --part")
    return course_dir / parts[0] / category if parts else course_dir / category


def eligible_resource_note_pdf(path: str, notes_course_dir: str, marked: bool = False) -> bool:
    parsed = course_part_category(path)
    if parsed is None or parsed[2] is None:
        return False
    parts = path.replace("\\", "/").split("/")
    root_at = parts.index(_RESOURCES_ROOT_NAME)
    if any(p.startswith(".") or p == "processed_outputs" or is_textbook_folder(p)
           for p in parts[root_at + 2:-1]):
        return False
    hub_path = parse_hub_path(path)
    mirror = os.path.join(notes_course_dir, *hub_path.groups, hub_path.category)
    return marked or os.path.isdir(mirror)


def has_authored_markdown_peer(pdf_path: str) -> bool:
    """A same-stem authored Markdown source supersedes its PDF export."""
    stem, _ = os.path.splitext(pdf_path)
    candidates = [stem + ".md"]
    try:
        mirrored = to_notes_root(pdf_path)
    except ValueError:
        pass
    else:
        if mirrored != pdf_path:
            candidates.append(os.path.splitext(mirrored)[0] + ".md")
    for path in candidates:
        if "processed_outputs" in Path(path).parts or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8-sig") as source:
            prefix = source.read(4096)
        if not prefix.strip():
            continue
        fields, _ = parse_frontmatter(prefix)
        if fields.get("authored_source", "").lower() == "true" or (
            "source_pdf" not in fields and "source_excalidraw" not in fields
        ):
            return True
    return False


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
