"""Problems found in the first real fill run: YAML dates, colons in refs, unhelpful YAML errors, cut-off sentences."""
import datetime

import pytest
import yaml

from agent.concept_graph.sources import classify_passage
from agent.concept_graph.stages import fill
from agent.concept_graph.store import GraphStore
from agent.concept_graph.tasks import ResultError, Task, extract_result, render_card
from cg_helpers import FakeRetriever, blank_explanations, copy_sample, entry_for

BOOK = "C:/hub/academic_notes/microecon/textbooks/processed_outputs/Rubenstein_Models_in_Microeconomic_Theory_2023/Rubenstein_Models_in_Microeconomic_Theory_2023.rag.md"
GOOD = {
    "gist": "A relation that ranks things without forbidding ties.",
    "explanation": "Two properties define it, so every element relates to itself and comparisons chain together.",
    "citations": [{"source": "rubinstein", "ref": "ch. 2, p. 12"}],
}


def filled(yaml_text):
    task = Task(id="t", stage="fill", subject={}, instructions="i", context="c", passages=[])
    return render_card(task).replace("```yaml\n```", "```yaml\n" + yaml_text + "\n```")


def test_an_unquoted_date_in_a_result_is_read_as_the_text_it_was_typed_as():
    got = extract_result(filled("citations:\n  - source: lecture\n    ref: 2026-09-10\nlectures: [2026-09-07, 2026-09-10]"))
    assert got["citations"][0]["ref"] == "2026-09-10" and isinstance(got["citations"][0]["ref"], str)
    assert got["lectures"] == ["2026-09-07", "2026-09-10"]
    assert not isinstance(got["lectures"][0], datetime.date)


def test_refs_are_safe_to_write_as_plain_yaml():
    for citation in ("§Definition 1.1: Complete binary relation, p. 23", "§Proposition: Union # note, p. 4", "§Why: because: reasons"):
        _, ref = classify_passage(BOOK, citation)
        assert ": " not in ref and " #" not in ref and not ref.endswith(":")
        assert yaml.safe_load("ref: " + ref)["ref"] == ref


def test_a_yaml_error_names_the_line_and_says_how_to_fix_it():
    with pytest.raises(ResultError) as err:
        extract_result(filled("gist: A relation: with a colon\nexplanation: fine"))
    message = str(err.value)
    assert "line 1" in message and "gist: A relation: with a colon" in message and "quote" in message.lower()


def test_instructions_tell_the_agent_how_to_quote_yaml():
    assert "double quotes" in fill.INSTRUCTIONS and "| block" in fill.INSTRUCTIONS


def one(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder"])
    task = fill.make_tasks(store, FakeRetriever(), nodes=["preorder"])[0]
    return store, entry_for(task)


def test_an_unclosed_dollar_sign_is_bounced_because_a_sentence_may_be_cut_off(tmp_path):
    store, entry = one(tmp_path)
    cut = dict(GOOD, explanation="Reflexivity holds when $x R x$ and, for identical options ($y =\nIt also serves as a base.")
    msgs = fill.validate_result(entry, cut, store)
    assert len(msgs) == 1 and "explanation" in msgs[0] and "$" in msgs[0] and "cut off" in msgs[0]


def test_balanced_math_and_escaped_dollars_are_fine(tmp_path):
    store, entry = one(tmp_path)
    ok = dict(GOOD, explanation="Holds for $x R x$ and for $$y R y$$; a price of \\$5 is not math.", example="Take $X = \\{1, 2\\}$.")
    assert fill.validate_result(entry, ok, store) == []


def test_the_gist_and_example_are_checked_too(tmp_path):
    store, entry = one(tmp_path)
    msgs = fill.validate_result(entry, dict(GOOD, gist="It is $x", example="A case with $y"), store)
    assert any(m.startswith("gist") for m in msgs) and any(m.startswith("example") for m in msgs)
