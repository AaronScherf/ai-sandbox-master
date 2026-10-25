"""
textbook_chapters.py
Chapter-aware splitting for audio_generator's textbook content type
(TODO-0057): reuses chapter_index.py's existing printed-TOC parser
(parse_printed_toc) and the folio tags convert_textbook/page_markers.py
already burns into the final, fully-converted markdown
(map_folios_to_physical_pages) to find where each chapter starts, so
textbook narration can produce one MP3 per chapter instead of one per
source file.

Deliberately NOT a from-scratch page-alignment reimplementation: the
offset chapter_index.bootstrap_chapter_index_from_front_matter would
otherwise have to re-derive by OCR-scanning page text is, for an
already-converted book, already burned into every page's own `<!-- page
N --><!-- folio F -->` tag -- see map_folios_to_physical_pages's own
docstring for why re-running that OCR-based scan against a whole
already-converted book finds nothing, confirmed against real output.

Best-effort and conservative: a book whose conversion run never derived a
folio offset (no folio tags anywhere in its final .md -- confirmed
against real output, e.g. an econometrics textbook whose conversion
never found a confident offset), or whose TOC resolves fewer than two
chapters to physical pages, has no usable chapter boundaries at all.
split_into_chapters() returns [] in both cases; callers must fall back to
the original single-MP3-per-book behavior, not guess a boundary.

Content before the first resolved chapter (title page, table of
contents, preface, ...) is dropped, not narrated as its own "chapter
0" -- a deliberate scope simplification for v1.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from pipelines.convert_textbook.chapter_index import map_folios_to_physical_pages, parse_printed_toc

# Local duplicate of chapter_index.py's own page-marker format (project
# convention, see discovery.py's own docstring for the same tradeoff):
# this module needs the markdown text *offset* of each physical page's
# tag, which is a splitting concern for audio_generator, not a piece of
# chapter-boundary domain knowledge that belongs in chapter_index.py.
_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


@dataclass
class ChapterSpan:
    index: int  # 1-based, matches the __chNN output filename suffix
    title: str
    text: str  # this chapter's own raw markdown slice (unnarrated, uncleaned)


def _physical_page_offsets(markdown_text: str) -> dict[int, int]:
    """Maps each physical page number appearing in markdown_text to the
    character offset where its own `<!-- page N -->` tag starts. First
    occurrence wins (a physical page number should only ever tag one
    page)."""
    offsets: dict[int, int] = {}
    for m in _PAGE_MARKER_RE.finditer(markdown_text):
        offsets.setdefault(int(m.group(1)), m.start())
    return offsets


def split_into_chapters(markdown_text: str) -> list[ChapterSpan]:
    """
    Splits already-converted textbook markdown at chapter boundaries.
    Returns [] whenever fewer than two chapters can be confidently
    resolved -- including when there's no parseable TOC at all, no folio
    tags anywhere (this book's conversion run never found a confident
    offset), or only one TOC entry happens to match a tagged page (the
    same consensus bar the rest of chapter_index.py uses before trusting
    a sparse match).
    """
    toc_chapters = parse_printed_toc(markdown_text)
    if not toc_chapters:
        return []

    folio_to_physical = map_folios_to_physical_pages(markdown_text)
    if not folio_to_physical:
        return []

    page_offsets = _physical_page_offsets(markdown_text)

    resolved: list[tuple[int, str, int]] = []  # (physical_page, title, start_offset)
    for entry in toc_chapters:
        if entry.folio_is_roman or entry.folio_page is None:
            continue
        physical_page = folio_to_physical.get(entry.folio_page)
        if physical_page is None:
            continue
        start_offset = page_offsets.get(physical_page)
        if start_offset is None:
            continue
        resolved.append((physical_page, entry.title, start_offset))

    if len(resolved) < 2:
        return []

    resolved.sort(key=lambda r: r[0])

    spans = []
    for i, (_physical_page, title, start_offset) in enumerate(resolved):
        end_offset = resolved[i + 1][2] if i + 1 < len(resolved) else len(markdown_text)
        spans.append(ChapterSpan(index=i + 1, title=title, text=markdown_text[start_offset:end_offset]))
    return spans
