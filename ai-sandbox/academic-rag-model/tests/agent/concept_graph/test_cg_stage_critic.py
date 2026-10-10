from agent.concept_graph.stages import critic
from agent.concept_graph.store import GraphStore
from agent.concept_graph.tasks import render_card
from cg_helpers import FakeRetriever, copy_sample, entry_for

PROV = {"driver": "agent", "agent": "test-agent", "run": "r1"}
EDGE = "rational-preference--implies--warp"


def prepared(tmp_path, **kw):
    store = GraphStore(copy_sample(tmp_path))
    tasks = critic.make_tasks(store, FakeRetriever(), **kw)
    return store, tasks


def test_one_task_per_proposed_edge_without_a_critic(tmp_path):
    store, tasks = prepared(tmp_path)
    assert len(tasks) == 17 and tasks[0].id.startswith("critic-")


def test_card_never_contains_the_edges_explanation_or_drafting_citations(tmp_path):
    store, tasks = prepared(tmp_path, nodes=["rational-preference"])
    task = next(t for t in tasks if t.subject["edge"] == EDGE)
    card = render_card(task)
    assert "Choosing the best element under a rational preference always satisfies" not in card  # the drafter's explanation
    assert "1.D" not in card  # the drafter's citation
    assert "choices are the most-preferred elements of each menu" in card  # the claim itself, with its condition
    assert "Rational preference relation" in card and "Weak axiom of revealed preference" in card


def test_skips_edges_that_already_have_a_critic_and_redo_includes_them(tmp_path):
    store, tasks = prepared(tmp_path)
    store.update_item("edge", EDGE, {"critic": {"verdict": "supports", "note": ""}})
    assert EDGE not in [t.subject["edge"] for t in critic.make_tasks(store, FakeRetriever())]
    assert EDGE in [t.subject["edge"] for t in critic.make_tasks(store, FakeRetriever(), redo=True)]


def test_verified_edges_are_never_criticised(tmp_path):
    store, tasks = prepared(tmp_path)
    store.update_item("edge", EDGE, {"status": "verified"})
    assert EDGE not in [t.subject["edge"] for t in critic.make_tasks(store, FakeRetriever(), redo=True)]


def test_section_filter_keeps_edges_touching_that_section(tmp_path):
    store, tasks = prepared(tmp_path, section="s02-choice")
    ids = {t.subject["edge"] for t in tasks}
    assert EDGE in ids and "preorder--is_a--binary-relation" not in ids


def test_verdict_must_be_one_of_three_and_unknown_keys_are_bounced(tmp_path):
    store, tasks = prepared(tmp_path)
    entry = entry_for(tasks[0])
    assert critic.validate_result(entry, {"verdict": "supports"}, store) == []
    assert any("verdict" in m for m in critic.validate_result(entry, {"verdict": "great"}, store))
    assert any("unknown" in m for m in critic.validate_result(entry, {"verdict": "supports", "score": 5}, store))


def test_weak_and_unsupported_need_a_note(tmp_path):
    store, tasks = prepared(tmp_path)
    entry = entry_for(tasks[0])
    for verdict in ("weak", "unsupported"):
        assert any("note" in m for m in critic.validate_result(entry, {"verdict": verdict}, store))
        assert critic.validate_result(entry, {"verdict": verdict, "note": "The passages never state the condition."}, store) == []


def test_copied_note_is_bounced(tmp_path):
    store, tasks = prepared(tmp_path)
    entry = entry_for(tasks[0])
    copied = {"verdict": "weak", "note": "It says a binary relation that is reflexive and transitive and nothing more."}
    assert any("note" in m for m in critic.validate_result(entry, copied, store))


def test_apply_sets_critic_and_leaves_status(tmp_path):
    store, tasks = prepared(tmp_path)
    entry = entry_for(next(t for t in tasks if t.subject["edge"] == EDGE))
    assert critic.apply_result(store, entry, {"verdict": "weak", "note": "Condition not stated."}, PROV) is None
    e = next(e for e in store.read_all().edges if e.id == EDGE)
    assert e.critic.verdict == "weak" and e.critic.note == "Condition not stated." and e.status == "proposed"


def test_apply_skips_an_edge_that_is_gone_or_verified(tmp_path):
    store, tasks = prepared(tmp_path)
    entry = entry_for(next(t for t in tasks if t.subject["edge"] == EDGE))
    store.update_item("edge", EDGE, {"status": "verified"})
    assert "verified" in critic.apply_result(store, entry, {"verdict": "supports"}, PROV)
    store.remove_item("edge", EDGE)
    assert "no longer exists" in critic.apply_result(store, entry, {"verdict": "supports"}, PROV)
