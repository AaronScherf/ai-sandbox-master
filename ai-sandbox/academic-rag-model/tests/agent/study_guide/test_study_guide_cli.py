# tests/agent/study_guide/test_study_guide_cli.py
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import (
    cmd_apply_review, cmd_draft, cmd_plan, main, plan_path_for, review_path_for,
)
from agent.study_guide.spec import load_spec
from sg_helpers import CARDS, CHUNKS, FakeLLM, StubSearch, hit, make_spec, root  # noqa: F401 (fixtures)

SPEC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"

  [[topic.source]]
  kind = "discover"
  query = "wald"
  min_score = 0.5
  max = 3
"""


@pytest.fixture
def spec_file(make_spec, tmp_path):
    make_spec(SPEC)
    return tmp_path / "spec.toml"


@pytest.fixture
def search():
    return StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})


def _plan(spec_file, root, search, **kw):
    return cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS, **kw)


def test_plan_writes_ledger_and_review_items(spec_file, root, search, capsys):
    assert _plan(spec_file, root, search) == 0
    spec = load_spec(spec_file)
    plan = json.loads(plan_path_for(root, spec).read_text(encoding="utf-8"))
    assert plan["spec_id"] == "demo" and plan["topics"][0]["entries"][0]["status"] == "accepted"
    items = json.loads(review_path_for(root, spec).read_text(encoding="utf-8"))
    assert [i["key"] for i in items] == ["Wald|cam-1", "Wald|han-1"]
    out = capsys.readouterr().out
    assert "1 accepted" in out and "1 pending" in out and "Wald" in out
    assert plan_path_for(root, spec).as_posix().endswith("academic_notes/econ/guide_plans/demo.plan.json")


def test_plan_refuses_to_overwrite_without_force(spec_file, root, search):
    assert _plan(spec_file, root, search) == 0
    assert _plan(spec_file, root, search) == 2
    assert _plan(spec_file, root, search, force=True) == 0


def test_plan_reports_spec_and_plan_errors_as_input_errors(tmp_path, root, search, make_spec):
    assert cmd_plan(str(tmp_path / "missing.toml"), root, search=search) == 2
    make_spec(SPEC.replace('labels = ["7.2"]', 'labels = ["99"]').replace('kind = "discover"', 'kind = "discover"\n  max_per_file = 1'))
    empty = StubSearch({"textbook": []})
    assert cmd_plan(str(tmp_path / "spec.toml"), root, search=empty, chunks=CHUNKS, cards=CARDS) == 2


def test_plan_without_a_client_or_search_is_exit_1(spec_file, root):
    assert cmd_plan(str(spec_file), root) == 1


def test_apply_review_updates_the_plan(spec_file, root, search, tmp_path, capsys):
    _plan(spec_file, root, search)
    spec = load_spec(spec_file)
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps({"Wald|han-1": "drop"}), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(decisions)) == 0
    entries = json.loads(plan_path_for(root, spec).read_text(encoding="utf-8"))["topics"][0]["entries"]
    assert [e["status"] for e in entries] == ["accepted", "dropped"]
    assert "1 dropped" in capsys.readouterr().out
    decisions.write_text(json.dumps({"Wald|nope": "keep"}), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(decisions)) == 2


def _decided(spec_file, root, search, tmp_path):
    _plan(spec_file, root, search)
    spec = load_spec(spec_file)
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"Wald|han-1": "keep"}), encoding="utf-8")
    cmd_apply_review(str(plan_path_for(root, spec)), str(d))
    return spec


def test_draft_end_to_end(spec_file, root, search, tmp_path):
    spec = _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    assert cmd_draft(str(spec_file), root, llm=llm, chunks=CHUNKS, cards=CARDS) == 0
    assert (Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md").is_file()
    assert len(llm.calls) == 1


def test_draft_blocks_on_pending_unless_accepted(spec_file, root, search):
    _plan(spec_file, root, search)
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True) == 0


def test_draft_dry_run_prints_counts_and_makes_no_call(spec_file, root, search, tmp_path, capsys):
    _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    assert cmd_draft(str(spec_file), root, llm=llm, dry_run=True, chunks=CHUNKS, cards=CARDS) == 0
    out = capsys.readouterr().out
    assert llm.calls == [] and "DRY RUN" in out and "1 call" in out and "2 passages" in out and "demo.md" in out


def test_draft_rejects_a_stale_plan_before_any_call(spec_file, root, search, tmp_path):
    _decided(spec_file, root, search, tmp_path)
    llm = FakeLLM()
    gone = [c for c in CHUNKS if c["chunk_id"] != "cam-1"]
    assert cmd_draft(str(spec_file), root, llm=llm, chunks=gone, cards=CARDS) == 2
    assert llm.calls == []


def test_draft_without_a_plan_file_is_an_input_error(spec_file, root):
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2


def test_draft_refuses_overwrite_and_reports_model_failures(spec_file, root, search, tmp_path):
    _decided(spec_file, root, search, tmp_path)
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 0
    assert cmd_draft(str(spec_file), root, llm=FakeLLM(), chunks=CHUNKS, cards=CARDS) == 2
    assert cmd_draft(str(spec_file), root, llm=FakeLLM([RuntimeError("503")]), chunks=CHUNKS, cards=CARDS, force=True) == 4


def test_draft_model_override_is_recorded(spec_file, root, search, tmp_path, monkeypatch):
    _decided(spec_file, root, search, tmp_path)
    seen = {}

    class Capturing(FakeLLM):
        def __init__(self, client, model):
            super().__init__()
            self.model = model
            seen["model"] = model

    monkeypatch.setattr(cli, "GeminiClient", Capturing)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: object())
    assert cmd_draft(str(spec_file), root, model="gemini-test", chunks=CHUNKS, cards=CARDS) == 0
    assert seen["model"] == "gemini-test"


def test_main_dispatches(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(cli, "cmd_plan", lambda spec, root, **kw: calls.setdefault("plan", (spec, kw)) and 0)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: "client")
    assert main(["plan", "s.toml", "--root", str(tmp_path), "--force"]) == 0
    spec, kw = calls["plan"]
    assert spec == "s.toml" and kw["force"] is True and kw["client"] == "client"
    monkeypatch.setattr(cli, "cmd_draft", lambda spec, root, **kw: calls.setdefault("draft", kw) and 0)
    assert main(["draft", "s.toml", "--root", str(tmp_path), "--tag", "t", "--dry-run", "--model", "m",
                 "--accept-unreviewed"]) == 0
    assert calls["draft"]["tag"] == "t" and calls["draft"]["dry_run"] and calls["draft"]["model"] == "m"
    assert calls["draft"]["accept_unreviewed"] is True


def test_run_plans_and_stops_for_review_without_yes(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "cmd_plan", lambda spec, root, **kw: seen.append("plan") or 0)
    monkeypatch.setattr(cli, "cmd_draft", lambda spec, root, **kw: seen.append("draft") or 0)
    monkeypatch.setattr(cli, "_paid_client", lambda env_file: "client")
    assert main(["run", "s.toml", "--root", str(tmp_path)]) == 0 and seen == ["plan"]
    seen.clear()
    assert main(["run", "s.toml", "--root", str(tmp_path), "--yes"]) == 0 and seen == ["plan", "draft"]


def test_baseline_spec_for_the_wald_guide_is_valid_and_matches_the_recovered_recipe():
    path = Path(__file__).resolve().parents[3] / "guide_specs" / "econometrics" / "wald_lm_lr_tests.toml"
    spec = load_spec(path)
    assert (spec.id, spec.course, spec.prompt, spec.label_match) == ("wald_lm_lr_tests", "econometrics", "tutor_v1", "citation-substring")
    assert spec.draft_model == "gemini-3.1-flash-lite" and (spec.top_k, spec.file_top_k) == (180, 80)
    assert [t.title for t in spec.topics] == [
        "Cameron & Trivedi Section 7.2: Wald test",
        "Cameron & Trivedi Section 7.3: likelihood ratio test",
        "Cameron & Trivedi Section 7.3.5: Lagrange multiplier test",
        "Hansen Section 9.10 and 9.11: Wald tests",
        "Hansen Section 9.11 reference check: likelihood ratio test",
        "Hansen Section 9.17: score (Lagrange multiplier) test",
    ]
    lr = spec.topics[1].sources[0]
    assert (lr.kind, lr.book, lr.labels, lr.exclude_labels, lr.max) == (
        "section", "Cameron_Microeconometrics", ("7.3.1", "7.3.2", "7.3.3", "7.3.4"), ("7.3.5",), 12)
    assert spec.topics[3].sources[0].labels == ("9.10", "9.11") and spec.topics[3].sources[0].book == "Hansen_ECONOMETRICS"
    assert len(spec.notes) == 1 and spec.notes[0].heading == "Source-reference discrepancy"
    comparison = spec.comparisons[0]
    assert comparison.title == "Comparing and choosing among the three tests" and comparison.take == 3
    assert comparison.from_topics == tuple(t.title for i, t in enumerate(spec.topics) if i != 4)
