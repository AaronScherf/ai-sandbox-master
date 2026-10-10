import hashlib
import http.client
import json
import threading
from pathlib import Path

import pytest

from tools.project_steering.cli import main
from tools.project_steering.parser import parse_tracker
from tools.project_steering.ranking import rank
from tools.project_steering.review_server import ReviewServer, score_proposals
from tools.project_steering.state import DecisionError, DecisionStore


SOURCE = ("## Work\n"
          "- <!-- TODO-0001 --> Fix a scoped bug. (added 2026-10-01)\n"
          "- <!-- TODO-0002 --> Fix another bug. (added 2026-10-02)\n")


def draft(tasks, source_hash="abc"):
    return {"source_sha256": source_hash, "batch": "codex_scores_2026_10_10", "rows": [
        {"id": task.task_id, "fingerprint": task.fingerprint, "impact": 2, "urgency": 1,
         "effort": "half_day", "confidence": "medium", "rationale": "Scoped repo fix."}
        for task in tasks]}


@pytest.mark.parametrize("damage", ["stale_source", "duplicate", "bad_value", "bad_fingerprint"])
def test_score_import_rejects_bad_batch_without_state_change(tmp_path: Path, damage: str):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    payload = draft(tasks)
    if damage == "stale_source":
        payload["source_sha256"] = "wrong"
    elif damage == "duplicate":
        payload["rows"][1]["id"] = payload["rows"][0]["id"]
    elif damage == "bad_value":
        payload["rows"][0]["impact"] = 4
    else:
        payload["rows"][0]["fingerprint"] = "changed"
    before = store.path.read_bytes()
    with pytest.raises(DecisionError):
        store.import_scores(tasks, payload, revision=state["revision"], source_sha256="abc")
    assert store.path.read_bytes() == before


def test_proposals_do_not_rank_until_approved_and_preserve_owner_values(tmp_path: Path):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    state = store.decide(tasks[0], revision=state["revision"], fingerprint=tasks[0].fingerprint,
                         changes={"impact": 3, "urgency": 0, "effort": "<2h"})
    state = store.import_scores(tasks, draft(tasks), revision=state["revision"], source_sha256="abc")
    assert rank(tasks, state)["groups"]["needs_estimate"][0]["task"]["task_id"] == tasks[1].task_id
    assert score_proposals(tasks, state)[tasks[1].task_id]["status"] == "unapproved"
    state, result = store.approve_scores(tasks, revision=state["revision"], task_ids=[task.task_id for task in tasks])
    assert result == {"applied": [task.task_id for task in tasks], "stale": []}
    assert [state["tasks"][tasks[0].task_id][key] for key in ("impact", "urgency", "effort")] == [3, 0, "<2h"]
    assert [state["tasks"][tasks[1].task_id][key] for key in ("impact", "urgency", "effort")] == [2, 1, "half_day"]
    assert len(rank(tasks, state)["ready"]) == 2
    assert score_proposals(tasks, state)[tasks[1].task_id]["status"] == "approved"


def test_changed_task_skips_stale_score_and_keeps_other_approval(tmp_path: Path):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    state = store.import_scores(tasks, draft(tasks), revision=state["revision"], source_sha256="abc")
    changed = parse_tracker(SOURCE.replace("Fix another bug", "Fix a changed bug")).tasks
    state = store.reconcile(changed)
    assert score_proposals(changed, state)[changed[1].task_id]["status"] == "stale"
    state, result = store.approve_scores(changed, revision=state["revision"], task_ids=[task.task_id for task in changed])
    assert result == {"applied": [changed[0].task_id], "stale": [changed[1].task_id]}
    assert state["tasks"][changed[1].task_id]["impact"] is None


def test_http_score_approval_updates_rank_and_requires_current_revision(tmp_path: Path):
    tracker = tmp_path / "tracker.md"
    tracker.write_text(SOURCE, encoding="utf-8")
    tasks = parse_tracker(SOURCE).tasks
    state_dir = tmp_path / "state"
    store = DecisionStore(state_dir)
    state = store.reconcile(tasks)
    source_hash = hashlib.sha256(tracker.read_bytes()).hexdigest()
    store.import_scores(tasks, draft(tasks, source_hash), revision=state["revision"], source_sha256=source_hash)
    assert main(["scan", "--tracker", str(tracker), "--state-dir", str(state_dir), "--format", "json"]) == 0
    server = ReviewServer(tracker, state_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/tasks?token=" + server.token)
        current = json.loads(conn.getresponse().read())
        assert current["score_proposals"][tasks[0].task_id]["status"] == "unapproved"
        payload = {"source_sha256": source_hash, "revision": current["revision"], "task_ids": [tasks[0].task_id]}
        headers = {"Content-Type": "application/json", "Origin": server.origin,
                   "X-Project-Steering-Token": server.token}
        conn.request("POST", "/api/scores/approve", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 200
        conn.request("POST", "/api/scores/approve", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 409
        assert store.read()["tasks"][tasks[0].task_id]["impact"] == 2
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
