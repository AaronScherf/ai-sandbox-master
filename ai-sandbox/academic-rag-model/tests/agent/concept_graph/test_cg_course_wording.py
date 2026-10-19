"""Course wording lives in the graph repo's config, not in code."""
import yaml

from agent.concept_graph.schema import Site, Vocab
from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.stages import fill, seed
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, copy_sample


def test_site_subject_defaults_and_vocab_accepts_kind_descriptions():
    assert Site().subject == "this course"
    v = Vocab.model_validate({"kinds": ["theorem", {"name": "estimator", "help": "a rule mapping data to an estimate"}],
                              "topics": []})
    assert v.kinds == ["theorem", "estimator"] and v.kind_help == {"estimator": "a rule mapping data to an estimate"}
    assert "kind_help" not in v.model_dump()


def test_add_vocab_does_not_duplicate_a_described_kind(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    path = store.root / "config" / "vocab.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["kinds"].append({"name": "estimator", "help": "h"})
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    store.add_vocab(kinds=["estimator"])
    kinds = yaml.safe_load(path.read_text(encoding="utf-8"))["kinds"]
    assert sum(1 for k in kinds if k == "estimator" or (isinstance(k, dict) and k.get("name") == "estimator")) == 1


def test_fill_card_names_the_subject(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    site = store.root / "config" / "site.yaml"
    site.write_text(site.read_text(encoding="utf-8") + "subject: graduate econometrics\n", encoding="utf-8")
    task = fill.make_tasks(store, FakeRetriever(), nodes=[store.read_all().nodes[0].id], redo=True)[0]
    assert "studying graduate econometrics" in task.instructions and "{subject}" not in task.instructions
    assert "microeconomic" not in task.instructions.lower()
    assert "`lecture`" in task.instructions and "may contain mistakes" in task.instructions


def test_seed_card_prefers_the_vocab_files_kind_help_and_names_the_subject(tmp_path):
    root = tmp_path / "g"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license",
             title="Econometrics concept graph", subject="graduate econometrics")
    (root / "config" / "vocab.yaml").write_text(
        "kinds: [theorem, {name: estimator, help: a rule that maps a sample to an estimate}]\ntopics: [ols]\n", encoding="utf-8")
    hub = tmp_path / "hub"
    (hub / "academic_notes" / "econometrics" / "syllabus").mkdir(parents=True)
    task = seed.make_tasks(GraphStore(root), None, hub_root=str(hub), course="econometrics")[0]
    assert "- estimator: a rule that maps a sample to an estimate" in task.context
    assert "Subject: graduate econometrics" in task.context
    assert "(sets, relations, orders)" not in task.instructions


def test_scaffold_uses_title_subject_and_book_keys(tmp_path):
    root = tmp_path / "g"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license",
             title="Econometrics concept graph", subject="graduate econometrics", book_keys=["hansen", "hayashi"])
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Econometrics concept graph") and "graduate econometrics" in readme
    assert "microeconomic" not in readme.lower()
    site = yaml.safe_load((root / "config/site.yaml").read_text(encoding="utf-8"))
    assert site["title"] == "Econometrics concept graph" and site["subject"] == "graduate econometrics"
    assert "Source keys: hansen, hayashi" in (root / "config/seed.yaml").read_text(encoding="utf-8")
