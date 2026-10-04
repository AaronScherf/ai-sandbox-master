import pytest

from agent.summary_enhance.schema import parse_topic
from agent.summary_enhance.validate import validate_topic
from conftest import words


def _parse(text, kind="grounded"):
    sources = ["S1"] if kind == "grounded" else []
    data = {"title": "T", "sections": [{"heading": "H", "blocks": [
        {"type": kind, "text": text, "sources": sources}]}]}
    return parse_topic(data).sections[0].blocks[0].text


# json.loads turns a single-backslash LaTeX command into a control character plus the rest
# of the word. Python escapes below build exactly what json.loads would have produced.
@pytest.mark.parametrize("decoded,expected", [
    ("constrained $\\tilde{\x08eta}$", "constrained $\\tilde{\\beta}$"),    # \b -> backspace
    ("\x0crac{a}{b}", "\\frac{a}{b}"),                                      # \f -> form feed
    ("angle \theta here", "angle \\theta here"),                            # \t -> tab + "heta"
    ("rank \rho here", "rank \\rho here"),                                  # \r -> CR + "ho"
    ("x\x08", "x\\b"),                                                      # backspace at the end
])
def test_decoded_escape_corruption_is_repaired(decoded, expected):
    assert _parse(decoded) == expected
    assert _parse(decoded, kind="external") == expected


def test_tab_before_a_non_letter_is_left_alone():
    assert _parse("a\t b") == "a\t b"


def test_crlf_is_not_touched():
    assert _parse("a\r\nb") == "a\r\nb"


def test_real_newlines_are_not_touched():
    assert _parse("para one\n\npara two") == "para one\n\npara two"


def test_repaired_text_then_passes_validation():
    data = {"title": "T", "sections": [
        {"heading": f"H{i}", "blocks": [{"type": "grounded", "sources": ["S1"],
                                         "text": words(40) + " $\\hat{\x08eta}$"}]}
        for i in range(3)]}
    topic = parse_topic(data)
    assert validate_topic(topic, {"S1"}, "T", 100) == []


def test_unrepairable_control_characters_are_still_rejected():
    data = {"title": "T", "sections": [
        {"heading": f"H{i}", "blocks": [{"type": "grounded", "sources": ["S1"],
                                         "text": words(40) + (" bad\x01char" if i == 0 else "")}]}
        for i in range(3)]}
    errors = validate_topic(parse_topic(data), {"S1"}, "T", 100)
    assert any("control character" in e for e in errors)
