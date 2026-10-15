import os
import tempfile
import unittest.mock

from core.indexer.index_card import compute_file_id
from pipelines.transcribe_notes.agent_work import ManifestEntry, doc_slug_for, save_manifest
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver
from pipelines.transcribe_notes.excalidraw_agent_submit import submit_doc, validate_chunk_card_output


def test_validate_chunk_card_output_parses_all_chunk_sections():
    raw = "--- CHUNK 0 ---\nFirst chunk text\n--- CHUNK 1 ---\nSecond chunk text\n"
    result = validate_chunk_card_output(raw, expected_indices=[0, 1])
    assert result.pages == {0: "First chunk text", 1: "Second chunk text"}
    assert result.bounce_reason is None


def test_validate_chunk_card_output_bounces_on_missing_chunk():
    raw = "--- CHUNK 0 ---\nFirst chunk text\n"
    result = validate_chunk_card_output(raw, expected_indices=[0, 1])
    assert result.bounce_reason is not None
    assert "1" in result.bounce_reason


def test_submit_doc_writes_chunk_cache_and_advances_to_expansion_stage():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "econ", "lecture_notes")
        os.makedirs(notes_dir)
        md_path = os.path.join(notes_dir, "canvas.excalidraw.md")
        img_path = os.path.join(notes_dir, "canvas.excalidraw.svg")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene")
        with open(img_path, "w", encoding="utf-8") as f:
            f.write("<svg></svg>")

        file_id = compute_file_id(md_path)
        doc_slug = doc_slug_for(md_path, file_id)
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n--- CHUNK 0 ---\nchunk zero text\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="chunks", pages=[0], status="pending")])

        from pipelines.transcribe_notes.agent_driver import AgentPending

        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
            side_effect=AgentPending(),
        ) as mock_process:
            status = submit_doc(hub, hub, "run-1", doc_slug, md_path, img_path, client=object(), model_override="m")

        assert "incomplete" in status  # expansion stage still pending after chunks finish
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert kwargs["collect_mode"] is True


def test_submit_doc_allow_api_fallback_finishes_via_the_api():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "econ", "lecture_notes")
        os.makedirs(notes_dir)
        md_path = os.path.join(notes_dir, "canvas.excalidraw.md")
        img_path = os.path.join(notes_dir, "canvas.excalidraw.svg")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene")
        with open(img_path, "w", encoding="utf-8") as f:
            f.write("<svg></svg>")

        doc_slug = doc_slug_for(md_path, compute_file_id(md_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        save_manifest(doc_dir, [ManifestEntry(task_id="task-0001", tier="chunks", pages=[0], status="pending")])
        with open(os.path.join(doc_dir, "task-0001.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n")  # never filled

        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
        ) as mock_process:
            status = submit_doc(
                hub, hub, "run-1", doc_slug, md_path, img_path, client=object(), model_override="m",
                allow_api_fallback=True,
            )
        assert "api fallback" in status
        mock_process.assert_called_once()
        _, kwargs = mock_process.call_args
        assert isinstance(kwargs["driver"], ExcalidrawApiDriver)
