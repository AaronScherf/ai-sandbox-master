#!/usr/bin/env python3
"""
toc_repair.py
Last-resort Gemini-assisted repair for a book whose folio tags, PDF
outline, and any existing manual chapter template have all failed
(confirmed live: Hayashi, whose front-matter Table of Contents renders
as a badly merged/misaligned markdown table -- some rows lose their
page number outright -- even though the body's own chapter headings
converted cleanly). Two independent jobs, deliberately kept separate:

1. classify_chapters_via_gemini(): the cheap job, for chapter
   splitting. Sends only a compact heading outline (every markdown
   heading paired with its nearest <!-- page N --> tag -- no prose, no
   PDF) and asks Gemini to classify which headings are real top-level
   chapters versus subsections, returning {title, page} pairs. The
   page number itself is never Gemini's job -- it's already known
   exactly from the existing page tags; Gemini only classifies.
   Feeds chapters_to_review_template()'s output straight into the same
   chapter_titles.txt format split_chapters.py already knows how to
   parse and verify (toc_identify.identify_chapters_from_manual_list) --
   no new matching logic.

2. reconstruct_toc_table_via_gemini(): the pricier job, for repairing
   the book's own Contents section as a human-readable artifact in its
   .rag.md (never the raw .md -- see describe_images.py's own
   convention that the original conversion output is never touched).
   Sends the garbled front-matter text and asks for a clean replacement
   table plus two verbatim markers bounding exactly what to replace.
   splice_repaired_table() then does the actual substitution -- and
   refuses (returns None) unless both markers are found as an exact,
   correctly-ordered substring match in the real text, since guessing
   where to cut a real file is not an acceptable failure mode here.

Pure-Python except for the two *_via_gemini() functions, which are the
only ones that touch the network -- not unit-tested locally, matching
describe_images.py's own describe_image_via_gemini().
"""
from __future__ import annotations

import json
import re

from common.gemini_utils import call_with_retries

_HEADING_RE = re.compile(r"^(#{1,6}\s+.+?)\s*$", re.MULTILINE)
_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


def extract_heading_outline(text: str) -> str:
    """
    Every markdown heading line, paired with the nearest preceding
    <!-- page N --> tag, one per line: "[page N] <heading line>". A
    heading before any page tag at all is marked "[page ?]" rather than
    guessing 0 or 1. This is the ONLY input classify_chapters_via_gemini()
    needs -- no prose, no PDF -- since the page number is already known
    exactly and the only open question is which headings are real
    chapters.
    """
    page_positions = [(m.start(), m.group(1)) for m in _PAGE_MARKER_RE.finditer(text)]
    lines = []
    for m in _HEADING_RE.finditer(text):
        page = "?"
        for pos, num in page_positions:
            if pos > m.start():
                break
            page = num
        lines.append(f"[page {page}] {m.group(1)}")
    return "\n".join(lines)


_OUTLINE_PAGE_RE = re.compile(r"^\[page (\d+|\?)\]")
_DEFAULT_MIN_GAP_PAGES = 20


def find_large_heading_gaps(outline_text: str, min_gap_pages: int = _DEFAULT_MIN_GAP_PAGES) -> list[tuple[int, int]]:
    """
    Scans extract_heading_outline()'s own output for consecutive
    headings whose page numbers jump by more than min_gap_pages,
    ignoring "[page ?]" entries (nothing to compare). Returns
    (start_page, end_page) for each gap found, in document order.

    Confirmed live (Hayashi): a 100+ page span with zero headings at
    all meant three real chapters' own headings never converted --
    classification correctly omitted them rather than guessing, since
    there was nothing to point at, but that silence looks identical to
    "this book just has fewer chapters" unless something flags it. This
    lets split_chapters.py warn a human to check the source PDF for a
    bad scan or missing pages in that range, instead of finding out only
    after noticing chapters are missing.
    """
    pages = []
    for line in outline_text.splitlines():
        m = _OUTLINE_PAGE_RE.match(line)
        if m and m.group(1) != "?":
            pages.append(int(m.group(1)))

    return [(prev, curr) for prev, curr in zip(pages, pages[1:]) if curr - prev > min_gap_pages]


def build_classification_prompt(outline_text: str) -> str:
    return (
        "Below is the complete heading outline of a converted textbook, in document "
        "order: every markdown heading, paired with the physical page it appears on. "
        "Subsections are numbered with a decimal (e.g. \"3.5 Some Topic\"); real "
        "top-level chapters are not (e.g. \"3 Single-Equation GMM\", or a chapter "
        "title with no visible number at all due to a markdown-formatting quirk). "
        "Front matter (Preface, Acknowledgments, Contents, Index, ...) is not a "
        "chapter either.\n\n"
        "Identify every real top-level chapter, in document order, and the page "
        "number already shown next to it.\n\n"
        f"{outline_text}\n\n"
        'Respond with ONLY a JSON array of {"title": "...", "page": N} objects, '
        "one per real chapter, in document order."
    )


def parse_classification_response(response_text: str) -> list[dict]:
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []

    chapters = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title")
        page = entry.get("page")
        if isinstance(title, str) and title.strip() and isinstance(page, int) and not isinstance(page, bool):
            chapters.append({"title": title.strip(), "page": page})
    return chapters


_REVIEW_TEMPLATE_HEADER = """\
# Chapter template for {book}
# AI-generated via Gemini (classified from this book's own heading
# structure) -- please review before trusting, then rerun
# split_chapters.py. Edit or replace any line below as needed; the
# format is unchanged from a manually-filled template:
#
#   Title | PageNumber
#
# PageNumber counts from the very first page of the PDF as page 1.
# Lines starting with '#' are ignored.
"""


def chapters_to_review_template(book: str, chapters: list[dict]) -> str:
    """chapter_titles.txt content for an AI-classified (not yet human-
    reviewed) chapter list -- same parseable format
    toc_identify.parse_manual_chapter_list expects, with a header
    flagging its provenance instead of blank fill-in instructions."""
    lines = [_REVIEW_TEMPLATE_HEADER.format(book=book)]
    for chapter in chapters:
        lines.append(f"{chapter['title']} | {chapter['page']}")
    return "\n".join(lines) + "\n"


def build_table_repair_prompt(front_matter_text: str) -> str:
    return (
        "Below is a textbook's front matter, converted from PDF to markdown. Its "
        "own Table of Contents did not convert cleanly -- rows may be merged, "
        "titles and page numbers may be misaligned or missing. Reconstruct a "
        "clean, correctly-paired replacement for that Contents table (chapters "
        "and their real subsections, each with its own page number, in the same "
        "order as the original), using whatever context in this text lets you "
        "recover the correct pairing.\n\n"
        f"{front_matter_text}\n\n"
        "Respond with ONLY a JSON object with exactly these keys: "
        '"toc_start_marker" (the first line of the garbled Contents block, copied '
        'verbatim from the text above), "toc_end_marker" (the last line of that '
        'block, copied verbatim), and "repaired_table_markdown" (your clean '
        "replacement, as markdown, to be substituted for everything from "
        "toc_start_marker through toc_end_marker inclusive)."
    )


def parse_table_repair_response(response_text: str) -> dict | None:
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None

    keys = ("toc_start_marker", "toc_end_marker", "repaired_table_markdown")
    values = {k: parsed.get(k) for k in keys}
    if not all(isinstance(v, str) and v for v in values.values()):
        return None
    return values


def splice_repaired_table(text: str, repair: dict) -> str | None:
    """
    Replaces the exact span from the first occurrence of
    repair["toc_start_marker"] through the first occurrence of
    repair["toc_end_marker"] *at or after* it, inclusive, with
    repair["repaired_table_markdown"]. Returns None -- never guesses --
    if either marker isn't found verbatim, or the end marker only
    appears before the start marker.
    """
    start_idx = text.find(repair["toc_start_marker"])
    if start_idx == -1:
        return None

    search_from = start_idx + len(repair["toc_start_marker"])
    end_idx = text.find(repair["toc_end_marker"], search_from)
    if end_idx == -1:
        return None

    end_idx_end = end_idx + len(repair["toc_end_marker"])
    return text[:start_idx] + repair["repaired_table_markdown"] + text[end_idx_end:]


def classify_chapters_via_gemini(outline_text: str, client, model: str) -> list[dict]:
    """
    Only function in this module (besides reconstruct_toc_table_via_gemini)
    that touches the network -- not unit-tested locally. Retries via
    call_with_retries: confirmed live (Hayashi) that a ~14-19K char JSON
    generation at temperature 0 can occasionally come back malformed on
    one attempt and clean on the very next, so a parse failure is worth
    one retry, not an immediate give-up.
    """
    def _call():
        response = client.models.generate_content(
            model=model,
            contents=build_classification_prompt(outline_text),
            config={"response_mime_type": "application/json", "temperature": 0},
        )
        chapters = parse_classification_response(response.text)
        if not chapters:
            raise ValueError("Gemini returned no usable chapter classification")
        return chapters

    try:
        return call_with_retries(_call)
    except Exception:
        return []


def reconstruct_toc_table_via_gemini(front_matter_text: str, client, model: str) -> dict | None:
    """Not unit-tested locally -- see classify_chapters_via_gemini, including
    for why a parse failure retries instead of giving up immediately."""
    def _call():
        response = client.models.generate_content(
            model=model,
            contents=build_table_repair_prompt(front_matter_text),
            config={"response_mime_type": "application/json", "temperature": 0},
        )
        repair = parse_table_repair_response(response.text)
        if repair is None:
            raise ValueError("Gemini returned no usable TOC table repair")
        return repair

    try:
        return call_with_retries(_call)
    except Exception:
        return None
