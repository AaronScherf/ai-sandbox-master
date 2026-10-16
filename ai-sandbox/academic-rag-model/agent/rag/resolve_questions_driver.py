# agent/rag/resolve_questions_driver.py
"""
Driver seam for resolve_questions.py's two Gemini call sites: key-term
extraction and answer generation. Mirrors excalidraw_agent_driver.py's
ApiDriver/AgentDriver/NullDriver split, in its own module for the same
reason: it needs prompt-building helpers that live in resolve_questions.py,
and resolve_questions.py needs this module's driver classes, so one of the
two imports must be lazy/local to avoid a cycle (resolve_questions.py's is).
See docs/superpowers/specs/agent/rag/
2026-10-16-question-resolver-agent-driver-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from core.indexer.index_card import GENERATION_MODEL
from pipelines.transcribe_notes.agent_driver import NullDriverFired

_ANSWER_MODEL = "gemini-3.6-flash"  # matches resolve_questions.RESOLVER_MODEL


class QuestionResolverDriver(Protocol):
    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str: ...

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str: ...

    def stage_key_terms(
        self, note_key: str, missing: list[tuple[str, str]],
    ) -> dict[str, str]: ...

    def stage_answers(
        self, note_key: str, missing: list[tuple[str, str]],
    ) -> dict[str, str]: ...


class QuestionResolverApiDriver:
    """Default driver: reproduces resolve_questions.py's existing direct
    Gemini calls unchanged."""

    def __init__(self, client):
        self.client = client

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        response = call_with_retries(lambda: self.client.models.generate_content(
            model=GENERATION_MODEL, contents=prompt,
            config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
        ))
        return (response.text or "").strip()

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        response = call_with_retries(lambda: self.client.models.generate_content(
            model=_ANSWER_MODEL, contents=prompt, config={"temperature": 0.2},
        ))
        return (response.text or "").strip()

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        return {qid: self.extract_key_terms(note_key, qid, prompt) for qid, prompt in missing}

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        return {qid: self.generate_answer(note_key, qid, prompt) for qid, prompt in missing}


class QuestionResolverNullDriver:
    """Used once every question's key terms/answer are already cached: a
    live call here is a cache-completeness bug, not a real gap."""

    def extract_key_terms(self, note_key: str, qid: str, prompt: str) -> str:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected live call for {qid} in "
            f"{note_key} -- the cache should already be complete at this point."
        )

    def generate_answer(self, note_key: str, qid: str, prompt: str) -> str:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected live call for {qid} in "
            f"{note_key} -- the cache should already be complete at this point."
        )

    def stage_key_terms(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected stage_key_terms call for {note_key} -- "
            "the cache should already be complete at this point."
        )

    def stage_answers(self, note_key: str, missing: list[tuple[str, str]]) -> dict[str, str]:
        raise NullDriverFired(
            f"QuestionResolverNullDriver: unexpected stage_answers call for {note_key} -- "
            "the cache should already be complete at this point."
        )
