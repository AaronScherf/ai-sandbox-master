import os

from core.indexer.related import (
    containment,
    handwriting_text,
    lecture_date,
    raw_transcript_path,
    read_raw,
)

HW = (
    "preference relation complete transitive define strict preference asymmetric "
    "indifference symmetric choice set nonempty by completeness utility function "
    "represents preferences ordinal"
)
HW_OTHER = (
    "consumer demand slutsky equation income substitution effect compensated hicksian "
    "marshallian expenditure minimization duality"
)


def test_raw_transcript_path_drops_the_rag_infix():
    assert raw_transcript_path("a/processed_outputs/X 2026-09-15.excalidraw.rag.md") == (
        "a/processed_outputs/X 2026-09-15.excalidraw.md"
    )


def test_raw_transcript_path_is_none_for_other_cards():
    assert raw_transcript_path("a/textbook.md") is None


def test_lecture_date_reads_first_iso_date_from_basename():
    assert lecture_date("a/b/Microeconomics with slides 2026-09-15 10.15.55.excalidraw.rag.md") == "2026-09-15"
    assert lecture_date("a/2026-01-01/Microeconomics.excalidraw.rag.md") is None


def test_handwriting_text_slides_note_keeps_only_handwritten_blocks():
    body = (
        "<!-- chunk 1 -->\n\n**[Slide]**\nslide words here\n\n**[Handwritten]**\n"
        f"{HW}\n\n<!-- chunk 2 -->\n\n**[Slide]**\nmore slide words\n"
    )
    text = handwriting_text({"embedded_slides": "true"}, body)
    assert "preference relation" in text
    assert "slide words" not in text
    assert "chunk" not in text


def test_handwriting_text_plain_note_is_whole_body_without_chunk_markers():
    text = handwriting_text({}, f"<!-- chunk 1 -->\n\n{HW}\n")
    assert "preference relation" in text
    assert "chunk" not in text


def test_containment_identical_is_one_and_disjoint_is_zero():
    assert containment(HW, HW) == 1.0
    assert containment(HW, HW_OTHER) == 0.0


def test_containment_is_asymmetric_subset_in_superset():
    assert containment(HW, HW + " " + HW_OTHER) == 1.0
    assert containment(HW + " " + HW_OTHER, HW) < 0.6


def test_containment_of_text_with_no_ngrams_is_zero():
    assert containment("", HW) == 0.0
    assert containment("two words", HW) == 0.0


def test_read_raw_returns_frontmatter_and_body_or_none(tmp_path):
    out = tmp_path / "academic_notes" / "c" / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True)
    (out / "N 2026-09-15.excalidraw.md").write_text("---\nchunks: 2\nembedded_slides: true\n---\n\nBODY", encoding="utf-8")
    card = {"path": "academic_notes/c/lecture_notes/processed_outputs/N 2026-09-15.excalidraw.rag.md"}
    meta, body = read_raw(str(tmp_path), card)
    assert meta["embedded_slides"] == "true" and body == "BODY"
    assert read_raw(str(tmp_path), {"path": "academic_notes/c/lecture_notes/processed_outputs/Gone.excalidraw.rag.md"}) is None
    assert read_raw(str(tmp_path), {"path": "x.md"}) is None
