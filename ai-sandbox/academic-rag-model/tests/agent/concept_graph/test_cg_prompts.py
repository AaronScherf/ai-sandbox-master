"""collect prints, and saves, the prompt that goes with a run of cards."""
from agent.concept_graph import stages
from agent.concept_graph.cli import main
from agent.concept_graph.prompts import STAGE_NOUN, STEPS
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, blank_explanations, copy_sample


def cli(root, *args):
    return main(["--graph-repo", str(root), *args], retriever_factory=lambda a: FakeRetriever())


def test_every_stage_has_steps_and_a_name():
    assert set(stages.STAGES) <= set(STEPS) and set(stages.STAGES) <= set(STAGE_NOUN)


def test_seed_steps_hold_for_a_first_seed_and_any_course():
    # The same steps are printed for a first seed of an empty graph and for `--redo`, in any course.
    assert "additive" not in STEPS["seed"] and "axioms" not in STEPS["seed"]


def test_collect_fill_prints_and_saves_a_prompt_that_names_the_run_and_stage(tmp_path, capsys):
    root = copy_sample(tmp_path)
    blank_explanations(GraphStore(root), ["preorder"])
    work = tmp_path / "work"
    assert cli(root, "collect", "fill", "--work-dir", str(work), "--run-id", "r1") == 0
    out = capsys.readouterr().out
    saved = (work / "r1" / "PROMPT.md").read_text(encoding="utf-8")
    assert saved.strip() in out
    assert "FILL run r1 (1 card)" in saved and str(work / "r1") in saved
    assert "Do not run submit yourself" in saved and "never mention the passages" in saved.lower()
    first = (work / "r1" / "cards" / "fill-preorder.md").read_text(encoding="utf-8").split("## Instructions")[1].strip().splitlines()[0]
    assert first[:60] in saved and "wrong run" in saved  # the agent can check it was given the right run


def test_collect_link_prompt_says_link_and_asks_for_cross_section_edges(tmp_path, capsys):
    root = copy_sample(tmp_path)
    work = tmp_path / "work"
    assert cli(root, "collect", "link", "--node", "preorder", "--redo", "--work-dir", str(work), "--run-id", "l1") == 0
    saved = (work / "l1" / "PROMPT.md").read_text(encoding="utf-8")
    assert "LINK run l1" in saved and "other sections" in saved and "FILL" not in saved


def test_summary_prompt_does_not_ask_for_citations_but_fill_prompt_does(tmp_path):
    root = copy_sample(tmp_path)
    blank_explanations(GraphStore(root), ["preorder"])
    work = tmp_path / "work"
    assert cli(root, "collect", "summary", "--work-dir", str(work), "--run-id", "s1") == 0
    assert cli(root, "collect", "fill", "--work-dir", str(work), "--run-id", "f1") == 0
    assert "citation" not in (work / "s1" / "PROMPT.md").read_text(encoding="utf-8").lower()
    assert "citation" in (work / "f1" / "PROMPT.md").read_text(encoding="utf-8").lower()
