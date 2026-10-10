# pipelines/transcribe_notes/agent_driver.py
"""
Driver seam for transcribe_notes.py's two Gemini call sites (a repair/
whole-document batch, and a tier-3 single page). ApiDriver reproduces
today's behavior unchanged; AgentDriver (pipelines/transcribe_notes/
agent_work.py) and NullDriver are the other two implementations. See
docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from pipelines.transcribe_notes.transcribe_notes import (
    repair_batch,
    transcribe_page_via_gemini,
)


class AgentPending(Exception):
    """Raised by AgentDriver to signal a batch/page has no result yet --
    a task card was written instead. Must be caught with its own
    `except AgentPending` clause BEFORE any generic `except Exception` at
    the call site: it must never be retried and must never trigger the
    per-page fallback a real API failure triggers."""


class TranscriptionDriver(Protocol):
    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        ...

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        ...


class ApiDriver:
    """Default driver: reproduces process_pdf's existing direct Gemini
    calls unchanged, still through call_with_retries."""

    def __init__(self, client):
        self.client = client

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        return call_with_retries(lambda: repair_batch(self.client, model, pdf_path, batch, prompt))

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        return call_with_retries(lambda: transcribe_page_via_gemini(self.client, model, image_bytes, prompt))


class NullDriverFired(RuntimeError):
    """Raised by NullDriver when it's called at all -- a cache-
    completeness bug, since every page/batch should have hit
    process_pdf's own cache-check branches first. Caught explicitly
    (ahead of `except Exception`) at process_pdf's three call sites so
    it propagates as a hard error instead of falling through to the
    real per-page fallback with a real (possibly paid) client -- final
    review finding I2."""


class NullDriver:
    """Used by submit's re-run of process_pdf once every page is already
    cached: every page/batch should hit process_pdf's own cache-check
    branches and never reach the driver at all. If one does, that is a
    cache-completeness bug -- raise a hard error instead of silently
    falling through to a paid API call."""

    def transcribe_batch(self, pdf_path: str, model: str, batch: list[int], prompt: str) -> dict[int, str]:
        raise NullDriverFired(
            f"NullDriver: unexpected live call for batch {batch} in {pdf_path} -- "
            "the cache should already be complete at this point."
        )

    def transcribe_page(
        self, pdf_path: str, model: str, page_num: int, prompt: str, image_bytes: bytes, total_pages: int,
    ) -> str:
        raise NullDriverFired(
            f"NullDriver: unexpected live call for page {page_num} in {pdf_path} -- "
            "the cache should already be complete at this point."
        )
