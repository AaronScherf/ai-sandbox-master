import json

import pytest

from agent.concept_graph.reviews import ReviewFile, apply_proposals, apply_review
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample


SECTION = TOPIC = "x"   # replaced by the `store` fixture with real values from the sample graph


def review(who, *decisions, version=2):
    return ReviewFile.model_validate({"schema_version": version, "graph_version": "v", "reviewer": {"name": who},
                                      "created": "t", "decisions": list(decisions)})


def add_node(name, **kw):
    p = {"name": name, "kind": "property", "section": SECTION, "topic": TOPIC, "note": "", "connections": []}
    p.update(kw)
    return {"action": "add_node", "proposal": p}


def add_edge(source, type_, target, **kw):
    p = {"source": source, "type": type_, "target": target}
    p.update(kw)
    return {"action": "add_edge", "proposal": p}


@pytest.fixture
def store(tmp_path):
    global SECTION, TOPIC
    s = GraphStore(copy_sample(tmp_path))
    g = s.read_all()
    SECTION, TOPIC = g.sections[0].id, g.vocab.topics[0]
    assert "property" in g.vocab.kinds
    return s


def test_version_1_files_still_load_and_apply(store):
    r = review("Ada", version=1)
    assert apply_review(store, r, "2026-10-20").applied == []
    assert apply_proposals(store, [r], "2026-10-20").applied == []


def test_proposals_are_rejected_in_a_version_1_file():
    with pytest.raises(ValueError):
        review("Ada", add_node("X Y"), version=1)


def test_a_new_concept_with_a_connection_is_written_as_proposed(store):
    g = store.read_all()
    other = g.nodes[0].id
    r = review("Ada", add_node("Quasi concavity", note="Upper sets are convex.",
                               connections=[{"other": other, "type": "is_a", "direction": "out"}]))
    report = apply_proposals(store, [r], "2026-10-20")
    after = store.read_all()
    n = next(x for x in after.nodes if x.id == "quasi-concavity")
    assert n.status == "proposed" and n.explanation == "" and n.gist == "Upper sets are convex."
    assert n.provenance.driver == "reviewer" and n.provenance.agent == "Ada"
    assert any(e.id == f"quasi-concavity--is_a--{other}" and e.status == "proposed" for e in after.edges)
    assert errors(validate(after)) == []
    assert any("quasi-concavity" in line for line in report.applied)


def test_two_reviewers_proposing_the_same_concept_become_one_merged_node(store):
    a = review("Ana", add_node("Quasi concavity", note="Upper sets are convex."))
    b = review("Ben", add_node("Quasi-concavity", note="Ranks bundles."))
    report = apply_proposals(store, [a, b], "2026-10-20")
    nodes = [n for n in store.read_all().nodes if "quasi" in n.id]
    assert len(nodes) == 1
    assert nodes[0].provenance.agent == "Ana; Ben"
    assert "Ana:" in nodes[0].gist and "Ben:" in nodes[0].gist
    assert any("merged 2 proposals" in line for line in report.applied)


def test_a_proposal_similar_to_an_existing_concept_becomes_edge_proposals_and_a_comment(store):
    g = store.read_all()
    existing, partner = g.nodes[0], g.nodes[1]
    r = review("Ada", add_node(existing.name.upper(), note="A thought.",
                               connections=[{"other": partner.id, "type": "is_a", "direction": "in"}]))
    report = apply_proposals(store, [r], "2026-10-20")
    after = store.read_all()
    assert len(after.nodes) == len(g.nodes)                       # nothing new
    comments = (store.root / "review-comments.md").read_text(encoding="utf-8")
    assert existing.id in comments and "A thought." in comments
    conflicts = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "treated as proposals about" in conflicts
    assert report.conflicts


def test_an_invalid_proposal_goes_to_conflicts_with_the_reason(store):
    r = review("Ada", add_node("Odd one", kind="widget"), add_edge("nope", "is_a", "also-nope"))
    report = apply_proposals(store, [r], "2026-10-20")
    text = (store.root / "review-conflicts.md").read_text(encoding="utf-8")
    assert "kind" in text and "not a concept" in text and len(report.conflicts) == 2
    assert not any(n.id == "odd-one" for n in store.read_all().nodes)


def test_a_connection_to_a_bounced_new_concept_bounces_too(store):
    g = store.read_all()
    r = review("Ada", add_node("Odd one", kind="widget"), add_edge("odd-one", "is_a", g.nodes[0].id))
    report = apply_proposals(store, [r], "2026-10-20")
    assert len(report.conflicts) == 2


def test_the_same_edge_from_two_reviewers_is_one_edge_with_both_conditions(store):
    g = store.read_all()
    have = {e.id for e in g.edges}
    ids = [n.id for n in g.nodes]
    a, b = next((a, b) for a in ids for b in ids if a != b
                and f"{a}--implies--{b}" not in have and f"{a}--iff--{b}" not in have and f"{b}--iff--{a}" not in have)
    x = review("Ana", add_edge(a, "implies", b, condition="single valued"))
    y = review("Ben", add_edge(a, "implies", b, condition="continuous"))
    apply_proposals(store, [x, y], "2026-10-20")
    e = next(e for e in store.read_all().edges if e.id == f"{a}--implies--{b}")
    assert "single valued" in e.condition and "continuous" in e.condition
    assert e.provenance.agent == "Ana; Ben"


def test_a_viewer_style_review_round_trips_through_the_cli_and_build(store, tmp_path, capsys):
    from agent.concept_graph.cli import main
    g = store.read_all()
    other = g.nodes[0].id
    payload = {"schema_version": 2, "graph_version": "v", "reviewer": {"name": "Ada"}, "created": "t",
               "decisions": [add_node("Quasi concavity", note="Upper sets are convex.",
                                      connections=[{"other": other, "type": "is_a", "direction": "out"}])]}
    f = tmp_path / "review.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["--graph-repo", str(store.root), "apply-review", str(f), "--today", "2026-10-20"]) == 0
    out = capsys.readouterr().out
    assert "proposals: " in out and "quasi-concavity" in out
    assert main(["--graph-repo", str(store.root), "validate"]) == 0
    assert main(["--graph-repo", str(store.root), "build"]) == 0
    built = json.loads((store.root / "build" / "graph.json").read_text(encoding="utf-8"))
    assert any(n["id"] == "quasi-concavity" and n["status"] == "proposed" for n in built["nodes"])
