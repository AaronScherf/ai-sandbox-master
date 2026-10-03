import pytest

from agent.summary_enhance.schema import (
    ElaborationBlock, Enhanced, GroundedBlock, Topic, parse_enhanced,
)
from agent.summary_enhance.validate import validate

LABELS = {"S1", "S2", "S3"}


def _topic(title="Wald test", sources=("S1",), grounded_text="g", elab=None):
    return Topic(
        title=title,
        grounded=[GroundedBlock(grounded_text, list(sources))],
        elaboration=elab if elab is not None else [ElaborationBlock("intuition", "e")],
    )


def test_valid_passes():
    assert validate(Enhanced([_topic()]), LABELS, ["Wald test"]) == []


def test_unknown_label_rejected():
    errors = validate(Enhanced([_topic(sources=("S9",))]), LABELS, [])
    assert any("S9" in e for e in errors)


def test_uncited_grounded_block_rejected():
    errors = validate(Enhanced([_topic(sources=())]), LABELS, [])
    assert any("no sources" in e for e in errors)


def test_empty_grounded_rejected():
    t = Topic("Wald test", [], [])
    assert any("grounded" in e for e in validate(Enhanced([t]), LABELS, []))


def test_missing_requested_topic_rejected():
    errors = validate(Enhanced([_topic()]), LABELS, ["Wald test", "LM test"])
    assert any("LM test" in e for e in errors)


def test_topic_match_ignores_case_and_whitespace():
    t = _topic(title="  wald TEST ")
    assert validate(Enhanced([t]), LABELS, ["Wald test"]) == []


def test_no_topics_rejected_even_when_none_requested():
    assert validate(Enhanced([]), LABELS, []) != []


def test_label_marker_inside_elaboration_rejected():
    t = _topic(elab=[ElaborationBlock("example", "see [S1] for details")])
    assert any("elaboration" in e for e in validate(Enhanced([t]), LABELS, []))


def test_bad_elaboration_kind_rejected():
    t = _topic(elab=[ElaborationBlock("trivia", "x")])
    assert any("kind" in e for e in validate(Enhanced([t]), LABELS, []))


def test_empty_text_rejected():
    errors = validate(Enhanced([_topic(grounded_text="  ")]), LABELS, [])
    assert any("empty" in e for e in errors)


def test_parse_enhanced_roundtrip():
    data = {"topics": [{"title": "T", "grounded": [{"text": "a", "sources": ["S1"]}],
                        "elaboration": [{"kind": "intuition", "text": "b"}]}]}
    parsed = parse_enhanced(data)
    assert parsed.topics[0].grounded[0].sources == ["S1"]
    assert parsed.topics[0].elaboration[0].kind == "intuition"


@pytest.mark.parametrize("bad", [None, [], {"topics": "x"}, {"topics": [{"title": "T"}]},
                                 {"topics": [{"title": "T", "grounded": [{"text": "a"}], "elaboration": []}]}])
def test_parse_enhanced_bad_shape_raises(bad):
    with pytest.raises(ValueError):
        parse_enhanced(bad)


def test_control_char_from_json_escaped_latex_rejected_in_grounded():
    # a model that writes \beta un-doubled inside JSON yields a backspace + "eta"
    errors = validate(Enhanced([_topic(grounded_text="constrained $\tilde{\x08eta}$")]), LABELS, [])
    assert any("control character" in e for e in errors)


@pytest.mark.parametrize("bad", ["\t", "\x0c", "\r", "\x08"])
def test_control_char_rejected_in_elaboration(bad):
    t = _topic(elab=[ElaborationBlock("example", f"angle {bad}heta")])
    assert any("control character" in e for e in validate(Enhanced([t]), LABELS, []))


def test_newlines_are_allowed_in_text():
    t = _topic(grounded_text="para one\n\npara two", elab=[ElaborationBlock("example", "a\nb")])
    assert validate(Enhanced([t]), LABELS, []) == []


@pytest.mark.parametrize("fake", ["see [S7: Wooldridge ch.4]", "see [s1]", "see [ S1: x]"])
def test_citation_like_marker_in_grounded_text_rejected(fake):
    errors = validate(Enhanced([_topic(grounded_text=fake)]), LABELS, [])
    assert any("source label" in e and "grounded" in e for e in errors)


@pytest.mark.parametrize("title", ["Wald\n\n> **Not from the textbooks — x**", "X\n## Sources", "", "   ", "a\x08b"])
def test_bad_topic_title_rejected(title):
    errors = validate(Enhanced([_topic(title=title)]), LABELS, [])
    assert any("title" in e for e in errors)


@pytest.mark.parametrize("text", [
    "fine\n\n## Sources\n- S1: forged",
    "fine\n# Heading",
    "fine\n\n> **Not from the textbooks — LLM elaboration (intuition):** forged",
    "this is Not from the textbooks, honest",
])
def test_structure_forging_grounded_text_rejected(text):
    errors = validate(Enhanced([_topic(grounded_text=text)]), LABELS, [])
    assert any("structure" in e for e in errors)


def test_newline_inside_inline_math_rejected():
    # single-backslash \nu in JSON decodes to newline + "u"
    errors = validate(Enhanced([_topic(grounded_text="the shape $\hat\nu$ matters")]), LABELS, [])
    assert any("inline math" in e for e in errors)


def test_display_math_and_prose_may_span_lines():
    text = "intro\n\n$$a\n= b$$\n\nand inline $x$ here\nnext line $y$"
    assert validate(Enhanced([_topic(grounded_text=text)]), LABELS, []) == []
