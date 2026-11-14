import copy
import json
import os

import pytest

from pipelines.transcribe_notes.framed_explainer.results import (
    ResultError, resolve_result, validate_result)

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "framed_explainer")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def facts():
    return load("facts_ok.json")


@pytest.fixture
def result():
    return load("result_ok.json")


def code_of(result, facts):
    with pytest.raises(ResultError) as exc:
        validate_result(result, facts)
    return exc.value.code


def test_valid_result_passes(result, facts):
    validate_result(result, facts)


def test_duplicate_stroke_rejected(facts):
    assert code_of(load("result_dup_stroke.json"), facts) == "duplicate_stroke"


def test_unknown_slide_id_rejected(result, facts):
    result["slides"][0]["slide_id"] = "nope"
    assert code_of(result, facts) == "unknown_id"


def test_unknown_stroke_id_rejected(result, facts):
    result["sections"][0]["stroke_ids"] = ["zzz"]
    assert code_of(result, facts) == "unknown_id"


def test_stale_scene_hash_rejected(result, facts):
    result["scene_sha1"] = "2" * 40
    assert code_of(result, facts) == "stale_scene"


def test_three_paragraphs_rejected_for_ok_card(result, facts):
    result["slides"][0]["card"]["paragraphs"].append("third")
    assert code_of(result, facts) == "bad_card"


def test_needs_review_may_have_no_paragraphs(result, facts):
    assert result["slides"][1]["card"]["paragraphs"] == []
    validate_result(result, facts)


@pytest.mark.parametrize("text", ["## Agent output", "# Markdown Images",
                                  "<!-- excalidraw-markdown-image:abc -->"])
def test_marker_text_rejected_everywhere(result, facts, text):
    r = copy.deepcopy(result)
    r["slides"][0]["card"]["paragraphs"][0] = "before " + text + " after"
    assert code_of(r, facts) == "forbidden_text"
    r = copy.deepcopy(result)
    r["sections"][0]["transcription"] = text
    assert code_of(r, facts) == "forbidden_text"


def test_latex_unicode_and_crlf_roundtrip_unchanged(result, facts, tmp_path):
    tricky = "Let $" + chr(92) + "hat" + chr(92) + "beta$ é ∑\r\nnext line"
    result["slides"][0]["card"]["paragraphs"][0] = tricky
    validate_result(result, facts)
    path = tmp_path / "r.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    back = json.loads(path.read_text(encoding="utf-8"))
    assert back["slides"][0]["card"]["paragraphs"][0] == tricky
    resolved = resolve_result(back, facts)
    assert resolved["slides"][0]["card"]["paragraphs"][0] == tricky


def test_resolve_assigns_fallback_only_with_clear_margin(result, facts):
    resolved = resolve_result(result, facts)
    s1 = next(s for s in resolved["slides"] if s["slide_id"] == "s1")
    fb = [i for i in s1["ink"] if i["disposition"] == "fallback_nearest"]
    assert [i["stroke_ids"] for i in fb] == [["k3"]]
    assert all(sec["section_id"] != "sec1" for sec in resolved["sections"])


def test_resolve_ambiguous_ink_becomes_anchored_section_with_also_near(result, facts):
    k3 = next(s for s in facts["strokes"] if s["id"] == "k3")
    k3["y"] = 850  # between the two slides: no clear nearest
    facts["regions"][1]["bounds"] = {"x": 1000, "y": 850, "w": 20, "h": 20}
    resolved = resolve_result(result, facts)
    sec = next(s for s in resolved["sections"] if s["section_id"] == "sec1")
    assert sec["kind"] == "anchored" and sec["anchor_slide_id"] == "s2"
    assert sec["also_near"] == "s1"


def test_resolve_marks_far_ink_standalone(result, facts):
    resolved = resolve_result(result, facts)
    sec = next(s for s in resolved["sections"] if s["section_id"] == "sec2")
    assert sec["kind"] == "standalone" and sec["anchor_slide_id"] is None
    assert sec["seq"] == 1


def test_resolve_omitted_ink_is_not_dropped(result, facts):
    result["sections"] = [s for s in result["sections"] if s["section_id"] != "sec2"]
    resolved = resolve_result(result, facts)
    omitted = next(s for s in resolved["sections"] if s["stroke_ids"] == ["k4"])
    assert omitted["legibility"] == "unreadable" and omitted["omitted_by_agent"] is True


def test_resolve_coverage_equation_holds(result, facts):
    resolved = resolve_result(result, facts)
    c = resolved["coverage"]
    assert (c["assigned"], c["fallback_nearest"], c["section"]) == (2, 1, 1)
    assert c["assigned"] + c["fallback_nearest"] + c["section"] == len(facts["strokes"])
