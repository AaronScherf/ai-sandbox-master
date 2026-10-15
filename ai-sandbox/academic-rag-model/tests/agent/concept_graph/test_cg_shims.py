"""Old import paths keep resolving, to the very same objects as core's."""
import core.agent_tasks.loop as core_loop
import core.agent_tasks.tasks as core_tasks
import core.agent_tasks.work as core_work
from agent.concept_graph import drivers, sources, tasks, work
from agent.concept_graph.stages import common


def test_task_card_names_are_core_objects():
    for name in ("Task", "Passage", "ResultError", "render_card", "extract_result",
                 "parse_result_text", "result_from_response"):
        assert getattr(tasks, name) is getattr(core_tasks, name), name
    assert sources.Passage is core_tasks.Passage


def test_run_names_are_core_objects_and_create_run_is_a_wrapper():
    for name in ("Run", "STATUSES", "task_entry", "render_worklist", "load_run"):
        assert getattr(work, name) is getattr(core_work, name), name
    assert work.create_run is not core_work.create_run


def test_driver_names_are_core_objects():
    for name in ("SubmitReport", "BudgetError", "estimate_cost", "PRICE_IN", "PRICE_OUT", "OUT_TOKENS",
                 "FREE_LIMIT", "API_SUFFIX"):
        assert getattr(drivers, name) is getattr(core_loop, name), name
    assert common.provenance is core_loop.provenance
    for name in ("collect", "submit", "api_run", "gemini_complete"):
        assert callable(getattr(drivers, name))
