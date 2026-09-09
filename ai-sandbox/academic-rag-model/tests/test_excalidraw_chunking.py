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
