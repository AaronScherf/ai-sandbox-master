from agent.concept_graph.sources import Passage, classify_passage, source_key
from core.course_materials import Catalog, Material

HUB = "C:/hub/academic-hub/academic_notes/microecon"
N = "academic_notes/microecon"


def test_without_a_catalog_paths_are_classified_by_their_own_shape():
    rub = f"{HUB}/textbooks/processed_outputs/Rubenstein_Lecture_Notes_2026/chapters/02_preferences.rag.md"
    assert classify_passage(rub, "§2.1 Preference relations, p. 12") == ("rubenstein", "ch. 2, §2.1 Preference relations, p. 12")
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_x.rag.md") == ("press", "ch. 1")
    assert classify_passage(f"{HUB}/lecture_notes/processed_outputs/Microeconomics 2026-09-15 10.15.55.excalidraw.rag.md") == ("lecture", "2026-09-15")
    assert classify_passage(f"{HUB}/professor_notes/processed_outputs/2.Utility_Maximization_1.md") == ("slides", "Utility Maximization 1")
    assert classify_passage(f"{HUB}/problem_sets/processed_outputs/Homework_2.md") == ("hw", "Homework_2")
    assert classify_passage(f"{HUB}/summaries/study_guide.md") == ("other", "study_guide")


def test_ref_is_never_empty():
    for path in ("", "x.md", "C:/a/b/.md", "C:/hub/textbooks/Rubenstein_X/chapters/readme.rag.md"):
        source, ref = classify_passage(path, "")
        assert source and ref


def test_passage_exposes_its_offered_citation():
    p = Passage(id="P1", source="mwg", ref="ch. 1", text="t", path="p")
    assert p.offered == ("mwg", "ch. 1")


def test_the_catalog_decides_book_keys_offerings_and_handwritten_notes():
    cat = Catalog(course="microecon", materials=[
        Material(path=f"{N}/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md", role="textbook", format="chapter", book="mwg"),
        Material(path=f"{N}/2024_class/Post lecture notes/processed_outputs/7.Consumer_Choice_2.md", role="instructor",
                 format="slides", offering="2024"),
        Material(path=f"{N}/2025_class/Homeworks/Solutions/processed_outputs/HW3_Sol.md", role="problem_set", offering="2025"),
        Material(path=f"{N}/2025_class/processed_outputs/Micro_I_Recitation_Notes.md", role="recitation", offering="2025"),
        Material(path=f"{N}/professor_notes/processed_outputs/092126.md", role="instructor", format="handwritten", date="2026-09-21"),
    ])
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md", "", cat) == ("mwg", "ch. 1")
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_MT_2011/Press_MT_2011.rag.md", "", cat)[0] == "mwg"
    assert classify_passage(f"{HUB}/2024_class/Post lecture notes/processed_outputs/7.Consumer_Choice_2.md", "", cat) == ("slides-2024", "Consumer Choice 2")
    assert classify_passage(f"{HUB}/2025_class/Homeworks/Solutions/processed_outputs/HW3_Sol.md", "", cat) == ("hw-2025", "HW3_Sol")
    assert classify_passage(f"{HUB}/2025_class/processed_outputs/Micro_I_Recitation_Notes.md", "", cat) == ("recitation-2025", "Micro I Recitation Notes")
    assert classify_passage(f"{HUB}/professor_notes/processed_outputs/092126.md", "", cat) == ("notes", "2026-09-21")


def test_a_path_the_catalog_lacks_is_classified_alone_and_remembered_as_a_miss():
    cat = Catalog(course="microecon", materials=[])
    assert classify_passage(f"{HUB}/problem_sets/processed_outputs/Homework_2.md", "", cat) == ("hw", "Homework_2")
    assert f"{N}/problem_sets/processed_outputs/Homework_2.md" in cat.misses


def test_source_key_rules():
    assert source_key(Material(path="x", role="instructor", format="slides")) == "slides"
    assert source_key(Material(path="x", role="instructor", format="typeset")) == "slides"
    assert source_key(Material(path="x", role="instructor", format="handwritten", offering="2024")) == "notes-2024"
    assert source_key(Material(path="x", role="textbook", book="hansen", offering="2024")) == "hansen"
    assert source_key(Material(path="x", role="syllabus")) == "syllabus"
