# tests/agent/study_guide/test_study_guide_revise_run.py
import hashlib
import json
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import cmd_plan, plan_path_for
from agent.study_guide.revise.edits import ReviseError, load_report
from agent.study_guide.revise.evidence import EvidenceChunk
from agent.study_guide.revise.run import build_report, cmd_apply_revise, cmd_revise, report_path, revised_path
from agent.study_guide.spec import load_spec
from rv_helpers import ScriptedLLM, bag_embed
from sg_helpers import CARDS, CHUNKS, StubSearch, hit, make_spec, root  # noqa: F401 (fixtures)

SPEC = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "file"
  file = "sl"

[revise]
criteria = ["relevance", "organization"]
relevance_low = 0.3
relevance_high = 0.9
min_block_words = 20

  [[revise.evidence]]
  kind = "file"
  file = "sl"
"""
HEADER = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'
GUIDE = ("---\ntitle: \"Demo\"\n---\n\n# Demo\n\n## Wald\n\n" + "wald statistic words " * 12 +
         "\n\n## Software packages\n\n" + "package install words " * 12 + "\n")
VOCAB = ["wald", "package"]
EVIDENCE = [EvidenceChunk("e1", "Exam, p. 1", 1.0, (1.0, 0.0))]


@pytest.fixture
def env(make_spec, root, tmp_path):
    make_spec(SPEC, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    search = StubSearch({"textbook": [hit("cam-1", .9)]})
    assert cmd_plan(str(spec_file), root, search=search, chunks=CHUNKS, cards=CARDS) == 0
    guide = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    guide.write_text(GUIDE, encoding="utf-8")
    return spec_file, load_spec(spec_file), guide


def _build(spec, guide, llm=None, stages=("relevance", "organization")):
    plan = cli.load_plan(plan_path_for(str(guide.parents[3]), spec))
    return build_report(spec, str(guide), plan, stages=stages, llm=llm or ScriptedLLM([{"edits": []}]),
                        embed=bag_embed(VOCAB), evidence=EVIDENCE, chunks=CHUNKS, now="2026-10-08T00:00:00+00:00")


def test_report_has_hash_blocks_and_stage_edits(env):
    _, spec, guide = env
    report = _build(spec, guide)
    assert report.guide_sha256 == hashlib.sha256(guide.read_bytes()).hexdigest()
    assert [(e.stage, e.type) for e in report.edits] == [("relevance", "delete")]
    assert report.edits[0].targets and len(report.blocks) >= 3 and report.protected_blocks


def test_stage_selection_limits_what_runs(env):
    _, spec, guide = env
    llm = ScriptedLLM([])
    report = _build(spec, guide, llm=llm, stages=("relevance",))
    assert llm.calls == [] and {e.stage for e in report.edits} == {"relevance"}


def test_stages_outside_the_spec_criteria_are_refused(env):
    _, spec, guide = env
    with pytest.raises(ReviseError, match="criteria"):
        _build(spec, guide, stages=("dedup",))


def test_cmd_revise_writes_the_report_and_review_items(env, root):
    spec_file, spec, guide = env
    llm = ScriptedLLM([{"edits": []}])
    code = cmd_revise(str(spec_file), root, guide_path=str(guide), llm=llm, embed=bag_embed(VOCAB), chunks=CHUNKS, cards=CARDS,
                      search=lambda *a, **k: [], evidence=EVIDENCE)
    assert code == 0
    rp = report_path(root, spec, str(guide), "")
    assert rp.is_file() and rp.with_name(rp.name.replace(".revise.json", ".revise.review.json")).is_file()


def test_dry_run_makes_no_calls_and_writes_nothing(env, root, capsys):
    spec_file, spec, guide = env
    code = cmd_revise(str(spec_file), root, guide_path=str(guide), dry_run=True, chunks=CHUNKS, cards=CARDS)
    out = capsys.readouterr().out
    assert code == 0 and "DRY RUN" in out and "blocks" in out and not report_path(root, spec, str(guide), "").exists()


def test_apply_revise_applies_accepted_edits_and_records_provenance(env, root, tmp_path):
    spec_file, spec, guide = env
    cmd_revise(str(spec_file), root, guide_path=str(guide), llm=ScriptedLLM([{"edits": []}]), embed=bag_embed(VOCAB),
               chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    edit_id = load_report(report_path(root, spec, str(guide), "")).edits[0].id
    decisions = tmp_path / "d.json"
    decisions.write_text(json.dumps({edit_id: "accept"}), encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 0
    revised = revised_path(str(guide), "").read_text(encoding="utf-8")
    assert "package install" not in revised and "wald statistic" in revised
    assert "revised_from:" in revised and "revise_edits_applied: 1" in revised
    assert "package install" in guide.read_text(encoding="utf-8")
    assert revised_path(str(guide), "").with_name("demo.revised.changelog.md").is_file()


def test_apply_revise_refuses_a_guide_that_changed_and_never_overwrites(env, root, tmp_path, capsys):
    spec_file, spec, guide = env
    cmd_revise(str(spec_file), root, guide_path=str(guide), llm=ScriptedLLM([{"edits": []}]), embed=bag_embed(VOCAB),
               chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    decisions = tmp_path / "d.json"
    decisions.write_text("{}", encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 0
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions)) == 2
    assert "already exists" in capsys.readouterr().out
    guide.write_text(GUIDE + "\nextra\n", encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions), force=True) == 2
    assert "changed since" in capsys.readouterr().out


def test_a_spec_without_a_revise_table_is_an_error(make_spec, root, tmp_path, capsys):
    make_spec(SPEC.split("[revise]")[0], header=HEADER)
    assert cmd_revise(str(tmp_path / "spec.toml"), root, guide_path="g.md", dry_run=True) == 2
    assert "[revise]" in capsys.readouterr().out


def test_main_dispatches_revise_commands(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setattr(cli, "cmd_revise", lambda spec, root, **kw: seen.setdefault("revise", kw) and 0)
    monkeypatch.setattr(cli, "cmd_apply_revise", lambda spec, root, **kw: seen.setdefault("apply", kw) and 0)
    assert cli.main(["revise", "s.toml", "--root", str(tmp_path), "--guide", "g.md", "--stages", "relevance,dedup",
                     "--tag", "t", "--dry-run"]) == 0
    assert seen["revise"]["stages"] == ["relevance", "dedup"] and seen["revise"]["dry_run"] is True
    assert cli.main(["apply-revise", "s.toml", "--root", str(tmp_path), "--guide", "g.md", "--decisions", "d.json"]) == 0
    assert seen["apply"]["decisions_path"] == "d.json"


def test_a_tag_that_could_leave_the_vault_is_refused(env, root, tmp_path, capsys):
    spec_file, spec, guide = env
    assert cmd_revise(str(spec_file), root, guide_path=str(guide), tag="../evil", dry_run=True) == 2
    assert "tag" in capsys.readouterr().out
    decisions = tmp_path / "d.json"
    decisions.write_text("{}", encoding="utf-8")
    assert cmd_apply_revise(str(spec_file), root, guide_path=str(guide), decisions_path=str(decisions), tag="a/b") == 2
    assert "tag" in capsys.readouterr().out


def test_the_relevance_judge_runs_inside_the_relevance_stage(make_spec, root, tmp_path):
    from agent.study_guide.revise.segment import segment, split_frontmatter
    text = SPEC.replace("relevance_low = 0.3", "relevance_low = 0.0\njudge_fraction = 1.0\nscope = \"Only the Wald test.\"")
    make_spec(text, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    assert cmd_plan(str(spec_file), root, search=StubSearch({"textbook": [hit("cam-1", .9)]}), chunks=CHUNKS, cards=CARDS) == 0
    guide = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    guide.write_text(GUIDE, encoding="utf-8")
    spec = load_spec(spec_file)
    pkg = next(b for b in segment(split_frontmatter(GUIDE)[1]) if b.heading_path[-1] == "Software packages")
    llm = ScriptedLLM([{"verdicts": [{"block": pkg.id, "verdict": "delete", "rationale": "software tutorial"}]}])
    report = _build(spec, guide, llm=llm, stages=("relevance",))
    assert [(e.type, e.targets, e.rationale.startswith("judge:")) for e in report.edits] == [("delete", [pkg.id], True)]
    assert "Only the Wald test." in llm.calls[0]
