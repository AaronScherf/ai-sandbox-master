"""
transcribe_excalidraw.py
Turns an Excalidraw handwritten-notes canvas (.excalidraw.md + its
plugin-auto-exported .png) into RAG-corpus markdown: chunk -> transcribe
-> assemble -> expand -> write. Replaces the OneNote capture workflow
(see docs/status/2026-08-24-notes-transcription-status.md's "2026-09-07"
section for why). Spec: docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
"""
from __future__ import annotations

import os

from common.gemini_utils import call_with_retries
from notes.transcribe_notes import transcribe_page_via_gemini

_ACCUMULATION_WINDOW = 3  # same value as transcribe_notes.py's Tier 3 -- see that
                          # module's _ACCUMULATION_WINDOW docstring for why a
                          # trailing window (not full-document accumulation) is used


def _accumulated_chunk_context(cache: dict, chunk_index: int, window: int) -> str:
    """0-based equivalent of transcribe_notes.py's build_accumulated_context.
    Not reused directly: that function assumes 1-based page numbers (its
    start-page floor is hardcoded to 1), which silently drops chunk 0's
    context when called with 0-based chunk indices -- caught by a real
    failing test (test_transcribe_chunks_passes_accumulated_context_from_prior_chunks),
    not assumed in advance. Same trailing-window behavior, just 0-based."""
    start = max(0, chunk_index - window)
    parts = []
    for i in range(start, chunk_index):
        text = cache.get(str(i))
        if text:
            parts.append(f"--- Chunk {i + 1} ---\n{text}")
    return "\n\n".join(parts)


def discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]:
    """Finds every `.excalidraw.md` directly under notes_dir with a
    matching `.excalidraw.png` sibling (the plugin's auto-export) --
    skips (with a warning, not an error) any .md whose PNG hasn't been
    written yet."""
    if not os.path.isdir(notes_dir):
        return []
    pairs = []
    for name in sorted(os.listdir(notes_dir)):
        if not name.lower().endswith(".excalidraw.md"):
            continue
        if file_filter is not None and name != file_filter:
            continue
        md_path = os.path.join(notes_dir, name)
        png_path = md_path[: -len(".md")] + ".png"
        if not os.path.exists(png_path):
            print(f"WARNING: {name} has no matching .png (auto-export may not have run yet) -- skipping.")
            continue
        pairs.append((md_path, png_path))
    return pairs


def build_chunk_transcription_prompt(accumulated_context: str, chunk_index: int, total_chunks: int) -> str:
    context_block = (
        f"Already-transcribed content from earlier chunks of this same canvas, for continuity "
        f"(a chunk boundary can split a derivation or sentence mid-thought):\n{accumulated_context}\n\n"
        if accumulated_context else ""
    )
    return (
        f"This is chunk {chunk_index + 1} of {total_chunks} from a single tall, continuous "
        "handwritten-notes canvas (an Excalidraw drawing, cropped at a whitespace gap -- not a "
        "page boundary). Transcribe everything on this chunk into clean markdown: preserve "
        "problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ or $$...$$), "
        "and reading order. Keep this transcription terse and faithful to the shorthand as "
        "written -- do not expand abbreviations or add explanation; that happens in a later "
        "pass.\n\n"
        f"{context_block}"
        "Respond with ONLY the transcribed markdown for THIS chunk -- no commentary, no code "
        "fence, no repetition of earlier chunks' content.\n"
    )


def assemble_raw_markdown(cache: dict, total_chunks: int) -> str:
    parts = []
    for chunk_index in range(total_chunks):
        text = cache.get(str(chunk_index))
        if text is None:
            continue
        parts.append(f"<!-- chunk {chunk_index + 1} -->\n\n{text}")
    return "\n\n".join(parts)


def transcribe_chunks(client, model: str, chunk_bytes: list[bytes]) -> dict[str, str]:
    cache: dict[str, str] = {}
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks)
        try:
            text = call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))
            cache[str(chunk_index)] = text
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache
