import json
import os

import pytest

from core.env.academic_hub_paths import (
    find_containing_offering_label,
    read_subset_marker,
    resolve_output_dir,
    textbook_rag_md_path,
    to_notes_root,
    to_resources_root,
)


def test_to_resources_root_swaps_the_segment_in_an_os_native_path():
    path = os.path.join("C:" + os.sep, "hub", "academic_notes", "econometrics", "ta_notes", "foo.pdf")
    result = to_resources_root(path)
    assert "academic_resources" in result
    assert "academic_notes" not in result
    assert result.endswith(os.path.join("econometrics", "ta_notes", "foo.pdf"))


def test_to_resources_root_preserves_forward_slash_relative_paths():
    assert (
        to_resources_root("academic_notes/econometrics/ta_notes/foo.pdf")
        == "academic_resources/econometrics/ta_notes/foo.pdf"
    )


def test_to_notes_root_is_the_inverse():
    assert (
        to_notes_root("academic_resources/econometrics/ta_notes/foo.pdf")
        == "academic_notes/econometrics/ta_notes/foo.pdf"
    )


def test_to_resources_root_raises_when_no_academic_notes_segment():
    with pytest.raises(ValueError):
        to_resources_root("some/other/path/foo.pdf")


def test_to_notes_root_raises_when_no_academic_resources_segment():
    with pytest.raises(ValueError):
        to_notes_root("academic_notes/econometrics/ta_notes/foo.pdf")


def test_resolve_output_dir_mirrors_when_source_under_resources():
    source = os.path.join("academic_resources", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "ta_notes", "processed_outputs")


def test_resolve_output_dir_stays_a_sibling_when_source_still_under_notes():
    source = os.path.join("academic_notes", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "ta_notes", "processed_outputs")


def test_resolve_output_dir_stays_a_sibling_for_an_excalidraw_scene_file():
    # The .excalidraw.md anchor never moves -- always sibling behavior,
    # identical to today, regardless of where its image sibling lives.
    source = os.path.join("academic_notes", "econometrics", "lecture_notes", "Drawing.excalidraw.md")
    result = resolve_output_dir(source)
    assert result == os.path.join("academic_notes", "econometrics", "lecture_notes", "processed_outputs")


def test_resolve_output_dir_works_with_a_full_absolute_windows_style_path():
    source = os.path.join("C:" + os.sep, "hub", "academic_resources", "econometrics", "ta_notes", "foo.pdf")
    result = resolve_output_dir(source)
    expected = os.path.join("C:" + os.sep, "hub", "academic_notes", "econometrics", "ta_notes", "processed_outputs")
    assert result == expected


def test_textbook_rag_md_path_mirrors_into_notes_for_a_resources_book_dir():
    book_dir = os.path.join("hub", "academic_resources", "econometrics", "textbooks", "processed_outputs", "Hansen_2022")
    assert textbook_rag_md_path(book_dir) == os.path.join(
        "hub", "academic_notes", "econometrics", "textbooks", "processed_outputs", "Hansen_2022", "Hansen_2022.rag.md",
    )


def test_textbook_rag_md_path_keeps_nested_subfolders_like_bonus():
    book_dir = "academic_resources/microecon/textbooks/Bonus/processed_outputs/Rubinstein_2023"
    assert textbook_rag_md_path(book_dir) == os.path.join(
        "academic_notes/microecon/textbooks/Bonus/processed_outputs/Rubinstein_2023", "Rubinstein_2023.rag.md",
    )


def test_textbook_rag_md_path_stays_a_sibling_outside_academic_resources():
    book_dir = os.path.join("tmp", "processed_outputs", "Hansen_2022")
    assert textbook_rag_md_path(book_dir) == os.path.join(book_dir, "Hansen_2022.rag.md")


def test_read_subset_marker_returns_parsed_dict(tmp_path):
    (tmp_path / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    assert read_subset_marker(str(tmp_path)) == {"label": "2024"}


def test_read_subset_marker_returns_none_when_missing(tmp_path):
    assert read_subset_marker(str(tmp_path)) is None


def test_read_subset_marker_warns_and_ignores_malformed_json(tmp_path, capsys):
    (tmp_path / ".notes_subset.json").write_text("{not valid json")
    assert read_subset_marker(str(tmp_path)) is None
    assert "WARNING" in capsys.readouterr().out


def test_find_containing_offering_label_returns_none_for_a_notes_rooted_path():
    path = os.path.join("academic_notes", "econometrics", "ta_notes", "foo.pdf")
    assert find_containing_offering_label(path) is None


def test_find_containing_offering_label_finds_a_marker_on_the_course_dir_itself(tmp_path):
    course_dir = tmp_path / "academic_resources" / "econometrics"
    course_dir.mkdir(parents=True)
    (course_dir / ".notes_subset.json").write_text(json.dumps({"label": "whole-course"}))
    pdf_path = course_dir / "class_2024" / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "whole-course"


def test_find_containing_offering_label_finds_a_marker_several_levels_up(tmp_path):
    subset = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    deep = subset / "Class Notes" / "Hand-Written Notes"
    deep.mkdir(parents=True)
    (subset / ".notes_subset.json").write_text(json.dumps({"label": "2024"}))
    pdf_path = deep / "090424.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "2024"


def test_find_containing_offering_label_returns_none_when_no_ancestor_is_marked(tmp_path):
    category_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    category_dir.mkdir(parents=True)
    pdf_path = category_dir / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) is None


def test_find_containing_offering_label_prefers_the_outermost_marker(tmp_path):
    # Mirrors find_subset_roots()'s own "one marker claims its whole
    # subtree, no stacking" rule -- the outer marker is the one that
    # actually governs this file, since find_subset_roots() would never
    # have looked for the inner one.
    outer = tmp_path / "academic_resources" / "econometrics" / "class_2024"
    inner = outer / "Class Notes"
    inner.mkdir(parents=True)
    (outer / ".notes_subset.json").write_text(json.dumps({"label": "outer"}))
    (inner / ".notes_subset.json").write_text(json.dumps({"label": "inner"}))
    pdf_path = inner / "foo.pdf"

    assert find_containing_offering_label(str(pdf_path)) == "outer"
