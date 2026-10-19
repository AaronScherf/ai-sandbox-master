"""Subscription extraction against a small indexed corpus; no network calls."""
import re
from unittest.mock import patch

from core.indexer.index_card import compute_content_hash, save_shard
from core.agent_tasks.work import load_run
from agent.problem_corpus import stage
from agent.problem_corpus.cli import main
from agent.problem_corpus.store import load_records, save_file_records


PATH = "academic_notes/math-camp/problem_sets/processed_outputs/set.md"
BODY = "1. Find the eigenvalues of A.\n\n2. Prove the set is compact.\nProof by covers.\n\n3. Show convergence.\n"
RESULT = """problems:
  - problem_text: Find the eigenvalues of A.
    solution_text: null
    topic_tag: eigenvalues
  - problem_text: Prove the set is compact.
    solution_text: Proof by covers.
    topic_tag: compactness
  - problem_text: Show convergence.
    solution_text: null
    topic_tag: convergence
"""


def corpus(tmp_path):
    root = tmp_path / "hub"
    source = root / PATH
    source.parent.mkdir(parents=True)
    source.write_text(BODY, encoding="utf-8")
    card = {"file_id": "aaa", "path": PATH, "course": "math-camp",
            "content_hash": compute_content_hash(str(source)), "orphaned": False, "needs_indexing": False}
    save_shard(str(root), "math-camp", [card])
    return root, source


def fill(run, body=RESULT):
    path = run.card_path(run.tasks[0]["id"])
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"```yaml\n.*?```", f"```yaml\n{body}```", text, count=1, flags=re.DOTALL),
                    encoding="utf-8")


def test_collect_creates_cards_without_api_calls(tmp_path):
    root, _ = corpus(tmp_path)
    with patch("agent.problem_corpus.cli._gemini_complete") as api:
        assert main(["--root", str(root), "collect", "--course", "math-camp", "--run-id", "r1"]) == 0
    api.assert_not_called()
    run = load_run(root / ".agent_work", "r1")
    assert run.stage == "problem_corpus"
    assert len(run.tasks) == 1
    assert len(run.tasks[0]["passages"]) == 3
    assert "Find the eigenvalues" in run.card_path(run.tasks[0]["id"]).read_text(encoding="utf-8")
    assert not (root / ".problem_corpus").exists()


def test_validate_result_checks_count_source_and_staleness(tmp_path):
    root, source = corpus(tmp_path)
    task = stage.make_tasks(stage.Target(str(root)))[0][0]
    from core.agent_tasks.work import task_entry
    entry = task_entry(task)
    result = {"problems": [
        {"problem_text": "Find the eigenvalues of A.", "solution_text": None, "topic_tag": "eigenvalues"},
        {"problem_text": "Prove the set is compact.", "solution_text": "Proof by covers.", "topic_tag": "compactness"},
        {"problem_text": "Show convergence.", "solution_text": None, "topic_tag": "convergence"},
    ]}
    assert stage.validate_result(entry, result, stage.Target(str(root))) == []
    bad = {"problems": [dict(item) for item in result["problems"]]}
    bad["problems"][1]["solution_text"] = "Invented proof"
    assert any("solution_text" in error for error in stage.validate_result(entry, bad, stage.Target(str(root))))
    assert stage.validate_result(entry, {"problems": []}, stage.Target(str(root)))
    source.write_text(BODY + "4. New problem.\n", encoding="utf-8")
    assert any("changed" in error for error in stage.validate_result(entry, result, stage.Target(str(root))))


def test_apply_result_replaces_only_the_source_file_and_derives_provenance(tmp_path):
    root, _ = corpus(tmp_path)
    from core.agent_tasks.tasks import parse_result_text
    from core.agent_tasks.work import task_entry
    entry = task_entry(stage.make_tasks(stage.Target(str(root)))[0][0])
    other = {"id": "other", "source": {"file_id": "bbb"}, "content_hash": "h"}
    save_file_records(str(root), "math-camp", "bbb", [other])
    result = parse_result_text(RESULT)
    assert stage.apply_result(stage.Target(str(root)), entry, result,
                              {"driver": "agent", "agent": "test", "run": "r1"}) is None
    records = load_records(str(root), "math-camp")
    assert len(records) == 4
    assert next(r for r in records if r["id"] == "other") == other
    extracted = [r for r in records if r["source"]["file_id"] == "aaa"]
    assert extracted[1]["solution_provenance"] == "student_attempt"
    assert extracted[0]["solution_provenance"] is None
    assert extracted[0]["source"]["citation"] == "set.md, Problem 1"
    assert all(r["content_hash"] == entry["subject"]["content_hash"] for r in extracted)
    assert stage.make_tasks(stage.Target(str(root)))[0] == []


def test_submit_bounces_then_applies_and_does_not_reapply(tmp_path):
    root, _ = corpus(tmp_path)
    args = ["--root", str(root)]
    assert main(args + ["collect", "--run-id", "r1"]) == 0
    run = load_run(root / ".agent_work", "r1")
    fill(run, RESULT.replace("Proof by covers.", "Invented proof"))
    assert main(args + ["submit", "r1"]) == 0
    assert load_run(root / ".agent_work", "r1").tasks[0]["status"] == "bounced"
    assert load_records(str(root), "math-camp") == []
    fill(run, RESULT)
    assert main(args + ["submit", "r1", "--agent-name", "test-agent"]) == 0
    assert load_run(root / ".agent_work", "r1").tasks[0]["status"] == "applied"
    saved = (root / ".problem_corpus" / "math-camp.json").read_text(encoding="utf-8")
    assert main(args + ["submit", "r1"]) == 0
    assert (root / ".problem_corpus" / "math-camp.json").read_text(encoding="utf-8") == saved


def test_api_is_explicit_and_uses_same_validation(tmp_path):
    root, _ = corpus(tmp_path)
    args = ["--root", str(root)]
    assert main(args + ["collect", "--run-id", "r1"]) == 0
    prompts = []
    assert main(args + ["api", "r1", "--approve-cost", "1"],
                complete=lambda prompt: prompts.append(prompt) or RESULT) == 0
    assert len(prompts) == 1
    assert len(load_records(str(root), "math-camp")) == 3
