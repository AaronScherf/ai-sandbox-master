"""
index_card.py
Per-file index card generation, file_id-based reconciliation, and shard
I/O for the academic-hub source indexer. Deliberately has no dependency
on marker/torch/surya (like chapter_index.py) so it stays testable off
the GCP VM -- convert_textbook.py imports those at module scope, which
requires CUDA to even succeed.

Spec: docs/superpowers/specs/2026-08-27-source-indexer-design.md
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone

import numpy as np

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONALITY = 768
EMBEDDING_MODEL_ID = f"{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONALITY}"
GENERATION_MODEL = "gemini-3.1-flash-lite"

KNOWN_DOC_TYPES = {"textbook", "problem_set", "exam", "ta_notes", "handwritten_notes"}
KNOWN_LEVELS = ("introductory", "intermediate", "advanced")

# Cap on how much of an assembled textbook markdown gets read as
# content_sample -- a book's front matter/TOC is reliably near the start
# regardless of the book's total length (spec §4), and this same constant
# is reused by both the live convert_textbook.py hook (Task 9) and
# rebuild's textbook-backfill path (Task 5) so they stay consistent.
TEXTBOOK_CONTENT_SAMPLE_CHARS = 12000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_file_id(pdf_path: str) -> str:
    """Truncated SHA-256 of the PDF's own bytes -- a card's true identity,
    independent of where the file currently lives (spec §3.1/§4.3)."""
    with open(pdf_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return digest[:16]


def derive_course(relative_path: str) -> str:
    """The course segment of a path relative to academic-hub/, e.g.
    'academic_notes/math-camp/ta_notes/foo.pdf' -> 'math-camp'. Distinct
    from folder_category (the immediate parent folder, e.g. 'ta_notes') --
    course is one segment further up."""
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        raise ValueError(f"cannot derive course from path: {relative_path!r}")
    return parts[1]


def _index_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index")


def shard_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), f"{course}.json")


def courses_path(academic_hub_root: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), "courses.json")


def load_shard(academic_hub_root: str, course: str) -> list[dict]:
    path = shard_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_shard(academic_hub_root: str, course: str, cards: list[dict]) -> None:
    path = shard_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)


def load_courses(academic_hub_root: str) -> dict[str, dict]:
    path = courses_path(academic_hub_root)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return {entry["course"]: entry for entry in entries}


def save_courses(academic_hub_root: str, courses: dict[str, dict]) -> None:
    path = courses_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(list(courses.values()), f, indent=2, ensure_ascii=False)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Gemini's embedding API does not return unit-normalized vectors
    (confirmed live: a real call returned L2 norm ~0.59, not 1.0) --
    this always normalizes itself rather than assuming unit length."""
    if not a or not b:
        return 0.0
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    denom = float(np.linalg.norm(arr_a) * np.linalg.norm(arr_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / denom)
