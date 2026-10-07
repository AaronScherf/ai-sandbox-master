# tests/agent/study_guide/test_study_guide_enhance_cmd.py
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import cmd_apply_review, cmd_enhance, cmd_plan, main, plan_path_for
from agent.study_guide.spec import load_spec
from sg_helpers import CARDS, CHUNKS, StubSearch, hit, make_spec, root  # noqa: F401 (fixtures)

SPEC = """
[models]
enhance = "gemini-test-enhance"

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

[[topic]]
title = "LM"
instruction = "Explain LM."

  [[topic.source]]
  kind = "file"
  file = "sl"
"""
HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'


@pytest.fixture
def setup(make_spec, root, tmp_path):
    make_spec(SPEC, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})
    assert cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS) == 0
    spec = load_spec(spec_file)
    draft = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    draft.write_text("---\ntitle: \"Demo\"\n---\n\nBody\n", encoding="utf-8")
    return spec_file, spec, draft


@pytest.fixture
def captured(monkeypatch):
    seen = {}

    def fake_run(guide, **kw):
        seen["guide"] = guide
        seen["kw"] = kw
        return 0

    monkeypatch.setattr(cli, "enhance_run", fake_run)
    return seen


def _decide(spec, root, tmp_path, decisions):
    d = tmp_path / "d.json"
    d.write_text(json.dumps(decisions), encoding="utf-8")
    assert cmd_apply_review(str(plan_path_for(root, spec)), str(d)) == 0


def test_pending_blocks_enhance_unless_accepted(setup, root, captured):
    spec_file, spec, draft = setup
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS) == 2
    assert "kw" not in captured


def test_extra_sources_and_options_are_passed_through(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    _decide(spec, root, tmp_path, {"Wald|han-1": "keep"})
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS,
                       worked_example=True, min_words=900, force=True, dry_run=True, env_file="e.env") == 0
    kw = captured["kw"]
    assert captured["guide"] == str(draft)
    assert kw["topics"] == ["Wald", "LM"] and kw["model"] == "gemini-test-enhance"
    assert kw["mode"] == "improve" and kw["worked_example"] is True and kw["min_words"] == 900
    assert kw["force"] is True and kw["dry_run"] is True and kw["env_file"] == "e.env" and kw["output"] is None
    extras = kw["extra_sources"]
    assert [(e.topic, e.chunk_id) for e in extras] == [("Wald", "cam-1"), ("Wald", "han-1"), ("LM", "sl-1"), ("LM", "sl-2")]
    assert extras[2].doc_type == "ta_notes" and extras[0].doc_type == "textbook" and extras[0].citation


def test_dropped_passages_are_not_sent(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    _decide(spec, root, tmp_path, {"Wald|han-1": "drop"})
    cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS)
    assert [e.chunk_id for e in captured["kw"]["extra_sources"] if e.topic == "Wald"] == ["cam-1"]


def test_model_override_mode_and_tag(setup, root, tmp_path, captured):
    spec_file, spec, draft = setup
    cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True,
                model="other-model", mode="rewrite", tag="e1")
    kw = captured["kw"]
    assert kw["model"] == "other-model" and kw["mode"] == "rewrite"
    assert kw["output"] == str(draft.with_name("demo.enhanced.e1.md"))


def test_stale_plan_is_rejected(setup, root, captured):
    spec_file, spec, draft = setup
    gone = [c for c in CHUNKS if c["chunk_id"] != "cam-1"]
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=gone, cards=CARDS, accept_unreviewed=True) == 2
    assert "kw" not in captured


def test_missing_draft_is_an_input_error(setup, root, captured):
    spec_file, spec, draft = setup
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft.with_name("nope.md")), chunks=CHUNKS, cards=CARDS,
                       accept_unreviewed=True) == 2


def test_exit_code_of_the_enhance_run_is_returned(setup, root, monkeypatch):
    spec_file, spec, draft = setup
    monkeypatch.setattr(cli, "enhance_run", lambda guide, **kw: 3)
    assert cmd_enhance(str(spec_file), root, draft_path=str(draft), chunks=CHUNKS, cards=CARDS, accept_unreviewed=True) == 3


def test_main_dispatches_enhance(monkeypatch, tmp_path):
    calls = {}
    monkeypatch.setattr(cli, "cmd_enhance", lambda spec, root, **kw: calls.update(kw) or 0)
    assert main(["enhance", "s.toml", "--root", str(tmp_path), "--draft", "g.md", "--mode", "rewrite",
                 "--worked-example", "--min-words", "700", "--tag", "e1", "--model", "m", "--force",
                 "--dry-run", "--accept-unreviewed", "--plan", "p.json"]) == 0
    assert calls["draft_path"] == "g.md" and calls["mode"] == "rewrite" and calls["worked_example"] is True
    assert calls["min_words"] == 700 and calls["tag"] == "e1" and calls["model"] == "m"
    assert calls["plan_path"] == "p.json" and calls["accept_unreviewed"] is True
    main(["enhance", "s.toml", "--root", str(tmp_path), "--draft", "g.md"])
    assert calls["mode"] == "improve" and calls["min_words"] == 1400
