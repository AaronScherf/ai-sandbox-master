import json

import pytest

from core.agent_tasks.tasks import Task, render_card
from core.agent_tasks.work import create_run, load_run


def _task(task_id="t-1", **kw):
    return Task(id=task_id, stage="demo", subject={}, instructions="Do.", context="Ctx.", **kw)


def test_guard_message_uses_the_label(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="inside the output repo"):
        create_run(repo / "work", repo, "demo", [_task()])
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo / "work", repo, "demo", [_task()], repo_label="graph repo")


def test_manifest_keeps_the_graph_repo_key_and_omits_empty_attachments(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "demo", [_task()], run_id="r1")
    data = json.loads((run.root / "manifest.json").read_text(encoding="utf-8"))
    assert data["graph_repo"] == str(repo)
    assert "attachments" not in data["tasks"][0]


def test_attachments_are_recorded_when_present(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    img = tmp_path / "p4.png"
    img.write_bytes(b"png")
    run = create_run(tmp_path / "work", repo, "demo", [_task(attachments=[str(img)])], run_id="r1")
    assert run.task("t-1")["attachments"] == [str(img)]
    assert str(img) in run.card_path("t-1").read_text(encoding="utf-8")


def test_a_missing_attachment_fails_early_and_leaves_no_run_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    work = tmp_path / "work"
    with pytest.raises(ValueError, match="attachment .*missing.png"):
        create_run(work, repo, "demo", [_task(attachments=[str(tmp_path / "missing.png")])], run_id="r1")
    assert not (work / "r1").exists()


def test_an_old_format_in_flight_run_still_loads_and_bounces(tmp_path):
    root = tmp_path / "work" / "old-1"
    (root / "cards").mkdir(parents=True)
    (root / "cards" / "t-1.md").write_text(render_card(_task()), encoding="utf-8", newline="\n")
    manifest = {"run_id": "old-1", "stage": "demo", "created": "2026-10-01T09:00:00", "graph_repo": "X:/repo",
                "tasks": [{"id": "t-1", "subject": {}, "status": "pending", "attempts": 0, "reasons": [],
                           "offered": [], "passages": []}]}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    run = load_run(tmp_path / "work", "old-1")
    run.bounce("t-1", ["needs a fix"])
    assert load_run(tmp_path / "work", "old-1").task("t-1")["status"] == "bounced"


def test_run_ids_may_not_carry_a_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="invalid run id"):
        create_run(tmp_path / "work", repo, "demo", [_task()], run_id="../evil")


def test_non_ascii_card_text_is_written_with_unix_newlines_and_round_trips(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    task = Task(id="t-1", stage="demo", subject={}, instructions="Do.",
                context="Élasticité β = 0.5 — “quoted”\nsecond line")
    run = create_run(tmp_path / "work", repo, "demo", [task], run_id="r1")
    raw = run.card_path("t-1").read_bytes()
    assert b"\r\n" not in raw
    assert raw.decode("utf-8") == render_card(task)
