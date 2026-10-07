# tests/agent/study_guide/test_study_guide_review.py
import json

import pytest

from agent.study_guide.plan import (
    PendingReviewError, Plan, PlanEntry, PlanError, TopicPlan, accepted, apply_decisions, decision_key,
    pending_entries, review_items, write_review_items,
)


def _entry(cid, rule="section", status="accepted", **kw):
    base = dict(chunk_id=cid, file_id="f-" + cid, path=f"academic_notes/econ/{cid}.md", citation=f"c-{cid}",
                doc_type="textbook", offering="", score=0.8, rule=rule, content_hash="h", status=status)
    base.update(kw)
    return PlanEntry(**base)


@pytest.fixture
def plan():
    return Plan("demo", "demo.toml", "sha", "econ", "2026-10-05T00:00:00+00:00", [
        TopicPlan("Wald", [_entry("a"), _entry("b", "discover", "pending"), _entry("c", "discover", "pending")]),
        TopicPlan("LM", [_entry("d"), _entry("e", "discover", "pending", offering="class_2024", doc_type="ta_notes")]),
    ])


def test_decision_key():
    assert decision_key("Wald", "a") == "Wald|a"


def test_review_items_list_every_entry_with_locks(plan):
    items = review_items(plan)
    assert [i["key"] for i in items] == ["Wald|a", "Wald|b", "Wald|c", "LM|d", "LM|e"]
    first, second = items[0], items[1]
    assert first["locked"] is True and second["locked"] is False
    assert second == {"key": "Wald|b", "topic": "Wald", "chunk_id": "b", "book": "b.md", "citation": "c-b",
                      "doc_type": "textbook", "offering": "", "score": 0.8, "rule": "discover",
                      "status": "pending", "locked": False}
    assert items[4]["offering"] == "class_2024" and items[4]["doc_type"] == "ta_notes"


def test_write_review_items_is_a_json_list(plan, tmp_path):
    path = tmp_path / "x" / "demo.review.json"
    write_review_items(plan, path)
    assert [i["key"] for i in json.loads(path.read_text(encoding="utf-8"))][:2] == ["Wald|a", "Wald|b"]


def test_apply_decisions_keeps_and_drops_without_mutating_the_input(plan):
    new = apply_decisions(plan, {"Wald|b": "keep", "Wald|c": "drop", "LM|e": "keep"})
    assert [e.status for e in new.topics[0].entries] == ["accepted", "accepted", "dropped"]
    assert [e.status for e in new.topics[1].entries] == ["accepted", "accepted"]
    assert [e.status for e in plan.topics[0].entries] == ["accepted", "pending", "pending"]


@pytest.mark.parametrize("decisions,fragment", [
    ({"Wald|zzz": "keep"}, "unknown"),
    ({"Wald|a": "drop"}, "pinned"),
    ({"Wald|b": "maybe"}, "keep"),
])
def test_apply_decisions_rejects_bad_input(plan, decisions, fragment):
    with pytest.raises(PlanError, match=fragment):
        apply_decisions(plan, decisions)


def test_deciding_twice_is_rejected(plan):
    once = apply_decisions(plan, {"Wald|b": "keep"})
    with pytest.raises(PlanError, match="already decided"):
        apply_decisions(once, {"Wald|b": "drop"})


def test_pending_entries(plan):
    assert [(t, e.chunk_id) for t, e in pending_entries(plan)] == [("Wald", "b"), ("Wald", "c"), ("LM", "e")]


def test_accepted_blocks_on_pending_unless_explicitly_allowed(plan):
    with pytest.raises(PendingReviewError, match="Wald"):
        accepted(plan, "Wald")
    assert [e.chunk_id for e in accepted(plan, "Wald", accept_unreviewed=True)] == ["a", "b", "c"]


def test_accepted_excludes_dropped(plan):
    decided = apply_decisions(plan, {"Wald|b": "keep", "Wald|c": "drop"})
    assert [e.chunk_id for e in accepted(decided, "Wald")] == ["a", "b"]


def test_accepted_unknown_topic(plan):
    with pytest.raises(PlanError, match="Nope"):
        accepted(plan, "Nope")
