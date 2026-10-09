# tests/agent/study_guide/test_study_guide_revise_spec.py
import pytest

from agent.study_guide.spec import DEFAULT_MODEL, SpecError, load_spec

BASE = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "file"
  file = "x"
"""
REVISE = """
[revise]
model = "gemini-test"
criteria = ["relevance", "correctness"]
relevance_low = 0.2
relevance_high = 0.7
dedup_similarity = 0.9
min_block_words = 40

  [[revise.evidence]]
  kind = "file"
  file = "class_2024/processed_outputs/2024 midterm-ans-key.md"
  weight = 3.0

  [[revise.evidence]]
  kind = "discover"
  query = "problem"
  doc_types = ["problem_set"]
"""


def _load(tmp_path, text):
    p = tmp_path / "spec.toml"
    p.write_text(text, encoding="utf-8")
    return load_spec(p)


def test_absent_table_means_no_revise(tmp_path):
    assert _load(tmp_path, BASE).revise is None


def test_revise_table_parses(tmp_path):
    r = _load(tmp_path, BASE + REVISE).revise
    assert (r.model, r.criteria, r.relevance_low, r.relevance_high) == ("gemini-test", ("relevance", "correctness"), 0.2, 0.7)
    assert (r.dedup_similarity, r.min_block_words) == (0.9, 40)
    assert [(e.rule.kind, e.weight) for e in r.evidence] == [("file", 3.0), ("discover", 1.0)]
    assert r.evidence[1].rule.doc_types == ("problem_set",)


def test_defaults(tmp_path):
    r = _load(tmp_path, BASE + "\n[revise]\n").revise
    assert r.model == DEFAULT_MODEL and r.criteria == ("relevance", "dedup", "correctness", "organization")
    assert (r.relevance_low, r.relevance_high, r.dedup_similarity, r.min_block_words) == (0.30, 0.60, 0.92, 60)
    assert r.evidence == ()


@pytest.mark.parametrize("old,new,fragment", [
    ('model = "gemini-test"', 'model = "gemini-test"\nbogus = 1', "unknown key"),
    ('criteria = ["relevance", "correctness"]', 'criteria = ["relevance", "style"]', "criteria"),
    ("relevance_low = 0.2", "relevance_low = 0.9", "relevance_low"),
    ("weight = 3.0", "weight = 0", "weight"),
    ('kind = "file"\n  file = "class_2024/processed_outputs/2024 midterm-ans-key.md"', 'kind = "weird"', "kind"),
])
def test_invalid_revise_tables_rejected(tmp_path, old, new, fragment):
    assert old in REVISE
    with pytest.raises(SpecError, match=fragment):
        _load(tmp_path, BASE + REVISE.replace(old, new))


def test_light_thinking_defaults_to_low_and_rejects_unknown_levels(tmp_path):
    assert _load(tmp_path, BASE + "\n[revise]\n").revise.light_thinking == "low"
    assert _load(tmp_path, BASE + '\n[revise]\nlight_thinking = "default"\n').revise.light_thinking == "default"
    with pytest.raises(SpecError, match="light_thinking"):
        _load(tmp_path, BASE + '\n[revise]\nlight_thinking = "off"\n')
