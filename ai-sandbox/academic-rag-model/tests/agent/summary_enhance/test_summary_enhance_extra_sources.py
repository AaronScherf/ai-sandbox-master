# tests/agent/summary_enhance/test_summary_enhance_extra_sources.py
import json

import pytest

from agent.summary_enhance.render import render
from agent.summary_enhance.schema import Block, Enhanced, Section, Topic
from agent.summary_enhance.source_loader import ExtraSource, MissingSourcesError, load_guide


def _extra(topic, chunk_id="notes-1", file_id="notes", **kw):
    return ExtraSource(topic, chunk_id, file_id, "academic_notes/econ/class_2024/notes.md", "Notes p. 3", **kw)


def test_extras_follow_the_guides_own_refs_with_continuing_labels(vault):
    guide = load_guide(vault.guide, [_extra("Wald", doc_type="ta_notes", offering="class_2024")])
    assert [s.label for s in guide.sources] == ["S1", "S2", "S3", "S4"]
    extra = guide.sources[3]
    assert (extra.chunk_id, extra.doc_type, extra.offering, extra.citation) == ("notes-1", "ta_notes", "class_2024", "Notes p. 3")
    assert extra.text.startswith("Class notes:")


def test_extra_that_the_guide_already_cites_reuses_its_label(vault):
    guide = load_guide(vault.guide, [_extra("Wald", chunk_id="cam-1", file_id="cam")])
    assert len(guide.sources) == 3
    assert guide.labels_for("Wald") == {"S1"}


def test_topic_labels_are_per_topic_and_normalized(vault):
    guide = load_guide(vault.guide, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam"),
                                     _extra("LM", chunk_id="unused-1", file_id="cam")])
    assert guide.labels_for("wald") == {"S4"}
    assert guide.labels_for("  LM ") == {"S1", "S5"}
    assert guide.labels_for("Never mapped") == {"S1", "S2", "S3", "S4", "S5"}


def test_without_extras_every_topic_may_cite_every_source(vault):
    guide = load_guide(vault.guide)
    assert guide.topic_labels == {} and guide.labels_for("Anything") == {"S1", "S2", "S3"}


@pytest.mark.parametrize("extra", [_extra("Wald", chunk_id="gone-9"), _extra("Wald", file_id="WRONG")])
def test_missing_or_mismatched_extras_are_rejected(vault, extra):
    with pytest.raises(MissingSourcesError):
        load_guide(vault.guide, [extra])


def _enhanced():
    return Enhanced([Topic("Wald", [Section("A", [Block("grounded", "text", ["S4"])])])])


def test_source_map_carries_doc_type_and_offering_when_known(vault):
    guide = load_guide(vault.guide, [_extra("Wald", doc_type="ta_notes", offering="class_2024")])
    text = render(guide, _enhanced(), model="m", generated_at="t", worked_example=False, min_words=1)
    front = text.split("\n---\n\n", 1)[0]
    smap = json.loads(next(l for l in front.splitlines() if l.startswith("source_map: "))[len("source_map: "):])
    assert smap == [{"chunk_id": "notes-1", "file_id": "notes", "path": "academic_notes/econ/class_2024/notes.md",
                     "citation": "Notes p. 3", "doc_type": "ta_notes", "offering": "class_2024",
                     "used_in": ["Wald > A"]}]


def test_source_map_omits_empty_fields(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    text = render(guide, _enhanced(), model="m", generated_at="t", worked_example=False, min_words=1)
    entry = json.loads(next(l for l in text.splitlines() if l.startswith("source_map: "))[len("source_map: "):])[0]
    assert "doc_type" not in entry and "offering" not in entry
