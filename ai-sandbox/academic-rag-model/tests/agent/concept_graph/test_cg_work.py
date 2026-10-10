import json

import pytest

from agent.concept_graph.sources import Passage
from agent.concept_graph.tasks import Task, render_card
from agent.concept_graph.work import create_run, load_run, render_worklist


def tasks():
    return [Task(id=f"fill-{n}", stage="fill", subject={"node": n}, instructions="rules", context=f"Node {n}",
                 passages=[Passage(id="P1", source="mwg", ref="ch. 1", text="secret passage text", path="p")])
            for n in ("a", "b")]


def test_work_dir_inside_the_graph_repo_is_refused(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo / "work", repo, "fill", tasks())
    with pytest.raises(ValueError, match="inside the graph repo"):
        create_run(repo, repo, "fill", tasks())


def test_create_run_writes_cards_and_a_manifest_with_offered_citations_and_passage_text(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="r1")
    assert run.run_id == "r1" and run.card_path("fill-a").is_file()
    manifest = json.loads((tmp_path / "work" / "r1" / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["tasks"][0]
    assert entry["id"] == "fill-a" and entry["status"] == "pending"
    assert entry["offered"] == [["mwg", "ch. 1"]]
    assert entry["passages"][0]["text"] == "secret passage text"
    assert "secret passage text" in run.card_path("fill-a").read_text(encoding="utf-8")


def test_default_run_ids_do_not_collide(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    a = create_run(tmp_path / "work", repo, "fill", tasks())
    b = create_run(tmp_path / "work", repo, "fill", tasks())
    assert a.run_id != b.run_id


def test_set_status_persists_and_leaves_no_temp_files(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="r1")
    run.set_status("fill-a", "applied")
    again = load_run(tmp_path / "work", "r1")
    assert again.task("fill-a")["status"] == "applied" and again.task("fill-b")["status"] == "pending"
    assert [p.name for p in (tmp_path / "work" / "r1").iterdir() if p.name.endswith(".tmp")] == []
    with pytest.raises(ValueError):
        run.set_status("fill-a", "not-a-status")
    with pytest.raises(KeyError):
        run.set_status("nope", "applied")


def test_bounce_appends_reasons_and_keeps_the_agents_work(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="r1")
    path = run.card_path("fill-a")
    path.write_text(path.read_text(encoding="utf-8").replace("```yaml\n```", "```yaml\ngist: My work\n```"), encoding="utf-8")
    run.bounce("fill-a", ["explanation: too close to a passage"])
    text = path.read_text(encoding="utf-8")
    assert "gist: My work" in text and "## Bounced" in text and "too close to a passage" in text
    assert run.task("fill-a")["status"] == "bounced" and run.task("fill-a")["reasons"] == ["explanation: too close to a passage"]


def test_a_second_bounce_replaces_the_first_section(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="r1")
    run.bounce("fill-a", ["first reason"])
    run.bounce("fill-a", ["second reason"])
    text = run.card_path("fill-a").read_text(encoding="utf-8")
    assert text.count("## Bounced") == 1 and "second reason" in text and "first reason" not in text
    assert run.task("fill-a")["attempts"] == 2


def test_worklist_lists_status_per_task(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="r1")
    run.set_status("fill-a", "applied")
    run.bounce("fill-b", ["bad"])
    text = render_worklist(run)
    assert "fill-a" in text and "applied" in text and "fill-b" in text and "bounced" in text


@pytest.mark.parametrize("bad", ["../graph/evil", "..", "a/b", "a\b", "/abs/path", "C:/abs/path", ".hidden", "", "x y"])
def test_a_crafted_run_id_cannot_escape_the_work_dir_or_reach_the_graph_repo(tmp_path, bad):
    repo = tmp_path / "graph"
    repo.mkdir()
    with pytest.raises(ValueError, match="run id"):
        create_run(tmp_path / "work", repo, "fill", tasks(), run_id=bad)
    assert list(repo.rglob("*")) == []
    with pytest.raises(ValueError, match="run id"):
        load_run(tmp_path / "work", bad)


def test_ordinary_run_ids_are_accepted(tmp_path):
    repo = tmp_path / "graph"
    repo.mkdir()
    run = create_run(tmp_path / "work", repo, "fill", tasks(), run_id="fill-2026-10-10_v2.1")
    assert run.root.parent == tmp_path / "work"
