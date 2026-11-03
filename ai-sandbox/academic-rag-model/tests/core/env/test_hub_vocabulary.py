import json
import logging

from core.env.hub_vocabulary import (
    LEGACY_VOCABULARY,
    default_config_path,
    load_vocabulary,
)

SEED_CATEGORIES = [
    "lecture_notes", "problem_sets", "ta_notes", "professor_notes", "textbooks", "textbooks-and-papers",
    "syllabus", "handwritten_notes", "cheat_sheet", "recitation_slides", "study_plan", "labs", "articles",
    "briefings", "latex", "lecture_slides", "lecture_recordings",
]


def _write(tmp_path, data):
    path = tmp_path / "hub_config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_names_and_matches_case_insensitively(tmp_path):
    path = _write(tmp_path, {"version": 1, "textbook_folders": ["textbooks"], "group_patterns": [r"^part_\d+$"],
                             "names": {"lecture_notes": {"kind": "category", "source": "seed"}}})
    vocab = load_vocabulary(path)
    assert vocab.kind_of("Lecture_Notes") == "category"
    assert vocab.kind_of("unknown") is None
    assert vocab.textbook_folders == ("textbooks",)


def test_missing_file_falls_back_to_legacy_with_one_warning(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        vocab = load_vocabulary(tmp_path / "nope.json")
    assert vocab == LEGACY_VOCABULARY
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_invalid_json_unknown_kind_or_bad_regex_fall_back(tmp_path, caplog):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    cases = [
        bad,
        _write(tmp_path, {"names": {"x": {"kind": "weird", "source": "owner"}}}),
        _write(tmp_path, {"group_patterns": ["("]}),
    ]
    for path in cases:
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            assert load_vocabulary(path) == LEGACY_VOCABULARY
        assert path.name in caplog.text


def test_cache_follows_file_changes(tmp_path):
    path = _write(tmp_path, {"names": {"a": {"kind": "category", "source": "owner"}}})
    assert load_vocabulary(path).kind_of("a") == "category"
    path.write_text(json.dumps({"names": {"a": {"kind": "group", "source": "owner"}}}), encoding="utf-8")
    import os
    os.utime(path, (path.stat().st_atime + 5, path.stat().st_mtime + 5))
    assert load_vocabulary(path).kind_of("a") == "group"


def test_shipped_config_has_the_seed():
    vocab = load_vocabulary(default_config_path())
    for name in SEED_CATEGORIES:
        assert vocab.kind_of(name) == "category", name
    for name in ("processed_outputs", "images", "assets"):
        assert vocab.kind_of(name) == "ignore", name
    for name in ("chapters", "summaries", "previous", "Solutions", "past_exams"):
        assert vocab.kind_of(name) is None, name
    assert vocab.textbook_folders == ("textbooks", "textbooks-and-papers")


# --- Task 3: vocabulary-driven parser -------------------------------------------------------------
import pytest

from core.env.hub_vocabulary import HubPath, Vocabulary, parse_hub_path
from tests.core.env.test_course_part_category_legacy import LEGACY_CASES


def _vocab(**kinds):
    return Vocabulary(names={name.casefold(): kind for name, kind in kinds.items()})


SEEDED = _vocab(lecture_notes="category", problem_sets="category", textbooks="category",
                processed_outputs="ignore", part_1="group", class_2024="group")


@pytest.mark.parametrize(("path", "legacy"), LEGACY_CASES)
def test_every_legacy_case_survives_with_an_empty_vocabulary(path, legacy):
    from core.env.academic_hub_paths import course_part_category
    assert course_part_category(path) == legacy
    parsed = parse_hub_path(path, Vocabulary())
    if legacy is None:
        assert parsed is None
    else:
        assert parsed.source == "legacy"
        assert (parsed.course, parsed.groups[0] if parsed.groups else None, parsed.category) == legacy


def test_nested_layers_above_a_known_category_keep_every_group():
    got = parse_hub_path("academic_notes/econ/2025_fall/part_1/lecture_notes/a.md", SEEDED)
    assert got == HubPath("academic_notes", "econ", ("2025_fall", "part_1"), "lecture_notes", "vocabulary")


def test_group_layer_no_longer_hides_the_category():
    got = parse_hub_path("academic_resources/econ/class_2024/problem_sets/a.pdf", SEEDED)
    assert (got.groups, got.category, got.source) == (("class_2024",), "problem_sets", "vocabulary")


def test_unconfirmed_subfolder_is_skipped_confirmed_one_wins():
    path = "academic_notes/econ/lecture_notes/Problem Sets/a.md"
    assert parse_hub_path(path, SEEDED).category == "lecture_notes"
    confirmed = _vocab(lecture_notes="category", **{"Problem Sets": "category"})
    got = parse_hub_path(path, confirmed)
    assert (got.category, got.groups) == ("Problem Sets", ("lecture_notes",))


def test_textbook_subfolders_resolve_to_textbooks():
    got = parse_hub_path("academic_notes/micro/textbooks/processed_outputs/Book/x.md", SEEDED)
    assert (got.category, got.groups) == ("textbooks", ())


def test_no_known_category_falls_back_to_legacy_result():
    got = parse_hub_path("academic_notes/econ/Unknown/a.md", SEEDED)
    assert (got.category, got.source) == ("Unknown", "legacy")


def test_file_name_is_never_a_folder():
    # a file literally named like a category must not be read as one
    assert parse_hub_path("academic_notes/econ/lecture_notes", SEEDED).source == "legacy"


def test_folder_names_match_case_insensitively():
    got = parse_hub_path("academic_notes/econ/Lecture_Notes/a.md", SEEDED)
    assert got.category == "Lecture_Notes"


# --- Task 4: one source for textbook names and the part/group patterns -----------------------------
from core.env.hub_vocabulary import is_group_name, is_part_name


def test_group_and_part_name_patterns():
    vocab = Vocabulary(group_patterns=(r"^part_\d+$", r"^class_\d{4}$", r"^\d{4}_class$"))
    assert all(is_group_name(n, vocab) for n in ("part_3", "class_2024", "2025_class"))
    assert not is_group_name("lecture_notes", vocab)
    assert is_part_name("part_3", vocab) and not is_part_name("class_2024", vocab)


def test_textbook_folder_follows_the_configured_vocabulary(tmp_path, monkeypatch):
    from core.env.academic_hub_paths import is_textbook_folder, textbook_folder_names
    cfg = _write(tmp_path, {"textbook_folders": ["textbooks", "course_readers"], "names": {}})
    monkeypatch.setenv("ACADEMIC_HUB_CONFIG", str(cfg))
    assert is_textbook_folder("Course_Readers") and "course_readers" in textbook_folder_names()
    assert not is_textbook_folder("textbooks-and-papers")


def test_audio_discovery_honors_a_configured_textbook_folder(tmp_path, monkeypatch):
    from audio_generator.discovery import discover_source_files
    cfg = _write(tmp_path, {"textbook_folders": ["course_readers"], "names": {}})
    monkeypatch.setenv("ACADEMIC_HUB_CONFIG", str(cfg))
    book = tmp_path / "hub" / "academic_resources" / "econ" / "course_readers" / "processed_outputs" / "Book"
    book.mkdir(parents=True)
    (book / "Book.rag.md").write_text("# x", encoding="utf-8")
    notes = tmp_path / "hub" / "academic_notes" / "econ" / "course_readers" / "n.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("# n", encoding="utf-8")
    sources = discover_source_files(str(tmp_path / "hub"), "econ", ["notes"])
    assert all("course_readers" not in s.rel_md_path for s in sources)


# --- Task 7 support: aliases (confirm --alias-of) -------------------------------------------------
def test_alias_returns_the_canonical_category_name(tmp_path):
    path = _write(tmp_path, {"names": {
        "problem_sets": {"kind": "category", "source": "seed"},
        "Problem Sets": {"kind": "category", "source": "owner", "alias_of": "problem_sets"},
    }})
    vocab = load_vocabulary(path)
    got = parse_hub_path("academic_notes/econ/class_2024/Problem Sets/a.md", vocab)
    assert (got.category, got.groups) == ("problem_sets", ("class_2024",))


def test_alias_with_a_non_string_target_is_ignored(tmp_path):
    path = _write(tmp_path, {"names": {"X": {"kind": "category", "source": "owner", "alias_of": 7}}})
    vocab = load_vocabulary(path)
    assert parse_hub_path("academic_notes/econ/X/a.md", vocab).category == "X"
