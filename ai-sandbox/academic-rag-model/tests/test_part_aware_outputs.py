from pathlib import Path

import pytest

from core.env.academic_hub_paths import course_output_dir
from agent.study_guide.draft import output_path
from agent.study_guide.cli import plan_path_for, review_path_for
from agent.study_guide.revise.run import report_path
from agent.rag.report_builder import summary_path
from audio_generator.discovery import discover_source_files
from pipelines.generate_video_notes.note_indexing import write_group_note


def test_course_output_dir_layouts(tmp_path):
    notes = tmp_path / "academic_notes"
    (notes / "legacy").mkdir(parents=True)
    assert course_output_dir(tmp_path, "legacy", "summaries") == notes / "legacy" / "summaries"
    (notes / "modern" / "part_1").mkdir(parents=True)
    assert course_output_dir(tmp_path, "modern", "summaries") == notes / "modern" / "part_1" / "summaries"
    (notes / "modern" / "part_2").mkdir()
    assert course_output_dir(tmp_path, "modern", "summaries", "part_2") == notes / "modern" / "part_2" / "summaries"
    with pytest.raises(ValueError, match="--part"):
        course_output_dir(tmp_path, "modern", "summaries")


def test_writer_paths_follow_part_layout(tmp_path):
    from types import SimpleNamespace
    for course, suffix in (("legacy", Path("legacy")), ("modern", Path("modern/part_1"))):
        (tmp_path / "academic_notes" / suffix).mkdir(parents=True)
        spec = SimpleNamespace(course=course, part=None, id="example")
        assert plan_path_for(str(tmp_path), spec).parent == tmp_path / "academic_notes" / suffix / "guide_plans"
        assert review_path_for(str(tmp_path), spec).parent == tmp_path / "academic_notes" / suffix / "guide_plans"
        assert report_path(str(tmp_path), spec, "guide.md", "").parent == tmp_path / "academic_notes" / suffix / "guide_plans"
        assert summary_path("Question", str(tmp_path), course) == str(tmp_path / "academic_notes" / suffix / "summaries" / "question.md")
        assert output_path(str(tmp_path), spec).parent == tmp_path / "academic_notes" / suffix / "summaries"
        rel_md, _ = write_group_note(str(tmp_path), course, "sample", "text", {})
        assert Path(rel_md).parent.as_posix() == (Path("academic_notes") / suffix / "lecture_notes").as_posix()


def test_audio_discovers_part_notes_and_textbook(tmp_path):
    notes = tmp_path / "academic_notes" / "modern" / "part_1" / "lecture_notes" / "processed_outputs"
    notes.mkdir(parents=True)
    (notes / "note.md").write_text("hello")
    book = tmp_path / "academic_resources" / "modern" / "part_1" / "textbooks" / "processed_outputs" / "Book"
    book.mkdir(parents=True)
    (book / "Book.md").write_text("hello")
    found = discover_source_files(str(tmp_path), "modern", ["notes", "textbook"])
    assert {Path(item.abs_md_path).name for item in found} == {"note.md", "Book.md"}
