# tests/agent/study_guide/test_study_guide_draft.py
import json

import pytest

from agent.study_guide.draft import DraftError, draft_guide, output_path
from agent.study_guide.plan import PendingReviewError, Plan, PlanEntry, TopicPlan
from agent.summary_enhance.llm import UnusableResponse
from agent.summary_enhance.source_loader import load_guide
from sg_helpers import CHUNKS, FakeLLM, make_spec, root  # noqa: F401 (fixtures)

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


def test_frontmatter_records_whether_unreviewed_passages_were_accepted(spec, root):
    plan = _plan()
    plan.topics[0].entries[1].status = "pending"
    out, _ = _run(spec, root, plan=plan, accept_unreviewed=True)
    assert "accept_unreviewed: true\n" in out.read_text(encoding="utf-8")
    out2, _ = _run(spec, root, force=True)
    assert "accept_unreviewed: false\n" in out2.read_text(encoding="utf-8")


def test_a_failure_midway_saves_the_finished_sections(spec, root):
    with pytest.raises(RuntimeError):
        _run(spec, root, llm=FakeLLM(["ANSWER ONE", RuntimeError("503")]))
    recovered = output_path(root, spec).with_name("demo.recovered.md")
    text = recovered.read_text(encoding="utf-8")
    assert "ANSWER ONE" in text and "## Wald" in text and "## LM" not in text
    assert not output_path(root, spec).exists()


STRIP_HEADER = ('[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n'
                '[draft]\nprompt = "guide_v1"\nmin_words = 1800\ncitations = "strip"\n\n')


def test_strip_mode_removes_inline_citations_and_source_lists_and_records_them_in_frontmatter(make_spec, root):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    plan = _plan()
    plan.topics[0].entries[0].citation = "Recitation 6 (corrected), p. 2"
    llm = FakeLLM(["Wald uses the covariance (Recitation 6 (corrected), p. 2; cite-han-1) and more [cite-han-1].",
                   "LM text (cite-cam-3).", "Compared (cite-cam-3)."])
    out, _ = _run(spec, root, llm=llm, plan=plan)
    text = out.read_text(encoding="utf-8")
    assert "Wald uses the covariance and more." in text and "LM text." in text
    assert "cite-han-1)" not in text.split("---\n", 2)[2] and "Retrieved sources" not in text
    assert "the passages retrieved for each section are listed beneath it" not in text
    front = text.split("---\n")[1]
    sources = json.loads(next(l for l in front.splitlines() if l.startswith("topic_sources: "))[len("topic_sources: "):])
    assert sources["Wald"] == ["Recitation 6 (corrected), p. 2", "cite-han-1"]
    assert sources["LM"] == ["cite-cam-3", "cite-cam-1"]
    assert sources["Compare"] == ["Recitation 6 (corrected), p. 2", "cite-cam-3"]


def test_strip_mode_warns_about_citations_it_could_not_match(make_spec, root, capsys):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    llm = FakeLLM(["Claim (Recitation 9 (draft), p. 4).", "ok", "ok"])
    out, _ = _run(spec, root, llm=llm)
    assert "(Recitation 9 (draft), p. 4)" in out.read_text(encoding="utf-8")
    assert "1 citation(s) could not be matched" in capsys.readouterr().out


def test_inline_mode_keeps_citations_and_source_lists(spec, root):
    out, _ = _run(spec, root, llm=FakeLLM(["Claim (cite-cam-1).", "b", "c"]))
    text = out.read_text(encoding="utf-8")
    assert "Claim (cite-cam-1)." in text and "Retrieved sources" in text and "topic_sources" not in text


CONSTRUCT_TOPICS = TOPICS.replace('instruction = "Explain Wald."', 'instruction = "Explain Wald."\nconstruct_examples = true')


def test_construct_examples_applies_only_to_flagged_topics_and_is_recorded(make_spec, root):
    header = STRIP_HEADER.replace('citations = "strip"', 'citations = "inline"')
    spec = make_spec(CONSTRUCT_TOPICS, header=header)
    out, llm = _run(spec, root)
    assert "Constructed example (not from the sources)" in llm.calls[0]
    assert "Constructed example (not from the sources)" not in llm.calls[1]
    assert "at least 1800 words" in llm.calls[0]
    assert 'constructed_examples: ["Wald"]\n' in out.read_text(encoding="utf-8")


def test_strip_mode_also_removes_shortened_page_citations(make_spec, root, capsys):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    llm = FakeLLM(["Claim (§9.12, p. 270; Hansen, p. 268) and (Recitation 5, pp. 10-11) kept (for example, n = 100).",
                   "ok", "ok"])
    out, _ = _run(spec, root, llm=llm)
    text = out.read_text(encoding="utf-8")
    assert "Claim and kept (for example, n = 100)." in text
    assert "could not be matched" not in capsys.readouterr().out


def test_usage_is_recorded_and_printed_when_the_client_tracks_it(spec, root, capsys):
    llm = FakeLLM()
    llm.usage = {"calls": 3, "prompt_tokens": 9000, "output_tokens": 2500, "thinking_tokens": 100}
    out, _ = _run(spec, root, llm=llm)
    front = out.read_text(encoding="utf-8").split("---\n")[1]
    assert 'usage: {"calls":3,"prompt_tokens":9000,"output_tokens":2500,"thinking_tokens":100}\n' in front
    assert "3 calls, 9000 prompt tokens, 2500 output tokens, 100 thinking tokens" in capsys.readouterr().out


def test_strip_handles_bracketed_labels_inside_parentheses_and_leaves_no_empty_parens(make_spec, root):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    llm = FakeLLM(["A ([cite-cam-1]; [cite-han-1]) B ( ) C (;) D [cite-cam-1] E ([cite-cam-1];;) F.", "ok", "ok"])
    out, _ = _run(spec, root, llm=llm)
    assert "A B C D E F." in out.read_text(encoding="utf-8")


def test_headings_inside_a_section_are_demoted_and_a_repeated_title_dropped(make_spec, root):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    llm = FakeLLM(["# Wald\n\nintro\n\n## Sub topic\n\n### Deeper\n\n#### Deepest\n\ntext", "ok", "ok"])
    out, _ = _run(spec, root, llm=llm)
    text = out.read_text(encoding="utf-8")
    wald = text.split("## Wald\n", 1)[1].split("\n---\n", 1)[0]
    assert "\n# " not in "\n" + wald and "\n## " not in wald
    assert "### Sub topic" in wald and "### Deeper" in wald and "#### Deepest" in wald
    assert "# Wald" not in wald


def test_strip_mode_saves_the_cited_text_beside_the_plan(make_spec, root):
    spec = make_spec(TOPICS, header=STRIP_HEADER)
    out, _ = _run(spec, root, llm=FakeLLM(["Cited claim (cite-cam-1).", "b", "c"]), tag="t1")
    side = out.parent.parent / "guide_plans" / "demo.t1.cited.json"
    assert json.loads(side.read_text(encoding="utf-8"))["Wald"] == "Cited claim (cite-cam-1)."


def test_inline_mode_writes_no_cited_sidecar(spec, root):
    out, _ = _run(spec, root)
    assert not (out.parent.parent / "guide_plans").exists()


def test_a_draft_stops_once_spend_passes_the_cap_and_keeps_the_finished_sections(spec, root):
    from agent.study_guide.revise.cost import CostCapReached
    llm = FakeLLM()
    llm.model = "gemini-3.8-flash"
    llm.usage = {"calls": 1, "prompt_tokens": 1_000_000, "output_tokens": 0, "thinking_tokens": 0}  # $0.75
    with pytest.raises(CostCapReached, match="Wald"):
        _run(spec, root, llm=llm, max_cost=0.5)
    assert len(llm.calls) == 1
    assert "ANSWER 1" in output_path(root, spec).with_name("demo.recovered.md").read_text(encoding="utf-8")
