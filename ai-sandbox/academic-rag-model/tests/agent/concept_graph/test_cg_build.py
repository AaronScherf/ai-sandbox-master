import json

import pytest

from agent.concept_graph.build import BuildError, build, graph_payload
from agent.concept_graph.schema import field_hash
from agent.concept_graph.store import GraphStore
from cg_helpers import copy_sample


@pytest.fixture
def vendor(tmp_path):
    d = tmp_path / "vendor"
    d.mkdir()
    (d / "cytoscape.min.js").write_text("/* cytoscape stub */", encoding="utf-8")
    (d / "katex.min.js").write_text("/* katex stub */", encoding="utf-8")
    return d


def test_payload_orders_sections_and_adds_field_hashes(tmp_path):
    g = GraphStore(copy_sample(tmp_path)).read_all()
    p = graph_payload(g)
    assert [s["id"] for s in p["sections"]] == ["s01-binary-relations", "s02-choice", "s03-demand"]
    node = next(n for n in p["nodes"] if n["id"] == "preorder")
    assert node["hashes"]["explanation"] == field_hash(node["explanation"])
    edge = next(e for e in p["edges"] if e["id"] == "preorder--is_a--binary-relation")
    assert edge["hashes"]["condition"] == field_hash("it is reflexive and transitive")
    assert len(p["graph_version"]) == 12


def test_version_changes_when_prose_changes(tmp_path):
    root = copy_sample(tmp_path)
    v1 = graph_payload(GraphStore(root).read_all())["graph_version"]
    GraphStore(root).update_item("node", "set", {"gist": "something else entirely"})
    v2 = graph_payload(GraphStore(root).read_all())["graph_version"]
    assert v1 != v2


def test_build_writes_graph_json_and_a_single_html_file(tmp_path, vendor):
    root = copy_sample(tmp_path)
    result = build(root, vendor_dir=vendor)
    data = json.loads(result.graph_json.read_text(encoding="utf-8"))
    html = result.index_html.read_text(encoding="utf-8")
    assert data["graph_version"] == result.graph_version
    assert result.graph_version in html
    assert "cytoscape stub" in html and "katex stub" in html
    assert "{{{" not in html
    assert "function edgeSentence" in html  # logic.js was inlined
    assert [w.code for w in result.warnings] == ["logical-cycle"]


def test_build_is_deterministic(tmp_path, vendor):
    root = copy_sample(tmp_path)
    first = build(root, vendor_dir=vendor).index_html.read_bytes()
    second = build(root, vendor_dir=vendor).index_html.read_bytes()
    assert first == second


def test_script_closer_in_prose_cannot_break_the_page(tmp_path, vendor):
    root = copy_sample(tmp_path)
    GraphStore(root).update_item("node", "set", {"explanation": "evil </script><script>alert(1)</script> and costs $5"})
    html = build(root, vendor_dir=vendor).index_html.read_text(encoding="utf-8")
    start = html.index('id="graph-data">') + len('id="graph-data">')
    end = html.index("</script>", start)
    payload = json.loads(html[start:end])  # still valid JSON up to the first real closer
    assert "alert(1)" in next(n for n in payload["nodes"] if n["id"] == "set")["explanation"]
    assert "</script><script>alert" not in html  # the closer was escaped to <\/script>


def test_build_refuses_a_graph_with_errors(tmp_path, vendor):
    root = copy_sample(tmp_path)
    GraphStore(root).update_item("edge", "binary-relation--defined_on--set", {"target": "nonexistent"})
    with pytest.raises(BuildError, match="dangling-endpoint"):
        build(root, vendor_dir=vendor)
    assert not (root / "index.html").exists()


def test_build_reports_missing_vendor_files(tmp_path):
    root = copy_sample(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(BuildError, match="vendor_fetch"):
        build(root, vendor_dir=empty)
