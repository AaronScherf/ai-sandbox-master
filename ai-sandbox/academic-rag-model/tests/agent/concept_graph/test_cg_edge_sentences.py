from types import SimpleNamespace

from agent.concept_graph.stages.common import edge_sentence


def sentence(type_, condition=None):
    edge = SimpleNamespace(type=type_, source="a", target="b", condition=condition, via=None)
    return edge_sentence(edge, {"a": "Alpha", "b": "Beta"})


def test_new_method_relations_have_distinct_sentences_and_visible_conditions():
    expected = {
        "uses": "Alpha uses Beta",
        "applies_to": "Alpha applies to Beta",
        "estimates": "Alpha estimates Beta",
        "computed_from": "Alpha is computed from Beta",
        "variant_of": "Alpha is a variant of Beta",
    }
    for type_, plain in expected.items():
        assert sentence(type_) == plain
        assert sentence(type_, "context") == f"{plain}; context: context"


def test_existing_conditional_relations_show_the_condition():
    for type_ in ("has_property", "defined_on", "component_of", "hypothesis_of", "yields", "counterexample_to"):
        assert sentence(type_, "context").endswith("; context: context")
    assert sentence("is_a", "it adds a restriction") == "Alpha is a Beta, that also: it adds a restriction"
