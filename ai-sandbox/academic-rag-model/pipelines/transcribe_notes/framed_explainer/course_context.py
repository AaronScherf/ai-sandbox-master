# pipelines/transcribe_notes/framed_explainer/course_context.py
"""Bounded, hint-only course context for the explainer agent: course profile,
syllabus lines near the lecture date, professor/TA note headings, and sibling
scenes within a date window. Read-only; no model call."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import date

_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_HEADING = re.compile(r"^#{1,3}\s+(.+?)\s*$")
_TEXT_EXT = (".md", ".txt")


@dataclass
class CourseContext:
    text: str
    version: str
    sources: list[str]
    truncated: bool


def _to_date(m: re.Match) -> date | None:
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def scene_date(scene_path: str) -> date | None:
    m = _DATE.search(os.path.basename(scene_path))
    return _to_date(m) if m else None


def _rel(path: str, hub_root: str) -> str:
    try:
        return os.path.relpath(path, hub_root).replace("\\", "/")
    except ValueError:
        return os.path.basename(path)


def _text_files(folder: str) -> list[str]:
    found: list[str] = []
    for root, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if name.lower().endswith(_TEXT_EXT) and "_pages_" not in name:
                found.append(os.path.join(root, name))
    return sorted(found)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def build_course_context(scene_path: str, hub_root: str, window_days: int = 7,
                         max_tokens: int = 2000) -> CourseContext:
    scene_abs = os.path.abspath(scene_path)
    parts = scene_abs.replace("\\", "/").split("/")
    idx = next((i for i, p in enumerate(parts) if re.fullmatch(r"part_\d+", p)), None)
    course = parts[idx - 1] if idx else "unknown"
    part = parts[idx] if idx is not None else "unknown"
    part_dir = "/".join(parts[: idx + 1]) if idx is not None else os.path.dirname(scene_abs)
    when = scene_date(scene_abs)

    lines = [f"- [{_rel(scene_abs, hub_root)}] Course: {course}; part: {part}"]
    sources: list[str] = []
    digests: list[str] = []

    def use(path: str) -> str:
        text = _read(path)
        rel = _rel(path, hub_root)
        sources.append(rel)
        digests.append(rel + hashlib.sha1(text.replace("\r\n", "\n").encode()).hexdigest())
        return text

    # Syllabus: only dated lines inside the window (undated syllabi add noise).
    for path in _text_files(os.path.join(part_dir, "syllabus")):
        for ln in use(path).splitlines():
            m = _DATE.search(ln)
            d = _to_date(m) if m else None
            if when and d and abs((d - when).days) <= window_days:
                lines.append(f"- [{_rel(path, hub_root)}] Syllabus: {ln.strip()}")

    # Professor and TA notes: headings only.
    for sub in ("professor_notes", "ta_notes"):
        for path in _text_files(os.path.join(part_dir, sub)):
            heads = [m.group(1) for ln in use(path).splitlines()
                     if (m := _HEADING.match(ln))][:12]
            if heads:
                lines.append(f"- [{_rel(path, hub_root)}] {sub.replace('_', ' ')}: "
                             + "; ".join(heads))

    # Sibling scenes inside the date window.
    lec = os.path.join(part_dir, "lecture_notes")
    near: list[str] = []
    if when and os.path.isdir(lec):
        for name in sorted(os.listdir(lec)):
            d = scene_date(name)
            if (name.endswith(".excalidraw.md")
                    and os.path.abspath(os.path.join(lec, name)) != scene_abs
                    and d and abs((d - when).days) <= window_days):
                near.append(name)
    if near:
        lines.append(f"- [{_rel(lec, hub_root)}] Neighbouring scenes "
                     f"(+/-{window_days}d): " + "; ".join(near))

    budget, kept, size, truncated = max_tokens * 4, [], 0, False
    for ln in lines:
        if size + len(ln) + 1 > budget:
            truncated = True
            break
        kept.append(ln)
        size += len(ln) + 1
    version = hashlib.sha1("|".join(sorted(digests)).encode()).hexdigest()
    return CourseContext(text="\n".join(kept), version=version,
                         sources=sources, truncated=truncated)
