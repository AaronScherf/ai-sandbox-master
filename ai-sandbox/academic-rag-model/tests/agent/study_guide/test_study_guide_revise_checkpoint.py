# tests/agent/study_guide/test_study_guide_revise_checkpoint.py
"""A revise run saves each finished stage (and each audited section) so a crashed run resumes instead of re-paying."""
from pathlib import Path

import pytest

from agent.study_guide import cli
from agent.study_guide.cli import cmd_plan, plan_path_for
from agent.study_guide.revise.checkpoint import Checkpoint
from agent.study_guide.revise.run import build_report, cmd_revise, report_path
from agent.study_guide.spec import load_spec
from rv_helpers import ScriptedLLM, bag_embed
from sg_helpers import CARDS, CHUNKS, StubSearch, hit, make_spec, root  # noqa: F401 (fixtures)
from test_study_guide_revise_run import EVIDENCE, GUIDE, HEADER, SPEC, VOCAB

ALL = SPEC.replace('criteria = ["relevance", "organization"]', 'criteria = ["relevance", "correctness", "organization"]')


def test_put_get_clear_and_key_mismatch(tmp_path):
    path = tmp_path / "x.partial.json"
    cp = Checkpoint(path, "k1")
    assert cp.get("relevance") is None
    cp.put("relevance", {"edits": [1]})
    assert Checkpoint(path, "k1").get("relevance") == {"edits": [1]}
    assert Checkpoint(path, "other-key").get("relevance") is None      # inputs changed: ignore the old work
    cp.clear()
    assert not path.exists()


def test_a_corrupt_checkpoint_is_ignored(tmp_path):
    path = tmp_path / "x.partial.json"
    path.write_text("{not json", encoding="utf-8")
    assert Checkpoint(path, "k").get("a") is None


@pytest.fixture
def env(make_spec, root, tmp_path):
    make_spec(ALL, header=HEADER)
    spec_file = tmp_path / "spec.toml"
    assert cmd_plan(str(spec_file), root, search=StubSearch({"textbook": [hit("cam-1", .9)]}), chunks=CHUNKS, cards=CARDS) == 0
    guide = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    guide.write_text(GUIDE, encoding="utf-8")
    return spec_file, load_spec(spec_file), guide


class CountingEmbed:
    def __init__(self):
        self.inner, self.calls = bag_embed(VOCAB), 0

    def __call__(self, text):
        self.calls += 1
        return self.inner(text)


def _plan(spec, guide):
    return cli.load_plan(plan_path_for(str(guide.parents[3]), spec))


def test_finished_units_are_reused_and_not_recomputed(env, tmp_path):
    _, spec, guide = env
    cp = Checkpoint(tmp_path / "p.json", "k")
    emb, llm = CountingEmbed(), ScriptedLLM([{"findings": []}, {"edits": []}])
    first = build_report(spec, str(guide), _plan(spec, guide), stages=("relevance", "correctness", "organization"), llm=llm,
                         embed=emb, evidence=EVIDENCE, chunks=CHUNKS, now="n", checkpoint=cp)
    assert emb.calls > 0 and len(llm.calls) == 2
    emb2, llm2 = CountingEmbed(), ScriptedLLM([])
    second = build_report(spec, str(guide), _plan(spec, guide), stages=("relevance", "correctness", "organization"), llm=llm2,
                          embed=emb2, evidence=EVIDENCE, chunks=CHUNKS, now="n", checkpoint=Checkpoint(tmp_path / "p.json", "k"))
    assert emb2.calls == 0 and llm2.calls == [] and second == first


def test_a_crashed_run_resumes_and_the_checkpoint_is_removed_on_success(env, root):
    spec_file, spec, guide = env
    emb = CountingEmbed()
    crash = ScriptedLLM([{"findings": []}, RuntimeError("boom")])
    kw = dict(guide_path=str(guide), embed=emb, chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    assert cmd_revise(str(spec_file), root, llm=crash, **kw) == 4
    partial = report_path(root, spec, str(guide), "").with_name("demo.revise.partial.json")
    assert partial.is_file()
    before = emb.calls
    ok = ScriptedLLM([{"edits": []}])
    assert cmd_revise(str(spec_file), root, llm=ok, **kw) == 0
    assert emb.calls == before and len(ok.calls) == 1          # relevance and the audit were reused
    assert not partial.exists() and report_path(root, spec, str(guide), "").is_file()


def test_no_resume_discards_the_checkpoint(env, root):
    spec_file, spec, guide = env
    emb = CountingEmbed()
    kw = dict(guide_path=str(guide), embed=emb, chunks=CHUNKS, cards=CARDS, search=lambda *a, **k: [], evidence=EVIDENCE)
    assert cmd_revise(str(spec_file), root, llm=ScriptedLLM([{"findings": []}, RuntimeError("boom")]), **kw) == 4
    before = emb.calls
    assert cmd_revise(str(spec_file), root, llm=ScriptedLLM([{"findings": []}, {"edits": []}]), resume=False, **kw) == 0
    assert emb.calls > before
