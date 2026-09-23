import os

from notes.migrate_sources_to_resources import find_migration_candidates, migrate_one


def test_find_migration_candidates_finds_an_unmigrated_pdf(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path))

    assert len(candidates) == 1
    current, target = candidates[0]
    assert current == str(pdf_path)
    assert target == str(tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf")


def test_find_migration_candidates_finds_an_unmigrated_excalidraw_image(tmp_path):
    lecture_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    lecture_dir.mkdir(parents=True)
    (lecture_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    svg_path = lecture_dir / "Drawing.excalidraw.svg"
    svg_path.write_text("<svg></svg>")

    candidates = find_migration_candidates(str(tmp_path))

    assert len(candidates) == 1
    current, target = candidates[0]
    assert current == str(svg_path)
    assert target == str(tmp_path / "academic_resources" / "econometrics" / "lecture_notes" / "Drawing.excalidraw.svg")


def test_find_migration_candidates_finds_docx_and_pptx(tmp_path):
    # 2026-09-21 addendum: docx/pptx are in scope too, purely mechanical --
    # no downstream code reads them, so this is the only thing that needs
    # to know about them.
    study_dir = tmp_path / "academic_notes" / "math-camp" / "study_plan"
    study_dir.mkdir(parents=True)
    (study_dir / "Prep Schedule.docx").write_bytes(b"x")
    (study_dir / "Overview.pptx").write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path))

    names = sorted(os.path.basename(c) for c, _t in candidates)
    assert names == ["Overview.pptx", "Prep Schedule.docx"]


def test_find_migration_candidates_skips_a_pdf_already_migrated(tmp_path):
    (tmp_path / "academic_notes" / "econometrics" / "ta_notes").mkdir(parents=True)
    resources_dir = tmp_path / "academic_resources" / "econometrics" / "ta_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "foo.pdf").write_bytes(b"x")

    assert find_migration_candidates(str(tmp_path)) == []


def test_find_migration_candidates_respects_course_filter(tmp_path):
    for course in ("econometrics", "microecon"):
        d = tmp_path / "academic_notes" / course / "ta_notes"
        d.mkdir(parents=True)
        (d / "foo.pdf").write_bytes(b"x")

    candidates = find_migration_candidates(str(tmp_path), course="econometrics")

    assert len(candidates) == 1
    assert "econometrics" in candidates[0][0]


def test_migrate_one_moves_the_file_and_creates_target_dirs(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"real bytes")
    target = tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf"

    migrate_one(str(pdf_path), str(target))

    assert not pdf_path.exists()
    assert target.read_bytes() == b"real bytes"


def test_migrate_one_dry_run_does_not_touch_the_filesystem(tmp_path):
    ta_dir = tmp_path / "academic_notes" / "econometrics" / "ta_notes"
    ta_dir.mkdir(parents=True)
    pdf_path = ta_dir / "foo.pdf"
    pdf_path.write_bytes(b"real bytes")
    target = tmp_path / "academic_resources" / "econometrics" / "ta_notes" / "foo.pdf"

    migrate_one(str(pdf_path), str(target), dry_run=True)

    assert pdf_path.exists()
    assert not target.exists()
