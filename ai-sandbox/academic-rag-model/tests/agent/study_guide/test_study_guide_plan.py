# tests/agent/study_guide/test_study_guide_plan.py
import json

import pytest

from agent.study_guide import plan as plan_mod
from agent.study_guide.plan import (
    PlanError, build_plan, check_fresh, guide_chunk_ids, heading_numbers, load_plan, plan_sha256, save_plan,
)
from sg_helpers import CARDS, CHUNKS, WALD_TOPIC, StubSearch, cite, hit, make_spec, root  # noqa: F401 (fixtures)

NOW = "2026-10-05T00:00:00+00:00"


def _topic(sources, title="Wald", instruction="Explain Wald."):
    return f'\n[[topic]]\ntitle = "{title}"\ninstruction = "{instruction}"\n' + sources


def _section(labels, book="Cameron", exclude="[]", mx=12, query="wald"):
    return (f'\n  [[topic.source]]\n  kind = "section"\n  book = "{book}"\n  labels = {json.dumps(labels)}\n'
            f'  exclude_labels = {exclude}\n  query = "{query}"\n  max = {mx}\n')


def _build(spec, root, search, **kw):
    return build_plan(spec, root, search=search, chunks=CHUNKS, cards=CARDS, now=NOW, **kw)


def _ids(plan, i=0):
    return [e.chunk_id for e in plan.topics[i].entries]


def test_heading_numbers_extracts_leading_section_numbers():
    path = ["Chapter 7", "**7.2.** Wald Test", "§7.2.3. Wald Test Statistic", "9.10 WALD TESTS", "Likelihood Ratio Test"]
    assert heading_numbers(path) == ["7.2", "7.2.3", "9.10"]


def test_section_rule_filters_by_book_and_label(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"])))
    search = StubSearch({"textbook": [hit("cam-1", .8), hit("han-1", .7), hit("cam-3", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-1"]


def test_unnumbered_child_heading_matches_its_numbered_parent(make_spec, root):
    spec = make_spec(_topic(_section(["7.3.1"])))
    search = StubSearch({"textbook": [hit("cam-2", .8), hit("cam-3", .7)]})
    assert _ids(_build(spec, root, search)) == ["cam-2"]


def test_label_prefix_stops_at_the_dot_boundary(make_spec, root):
    spec = make_spec(_topic(_section(["7.3"])))
    search = StubSearch({"textbook": [hit("cam-2", .8), hit("cam-3", .7), hit("cam-4", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-2", "cam-3"]          # not 7.30


def test_hansen_label_9_1_does_not_match_9_10_but_legacy_substring_does(make_spec, root):
    search = StubSearch({"textbook": [hit("han-1", .8), hit("han-2", .7)]})
    new = make_spec(_topic(_section(["9.1"], book="Hansen")))
    assert _ids(_build(new, root, search)) == ["han-2"]
    legacy = make_spec(_topic(_section(["9.1"], book="Hansen")), header=HEADER_LEGACY)
    assert _ids(_build(legacy, root, search)) == ["han-1", "han-2"]


HEADER_LEGACY = '[guide]\nid = "demo"\ntitle = "Demo guide"\ncourse = "econ"\n\n[draft]\nlabel_match = "citation-substring"\n\n'


def test_legacy_substring_misses_unnumbered_child_headings(make_spec, root):
    spec = make_spec(_topic(_section(["7.3.1"])), header=HEADER_LEGACY)
    search = StubSearch({"textbook": [hit("cam-2", .8)]})
    with pytest.raises(PlanError, match="Wald"):
        _build(spec, root, search)


def test_exclude_labels_and_max_follow_search_order(make_spec, root):
    spec = make_spec(_topic(_section(["7"], exclude='["7.3.5"]', mx=2)))
    search = StubSearch({"textbook": [hit("cam-3", .9), hit("cam-1", .8), hit("cam-2", .7), hit("cam-4", .6)]})
    assert _ids(_build(spec, root, search)) == ["cam-1", "cam-2"]


def test_section_search_text_and_parameters(make_spec, root):
    spec = make_spec(WALD_TOPIC)
    search = StubSearch({"textbook": [hit("cam-1", .8)]})
    _build(spec, root, search)
    assert search.calls == [{"query": "Econ textbook: wald. Explain Wald.", "doc_type": "textbook",
                             "top_k": 180, "file_top_k": 80}]


def _file_rule(file, query="", mx=12):
    q = f'  query = "{query}"\n' if query else ""
    return f'\n  [[topic.source]]\n  kind = "file"\n  file = "{file}"\n{q}  max = {mx}\n'


def test_file_rule_ranks_by_search_then_fills_in_document_order(make_spec, root):
    spec = make_spec(_topic(_file_rule("Slides/processed_outputs/slidesASYM.md", query="wald", mx=2)))
    search = StubSearch({"ta_notes": [hit("sl-2", .9), hit("rec-1", .8)]})
    plan = _build(spec, root, search)
    assert _ids(plan) == ["sl-2", "sl-1"]
    assert plan.topics[0].entries[0].score == .9 and plan.topics[0].entries[1].score == 0.0
    assert search.calls[0]["doc_type"] == "ta_notes" and search.calls[0]["file_top_k"] == 200


def test_file_rule_without_query_uses_document_order_and_file_id(make_spec, root):
    search = StubSearch({})
    assert _ids(_build(make_spec(_topic(_file_rule("sl"))), root, search)) == ["sl-1", "sl-2"]
    assert _ids(_build(make_spec(_topic(_file_rule("sl", mx=1))), root, search)) == ["sl-1"]
    assert search.calls == []


@pytest.mark.parametrize("ref,fragment", [("Nope/missing.md", "not found"), ("Recitations/processed_outputs/Empty.md", "chunk")])
def test_file_rule_errors(make_spec, root, ref, fragment):
    with pytest.raises(PlanError, match=fragment):
        _build(make_spec(_topic(_file_rule(ref))), root, StubSearch({}))


def _discover(extra="", query="wald", doc_types='["textbook"]', mx=8, min_score=0.72):
    return (f'\n  [[topic.source]]\n  kind = "discover"\n  query = "{query}"\n  doc_types = {doc_types}\n'
            f'  max = {mx}\n  min_score = {min_score}\n{extra}')


def test_discover_applies_threshold_pinned_exclusion_and_pending_status(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]) + _discover()))
    search = StubSearch({"textbook": [hit("cam-1", .80), hit("han-1", .76), hit("cam-3", .74), hit("han-2", .70)]})
    plan = _build(spec, root, search)
    assert _ids(plan) == ["cam-1", "han-1", "cam-3"]
    assert [e.status for e in plan.topics[0].entries] == ["accepted", "pending", "pending"]
    assert [e.rule for e in plan.topics[0].entries] == ["section", "discover", "discover"]


def test_discover_excludes_a_guides_chunks(make_spec, root, tmp_path):
    guide = tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "old.md"
    guide.write_text('---\ntitle: "Old"\nindexer_source_refs: [{"chunk_id":"han-1","file_id":"han","path":"p","citation":"c"}]\n---\n\nBody\n',
                     encoding="utf-8")
    spec = make_spec(_topic(_discover(extra='  exclude_guide = "academic_notes/econ/summaries/old.md"\n')))
    search = StubSearch({"textbook": [hit("han-1", .9), hit("cam-1", .8)]})
    assert _ids(_build(spec, root, search)) == ["cam-1"]


def test_guide_chunk_ids_reads_source_map_too(root, tmp_path):
    guide = tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "new.md"
    guide.write_text('---\nsource_map: [{"chunk_id":"a-1"},{"chunk_id":"a-2"}]\n---\n\nBody\n', encoding="utf-8")
    assert guide_chunk_ids(root, "academic_notes/econ/summaries/new.md") == {"a-1", "a-2"}


@pytest.mark.parametrize("content,fragment", [
    (None, "not readable"),
    ("no frontmatter here\n", "frontmatter"),
    ('---\ntitle: "x"\n---\n\nBody\n', "no source chunks"),
])
def test_exclude_guide_errors_are_loud(make_spec, root, tmp_path, content, fragment):
    if content is not None:
        (tmp_path / "hub" / "academic_notes" / "econ" / "summaries" / "old.md").write_text(content, encoding="utf-8")
    spec = make_spec(_topic(_discover(extra='  exclude_guide = "academic_notes/econ/summaries/old.md"\n')))
    with pytest.raises(PlanError, match=fragment):
        _build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))


def test_discover_max_per_file_and_multiple_doc_types(make_spec, root):
    spec = make_spec(_topic(_discover(doc_types='["textbook", "ta_notes"]', extra="  max_per_file = 1\n")))
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("cam-2", .85), hit("han-1", .8)],
                         "ta_notes": [hit("sl-1", .95), hit("sl-2", .9)]})
    assert _ids(_build(spec, root, search)) == ["sl-1", "cam-1", "han-1"]


def test_rule_order_is_section_then_file_then_discover(make_spec, root):
    spec = make_spec(_topic(_discover() + _file_rule("sl", mx=1) + _section(["7.2"])))
    search = StubSearch({"textbook": [hit("cam-1", .9), hit("han-1", .8)]})
    assert _ids(_build(spec, root, search)) == ["cam-1", "sl-1", "han-1"]


def test_duplicate_chunks_within_a_topic_are_kept_once(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]) + _section(["7.2"], query="wald again")))
    assert _ids(_build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))) == ["cam-1"]


def test_entry_metadata(make_spec, root, monkeypatch):
    monkeypatch.setattr(plan_mod, "_offering", lambda card, hub: "class_2024" if card["file_id"] == "sl" else "")
    spec = make_spec(_topic(_section(["7.2"]) + _file_rule("sl", mx=1)))
    plan = _build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))
    cam, sl = plan.topics[0].entries
    assert (cam.doc_type, cam.content_hash, cam.offering, cam.file_id) == ("textbook", "h-cam", "", "cam")
    assert cam.path.endswith("Cameron_Micro_2013.rag.md") and cam.citation == cite(CHUNKS[0])
    assert (sl.doc_type, sl.offering, sl.citation) == ("ta_notes", "class_2024", "sl-1")
    assert (plan.spec_id, plan.course, plan.generated_at, plan.spec_sha256) == ("demo", "econ", NOW, spec.sha256)


def test_chunks_without_a_heading_path_fall_back_to_the_citation(make_spec, root):
    from types import SimpleNamespace
    chunks = CHUNKS + [{"chunk_id": "cam-5", "file_id": "cam", "text": "no heading path"}]
    result = SimpleNamespace(chunk_id="cam-5", file_id="cam", path=CARDS[0]["rag_md_path"], score=.9,
                             citation="§7.2.9 Lack of Invariance, p. 256", text="t")
    spec = make_spec(_topic(_section(["7.2"])))
    plan = build_plan(spec, root, search=StubSearch({"textbook": [result]}), chunks=chunks, cards=CARDS, now=NOW)
    assert _ids(plan) == ["cam-5"]


def test_topic_with_no_passages_fails_and_names_the_topic(make_spec, root):
    spec = make_spec(_topic(_section(["7.2"]), title="Empty Topic"))
    with pytest.raises(PlanError, match="Empty Topic"):
        _build(spec, root, StubSearch({"textbook": []}))


def test_save_load_roundtrip_and_sha(make_spec, root, tmp_path):
    plan = _build(make_spec(WALD_TOPIC), root, StubSearch({"textbook": [hit("cam-1", .8)]}))
    path = tmp_path / "out" / "demo.plan.json"
    save_plan(plan, path)
    assert load_plan(path) == plan
    assert len(plan_sha256(path)) == 64


def test_load_rejects_other_formats(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"format": 99}), encoding="utf-8")
    with pytest.raises(PlanError, match="format"):
        load_plan(path)


def test_check_fresh_detects_missing_chunks_and_changed_files(make_spec, root):
    plan = _build(make_spec(WALD_TOPIC), root, StubSearch({"textbook": [hit("cam-1", .8)]}))
    assert check_fresh(plan, chunks=CHUNKS, cards=CARDS) == []
    gone = check_fresh(plan, chunks=[c for c in CHUNKS if c["chunk_id"] != "cam-1"], cards=CARDS)
    assert len(gone) == 1 and "cam-1" in gone[0]
    changed = [dict(c, content_hash="NEW") if c["file_id"] == "cam" else c for c in CARDS]
    assert "changed" in check_fresh(plan, chunks=CHUNKS, cards=changed)[0]


def test_a_section_rule_that_matches_nothing_fails_even_if_other_rules_hit(make_spec, root):
    spec = make_spec(_topic(_section(["7.2a"]) + _file_rule("sl", mx=1)))
    with pytest.raises(PlanError, match=r"section rule.*7\.2a"):
        _build(spec, root, StubSearch({"textbook": [hit("cam-1", .9)]}))
