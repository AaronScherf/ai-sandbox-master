# pipelines/transcribe_notes/excalidraw_agent_driver.py
"""
Driver seam for transcribe_excalidraw.py's two Gemini call sites: per-chunk
vision transcription and per-segment text expansion. Mirrors agent_driver.py's
ApiDriver/AgentDriver/NullDriver split for PDFs, in its own module since the
call shapes differ (a chunk's image bytes are already available -- no page-
rendering step -- and expansion operates on already-split text segments, not
raw page images) and because this module needs prompt-building helpers that
live in transcribe_excalidraw.py (importing agent_driver.py directly would
need the reverse, which transcribe_notes.py's process_pdf already avoids via
a local import -- see that function). See docs/superpowers/specs/
transcribe_notes/2026-10-15-excalidraw-agent-driver-design.md.
"""
from __future__ import annotations

from typing import Protocol

from core.env.gemini_utils import call_with_retries
from core.env.ollama_utils import call_ollama
from pipelines.transcribe_notes.agent_driver import NullDriverFired
from pipelines.transcribe_notes.transcribe_notes import transcribe_page_via_gemini

_EXPANSION_MODEL_GEMINI = "gemini-3.1-flash-lite"
_EXPANSION_MODEL_OLLAMA = "qwen2.5:7b-instruct"


class ExcalidrawDriver(Protocol):
    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str: ...

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str: ...


class ExcalidrawApiDriver:
    """Default driver: reproduces transcribe_excalidraw.py's existing direct
    Gemini/Ollama calls unchanged, chunk calls through call_with_retries
    (matching the retry the plain sequential loop already applied)."""

    def __init__(self, client, backend: str = "gemini"):
        self.client = client
        self.backend = backend

    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str:
        def transcribe_nonempty() -> str:
            text = transcribe_page_via_gemini(self.client, model, image_bytes, prompt)
            if not text or not text.strip():
                raise ValueError("empty chunk transcription")
            return text

        return call_with_retries(transcribe_nonempty)

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str:
        if self.backend == "ollama":
            result = call_ollama(prompt, model=_EXPANSION_MODEL_OLLAMA, request_timeout=300)
            if isinstance(result, str):
                return result
            print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
            self.backend = "gemini"
        response = self.client.models.generate_content(
            model=_EXPANSION_MODEL_GEMINI, contents=[prompt],
            config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
        )
        return response.text or ""


class ExcalidrawNullDriver:
    """Used once every chunk/segment is already cached: a live call here is
    a cache-completeness bug, not a real gap -- raise rather than silently
    making a real (possibly paid) call."""

    def transcribe_chunk(
        self, excalidraw_md_path: str, model: str, chunk_index: int, total_chunks: int,
        prompt: str, image_bytes: bytes,
    ) -> str:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected live call for chunk {chunk_index} in "
            f"{excalidraw_md_path} -- the cache should already be complete at this point."
        )

    def expand(
        self, excalidraw_md_path: str, prompt: str, segment_index: int, total_segments: int,
    ) -> str:
        raise NullDriverFired(
            f"ExcalidrawNullDriver: unexpected live call for segment {segment_index} in "
            f"{excalidraw_md_path} -- the cache should already be complete at this point."
        )
