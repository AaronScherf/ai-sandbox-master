from datetime import date

from pipelines.transcribe_notes.framed_explainer.course_context import (
    build_course_context, scene_date)


def _vault(tmp_path):
    part = tmp_path / "academic_notes" / "econometrics" / "part_2"
    (part / "lecture_notes").mkdir(parents=True)
    for name in ("Econometrics 2026-11-04 LIML2.excalidraw.md",
                 "Econometrics 2026-11-09 next.excalidraw.md",
                 "Econometrics 2026-10-01 old.excalidraw.md"):
        (part / "lecture_notes" / name).write_text("x", encoding="utf-8")
    return part, str(part / "lecture_notes" / "Econometrics 2026-11-04 LIML2.excalidraw.md")


def _note(part, name, text):
    d = part / "professor_notes" / "processed_outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_scene_date_parses_filename():
    assert scene_date("a/Econometrics 2026-11-04 LIML2.excalidraw.md") == date(2026, 11, 4)
    assert scene_date("a/no date here.excalidraw.md") is None


def test_missing_syllabus_degrades_to_profile(tmp_path):
    part, scene = _vault(tmp_path)
    ctx = build_course_context(scene, str(tmp_path))
    assert "econometrics" in ctx.text and "part_2" in ctx.text
    assert ctx.truncated is False


def test_window_selects_neighbour_notes_only(tmp_path):
    part, scene = _vault(tmp_path)
    ctx = build_course_context(scene, str(tmp_path), window_days=7)
    neighbours = ctx.text.split("Neighbouring scenes", 1)[-1]
    assert "2026-11-09" in neighbours
    assert "2026-10-01" not in neighbours
    assert "LIML2" not in neighbours  # the scene itself is excluded


def test_cap_truncates_and_flags(tmp_path):
    part, scene = _vault(tmp_path)
    _note(part, "GMM.md", "\n".join(f"## Heading number {i} about moments" for i in range(400)))
    _note(part, "IV.md", "\n".join(f"## Another heading {i} about instruments" for i in range(400)))
    ctx = build_course_context(scene, str(tmp_path), max_tokens=60)
    assert len(ctx.text) / 4 <= 60
    assert ctx.truncated is True


def test_version_changes_when_source_changes(tmp_path):
    part, scene = _vault(tmp_path)
    _note(part, "GMM.md", "# GMM\n## Moments\n")
    v1 = build_course_context(scene, str(tmp_path)).version
    _note(part, "GMM.md", "# GMM\n## Moments\n## Weighting\n")
    assert build_course_context(scene, str(tmp_path)).version != v1


def test_every_line_has_source_path(tmp_path):
    part, scene = _vault(tmp_path)
    _note(part, "GMM.md", "# GMM\n## Moments\n")
    ctx = build_course_context(scene, str(tmp_path))
    body = [ln for ln in ctx.text.splitlines() if ln.strip()]
    assert body and all(ln.startswith("- [") and "]" in ln for ln in body)
    assert any("GMM.md" in s for s in ctx.sources)


def test_no_date_in_filename_still_builds(tmp_path):
    part, _ = _vault(tmp_path)
    undated = part / "lecture_notes" / "Scratch.excalidraw.md"
    undated.write_text("x", encoding="utf-8")
    ctx = build_course_context(str(undated), str(tmp_path))
    assert "econometrics" in ctx.text
