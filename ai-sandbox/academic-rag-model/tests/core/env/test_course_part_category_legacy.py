"""Pins what course_part_category returned before the hub vocabulary existed.

Every row must keep holding after the parser becomes vocabulary-driven: a path
with no confirmed category falls back to this behavior (Task 3 of the P2 plan).
"""
import pytest

from core.env.academic_hub_paths import course_part_category

LEGACY_CASES = [
    ("foo/bar.md", None),
    ("academic_notes/econ", None),
    ("academic_notes/econ/a.md", ("econ", None, None)),
    ("academic_notes/econ/lecture_notes/a.md", ("econ", None, "lecture_notes")),
    ("academic_notes/econ/part_2/problem_sets/a.md", ("econ", "part_2", "problem_sets")),
    ("academic_notes/econ/part_1/a.md", ("econ", "part_1", None)),
    ("academic_notes\\econ\\ta_notes\\a.md", ("econ", None, "ta_notes")),
    ("academic_resources/econometrics/class_2024/Recitations/x.pdf", ("econometrics", None, "class_2024")),
    ("academic_resources/math_methods/Problem Sets and Solutions/x.md",
     ("math_methods", None, "Problem Sets and Solutions")),
    ("academic_notes/microecon/textbooks/processed_outputs/Book_2013/x.md", ("microecon", None, "textbooks")),
    ("C:/x/academic_notes/backup/academic_resources/econ/lecture_notes/a.md", ("econ", None, "lecture_notes")),
]


@pytest.mark.usefixtures("seed_hub_config")
@pytest.mark.parametrize(("path", "expected"), LEGACY_CASES)
def test_legacy_behavior(path, expected):
    assert course_part_category(path) == expected
