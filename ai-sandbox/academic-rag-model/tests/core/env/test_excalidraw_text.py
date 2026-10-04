from core.env import excalidraw_text as et
from core.env.excalidraw_text import QUESTION_TAG, QUESTION_TAG_RE, split_labeled_segments


def test_question_tag_constant():
    assert QUESTION_TAG == "[Question]"


def test_tag_regex_matches_open_and_resolved_markers_only():
    text = (
        "a [Question] b [Question: answered -> f.md#q1-ab] c "
        "[Question: answered (ungrounded) -> f.md#q2-cd] d [Questions] e [Question2]"
    )
    assert [m.group(0) for m in QUESTION_TAG_RE.finditer(text)] == [
        "[Question]",
        "[Question: answered -> f.md#q1-ab]",
        "[Question: answered (ungrounded) -> f.md#q2-cd]",
    ]


def test_split_labeled_segments_orders_labels_and_strips_chunk_markers():
    raw = (
        "<!-- chunk 1 -->\n\n**[Handwritten]**\nnote a\n\n**[Slide]**\n* Slide one\n\n"
        "<!-- chunk 2 -->\n\n**[Handwritten]**\nnote b\n"
    )
    segments = split_labeled_segments(raw)
    assert [label for label, _ in segments] == ["Handwritten", "Slide", "Handwritten"]
    assert all("<!-- chunk" not in text for _, text in segments)
    assert segments[1][1] == "* Slide one"


def test_split_labeled_segments_treats_leading_unlabeled_text_as_handwritten():
    assert split_labeled_segments("stray words\n\n**[Slide]**\n* s\n")[0] == ("Handwritten", "stray words")


def test_every_module_uses_the_one_shared_definition():
    from core.indexer import related
    from pipelines.transcribe_notes import transcribe_excalidraw as te

    assert te.split_labeled_segments is split_labeled_segments
    assert te._SEGMENT_LABEL_RE is et.SEGMENT_LABEL_RE
    assert te._CHUNK_MARKER_RE is et.CHUNK_MARKER_RE
    assert te._QUESTION_TAG == QUESTION_TAG
    assert related._LABEL_RE is et.SEGMENT_LABEL_RE
    assert related._CHUNK_MARKER_RE is et.CHUNK_MARKER_RE
