from agent.concept_graph.sources import classify_passage

BOOK = "C:/hub/academic_notes/microecon/textbooks/processed_outputs/Rubenstein_Models_in_Microeconomic_Theory_2023/Rubenstein_Models_in_Microeconomic_Theory_2023.rag.md"


def test_markdown_emphasis_is_stripped_from_refs():
    source, ref = classify_passage(BOOK, "§**Definition 1.1: Complete binary relation**, p. 23")
    assert source == "rubenstein"
    assert "*" not in ref and "Definition 1.1 - Complete binary relation" in ref and ref.endswith("p. 23")


def test_property_names_with_emphasis_and_math_markers_are_cleaned():
    _, ref = classify_passage(BOOK, "§2.3 Property *α*, p. 39")
    assert ref.endswith("§2.3 Property α, p. 39")


def test_very_long_citations_are_shortened_but_keep_the_page():
    long_heading = "§" + "A very long heading " * 12 + ", p. 7"
    _, ref = classify_passage(BOOK, long_heading)
    assert len(ref) <= 180 and ref.endswith("p. 7")


def test_refs_are_single_line():
    _, ref = classify_passage(BOOK, "§Two\nline heading, p. 1")
    assert "\n" not in ref
