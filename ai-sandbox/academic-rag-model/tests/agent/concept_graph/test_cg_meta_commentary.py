"""Drafted prose must teach the concept, not comment on the sources it was drafted from."""
import pytest

from agent.concept_graph.ipguard import check_meta
from agent.concept_graph.stages import fill, link
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, blank_explanations, copy_sample, entry_for

CITE = [{"source": "rubinstein", "ref": "ch. 2, p. 12"}]
GOOD = {"gist": "A relation that ranks things without forbidding ties.",
        "explanation": "Two properties define it, so every element relates to itself and comparisons chain together.",
        "citations": CITE}


@pytest.mark.parametrize("sentence", [
    "The offered passages do not explicitly define the term transitive closure, focusing instead on binary relations.",
    "The provided sources only mention this in passing.",
    "These passages focus on the definition of transitivity.",
    "The excerpt does not state the condition.",
    "According to the passages, the relation must be complete.",
    "This is not explicitly defined in the lecture notes.",
    "The slides do not cover the converse.",
])
def test_commentary_about_the_sources_is_flagged(sentence):
    problems = check_meta({"explanation": sentence})
    assert len(problems) == 1 and problems[0].startswith("explanation") and "sources" in problems[0]


@pytest.mark.parametrize("sentence", [
    "A transitive closure adds every pair reachable through a chain of related elements.",
    "The passage of time does not change a fixed preference relation.",
    "Choice sets are drawn from a finite source of alternatives.",
    "If the budget set is empty there is nothing to choose, so demand is undefined.",
    "A consumer who has the lecture's example in mind still needs completeness to rank every pair.",
])
def test_ordinary_teaching_prose_is_not_flagged(sentence):
    assert check_meta({"explanation": sentence}) == []


def test_empty_fields_are_ignored():
    assert check_meta({"gist": "", "example": None}) == []


def test_fill_bounces_commentary_in_gist_explanation_and_example(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder"])
    entry = entry_for(fill.make_tasks(store, FakeRetriever(), nodes=["preorder"])[0])
    bad = dict(GOOD, explanation="The offered passages do not define this, so only the idea is described.",
               example="The provided sources give no example.")
    msgs = fill.validate_result(entry, bad, store)
    assert any(m.startswith("explanation") for m in msgs) and any(m.startswith("example") for m in msgs)


def test_fill_instructions_forbid_talking_about_the_sources():
    text = fill.INSTRUCTIONS.lower()
    assert "never mention" in text and "passages" in text


def test_link_bounces_commentary_in_an_edge_explanation(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    task = link.make_tasks(store, FakeRetriever(), nodes=["preorder"], redo=True)[0]
    entry = entry_for(task)
    edge = {"source": "preorder", "type": "defined_on", "target": "set", "citations": CITE,
            "explanation": "The offered passages do not state this directly, but it follows from the definition."}
    assert any("sources" in m for m in link.validate_result(entry, {"edges": [edge]}, store))
