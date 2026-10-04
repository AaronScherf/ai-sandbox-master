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


from core.indexer.questions import apply_markers, marker_for, raw_tags

RAW = (
    "---\nchunks: 1\n---\n\n**[Handwritten]**\n"
    "[Question] Is IIA nec. & sufficient?\nother\n[Question] why not reflexivity?\n"
)
RAG = (
    "---\nx: y\n---\n\nProse. [Question] Is IIA necessary and sufficient?\n\n"
    "More. [Question] why not reflexivity?\n"
)


def _entry_for(tag, grounded=True):
    return Entry(
        qid=tag.qid, question=tag.text, grounded=grounded, model="m", resolved_at="t",
        answer="ans", sources=["s"] if grounded else [],
    )


def _setup(tmp_path, raw=RAW, rag=RAG, entry_indexes=(0, 1), grounded=True):
    raw_path = str(tmp_path / "N.excalidraw.md")
    rag_path = rag_path_for(raw_path)
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(rag)
    tags = raw_tags(raw)
    entries = [_entry_for(tags[i], grounded) for i in entry_indexes]
    if entries:
        write_sidecar(sidecar_path_for(raw_path), {"questions": str(len(entries))}, entries)
    return raw_path, rag_path, tags


def _read(path):
    return open(path, encoding="utf-8").read()


def test_marker_text_for_grounded_and_ungrounded_entries():
    grounded = Entry(qid="q1-ab12cd34", question="q?", grounded=True, model="m", resolved_at="t")
    ungrounded = Entry(qid="q1-ab12cd34", question="q?", grounded=False, model="m", resolved_at="t")
    assert marker_for(grounded, "N.excalidraw.questions.md") == "[Question: answered -> N.excalidraw.questions.md#q1-ab12cd34]"
    assert marker_for(ungrounded, "N.excalidraw.questions.md") == (
        "[Question: answered (ungrounded) -> N.excalidraw.questions.md#q1-ab12cd34]"
    )


def test_markers_are_applied_by_position_when_tag_counts_match_and_wording_differs(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path)
    assert apply_markers(raw_path, rag_path) is True
    text = _read(rag_path)
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[0].qid}] Is IIA necessary and sufficient?" in text
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[1].qid}] why not reflexivity?" in text


def test_ungrounded_entries_get_the_ungrounded_marker(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path, grounded=False)
    apply_markers(raw_path, rag_path)
    assert f"[Question: answered (ungrounded) -> N.excalidraw.questions.md#{tags[0].qid}]" in _read(rag_path)


def test_a_tag_without_a_sidecar_entry_stays_open(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path, entry_indexes=(1,))
    apply_markers(raw_path, rag_path)
    text = _read(rag_path)
    assert "Prose. [Question] Is IIA necessary and sufficient?" in text
    assert f"#{tags[1].qid}]" in text


def test_second_application_changes_nothing(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path)
    apply_markers(raw_path, rag_path)
    after_first = _read(rag_path)
    assert apply_markers(raw_path, rag_path) is False
    assert _read(rag_path) == after_first


def test_when_counts_differ_tags_pair_by_text_similarity_and_unmatched_entries_go_stale(tmp_path):
    rag_one_tag = "---\nx: y\n---\n\nOnly. [Question] Why not reflexivity?\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag_one_tag)
    apply_markers(raw_path, rag_path)
    assert f"[Question: answered -> N.excalidraw.questions.md#{tags[1].qid}] Why not reflexivity?" in _read(rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    stale = {e.qid: e.stale for e in entries}
    assert stale == {tags[0].qid: True, tags[1].qid: False}


def test_a_dissimilar_tag_is_left_open_when_counts_differ(tmp_path):
    rag = "---\nx: y\n---\n\nOnly. [Question] something entirely unrelated to either\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag)
    apply_markers(raw_path, rag_path)
    assert "[Question] something entirely unrelated to either" in _read(rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert all(e.stale for e in entries)


def test_stale_entries_recover_when_the_tags_match_again(tmp_path):
    rag_one_tag = "---\nx: y\n---\n\nOnly. [Question] Why not reflexivity?\n"
    raw_path, rag_path, tags = _setup(tmp_path, rag=rag_one_tag)
    apply_markers(raw_path, rag_path)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(RAG)
    apply_markers(raw_path, rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert not any(e.stale for e in entries)


def test_a_marker_reverts_to_open_when_its_sidecar_entry_is_removed(tmp_path):
    raw_path, rag_path, tags = _setup(tmp_path)
    apply_markers(raw_path, rag_path)
    write_sidecar(sidecar_path_for(raw_path), {"questions": "1"}, [_entry_for(tags[1])])
    apply_markers(raw_path, rag_path)
    text = _read(rag_path)
    assert "Prose. [Question] Is IIA necessary and sufficient?" in text
    assert f"#{tags[1].qid}]" in text


def test_no_sidecar_leaves_open_tags_untouched(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path, entry_indexes=())
    assert apply_markers(raw_path, rag_path) is False
    assert _read(rag_path) == RAG


def test_missing_rag_file_is_a_noop(tmp_path):
    raw_path, rag_path, _ = _setup(tmp_path)
    os.remove(rag_path)
    assert apply_markers(raw_path, rag_path) is False


from core.indexer.questions import rekey_entries

RAW_TWO = "---\nchunks: 1\n---\n\n[Question] first question?\nx\n[Question] why not reflexivity?\n"
RAW_AFTER_DELETE = "---\nchunks: 1\n---\n\n[Question] why not reflexivity?\n"


def test_rekey_moves_an_answer_to_the_ordinal_its_question_shifted_to():
    old = raw_tags(RAW_TWO)
    entries = [_entry_for(old[0]), _entry_for(old[1])]
    new = raw_tags(RAW_AFTER_DELETE)  # the first question was deleted; "second" is now q1
    assert new[0].qid != old[1].qid and new[0].qid.split("-")[1] == old[1].qid.split("-")[1]
    assert rekey_entries(new, entries) is True
    assert entries[1].qid == new[0].qid
    assert entries[0].qid == old[0].qid  # no matching question left: untouched, stays stale-able


def test_rekey_is_a_noop_when_ids_already_match():
    tags = raw_tags(RAW_TWO)
    entries = [_entry_for(t) for t in tags]
    assert rekey_entries(tags, entries) is False
    assert [e.qid for e in entries] == [t.qid for t in tags]


def test_rekey_never_reassigns_an_entry_whose_id_is_still_current():
    tags = raw_tags("[Question] same words?\n[Question] same words?\n")
    only_second = [_entry_for(tags[1])]
    assert rekey_entries(tags, only_second) is False
    assert only_second[0].qid == tags[1].qid


def test_apply_markers_keeps_an_answer_attached_after_the_raw_transcript_shifts_ordinals(tmp_path):
    raw_path, rag_path, old_tags = _setup(tmp_path)
    apply_markers(raw_path, rag_path)
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(RAW_AFTER_DELETE)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write("---\nx: y\n---\n\nOnly. [Question] why not reflexivity?\n")
    new_tags = raw_tags(RAW_AFTER_DELETE)
    assert apply_markers(raw_path, rag_path) is True
    assert f"[Question: answered -> N.excalidraw.questions.md#{new_tags[0].qid}] why not reflexivity?" in _read(rag_path)
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    by_text = {e.question: e for e in entries}
    assert by_text["why not reflexivity?"].qid == new_tags[0].qid and not by_text["why not reflexivity?"].stale
