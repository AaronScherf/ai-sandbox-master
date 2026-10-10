import hashlib
import http.client
import json
import threading
from datetime import date
from pathlib import Path

import pytest

from tools.project_steering.cli import main
from tools.project_steering.parser import parse_tracker
from tools.project_steering.ranking import rank
from tools.project_steering.review_server import ReviewServer
from tools.project_steering.routing import route_for, route_view
from tools.project_steering.state import DecisionError, DecisionStore


SOURCE = ("## Work\n"
          "- <!-- TODO-0001 --> Run existing transcription pipeline. (added 2026-10-01)\n"
          "- <!-- TODO-0002 --> Design new scheduler. (added 2026-10-02)\n")


def draft(tasks, source_hash="abc"):
    agents = ("gemini", "claude")
    return {"source_sha256": source_hash, "batch": "claude_import_2026-10-10", "rows": [
        {"id": task.task_id, "fingerprint": task.fingerprint, "agent": agents[i],
         "complexity": "moderate", "difficulty": "medium", "context": "needs_repo_context",
         "confidence": "medium", "rationale": "Task wording and routing guide."}
        for i, task in enumerate(tasks)]}


def test_v1_ledger_upgrade_and_safe_new_task_fallback(tmp_path: Path):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    first = store.reconcile(tasks)
    old = {**first, "version": 1}
    old["tasks"][tasks[0].task_id]["impact"] = 2
    store.path.write_text(json.dumps(old), encoding="utf-8")
    loaded = store.read()
    assert loaded["version"] == 2
    assert loaded["tasks"][tasks[0].task_id]["impact"] == 2
    resolved = route_for(tasks[0], loaded["tasks"][tasks[0].task_id])
    assert resolved["agent"] == "needs_human"
    assert resolved["proposal_status"] == "none"
    assert not resolved["fully_approved"]
    unsigned = {**loaded["tasks"][tasks[0].task_id], "agent": "codex", "complexity": "moderate",
                "difficulty": "medium", "context": "needs_repo_context"}
    assert route_for(tasks[0], unsigned)["agent"] == "needs_human"


@pytest.mark.parametrize("damage", ["bad_enum", "unknown_id", "duplicate_id", "bad_fingerprint", "missing_id"])
def test_invalid_import_is_atomic(tmp_path: Path, damage: str):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    payload = draft(tasks)
    if damage == "bad_enum":
        payload["rows"][0]["agent"] = "random_agent"
    elif damage == "unknown_id":
        payload["rows"][0]["id"] = "TODO-9999"
    elif damage == "duplicate_id":
        payload["rows"][1]["id"] = payload["rows"][0]["id"]
    elif damage == "bad_fingerprint":
        payload["rows"][0]["fingerprint"] = "stale"
    else:
        payload["rows"].pop()
    before = store.path.read_bytes()
    with pytest.raises(DecisionError):
        store.import_routing(tasks, payload, revision=state["revision"], source_sha256="abc")
    assert store.path.read_bytes() == before


def test_import_reimport_override_batch_approval_and_stale_proposal(tmp_path: Path):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    state = store.import_routing(tasks, draft(tasks), revision=state["revision"], source_sha256="abc")
    assert state["tasks"][tasks[0].task_id]["agent_suggested"] == "gemini"
    assert "agent" not in state["tasks"][tasks[0].task_id]
    initial_view = route_view(tasks, state, rank(tasks, state))
    assert initial_view["proposed_batches"]["gemini"] == [tasks[0].task_id]
    assert initial_view["approved_batches"]["gemini"] == []
    state = store.route_decide(tasks[0], revision=state["revision"], fingerprint=tasks[0].fingerprint,
                               changes={"agent": "codex"})
    rerun = draft(tasks)
    rerun["rows"][0]["agent"] = "claude"
    state = store.import_routing(tasks, rerun, revision=state["revision"], source_sha256="abc")
    assert state["tasks"][tasks[0].task_id]["agent"] == "codex"
    assert state["tasks"][tasks[0].task_id]["agent_suggested"] == "claude"
    state, result = store.batch_approve(tasks, revision=state["revision"],
                                        task_ids=[task.task_id for task in tasks])
    assert result == {"applied": [task.task_id for task in tasks], "stale": []}
    assert state["tasks"][tasks[0].task_id]["agent"] == "codex"
    assert route_view(tasks, state, rank(tasks, state))["approved_batches"]["codex"] == [tasks[0].task_id]
    state = store.route_decide(tasks[0], revision=state["revision"], fingerprint=tasks[0].fingerprint,
                               changes={"agent": None})
    assert route_for(tasks[0], state["tasks"][tasks[0].task_id])["agent"] == "needs_human"
    assert route_for(tasks[0], state["tasks"][tasks[0].task_id])["proposed"]["agent"] == "claude"


def test_changed_text_flags_stale_and_batch_skips_only_that_task(tmp_path: Path):
    tasks = parse_tracker(SOURCE).tasks
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    state = store.import_routing(tasks, draft(tasks), revision=state["revision"], source_sha256="abc")
    changed = parse_tracker(SOURCE.replace("Design new scheduler", "Design a different scheduler")).tasks
    state = store.reconcile(changed)
    assert route_for(changed[1], state["tasks"][changed[1].task_id])["proposal_status"] == "stale"
    state, result = store.batch_approve(changed, revision=state["revision"],
                                        task_ids=[task.task_id for task in changed])
    assert result["applied"] == [changed[0].task_id]
    assert result["stale"] == [changed[1].task_id]
    assert "agent" not in state["tasks"][changed[1].task_id]


def test_not_before_gate_excludes_today_then_readmits_without_score_penalty(tmp_path: Path):
    task = parse_tracker("## Trial\n- <!-- TODO-0024 --> Review scheduled runs. (added 2026-10-10)\n").tasks[0]
    store = DecisionStore(tmp_path)
    state = store.reconcile((task,))
    state = store.decide(task, revision=state["revision"], fingerprint=task.fingerprint,
                         changes={"impact": 3, "urgency": 2, "effort": "<2h"})
    state = store.route_decide(task, revision=state["revision"], fingerprint=task.fingerprint,
                               changes={"not_before": "2026-10-17"})
    early = rank((task,), state, today=date(2026, 10, 10))
    assert early["shortlist"] == []
    assert early["groups"]["not_before"][0]["task"]["task_id"] == task.task_id
    assert rank((task,), state, today=date(2026, 10, 17))["shortlist"][0]["task"]["task_id"] == task.task_id


def test_http_batch_approval_requires_revision_and_origin(tmp_path: Path):
    tracker = tmp_path / "tracker.md"
    tracker.write_text(SOURCE, encoding="utf-8")
    tasks = parse_tracker(SOURCE).tasks
    state_dir = tmp_path / "state"
    store = DecisionStore(state_dir)
    state = store.reconcile(tasks)
    source_hash = hashlib.sha256(tracker.read_bytes()).hexdigest()
    store.import_routing(tasks, draft(tasks, source_hash), revision=state["revision"], source_sha256=source_hash)
    assert main(["scan", "--tracker", str(tracker), "--state-dir", str(state_dir), "--format", "json"]) == 0
    server = ReviewServer(tracker, state_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/tasks?token=" + server.token)
        current = json.loads(conn.getresponse().read())
        assert current["routing"]["proposed_batches"]["gemini"] == [tasks[0].task_id]
        payload = {"source_sha256": source_hash, "revision": current["revision"],
                   "task_ids": [tasks[0].task_id]}
        conn.request("POST", "/api/routing/approve", body=json.dumps(payload),
                     headers={"Content-Type": "application/json", "X-Project-Steering-Token": server.token})
        assert conn.getresponse().status == 403
        headers = {"Content-Type": "application/json", "Origin": server.origin,
                   "X-Project-Steering-Token": server.token}
        conn.request("POST", "/api/routing/approve", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 200
        conn.request("POST", "/api/routing/approve", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 409
        assert store.read()["tasks"][tasks[0].task_id]["agent"] == "gemini"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
