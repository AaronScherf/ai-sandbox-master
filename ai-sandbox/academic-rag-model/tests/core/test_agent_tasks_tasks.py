import pytest

from core.agent_tasks.tasks import (
    Passage, ResultError, Task, extract_result, parse_result_text, render_card, result_from_response,
)


def _task(**kw):
    base = dict(id="t-1", stage="demo", subject={"k": "v"}, instructions="Do it.", context="Ctx.",
                passages=[Passage(id="P1", source="paper", ref="p. 3", text="Body.")])
    base.update(kw)
    return Task(**base)


def test_card_without_attachments_has_no_attachments_section():
    assert "## Attachments" not in render_card(_task())


def test_attachments_section_sits_just_before_result():
    card = render_card(_task(attachments=["pages/p4.png", "pages/p5.png"]))
    assert card.index("## Offered passages") < card.index("## Attachments") < card.index("## Result")
    assert "- `pages/p4.png`" in card and "- `pages/p5.png`" in card


def test_non_ascii_text_round_trips_in_the_card():
    card = render_card(_task(context="Élasticité β = 0.5 — “quoted”"))
    assert "Élasticité β = 0.5 — “quoted”" in card


def test_extract_result_reads_the_fenced_mapping():
    card = render_card(_task()).replace("```yaml\n```", "```yaml\nvalue: 1\nnote: \"a: b\"\n```")
    assert extract_result(card) == {"value": 1, "note": "a: b"}


def test_empty_block_is_none_and_missing_heading_raises():
    assert extract_result(render_card(_task())) is None
    with pytest.raises(ResultError, match="no '## Result' heading"):
        extract_result("nothing here")


def test_dates_come_back_as_text():
    assert parse_result_text("when: 2026-09-10\n") == {"when": "2026-09-10"}


def test_result_from_response_prefers_the_fence():
    assert result_from_response("sure\n```yaml\na: 1\n```\nthanks") == {"a": 1}
    assert result_from_response("a: 2") == {"a": 2}
