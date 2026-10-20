import pytest
from pydantic import ValidationError

from agent.concept_graph.schema import (
    EDGE_TYPES,
    Edge,
    Node,
    Section,
    edge_id,
    field_hash,
)


def test_edge_id_is_canonical():
    assert edge_id("total-order", "is_a", "partial-order") == "total-order--is_a--partial-order"


def test_field_hash_ignores_surrounding_whitespace_and_none():
    assert field_hash("  hello\n") == field_hash("hello")
    assert field_hash(None) == field_hash("")
    assert len(field_hash("x")) == 16


def test_node_rejects_unknown_fields_and_bad_slug():
    with pytest.raises(ValidationError):
        Node(id="Bad Id", name="x", kind="object", section="s", topic="t")
    with pytest.raises(ValidationError):
        Node(id="ok", name="x", kind="object", section="s", topic="t", colour="red")


def test_node_defaults_to_proposed_with_empty_prose():
    n = Node(id="ok", name="Ok", kind="object", section="s", topic="t")
    assert n.status == "proposed"
    assert n.explanation == ""
    assert n.citations == []
    assert n.critic is None


def test_section_state_is_restricted():
    with pytest.raises(ValidationError):
        Section(id="s1", title="T", order=1, state="done")


def test_edge_requires_slug_endpoints():
    with pytest.raises(ValidationError):
        Edge(id="x", source="Not Slug", type="is_a", target="b")
    e = Edge(id="a--is_a--b", source="a", type="is_a", target="b")
    assert e.condition is None and e.via is None and e.status == "proposed"


def test_edge_types_include_method_relations_without_dropping_logical_types():
    assert len(EDGE_TYPES) == 14
    expected = {"component_of", "implies", "iff", "uses", "applies_to", "estimates", "computed_from", "variant_of"}
    assert expected <= set(EDGE_TYPES)
