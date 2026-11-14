import json
import os
import shutil

import pytest

from pipelines.transcribe_notes.agent_work import load_manifest
from pipelines.transcribe_notes.framed_explainer.results import ResultError
from pipelines.transcribe_notes.framed_explainer.submit import submit

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "framed_explainer")


def _run_dir(tmp_path, result_name="result_ok.json"):
    run = tmp_path / "run"
    run.mkdir()
    shutil.copy(os.path.join(FIX, "facts_ok.json"), run / "facts.json")
    shutil.copy(os.path.join(FIX, result_name), run / "result.json")
    return str(run)


def test_submit_writes_resolved_state_and_counts(tmp_path):
    run = _run_dir(tmp_path)
    report = submit(run)
    resolved = json.load(open(os.path.join(run, "result.resolved.json"), encoding="utf-8"))
    state = json.load(open(os.path.join(run, "state.json"), encoding="utf-8"))
    assert resolved["coverage"]["fallback_nearest"] == 1
    assert report.counts == {"assigned": 2, "fallback_nearest": 1, "section": 1}
    assert report.needs_review == ["s2"]
    assert state["s1"]["state"] == "validated" and state["s2"]["state"] == "needs_review"
    assert state["s1"]["fingerprint"] == "fp1"


def test_submit_invalid_result_raises_and_writes_nothing(tmp_path):
    run = _run_dir(tmp_path, "result_dup_stroke.json")
    with pytest.raises(ResultError) as exc:
        submit(run)
    assert exc.value.code == "duplicate_stroke"
    assert not os.path.exists(os.path.join(run, "result.resolved.json"))


def test_submit_marks_manifest_submitted(tmp_path):
    from pipelines.transcribe_notes.agent_work import ManifestEntry, save_manifest
    run = _run_dir(tmp_path)
    save_manifest(run, [ManifestEntry("task-0001", "cards", [1, 2], "pending")])
    submit(run)
    assert [e.status for e in load_manifest(run)] == ["submitted"]
