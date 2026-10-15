"""Pins the on-disk contract of concept_graph's task cards and run manifests.

Written before the code moved to core/agent_tasks; it must keep passing, unedited, afterwards."""
import json

from agent.concept_graph.sources import Passage
from agent.concept_graph.tasks import Task, render_card
from agent.concept_graph.work import create_run, load_run


def _task():
    return Task(
        id="fill-001", stage="fill", subject={"concept": "Elasticity"},
        instructions="Draft the entry.\n", context="Concept: Elasticity\n",
        passages=[Passage(id="P1", source="notes", ref="Lecture 3", text="Elasticity measures...\n", path="a/b.md")],
    )


def test_card_text_is_byte_stable():
    expected = "\n".join([
        "# Task fill-001   (stage: fill)",
        "",
        "## Instructions",
        "Draft the entry.",
        "",
        "## Subject",
        "Concept: Elasticity",
        "",
        "## Offered passages",
        "### P1  [source: notes | ref: Lecture 3]",
        "Elasticity measures...",
        "",
        "## Result",
        "Write only the YAML mapping, inside the fence below.",
        "```yaml",
        "```",
        "",
    ])
    assert render_card(_task()) == expected


def test_manifest_keys_and_worklist_are_stable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", [_task()], run_id="r1")
    data = json.loads((run.root / "manifest.json").read_text(encoding="utf-8"))
    assert list(data) == ["run_id", "stage", "created", "graph_repo", "tasks"]
    assert data["graph_repo"] == str(repo)
    entry = data["tasks"][0]
    assert list(entry) == ["id", "subject", "status", "attempts", "reasons", "offered", "passages"]
    assert list(entry["passages"][0]) == ["id", "source", "ref", "text", "path"]
    assert (run.root / "worklist.md").read_text(encoding="utf-8").startswith("# Worklist: run r1 (stage: fill)\n")
    assert (run.root / "cards" / "fill-001.md").read_text(encoding="utf-8") == render_card(_task())


def test_bounce_text_and_counters_are_stable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", [_task()], run_id="r1")
    run.bounce("fill-001", ["reason one"])
    card = run.card_path("fill-001").read_text(encoding="utf-8")
    assert card.endswith(
        "\n## Bounced\nFix only what is listed, in the same ```yaml block above, then ask for a re-submit.\n- reason one\n"
    )
    reloaded = load_run(tmp_path / "work", "r1")
    assert reloaded.task("fill-001")["status"] == "bounced"
    assert reloaded.task("fill-001")["attempts"] == 1


def test_privacy_guard_message_names_the_graph_repo(tmp_path):
    import pytest
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo / "work", repo, "fill", [_task()])
