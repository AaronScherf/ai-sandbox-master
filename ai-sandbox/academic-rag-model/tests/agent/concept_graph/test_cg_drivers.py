import hashlib

import pytest

from agent.concept_graph import drivers
from agent.concept_graph.store import GraphStore
from agent.concept_graph.work import load_run
from cg_helpers import FakeRetriever, blank_explanations, copy_sample

GOOD = ("gist: A relation that ranks things without forbidding ties.\n"
        "explanation: Two properties define it, so every element relates to itself and comparisons chain together.\n"
        "citations:\n  - {source: rubinstein, ref: 'ch. 2, p. 12'}\n")
COPIED = ("gist: Short.\n"
          "explanation: Note that a binary relation that is reflexive and transitive and nothing more is a preorder.\n"
          "citations:\n  - {source: rubinstein, ref: 'ch. 2, p. 12'}\n")


def fill_card(run, task_id, yaml_text):
    path = run.card_path(task_id)
    path.write_text(path.read_text(encoding="utf-8").replace("```yaml\n```", "```yaml\n" + yaml_text + "```"), encoding="utf-8")


def setup(tmp_path, blanks=("preorder", "total-order", "warp")):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, list(blanks))
    run = drivers.collect("fill", store, FakeRetriever(), tmp_path / "work")
    return store, run


def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.name.encode() + p.read_bytes())
    return h.hexdigest()


def node(store, node_id):
    return next(n for n in store.read_all().nodes if n.id == node_id)


def test_collect_writes_cards_and_manifest_and_never_touches_the_graph_repo(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    blank_explanations(store, ["preorder", "warp"])
    before = tree_hash(store.root)
    run = drivers.collect("fill", store, FakeRetriever(), tmp_path / "work")
    assert tree_hash(store.root) == before
    assert {t["id"] for t in run.tasks} == {"fill-preorder", "fill-warp"}
    assert all(run.card_path(t["id"]).is_file() for t in run.tasks)
    assert (tmp_path / "work" / run.run_id / "worklist.md").is_file()


def test_collect_with_nothing_to_do_returns_none(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    assert drivers.collect("fill", store, FakeRetriever(), tmp_path / "work") is None


def test_submit_applies_valid_cards_and_bounces_bad_ones_independently(tmp_path):
    store, run = setup(tmp_path)
    fill_card(run, "fill-preorder", GOOD)
    fill_card(run, "fill-total-order", COPIED)
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == ["fill-preorder"] and list(report.bounced) == ["fill-total-order"]
    assert report.untouched == ["fill-warp"]
    assert node(store, "preorder").explanation.startswith("Two properties")
    assert node(store, "total-order").explanation == ""
    assert any("explanation" in r for r in report.bounced["fill-total-order"])
    again = load_run(tmp_path / "work", run.run_id)
    assert {t["id"]: t["status"] for t in again.tasks} == {"fill-preorder": "applied", "fill-total-order": "bounced", "fill-warp": "pending"}


def test_submit_skips_cards_the_agent_has_not_filled(tmp_path):
    store, run = setup(tmp_path)
    before = tree_hash(store.root)
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == [] and report.bounced == {} and len(report.untouched) == 3
    assert tree_hash(store.root) == before


def test_submit_twice_does_not_duplicate_or_rewrite(tmp_path):
    store, run = setup(tmp_path)
    fill_card(run, "fill-preorder", GOOD)
    drivers.submit(run, store, "test-agent")
    first = tree_hash(store.root)
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == [] and tree_hash(store.root) == first


def test_card_edited_after_apply_is_not_applied_again(tmp_path):
    store, run = setup(tmp_path)
    fill_card(run, "fill-preorder", GOOD)
    drivers.submit(run, store, "test-agent")
    path = run.card_path("fill-preorder")
    path.write_text(path.read_text(encoding="utf-8").replace("ranks things", "ranks stuff"), encoding="utf-8")
    assert drivers.submit(run, store, "test-agent").applied == []
    assert "ranks things" in node(store, "preorder").gist


def test_bounced_card_can_be_fixed_and_resubmitted(tmp_path):
    store, run = setup(tmp_path)
    fill_card(run, "fill-total-order", COPIED)
    drivers.submit(run, store, "test-agent")
    path = run.card_path("fill-total-order")
    text = path.read_text(encoding="utf-8")
    assert "## Bounced" in text
    path.write_text(text.replace("Note that a binary relation that is reflexive and transitive and nothing more is a preorder.",
                                 "Comparisons chain and each element relates to itself."), encoding="utf-8")
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == ["fill-total-order"]
    assert node(store, "total-order").explanation.startswith("Comparisons chain")


def test_malformed_yaml_is_bounced_and_the_other_cards_still_run(tmp_path):
    store, run = setup(tmp_path)
    fill_card(run, "fill-preorder", "gist: [unclosed\n")
    fill_card(run, "fill-warp", GOOD)
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == ["fill-warp"] and "fill-preorder" in report.bounced


def test_a_card_that_blows_up_is_reported_and_does_not_stop_the_run(tmp_path, monkeypatch):
    store, run = setup(tmp_path)
    fill_card(run, "fill-preorder", GOOD)
    fill_card(run, "fill-warp", GOOD)
    from agent.concept_graph.stages import fill
    real = fill.validate_result

    def flaky(entry, result, store_):
        if entry["id"] == "fill-preorder":
            raise RuntimeError("boom")
        return real(entry, result, store_)

    monkeypatch.setattr(fill, "validate_result", flaky)
    report = drivers.submit(run, store, "test-agent")
    assert report.applied == ["fill-warp"] and any("boom" in r for r in report.bounced["fill-preorder"])


def test_estimate_scales_with_task_text():
    small = drivers.estimate_cost(["x" * 400])
    big = drivers.estimate_cost(["x" * 400] * 10)
    assert 0 < small < big


def make_complete(responses=None, fail_for=()):
    calls = []

    def complete(prompt):
        calls.append(prompt)
        for key in fail_for:
            if key in prompt:
                raise RuntimeError("api down")
        return (responses or {}).get("default", "```yaml\n" + GOOD + "```")

    complete.calls = calls
    return complete


def test_api_run_refuses_over_budget_before_any_call(tmp_path):
    store, run = setup(tmp_path)
    complete = make_complete()
    with pytest.raises(drivers.BudgetError, match="estimate"):
        drivers.api_run("fill", run, store, complete, approve_cost=0.0000001)
    assert complete.calls == []


def test_api_run_requires_approval_above_one_dollar(tmp_path):
    store, run = setup(tmp_path)
    complete = make_complete()
    with pytest.raises(drivers.BudgetError, match="--approve-cost"):
        drivers.api_run("fill", run, store, complete, approve_cost=None, price_out=100000.0)
    assert complete.calls == []


def test_api_run_applies_through_the_same_validation_and_labels_the_driver(tmp_path):
    store, run = setup(tmp_path, blanks=("preorder", "warp"))
    complete = make_complete()
    report = drivers.api_run("fill", run, store, complete, approve_cost=1.0, agent_name="gemini-test")
    assert sorted(report.applied) == ["fill-preorder", "fill-warp"]
    assert node(store, "preorder").provenance.driver == "api" and node(store, "preorder").provenance.agent == "gemini-test"


def test_api_results_that_copy_a_passage_are_bounced_not_applied(tmp_path):
    store, run = setup(tmp_path, blanks=("preorder",))
    complete = make_complete({"default": COPIED})  # bare yaml, no fence
    report = drivers.api_run("fill", run, store, complete, approve_cost=1.0)
    assert report.applied == [] and "fill-preorder" in report.bounced
    assert node(store, "preorder").explanation == ""


def test_api_run_survives_one_failing_task(tmp_path):
    store, run = setup(tmp_path, blanks=("preorder", "warp"))
    complete = make_complete(fail_for=("fill-preorder",))
    report = drivers.api_run("fill", run, store, complete, approve_cost=1.0)
    assert report.applied == ["fill-warp"] and any("api down" in r for r in report.bounced["fill-preorder"])
