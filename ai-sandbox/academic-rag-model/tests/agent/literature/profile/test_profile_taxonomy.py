from agent.literature.profile.taxonomy import ancestors, load_openalex, rollup
from agent.literature.vocab import Term, Vocabulary


def _vocab():
    terms = {
        "intervention.health": Term("intervention.health", "Health"),
        "intervention.health.nutrition": Term("intervention.health.nutrition", "Nutrition", parent="intervention.health"),
        "intervention.health.nutrition.supplement": Term(
            "intervention.health.nutrition.supplement", "Supplement", parent="intervention.health.nutrition"),
    }
    return Vocabulary("intervention", 1, "3ie", "test", terms)


def test_openalex_has_26_fields_and_4_domains():
    tax = load_openalex()
    assert len(tax.fields) == 26
    assert len(tax.domains) == 4


def test_every_field_maps_to_one_domain():
    tax = load_openalex()
    for field_id in tax.fields:
        assert tax.field_domain(field_id) in tax.domains


def test_every_subfield_maps_to_a_field():
    tax = load_openalex()
    assert len(tax.subfields) > 200
    for sub_id in tax.subfields:
        assert tax.subfield_field(sub_id) in tax.fields


def test_ancestors_of_leaf_is_branch_then_sector():
    assert ancestors(_vocab(), "intervention.health.nutrition.supplement") == [
        "intervention.health.nutrition", "intervention.health"]


def test_rollup_includes_ancestors_but_branch_does_not_imply_leaf():
    v = _vocab()
    assert rollup(v, ["intervention.health.nutrition"]) == {"intervention.health.nutrition", "intervention.health"}
    assert "intervention.health.nutrition.supplement" not in rollup(v, ["intervention.health.nutrition"])
    assert rollup(v, ["intervention.health.nutrition.supplement"]) == {
        "intervention.health.nutrition.supplement", "intervention.health.nutrition", "intervention.health"}
