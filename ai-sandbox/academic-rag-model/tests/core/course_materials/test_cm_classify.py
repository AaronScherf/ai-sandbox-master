import json
import os

import pytest
from cm_helpers import LANDSCAPE, PORTRAIT, make_pdf, write

from core.course_materials import (Catalog, CatalogError, classify_course, classify_path, date_from_stem, load_catalog,
                                   record_decision)
from core.course_materials.classify import catalog_path, decisions_path

COURSE = "demo"
N = f"academic_notes/{COURSE}"


def build_course(tmp_path, with_pdfs=True):
    """A course whose folder names follow no convention: the classifier must lean on content, PDFs and layout."""
    hub = tmp_path / "hub"
    notes, res = hub / "academic_notes" / COURSE, hub / "academic_resources" / COURSE

    def converted(rel, body, pdf_rel=None, shape=None, extra=""):
        fm = f"---\nsource_pdf: academic_resources/{COURSE}/{pdf_rel}\n{extra}---\n\n" if pdf_rel else ""
        if pdf_rel and with_pdfs:
            make_pdf(res / pdf_rel, *shape)
        return write(notes / rel, fm + body)

    converted("misc/processed_outputs/week1.md", "# Intro\n\nDefinition 1 A thing\n", "misc/week1.pdf", LANDSCAPE)
    converted("stuff/processed_outputs/week3.md", "Problem 1\n(a) x\n\nProblem 2\n(b) y\n", "stuff/week3.pdf", PORTRAIT)
    converted("professor_notes/processed_outputs/092126.md",
              "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1\n(1) iid\n", "professor_notes/092126.pdf", PORTRAIT)
    scene = "---\n\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n\n---\n==Switch to EXCALIDRAW VIEW==\n"
    write(notes / "notes" / "Demo 2026-09-09 10.00.00.excalidraw.md", scene)
    exc = "---\nsource_excalidraw: Demo 2026-09-09 10.00.00.excalidraw.md\n---\n\n"
    write(notes / "notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.md", exc + "chunk\n")
    write(notes / "notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.rag.md", exc + "### Expanded\n")
    write(notes / "reading/processed_outputs/Greene_Econometric_Analysis_2018/chapters/01_intro.rag.md", "# Intro\n")
    write(notes / "reading/processed_outputs/Greene_Econometric_Analysis_2018/chapters/02_ols.rag.md", "# OLS\n")
    converted("class_2023/deck/processed_outputs/1.Intro.md", "# Intro\n", "class_2023/deck/1.Intro.pdf", LANDSCAPE)
    write(res / "class_2023" / ".notes_subset.json", json.dumps({"label": "2023"}))
    write(notes / "summaries/guide.md", "# A generated study guide\n")
    return hub


def by_stem(catalog):
    return {m.stem: m for m in catalog.materials}


def test_classifies_a_course_with_unconventional_names(tmp_path):
    cat = by_stem(classify_course(build_course(tmp_path), COURSE))
    assert (cat["week1"].role, cat["week1"].format, cat["week1"].flagged) == ("instructor", "slides", True)  # orientation only
    assert cat["week3"].role == "problem_set"
    assert (cat["092126"].role, cat["092126"].format, cat["092126"].date) == ("instructor", "handwritten", "2026-09-21")
    assert cat["092126"].flagged
    assert (cat["01_intro"].role, cat["01_intro"].book) == ("textbook", "greene")
    assert cat["1.Intro"].offering == "2023" and cat["1.Intro"].role == "instructor"
    assert "week1" in cat and cat["week1"].offering is None


def test_one_record_per_source_preferring_rag_and_raw_scenes_and_generated_dirs_skipped(tmp_path):
    paths = [m.path for m in classify_course(build_course(tmp_path), COURSE).materials]
    excal = [p for p in paths if "Demo 2026-09-09" in p]
    assert excal == [f"{N}/notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.rag.md"]
    assert not any("summaries" in p for p in paths)


def test_the_catalog_is_written_and_reloaded(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    assert catalog_path(hub, COURSE).is_file()
    again = load_catalog(hub, COURSE, refresh="never")
    assert isinstance(again, Catalog) and len(again.materials) == 7


def test_decisions_win_survive_reclassification_and_can_exclude(tmp_path):
    hub = build_course(tmp_path)
    record_decision(hub, COURSE, f"{N}/stuff/processed_outputs/week3.md", role="exam")
    record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", exclude=True)
    cat = by_stem(classify_course(hub, COURSE))
    assert (cat["week3"].role, cat["week3"].flagged, cat["week3"].decided_by) == ("exam", False, "review")
    assert "week1" not in cat
    assert json.loads(decisions_path(hub, COURSE).read_text(encoding="utf-8"))[f"{N}/stuff/processed_outputs/week3.md"] == {"role": "exam"}


def test_a_folder_decision_applies_to_everything_under_it(tmp_path):
    hub = build_course(tmp_path)
    key = record_decision(hub, COURSE, f"{N}/reading/processed_outputs/Greene_Econometric_Analysis_2018", book="greene-ea")
    assert key.endswith("/")
    cat = by_stem(classify_course(hub, COURSE))
    assert cat["01_intro"].book == cat["02_ols"].book == "greene-ea"


def test_decisions_for_missing_files_are_reported_and_kept(tmp_path):
    hub = build_course(tmp_path)
    record_decision(hub, COURSE, f"{N}/gone/old.md", role="exam")
    assert classify_course(hub, COURSE).unknown_decisions == [f"{N}/gone/old.md"]
    assert f"{N}/gone/old.md" in json.loads(decisions_path(hub, COURSE).read_text(encoding="utf-8"))


def test_bad_decisions_are_refused(tmp_path):
    hub = build_course(tmp_path)
    with pytest.raises(ValueError):
        record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", role="lecturer")
    with pytest.raises(ValueError):
        record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", colour="blue")
    with pytest.raises(CatalogError):
        record_decision(hub, COURSE, "C:/not/in/the/hub.md", role="exam")


def test_load_catalog_rebuilds_when_a_file_or_the_decisions_change(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    built = catalog_path(hub, COURSE).stat().st_mtime
    new = write(hub / N / "misc/processed_outputs/week2.md", "# More\n")
    os.utime(new, (built + 10, built + 10))
    assert "week2" in by_stem(load_catalog(hub, COURSE))
    assert "week2" in by_stem(load_catalog(hub, COURSE, refresh="never"))


def test_corrupt_catalog_and_decisions_raise_naming_the_file(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    catalog_path(hub, COURSE).write_text("{not json", encoding="utf-8")
    with pytest.raises(CatalogError, match=r"demo\.json"):
        load_catalog(hub, COURSE, refresh="never")
    decisions_path(hub, COURSE).write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(CatalogError, match="decisions"):
        classify_course(hub, COURSE)


def test_missing_source_pdfs_abstain_without_crashing(tmp_path):
    cat = by_stem(classify_course(build_course(tmp_path, with_pdfs=False), COURSE))
    assert any(e[0] == "pdf unavailable" for e in cat["week1"].evidence)
    assert cat["week1"].flagged


def test_crlf_frontmatter_is_read(tmp_path):
    hub = tmp_path / "hub"
    text = "---\r\nsource_excalidraw: a.excalidraw.md\r\n---\r\n\r\nbody\r\n"
    (hub / N / "x").mkdir(parents=True)
    (hub / N / "x" / "a.md").write_bytes(text.encode("utf-8"))
    assert classify_course(hub, COURSE).materials[0].role == "student_notes"


def test_index_cards_vote_and_a_corrupt_card_file_only_loses_that_signal(tmp_path):
    hub = build_course(tmp_path)
    write(hub / N / "loose/processed_outputs/n1.md", "plain text\n")
    cards = [{"path": f"academic_resources/{COURSE}/loose/processed_outputs/n1.md", "doc_type": "ta_notes"}]
    write(hub / ".index" / f"{COURSE}.json", json.dumps(cards))
    n1 = by_stem(classify_course(hub, COURSE))["n1"]
    assert n1.authority == "class" and n1.flagged is False  # the card vouches for class material, not for its author


def test_a_corrupt_index_card_file_only_loses_that_signal(tmp_path):
    hub = build_course(tmp_path)
    write(hub / ".index" / f"{COURSE}.json", "{broken")
    assert by_stem(classify_course(hub, COURSE))["week1"].role == "instructor"


def test_a_missing_course_folder_gives_an_empty_catalog_and_writes_nothing(tmp_path):
    cat = classify_course(tmp_path / "hub", "nope")
    assert cat.materials == [] and not (tmp_path / "hub" / ".index").exists()


def test_classify_path_needs_no_files():
    m = classify_path("C:/hub/academic_notes/microecon/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md")
    assert (m.role, m.book) == ("textbook", "press")
    assert classify_path("").role == "other"


def test_dates_from_iso_and_mmddyy_stems():
    assert date_from_stem("Econometrics 2026-09-09 10.11.39.excalidraw") == "2026-09-09"
    assert date_from_stem("092126") == "2026-09-21"
    assert date_from_stem("133126") is None and date_from_stem("slides1") is None
