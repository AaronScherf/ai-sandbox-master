from framed_explainer_helpers import slide, stroke
from pipelines.transcribe_notes.framed_explainer.ink import (
    Bounds, Region, anchor_for, box_gap, cluster_ink, fallback_slide, reading_order)


def _region(rid, x, y, w=100, h=50):
    return Region(rid, Bounds(x, y, w, h), [rid + "-s"])


def test_cluster_ink_splits_on_gap():
    far = cluster_ink([stroke("a", 0, 0), stroke("b", 220, 0)])
    near = cluster_ink([stroke("a", 0, 0), stroke("b", 70, 0)])
    assert [sorted(r.stroke_ids) for r in far] == [["a"], ["b"]]
    assert [sorted(r.stroke_ids) for r in near] == [["a", "b"]]


def test_cluster_ink_respects_max_size():
    chain = [stroke(f"s{i:02d}", i * 70, 0) for i in range(30)]  # 2,100 wide chain
    regions = cluster_ink(chain)
    assert len(regions) >= 2
    assert all(r.bounds.w <= 1200 for r in regions)


def test_box_gap_is_euclidean_between_boxes():
    assert box_gap(Bounds(0, 0, 10, 10), Bounds(13, 14, 10, 10)) == 5.0
    assert box_gap(Bounds(0, 0, 10, 10), Bounds(5, 5, 10, 10)) == 0.0


def test_fallback_requires_clear_margin():
    s1, s2 = slide("s1", 0, 0), slide("s2", 3000, 0)
    close = _region("c", 1000, 0)           # gap 93 to s1, 1900 to s2
    assert fallback_slide(close, [s1, s2], [close]) == "s1"
    tie = Region("t", Bounds(1700, 0, 100, 50), ["t-s"])  # gap 793 to s1, 1200 to s2
    assert fallback_slide(tie, [s1, s2], [tie]) is None   # 793 !< 0.5*1200


def test_fallback_blocked_by_intervening_ink():
    s1 = slide("s1", 0, 0)
    target = _region("t", 1100, 0)
    blocker = _region("b", 960, 0, 80, 50)  # lies in the gap between slide edge (907) and target
    assert fallback_slide(target, [s1], [target, blocker]) is None
    assert fallback_slide(target, [s1], [target]) == "s1"


def test_anchor_threshold():
    s1 = slide("s1", 0, 0)  # width 907 -> threshold 1360.5
    ok = Region("o", Bounds(907 + 1300, 0, 50, 50), ["o"])
    far = Region("f", Bounds(907 + 1400, 0, 50, 50), ["f"])
    assert anchor_for(ok, [s1])[0] == "s1"
    assert anchor_for(far, [s1]) == (None, None)


def test_anchor_records_also_near_for_between_two():
    s1, s2 = slide("s1", 0, 0), slide("s2", 2400, 0)
    mid = Region("m", Bounds(1100, 0, 100, 50), ["m"])  # gap 193 to s1, ~1200 to s2 -> s2 not near-tie
    mid2 = Region("x", Bounds(1500, 0, 100, 50), ["x"])  # gap 593 vs 800 -> near tie
    assert anchor_for(mid, [s1, s2]) == ("s1", None)
    assert anchor_for(mid2, [s1, s2]) == ("s1", "s2")


def test_reading_order_rows_then_columns():
    a, b, c = _region("a", 900, 10), _region("b", 0, 120), _region("c", 0, 900)
    assert [r.region_id for r in reading_order([c, a, b])] == ["b", "a", "c"]


def test_fallback_has_distance_cap_with_single_slide():
    slides = [{"id": "A", "x": 0, "y": 0, "width": 907, "height": 510}]
    far = Region("r", Bounds(20000, 20000, 20, 20), ["k"])
    assert fallback_slide(far, slides, [far]) is None
