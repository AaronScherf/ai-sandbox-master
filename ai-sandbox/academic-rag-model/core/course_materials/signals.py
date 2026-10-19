"""Evidence about one converted file, as weighted votes for its role and format. `decide` adds them up.

No signal is trusted alone except where the evidence is unambiguous (an Excalidraw source, a converted textbook's
chapters/ layout); folder and file names are only weak votes, and page orientation names a format, never who made
the file. No model calls."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from core.env.academic_hub_paths import TEXTBOOK_FOLDER_NAMES

from .model import AUTHORITY

DECISIVE, STRONG, MEDIUM, WEAK = 10, 3, 2, 1
FLAG_BELOW, FLAG_MARGIN = 3, 2

logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Vote:
    signal: str
    field: str  # "role", "format", or "authority" (vouches for a group without naming a role)
    value: str
    weight: int  # 0 = evidence only


@dataclass
class Facts:
    path: str  # hub-relative, academic_notes/<course>/...
    frontmatter: dict
    body: str
    card_doc_type: str | None = None
    pdf_shape: str | None = None  # landscape, portrait, unavailable; None when no source PDF is named


@dataclass
class Decision:
    role: str
    format: str
    confidence: float
    flagged: bool
    votes: list[Vote] = field(default_factory=list)


def pdf_shape(pdf_path: Path, pages: int = 3) -> str:
    """Majority page orientation of the first pages, rotation applied."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        land = port = 0
        for page in reader.pages[:pages]:
            w, h = float(page.mediabox.width), float(page.mediabox.height)
            if int(page.get("/Rotate", 0) or 0) % 180 == 90:
                w, h = h, w
            if w > h * 1.1:
                land += 1
            else:
                port += 1
    except Exception:  # pypdf raises many types for damaged files; a missing shape only costs this signal
        return "unavailable"
    if land + port == 0:
        return "unavailable"
    return "landscape" if land > port else "portrait"


def excalidraw_signal(f: Facts) -> list[Vote]:
    if "source_excalidraw" in f.frontmatter:
        return [Vote("excalidraw source", "format", "excalidraw", DECISIVE),
                Vote("excalidraw source", "role", "student_notes", DECISIVE)]
    if ".excalidraw." in PurePosixPath(f.path).name:
        return [Vote("excalidraw file name", "format", "excalidraw", MEDIUM),
                Vote("excalidraw file name", "role", "student_notes", MEDIUM)]
    return []


_CHAPTER_FILE = re.compile(r"^\d+_")


def textbook_signal(f: Facts) -> list[Vote]:
    parts = f.path.split("/")
    chapter = len(parts) >= 2 and parts[-2] == "chapters" and bool(_CHAPTER_FILE.match(parts[-1]))
    if f.card_doc_type == "textbook" or chapter:
        return [Vote("textbook layout", "format", "chapter", DECISIVE), Vote("textbook layout", "role", "textbook", DECISIVE)]
    if any(p in TEXTBOOK_FOLDER_NAMES for p in parts[:-1]):
        return [Vote("textbook folder", "format", "chapter", STRONG), Vote("textbook folder", "role", "textbook", STRONG)]
    return []


def pdf_signal(f: Facts) -> list[Vote]:
    if f.pdf_shape == "landscape":
        # A convention of the courses seen so far, not a rule: it hints at a slide deck and says nothing about who made it.
        return [Vote("pdf landscape", "format", "slides", MEDIUM)]
    if f.pdf_shape in ("portrait", "unavailable"):
        return [Vote(f"pdf {f.pdf_shape}", "format", f.pdf_shape, 0)]
    return []


# The indexer's model picks one of only four labels, and files any class handout it cannot place (the professor's
# decks included) under ta_notes; so that label vouches for class material, not for who wrote it.
_CARD_VOTES = {"problem_set": ("role", "problem_set"), "ta_notes": ("authority", "class"),
               "syllabus": ("role", "syllabus"), "handwritten_notes": ("format", "handwritten"),
               "lecture_notes": ("role", "student_notes"), "excalidraw_notes": ("role", "student_notes")}


def card_signal(f: Facts) -> list[Vote]:
    hit = _CARD_VOTES.get(f.card_doc_type or "")
    return [Vote(f"index card {f.card_doc_type}", hit[0], hit[1], STRONG)] if hit else []


_CONTENT = (
    ("syllabus", re.compile(r"(?i)\b(office hours|grading|course (?:description|objectives|outline)|"
                            r"learning (?:outcomes|objectives)|required (?:texts?|readings?))\b"), 2),
    ("problem_set", re.compile(r"(?im)^\W*(?:problem|question|exercise)\s*\d+"), 2),
    ("exam", re.compile(r"(?i)\b(?:midterm|final exam|exam)\b"), 2),
    ("recitation", re.compile(r"(?i)\b(?:recitation|ta session|section notes)\b"), 1),
)


def content_signal(f: Facts, head: int = 6000) -> list[Vote]:
    text = f.body[:head]
    return [Vote(f"content: {role} wording", "role", role, MEDIUM)
            for role, pattern, need in _CONTENT if len(pattern.findall(text)) >= need]


_PATH_WORDS = {
    "professor": ("role", "instructor"), "prof": ("role", "instructor"), "instructor": ("role", "instructor"),
    "proof": ("role", "instructor"), "proofs": ("role", "instructor"),
    "slides": ("format", "slides"), "slide": ("format", "slides"), "handwritten": ("format", "handwritten"),
    "ta": ("role", "recitation"), "recitation": ("role", "recitation"), "recitations": ("role", "recitation"),
    "hw": ("role", "problem_set"), "homework": ("role", "problem_set"), "homeworks": ("role", "problem_set"),
    "problem": ("role", "problem_set"), "problems": ("role", "problem_set"), "pset": ("role", "problem_set"),
    "solution": ("role", "problem_set"), "solutions": ("role", "problem_set"),
    "exam": ("role", "exam"), "exams": ("role", "exam"), "midterm": ("role", "exam"),
    "syllabus": ("role", "syllabus"),
}
_WORD = re.compile(r"[a-z]+")


def path_signal(f: Facts) -> list[Vote]:
    below_course = f.path.split("/", 2)[-1].lower()
    words = sorted(set(_WORD.findall(below_course)) & set(_PATH_WORDS))
    return [Vote(f"path word '{w}'", *_PATH_WORDS[w], WEAK) for w in words]


_HEADING_LINE = re.compile(r"(?m)^#{1,3}\s")


def format_fallback(f: Facts) -> list[Vote]:
    """When nothing names a format: a portrait scan with few headings and short lines reads as handwriting."""
    if f.pdf_shape == "portrait":
        lines = sorted(len(ln) for ln in f.body.splitlines() if ln.strip())
        pages = max(f.body.count("<!-- page "), 1)
        if lines and lines[len(lines) // 2] < 60 and len(_HEADING_LINE.findall(f.body)) < pages / 2:
            return [Vote("portrait scan, few headings", "format", "handwritten", WEAK)]
    return [Vote("default", "format", "typeset", WEAK)]


SIGNALS = (excalidraw_signal, textbook_signal, pdf_signal, card_signal, content_signal, path_signal)


def _tally(votes: list[Vote], field_name: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for v in votes:
        if v.field == field_name and v.weight > 0:
            scores[v.value] = scores.get(v.value, 0) + v.weight
    return scores


def _best(scores: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def decide(f: Facts) -> Decision:
    """Authority first (class, reference, student), then the role inside it. Only the authority is flagged when unsure:
    mixing up two kinds of class material costs little, mixing up class material and a student's notes does not."""
    votes = [v for signal in SIGNALS for v in signal(f)]
    if not any(v.field == "format" and v.weight > 0 for v in votes):
        votes += format_fallback(f)
    formats = _tally(votes, "format")
    fmt = _best(formats)[0][0] if formats else "typeset"
    roles = _tally(votes, "role")
    groups: dict[str, int] = {}
    for role, score in roles.items():
        groups[AUTHORITY[role]] = groups.get(AUTHORITY[role], 0) + score
    for group_name, score in _tally(votes, "authority").items():
        groups[group_name] = groups.get(group_name, 0) + score
    if fmt == "slides":  # a slide deck is class material rather than a student's notes or a book, whoever presented it
        groups["class"] = groups.get("class", 0) + formats["slides"]
    ranked = _best(groups)
    if not ranked:
        return Decision(role="other", format=fmt, confidence=0.0, flagged=True, votes=votes)
    group, top = ranked[0]
    runner = ranked[1][1] if len(ranked) > 1 else 0
    inside = _best({r: s for r, s in roles.items() if AUTHORITY[r] == group})
    role = inside[0][0] if inside else "instructor"  # only `class` is reachable without role votes (via slides)
    margin = top - runner
    return Decision(role=role, format=fmt, confidence=float(margin),
                    flagged=top < FLAG_BELOW or margin < FLAG_MARGIN, votes=votes)
