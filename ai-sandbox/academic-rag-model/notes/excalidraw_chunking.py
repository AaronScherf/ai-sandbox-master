"""
excalidraw_chunking.py
Turns a tall Excalidraw canvas PNG (unbounded height, unlike a fixed-size
PDF page) into API-ready chunks by cutting at whitespace gaps rather than
a fixed pixel interval -- spiked and validated against two real canvases
(785x13,860px and 786x7,049px) before this module existed; see
docs/status/2026-08-24-notes-transcription-status.md's "2026-09-09"
section and docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
No network calls, no filesystem writes -- pure image processing.
"""
from __future__ import annotations

import numpy as np


def find_gaps(gray: np.ndarray, ink_row_threshold: int = 245, min_gap_rows: int = 8) -> list[tuple[int, int]]:
    """Returns (start, end) row ranges that are blank -- every pixel in
    the row is >= ink_row_threshold. A run shorter than min_gap_rows is
    not returned; it's too small to safely cut inside without risking a
    near-miss on real ink (e.g. the gap between two lines of the same
    sentence)."""
    row_min = gray.min(axis=1)
    is_blank = row_min >= ink_row_threshold
    gaps = []
    start = None
    for y, blank in enumerate(is_blank):
        if blank and start is None:
            start = y
        elif not blank and start is not None:
            if y - start >= min_gap_rows:
                gaps.append((start, y))
            start = None
    if start is not None and len(is_blank) - start >= min_gap_rows:
        gaps.append((start, len(is_blank)))
    return gaps
