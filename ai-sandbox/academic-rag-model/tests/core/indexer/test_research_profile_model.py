import json
import os
import tempfile

import pytest

from core.indexer.index_card import load_shard, save_shard, shard_path
from core.indexer.research_profile import (
    RESEARCH_PROFILE_VERSION,
    derive_applicability,
    set_research_profile,
    validate_profile,
)

TAG = {"term_id": "intervention.x", "level": 3, "quote": "q", "quote_locator": "p1"}


@pytest.mark.parametrize("interventions,outcomes,assessed,expected", [
    ([TAG], [TAG], True, "both"),
    ([TAG], [], True, "intervention_only"),
    ([], [TAG], True, "outcome_only"),
    ([], [], True, "not_applicable"),
    (None, None, True, "not_applicable"),
    ([TAG], [TAG], False, "not_assessed"),
    (None, None, False, "not_assessed"),
])
def test_applicability_table(interventions, outcomes, assessed, expected):
    assert derive_applicability(interventions, outcomes, assessed=assessed) == expected


def test_validate_rejects_unknown_report_type_and_bad_enums():
    problems = validate_profile({"report_type": "blog", "method_class": "vibes", "orientation": "sideways",
                                 "evidence_role": "judge", "applicability": "maybe"})
    text = " ".join(problems)
    for field in ("report_type", "method_class", "orientation", "evidence_role", "applicability"):
        assert field in text


def test_validate_accepts_open_report_type_when_marked_proposed():
    assert validate_profile({"report_type": "policy_brief", "report_type_proposed": True}) == []


def test_validate_flags_unknown_keys():
    assert any("surprise" in p for p in validate_profile({"surprise": 1}))


def _seed(root, file_id="f1", course="business"):
    save_shard(root, course, [{"file_id": file_id, "path": "a.md", "course": course, "summary": "keep me"}])


def test_set_profile_merges_without_touching_other_keys():
    with tempfile.TemporaryDirectory() as root:
        _seed(root)
        assert set_research_profile(root, "f1", {"report_type": "journal_article", "method_class": "quantitative"})
        assert set_research_profile(root, "f1", {"orientation": "retrospective"})
        card = load_shard(root, "business")[0]
        assert card["summary"] == "keep me" and card["path"] == "a.md"
        assert card["research_profile"] == {
            "report_type": "journal_article", "method_class": "quantitative", "orientation": "retrospective",
            "research_profile_version": RESEARCH_PROFILE_VERSION}


def test_set_profile_unknown_key_raises():
    with tempfile.TemporaryDirectory() as root:
        _seed(root)
        with pytest.raises(ValueError):
            set_research_profile(root, "f1", {"path": "evil.md"})


def test_set_profile_missing_card_returns_false():
    with tempfile.TemporaryDirectory() as root:
        assert set_research_profile(root, "nope", {"report_type": "report"}) is False


def test_course_shard_without_profile_is_byte_identical_after_other_card_updated():
    with tempfile.TemporaryDirectory() as root:
        save_shard(root, "economics", [{"file_id": "c1", "course": "economics", "summary": "course card"}])
        _seed(root)
        before = open(shard_path(root, "economics"), "rb").read()
        set_research_profile(root, "f1", {"report_type": "report"})
        assert open(shard_path(root, "economics"), "rb").read() == before
        assert "research_profile" not in json.loads(before)[0]
        assert os.path.exists(shard_path(root, "business"))
