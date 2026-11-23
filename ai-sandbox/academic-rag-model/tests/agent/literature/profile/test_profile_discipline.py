from agent.literature.profile.discipline import field_from_topics, resolve_discipline
from agent.literature.profile.taxonomy import load_openalex

TAX = load_openalex()
ECON = next(i for i, label in TAX.fields.items() if label.startswith("Economics"))
BUS = next(i for i, label in TAX.fields.items() if label.startswith("Business"))
MED = next(i for i, label in TAX.fields.items() if label == "Medicine")


def _topics(*pairs):
    return [{"id": f"T{n}", "name": "t", "score": s, "field_id": f, "subfield_id": None, "domain_id": None}
            for n, (f, s) in enumerate(pairs)]


def _llm(field_id, conf=0.9):
    return {"discipline": TAX.fields[field_id], "discipline_confidence": conf}


def test_field_from_topics_sums_scores_per_field_and_normalises():
    field, share = field_from_topics(_topics((ECON, 0.9), (ECON, 0.7), (BUS, 0.4)))
    assert field == ECON and round(share, 2) == 0.8


def test_field_from_topics_empty_or_fieldless():
    assert field_from_topics(None) == (None, 0.0)
    assert field_from_topics(_topics((None, 0.9))) == (None, 0.0)


def test_agreement_above_threshold_no_review():
    out = resolve_discipline(_llm(ECON, 0.95), _llm(ECON), None)
    assert out["discipline"] == TAX.fields[ECON] and out["needs_review"] is False
    assert out["discipline_source"] == "llm"


def test_low_agent_confidence_is_recorded_as_a_mixed_fit_not_a_review_item():
    out = resolve_discipline(_llm(ECON, 0.5), _llm(BUS, 0.5), None)
    assert out["needs_review"] is False and out["discipline_fit"] == "mixed"


def test_disagreeing_agents_give_a_secondary_discipline_and_no_review_item():
    out = resolve_discipline(_llm(ECON), _llm(MED), None)
    assert out["discipline"] == TAX.fields[ECON] and out["secondary_discipline"] == TAX.fields[MED]
    assert out["discipline_fit"] == "mixed" and out["needs_review"] is False


def test_agreement_is_a_clear_fit_with_no_secondary_from_the_agents():
    out = resolve_discipline(_llm(ECON, 0.95), _llm(ECON, 0.95), None)
    assert out["discipline_fit"] == "clear" and out["secondary_discipline"] is None


def test_secondary_is_the_runner_up_of_the_pooled_evidence_even_for_a_clear_paper():
    out = resolve_discipline(_llm(ECON, 0.95), _llm(ECON, 0.95), _topics((ECON, 0.9), (BUS, 0.1)))
    assert out["secondary_discipline"] == TAX.fields[BUS] and out["discipline_fit"] == "clear"
    assert 0 < out["secondary_score"] < out["discipline_scores"][0]["score"]


def test_openalex_primary_stays_but_agents_agreeing_against_it_make_the_fit_mixed():
    out = resolve_discipline(_llm(ECON), _llm(ECON), _topics((BUS, 0.9), (ECON, 0.05)))
    assert out["discipline"] == TAX.fields[BUS] and out["discipline_source"] == "openalex"
    assert out["secondary_discipline"] == TAX.fields[ECON] and out["discipline_fit"] == "mixed"


def test_weak_topics_pool_with_the_agents_to_pick_the_primary():
    out = resolve_discipline(_llm(BUS), _llm(ECON), _topics((ECON, 0.7), (BUS, 0.3)))
    assert out["discipline"] == TAX.fields[ECON] and out["secondary_discipline"] == TAX.fields[BUS]


def test_topics_used_when_strong_else_llm():
    strong = resolve_discipline(_llm(BUS), _llm(ECON), _topics((ECON, 0.95), (BUS, 0.05)))
    assert strong["discipline"] == TAX.fields[ECON] and strong["discipline_source"] == "openalex"
    weak = resolve_discipline(_llm(BUS), _llm(BUS), _topics((ECON, 0.5), (BUS, 0.5)))
    assert weak["discipline"] == TAX.fields[BUS] and weak["discipline_source"] == "llm"


def test_no_check_result_needs_review():
    out = resolve_discipline(_llm(ECON), None, None)
    assert out["needs_review"] is True and "second" in out["reason"]
    assert out["secondary_discipline"] is None


def test_other_is_a_valid_discipline():
    out = resolve_discipline({"discipline": "other", "discipline_confidence": 0.9},
                             {"discipline": "other", "discipline_confidence": 0.9}, None)
    assert out["discipline"] == "other" and out["needs_review"] is False


def test_subfields_from_topics_scored_within_chosen_field():
    from agent.literature.profile.discipline import subfields_from_topics
    sub_a = next(i for i, f in TAX._subfield_field.items() if f == ECON)
    sub_b = next(i for i, f in TAX._subfield_field.items() if f == BUS)
    topics = [{"id": "T1", "score": 0.9, "field_id": ECON, "subfield_id": sub_a},
              {"id": "T2", "score": 0.3, "field_id": BUS, "subfield_id": sub_b}]
    out = subfields_from_topics(topics, ECON)
    assert [s["id"] for s in out] == [sub_a] and out[0]["source"] == "openalex"
    assert out[0]["label"] == TAX.subfields[sub_a] and 0 < out[0]["score"] <= 1
