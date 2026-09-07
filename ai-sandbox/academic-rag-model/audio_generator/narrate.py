"""
narrate.py
Chunked, holistic LaTeX-to-narration rewrite via a local LLM, running
before cleaner.py on the raw .md (spec §3.1). Deliberately has zero
dependency on cleaner.py in either direction: a chunk this module can't
successfully rewrite is returned unmodified, and cleaner.py's existing
(unchanged) regex wrap catches whatever raw LaTeX survives downstream.
"""
from __future__ import annotations

import os
import re

from common.ollama_utils import call_ollama

AUDIOGEN_NARRATE_OLLAMA_MODEL = os.environ.get("AUDIOGEN_NARRATE_OLLAMA_MODEL", "qwen2-math:7b")
AUDIOGEN_NARRATE_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("AUDIOGEN_NARRATE_OLLAMA_TIMEOUT", "300"))

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
_CHUNK_TARGET_SIZE = 2500
_MIN_LENGTH_RATIO = 0.5

_PROMPT_TEMPLATE = """Rewrite this passage as natural spoken prose for audio narration. \
Describe mathematical notation in words rather than symbols. Do not omit or summarize any \
content -- rewrite every sentence, changing only how notation is expressed.

--- PASSAGE START ---
{chunk}
--- PASSAGE END ---"""


def _split_into_pieces(md_text: str) -> list[str]:
    """Splits on paragraph boundaries, treating a fenced code block as one
    atomic piece regardless of blank lines inside it (spec §3.1)."""
    pieces = []
    pos = 0
    for match in _CODE_BLOCK_PATTERN.finditer(md_text):
        before = md_text[pos:match.start()]
        pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(before) if p.strip())
        pieces.append(match.group())
        pos = match.end()
    pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(md_text[pos:]) if p.strip())
    return pieces


def _group_into_chunks(pieces: list[str]) -> list[str]:
    """Groups paragraph pieces into ~_CHUNK_TARGET_SIZE-character chunks.
    A code-block piece is never merged with anything else -- it always
    becomes its own chunk (spec §3.1)."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for piece in pieces:
        if _CODE_BLOCK_PATTERN.fullmatch(piece):
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(piece)
            continue
        if current and current_len + len(piece) > _CHUNK_TARGET_SIZE:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(piece)
        current_len += len(piece)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _passes_sanity_check(original: str, rewritten) -> bool:
    """Cheap proxy for 'did the model drop/summarize content' (spec §3.1,
    §9 -- exact ratio flagged as needing real tuning, not a validated
    constant)."""
    if not isinstance(rewritten, str) or not rewritten.strip():
        return False
    return len(rewritten) >= _MIN_LENGTH_RATIO * len(original)


def _narrate_chunk(chunk: str) -> str:
    """Rewrites one chunk via the local LLM. Never raises; returns the
    chunk's original, unmodified text on any failure that survives a
    retry (spec §3.1) -- this module never invents its own fallback text."""
    prompt = _PROMPT_TEMPLATE.format(chunk=chunk)
    for _ in range(2):
        result = call_ollama(prompt, AUDIOGEN_NARRATE_OLLAMA_MODEL, AUDIOGEN_NARRATE_OLLAMA_TIMEOUT_SECONDS)
        if result is None:
            return chunk  # server unreachable -- not worth retrying
        if isinstance(result, str) and _passes_sanity_check(chunk, result):
            return result
        # OLLAMA_TIMEOUT, or a real response that failed the sanity check -- retry once
    return chunk


def narrate_for_speech(md_text: str) -> str:
    """Entry point pipeline.py calls first, on raw .md text, before
    cleaner.clean_markdown_for_speech() (spec §3.1)."""
    chunks = _group_into_chunks(_split_into_pieces(md_text))
    narrated = [
        chunk if _CODE_BLOCK_PATTERN.fullmatch(chunk) else _narrate_chunk(chunk)
        for chunk in chunks
    ]
    return "\n\n".join(narrated)
