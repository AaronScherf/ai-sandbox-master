"""Fixture helpers for course_materials tests: blank PDFs of a given page shape, and small course trees."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

LANDSCAPE, PORTRAIT = (792, 612), (612, 792)


def make_pdf(path: Path, width: float, height: float, rotate: int = 0) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=width, height=height)
    if rotate:
        page.rotate(rotate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
