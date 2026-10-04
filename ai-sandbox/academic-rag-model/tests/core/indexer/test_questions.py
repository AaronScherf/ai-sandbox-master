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
