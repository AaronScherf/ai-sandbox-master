import json
import os
import shutil

from framed_explainer_helpers import el, slide, stroke, write_scene
from pipelines.transcribe_notes.framed_explainer.collect import collect
from pipelines.transcribe_notes.framed_explainer.review import (
    apply_decisions, build_review_items)

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "framed_explainer")


def _resolved():
    with open(os.path.join(FIX, "result_resolved_ok.json"), encoding="utf-8") as f:
        return json.load(f)


def _kinds(items):
    return sorted(i.kind for i in items)


def test_fallback_nearest_and_needs_review_become_items():
    items = build_review_items(_resolved(), [])
    assert _kinds(items) == ["fallback_nearest", "needs_review"]
    fb = next(i for i in items if i.kind == "fallback_nearest")
    assert fb.options == ["accept", "make_section"] and fb.target_key == "s1"


def test_low_confidence_assignment_becomes_item():
    res = _resolved()
    res["slides"][0]["ink"][0]["confidence"] = 0.3
    assert "low_confidence" in _kinds(build_review_items(res, []))


def test_anchor_tie_becomes_item():
    res = _resolved()
    res["sections"][0]["also_near"] = "s2"
    res["sections"][0]["anchor_slide_id"] = "s1"
    assert "anchor_tie" in _kinds(build_review_items(res, []))


def test_placement_conflict_and_existing_become_items_with_options():
    items = build_review_items(_resolved(), [
        {"key": "s1", "action": "placement_conflict"},
        {"key": "s2", "action": "skipped_existing"}])
    by_kind = {i.kind: i for i in items}
    assert by_kind["placement_conflict"].options == ["skip", "expand"]
    assert by_kind["replace_existing"].options == ["keep", "replace"]


def _scene(tmp_path, ink_x=1000):
    lec = tmp_path / "academic_notes" / "econometrics" / "part_2" / "lecture_notes"
    lec.mkdir(parents=True, exist_ok=True)
    return write_scene(lec / "Econometrics 2026-11-04 t.excalidraw.md", [
        slide("s1", 0, 0), el("f1", "frame", -10, -10, 2200, 700, name="001 Slide 1"),
        stroke("k1", ink_x, 50)])


def test_declined_decision_suppresses_card_on_same_fingerprint(tmp_path):
    scene = _scene(tmp_path)
    first = collect(scene, str(tmp_path), "r1")
    assert [t.eligibility for t in first.targets] == ["eligible"]
    items = build_review_items(_resolved(), [])
    needs = next(i for i in items if i.kind == "needs_review")
    needs.target_key = "s1"
    apply_decisions({needs.item_id: "decline"}, [needs], first.run_dir)
    second = collect(scene, str(tmp_path), "r2")
    assert [t.eligibility for t in second.targets] == ["declined"]


def test_changed_fingerprint_reopens_declined_card(tmp_path):
    scene = _scene(tmp_path)
    first = collect(scene, str(tmp_path), "r1")
    item = build_review_items(_resolved(), [])[-1]
    item.target_key = "s1"
    apply_decisions({item.item_id: "decline"}, [item], first.run_dir)
    scene = _scene(tmp_path, ink_x=1100)   # ink moved: fingerprint changes
    again = collect(scene, str(tmp_path), "r3")
    assert [t.eligibility for t in again.targets] == ["eligible"]
    shutil.rmtree(tmp_path / ".agent_work")
