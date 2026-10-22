import json

import pytest

from agent.concept_graph.cli import main
from agent.concept_graph.store import GraphStore
from cg_helpers import copy_sample


def run(root, *args):
    return main(["--graph-repo", str(root), *args])


def test_retype_changes_identity_and_clears_critic(tmp_path, capsys):
    root = copy_sample(tmp_path)
    store = GraphStore(root)
    old = "preorder--has_property--reflexivity"
    store.update_item("edge", old, {"critic": {"verdict": "weak", "note": "wrong type"}})

    assert run(root, "retype", old, "--type", "applies_to", "--target", "transitivity",
               "--agent-name", "Ada", "--run-id", "repair-1") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["old_id"] == old
    assert result["id"] == "preorder--applies_to--transitivity"
    graph = store.read_all()
    assert old not in {e.id for e in graph.edges}
    edge = next(e for e in graph.edges if e.id == result["id"])
    assert edge.type == "applies_to" and edge.target == "transitivity"
    assert edge.critic is None
    assert edge.provenance.model_dump() == {"driver": "agent", "agent": "Ada", "model": None, "run": "repair-1"}


def test_retype_can_change_condition_without_changing_id(tmp_path, capsys):
    root = copy_sample(tmp_path)
    eid = "rational-preference--implies--warp"
    assert run(root, "retype", eid, "--condition", "only under the new assumption", "--run-id", "repair-2") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["id"] == eid
    edge = next(e for e in GraphStore(root).read_all().edges if e.id == eid)
    assert edge.condition == "only under the new assumption" and edge.provenance.run == "repair-2"


@pytest.mark.parametrize("options, expected", [
    (("--type", "invalid"), "unknown connection type"),
    (("--type", "implies"), "condition"),
    (("--type", "is_a", "--target", "preorder"), "itself"),
    (("--type", "is_a", "--target", "partial-order"), "cycle"),
    (("--type", "is_a", "--target", "nowhere"), "not a concept"),
])
def test_retype_refuses_invalid_changes_without_writing(tmp_path, capsys, options, expected):
    root = copy_sample(tmp_path)
    old = "preorder--has_property--reflexivity"
    before = (root / "data" / "edges" / "s01-binary-relations.yaml").read_bytes()
    assert run(root, "retype", old, *options) == 1
    captured = capsys.readouterr()
    assert expected in captured.err
    assert expected in json.loads(captured.out)["error"]
    assert (root / "data" / "edges" / "s01-binary-relations.yaml").read_bytes() == before


def test_retype_refuses_duplicate_and_rejected_ids(tmp_path, capsys):
    root = copy_sample(tmp_path)
    old = "preorder--has_property--reflexivity"
    assert run(root, "retype", old, "--type", "has_property", "--target", "transitivity") == 1
    assert "already exists" in capsys.readouterr().err
    GraphStore(root).add_rejected("edge", "preorder--applies_to--reflexivity")
    assert run(root, "retype", old, "--type", "applies_to") == 1
    assert "rejected earlier" in capsys.readouterr().err
    assert any(e.id == old for e in GraphStore(root).read_all().edges)


def test_reject_edge_tombstones_and_warns_about_new_orphan(tmp_path, capsys):
    root = copy_sample(tmp_path)
    eid = "sen-beta--component_of--sen-alpha-beta"
    assert run(root, "reject-edge", eid) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"action": "reject-edge", "id": eid, "orphans": ["sen-beta"]}
    assert "sen-beta" in captured.err and "orphan" in captured.err
    graph = GraphStore(root).read_all()
    assert eid not in {e.id for e in graph.edges}
    assert ("edge", eid) in {(r.kind, r.id) for r in graph.rejected}
    assert run(root, "reject-edge", eid) == 1
    assert "not found" in capsys.readouterr().err
