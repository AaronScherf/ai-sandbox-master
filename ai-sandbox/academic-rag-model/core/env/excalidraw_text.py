"""
excalidraw_text.py
The one definition of the text conventions the Excalidraw notes pipeline,
the subset linker, and the question resolver all parse: the `[Question]`
tag (open, or already rewritten into a resolved marker) and the
`**[Slide]**` / `**[Handwritten]**` block labels of a slide-aware raw
transcript. No network, no filesystem.
"""
from __future__ import annotations

import re

QUESTION_TAG = "[Question]"
# Matches an open tag and a resolved marker such as
# "[Question: answered -> <sidecar>#<qid>]" (see core.indexer.questions).
QUESTION_TAG_RE = re.compile(r"\[Question(?::[^\]]*)?\]")

SEGMENT_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)


def split_labeled_segments(raw_markdown: str) -> list[tuple[str, str]]:
    """Splits a slide-aware raw transcript into ordered (label, text) blocks,
    label being 'Slide' or 'Handwritten'. Chunk markers are dropped (a block
    can straddle a chunk boundary; they are transcription bookkeeping, not
    content). Text before the first label is treated as handwriting -- the
    safe default, since handwriting is the part that gets rewritten and the
    fallback on any failure is to keep it verbatim."""
    text = CHUNK_MARKER_RE.sub("", raw_markdown)
    matches = list(SEGMENT_LABEL_RE.finditer(text))
    pieces: list[tuple[str, str]] = []
    first_start = matches[0].start() if matches else len(text)
    if text[:first_start].strip():
        pieces.append(("Handwritten", text[:first_start].strip()))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            pieces.append((m.group(1), body))
    return pieces
