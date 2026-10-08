# tests/agent/study_guide/test_study_guide_revise_review.py
import json

import pytest

from agent.study_guide.revise.edits import Edit, EditReport, ReviseError
from agent.study_guide.revise.review import accepted_ids, review_items, write_review_items
from agent.study_guide.revise.segment import segment

BODY = "# T\n\n## A\n\nalpha text\n\n## B\n\nbeta text\n"


def _report():
    ids = {b.heading_path[-1]: b.id for b in segment(BODY)}
    edits = [Edit("e1", "delete", [ids["A"]], "off topic", stage="relevance", evidence=["Exam, p. 1"], protected=True),
             Edit("e2", "fix", [ids["B"]], "wrong", stage="correctness", quote="beta", replacement="gamma")]
    return EditReport("g.md", "sha", "now", [], edits, [ids["A"]])


def test_review_items_show_before_and_after():
    items = review_items(_report(), BODY)
    assert items[0]["id"] == "e1" and items[0]["before"].startswith("## A") and items[0]["after"] is None
    assert items[0]["protected"] is True and items[0]["evidence"] == ["Exam, p. 1"]
    assert items[1]["after"] == "gamma" and items[1]["quote"] == "beta"


def test_write_review_items(tmp_path):
    write_review_items(_report(), BODY, tmp_path / "r.json")
    assert [i["id"] for i in json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))] == ["e1", "e2"]


def test_only_explicit_accepts_count():
    assert accepted_ids(_report(), {"e1": "accept", "e2": "reject"}) == {"e1"}
    assert accepted_ids(_report(), {}) == set()


@pytest.mark.parametrize("decisions,fragment", [({"zzz": "accept"}, "unknown"), ({"e1": "maybe"}, "accept")])
def test_bad_decisions_are_rejected(decisions, fragment):
    with pytest.raises(ReviseError, match=fragment):
        accepted_ids(_report(), decisions)
