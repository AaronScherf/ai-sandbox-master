"""Course-specific folder names can be selected without widening the default scan."""
from core.agent_tasks.work import load_run
from core.indexer.index_card import compute_content_hash, save_shard

from agent.problem_corpus import stage
from agent.problem_corpus.cli import main


PREFIX = "academic_notes/econometrics/"
REVIEW = PREFIX + "problem_sets/processed_outputs/review.md"
PSET = PREFIX + "class_2024/Problem Sets with Solutions/processed_outputs/GR6411_pset1.md"
SOLUTIONS = PREFIX + "class_2024/Problem Sets with Solutions/processed_outputs/Solutions-pset1.md"
RECITATION = PREFIX + "class_2024/Recitations/processed_outputs/Recitation 3.md"
RESOURCE = "academic_resources/econometrics/textbooks/processed_outputs/book.md"
NEAR_PREFIX = "academic_notes/econometrics-extra/problem_sets/processed_outputs/other.md"
NUMBERED = "1. First problem.\n\n2. Second problem.\n\n3. Third problem.\n"
Q_NUMBERED = "Q1. First problem.\n\nQ2. Second problem.\n\nQ3. Third problem.\n"


def indexed_corpus(tmp_path, *, recitation_body=Q_NUMBERED):
    root = tmp_path / "hub"
    cards = []
    for i, (path, body) in enumerate([
        (REVIEW, NUMBERED), (PSET, Q_NUMBERED), (SOLUTIONS, Q_NUMBERED),
        (RECITATION, recitation_body), (RESOURCE, NUMBERED), (NEAR_PREFIX, NUMBERED),
    ]):
        source = root / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(body, encoding="utf-8")
        cards.append({"file_id": f"file-{i}", "path": path, "course": "econometrics",
                      "content_hash": compute_content_hash(str(source)),
                      "orphaned": False, "needs_indexing": False})
    save_shard(str(root), "econometrics", cards)
    return root


def paths(tasks):
    return {task.subject["path"] for task in tasks}


def test_default_collection_keeps_existing_categories(tmp_path):
    root = indexed_corpus(tmp_path)
    tasks, _ = stage.make_tasks(stage.Target(str(root)), course="econometrics")
    assert paths(tasks) == {REVIEW, RESOURCE, NEAR_PREFIX}


def test_extra_categories_and_prefix_are_opt_in_and_solution_files_are_skipped(tmp_path):
    root = indexed_corpus(tmp_path)
    tasks, skipped = stage.make_tasks(
        stage.Target(str(root)), course="econometrics", path_prefix=PREFIX,
        include_categories=["Problem Sets with Solutions", "Recitations"],
        exclude_paths=[RECITATION],
    )
    assert paths(tasks) == {REVIEW, PSET}
    assert "solution" in skipped[SOLUTIONS]
    assert skipped[RECITATION] == "excluded by --exclude-path"
    pset = next(task for task in tasks if task.subject["path"] == PSET)
    assert [p.ref for p in pset.passages] == ["Problem 1", "Problem 2", "Problem 3"]


def test_collect_and_status_use_the_same_selection(tmp_path, capsys):
    root = indexed_corpus(tmp_path)
    argv = ["--root", str(root)]
    scope = ["--course", "econometrics", "--path-prefix", PREFIX.rstrip("/"),
             "--include-category", "Problem Sets with Solutions",
             "--include-category", "Recitations", "--exclude-path", RECITATION]
    assert main(argv + ["collect", *scope, "--run-id", "econometrics-r1"]) == 0
    run = load_run(root / ".agent_work", "econometrics-r1")
    assert {task["subject"]["path"] for task in run.tasks} == {REVIEW, PSET}
    assert not (root / ".problem_corpus").exists()
    capsys.readouterr()
    assert main(argv + ["status", *scope]) == 0
    assert "eligible index cards: 2; stored problems: 0" in capsys.readouterr().out


def test_prefix_requires_a_directory_boundary():
    assert not stage.source_selected(NEAR_PREFIX, path_prefix=PREFIX.rstrip("/"))
    assert stage.source_selected(PSET, path_prefix=PREFIX.rstrip("/"),
                                 include_categories=["Problem Sets with Solutions"])


def test_numbered_recitation_notes_are_not_collected_as_problems(tmp_path):
    root = indexed_corpus(tmp_path, recitation_body=NUMBERED)
    tasks, skipped = stage.make_tasks(stage.Target(str(root)), course="econometrics",
                                      path_prefix=PREFIX, include_categories=["Recitations"])
    assert RECITATION not in paths(tasks)
    assert skipped[RECITATION] == "no problem spans detected"
