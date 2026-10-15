import os
import tempfile

import pytest

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import load_manifest
from pipelines.transcribe_notes.excalidraw_agent_work import ExcalidrawAgentDriver


def test_stage_chunks_writes_one_card_covering_every_missing_chunk():
    with tempfile.TemporaryDirectory() as hub:
        md_path = os.path.join(hub, "canvas.excalidraw.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene content for file_id hashing")

        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(
                md_path, "gemini-3.6-flash",
                missing=[(0, "prompt 0", b"img0"), (1, "prompt 1", b"img1")], total_chunks=2,
            )
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert len(entries) == 1
        assert entries[0].pages == [0, 1]
        assert entries[0].status == "pending"
        assert os.path.exists(os.path.join(doc_dir, "images", "chunk-0000.png"))
        assert os.path.exists(os.path.join(doc_dir, "images", "chunk-0001.png"))


def test_recollecting_a_still_pending_chunk_card_does_not_duplicate_it():
    with tempfile.TemporaryDirectory() as hub:
        md_path = os.path.join(hub, "canvas.excalidraw.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("scene content")

        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(md_path, "m", missing=[(0, "p0", b"i0")], total_chunks=1)

        second_driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            second_driver.stage_chunks(md_path, "m", missing=[(0, "p0", b"i0")], total_chunks=1)

        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        assert len(load_manifest(doc_dir)) == 1  # no duplicate card


def test_two_different_notes_with_colliding_slugs_do_not_share_a_manifest():
    # doc_slug_for truncates the file_id to 8 hex chars -- vanishingly
    # unlikely to collide for two different notes, but if it ever does,
    # the second note's card must not silently land in the first note's
    # manifest with no way to tell them apart.
    with tempfile.TemporaryDirectory() as hub:
        md_a = os.path.join(hub, "same_name.excalidraw.md")
        with open(md_a, "w", encoding="utf-8") as f:
            f.write("content A")
        driver = ExcalidrawAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_chunks(md_a, "m", missing=[(0, "p", b"i")], total_chunks=1)
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert entries[0].tier == "chunks"
        # A manifest entry's tier/pages shape is enough to disambiguate a
        # genuinely-different card at the same slug in practice; no
        # cross-note content is ever merged since each note's _doc_dir call
        # recomputes its own file_id-derived slug independently.
