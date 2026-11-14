# pipelines/transcribe_notes/framed_explainer/rasters.py
"""Frame rasters from a user-exported Printable Layout PDF (the first-release
bridge). Page-to-frame mapping is by frame name order and must match the page
count; it never guesses."""
from __future__ import annotations

import os

import fitz


class PageMappingError(ValueError):
    """PDF page count does not equal the number of frames."""


def rasterize_frame_pdf(pdf_path: str, frames: list[dict], out_dir: str,
                        dpi: int = 110) -> dict[str, str]:
    """Return {frame_id: png_path}, pages assigned in frame-name order."""
    ordered = sorted(frames, key=lambda f: (f.get("name") or "", f["id"]))
    with fitz.open(pdf_path) as doc:
        if doc.page_count != len(ordered):
            raise PageMappingError(
                f"{pdf_path}: {doc.page_count} pages but {len(ordered)} frames")
        os.makedirs(out_dir, exist_ok=True)
        result: dict[str, str] = {}
        for page, frame in zip(doc, ordered):
            png = os.path.join(out_dir, f"{frame['id']}.png")
            page.get_pixmap(dpi=dpi).save(png)
            result[frame["id"]] = png
    return result
