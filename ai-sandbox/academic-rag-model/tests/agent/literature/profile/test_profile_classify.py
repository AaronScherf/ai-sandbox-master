import tempfile
from pathlib import Path

import pytest

from agent.literature.profile import classify
from agent.literature.profile.taxonomy import load_openalex
from core.indexer.index_card import find_card_by_file_id, save_shard

TAX = load_openalex()
ECON = next(label for label in TAX.fields.values() if label.startswith("Economics"))
ECON_ID = next(i for i, label in TAX.fields.items() if label == ECON)
SUB = next(label for i, label in TAX.subfields.items() if TAX.subfield_field(i) == ECON_ID)
OTHER_SUB = next(label for i, label in TAX.subfields.items() if TAX.subfield_field(i) != ECON_ID)
PROV = {"driver": "agent", "agent": "gemini", "run": "r1"}


def _root(pages=5):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    md = root / "journal-articles" / "business" / "processed_outputs" / "p.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\ntags: []\n---\n" + "".join(f"\n<!-- page {n} -->\n\nText of page {n}.\n" for n in range(1, pages + 1)),
                  encoding="utf-8")
    save_shard(str(root), "business", [{"file_id": "f1", "course": "business", "title": "A Paper", "doc_type": "journal_article",
                                        "path": "journal-articles/business/processed_outputs/p.md"}])
    return tmp, root


def _result(**over):
    base = {"report_type": "journal_article", "subtype": "empirical_study", "discipline": ECON,
            "discipline_confidence": 0.9, "subfields": [SUB], "country": ["Rwanda"], "admin1": [],
            "method_class": "quantitative", "study_design": "randomized_controlled_trial",
            "orientation": "retrospective", "evidence_role": "primary_evaluation", "intervention_start_year": 2018}
    base.update(over)
    return base


def _target(root):
    return classify.Target(index_root=str(root))


def _entry(variant="a"):
    return {"subject": {"file_id": "f1", "variant": variant}}


def test_make_tasks_offers_only_first_pages_and_records_variant():
    tmp, root = _root(pages=8)
    with tmp:
        card = find_card_by_file_id(str(root), "f1")[1]
        tasks, skipped = classify.make_tasks(_target(root), [card], variant="b")
        assert skipped == {} and len(tasks) == 1
        assert [p.ref for p in tasks[0].passages] == [f"page {n}" for n in range(1, classify.CARD_PAGES + 1)]
        assert tasks[0].subject["variant"] == "b" and tasks[0].stage == classify.STAGE


def test_make_tasks_skips_already_classified_same_prompt_version():
    tmp, root = _root()
    with tmp:
        card = find_card_by_file_id(str(root), "f1")[1]
        classify.apply_result(_target(root), _entry(), _result(), PROV)
        card = find_card_by_file_id(str(root), "f1")[1]
        tasks, skipped = classify.make_tasks(_target(root), [card], variant="a")
        assert tasks == [] and "already" in skipped["f1"]


def test_validate_rejects_field_not_in_openalex_list():
    tmp, root = _root()
    with tmp:
        problems = classify.validate_result(_entry(), _result(discipline="Astrology"), _target(root))
        assert any("discipline" in p for p in problems)


def test_validate_rejects_subfield_outside_chosen_field():
    tmp, root = _root()
    with tmp:
        problems = classify.validate_result(_entry(), _result(subfields=[OTHER_SUB]), _target(root))
        assert any("subfield" in p for p in problems)


def test_validate_requires_method_fields_for_research_types_only():
    tmp, root = _root()
    with tmp:
        bare = {"report_type": "notes", "discipline": "other", "discipline_confidence": 0.9}
        assert classify.validate_result(_entry(), bare, _target(root)) == []
        research = {k: v for k, v in _result().items() if k != "method_class"}
        assert any("method_class" in p for p in classify.validate_result(_entry(), research, _target(root)))


def test_validate_accepts_proposed_report_type():
    tmp, root = _root()
    with tmp:
        assert classify.validate_result(_entry(), _result(report_type="policy_brief", report_type_proposed=True),
                                        _target(root)) == []
        assert classify.validate_result(_entry(), _result(report_type="policy_brief"), _target(root))


def test_apply_a_writes_profile_and_needs_second_check():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry(), _result(), PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["report_type"] == "journal_article" and p["discipline"] == ECON
        assert p["study_design"] == "study_design.randomized_controlled_trial"
        assert p["openalex_subfields"][0]["label"] == SUB and p["openalex_subfields"][0]["source"] == "llm"
        assert p["country"] == ["Rwanda"] and p["needs_review"] is True  # no second agent yet
        assert p["discipline_domain"] == "Social Sciences"


def test_apply_a_derives_income_group_and_start_year():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry(), _result(), PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["intervention_start_year"] == 2018 and p["intervention_start_year_approximate"] is False
        assert p["country_income_group"] == "low"


def test_apply_a_falls_back_to_publication_year_marked_approximate():
    tmp, root = _root()
    with tmp:
        from core.indexer.index_card import set_card_fields
        set_card_fields(str(root), "f1", {"publication_year": 2016})
        result = {k: v for k, v in _result().items() if k != "intervention_start_year"}
        classify.apply_result(_target(root), _entry(), result, PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["intervention_start_year"] == 2016 and p["intervention_start_year_approximate"] is True


def test_non_research_report_type_sets_not_assessed():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry(), {"report_type": "notes", "discipline": "other",
                                                         "discipline_confidence": 0.9}, PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["applicability"] == "not_assessed"


def test_variant_b_never_overwrites_primary_discipline_and_clears_review_on_agreement():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry("a"), _result(), PROV)
        classify.apply_result(_target(root), _entry("b"), {"discipline": ECON, "discipline_confidence": 0.9,
                                                            "subfields": [SUB]}, PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["discipline"] == ECON and p["discipline_check"]["discipline"] == ECON
        assert p["report_type"] == "journal_article" and p["needs_review"] is False


def test_variant_b_disagreement_keeps_primary_and_records_the_other_as_secondary():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry("a"), _result(), PROV)
        classify.apply_result(_target(root), _entry("b"), {"discipline": "Medicine", "discipline_confidence": 0.9,
                                                            "subfields": []}, PROV)
        p = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
        assert p["discipline"] == ECON and p["needs_review"] is False
        assert p["secondary_discipline"] == "Medicine" and p["discipline_fit"] == "mixed"


def test_validate_rejects_a_country_string_and_a_non_numeric_year():
    tmp, root = _root()
    with tmp:
        assert any("country" in p for p in classify.validate_result(_entry(), _result(country="Kenya"), _target(root)))
        assert any("intervention_start_year" in p
                   for p in classify.validate_result(_entry(), _result(intervention_start_year="2010s"), _target(root)))
        assert classify.validate_result(_entry(), _result(), _target(root)) == []


def test_apply_stores_the_canonical_field_name_whatever_case_the_agent_used():
    tmp, root = _root()
    with tmp:
        classify.apply_result(_target(root), _entry(), _result(discipline=ECON.upper()), PROV)
        assert find_card_by_file_id(str(root), "f1")[1]["research_profile"]["discipline"] == ECON
