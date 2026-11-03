from core.env.hub_vocab_learn import propose_vocabulary
from core.env.hub_vocabulary import Vocabulary


def _file(hub, rel):
    path = hub / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def _names(items):
    return {item["name"]: item["courses"] for item in items}


def test_name_with_content_in_two_courses_is_a_category_candidate(tmp_path):
    for course in ("econ", "micro"):
        _file(tmp_path, f"academic_notes/{course}/exam_kits/a.md")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert _names(got["category_candidates"]) == {"exam_kits": ["econ", "micro"]}


def test_single_course_name_is_unclassified(tmp_path):
    _file(tmp_path, "academic_notes/econ/Recitation Notes/a.md")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert _names(got["unclassified"]) == {"Recitation Notes": ["econ"]}
    assert got["category_candidates"] == []


def test_numbered_year_and_part_names_are_group_candidates(tmp_path):
    for name in ("part_3", "2024_class", "class_2025", "2026", "week_12"):
        _file(tmp_path, f"academic_notes/econ/{name}/a.md")
    got = propose_vocabulary(tmp_path, Vocabulary(group_patterns=(r"^part_\d+$", r"^class_\d{4}$", r"^\d{4}_class$")))
    assert set(_names(got["group_candidates"])) == {"part_3", "2024_class", "class_2025", "2026"}
    assert "week_12" in _names(got["unclassified"])


def test_a_folder_above_a_known_category_is_a_group_candidate(tmp_path):
    _file(tmp_path, "academic_notes/econ/spring_block/lecture_notes/a.md")
    vocab = Vocabulary(names={"lecture_notes": "category"})
    got = propose_vocabulary(tmp_path, vocab)
    assert "spring_block" in _names(got["group_candidates"])


def test_known_names_are_never_proposed_again(tmp_path):
    for course in ("econ", "micro"):
        _file(tmp_path, f"academic_notes/{course}/Lecture_Notes/a.md")
    got = propose_vocabulary(tmp_path, Vocabulary(names={"lecture_notes": "category"}))
    assert all(not got[key] for key in ("category_candidates", "group_candidates", "unclassified", "ignore_candidates"))


def test_hidden_folders_and_non_content_files_are_skipped(tmp_path):
    for course in ("econ", "micro"):
        _file(tmp_path, f"academic_notes/{course}/.git/a.md")
        _file(tmp_path, f"academic_notes/{course}/notes_only/readme.txt")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert all(not got[key] for key in ("category_candidates", "group_candidates", "unclassified"))


def test_both_roots_count_each_course_once(tmp_path):
    _file(tmp_path, "academic_notes/econ/exam_kits/a.md")
    _file(tmp_path, "academic_resources/econ/exam_kits/a.pdf")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert _names(got["unclassified"]) == {"exam_kits": ["econ"]}
    _file(tmp_path, "academic_resources/micro/exam_kits/b.pdf")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert _names(got["category_candidates"]) == {"exam_kits": ["econ", "micro"]}


def test_infrastructure_names_are_suggested_as_ignore_not_category(tmp_path):
    for course in ("econ", "micro"):
        _file(tmp_path, f"academic_notes/{course}/summaries/a.md")
    got = propose_vocabulary(tmp_path, Vocabulary())
    assert _names(got["ignore_candidates"]) == {"summaries": ["econ", "micro"]}
    assert got["category_candidates"] == []


def test_textbook_and_ignored_folders_are_not_descended(tmp_path):
    for course in ("econ", "micro"):
        _file(tmp_path, f"academic_resources/{course}/textbooks/processed_outputs/Book_{course}/ch1.md")
    got = propose_vocabulary(tmp_path, Vocabulary(names={"processed_outputs": "ignore"}))
    assert all(not got[key] for key in ("category_candidates", "group_candidates", "unclassified"))
