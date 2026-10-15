import json

import pytest

from agent.concept_graph.build import BuildError, build
from cg_helpers import copy_sample


def write_layout(root, name, body):
    d = root / "config" / "layouts"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(body), encoding="utf-8")


def node_ids(root):
    g = json.loads((root / "build" / "graph.json").read_text(encoding="utf-8")) if (root / "build" / "graph.json").exists() else None
    return g


def test_layouts_are_embedded_sorted_by_id(tmp_path):
    root = copy_sample(tmp_path)
    result = build(root)
    first = json.loads(result.graph_json.read_text(encoding="utf-8"))["nodes"][0]["id"]
    write_layout(root, "b-second", {"name": "Second", "positions": {first: {"x": 1, "y": 2}}})
    write_layout(root, "a-first", {"name": "First", "positions": {first: {"x": 3, "y": 4}}})
    data = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    assert [l["id"] for l in data["layouts"]] == ["a-first", "b-second"]
    assert data["layouts"][0]["positions"][first] == {"x": 3, "y": 4}


def test_an_unknown_concept_id_fails_the_build_with_the_file_name(tmp_path):
    root = copy_sample(tmp_path)
    write_layout(root, "bad", {"name": "Bad", "positions": {"no-such-concept": {"x": 0, "y": 0}}})
    with pytest.raises(BuildError) as exc:
        build(root)
    assert "bad.json" in str(exc.value) and "no-such-concept" in str(exc.value)


def test_a_malformed_layout_fails_clearly(tmp_path):
    root = copy_sample(tmp_path)
    write_layout(root, "oops", {"name": "Oops", "positions": {"x": "not a point"}})
    with pytest.raises(BuildError):
        build(root)


def test_no_layouts_folder_means_an_empty_list(tmp_path):
    root = copy_sample(tmp_path)
    data = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    assert data["layouts"] == []

def test_section_topic_short_and_summary_reach_the_page_data(tmp_path):
    from agent.concept_graph.store import GraphStore
    root = copy_sample(tmp_path)
    sid = GraphStore(root).read_all().sections[0].id
    GraphStore(root).update_section(sid, {"short": "Short", "summary": "A summary."})
    data = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    sec = next(s for s in data["sections"] if s["id"] == sid)
    assert sec["short"] == "Short" and sec["summary"] == "A summary."



def test_a_non_finite_position_fails_the_build(tmp_path):
    root = copy_sample(tmp_path)
    first = json.loads(build(root).graph_json.read_text(encoding="utf-8"))["nodes"][0]["id"]
    d = root / "config" / "layouts"
    d.mkdir(parents=True, exist_ok=True)
    (d / "nan.json").write_text('{"name": "Nan", "positions": {"%s": {"x": NaN, "y": 1}}}' % first, encoding="utf-8")
    with pytest.raises(BuildError) as exc:
        build(root)
    assert "nan.json" in str(exc.value)


def test_adding_a_layout_does_not_change_the_graph_version(tmp_path):
    root = copy_sample(tmp_path)
    first = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    node_id = first["nodes"][0]["id"]
    write_layout(root, "extra", {"name": "Extra", "positions": {node_id: {"x": 1, "y": 2}}})
    second = json.loads(build(root).graph_json.read_text(encoding="utf-8"))
    assert second["layouts"] and first["graph_version"] == second["graph_version"]
