import hashlib
import http.client
import json
import subprocess
import threading
from pathlib import Path

import pytest

from tools.project_steering.identity import TRACKER_RELATIVE, apply_ids, preview_ids
from tools.project_steering.parser import parse_tracker
from tools.project_steering.ranking import rank
from tools.project_steering.review_server import ReviewServer
from tools.project_steering.report import make_report, publish_report, render_markdown
from tools.project_steering.state import DecisionError, DecisionStore


def fixture_tasks():
    text = ("## Alpha\n- <!-- TODO-0001 --> A. (added 2026-10-01)\n"
            "- <!-- TODO-0002 --> B. (added 2026-10-02)\n"
            "## Beta\n- <!-- TODO-0003 --> C.\n")
    return parse_tracker(text).tasks


def test_id_preview_is_one_pass_and_marker_only():
    source = "## A\n- One. (added 2026-10-01)\n### B\n- Two. (added 2026-10-02)\n## C\n- Three.\n"
    first = preview_ids(source)
    assert first.assigned == 3
    assert first.needs_id == ()
    assert [t.task_id for t in parse_tracker(first.output).tasks] == ["TODO-0001", "TODO-0002", "TODO-0003"]
    assert preview_ids(first.output).assigned == 0
    assert first.output.replace("<!-- TODO-0001 --> ", "").replace("<!-- TODO-0002 --> ", "").replace("<!-- TODO-0003 --> ", "") == source


def test_id_migration_rejects_stale_source_and_requires_fresh_preview(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    path = tmp_path / TRACKER_RELATIVE
    path.parent.mkdir(parents=True)
    path.write_text("## A\n- One.\n", encoding="utf-8")
    subprocess.run(["git", "add", str(TRACKER_RELATIVE)], cwd=tmp_path, check=True)
    old = preview_ids(path.read_bytes().decode("utf-8"))
    path.write_text("## A\n- One.\n- Two.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        apply_ids(path, old.source_sha256)
    fresh = preview_ids(path.read_bytes().decode("utf-8"))
    applied = apply_ids(path, fresh.source_sha256)
    assert applied.assigned == 2
    assert preview_ids(path.read_text(encoding="utf-8")).assigned == 0


def test_duplicate_body_and_ambiguous_marker_remain_unassigned():
    parsed = parse_tracker("## A\n- Same.\n- Same.\n- <!-- unknown --> Maybe.\n")
    assert [w.kind for w in parsed.warnings] == ["duplicate_body", "ambiguous_marker"]
    preview = preview_ids("## A\n- Same.\n- Same.\n- <!-- unknown --> Maybe.\n")
    assert preview.needs_id == (3, 4)


def test_state_survives_restart_and_invalidates_edited_decline(tmp_path: Path):
    store = DecisionStore(tmp_path)
    task = fixture_tasks()[0]
    first = store.reconcile((task,))
    store.decide(task, revision=first["revision"], fingerprint=task.fingerprint,
                 changes={"impact": 3, "urgency": 2, "effort": "<2h", "status": "declined"})
    changed = parse_tracker("## Alpha\n- <!-- TODO-0001 --> Changed. (added 2026-10-01)\n").tasks[0]
    newer = DecisionStore(tmp_path).reconcile((changed,))
    assert newer["tasks"][task.task_id]["status"] == "candidate"
    assert newer["tasks"][task.task_id]["recheck"] is True
    assert newer["tasks"][task.task_id]["impact"] == 3
    with pytest.raises(DecisionError, match="stale"):
        store.decide(changed, revision=first["revision"], fingerprint=changed.fingerprint, changes={"impact": 1})
    vanished = store.reconcile(())
    assert vanished["tasks"][task.task_id]["vanished"]
    assert not store.reconcile((changed,))["tasks"][task.task_id]["vanished"]


def test_state_rejects_unknown_version_and_keeps_prior_bytes_on_write_failure(tmp_path: Path, monkeypatch):
    store = DecisionStore(tmp_path)
    task = fixture_tasks()[0]
    state = store.reconcile((task,))
    previous = store.path.read_bytes()
    def fail_write(_data):
        raise OSError("interrupted state replacement")
    monkeypatch.setattr(store, "_write", fail_write)
    with pytest.raises(OSError, match="interrupted"):
        store.decide(task, revision=state["revision"], fingerprint=task.fingerprint, changes={"impact": 2})
    assert store.path.read_bytes() == previous
    store.path.write_text('{"version": 99, "revision": 0, "tasks": {}}', encoding="utf-8")
    with pytest.raises(DecisionError, match="unsupported"):
        store.read()


def test_two_writers_cannot_apply_same_revision(tmp_path: Path):
    store = DecisionStore(tmp_path)
    task = fixture_tasks()[0]
    state = store.reconcile((task,))
    outcomes = []
    def update(value):
        try:
            store.decide(task, revision=state["revision"], fingerprint=task.fingerprint, changes={"impact": value})
            outcomes.append("saved")
        except DecisionError:
            outcomes.append("stale")
    threads = [threading.Thread(target=update, args=(value,)) for value in (1, 2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=3)
    assert sorted(outcomes) == ["saved", "stale"]


def test_ranking_shortlist_diverges_from_full_order_and_unknown_date_sorts_last(tmp_path: Path):
    tasks = fixture_tasks()
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    for task in tasks:
        state = store.decide(task, revision=state["revision"], fingerprint=task.fingerprint,
                             changes={"impact": 2, "urgency": 2, "effort": "<2h"})
    # A, B and C tie in score; full order prefers A then B by date, while slot two prefers Beta/C.
    result = rank(tasks, state)
    assert [x["task"]["task_id"] for x in result["ready"]] == ["TODO-0001", "TODO-0002", "TODO-0003"]
    assert [x["task"]["task_id"] for x in result["shortlist"]] == ["TODO-0001", "TODO-0003", "TODO-0002"]
    assert "preferred a section" in result["shortlist"][1]["selection_reason"]
    assert result["ready"][0]["score"] == 12


def test_dependency_blocking_cycle_and_missing_target(tmp_path: Path):
    tasks = fixture_tasks()
    store = DecisionStore(tmp_path)
    state = store.reconcile(tasks)
    for task in tasks:
        state = store.decide(task, revision=state["revision"], fingerprint=task.fingerprint,
                             changes={"impact": 1, "urgency": 1, "effort": "half_day"})
    state = store.decide(tasks[1], revision=state["revision"], fingerprint=tasks[1].fingerprint,
                         changes={"depends_on": [tasks[0].task_id]})
    result = rank(tasks, state)
    assert [n["task"]["task_id"] for n in result["groups"]["blocked"]] == [tasks[1].task_id]
    assert next(n for n in result["ready"] if n["task"]["task_id"] == tasks[0].task_id)["terms"]["unlock"] == 2
    state = store.decide(tasks[0], revision=state["revision"], fingerprint=tasks[0].fingerprint,
                         changes={"depends_on": [tasks[1].task_id]})
    assert len(rank(tasks, state)["groups"]["needs_review"]) == 2


def test_dependency_suggestion_requires_explicit_confirmation():
    parsed = parse_tracker("## A\n- <!-- TODO-0001 --> Build index.\n"
                           "- <!-- TODO-0002 --> Run after TODO-0001.\n")
    tasks = parsed.tasks
    state = {"tasks": {
        tasks[0].task_id: {"status": "candidate", "impact": 1, "urgency": 1, "effort": "<2h", "depends_on": []},
        tasks[1].task_id: {"status": "candidate", "impact": 1, "urgency": 1, "effort": "<2h", "depends_on": []},
    }}
    initial = rank(tasks, state)
    assert len(initial["ready"]) == 2
    assert initial["ready"][1]["suggestions"] == [{"target": "TODO-0001", "evidence": "after TODO-0001"}]
    state["tasks"][tasks[1].task_id]["depends_on"] = [tasks[0].task_id]
    confirmed = rank(tasks, state)
    assert len(confirmed["groups"]["blocked"]) == 1
    assert confirmed["ready"][0]["terms"]["unlock"] == 2


def test_review_server_rejects_missing_token_and_stale_post(tmp_path: Path):
    tracker = tmp_path / "tracker.md"
    tracker.write_text("## A\n- <!-- TODO-0001 --> One.\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    store = DecisionStore(state_dir)
    task = parse_tracker(tracker.read_text()).tasks[0]
    state = store.reconcile((task,))
    server = ReviewServer(tracker, state_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/")
        assert conn.getresponse().status == 403
        conn.request("POST", "/api/decision", body="{}", headers={"Content-Type": "application/json"})
        assert conn.getresponse().status == 403
        payload = {"task_id": task.task_id, "fingerprint": task.fingerprint,
                   "source_sha256": hashlib.sha256(tracker.read_bytes()).hexdigest(),
                   "revision": state["revision"], "changes": {"impact": 3, "urgency": 2, "effort": "<2h"}}
        headers = {"Content-Type": "application/json", "Origin": server.origin,
                   "X-Project-Steering-Token": server.token}
        conn.request("POST", "/api/decision", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 200
        conn.request("POST", "/api/decision", body=json.dumps(payload), headers=headers)
        assert conn.getresponse().status == 409
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def test_review_page_scores_unknown_date_task_and_persists_choice(tmp_path: Path):
    tracker = tmp_path / "tracker.md"
    tracker.write_text("## Textbook\n- <!-- TODO-0001 --> Fix equations.\n", encoding="utf-8")
    tasks = parse_tracker(tracker.read_text()).tasks
    state_dir = tmp_path / "state"
    state = DecisionStore(state_dir).reconcile(tasks)
    source_hash = hashlib.sha256(tracker.read_bytes()).hexdigest()
    parsed = parse_tracker(tracker.read_text())
    report = make_report(parsed, tracker=tracker, source_hash=source_hash,
                         source_bytes=len(tracker.read_bytes()), duration_seconds=0,
                         ranking=rank(tasks, state), revision=state["revision"])
    publish_report(state_dir, report, render_markdown(report))
    server = ReviewServer(tracker, state_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/?token=" + server.token)
        page = conn.getresponse().read().decode("utf-8")
        assert "review.js?token=" + server.token in page
        conn.request("GET", "/api/tasks?token=" + server.token)
        initial = json.loads(conn.getresponse().read())
        assert len(initial["ranking"]["groups"]["needs_estimate"]) == 1
        payload = {"task_id": tasks[0].task_id, "fingerprint": tasks[0].fingerprint,
                   "source_sha256": source_hash, "revision": initial["revision"],
                   "changes": {"impact": 2, "urgency": 2, "effort": "half_day"}}
        conn.request("POST", "/api/decision", body=json.dumps(payload), headers={
            "Content-Type": "application/json", "Origin": server.origin,
            "X-Project-Steering-Token": server.token})
        assert conn.getresponse().status == 200
        conn.request("GET", "/api/tasks?token=" + server.token)
        after = json.loads(conn.getresponse().read())
        assert after["ranking"]["shortlist"][0]["task"]["added"] == "unknown"
        assert len(rank(tasks, DecisionStore(state_dir).read())["shortlist"]) == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
