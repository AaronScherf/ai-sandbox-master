from agent.concept_graph.sources import Passage, classify_passage

HUB = "C:/hub/academic-hub/academic_notes/microecon"


def test_rubinstein_chapter_file_maps_to_source_and_chapter():
    path = f"{HUB}/textbooks/processed_outputs/Rubenstein_Lecture_Notes_in_Microeconomic_Theory_2026/chapters/02_preferences.rag.md"
    assert classify_passage(path, "§2.1 Preference relations, p. 12") == ("rubinstein", "ch. 2, §2.1 Preference relations, p. 12")
    assert classify_passage(path, "") == ("rubinstein", "ch. 2")


def test_mwg_ok_lecture_slides_hw_and_other_sources():
    mwg = f"{HUB}/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md"
    ok = f"{HUB}/textbooks/processed_outputs/Ok_Real_Analysis_with_Economic_Applications_2026/chapters/04_continuity_i.rag.md"
    lecture = f"{HUB}/lecture_notes/processed_outputs/Microeconomics 2026-09-15 10.15.55.excalidraw.rag.md"
    slides = f"{HUB}/professor_notes/processed_outputs/2.Utility_Maximization_1.md"
    hw = f"{HUB}/problem_sets/processed_outputs/Homework_2.md"
    other = f"{HUB}/summaries/study_guide.md"
    assert classify_passage(mwg, "") == ("mwg", "ch. 1")
    assert classify_passage(ok, "") == ("ok", "ch. 4")
    assert classify_passage(lecture, "") == ("lecture", "2026-09-15")
    assert classify_passage(slides, "") == ("slides", "Utility Maximization 1")
    assert classify_passage(hw, "") == ("hw", "Homework_2")
    assert classify_passage(other, "") == ("other", "study_guide")


def test_ref_is_never_empty():
    for path in ("", "x.md", "C:/a/b/.md", "C:/hub/textbooks/Rubenstein_X/chapters/readme.rag.md"):
        source, ref = classify_passage(path, "")
        assert source and ref


def test_passage_exposes_its_offered_citation():
    p = Passage(id="P1", source="mwg", ref="ch. 1", text="t", path="p")
    assert p.offered == ("mwg", "ch. 1")
