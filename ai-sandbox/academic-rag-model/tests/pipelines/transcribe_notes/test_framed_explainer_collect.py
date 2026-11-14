import json
import os

from framed_explainer_helpers import MD_C, el, slide, stroke, write_scene
from pipelines.transcribe_notes.framed_explainer.collect import collect


def _scene(tmp_path, elements, name="Econometrics 2026-11-04 t.excalidraw.md"):
    part = tmp_path / "academic_notes" / "econometrics" / "part_2" / "lecture_notes"
    part.mkdir(parents=True, exist_ok=True)
    return write_scene(part / name, elements)


def _framed_slide():
    return [slide("s1", 0, 0), el("f1", "frame", -10, -10, 2200, 700, name="001 Slide 1"),
            stroke("k1", 1000, 50), stroke("k2", 1040, 60)]


def test_empty_scene_is_nothing_to_do_and_writes_nothing(tmp_path):
    scene = _scene(tmp_path, [el("gone", "freedraw", isDeleted=True)])
    res = collect(scene, str(tmp_path), "run1")
    assert res.status == "nothing_to_do" and res.targets == []
    assert not os.path.exists(tmp_path / ".agent_work")


def test_ink_only_scene_stages_sections_mode(tmp_path):
    scene = _scene(tmp_path, [stroke("k1", 0, 0), stroke("k2", 500, 0)])
    res = collect(scene, str(tmp_path), "run1")
    facts = json.load(open(res.facts_path, encoding="utf-8"))
    assert res.status == "staged"
    assert facts["mode"] == "ink_only" and facts["slides"] == []
    assert len(facts["regions"]) == 2
    assert [t.eligibility for t in res.targets] == ["eligible", "eligible"]


def test_slide_with_frame_is_eligible_and_context_written(tmp_path):
    res = collect(_scene(tmp_path, _framed_slide()), str(tmp_path), "run1")
    facts = json.load(open(res.facts_path, encoding="utf-8"))
    assert facts["mode"] == "slides" and facts["slides"][0]["frame_id"] == "f1"
    assert [t.eligibility for t in res.targets] == ["eligible"]
    assert os.path.exists(os.path.join(res.run_dir, "course_context.md"))
    task = open(res.task_path, encoding="utf-8").read()
    assert "result.json" in task and "facts.json" in task
    assert facts["scene_sha1"] and facts["schema"] == 1


def test_existing_explanation_marks_existing_card(tmp_path):
    els = _framed_slide() + [el("e1", "image", 1000, 0, 950, 500, fileId=MD_C, frameId="f1",
                                customData={"markdownImage": {"schemaVersion": 1}})]
    res = collect(_scene(tmp_path, els), str(tmp_path), "run1")
    assert [t.eligibility for t in res.targets] == ["existing_card"]


def test_slide_without_frame_needs_review(tmp_path):
    res = collect(_scene(tmp_path, [slide("s1", 0, 0)]), str(tmp_path), "run1")
    assert [t.eligibility for t in res.targets] == ["needs_review"]


def test_restage_same_input_is_already_staged(tmp_path):
    scene = _scene(tmp_path, _framed_slide())
    first = collect(scene, str(tmp_path), "run1")
    again = collect(scene, str(tmp_path), "run1")
    assert first.status == "staged" and again.status == "already_staged"


def test_facts_json_uses_lf_and_is_deterministic(tmp_path):
    scene = _scene(tmp_path, _framed_slide())
    a = collect(scene, str(tmp_path), "runA")
    b = collect(scene, str(tmp_path), "runB")
    raw = open(a.facts_path, "rb").read()
    assert b"\r\n" not in raw and raw.endswith(b"\n")
    assert raw == open(b.facts_path, "rb").read()


def test_scene_never_modified(tmp_path):
    scene = _scene(tmp_path, _framed_slide())
    before = open(scene, "rb").read()
    collect(scene, str(tmp_path), "run1")
    assert open(scene, "rb").read() == before


def _card(fp):
    return el("c1", "image", -1000, 0, 950, 500, fileId=MD_C, frameId="f1",
              customData={"markdownImage": {"schemaVersion": 1},
                          "autoExplainKey": "ns|f1|s1", "autoExplainFingerprint": fp})


def test_auto_card_with_stale_fingerprint_is_eligible_for_replacement(tmp_path):
    res = collect(_scene(tmp_path, _framed_slide() + [_card("old")]), str(tmp_path), "run1")
    assert [t.eligibility for t in res.targets] == ["eligible"]


def test_auto_card_with_current_fingerprint_is_existing(tmp_path):
    first = collect(_scene(tmp_path, _framed_slide()), str(tmp_path), "run1")
    fp = first.targets[0].fingerprint
    res = collect(_scene(tmp_path, _framed_slide() + [_card(fp)]), str(tmp_path), "run2")
    assert [t.eligibility for t in res.targets] == ["existing_card"]


def test_namespace_is_vault_relative_not_absolute(tmp_path):
    a = collect(_scene(tmp_path / "a", _framed_slide()), str(tmp_path / "a"), "r")
    b = collect(_scene(tmp_path / "b", _framed_slide()), str(tmp_path / "b"), "r")
    ns = lambda r: json.load(open(r.facts_path, encoding="utf-8"))["namespace"]
    assert ns(a) == ns(b)


def test_band_assignment_is_staged_per_slide_and_region(tmp_path):
    els = [slide("s1", 0, 0), slide("s2", 20, 1000), stroke("a", 3000, 100), stroke("b", 3000, 1100)]
    res = collect(_scene(tmp_path, els), str(tmp_path), "run1")
    facts = json.load(open(res.facts_path, encoding="utf-8"))
    ink = {s["id"]: s["ink_stroke_ids"] for s in facts["slides"]}
    assert ink == {"s1": ["a"], "s2": ["b"]}
    band = {tuple(r["stroke_ids"]): r["band_slide"] for r in facts["regions"]}
    assert band == {("a",): "s1", ("b",): "s2"}
    assert all("created" in s for s in facts["strokes"])
