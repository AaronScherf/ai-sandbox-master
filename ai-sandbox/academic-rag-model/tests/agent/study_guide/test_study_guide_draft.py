# tests/agent/study_guide/test_study_guide_draft.py
import json

import pytest

from agent.study_guide.draft import DraftError, draft_guide, output_path
from agent.study_guide.plan import PendingReviewError, Plan, PlanEntry, TopicPlan
from agent.summary_enhance.llm import UnusableResponse
from agent.summary_enhance.source_loader import load_guide
from sg_helpers import CHUNKS, FakeLLM

NOW = "2026-10-05T00:00:00+00:00"
TOPICS = """
[[topic]]
title = "Wald"
instruction = "Explain Wald."

  [[topic.source]]
  kind = "file"
  file = "x"

[[topic]]
title = "LM"
instruction = "Explain LM."

  [[topic.source]]
  kind = "file"
  file = "y"

[[note]]
heading = "A static note"
body = "Note body text."

[[comparison]]
title = "Compare"
instruction = "Compare the two tests."
from = ["Wald", "LM"]
take = 1
"""


def _e(cid, status="accepted", rule="section"):
    chunk = next(c for c in CHUNKS if c["chunk_id"] == cid)
    return PlanEntry(chunk_id=cid, file_id=chunk["file_id"], path=f"academic_notes/econ/{cid}.md",
                     citation=f"cite-{cid}", doc_type="textbook", offering="", score=0.8, rule=rule,
                     content_hash="h", status=status)


def _plan(wald=("cam-1", "han-1"), lm=("cam-3", "cam-1")):
    return Plan("demo", "spec.toml", "sha", "econ", NOW, [
        TopicPlan("Wald", [_e(c) for c in wald]), TopicPlan("LM", [_e(c) for c in lm])])


@pytest.fixture
def spec(make_spec):
    return make_spec(TOPICS)


def _run(spec, root, llm=None, **kw):
    llm = llm or FakeLLM()
    kw.setdefault("plan", _plan())
    plan = kw.pop("plan")
    return draft_guide(spec, plan, root=root, llm=llm, chunks=CHUNKS, now=NOW, plan_path="p/demo.plan.json",
                       plan_sha256="planhash", **kw), llm


def test_default_output_path(spec, root):
    out, _ = _run(spec, root)
    assert out == output_path(root, spec) and out.name == "demo.md"
    assert out.parent.as_posix().endswith("academic_notes/econ/summaries")


def test_one_call_per_topic_plus_comparison(spec, root):
    _, llm = _run(spec, root)
    assert len(llm.calls) == 3


def test_topic_prompt_uses_the_frozen_tutor_wording_and_excerpts(spec, root):
    _, llm = _run(spec, root)
    p = llm.calls[0]
    assert p.startswith("You are tutoring a student using ONLY the excerpts below")
    assert "Question: Wald. Explain Wald. Use only these excerpts." in p
    assert "[cite-cam-1]\nCameron: the Wald statistic." in p and "[cite-han-1]\nHansen: Wald tests." in p


def test_comparison_uses_first_take_passages_deduplicated_and_the_bare_instruction(spec, root):
    _, llm = _run(spec, root)
    p = llm.calls[2]
    assert "Question: Compare the two tests." in p
    assert p.count("[cite-cam-1]") == 1 and "[cite-cam-3]" in p and "cite-han-1" not in p


def test_document_layout_and_frontmatter(spec, root):
    out, _ = _run(spec, root)
    text = out.read_text(encoding="utf-8")
    front, body = text.split("\n---\n\n", 1)
    fields = {line.split(": ", 1)[0]: line.split(": ", 1)[1] for line in front.splitlines()[1:]}
    assert fields["llm_generated"] == "true" and fields["content_kind"] == "derived_summary"
    assert json.loads(fields["draft_model"]) == "fake-draft" and json.loads(fields["prompt_id"]) == "tutor_v1"
    assert json.loads(fields["spec"]) == {"id": "demo", "file": "spec.toml", "sha256": spec.sha256}
    assert json.loads(fields["plan"]) == {"file": "demo.plan.json", "sha256": "planhash"}
    refs = json.loads(fields["indexer_source_refs"])
    assert [r["chunk_id"] for r in refs] == ["cam-1", "han-1", "cam-3"]
    assert set(refs[0]) == {"path", "file_id", "chunk_id", "citation"}
    assert str(root) not in text
    assert body.startswith("# Demo guide\n\nEach section below was written")
    assert "## A static note\n\nNote body text." in body
    assert "## Wald\n\nANSWER 1\n\n**Retrieved sources**\n\n- [cite-cam-1] `academic_notes/econ/cam-1.md`" in body
    assert "## Compare\n\nANSWER 3" in body and body.count("---") >= 3


def test_draft_is_loadable_by_summary_enhance(spec, root, tmp_path):
    import json as _json
    chunk_file = tmp_path / "hub" / ".index" / "chunks" / "econ.json"
    chunk_file.parent.mkdir(parents=True)
    chunk_file.write_text(_json.dumps(CHUNKS), encoding="utf-8")
    out, _ = _run(spec, root)
    guide = load_guide(out)
    assert [s.chunk_id for s in guide.sources] == ["cam-1", "han-1", "cam-3"]


def test_tag_names_the_variant_and_is_validated(spec, root):
    out, _ = _run(spec, root, tag="b2-pro")
    assert out.name == "demo.b2-pro.md"
    with pytest.raises(DraftError, match="tag"):
        _run(spec, root, tag="bad tag!")


def test_existing_output_is_not_overwritten_without_force(spec, root):
    out, _ = _run(spec, root)
    out.write_text("precious", encoding="utf-8")
    with pytest.raises(DraftError, match="exists"):
        _run(spec, root)
    assert out.read_text(encoding="utf-8") == "precious"
    _run(spec, root, force=True)
    assert "llm_generated" in out.read_text(encoding="utf-8")


def test_pending_entries_block_unless_explicitly_accepted(spec, root):
    plan = _plan()
    plan.topics[0].entries[1].status = "pending"
    with pytest.raises(PendingReviewError):
        _run(spec, root, plan=plan)
    out, llm = _run(spec, root, plan=plan, accept_unreviewed=True)
    assert "[cite-han-1]" in llm.calls[0]


def test_dropped_entries_are_left_out(spec, root):
    plan = _plan()
    plan.topics[0].entries[1].status = "dropped"
    _, llm = _run(spec, root, plan=plan)
    assert "cite-han-1" not in llm.calls[0]


def test_missing_chunk_text_is_an_error_before_any_call(spec, root):
    llm = FakeLLM()
    with pytest.raises(DraftError, match="cam-1"):
        draft_guide(spec, _plan(), root=root, llm=llm, chunks=[c for c in CHUNKS if c["chunk_id"] != "cam-1"], now=NOW)
    assert llm.calls == []


def test_guide_v1_prompt_is_used_when_selected(make_spec, root):
    guide_spec = make_spec(TOPICS, header='[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n[draft]\nprompt = "guide_v1"\n\n')
    _, llm = _run(guide_spec, root)
    assert "Section: Wald" in llm.calls[0] and "tutoring" not in llm.calls[0]


def test_unusable_response_is_retried_once_then_fails(spec, root):
    out, llm = _run(spec, root, llm=FakeLLM([UnusableResponse("truncated")]))
    assert len(llm.calls) == 4 and out.is_file()
    with pytest.raises(DraftError, match="usable"):
        _run(spec, root, llm=FakeLLM([UnusableResponse("a"), UnusableResponse("b")]), force=True)


def test_other_llm_errors_propagate_and_nothing_is_written(spec, root):
    with pytest.raises(RuntimeError):
        _run(spec, root, llm=FakeLLM([RuntimeError("503")]))
    assert not output_path(root, spec).exists()
