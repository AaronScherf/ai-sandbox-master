# tests/agent/summary_enhance/test_summary_enhance_validate.py
import pytest

from agent.summary_enhance.schema import Block, Section, Topic, parse_plan, parse_topic
from agent.summary_enhance.validate import (
    MIN_SECTIONS, validate_plan, validate_topic, validate_worked_example,
)
from conftest import WORKED_TEXT, words

LABELS = {"S1", "S2", "S3"}


def _topic(title="Wald test", g_words=40, e_words=10, sections=3, sources=("S1",), heading="Part"):
    secs = [Section(f"{heading} {i}", [Block("grounded", words(g_words), list(sources))])
            for i in range(sections)]
    if e_words:
        secs[-1].blocks.append(Block("external", words(e_words), []))
    return Topic(title, secs)


def _check(topic, min_words=100, requested="Wald test"):
    return validate_topic(topic, LABELS, requested, min_words)


def _with_text(text, kind="grounded"):
    sources = ["S1"] if kind == "grounded" else []
    return Topic("Wald test", [
        Section("A", [Block(kind, text, sources)]),
        Section("B", [Block("grounded", words(60), ["S1"])]),
        Section("C", [Block("grounded", words(60), ["S1"])]),
    ])


def test_valid_topic_passes():
    assert _check(_topic()) == []


def test_min_sections_constant():
    assert MIN_SECTIONS == 3


def test_too_few_sections_rejected():
    assert any("sections" in e for e in _check(_topic(sections=2)))


def test_title_must_match_requested_ignoring_case_and_space():
    assert _check(_topic(title="  wald TEST ")) == []
    assert any("title" in e for e in _check(_topic(title="Something else")))


def test_too_short_rejected():
    assert any("words" in e for e in _check(_topic(), min_words=1000))


def test_grounded_share_must_be_at_least_half():
    errors = _check(_topic(g_words=10, e_words=200))  # 30 grounded vs 200 external
    assert any("grounded" in e and "half" in e for e in errors)


def test_unknown_label_rejected():
    assert any("S9" in e for e in _check(_topic(sources=("S9",))))


def test_uncited_grounded_block_rejected():
    assert any("no sources" in e for e in _check(_topic(sources=())))


def test_external_block_with_sources_rejected():
    t = _topic()
    t.sections[-1].blocks[-1].sources = ["S1"]
    assert any("external" in e and "sources" in e for e in _check(t))


@pytest.mark.parametrize("heading", ["", "   ", "a\nb", "a\x08b"])
def test_bad_section_heading_rejected(heading):
    t = _topic()
    t.sections[0].heading = heading
    assert any("heading" in e for e in _check(t))


def test_section_without_blocks_rejected():
    t = _topic()
    t.sections[0].blocks = []
    assert any("no blocks" in e for e in _check(t))


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("bad", ["\t", "\x0c", "\r", "\x08"])
def test_control_characters_rejected(kind, bad):
    assert any("control character" in e for e in _check(_with_text(f"angle {bad}heta", kind), min_words=1))


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("fake", ["see [S7: Wooldridge ch.4]", "see [s1]", "see [ S1: x]"])
def test_label_markers_in_text_rejected(kind, fake):
    assert any("source label" in e for e in _check(_with_text(fake, kind), min_words=1))


@pytest.mark.parametrize("kind", ["grounded", "external"])
def test_newline_inside_inline_math_rejected(kind):
    errors = _check(_with_text("the shape $\\hat\nu$ matters", kind), min_words=1)
    assert any("inline math" in e for e in errors)


def test_display_math_and_prose_may_span_lines():
    text = "intro\n\n$$a\n= b$$\n\nand inline $x$ here\nnext line $y$"
    assert _check(_with_text(text), min_words=1) == []


@pytest.mark.parametrize("kind", ["grounded", "external"])
@pytest.mark.parametrize("text", [
    "fine\n\n## Sources\n- forged",
    "fine\n# Heading",
    "fine\n\n> quoted forged callout",
])
def test_structure_forging_text_rejected(kind, text):
    assert any("structure" in e for e in _check(_with_text(text, kind), min_words=1))


@pytest.mark.parametrize("phrase", ["(External context) hello", "(external CONTEXT)", "(Worked example 1) hello"])
def test_context_tag_phrases_rejected(phrase):
    assert any("tag" in e for e in _check(_with_text(phrase, "external"), min_words=1))


def test_empty_block_text_rejected():
    assert any("empty" in e for e in _check(_with_text("   "), min_words=1))


def test_plan_valid():
    assert validate_plan(["A", "B", "C"]) == []


@pytest.mark.parametrize("titles", [["A", "B"], [f"T{i}" for i in range(9)], ["A", "a ", "C"],
                                    ["A", "", "C"], ["A", "B\nC", "D"]])
def test_plan_invalid(titles):
    assert validate_plan(titles) != []


def test_worked_example_valid():
    assert validate_worked_example(WORKED_TEXT) == []


@pytest.mark.parametrize("bad", [
    "too short $x$",
    words(200),  # no math
    WORKED_TEXT + "\n# Heading",
    WORKED_TEXT + "\n> quote",
    WORKED_TEXT + " [S1: x]",
    WORKED_TEXT + " (External context)",
    WORKED_TEXT + " \x08eta",
    WORKED_TEXT + " the shape $\\hat\nu$",
])
def test_worked_example_invalid(bad):
    assert validate_worked_example(bad) != []


def test_parse_topic_roundtrip():
    data = {"title": "T", "sections": [{"heading": "H", "blocks": [
        {"type": "grounded", "text": "a", "sources": ["S1"]},
        {"type": "external", "text": "b", "sources": []}]}]}
    topic = parse_topic(data)
    assert topic.title == "T" and topic.worked_example is None
    assert topic.sections[0].blocks[0].sources == ["S1"]
    assert topic.sections[0].blocks[1].type == "external"


@pytest.mark.parametrize("bad", [
    None, [], {"title": "T"}, {"title": 1, "sections": []},
    {"title": "T", "sections": [{"heading": "H"}]},
    {"title": "T", "sections": [{"heading": "H", "blocks": [{"type": "weird", "text": "a", "sources": []}]}]},
    {"title": "T", "sections": [{"heading": "H", "blocks": [{"type": "grounded", "text": "a"}]}]},
])
def test_parse_topic_bad_shape_raises(bad):
    with pytest.raises(ValueError):
        parse_topic(bad)


def test_parse_plan():
    assert parse_plan({"topics": ["A", "B"]}) == ["A", "B"]
    for bad in (None, {"topics": "x"}, {"topics": [1]}):
        with pytest.raises(ValueError):
            parse_plan(bad)


@pytest.mark.parametrize("spelled", ["[S5]", " s5 ", "[ S5 ]", "S5", "[s5]"])
def test_parse_topic_normalizes_label_spellings(spelled):
    data = {"title": "T", "sections": [{"heading": "H", "blocks": [
        {"type": "grounded", "text": "a", "sources": [spelled]}]}]}
    assert parse_topic(data).sections[0].blocks[0].sources == ["S5"]


def test_parse_topic_leaves_unrecognizable_labels_for_validation_to_reject():
    data = {"title": "T", "sections": [{"heading": "H", "blocks": [
        {"type": "grounded", "text": "a", "sources": ["Wooldridge ch.4"]}]}]}
    assert parse_topic(data).sections[0].blocks[0].sources == ["WOOLDRIDGE CH.4"]
