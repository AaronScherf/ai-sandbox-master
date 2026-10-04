from core.indexer.questions import find_tags, normalize, question_id, raw_tags


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Why   NOT\nreflexivity? ") == "why not reflexivity?"


def test_line_start_tag_text_runs_to_the_question_mark():
    tags = find_tags("intro\n[Question] why not reflexivity? and then more words\nnext")
    assert [t.text for t in tags] == ["why not reflexivity?"]


def test_mid_sentence_tag_text_is_cut_at_the_next_question_mark():
    text = "We define d_A as the distance [Question] what is furthest you can get from A while in B? and d_B as the distance"
    assert find_tags(text)[0].text == "what is furthest you can get from A while in B?"


def test_tag_alone_on_its_line_takes_the_next_non_blank_line():
    assert find_tags("[Question]\n\nWhat if X is not finite?\nx")[0].text == "What if X is not finite?"


def test_text_without_a_question_mark_runs_to_end_of_line():
    assert find_tags("[Question] explain the proof\nnext line")[0].text == "explain the proof"


def test_text_is_capped_and_whitespace_collapsed():
    text = find_tags("[Question] " + "word  " * 100)[0].text
    assert len(text) <= 200 and "  " not in text


def test_ordinals_are_one_based_in_document_order_and_embedded_in_ids():
    tags = find_tags("[Question] a?\n[Question] b?")
    assert [t.ordinal for t in tags] == [1, 2]
    assert tags[0].qid.startswith("q1-") and tags[1].qid.startswith("q2-")


def test_question_id_ignores_case_and_whitespace_but_not_text_or_ordinal():
    assert question_id(1, "Why not   reflexivity?") == question_id(1, "why not reflexivity?")
    assert question_id(1, "why not reflexivity?") != question_id(1, "why not symmetry?")
    assert question_id(1, "x?") != question_id(2, "x?")
    assert len(question_id(1, "x?").split("-")[1]) == 8


def test_resolved_markers_count_as_tags_and_the_span_covers_the_whole_marker():
    marker = "[Question: answered -> f.questions.md#q1-ab12cd34]"
    tags = find_tags(marker + " why not reflexivity?")
    assert len(tags) == 1 and tags[0].text == "why not reflexivity?"
    assert tags[0].end - tags[0].start == len(marker)


def test_raw_tags_ignores_frontmatter():
    raw = "---\nnote: [Question] fake?\n---\n\n[Question] real?\n"
    assert [t.text for t in raw_tags(raw)] == ["real?"]


import os
from unittest.mock import patch

import pytest

from core.indexer.questions import (
    SIDECAR_SUFFIX,
    Entry,
    parse_entries,
    rag_path_for,
    read_sidecar,
    render_entry,
    sidecar_path_for,
    write_sidecar,
)


def _entry(**kw):
    base = dict(
        qid="q1-1a2b3c4d", question="why not reflexivity?", grounded=True, model="gemini-3.6-flash",
        resolved_at="2026-10-03T12:00:00+00:00", stale=False, context="x succsim y",
        answer="Because $x$ is related.\n\n$$u(x) \\geq u(y)$$\n\nSecond paragraph.",
        sources=["a/b.md (p. 3)", "c/d.md (section 2)"],
    )
    base.update(kw)
    return Entry(**base)


def test_paths_derive_from_the_raw_transcript_path():
    raw = "a/processed_outputs/N 2026-09-15.excalidraw.md"
    assert sidecar_path_for(raw) == "a/processed_outputs/N 2026-09-15" + SIDECAR_SUFFIX
    assert rag_path_for(raw) == "a/processed_outputs/N 2026-09-15.excalidraw.rag.md"
    with pytest.raises(ValueError):
        sidecar_path_for("a/b.md")
    with pytest.raises(ValueError):
        rag_path_for("a/b.md")


def test_entry_round_trips_grounded_with_sources():
    entry = _entry()
    assert parse_entries(render_entry(entry)) == [entry]


def test_entry_round_trips_ungrounded_with_no_sources():
    entry = _entry(grounded=False, sources=[])
    rendered = render_entry(entry)
    assert "not sourced from your course materials" in rendered
    assert parse_entries(rendered) == [entry]


def test_stale_flag_round_trips():
    assert parse_entries(render_entry(_entry(stale=True)))[0].stale is True


def test_answer_headings_cannot_split_an_entry():
    entry = _entry(answer="## Heading in answer\ntext")
    parsed = parse_entries(render_entry(entry) + "\n" + render_entry(_entry(qid="q2-aaaaaaaa")))
    assert [p.qid for p in parsed] == ["q1-1a2b3c4d", "q2-aaaaaaaa"]
    assert parsed[0].answer.startswith("### Heading in answer")


def test_write_then_read_sidecar_keeps_frontmatter_and_entries(tmp_path):
    path = str(tmp_path / ("N" + SIDECAR_SUFFIX))
    fields = {"source_excalidraw": "a/N.excalidraw.md", "questions": "2"}
    entries = [_entry(), _entry(qid="q2-bbbbbbbb", question="what if X is infinite?")]
    write_sidecar(path, fields, entries)
    got_fields, got_entries = read_sidecar(path)
    assert got_fields == fields and got_entries == entries
    assert not os.path.exists(path + ".tmp")


def test_read_sidecar_of_a_missing_file_is_empty(tmp_path):
    assert read_sidecar(str(tmp_path / "none.md")) == ({}, [])


def test_failed_write_keeps_the_existing_sidecar_and_removes_the_temp_file(tmp_path):
    path = str(tmp_path / ("N" + SIDECAR_SUFFIX))
    write_sidecar(path, {"questions": "1"}, [_entry()])
    before = open(path, encoding="utf-8").read()
    with patch("core.indexer.questions.os.replace", side_effect=OSError("disk")):
        with pytest.raises(OSError):
            write_sidecar(path, {"questions": "2"}, [_entry(), _entry(qid="q2-bbbbbbbb")])
    assert open(path, encoding="utf-8").read() == before
    assert not os.path.exists(path + ".tmp")
