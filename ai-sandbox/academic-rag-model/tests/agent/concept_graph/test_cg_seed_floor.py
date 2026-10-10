"""Seed stage: every section must end up with a minimum number of nodes, and required concepts are a floor."""
from agent.concept_graph.schema import SeedConfig
from agent.concept_graph.stages import seed
from test_cg_seed_outline import GOOD, PROV, empty_store, rich_hub, task_for, write_seed_config  # noqa: F401


def node(i, section="s01-preferences"):
    return {"id": f"concept-{i}", "name": f"Concept {i}", "kind": "object", "section": section, "topic": "preferences"}


def test_the_floor_defaults_to_one_so_empty_sections_are_still_refused():
    assert SeedConfig().min_nodes_per_section == 1


def test_an_empty_section_is_bounced_with_the_section_named(tmp_path):
    store, task, entry = task_for(tmp_path)
    result = {"topics": ["preferences"], "sections": GOOD["sections"] + [
        {"id": "s02-empty", "title": "Nothing here", "order": 2, "state": "planned"}], "nodes": GOOD["nodes"]}
    msgs = seed.validate_result(entry, result, store)
    assert len(msgs) == 1 and "s02-empty" in msgs[0] and "at least 1" in msgs[0]


def test_the_configured_floor_applies_to_every_section(tmp_path):
    store = empty_store(tmp_path)
    write_seed_config(store, "min_nodes_per_section: 3\n")
    task = seed.make_tasks(store, None, hub_root=str(rich_hub(tmp_path)), course="microecon")[0]
    entry = {"subject": task.subject, "passages": []}
    assert task.subject["min_nodes_per_section"] == 3
    msgs = seed.validate_result(entry, GOOD, store)  # GOOD has two nodes in its one section
    assert len(msgs) == 1 and "s01-preferences" in msgs[0] and "only 2" in msgs[0] and "at least 3" in msgs[0]
    ok = dict(GOOD, nodes=GOOD["nodes"] + [node(1)])
    assert seed.validate_result(entry, ok, store) == []


def test_existing_nodes_count_toward_the_floor_in_additive_mode(tmp_path):
    store = empty_store(tmp_path)
    seed.apply_result(store, {}, GOOD, PROV)  # two nodes in s01-preferences
    entry = {"subject": {"must_include": [], "min_nodes_per_section": 3}, "passages": []}
    assert seed.validate_result(entry, {"nodes": [node(1)]}, store) == []  # 2 existing + 1 new = 3


def test_an_existing_section_that_is_still_below_the_floor_must_be_filled_by_the_additive_pass(tmp_path):
    store = empty_store(tmp_path)
    thin = dict(GOOD, nodes=GOOD["nodes"][:1])
    seed.apply_result(store, {}, thin, PROV)  # one node in s01-preferences
    entry = {"subject": {"must_include": [], "min_nodes_per_section": 3}, "passages": []}
    elsewhere = {"sections": [{"id": "s02-more", "title": "More", "order": 2, "state": "planned"}],
                 "nodes": [node(i, "s02-more") for i in range(3)]}
    msgs = seed.validate_result(entry, elsewhere, store)
    assert len(msgs) == 1 and "s01-preferences" in msgs[0] and "only 1" in msgs[0]


def test_the_card_says_the_required_list_is_a_floor_and_states_the_minimum(tmp_path):
    store = empty_store(tmp_path)
    write_seed_config(store, "min_nodes_per_section: 6\nmust_include: [Preorder]\n")
    task = seed.make_tasks(store, None, hub_root=str(rich_hub(tmp_path)), course="microecon")[0]
    assert "at least 6 nodes" in task.context
    assert "minimum" in task.instructions.lower() and "many more" in task.instructions.lower()
