import os
import tempfile

import pytest

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import load_manifest
from agent.rag.resolve_questions_agent_work import QuestionResolverAgentDriver


def test_stage_key_terms_writes_one_card_covering_every_missing_question():
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("scene content for file_id hashing")

        driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_key_terms(
                raw_path, missing=[("q1-abc", "key-term prompt for q1"), ("q2-def", "key-term prompt for q2")],
            )
        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        entries = load_manifest(doc_dir)
        assert len(entries) == 1
        assert entries[0].pages == ["q1-abc", "q2-def"]
        assert entries[0].status == "pending"
        assert entries[0].tier == "keyterms"


def test_recollecting_a_still_pending_keyterms_card_does_not_duplicate_it():
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("scene content")

        driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            driver.stage_key_terms(raw_path, missing=[("q1-abc", "prompt")])

        second_driver = QuestionResolverAgentDriver(hub, "run-1")
        with pytest.raises(AgentPending):
            second_driver.stage_key_terms(raw_path, missing=[("q1-abc", "prompt")])

        doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
        assert len(load_manifest(doc_dir)) == 1
