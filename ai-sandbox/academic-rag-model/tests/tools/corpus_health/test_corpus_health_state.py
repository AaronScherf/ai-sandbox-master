from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateError, StateStore


def _finding(fingerprint="sha256:one", path="C:/notes/a.md", action="index"):
    return Finding("index_card_missing", "notes", path, "a.md", "missing card",
                   "C:/hub/.index/econ.json", action, fingerprint)


def test_identical_content_at_a_new_path_does_not_inherit_a_prior_decline(tmp_path):
    store = StateStore(tmp_path / "state")
    first = store.refresh([_finding()])[0]
    store.decide(first.finding_id, "declined", first.fingerprint)
    renamed = store.refresh([_finding(path="C:/notes/renamed.md")])[0]

    assert renamed.finding_id != first.finding_id
    assert len(store.pending()) == 1
    data = json.loads(store.state_path.read_text(encoding="utf-8"))
    new_entry = data["findings"][renamed.finding_id]
    assert new_entry["status"] == "pending_review"
    assert "possible rename or duplicate" in new_entry["finding"]["evidence"]
    assert data["findings"][first.finding_id]["status"] == "vanished"


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


def test_source_deleted_without_replacement_is_retained_as_vanished(tmp_path):
    store = StateStore(tmp_path / "state")
    finding = store.refresh([_finding()])[0]
    store.decide(finding.finding_id, "declined", finding.fingerprint)

    assert store.refresh([]) == []

    data = json.loads(store.state_path.read_text(encoding="utf-8"))
    entry = data["findings"][finding.finding_id]
    assert entry["status"] == "vanished"
    assert entry["previous_status"] == "declined"
    assert store.pending() == []


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


def test_concurrent_process_writers_are_serialized_and_preserve_the_atomic_ledger(tmp_path):
    state_dir = tmp_path / "state"
    holder_ready = tmp_path / "holder-ready"
    release_holder = tmp_path / "release-holder"
    writer_attempted = tmp_path / "writer-attempted"
    writer_done = tmp_path / "writer-done"
    holder_script = r"""
import sys
import time
from pathlib import Path
from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateStore

state_dir, ready, release = map(Path, sys.argv[1:])
store = StateStore(state_dir)
write_unlocked = store._write_unlocked
def paused_write(data):
    ready.write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 10
    while not release.exists():
        if time.monotonic() > deadline:
            raise TimeoutError("test did not release writer")
        time.sleep(0.01)
    write_unlocked(data)
store._write_unlocked = paused_write
store.refresh([Finding("index_card_missing", "notes", "C:/notes/first.md", "first.md",
                       "missing", suggested_action="index", fingerprint="sha256:first")])
"""
    writer_script = r"""
import sys
from pathlib import Path
from tools.corpus_health.finding import Finding
from tools.corpus_health.state import StateStore

state_dir, attempted, done = map(Path, sys.argv[1:])
attempted.write_text("attempted", encoding="utf-8")
StateStore(state_dir).refresh([Finding("index_card_missing", "notes", "C:/notes/second.md", "second.md",
                                       "missing", suggested_action="index", fingerprint="sha256:second")])
done.write_text("done", encoding="utf-8")
"""
    holder = subprocess.Popen(
        [sys.executable, "-c", holder_script, str(state_dir), str(holder_ready), str(release_holder)],
        cwd=Path(__file__).resolve().parents[3],
    )
    writer = None
    try:
        deadline = time.monotonic() + 10
        while not holder_ready.exists():
            if holder.poll() is not None:
                raise AssertionError(f"lock-holding writer exited early with {holder.returncode}")
            if time.monotonic() > deadline:
                raise TimeoutError("first writer did not reach its critical section")
            time.sleep(0.01)

        writer = subprocess.Popen(
            [sys.executable, "-c", writer_script, str(state_dir), str(writer_attempted), str(writer_done)],
            cwd=Path(__file__).resolve().parents[3],
        )
        deadline = time.monotonic() + 10
        while not writer_attempted.exists():
            if writer.poll() is not None:
                raise AssertionError(f"second writer exited early with {writer.returncode}")
            if time.monotonic() > deadline:
                raise TimeoutError("second writer did not start")
            time.sleep(0.01)
        time.sleep(0.3)
        assert not writer_done.exists(), "second writer entered while the first held the state lock"

        release_holder.write_text("release", encoding="utf-8")
        assert holder.wait(timeout=10) == 0
        assert writer.wait(timeout=10) == 0

        data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert len(data["findings"]) == 2
        assert {entry["finding"]["path"] for entry in data["findings"].values()} == {
            "C:/notes/first.md", "C:/notes/second.md",
        }
    finally:
        release_holder.touch(exist_ok=True)
        if holder.poll() is None:
            holder.wait(timeout=10)
        if writer is not None and writer.poll() is None:
            writer.wait(timeout=10)
