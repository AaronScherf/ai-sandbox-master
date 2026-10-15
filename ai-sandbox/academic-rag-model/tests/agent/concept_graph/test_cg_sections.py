import pytest

from agent.concept_graph.schema import Graph, Node, Section, Vocab, member_hash
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample


def graph(topic_of_section=None, node_topic="t1"):
    sec = Section(id="s1", title="One", order=1, state="taught", topic=topic_of_section, short="One")
    n = Node(id="a", name="A", kind="object", section="s1", topic=node_topic, explanation="x")
    return Graph(sections=[sec], nodes=[n], edges=[], rejected=[], vocab=Vocab(kinds=["object"], topics=["t1", "t2"]))


def test_member_hash_ignores_order_and_changes_with_membership():
    assert member_hash(["b", "a"]) == member_hash(["a", "b"])
    assert member_hash(["a"]) != member_hash(["a", "b"])
    assert len(member_hash(["a"])) == 16


def test_a_section_without_a_topic_does_not_constrain_its_concepts():
    assert not [i for i in validate(graph(None, "t2")) if i.code == "topic-mismatch"]


def test_a_concept_whose_topic_differs_from_its_section_is_an_error():
    found = [i for i in errors(validate(graph("t1", "t2"))) if i.code == "topic-mismatch"]
    assert len(found) == 1 and "a" in found[0].message


def test_missing_and_stale_summaries_are_warnings_not_errors():
    g = graph("t1", "t1")
    codes = {i.code for i in validate(g)}
    assert "missing-summary" in codes
    g.sections[0].summary = "A short summary."
    g.sections[0].summary_hash = "0" * 16
    assert "stale-summary" in {i.code for i in validate(g)}
    g.sections[0].summary_hash = member_hash(["a"])
    assert not {"missing-summary", "stale-summary"} & {i.code for i in validate(g)}
    assert errors(validate(g)) == []


def test_update_section_changes_only_that_section(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    first = store.read_all().sections[0].id
    store.update_section(first, {"summary": "Hello.", "summary_hash": "abc"})
    after = {s.id: s for s in store.read_all().sections}
    assert after[first].summary == "Hello." and after[first].summary_hash == "abc"
    assert all(s.summary is None for sid, s in after.items() if sid != first)
    with pytest.raises(KeyError):
        store.update_section("nope", {"summary": "x"})
