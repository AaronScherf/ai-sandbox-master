import pytest

from agent.concept_graph.store import GraphDataError, GraphStore
from cg_helpers import copy_sample


def test_read_all_loads_the_sample(tmp_path):
    g = GraphStore(copy_sample(tmp_path)).read_all()
    assert [s.id for s in g.sections] == ["s01-binary-relations", "s02-choice", "s03-demand"]
    assert len(g.nodes) == 17
    assert len(g.edges) == 17
    assert g.node_files["partial-order"] == "s01-binary-relations"
    assert g.rejected == []
    assert "order-theory" in g.vocab.topics
    assert g.site["title"] == "Microeconomics concept graph"


def test_unquoted_yaml_dates_become_strings(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s03-demand.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  introduced_in: 2026-09-10\n", encoding="utf-8")
    g = GraphStore(root).read_all()
    node = next(n for n in g.nodes if n.id == "walrasian-demand")
    assert node.introduced_in == "2026-09-10"


def test_update_item_changes_one_item_and_keeps_comments(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s01-binary-relations.yaml"
    path.write_text("# keep me\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    store = GraphStore(root)
    store.update_item("node", "preorder", {"status": "verified", "reviewed_by": "Ada", "gist": "line one\nline two"})
    assert "# keep me" in path.read_text(encoding="utf-8")
    g = store.read_all()
    preorder = next(n for n in g.nodes if n.id == "preorder")
    assert preorder.status == "verified" and preorder.reviewed_by == "Ada"
    assert preorder.gist.strip() == "line one\nline two"
    assert next(n for n in g.nodes if n.id == "partial-order").status == "proposed"


def test_update_unknown_item_raises(tmp_path):
    with pytest.raises(KeyError):
        GraphStore(copy_sample(tmp_path)).update_item("edge", "nope", {"status": "verified"})


def test_remove_item_and_tombstone(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.remove_item("edge", "preorder--has_property--reflexivity")
    store.add_rejected("edge", "preorder--has_property--reflexivity")
    g = store.read_all()
    assert len(g.edges) == 16
    assert [(r.kind, r.id) for r in g.rejected] == [("edge", "preorder--has_property--reflexivity")]
    with pytest.raises(KeyError):
        store.remove_item("edge", "preorder--has_property--reflexivity")


def test_missing_vocab_raises(tmp_path):
    root = copy_sample(tmp_path)
    (root / "config" / "vocab.yaml").unlink()
    with pytest.raises(GraphDataError, match="vocab"):
        GraphStore(root).read_all()


def test_bad_item_error_names_the_file(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "data" / "nodes" / "s03-demand.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "  colour: red\n", encoding="utf-8")
    with pytest.raises(GraphDataError, match="s03-demand.yaml"):
        GraphStore(root).read_all()
