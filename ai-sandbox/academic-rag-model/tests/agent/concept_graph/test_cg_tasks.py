import pytest

from agent.concept_graph.sources import Passage
from agent.concept_graph.tasks import ResultError, Task, extract_result, render_card


def make_task():
    return Task(
        id="fill-partial-order", stage="fill", subject={"node": "partial-order"},
        instructions="Write in your own words.", context="Node: Partial order (object)",
        passages=[Passage(id="P1", source="rubinstein", ref="ch. 2, p. 12", text="A preorder that is antisymmetric.", path="x"),
                  Passage(id="P2", source="mwg", ref="ch. 1", text="Another passage.", path="y")],
    )


def filled(card, yaml_text):
    return card.replace("```yaml\n```", "```yaml\n" + yaml_text + "\n```")


def test_card_has_the_expected_sections_and_offered_passages():
    card = render_card(make_task())
    for part in ("# Task fill-partial-order", "## Instructions", "## Subject", "## Offered passages",
                 "### P1  [source: rubinstein | ref: ch. 2, p. 12]", "A preorder that is antisymmetric.", "## Result"):
        assert part in card
    assert card.rstrip().endswith("```")


def test_card_round_trips_the_agents_yaml():
    card = filled(render_card(make_task()), "gist: Short.\nexplanation: |\n  Two lines\n  here.\ncitations:\n  - {source: mwg, ref: ch. 1}")
    got = extract_result(card)
    assert got["gist"] == "Short." and got["explanation"] == "Two lines\nhere.\n"
    assert got["citations"] == [{"source": "mwg", "ref": "ch. 1"}]


def test_empty_result_block_is_none():
    assert extract_result(render_card(make_task())) is None
    assert extract_result(filled(render_card(make_task()), "# nothing yet\n")) is None


def test_malformed_yaml_gives_a_readable_reason():
    with pytest.raises(ResultError, match="YAML"):
        extract_result(filled(render_card(make_task()), "gist: [unclosed"))


def test_a_list_instead_of_a_mapping_is_an_error():
    with pytest.raises(ResultError, match="mapping"):
        extract_result(filled(render_card(make_task()), "- a\n- b"))


def test_extra_prose_outside_the_fence_is_ignored():
    card = filled(render_card(make_task()), "gist: Short.")
    card = card.replace("## Result", "## Result\nHere is my answer:") + "\nThanks!\n"
    assert extract_result(card) == {"gist": "Short."}


def test_two_fences_is_an_error_and_no_fence_is_an_error():
    card = filled(render_card(make_task()), "gist: A") + "\n```yaml\ngist: B\n```\n"
    with pytest.raises(ResultError, match="one"):
        extract_result(card)
    with pytest.raises(ResultError, match="block"):
        extract_result("# Task x\n## Result\nI could not do it.\n")


def test_passage_text_that_mentions_a_fence_does_not_confuse_the_result():
    task = make_task()
    task.passages[0] = Passage(id="P1", source="mwg", ref="ch. 1", text="Use ```yaml fences like this```.", path="x")
    card = filled(render_card(task), "gist: Fine.")
    assert extract_result(card) == {"gist": "Fine."}
