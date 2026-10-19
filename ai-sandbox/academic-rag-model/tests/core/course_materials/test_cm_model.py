import pytest

from core.course_materials.model import AUTHORITY, ROLES, Catalog, CatalogError, Material, normalize, rag_twin

N = "academic_notes/econometrics"


def test_every_role_has_an_authority_group():
    assert set(AUTHORITY) == set(ROLES)
    assert Material(path="x", role="recitation").authority == Material(path="x", role="instructor").authority == "class"
    assert Material(path="x", role="student_notes").authority == "student"
    assert Material(path="x", role="textbook").authority == "reference"


def test_normalize_maps_either_root_to_a_hub_relative_notes_path():
    assert normalize("C:/hub/academic_notes/econometrics/syllabus/a.md") == f"{N}/syllabus/a.md"
    assert normalize("academic_resources/econometrics/textbooks/x.md") == f"{N}/textbooks/x.md"
    assert normalize("C:/somewhere/else/a.md") is None
    assert normalize("") is None


def test_rag_twin_swaps_both_ways():
    assert rag_twin("a/X.excalidraw.md") == "a/X.excalidraw.rag.md"
    assert rag_twin("a/X.excalidraw.rag.md") == "a/X.excalidraw.md"


def test_stem_drops_rag_and_md_suffixes():
    assert Material(path=f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.rag.md").stem == "E 2026-09-09.excalidraw"
    assert Material(path=f"{N}/professor_notes/processed_outputs/092126.md").stem == "092126"
    assert Material(path="").stem == ""


def catalog():
    return Catalog(course="econometrics", materials=[
        Material(path=f"{N}/professor_notes/processed_outputs/slides2.md", role="instructor", format="slides", order=[1_000_000, "", "slides2"]),
        Material(path=f"{N}/professor_notes/processed_outputs/slides1.md", role="instructor", format="slides", order=[1_000_000, "", "slides1"]),
        Material(path=f"{N}/class_2024/Slides/processed_outputs/1.Intro.md", role="instructor", format="slides", offering="2024"),
        Material(path=f"{N}/textbooks/processed_outputs/Hansen_2022/chapters/01_intro.rag.md", role="textbook", format="chapter", book="hansen"),
        Material(path=f"{N}/textbooks/processed_outputs/Hansen_2022/chapters/02_ols.rag.md", role="textbook", format="chapter", book="hansen"),
        Material(path=f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.rag.md", role="student_notes", format="excalidraw", flagged=False),
        Material(path=f"{N}/mixed/a.md", role="recitation"),
        Material(path=f"{N}/mixed/b.md", role="problem_set"),
    ])


def test_lookup_exact_twin_and_misses():
    c = catalog()
    assert c.lookup(f"C:/hub/{N}/professor_notes/processed_outputs/slides1.md").stem == "slides1"
    assert c.lookup(f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.md").role == "student_notes"
    assert c.lookup("C:/elsewhere/a.md") is None
    assert c.lookup(f"{N}/nowhere/x.md") is None
    assert f"{N}/nowhere/x.md" in c.misses and "C:/elsewhere/a.md" not in c.misses


def test_lookup_accepts_backslashes_and_resources_root():
    c = catalog()
    win = "C:\\hub\\academic_notes\\econometrics\\lecture_notes\\processed_outputs\\E 2026-09-09.excalidraw.rag.md"
    assert c.lookup(win).role == "student_notes"
    assert c.lookup("academic_resources/econometrics/professor_notes/processed_outputs/slides2.md").stem == "slides2"


def test_lookup_falls_back_to_the_nearest_ancestor_only_when_it_is_uniform():
    c = catalog()
    front = c.lookup(f"{N}/textbooks/processed_outputs/Hansen_2022/Hansen_2022.rag.md")
    assert front is not None and front.book == "hansen"
    assert c.lookup(f"{N}/mixed/c.md") is None


def test_by_role_filters_offering_and_sorts_by_order():
    c = catalog()
    assert [m.stem for m in c.by_role("instructor")] == ["slides1", "slides2"]
    assert [m.stem for m in c.by_role("instructor", offering="2024")] == ["1.Intro"]
    assert c.offerings() == ["2024"] and c.book_keys() == ["hansen"]
    assert {m.role for m in c.flagged()} == {"instructor", "textbook", "recitation", "problem_set"}


def test_json_round_trip_and_bad_data():
    c = catalog()
    again = Catalog.from_json(c.to_json())
    assert [m.path for m in again.materials] == [m.path for m in c.materials]
    assert "misses" not in c.to_json()
    with pytest.raises(CatalogError, match="catalog"):
        Catalog.from_json({"materials": []})
    with pytest.raises(CatalogError):
        Catalog.from_json({"course": "x", "materials": [{"nope": 1}]})
