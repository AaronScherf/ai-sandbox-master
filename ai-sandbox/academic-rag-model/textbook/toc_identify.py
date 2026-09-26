"""
toc_identify.py
Identifies chapter boundaries in an already-converted, already-merged
textbook .rag.md by locating, for each chapter in its own printed table
of contents (chapter_index.parse_printed_toc), the first <!-- folio N -->
tag in the body whose page reaches that chapter's printed folio number.

Splits on folio position rather than a matching markdown heading,
deliberately: a real-world book (Rudin) confirmed live that Marker
doesn't reliably emit a "#" heading for every chapter, even though
every page's folio tag is always present -- heading-text matching left
most real chapters unmatchable, and once matched a decoy heading (an
appended solutions manual's own identically-titled chapter, hundreds of
pages later) for a silently wrong split. Folio position sidesteps both
problems: it needs no heading at all, and forward-only search for the
first tag reaching each target can't jump past the real chapter into
unrelated later content with a coincidentally higher folio number,
since the real chapter's own tag is reached first.

Deliberately conservative: identify_chapters() reports confident=True
only when every TOC chapter's folio number is reached by some body
folio tag, each one no earlier in the document than the previous
chapter's. Anything less (no parseable TOC, no folio tags in the body,
a chapter's folio page never reached) is reported via `reason`, not
guessed at -- split_chapters.py never has to choose between a good
split and a silently wrong one. See docs/superpowers/specs/2026-09-23-
textbook-chapter-split-design.md.

identify_chapters_via_outline() is a separate, independent fallback for
books whose folio tags AND printed TOC are both unusable (confirmed
live: Hansen) -- it reads numbered chapter titles directly off the
source PDF's own outline/bookmarks instead, and splits on <!-- page N
--> tags. Same conservative contract: confident only when every
chapter-shaped outline entry is reached, in order.

identify_chapters_from_manual_list() is the last-resort fallback for a
book with neither usable folio tags nor a usable PDF outline (confirmed
live: Simon has zero outline entries at all; Press and Rubenstein's
PDFs have none either). A human fills in a simple "Title | PageNumber"
template (generate_chapter_template/parse_manual_chapter_list) by eye
from the PDF's own page counter; matched against <!-- page N --> tags
with the same conservative contract as every other path here.

Pure-Python, no filesystem/network dependency -- same testing posture
as chapter_index.py, which this module builds on. identify_chapters()
and identify_chapters_from_manual_list() need no PDF at all;
identify_chapters_via_outline() takes an already-opened
pypdf.PdfReader (the caller does the file I/O), so this module itself
still never touches the filesystem or network directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from textbook.chapter_index import ChapterEntry, get_all_outline_entries, parse_printed_toc

_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")
_FOLIO_MARKER_RE = re.compile(r"<!-- folio (\d+) -->")
_OUTLINE_CHAPTER_NUM_RE = re.compile(r"^(\d+)\.?\s+(\S.*)$")
_OUTLINE_CHAPTER_WORD_RE = re.compile(r"^chapter\s+\w+\b\s*[.:\-–—]?\s*(\S.*)$", re.IGNORECASE)
_TOC_SEARCH_PAGES = 50
_MIN_TRUNCATABLE_CHARS = 8000


@dataclass
class ChapterMatch:
    chapter: ChapterEntry
    offset: int  # character offset of the matched folio tag's line start
    matched_at: int  # the body's own folio number at that position


@dataclass
class TocIdentification:
    toc_chapters: list[ChapterEntry]
    matches: list[ChapterMatch] = field(default_factory=list)
    confident: bool = False
    reason: str = ""


def front_matter_window(text: str, max_page: int = _TOC_SEARCH_PAGES) -> str:
    """
    Restricts TOC parsing to roughly the first `max_page` physical pages
    of the document (using its own <!-- page N --> tags) -- a book's
    real printed TOC always lives in its front matter, and scanning the
    whole document risks picking up a look-alike table anywhere later
    (confirmed live: Rudin's rag.md bundles an appended solutions
    manual with its own "Contents" page hundreds of pages in, which
    otherwise gets parsed as more, unmatchable chapters). Falls back to
    the first quarter of the text if there are no page markers at all
    and the document is long enough for that to be a meaningful front
    matter cutoff, rather than risk truncating a short/untagged
    document's own real TOC.
    """
    markers = list(_PAGE_MARKER_RE.finditer(text))
    if not markers:
        if len(text) < _MIN_TRUNCATABLE_CHARS:
            return text
        return text[: len(text) // 4]
    for m in markers:
        if int(m.group(1)) > max_page:
            return text[: m.start()]
    return text


def _dedupe_by_increasing(chapters: list[ChapterEntry], attr: str) -> list[ChapterEntry]:
    """
    Keeps only entries whose getattr(chapter, attr) strictly increases
    over the last kept entry, dropping the rest -- a duplicate table row
    (the same chapter's title split across two rows, both carrying the
    same folio) and a stray false-positive entry (a numbered subsection
    inside real chapter-1 body text, caught by the front-matter window,
    whose "folio" doesn't advance past chapters already parsed) both
    confirmed live in Cameron's rag.md. Entries with no value for `attr`
    at all are dropped too -- nothing to position them against. Shared
    by identify_chapters (folio_page) and identify_chapters_via_outline
    (physical_page): same duplicate/stray-entry risk either way.
    """
    kept: list[ChapterEntry] = []
    last_value = None
    for chapter in chapters:
        value = getattr(chapter, attr)
        if value is None:
            continue
        if last_value is not None and value <= last_value:
            continue
        kept.append(chapter)
        last_value = value
    return kept


def _dedupe_by_increasing_folio(chapters: list[ChapterEntry]) -> list[ChapterEntry]:
    return _dedupe_by_increasing(chapters, "folio_page")


def _chapter_shaped_outline_entries(entries: list[ChapterEntry]) -> list[ChapterEntry]:
    """
    Filters PDF outline entries down to ones shaped like a real, numbered
    top-level chapter ("19. Nonparametric Regression"), dropping decimal-
    numbered subsections ("19.1 Some Topic" -- no whitespace immediately
    after the chapter number, so the pattern doesn't match) and
    non-chapter entries (Part dividers, "Preface", "Cover", ...).
    Deliberately doesn't touch the book's own printed TOC at all --
    confirmed live (Hansen): that TOC parsed to just 1 spurious entry
    (a separate OCR/table-format failure) even though the PDF's own
    outline had a clean, complete chapter list.
    """
    chapters = []
    for entry in entries:
        if entry.physical_page is None:
            continue
        title = entry.title.strip().rstrip("\x00").strip()
        m = _OUTLINE_CHAPTER_NUM_RE.match(title)
        clean_title = m.group(2).strip() if m else None
        if clean_title is None:
            m = _OUTLINE_CHAPTER_WORD_RE.match(title)
            clean_title = m.group(1).strip() if m else None
        if not clean_title:
            continue
        chapters.append(ChapterEntry(title=clean_title, physical_page=entry.physical_page))
    return chapters


def _folio_positions(text: str) -> list[tuple[int, int]]:
    """Every <!-- folio N --> tag's (line_start_offset, folio_number), in
    document order. Uses the containing line's start (not the tag's own
    match start) so a split at this offset never separates a folio tag
    from a page tag sharing its line."""
    return _tag_positions(_FOLIO_MARKER_RE, text)


def _page_positions(text: str) -> list[tuple[int, int]]:
    """Every <!-- page N --> tag's (line_start_offset, page_number), in
    document order. convert_textbook.py always emits these, regardless
    of whether folio-anchoring succeeded for the book."""
    return _tag_positions(_PAGE_MARKER_RE, text)


def _tag_positions(pattern: re.Pattern, text: str) -> list[tuple[int, int]]:
    positions = []
    for m in pattern.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        positions.append((line_start, int(m.group(1))))
    return positions


def _match_forward(
    chapters: list[ChapterEntry], target_attr: str, positions: list[tuple[int, int]], noun: str
) -> tuple[list[ChapterMatch], str]:
    """
    For each chapter (in order), finds the first position whose value
    reaches getattr(chapter, target_attr), searching forward from the
    previous chapter's own match -- so a match can never jump backward or
    reuse an earlier position. Returns (matches, "") on full success, or
    (partial_matches, reason) the moment any chapter can't be placed.
    Shared by identify_chapters (folio tags) and
    identify_chapters_via_outline (page tags): same conservative
    "advance monotonically or give up" contract either way.
    """
    matches: list[ChapterMatch] = []
    search_from = 0
    for chapter in chapters:
        target = getattr(chapter, target_attr)
        found = None
        if target is not None:
            for idx in range(search_from, len(positions)):
                offset, value = positions[idx]
                if value >= target:
                    found = (idx, offset, value)
                    break
        if found is None:
            return matches, f"chapter {chapter.title!r} ({noun} {target}) is never reached by the body's {noun} tags"
        idx, offset, value = found
        matches.append(ChapterMatch(chapter=chapter, offset=offset, matched_at=value))
        search_from = idx + 1
    return matches, ""


def identify_chapters(text: str) -> TocIdentification:
    toc_chapters = _dedupe_by_increasing_folio(parse_printed_toc(front_matter_window(text)))
    if not toc_chapters:
        return TocIdentification(toc_chapters=[], reason="no parseable table of contents found")

    folio_positions = _folio_positions(text)
    if not folio_positions:
        return TocIdentification(
            toc_chapters=toc_chapters,
            reason="no folio tags found in the body to position chapters against",
        )

    matches, reason = _match_forward(toc_chapters, "folio_page", folio_positions, "folio")
    return TocIdentification(toc_chapters=toc_chapters, matches=matches, confident=not reason, reason=reason)


def identify_chapters_via_outline(text: str, reader) -> TocIdentification:
    """
    Fallback for books whose folio tags are missing or insufficient
    (confirmed live: Hansen's front-matter OCR never confidently
    anchored a folio offset during conversion, so no folio tags were
    ever written for the whole 1081-page book) -- and deliberately
    doesn't depend on the book's own printed TOC either (also confirmed
    live: Hansen's TOC parsed to just 1 usable entry, a separate OCR/
    table-format failure independent of the folio-anchoring one).
    Instead, reads numbered chapter-shaped titles directly off the
    source PDF's own embedded outline/bookmarks
    (_chapter_shaped_outline_entries), then splits on <!-- page N -->
    tags, which convert_textbook.py always emits regardless of
    folio-anchoring success. `reader` is an already-opened
    pypdf.PdfReader for the book's own source PDF -- this function does
    no file I/O itself.
    """
    outline_entries = get_all_outline_entries(reader)
    if not outline_entries:
        return TocIdentification(toc_chapters=[], reason="source PDF has no embedded outline/bookmarks")

    chapters = _dedupe_by_increasing(_chapter_shaped_outline_entries(outline_entries), "physical_page")
    if not chapters:
        return TocIdentification(
            toc_chapters=[],
            reason="no numbered chapter-shaped entries found in the PDF outline",
        )

    page_positions = _page_positions(text)
    if not page_positions:
        return TocIdentification(
            toc_chapters=chapters,
            reason="no page tags found in the body to position chapters against",
        )

    matches, reason = _match_forward(chapters, "physical_page", page_positions, "page")
    return TocIdentification(toc_chapters=chapters, matches=matches, confident=not reason, reason=reason)


_MANUAL_LINE_RE = re.compile(r"^(.*?)\s*\|\s*(\d+)\s*$")

_CHAPTER_TEMPLATE = """\
# Chapter template for {book}
# Neither this book's folio tags nor its PDF outline could be read
# automatically -- fill in one chapter per line below, then rerun
# split_chapters.py:
#
#   Title | PageNumber
#
# PageNumber counts from the very first page of the PDF as page 1 --
# the same number your PDF viewer's own page counter shows (not the
# printed page number in the book, which is often offset by the
# front matter).
#
# Example:
# Introduction | 12
# Linear Models | 45
#
# Lines starting with '#' (like this one) are ignored.
"""


def generate_chapter_template(book: str) -> str:
    """A starter file for identify_chapters_from_manual_list(), with the
    format documented inline so a human can fill it in without needing
    to read this module."""
    return _CHAPTER_TEMPLATE.format(book=book)


def parse_manual_chapter_list(text: str) -> list[ChapterEntry]:
    """
    Parses a human-filled chapter template (generate_chapter_template):
    one "Title | PageNumber" per line. Blank lines and lines starting
    with '#' are ignored; a malformed line is silently skipped rather
    than raised on -- identify_chapters_from_manual_list()'s own
    confidence check (every chapter must actually be reached) is what
    catches a badly-filled template, not this parser guessing at intent.
    """
    chapters = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _MANUAL_LINE_RE.match(line)
        if not m:
            continue
        title = m.group(1).strip()
        if not title:
            continue
        chapters.append(ChapterEntry(title=title, physical_page=int(m.group(2))))
    return chapters


def identify_chapters_from_manual_list(text: str, manual_text: str) -> TocIdentification:
    """
    Last-resort fallback for a book with neither usable folio tags nor a
    usable PDF outline (confirmed live: Simon has zero outline entries
    at all; Press and Rubenstein's PDFs have none either). `manual_text`
    is the human-filled template's own contents (see
    generate_chapter_template); matched against <!-- page N --> tags
    with the same conservative "every chapter reached, in order"
    contract as identify_chapters and identify_chapters_via_outline.
    """
    chapters = _dedupe_by_increasing(parse_manual_chapter_list(manual_text), "physical_page")
    if not chapters:
        return TocIdentification(toc_chapters=[], reason="chapter template is empty or unparseable")

    page_positions = _page_positions(text)
    if not page_positions:
        return TocIdentification(
            toc_chapters=chapters,
            reason="no page tags found in the body to position chapters against",
        )

    matches, reason = _match_forward(chapters, "physical_page", page_positions, "page")
    return TocIdentification(toc_chapters=chapters, matches=matches, confident=not reason, reason=reason)
