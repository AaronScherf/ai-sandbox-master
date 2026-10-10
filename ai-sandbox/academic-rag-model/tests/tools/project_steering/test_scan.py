import json
import subprocess
from pathlib import Path

import pytest

from tools.project_steering.cli import _state_dir_is_safe, main
from tools.project_steering.parser import parse_tracker
from tools.project_steering import report as reporting


TRACKER = """# Pending work

## Tutor
- **URGENT — Fix leak:** check the validator
  and preserve the answer. (added 2026-10-08; updated 2026-10-09)
- Paused at user request: run later. (added 2026-10-04)

## Textbook
Things to fix?
- Missing hats from estimators
\t- Nested observation
- Add TOC repair. (added 2026-10-04)

Example from Hansen:
- This pasted bullet is not a to-do. (added 2026-10-04)

### Example detail
- Another pasted bullet. (added 2026-10-04)
"""


def test_parser_preserves_multiline_task_and_surfaces_undated_work():
    parsed = parse_tracker(TRACKER)
    assert len(parsed.tasks) == 4
    assert parsed.tasks[0].first_line == 4
    assert parsed.tasks[0].last_line == 5
    assert parsed.tasks[0].updated == "2026-10-09"
    assert parsed.tasks[0].urgent_suggestion
    assert parsed.tasks[1].deferred_suggestion
    assert parsed.notices[0].kind == "undated_bullet"
    assert parsed.notices[0].first_line == 10
    assert parsed.tasks[2].added == "unknown"
    assert len(parsed.excluded) == 2
    assert parsed.coverage_complete


def test_invalid_date_and_duplicate_body_are_visible():
    parsed = parse_tracker("## Work\n- Valid. (added 2026-10-04)\n- Valid. (added 2026-10-04)\n- Bad. (added 2026-99-99)\n")
    assert len(parsed.tasks) == 1
    assert len({task.task_id for task in parsed.tasks}) == 1
    assert {warning.kind for warning in parsed.warnings} == {"duplicate_body", "invalid_date"}


def test_comma_updated_date_variant_from_live_tracker():
    parsed = parse_tracker("## Work\n- Add a guide. (added 2026-10-05, updated 2026-10-06)\n")
    assert parsed.coverage_complete
    assert parsed.tasks[0].updated == "2026-10-06"


def test_dated_bullet_under_subsection_is_eligible():
    parsed = parse_tracker("## Brainstorm\n### Notes\n- A real follow-up. (added 2026-10-07)\n")
    assert len(parsed.tasks) == 1
    assert parsed.notices[0].kind == "dated_subsection_bullet"
    assert parsed.coverage_complete


def test_scan_writes_complete_view_without_changing_tracker(tmp_path: Path, capsys):
    tracker = tmp_path / "tracker.md"
    state = tmp_path / "state"
    tracker.write_text(TRACKER, encoding="utf-8")
    before = tracker.read_bytes()

    assert main(["scan", "--tracker", str(tracker), "--state-dir", str(state), "--format", "json"]) == 0
    stdout = json.loads(capsys.readouterr().out)
    latest = json.loads((state / "latest.json").read_text(encoding="utf-8"))
    snapshot = json.loads((state / latest["snapshot"]).read_text(encoding="utf-8"))
    view = (state / latest["ranked_view"]).read_text(encoding="utf-8")

    assert stdout["coverage_complete"]
    assert snapshot["source_sha256"] == latest["source_sha256"]
    assert "Missing hats from estimators" in view
    assert "Coverage: complete" in view
    assert "No owner-scored ready tasks yet" in view
    assert tracker.read_bytes() == before


def test_complete_scan_returns_zero_and_repeated_content_is_stable(tmp_path: Path, capsys):
    tracker = tmp_path / "tracker.md"
    state = tmp_path / "state"
    tracker.write_text("# Pending\n## Work\n- Fix one. (added 2026-10-04)\n", encoding="utf-8")
    args = ["scan", "--tracker", str(tracker), "--state-dir", str(state)]
    assert main(args) == 0
    first = (state / json.loads((state / "latest.json").read_text())["ranked_view"]).read_text()
    capsys.readouterr()
    assert main(args) == 0
    second = (state / json.loads((state / "latest.json").read_text())["ranked_view"]).read_text()
    assert first == second


def test_publish_failure_preserves_last_complete_pointer(tmp_path: Path, monkeypatch):
    original_write = reporting._write_atomic
    sample = {"source_sha256": "abc", "run_at": "2026-10-09T00:00:00+00:00"}
    first = reporting.publish_report(tmp_path, sample, "first\n")
    previous = (tmp_path / "latest.json").read_bytes()

    def fail_latest(path: Path, content: str) -> None:
        if path.name == "latest.json":
            raise OSError("simulated interrupted pointer update")
        original_write(path, content)

    monkeypatch.setattr(reporting, "_write_atomic", fail_latest)
    with pytest.raises(OSError, match="simulated"):
        reporting.publish_report(tmp_path, sample, "second\n")
    assert (tmp_path / "latest.json").read_bytes() == previous
    assert (tmp_path / first["ranked_view"]).read_text() == "first\n"


def test_state_dir_must_stay_outside_tracked_source(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    tracker = repo / "docs" / "tracker.md"
    tracker.parent.mkdir()
    tracker.write_text("## Work\n- Task. (added 2026-10-04)\n", encoding="utf-8")
    assert not _state_dir_is_safe(tracker, repo / "reports")
    assert _state_dir_is_safe(tracker, repo / ".git" / "project-steering")
    assert _state_dir_is_safe(tracker, tmp_path / "reports")


def test_missing_tracker_returns_error_without_report(tmp_path: Path, capsys):
    state = tmp_path / "state"
    assert main(["scan", "--tracker", str(tmp_path / "missing" / "tracker.md"), "--state-dir", str(state)]) == 2
    assert "scan failed" in capsys.readouterr().err
    assert not state.exists()
