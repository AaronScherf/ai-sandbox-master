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
