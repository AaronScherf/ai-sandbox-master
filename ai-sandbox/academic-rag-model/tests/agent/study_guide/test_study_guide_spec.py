# tests/agent/study_guide/test_study_guide_spec.py
import hashlib

import pytest

from agent.study_guide.spec import DEFAULT_MODEL, SpecError, load_spec

MINIMAL = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.2"]
  query = "wald"
"""

FULL = """
[guide]
id = "demo_guide"
title = "Demo"
course = "econ"

[models]
draft = "gemini-3.1-flash-lite"
enhance = "gemini-3.8-flash"

[draft]
prompt = "guide_v1"
label_match = "citation-substring"
top_k = 100
file_top_k = 40

[[note]]
heading = "A note"
body = "Some static text."

[[topic]]
title = "Topic A"
instruction = "Explain A."

  [[topic.source]]
  kind = "section"
  book = "Cameron"
  labels = ["7.3.1", "7.3.2"]
  exclude_labels = ["7.3.5"]
  query = "wald"
  max = 5

  [[topic.source]]
  kind = "file"
  file = "class_2024/Slides/slidesASYM.md"
  query = "wald statistic"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "wald"
  doc_types = ["textbook", "ta_notes"]
  exclude_guide = "academic_notes/econ/summaries/old.md"
  max = 8
  min_score = 0.72
  max_per_file = 2

[[topic]]
title = "Topic B"
instruction = "Explain B."

  [[topic.source]]
  kind = "file"
  file = "abc123"

[[comparison]]
title = "Compare"
instruction = "Compare A and B."
from = ["Topic A", "Topic B"]
take = 2
"""


def _write(tmp_path, text):
    p = tmp_path / "g.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_minimal_spec_gets_defaults(tmp_path):
    spec = load_spec(_write(tmp_path, MINIMAL))
    assert (spec.id, spec.title, spec.course) == ("demo_guide", "Demo", "econ")
    assert spec.draft_model == spec.enhance_model == DEFAULT_MODEL == "gemini-3.8-flash"
    assert (spec.prompt, spec.label_match, spec.top_k, spec.file_top_k) == ("tutor_v1", "heading-prefix", 180, 80)
    rule = spec.topics[0].sources[0]
    assert (rule.kind, rule.book, rule.labels, rule.exclude_labels, rule.max) == ("section", "Cameron", ("7.2",), (), 12)
    assert spec.notes == () and spec.comparisons == ()


def test_sha256_and_path_recorded(tmp_path):
    p = _write(tmp_path, MINIMAL)
    spec = load_spec(p)
    assert spec.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert spec.path == str(p)


def test_full_spec_parses_every_section(tmp_path):
    spec = load_spec(_write(tmp_path, FULL))
    assert spec.draft_model == "gemini-3.1-flash-lite" and spec.enhance_model == "gemini-3.8-flash"
    assert (spec.prompt, spec.label_match, spec.top_k, spec.file_top_k) == ("guide_v1", "citation-substring", 100, 40)
    assert [(n.heading, n.body) for n in spec.notes] == [("A note", "Some static text.")]
    section, file_rule, discover = spec.topics[0].sources
    assert (section.labels, section.exclude_labels, section.max) == (("7.3.1", "7.3.2"), ("7.3.5",), 5)
    assert (file_rule.kind, file_rule.file, file_rule.query, file_rule.max) == ("file", "class_2024/Slides/slidesASYM.md", "wald statistic", 6)
    assert (discover.doc_types, discover.exclude_guide, discover.max, discover.min_score, discover.max_per_file) == (
        ("textbook", "ta_notes"), "academic_notes/econ/summaries/old.md", 8, 0.72, 2)
    assert spec.topics[1].sources[0].query == ""
    cmp_ = spec.comparisons[0]
    assert (cmp_.title, cmp_.from_topics, cmp_.take) == ("Compare", ("Topic A", "Topic B"), 2)


@pytest.mark.parametrize("old,new,fragment", [
    ('id = "demo_guide"\n', "", "missing 'id'"),
    ('id = "demo_guide"', 'id = "Bad Id"', "id"),
    ('course = "econ"', 'course = "econ"\nbogus = 1', "unknown key"),
    ('instruction = "Explain A."', 'instruction = "Explain A."\nextra = 1', "unknown key"),
    ('kind = "section"', 'kind = "weird"', "kind"),
    ('labels = ["7.2"]', "", "labels"),
    ('book = "Cameron"\n', "", "book"),
    ('query = "wald"', 'query = "wald"\nmax = 0', "max"),
    ('query = "wald"', 'query = ""', "query"),
])
def test_invalid_specs_rejected(tmp_path, old, new, fragment):
    assert old in MINIMAL
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, MINIMAL.replace(old, new)))


@pytest.mark.parametrize("extra,fragment", [
    ('\n[bogus]\nx = 1\n', "unknown"),
    ('\n[draft]\nprompt = "nope"\n', "prompt"),
    ('\n[draft]\nlabel_match = "nope"\n', "label_match"),
    ('\n[draft]\ntop_k = 0\n', "top_k"),
    ('\n[models]\ndraft = ""\n', "draft"),
    ('\n[[comparison]]\ntitle = "C"\ninstruction = "x"\nfrom = ["Nope"]\n', "Nope"),
    ('\n[[comparison]]\ntitle = "C"\ninstruction = "x"\nfrom = ["Topic A"]\ntake = 0\n', "take"),
    ('\n[[comparison]]\ntitle = "Topic A"\ninstruction = "x"\nfrom = ["Topic A"]\n', "duplicate"),
])
def test_invalid_extra_tables_rejected(tmp_path, extra, fragment):
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, MINIMAL + extra))


def test_no_topics_rejected(tmp_path):
    head = MINIMAL.split("[[topic]]")[0]
    with pytest.raises(SpecError, match="at least one topic"):
        load_spec(_write(tmp_path, head))


def test_topic_without_sources_rejected(tmp_path):
    text = MINIMAL.split("  [[topic.source]]")[0]
    with pytest.raises(SpecError, match="source"):
        load_spec(_write(tmp_path, text))


def test_duplicate_topic_titles_rejected(tmp_path):
    topic = MINIMAL.split("[[topic]]")[1]
    with pytest.raises(SpecError, match="duplicate"):
        load_spec(_write(tmp_path, MINIMAL + "\n[[topic]]" + topic))


@pytest.mark.parametrize("rule,fragment", [
    ('kind = "file"\n  query = "x"', "file"),
    ('kind = "discover"', "query"),
    ('kind = "discover"\n  query = "x"\n  min_score = 1.5', "min_score"),
    ('kind = "discover"\n  query = "x"\n  doc_types = []', "doc_types"),
    ('kind = "section"\n  book = "B"\n  labels = ["7"]\n  query = "q"\n  file = "x"', "unknown key"),
])
def test_rule_specific_validation(tmp_path, rule, fragment):
    text = MINIMAL.split("  [[topic.source]]")[0] + "  [[topic.source]]\n  " + rule + "\n"
    with pytest.raises(SpecError, match=fragment):
        load_spec(_write(tmp_path, text))


def test_invalid_toml_rejected(tmp_path):
    with pytest.raises(SpecError, match="TOML"):
        load_spec(_write(tmp_path, "this is = = not toml"))


def test_missing_file_rejected(tmp_path):
    with pytest.raises(SpecError, match="not found"):
        load_spec(tmp_path / "nope.toml")
