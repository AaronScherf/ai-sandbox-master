import numpy as np

from notes.excalidraw_chunking import find_gaps


def _rows(*specs):
    """Build a tiny grayscale array from a list of (row_count, min_value) pairs."""
    rows = []
    for count, value in specs:
        rows.extend([value] * count)
    return np.array([[v] * 3 for v in rows], dtype=np.uint8)


def test_find_gaps_finds_a_single_blank_band():
    # 5 ink rows (dark), 10 blank rows (white), 5 ink rows
    gray = _rows((5, 50), (10, 255), (5, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == [(5, 15)]


def test_find_gaps_ignores_short_blank_runs():
    # a 3-row blank run is below min_gap_rows=8 -- not a real gap
    gray = _rows((5, 50), (3, 255), (5, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == []


def test_find_gaps_handles_trailing_blank_run():
    gray = _rows((5, 50), (10, 255))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == [(5, 15)]


def test_find_gaps_no_gaps_in_solid_ink():
    gray = _rows((20, 50))
    assert find_gaps(gray, ink_row_threshold=245, min_gap_rows=8) == []


from PIL import Image

from notes.excalidraw_chunking import choose_cuts, chunk_image


def test_choose_cuts_picks_gap_nearest_target_height():
    # gaps at 100-110 and 2990-3010 and 6000-6010, height 8000,
    # target 3000 -> first cut should land in the 2990-3010 gap (midpoint 3000)
    gaps = [(100, 110), (2990, 3010), (6000, 6010)]
    cuts = choose_cuts(8000, gaps, target_chunk_height=3000, max_chunk_height=4500)
    assert cuts[0] == (3000, False)


def test_choose_cuts_hard_cuts_when_no_gap_available():
    # no gaps at all -- must still produce a cut, flagged as hard
    cuts = choose_cuts(10000, [], target_chunk_height=3000, max_chunk_height=4500)
    assert cuts[0] == (4500, True)


def test_choose_cuts_no_cuts_needed_under_target():
    cuts = choose_cuts(2000, [], target_chunk_height=3000, max_chunk_height=4500)
    assert cuts == []


def _make_canvas(height: int, ink_rows: set[int]) -> Image.Image:
    """White canvas, width 10, with the given rows painted dark (ink)."""
    img = Image.new("RGB", (10, height), color=(255, 255, 255))
    pixels = img.load()
    for y in ink_rows:
        for x in range(10):
            pixels[x, y] = (30, 30, 30)
    return img


def test_chunk_image_splits_at_a_real_gap_not_through_ink():
    # ink rows 0-4 and 20-24, blank 5-19 (15 rows, a real gap) and 25-29
    ink_rows = set(range(0, 5)) | set(range(20, 25))
    canvas = _make_canvas(30, ink_rows)
    chunks = chunk_image(canvas, target_chunk_height=10, max_chunk_height=20, min_gap_rows=8)
    assert len(chunks) == 2
    assert chunks[0].size == (10, 12)  # cut at gap midpoint (5+20)//2=12
    total_height = sum(c.size[1] for c in chunks)
    assert total_height == 30
