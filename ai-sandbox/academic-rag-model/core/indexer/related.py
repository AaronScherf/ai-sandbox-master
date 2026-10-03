"""
related.py
Links a handwriting-only Excalidraw lecture note (the "subset") to its
"with slides" counterpart (the "superset") on the subset's index card, so
default search can return just the superset. Detection: same course and
folder, same YYYY-MM-DD in the filename, the superset's raw transcript
flagged embedded_slides: true and the subset's not -- then confirmed by
word-3-gram containment of the subset's handwriting inside the superset's
[Handwritten] blocks (whole-card embeddings were measured and cannot
separate true pairs from different lectures on the same topic).

Spec: docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md
"""
from __future__ import annotations

import os
import re

from core.env.frontmatter import parse_frontmatter

CONTAINMENT_THRESHOLD = 0.3
_NGRAM = 3

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
_CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[A-Za-z]{3,}|\\[A-Za-z]+")
_RAG_SUFFIX = ".excalidraw.rag.md"


def raw_transcript_path(card_path: str) -> str | None:
    if not card_path.endswith(_RAG_SUFFIX):
        return None
    return card_path[: -len(_RAG_SUFFIX)] + ".excalidraw.md"


def lecture_date(card_path: str) -> str | None:
    match = _DATE_RE.search(os.path.basename(card_path))
    return match.group(0) if match else None


def read_raw(academic_hub_root: str, card: dict) -> tuple[dict, str] | None:
    rel = raw_transcript_path(card.get("path", ""))
    if rel is None:
        return None
    full = os.path.join(academic_hub_root, *rel.split("/"))
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8") as f:
        return parse_frontmatter(f.read())


def handwriting_text(meta: dict, body: str) -> str:
    text = _CHUNK_MARKER_RE.sub("", body)
    if meta.get("embedded_slides", "").strip().lower() != "true":
        return text
    parts = _LABEL_RE.split(text)  # [pre, label, body, label, body, ...]
    return "\n".join(parts[i + 1] for i in range(1, len(parts) - 1, 2) if parts[i] == "Handwritten")


def _ngrams(text: str) -> set[tuple[str, ...]]:
    words = _TOKEN_RE.findall(text.lower())
    return {tuple(words[i : i + _NGRAM]) for i in range(len(words) - _NGRAM + 1)}


def containment(subset_text: str, superset_text: str) -> float:
    sub = _ngrams(subset_text)
    if not sub:
        return 0.0
    return len(sub & _ngrams(superset_text)) / len(sub)
