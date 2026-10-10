from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.store import GraphStore


def test_scaffold_writes_a_documented_seed_config_that_loads_as_empty(tmp_path):
    root = tmp_path / "g"
    created = scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license")
    assert "config/seed.yaml" in created
    text = (root / "config" / "seed.yaml").read_text(encoding="utf-8")
    assert "must_include" in text and "textbook_chapters" in text and "scope" in text
    cfg = GraphStore(root).read_seed_config()
    assert cfg.scope == "" and cfg.must_include == [] and cfg.textbook_chapters == {}
