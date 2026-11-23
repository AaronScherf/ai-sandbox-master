from dataclasses import replace

from agent.literature.profile import profiles
from agent.literature.profile.profiles import DEFAULT_DIR, load_profile, matches

STRICT = load_profile(DEFAULT_DIR / "3ie_strict.yaml")
BROAD = load_profile(DEFAULT_DIR / "broad.yaml")
TAG = {"term_id": "intervention.x", "level": 1, "quote": "q", "quote_locator": 1}


def _record(**over):
    base = {"evidence_role": "primary_evaluation", "study_design": "study_design.randomized_controlled_trial",
            "orientation": "retrospective", "country_income_group": "low", "publication_year": 2015,
            "intervention_tags": [TAG], "outcome_tags": [TAG], "applicability": "both"}
    base.update(over)
    return base


def test_strict_includes_impact_evaluation_in_lmic_after_min_year():
    ok, reason = matches(STRICT, _record())
    assert ok and reason == "included"


def test_strict_includes_a_systematic_review():
    ok, _ = matches(STRICT, _record(evidence_role="synthesis", study_design="study_design.systematic_review"))
    assert ok


def test_strict_excludes_high_income_country():
    ok, reason = matches(STRICT, _record(country_income_group="high"))
    assert not ok and "income" in reason


def test_strict_excludes_non_causal_design_and_prospective_and_no_intervention():
    assert not matches(STRICT, _record(study_design="study_design.cross_sectional_regression"))[0]
    assert not matches(STRICT, _record(orientation="prospective"))[0]
    assert not matches(STRICT, _record(intervention_tags=[], applicability="outcome_only"))[0]


def test_missing_income_group_is_unclear_and_included():
    ok, reason = matches(STRICT, _record(country_income_group=None))
    assert ok and reason.startswith("unclear") and "income" in reason


def test_unclear_is_excluded_when_the_profile_says_so():
    ok, _ = matches(replace(STRICT, include_unclear=False), _record(country_income_group=None))
    assert not ok


def test_min_year_is_a_profile_parameter_not_a_constant():
    assert STRICT.min_year == 2000
    assert not matches(STRICT, _record(publication_year=1995))[0]
    assert matches(replace(STRICT, min_year=1990), _record(publication_year=1995))[0]
    assert "2000" not in open(profiles.__file__, encoding="utf-8").read()


def test_broad_includes_any_tagged_paper_and_excludes_untagged():
    assert matches(BROAD, _record(country_income_group="high", orientation="prospective"))[0]
    assert matches(BROAD, _record(intervention_tags=[], applicability="outcome_only"))[0]
    assert not matches(BROAD, _record(intervention_tags=[], outcome_tags=[], applicability="not_applicable"))[0]
