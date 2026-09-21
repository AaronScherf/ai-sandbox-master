import os

import pytest

from common.academic_hub_paths import resolve_output_dir, to_notes_root, to_resources_root


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
