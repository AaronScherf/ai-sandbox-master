from cm_helpers import LANDSCAPE, PORTRAIT, make_pdf

from core.course_materials.signals import Facts, decide, pdf_shape

N = "academic_notes/demo"


def facts(path, fm=None, body="", card=None, shape=None):
    return Facts(path=f"{N}/{path}", frontmatter=fm or {}, body=body, card_doc_type=card, pdf_shape=shape)


def test_pdf_shape_reads_orientation_and_rotation_and_abstains_on_bad_files(tmp_path):
    assert pdf_shape(make_pdf(tmp_path / "l.pdf", *LANDSCAPE)) == "landscape"
    assert pdf_shape(make_pdf(tmp_path / "p.pdf", *PORTRAIT)) == "portrait"
    assert pdf_shape(make_pdf(tmp_path / "r.pdf", *PORTRAIT, rotate=90)) == "landscape"
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
    assert pdf_shape(tmp_path / "bad.pdf") == "unavailable"
    assert pdf_shape(tmp_path / "missing.pdf") == "unavailable"


def test_an_excalidraw_source_is_decisive_student_notes():
    d = decide(facts("x/processed_outputs/a.md", fm={"source_excalidraw": "a.excalidraw.md"}, body="exam exam midterm"))
    assert (d.role, d.format, d.flagged) == ("student_notes", "excalidraw", False)


def test_the_excalidraw_file_name_alone_is_a_medium_vote():
    d = decide(facts("x/E 2026-09-09 10.00.00.excalidraw.rag.md"))
    assert (d.role, d.format) == ("student_notes", "excalidraw") and d.flagged


def test_a_chapters_layout_is_a_decisive_textbook_under_any_folder_name():
    d = decide(facts("reading/processed_outputs/Greene_2018/chapters/03_ols.rag.md"))
    assert (d.role, d.format, d.flagged) == ("textbook", "chapter", False)
    front = decide(facts("textbooks/processed_outputs/Greene_2018/Greene_2018.rag.md"))
    assert front.role == "textbook" and front.flagged is False


def test_orientation_alone_names_the_format_not_the_provenance():
    d = decide(facts("misc/processed_outputs/week1.md", shape="landscape"))
    assert (d.role, d.format) == ("instructor", "slides")  # class material by default, but not confident
    assert d.flagged
    assert not any(v.signal == "pdf landscape" and v.field == "role" for v in d.votes)


def test_a_landscape_deck_with_any_class_signal_clears_review():
    d = decide(facts("professor_notes/processed_outputs/slides1.md", shape="landscape"))
    assert (d.role, d.format, d.flagged) == ("instructor", "slides", False)


def test_a_recitation_deck_is_class_material_and_not_flagged():
    d = decide(facts("ta_sessions/processed_outputs/r1.md", shape="landscape", body="Recitation 1: review"))
    assert (d.role, d.flagged) == ("recitation", False)


def test_class_roles_that_tie_are_not_flagged():
    d = decide(facts("professor_proofs/processed_outputs/r2.md", body="Recitation 2"))
    assert d.role == "instructor" and d.flagged is False  # instructor 2 vs recitation 2: both ground truth


def test_class_against_student_evidence_is_flagged():
    d = decide(facts("professor_notes/E 2026-09-09 10.00.00.excalidraw.rag.md"))
    assert d.flagged


def test_a_portrait_scan_in_the_professor_category_folder_is_instructor_handwriting():
    # The course's category folder is the owner's own filing (econometrics review, 2026-10-19: every such scan was
    # confirmed as the instructor's), so it clears review without any other class signal.
    body = "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1\n(1) iid\n\n<!-- page 2 -->\n\nY = Xb + e\n"
    d = decide(facts("professor_notes/processed_outputs/092126.md", shape="portrait", body=body))
    assert (d.role, d.format, d.flagged) == ("instructor", "handwritten", False)


def test_the_category_folder_outvotes_an_index_card_calling_a_ta_note_a_textbook():
    # econometrics ta_notes/A3-martingale-difference-sequence.md: the indexer labelled it textbook.
    d = decide(facts("ta_notes/processed_outputs/A3-martingale-difference-sequence.md", card="textbook"))
    assert (d.role, d.format, d.flagged) == ("recitation", "typeset", False)


def test_an_index_card_saying_textbook_is_decisive_only_with_a_chapters_layout():
    loose = decide(facts("reading/processed_outputs/survey.md", card="textbook"))
    assert loose.role == "textbook" and loose.flagged  # a hint to review, not a verdict
    assert decide(facts("reading/processed_outputs/Greene_2018/chapters/03_ols.rag.md", card="textbook")).flagged is False


def test_the_category_folders_vote_for_their_roles():
    assert decide(facts("problem_sets/processed_outputs/ps1.md")).role == "problem_set"
    assert decide(facts("syllabus/processed_outputs/s.md")).role == "syllabus"
    assert decide(facts("ta_notes/processed_outputs/01-terms.md")).role == "recitation"
    assert any(v.signal == "category folder ta_notes" for v in decide(facts("ta_notes/processed_outputs/01.md")).votes)
    # Deeper folders with the same names are not the course's category folder.
    assert not any(v.signal.startswith("category folder") for v in decide(facts("class_2024/syllabus/s.md")).votes)


def test_a_portrait_document_with_headings_and_long_lines_is_typeset():
    body = "# Problem Set 3\n\n" + ("This is a long typeset line of the problem statement that goes on. " * 2 + "\n") * 6
    body += "\nProblem 1\n(a) x\n\nProblem 2\n(b) y\n"
    d = decide(facts("stuff/processed_outputs/week3.md", shape="portrait", body=body))
    assert (d.role, d.format) == ("problem_set", "typeset")


def test_index_card_doc_type_is_a_strong_role_vote():
    d = decide(facts("ta_notes/processed_outputs/n1.md", card="ta_notes"))
    assert d.role == "recitation" and d.flagged is False


def test_an_index_card_saying_ta_notes_only_vouches_for_class_material():
    # The indexer's model must pick one of four labels and files the professor's decks under ta_notes (microecon,
    # 2026-10-19): the label says "class handout", not who wrote it, so it must not outvote a professor hint.
    d = decide(facts("professor_notes/processed_outputs/2.Utility_Maximization_1.md", card="ta_notes", shape="landscape"))
    assert (d.role, d.flagged) == ("instructor", False)
    alone = decide(facts("loose/processed_outputs/n1.md", card="ta_notes"))
    assert alone.flagged is False and alone.role == "instructor"  # class material, role unknown: the class default


def test_syllabus_wording_and_path_words():
    body = "Office hours: Tuesday. Grading: homework 40%. Course description: econometrics."
    d = decide(facts("syllabus/processed_outputs/s.md", body=body))
    assert d.role == "syllabus" and d.flagged is False


def test_nothing_known_is_other_and_flagged_with_evidence_of_the_pdf_state():
    d = decide(facts("x/processed_outputs/y.md", shape="unavailable"))
    assert (d.role, d.flagged) == ("other", True)
    assert any(v.signal == "pdf unavailable" for v in d.votes)
