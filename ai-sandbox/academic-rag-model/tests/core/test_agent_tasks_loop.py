"""The loop with a toy stage and a plain-dict target: proves it has no concept_graph dependency."""
import types

import pytest

from core.agent_tasks import loop
from core.agent_tasks.tasks import Task
from core.agent_tasks.work import load_run


def _stage(applied):
    def validate_result(entry, result, target):
        return [] if "answer" in result else ["answer is required"]

    def apply_result(target, entry, result, prov):
        target[entry["id"]] = {"answer": result["answer"], "prov": prov}
        applied.append(entry["id"])
        return None

    return types.SimpleNamespace(validate_result=validate_result, apply_result=apply_result)


def _run(tmp_path, n=1):
    repo = tmp_path / "repo"
    repo.mkdir()
    tasks = [Task(id=f"t-{i}", stage="toy", subject={}, instructions="Answer.", context="Q") for i in range(n)]
    return loop.collect_run("toy", tasks, tmp_path / "work", repo, run_id="r1")


def _fill(run, task_id, body):
    path = run.card_path(task_id)
    path.write_text(path.read_text(encoding="utf-8").replace("```yaml\n```", f"```yaml\n{body}\n```"),
                    encoding="utf-8", newline="\n")


def test_collect_returns_none_without_tasks(tmp_path):
    assert loop.collect_run("toy", [], tmp_path / "work", tmp_path / "repo") is None


def test_submit_applies_a_valid_card_with_provenance(tmp_path):
    run, target, applied = _run(tmp_path), {}, []
    _fill(run, "t-0", "answer: 42")
    report = loop.submit_run(run, _stage(applied), target, "test-agent")
    assert report.applied == ["t-0"]
    assert target["t-0"]["prov"] == {"driver": "agent", "agent": "test-agent", "run": "r1"}
    assert load_run(tmp_path / "work", "r1").task("t-0")["status"] == "applied"


def test_invalid_card_bounces_and_untouched_card_is_left_alone(tmp_path):
    run, target = _run(tmp_path, n=2), {}
    _fill(run, "t-0", "other: 1")
    report = loop.submit_run(run, _stage([]), target)
    assert report.bounced == {"t-0": ["answer is required"]}
    assert report.untouched == ["t-1"]


def test_stage_functions_are_looked_up_at_call_time(tmp_path):
    run, target = _run(tmp_path), {}
    _fill(run, "t-0", "answer: 1")
    mod = _stage([])
    mod.validate_result = lambda entry, result, tgt: ["patched after import"]
    assert loop.submit_run(run, mod, target).bounced == {"t-0": ["patched after import"]}


def test_a_card_that_raises_is_bounced_with_the_target_label(tmp_path):
    run, target = _run(tmp_path), {}
    _fill(run, "t-0", "answer: 1")
    mod = _stage([])
    mod.apply_result = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk"))
    report = loop.submit_run(run, mod, target, target_label="graph")
    assert "part of the card may already be in the graph" in report.bounced["t-0"][0]


def test_api_run_stops_at_the_cost_gate_before_sending(tmp_path):
    run, target, sent = _run(tmp_path), {}, []
    with pytest.raises(loop.BudgetError, match="--approve-cost"):
        loop.api_run(run, _stage([]), target, lambda p: sent.append(p) or "answer: 1", None, price_out=100000.0)
    assert sent == []


def test_api_run_applies_replies_through_the_same_path(tmp_path):
    run, target = _run(tmp_path), {}
    report = loop.api_run(run, _stage([]), target, lambda p: "```yaml\nanswer: 7\n```", 1.0, agent_name="g-test")
    assert report.applied == ["t-0"]
    assert target["t-0"]["prov"]["driver"] == "api"
