from collections import Counter

from agent.literature.profile.profiles import DEFAULT_DIR, load_profile
from agent.literature.profile.summary import render_summary, summarize
from agent.literature.vocab import Term, Vocabulary

STRICT = load_profile(DEFAULT_DIR / "3ie_strict.yaml")


def _vocab():
    terms = {
        "intervention.s1": Term("intervention.s1", "S1"),
        "intervention.b1": Term("intervention.b1", "B1", parent="intervention.s1"),
        "intervention.l1": Term("intervention.l1", "L1", parent="intervention.b1"),
        "intervention.l2": Term("intervention.l2", "L2", parent="intervention.b1"),
    }
    return Vocabulary("intervention", 1, "3ie", "t", terms)


def _card(fid, **profile):
    return {"file_id": fid, "title": f"Paper {fid}", "research_profile": profile}


CARDS = [
    _card("a", report_type="journal_article", discipline="Medicine", method_class="quantitative",
          orientation="retrospective", evidence_role="primary_evaluation", applicability="both",
          intervention_tags=[{"term_id": "intervention.l1", "level": 3}], outcome_tags=[{"term_id": "outcome.x", "level": 1}],
          country_income_group="low", study_design="study_design.randomized_controlled_trial", publication_year=2015),
    _card("b", report_type="journal_article", discipline="Medicine", method_class="qualitative",
          orientation="prospective", evidence_role="other", applicability="intervention_only",
          intervention_tags=[{"term_id": "intervention.l2", "level": 3}], outcome_tags=[]),
    _card("c", report_type="notes", discipline="other", applicability="not_assessed"),
    _card("d", report_type="journal_article", discipline="Physics and Astronomy", method_class="quantitative",
          applicability="not_applicable", intervention_tags=[], outcome_tags=[], needs_review=True,
          review_reasons=["discipline: low confidence"], doi_verified={"match": "mismatch"}),
    {"file_id": "course1", "title": "A course handout", "doc_type": "ta_notes"},
]


def test_summary_counts_equal_direct_counts_over_cards():
    s = summarize(CARDS)
    research = [c["research_profile"] for c in CARDS if "research_profile" in c]
    assert s["n_documents"] == len(research) == 4
    for field in ("report_type", "discipline", "method_class", "applicability"):
        assert s[field] == dict(Counter(p[field] for p in research if p.get(field)))


def test_summary_rolls_leaf_tags_up_to_branch_and_sector():
    s = summarize(CARDS, vocabs={"intervention": _vocab()})
    assert s["intervention_terms"] == {"intervention.l1": 1, "intervention.l2": 1, "intervention.b1": 2, "intervention.s1": 2}


def test_summary_ignores_course_material_cards():
    assert "course1" not in str(summarize(CARDS)["flagged"]) and summarize(CARDS)["n_documents"] == 4


def test_summary_flags_review_and_doi_mismatch():
    flagged = {f["file_id"]: f["reasons"] for f in summarize(CARDS)["flagged"]}
    assert set(flagged) == {"d"} and any("doi" in r.lower() for r in flagged["d"])


def test_summary_applies_a_profile():
    s = summarize(CARDS, profile=STRICT)
    assert s["profile"]["name"] == "3ie_strict" and s["profile"]["included"] == 1
    assert s["profile"]["included"] + s["profile"]["unclear"] + s["profile"]["excluded"] == 4


def test_render_summary_mentions_every_section():
    text = render_summary(summarize(CARDS, profile=STRICT))
    for word in ("report_type", "discipline", "applicability", "3ie_strict"):
        assert word in text


def test_summary_counts_the_owners_decision_not_the_models_value():
    import tempfile
    from agent.literature.profile import review
    with tempfile.TemporaryDirectory() as root:
        card = {"file_id": "z1", "research_profile": {"report_type": "notes"}}
        review.record_decision(root, "z1", "report_type", "journal_article", "owner")
        assert summarize([card], index_root=root)["report_type"] == {"journal_article": 1}
        assert summarize([card])["report_type"] == {"notes": 1}
