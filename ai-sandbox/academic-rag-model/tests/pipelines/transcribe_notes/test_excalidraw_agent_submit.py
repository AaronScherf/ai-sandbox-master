import os
import tempfile
import unittest.mock

from core.env.gemini_utils import load_json_cache
from core.indexer.index_card import compute_file_id, compute_id_from_parts
from pipelines.transcribe_notes.agent_work import ManifestEntry, doc_slug_for, load_manifest, save_manifest
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver
from pipelines.transcribe_notes.excalidraw_agent_submit import submit_doc, validate_chunk_card_output
from pipelines.transcribe_notes.transcribe_excalidraw import chunk_cache_paths_for, expansion_cache_paths_for


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


def test_submit_doc_reuses_submitted_chunks_and_segments_with_real_cache_checks(tmp_path):
    notes_dir = tmp_path / "academic_notes" / "econ" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    md_path = notes_dir / "canvas.excalidraw.md"
    img_path = notes_dir / "canvas.excalidraw.svg"
    md_path.write_text("scene", encoding="utf-8")
    img_path.write_text("<svg></svg>", encoding="utf-8")
    doc_slug = doc_slug_for(str(md_path), compute_file_id(str(md_path)))
    doc_dir = tmp_path / ".agent_work" / "run-1" / doc_slug
    doc_dir.mkdir(parents=True)
    (doc_dir / "task-0001.md").write_text(
        "## Agent output\n\n--- CHUNK 0 ---\nchunk zero text\n", encoding="utf-8",
    )
    save_manifest(str(doc_dir), [ManifestEntry("task-0001", "chunks", [0], "pending")])

    with unittest.mock.patch(
        "pipelines.transcribe_notes.transcribe_excalidraw.load_canvas_image", return_value=object(),
    ), unittest.mock.patch(
        "pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=[object()],
    ), unittest.mock.patch(
        "pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", return_value=b"chunk",
    ), unittest.mock.patch(
        "pipelines.transcribe_notes.transcribe_excalidraw.write_outputs",
    ) as mock_write:
        status = submit_doc(
            str(tmp_path), str(tmp_path), "run-1", doc_slug, str(md_path), str(img_path),
            client=object(), model_override="m",
        )
        assert "expansion card staged" in status
        entries = load_manifest(str(doc_dir))
        assert [(e.task_id, e.tier, e.status) for e in entries] == [
            ("task-0001", "chunks", "submitted"),
            ("task-0002", "segments", "pending"),
        ]
        chunk_cache_path, chunk_driver_path = chunk_cache_paths_for(str(md_path))
        assert load_json_cache(chunk_cache_path) == {"0": "chunk zero text"}
        assert load_json_cache(chunk_driver_path) == {"source_hash": compute_file_id(str(img_path))}

        with (doc_dir / "task-0002.md").open("a", encoding="utf-8") as card:
            card.write("--- SEGMENT 0 ---\nexpanded text\n")
        status = submit_doc(
            str(tmp_path), str(tmp_path), "run-1", doc_slug, str(md_path), str(img_path),
            client=object(), model_override="m",
        )

        assert status == "complete"
        exp_cache_path, exp_driver_path = expansion_cache_paths_for(str(md_path))
        assert load_json_cache(exp_cache_path) == {"0": "expanded text"}
        raw_markdown = "<!-- chunk 1 -->\n\nchunk zero text"
        assert load_json_cache(exp_driver_path) == {
            "source_hash": compute_id_from_parts([raw_markdown]),
        }
        mock_write.assert_called_once()


def test_submit_doc_final_write_pass_uses_the_real_client_for_indexing():
    # Final review finding: the final NullDriver re-run must still index the
    # note (reconcile_and_write needs a real client) -- passing client=None
    # there silently leaves every agent-submitted note out of search.
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
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n--- CHUNK 0 ---\nchunk zero text\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="chunks", pages=[0], status="pending")])

        real_client = object()
        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
            return_value=True,
        ) as mock_process:
            submit_doc(hub, hub, "run-1", doc_slug, md_path, img_path, client=real_client, model_override="m")

        final_call = mock_process.call_args_list[-1]
        assert final_call.args[2] is real_client


def test_submit_doc_threads_use_grounding_through_to_process_excalidraw_note():
    # Final review finding: --grounding was silently dropped on the agent
    # collect/submit path even though grounding is retrieval, not generation,
    # and the spec says it should stay active regardless of driver.
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
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write("## Agent output\n\n--- CHUNK 0 ---\nchunk zero text\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="chunks", pages=[0], status="pending")])

        with unittest.mock.patch(
            "pipelines.transcribe_notes.excalidraw_agent_submit.process_excalidraw_note",
            return_value=True,
        ) as mock_process:
            submit_doc(
                hub, hub, "run-1", doc_slug, md_path, img_path, client=object(), model_override="m",
                use_grounding=True,
            )

        for call in mock_process.call_args_list:
            assert call.kwargs["use_grounding"] is True


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
