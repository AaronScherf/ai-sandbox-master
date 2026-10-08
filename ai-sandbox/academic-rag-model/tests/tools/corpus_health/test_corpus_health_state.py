from __future__ import annotations

import json

import pytest

from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateError, StateStore


def _finding(fingerprint="sha256:one", path="C:/notes/a.md", action="index"):
    return Finding("index_card_missing", "notes", path, "a.md", "missing card",
                   "C:/hub/.index/econ.json", action, fingerprint)


def test_unchanged_declined_finding_stays_suppressed_across_a_unique_rename(tmp_path):
    store = StateStore(tmp_path / "state")
    first = store.refresh([_finding()])[0]
    store.decide(first.finding_id, "declined", first.fingerprint)
    renamed = store.refresh([_finding(path="C:/notes/renamed.md")])[0]

    assert renamed.finding_id != first.finding_id
    assert store.pending() == []
    assert store.pending(include_deferred=True) == []
    data = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert data["findings"][renamed.finding_id]["status"] == "declined"


def test_identical_content_in_distinct_locations_keeps_separate_decisions(tmp_path):
    store = StateStore(tmp_path / "state")
    findings = store.refresh([_finding(path="C:/notes/a.md"), _finding(path="C:/notes/b.md")])

    assert findings[0].finding_id != findings[1].finding_id
    assert len(store.pending()) == 2


def test_changed_content_creates_new_pending_finding_and_old_one_vanishes(tmp_path):
    store = StateStore(tmp_path / "state")
    first = store.refresh([_finding()])[0]
    store.decide(first.finding_id, "accepted", first.fingerprint)
    changed = store.refresh([_finding(fingerprint="sha256:two")])[0]

    assert changed.finding_id != first.finding_id
    assert changed.finding_id == store.pending()[0]["finding_id"]
    data = json.loads(store.state_path.read_text(encoding="utf-8"))
    assert data["findings"][first.finding_id]["status"] == "vanished"


def test_deferred_items_are_not_pending_but_remain_visible_in_deferred_view(tmp_path):
    store = StateStore(tmp_path / "state")
    finding = store.refresh([_finding()])[0]
    store.decide(finding.finding_id, "deferred", finding.fingerprint)

    assert store.pending() == []
    assert store.pending(include_deferred=True)[0]["status"] == "deferred"


def test_action_change_invalidates_prior_decline(tmp_path):
    store = StateStore(tmp_path / "state")
    finding = store.refresh([_finding()])[0]
    store.decide(finding.finding_id, "declined", finding.fingerprint)
    changed_action = store.refresh([_finding(action="repair frontmatter")])[0]

    assert changed_action.finding_id == finding.finding_id
    assert store.pending()[0]["status"] == "pending_review"


def test_batch_decision_is_atomic_when_one_fingerprint_is_stale(tmp_path):
    store = StateStore(tmp_path / "state")
    findings = store.refresh([_finding(), _finding("sha256:two", "C:/notes/b.md")])
    decisions = [
        {"finding_id": item.finding_id, "fingerprint": item.fingerprint,
         "decision": "accepted"} for item in findings
    ]
    decisions[1]["fingerprint"] = "stale"

    with pytest.raises(StateError, match="stale"):
        store.decide_many(decisions)
    assert all(entry["status"] == "pending_review" for entry in store.pending())


def test_malformed_state_is_not_silently_replaced(tmp_path):
    store = StateStore(tmp_path / "state")
    store.directory.mkdir()
    store.state_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(StateError, match="cannot read state"):
        store.refresh([_finding()])
    assert store.state_path.read_text(encoding="utf-8") == "{broken"


def test_acceptance_requires_a_content_fingerprint(tmp_path):
    store = StateStore(tmp_path / "state")
    finding = store.refresh([_finding(fingerprint="stat:9000000:123")])[0]

    with pytest.raises(StateError, match="content fingerprint"):
        store.decide(finding.finding_id, "accepted", finding.fingerprint)
    assert store.pending()[0]["status"] == "pending_review"
