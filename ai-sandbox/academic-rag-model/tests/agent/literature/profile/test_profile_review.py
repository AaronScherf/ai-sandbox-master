import json
import os
import tempfile

import pytest

from agent.literature.profile import review
from core.indexer.index_card import find_card_by_file_id, save_shard
from core.indexer.research_profile import set_research_profile


def _root(profiles):
    tmp = tempfile.TemporaryDirectory()
    cards = [{"file_id": fid, "course": "business", "title": f"Paper {fid}", "doc_type": "journal_article",
              "path": f"{fid}.md"} for fid in profiles]
    save_shard(tmp.name, "business", cards)
    for fid, profile in profiles.items():
        if profile:
            set_research_profile(tmp.name, fid, profile)
    return tmp


def _card(root, fid):
    return find_card_by_file_id(root, fid)[1]


def test_decision_overrides_model_value():
    with _root({"a": {"discipline": "Economics, Econometrics and Finance"}}) as root:
        review.record_decision(root, "a", "discipline", "Medicine", "owner")
        assert review.effective_value(root, _card(root, "a"), "discipline") == "Medicine"
        assert _card(root, "a")["research_profile"]["discipline"] == "Economics, Econometrics and Finance"


def test_effective_value_falls_back_to_the_card():
    with _root({"a": {"discipline": "Medicine"}}) as root:
        assert review.effective_value(root, _card(root, "a"), "discipline") == "Medicine"
        assert review.effective_value(root, _card(root, "a"), "country") is None


def test_decision_survives_a_later_model_rewrite_of_the_field():
    with _root({"a": {"discipline": "Medicine"}}) as root:
        review.record_decision(root, "a", "discipline", "Physics and Astronomy", "owner")
        set_research_profile(root, "a", {"discipline": "Social Sciences", "provenance": {"classify_a": {"prompt_version": "classify-v9"}}})
        assert review.effective_value(root, _card(root, "a"), "discipline") == "Physics and Astronomy"


def test_queue_lists_low_confidence_disagreeing_and_mismatched_cards_but_not_clean_ones():
    profiles = {
        "clean": {"report_type": "journal_article", "needs_review": False, "study_design": "study_design.randomized_controlled_trial",
                  "method_class": "quantitative", "doi_verified": {"match": "match"}},
        "lowconf": {"needs_review": True, "review_reasons": ["discipline: low confidence 0.60 below 0.8"], "discipline": "Medicine"},
        "design": {"study_design": "study_design.qualitative", "method_class": "quantitative"},
        "doi": {"doi_verified": {"match": "mismatch"}, "bibliography_mismatches": ["title: card 'x' vs registry 'y'"]},
        "noprofile": {},
    }
    with _root(profiles) as root:
        queue = review.review_queue(root)
        pairs = {(i["file_id"], i["field"]) for i in queue}
        assert pairs == {("lowconf", "discipline"), ("design", "method_class"), ("doi", "bibliography")}


def test_resolved_item_leaves_queue():
    with _root({"lowconf": {"needs_review": True, "review_reasons": ["discipline: strong: x"], "discipline": "Medicine"}}) as root:
        assert len(review.review_queue(root)) == 1
        review.resolve_item(root, "lowconf", "discipline", "Medicine", "owner")
        assert review.review_queue(root) == []


def test_resolve_item_rejects_unknown_field_and_bad_discipline():
    with _root({"a": {"discipline": "Medicine"}}) as root:
        with pytest.raises(ValueError):
            review.resolve_item(root, "a", "path", "evil", "owner")
        with pytest.raises(ValueError):
            review.resolve_item(root, "a", "discipline", "Astrology", "owner")


def test_ledger_write_is_atomic_on_interruption(monkeypatch):
    with _root({"a": {"discipline": "Medicine"}}) as root:
        review.record_decision(root, "a", "discipline", "Medicine", "owner")
        before = open(review.ledger_path(root), "rb").read()

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            review.record_decision(root, "a", "discipline", "Physics and Astronomy", "owner")
        monkeypatch.undo()
        assert open(review.ledger_path(root), "rb").read() == before
        assert json.loads(before)["a"]["discipline"]["value"] == "Medicine"
        assert not [f for f in os.listdir(os.path.dirname(review.ledger_path(root))) if f.endswith(".tmp")]
