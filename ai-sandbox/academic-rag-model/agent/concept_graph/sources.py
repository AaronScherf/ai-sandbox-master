"""Retrieved passages and the citation keys they are offered under."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_CHAPTER = re.compile(r"/chapters/(\d+)_")


@dataclass(frozen=True)
class Passage:
    id: str
    source: str
    ref: str
    text: str
    path: str = ""

    @property
    def offered(self) -> tuple[str, str]:
        return (self.source, self.ref)


def _stem(path: str) -> str:
    name = PurePosixPath(path).name
    for suffix in (".rag.md", ".excalidraw.rag.md", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


_PAGE = re.compile(r",?\s*(p\. ?[\d\-–]+)$")


def _clean_citation(citation: str, limit: int = 110) -> str:
    """A citation that is safe to copy back exactly: one line, no markdown emphasis, bounded length."""
    text = re.sub(r"\s+", " ", (citation or "").replace("*", "").replace("`", "")).strip()
    page = _PAGE.search(text)
    tail = f", {page.group(1)}" if page else ""
    head = text[: page.start()] if page else text
    if len(head) + len(tail) > limit:
        head = head[: max(limit - len(tail) - 1, 10)].rstrip() + "…"
    return head + tail


def _chapter_ref(path: str, citation: str) -> str:
    m = _CHAPTER.search(path)
    base = f"ch. {int(m.group(1))}" if m else (_stem(path) or "unknown")
    citation = _clean_citation(citation)
    return f"{base}, {citation}" if citation else base


def classify_passage(path: str, citation: str = "") -> tuple[str, str]:
    """Map a retrieved passage's file path (and rendered citation) to a (source, ref) pair.

    The pair is what a card offers and what an agent must cite, so the ref is never empty."""
    p = (path or "").replace("\\", "/")
    low = p.lower()
    if "rubenstein" in low or "rubinstein" in low:
        return ("rubinstein", _chapter_ref(p, citation))
    if "press_microeconomic_theory" in low or "mas-colell" in low:
        return ("mwg", _chapter_ref(p, citation))
    if "ok_real_analysis" in low:
        return ("ok", _chapter_ref(p, citation))
    stem = _stem(p) or "unknown"
    if "/lecture_notes/" in low:
        m = _DATE.search(stem)
        return ("lecture", m.group(0) if m else stem)
    if "/professor_notes/" in low:
        topic = re.sub(r"^\d+\.\s*", "", stem).replace("_", " ").strip()
        return ("slides", topic or stem)
    if "/problem_sets/" in low:
        return ("hw", stem)
    return ("other", stem)
