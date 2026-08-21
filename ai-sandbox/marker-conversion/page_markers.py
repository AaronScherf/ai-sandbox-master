"""
page_markers.py
Pure-Python helpers for rewriting Marker's chunk-local page markers,
anchors, and links into book-wide physical page numbers -- and, where
derivable, printed folio numbers. No dependency on marker/torch/surya:
this operates purely on already-rendered markdown text.

Each chunk is converted as an independent temp PDF, so Marker's own
paginate_output numbering, <span id="page-N-M"> anchors, and internal
(#page-N-M) links are all local to that chunk (always starting at 0).
Confirmed directly against real output (Axler_Linear_Algebra_Done_Right_2026):
the same id="page-1-0" recurs once per chunk in the merged file, so any
link generated against a chapter past the first chunk resolves to the
wrong target. Remapping by a fixed offset per chunk fixes both the display
page tags and this collision in one pass.
"""
from __future__ import annotations

import re

_MARKER_PAGE_BREAK_RE = re.compile(r"\n\n(\d+)-{48}\n\n")
_SPAN_ID_RE = re.compile(r'(<span id="page-)(\d+)(-\d+"></span>)')
_LINK_TARGET_RE = re.compile(r"(\(#page-)(\d+)(-\d+\))")


def _folio_tag(physical_page: int, folio_offset: int | None, folio_start_page: int) -> str:
    if folio_offset is not None and physical_page >= folio_start_page:
        return f"<!-- folio {physical_page - folio_offset} -->"
    return ""


def remap_page_markers(text: str, physical_offset: int, folio_offset: int | None, folio_start_page: int) -> str:
    """
    Rewrites a converted chunk's text so every page/anchor/link reference
    reflects the book's true physical page numbering instead of Marker's
    chunk-local numbering.
    """

    def _replace_page_break(m: re.Match) -> str:
        physical_page = physical_offset + int(m.group(1))
        tag = f"<!-- page {physical_page} -->" + _folio_tag(physical_page, folio_offset, folio_start_page)
        return f"\n\n{tag}\n\n"

    text = _MARKER_PAGE_BREAK_RE.sub(_replace_page_break, text)
    text = _SPAN_ID_RE.sub(lambda m: f"{m.group(1)}{physical_offset + int(m.group(2))}{m.group(3)}", text)
    text = _LINK_TARGET_RE.sub(lambda m: f"{m.group(1)}{physical_offset + int(m.group(2))}{m.group(3)}", text)
    return text


def tag_single_page(text: str, physical_page: int, folio_offset: int | None, folio_start_page: int) -> str:
    """
    Prepends a page (and, where derivable, folio) tag directly -- for
    content that never went through Marker's paginate_output at all (the
    raw-PyPDF last-resort fallback tier).
    """
    tag = f"<!-- page {physical_page} -->" + _folio_tag(physical_page, folio_offset, folio_start_page)
    return f"{tag}\n\n{text}"
