"""Python assign_strokes must agree with the framer's JS matchInk on the same scenes."""
import json
import os
import random
import shutil
import subprocess

import pytest

from pipelines.transcribe_notes.framed_explainer.bands import assign_strokes

RUNNER = os.path.join(os.path.dirname(__file__), "framer_band_runner.cjs")


def _slide(i, x, y, w=907, h=510):
    return {"id": i, "type": "image", "x": x, "y": y, "width": w, "height": h}


def _stroke(i, x, y, created=None, w=20, h=20):
    e = {"id": i, "type": "freedraw", "x": x, "y": y, "width": w, "height": h}
    if created is not None:
        e["created"] = created
    return e


def _js(slides, strokes):
    script = os.environ.get("AUTO_FRAME_SCRIPT")
    if not script or not os.path.exists(script) or not shutil.which("node"):
        pytest.skip("set AUTO_FRAME_SCRIPT to the framer script and install node")
    out = subprocess.run(["node", RUNNER, script],
                         input=json.dumps({"slides": slides, "strokes": strokes}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _check(slides, strokes):
    js = _js(slides, strokes)
    py = assign_strokes(slides, strokes)
    assert py.by_slide == js["bySlide"]
    assert py.loose == js["loose"]
    return py


COLUMN = [_slide("s1", 0, 0), _slide("s2", 30, 1000), _slide("s3", -20, 2000)]


def _boundary(extra):
    ink = [_stroke(f"u{i:02d}", 2500, 100 + i * 25, 1000 + i * 5000) for i in range(20)]
    ink += [_stroke(f"l{i:02d}", 2500, 1400 + i * 25, 300000 + i * 5000) for i in range(20)]
    return ink + extra


def test_column_far_right_ink():
    py = _check(COLUMN, [_stroke("a", 2500, 100), _stroke("b", 2500, 1100), _stroke("c", 2500, 2100)])
    assert py.mode == "column" and py.by_slide == {"s1": ["a"], "s2": ["b"], "s3": ["c"]}


@pytest.mark.parametrize("y,created,owner", [
    (1010, 98000, "s1"), (1010, 299000, "s2"), (1010, 9_000_000, "s2"),
    (950, 299000, "s1")])
def test_edge_stroke_time_rules(y, created, owner):
    py = _check(COLUMN, _boundary([_stroke("x", 2500, y, created)]))
    assert "x" in py.by_slide[owner]


def test_identical_created_is_ignored():
    py = _check(COLUMN, _boundary([_stroke("x", 2500, 1010, 98000), _stroke("y", 2900, 1010, 98000)]))
    assert "x" in py.by_slide["s2"]


def test_burst_stays_with_slide_above():
    py = _check(COLUMN, _boundary([_stroke("x1", 2500, 950, 299000), _stroke("x2", 2500, 1010, 300500)]))
    assert {"x1", "x2"} <= set(py.by_slide["s1"])


def test_chain_defers_without_timestamps():
    ink = [_stroke(f"c{i:02d}", 2500, 300 + i * 50, None, 20, 40) for i in range(14)]
    ink.append(_stroke("t", 2500, 1020, None, 20, 40))
    ink += [_stroke(f"n{i}", 2500, 1500 + i * 50, None, 20, 40) for i in range(5)]
    py = _check(COLUMN, ink)
    assert "t" in py.by_slide["s1"]


def test_row_bands():
    py = _check([_slide("a", 0, 0), _slide("b", 1500, 10)], [_stroke("p", 100, 900), _stroke("q", 1600, 900)])
    assert py.mode == "row" and py.by_slide == {"a": ["p"], "b": ["q"]}


GRID = [_slide("a", 0, 0), _slide("b", 1000, 0), _slide("c", 0, 700), _slide("d", 1000, 700)]


def test_grid_proximity_and_cannot_tell():
    py = _check(GRID, [_stroke("near", -60, 300), _stroke("mid", 950, 100, None, 10, 10)])
    assert py.mode == "proximity"
    assert py.by_slide == {"a": ["near"]} and py.loose == ["mid"]


def test_lone_slide_rejects_far_ink():
    py = _check([_slide("a", 0, 0)], [_stroke("far", 9000, 9000)])
    assert py.by_slide == {} and py.loose == ["far"]


def test_random_columns_match_js():
    rng = random.Random(5)
    slides = [_slide(f"s{i}", rng.randrange(-60, 60), i * 700 + rng.randrange(0, 80)) for i in range(5)]
    strokes = [_stroke(f"k{i:03d}", rng.randrange(1000, 2600), rng.randrange(-300, 3800),
                       rng.choice([None, rng.randrange(0, 600000)]), rng.randrange(5, 60),
                       rng.randrange(5, 80)) for i in range(160)]
    _check(slides, strokes)
