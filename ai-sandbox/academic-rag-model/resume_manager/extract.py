"""
extract.py
Local, zero-API-call text extraction for the resume PDF -- reuses
notes/transcribe_notes.py's Tier-1 primitives directly rather than
its process_pdf() tier-routing wrapper. That wrapper's
has_reliable_pagination() check sniffs /Creator//Producer metadata for
LaTeX/Word/LibreOffice/FOP/XEP and fails safe to the handwriting/
messy-export fallback for anything else -- confirmed against the real
resume.pdf (/Producer: Skia/PDF m124, a headless-Chrome export) that
this would misroute a clean typeset resume through that fallback
purely on an unrecognized metadata string. Spec §3.
"""
from __future__ import annotations

import os

from pypdf import PdfReader

from notes.transcribe_notes import (
    build_final_markdown, build_frontmatter, extract_all_page_texts, page_looks_defective,
)


class DefectivePageError(Exception):
    """Raised when a page's local text extraction looks defective.
    Conversion stops here rather than silently escalating to Gemini
    vision -- a 1-2 page resume is short enough to deserve the user's
    direct attention instead (spec §3, §8)."""


def extract_resume_text(pdf_path: str) -> str:
    """Local PyMuPDF extraction of every page, page-tagged and
    frontmatter-wrapped the same way the rest of the corpus's Markdown
    is (build_final_markdown/build_frontmatter, reused unchanged).
    Raises DefectivePageError if any page fails page_looks_defective()
    -- never falls back to a Gemini call."""
    total_pages = len(PdfReader(pdf_path).pages)
    all_page_texts = extract_all_page_texts(pdf_path, total_pages)

    defective_pages = [n for n in range(1, total_pages + 1) if page_looks_defective(all_page_texts[n - 1])]
    if defective_pages:
        raise DefectivePageError(
            f"page(s) {defective_pages} of {pdf_path} look defective under local extraction -- "
            f"re-export the source PDF, or transcribe those pages by hand, rather than escalating "
            f"to a vision model this pipeline doesn't use (spec §3)."
        )

    cache = {str(n): all_page_texts[n - 1].strip() for n in range(1, total_pages + 1)}
    final_md = build_final_markdown(cache, total_pages)
    frontmatter = build_frontmatter({
        "source_pdf": os.path.basename(pdf_path), "total_pages": total_pages, "routing": "local", "tags": [],
    })
    return frontmatter + final_md
