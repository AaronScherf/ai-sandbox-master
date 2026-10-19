"""Retrieved passages and the citation keys they are offered under.

A passage's key comes from what its file is (core.course_materials): a textbook by its book key, instructor slides
or notes, the student's lecture notes, and so on, with an earlier offering's label as a suffix."""
from __future__ import annotations

import re

from core.agent_tasks.tasks import Passage  # noqa: F401  (re-exported: the very object core defines)
from core.course_materials import Catalog, Material, classify_path, date_from_stem, normalize

_CHAPTER = re.compile(r"/chapters/(\d+)_")
_PAGE = re.compile(r",?\s*(p\. ?[\d\-–]+)$")
_ROLE_KEYS = {"student_notes": "lecture", "recitation": "recitation", "problem_set": "hw", "exam": "exam",
              "syllabus": "syllabus"}


def _clean_citation(citation: str, limit: int = 110) -> str:
    """A citation that is safe to copy back exactly: one line, no markdown emphasis, bounded length."""
    text = re.sub(r"\s+", " ", (citation or "").replace("*", "").replace("`", "").replace("#", "")).strip()
    text = re.sub(r"\s*:\s*", " - ", text)  # a colon inside a plain YAML value would make it invalid
    page = _PAGE.search(text)
    tail = f", {page.group(1)}" if page else ""
    head = text[: page.start()] if page else text
    if len(head) + len(tail) > limit:
        head = head[: max(limit - len(tail) - 1, 10)].rstrip() + "…"
    return head + tail


def _chapter_ref(path: str, stem: str, citation: str) -> str:
    m = _CHAPTER.search(path)
    base = f"ch. {int(m.group(1))}" if m else (stem or "unknown")
    citation = _clean_citation(citation)
    return f"{base}, {citation}" if citation else base


def _deck_title(stem: str) -> str:
    return re.sub(r"^\d+\.\s*", "", stem).replace("_", " ").strip() or stem


def source_key(m: Material) -> str:
    if m.role == "textbook":
        return m.book or "book"
    if m.role == "instructor":
        key = "notes" if m.format == "handwritten" else "slides"
    else:
        key = _ROLE_KEYS.get(m.role, "other")
    return f"{key}-{m.offering}" if m.offering else key


def classify_passage(path: str, citation: str = "", catalog: Catalog | None = None) -> tuple[str, str]:
    """Map a retrieved passage's file path (and rendered citation) to the (source, ref) pair a card offers.

    The ref is always built from `path` itself (a book's front matter found through its folder still cites its own
    file); the catalog only says what kind of file it is. The ref is never empty."""
    m = (catalog.lookup(path) if catalog is not None else None) or classify_path(path)
    p = normalize(path) or (path or "").replace("\\", "/")
    stem = Material(path=p).stem
    date = date_from_stem(stem)
    if m.role == "textbook":
        ref = _chapter_ref(p, stem, citation)
    elif m.role == "student_notes":
        ref = date or stem
    elif m.role == "instructor":
        ref = (date or _deck_title(stem)) if m.format == "handwritten" else _deck_title(stem)
    elif m.role == "recitation":
        ref = _deck_title(stem) or date or stem
    else:
        ref = stem
    return source_key(m), ref or "unknown"
