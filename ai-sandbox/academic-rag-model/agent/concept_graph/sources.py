"""Retrieved passages and the citation keys they are offered under."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from core.agent_tasks.tasks import Passage  # noqa: F401  (re-exported: the very object core defines)

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_CHAPTER = re.compile(r"/chapters/(\d+)_")
_PRIOR_YEAR = re.compile(r"/(20\d\d)_class/(.*)$")
# Earlier years of the course: (words in the path under the year folder, source key). First match wins.
_PRIOR_KINDS = (("proof", "proofs"), ("recitation", "recitation"), ("homework", "hw"), ("/hw", "hw"),
                ("exam", "exam"), ("midterm", "exam"), ("survival", "exam"), ("syllabus", "syllabus"),
                ("pre lecture", "slides-pre"), ("post", "slides"))


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
    text = re.sub(r"\s+", " ", (citation or "").replace("*", "").replace("`", "").replace("#", "")).strip()
    text = re.sub(r"\s*:\s*", " - ", text)  # a colon inside a plain YAML value would make it invalid
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
    prior = _PRIOR_YEAR.search(low)
    if prior:  # an earlier year's class folder, kept apart from this year's material by a year suffix on the key
        rest = "/" + prior.group(2)
        kind = next((key for word, key in _PRIOR_KINDS if word in rest), "other")
        topic = re.sub(r"^\d+\.\s*", "", re.sub(r"_for_circulation.*$", "", stem)).replace("_", " ").strip()
        return (f"{kind}-{prior.group(1)}", topic or stem)
    if "/lecture_notes/" in low:
        m = _DATE.search(stem)
        return ("lecture", m.group(0) if m else stem)
    if "/professor_notes/" in low:
        topic = re.sub(r"^\d+\.\s*", "", stem).replace("_", " ").strip()
        return ("slides", topic or stem)
    if "/problem_sets/" in low:
        return ("hw", stem)
    return ("other", stem)
