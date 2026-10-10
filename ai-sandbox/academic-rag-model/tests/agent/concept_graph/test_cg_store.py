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


def test_site_config_with_an_unknown_key_is_rejected_and_names_the_file(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "config" / "site.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "contact_email: someone@example.test\n", encoding="utf-8")
    with pytest.raises(GraphDataError, match="site.yaml"):
        GraphStore(root).read_all()


def test_site_repo_must_look_like_owner_slash_name(tmp_path):
    root = copy_sample(tmp_path)
    (root / "config" / "site.yaml").write_text("title: T\nrepo: https://github.com/a/b\n", encoding="utf-8")
    with pytest.raises(GraphDataError, match="site.yaml"):
        GraphStore(root).read_all()


NEW_NODE = {"id": "budget-set", "name": "Budget set", "kind": "object", "section": "s03-demand", "topic": "demand",
            "gist": "What the consumer can afford.", "explanation": "Line one\nline two", "status": "proposed",
            "provenance": {"driver": "agent", "agent": "test", "run": "r1"}}


def test_add_sections_appends_in_order_and_refuses_an_existing_id(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.add_sections([{"id": "s04-production", "title": "Production", "order": 4, "state": "planned", "lectures": []}])
    assert [s.id for s in store.read_all().sections][-1] == "s04-production"
    with pytest.raises(ValueError, match="s01-binary-relations"):
        store.add_sections([{"id": "s01-binary-relations", "title": "x", "order": 9, "state": "planned"}])


def test_add_nodes_creates_the_section_file_and_round_trips(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.add_sections([{"id": "s04-production", "title": "Production", "order": 4, "state": "planned", "lectures": []}])
    node = dict(NEW_NODE, id="cost-function", name="Cost function", section="s04-production")
    store.add_nodes("s04-production", [node])
    assert (store.root / "data" / "nodes" / "s04-production.yaml").is_file()
    g = store.read_all()
    got = next(n for n in g.nodes if n.id == "cost-function")
    assert got.explanation.strip() == "Line one\nline two" and got.provenance.run == "r1"
    assert g.node_files["cost-function"] == "s04-production"


def test_add_nodes_refuses_an_existing_id_and_a_section_mismatch(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    with pytest.raises(ValueError, match="set"):
        store.add_nodes("s01-binary-relations", [dict(NEW_NODE, id="set", section="s01-binary-relations")])
    with pytest.raises(ValueError, match="section"):
        store.add_nodes("s03-demand", [dict(NEW_NODE, section="s01-binary-relations")])


def test_add_nodes_drops_none_values(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    store.add_nodes("s03-demand", [dict(NEW_NODE, formal=None, example=None)])
    text = (store.root / "data" / "nodes" / "s03-demand.yaml").read_text(encoding="utf-8")
    assert "formal" not in text and "example" not in text


def test_add_edges_goes_to_the_higher_order_sections_file(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    edge = {"id": "walrasian-demand--defined_on--set", "source": "walrasian-demand", "type": "defined_on",
            "target": "set", "explanation": "Demand lives on a set of bundles.", "status": "proposed"}
    store.add_edges([edge])
    assert (store.root / "data" / "edges" / "s03-demand.yaml").is_file()
    assert any(e.id == edge["id"] for e in store.read_all().edges)


def test_add_edges_refuses_a_duplicate_id_and_an_unknown_endpoint(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    with pytest.raises(ValueError, match="preorder--is_a--binary-relation"):
        store.add_edges([{"id": "preorder--is_a--binary-relation", "source": "preorder", "type": "is_a",
                          "target": "binary-relation", "status": "proposed"}])
    with pytest.raises(ValueError, match="ghost"):
        store.add_edges([{"id": "ghost--is_a--set", "source": "ghost", "type": "is_a", "target": "set", "status": "proposed"}])


def test_add_vocab_appends_only_new_entries_and_keeps_comments(tmp_path):
    root = copy_sample(tmp_path)
    path = root / "config" / "vocab.yaml"
    path.write_text("# vocab comment\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    store = GraphStore(root)
    store.add_vocab(kinds=["object", "newkind"], topics=["production"])
    g = store.read_all()
    assert g.vocab.kinds.count("object") == 1 and g.vocab.kinds[-1] == "newkind"
    assert g.vocab.topics[-1] == "production"
    assert "# vocab comment" in path.read_text(encoding="utf-8")


def test_added_items_validate_cleanly(tmp_path):
    from agent.concept_graph.validate import errors, validate
    store = GraphStore(copy_sample(tmp_path))
    store.add_nodes("s03-demand", [NEW_NODE])
    store.add_edges([{"id": "walrasian-demand--defined_on--budget-set", "source": "walrasian-demand",
                      "type": "defined_on", "target": "budget-set", "status": "proposed"}])
    assert errors(validate(store.read_all())) == []
