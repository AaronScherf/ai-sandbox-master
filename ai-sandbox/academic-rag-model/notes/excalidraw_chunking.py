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

import io

import numpy as np
from PIL import Image


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


def choose_cuts(
    height: int, gaps: list[tuple[int, int]],
    target_chunk_height: int = 3000, max_chunk_height: int = 4500,
) -> list[tuple[int, bool]]:
    """Walks down the image picking a gap-midpoint cut near every
    target_chunk_height, falling back to a hard cut at max_chunk_height
    only when no gap is available in that window -- never observed on
    the two real canvases this was spiked against, but must still be
    handled rather than assumed impossible."""
    cuts: list[tuple[int, bool]] = []
    last_cut = 0
    while last_cut + target_chunk_height < height:
        want = last_cut + target_chunk_height
        window_end = min(last_cut + max_chunk_height, height)
        candidates = [g for g in gaps if last_cut < (g[0] + g[1]) // 2 <= window_end]
        if candidates:
            best = min(candidates, key=lambda g: abs((g[0] + g[1]) // 2 - want))
            cut = (best[0] + best[1]) // 2
            hard = False
        else:
            cut = last_cut + max_chunk_height
            hard = True
        if cut >= height:
            # No room for another cut before the end of the image -- the
            # final segment (handled by chunk_image's own trailing
            # `height` boundary) runs long instead. Without this guard,
            # a hard cut that lands exactly on `height` would produce a
            # spurious zero-height final chunk.
            break
        cuts.append((cut, hard))
        last_cut = cut
    return cuts


def chunk_image(
    image: Image.Image,
    target_chunk_height: int = 3000, max_chunk_height: int = 4500,
    ink_row_threshold: int = 245, min_gap_rows: int = 8,
) -> list[Image.Image]:
    """Crops `image` into ordered, top-to-bottom chunks cut at whitespace
    gaps. Full width is preserved on every chunk -- only height is cut."""
    gray = np.array(image.convert("L"))
    height, width = gray.shape
    gaps = find_gaps(gray, ink_row_threshold=ink_row_threshold, min_gap_rows=min_gap_rows)
    cuts = choose_cuts(height, gaps, target_chunk_height=target_chunk_height, max_chunk_height=max_chunk_height)

    rgb = image.convert("RGB")
    chunks = []
    prev = 0
    for cut, _hard in cuts + [(height, False)]:
        chunks.append(rgb.crop((0, prev, width, cut)))
        prev = cut
    return chunks


def resize_chunk_for_api(image: Image.Image, max_width: int = 2000, jpeg_quality: int = 85) -> bytes:
    """Encodes a chunk for the Gemini API call -- caps width (height
    scaled proportionally) and re-encodes as JPEG. max_width defaults to
    2000px, well above real Excalidraw canvases (~785px wide observed),
    because a real experiment found resizing/compressing bought no
    measured token-cost or accuracy benefit at that scale -- Gemini's
    vision tokenization is resolution-bucketed, not byte-size-driven, and
    these canvases already fall in a small bucket (see
    docs/status/2026-08-24-notes-transcription-status.md's 2026-09-09
    compression-experiment entry). The high default is a safety net for
    an unusually wide future canvas, not a routine resize; JPEG
    re-encoding is kept purely for a smaller upload payload."""
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
    return buf.getvalue()
