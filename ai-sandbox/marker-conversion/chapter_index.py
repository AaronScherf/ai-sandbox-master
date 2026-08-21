"""
chapter_index.py
Pure-Python helpers for building a chapter index from a textbook PDF --
either from its embedded outline, or bootstrapped from a parse of its own
rendered table of contents -- used by convert_textbook.py to align chunk
boundaries to chapter breaks and to tag output pages with physical PDF page
index and (where derivable) printed folio number.

Deliberately has NO dependency on marker, torch, or surya: convert_textbook.py
imports those at module scope, which requires the GCP VM's CUDA environment
to even succeed, so nothing that depends on them can be unit tested off that
VM. Everything in this module can be, on any machine with pypdf installed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChapterEntry:
    title: str
    physical_page: int | None = None
    folio_page: int | None = None
    folio_is_roman: bool = False
    folio_raw: str | None = None


def get_outline_chapters(reader) -> list[ChapterEntry]:
    """
    Top-level (depth 1) entries from the PDF's embedded outline/bookmarks,
    resolved to physical page numbers. Never raises: returns [] if there's
    no outline, or if resolving any entry fails outright.
    """
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []

    chapters = []
    for item in outline:
        # pypdf represents nested outline levels as sub-lists; only take
        # top-level Destination objects here, not nested lists (those are
        # subsections, which chunking deliberately ignores).
        if isinstance(item, list):
            continue
        try:
            page_num = reader.get_destination_page_number(item)
            title = str(item.title).strip()
        except Exception:
            continue
        if title:
            chapters.append(ChapterEntry(title=title, physical_page=page_num))
    return chapters
