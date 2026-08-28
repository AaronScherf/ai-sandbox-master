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

from gemini_utils import call_with_retries
from google.genai import types

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


def recompute_course_entry(academic_hub_root: str, course: str) -> None:
    """Free byproduct of writing any card in this course -- no LLM or
    embedding call (spec §3.2). Excludes orphaned and not-yet-embedded
    (needs_indexing) cards from the centroid so a failed/pending card
    can't skew course-level ranking."""
    cards = [c for c in load_shard(academic_hub_root, course) if not c.get("orphaned")]
    courses = load_courses(academic_hub_root)

    if not cards:
        courses.pop(course, None)
        save_courses(academic_hub_root, courses)
        return

    embeddings = [c["embedding"] for c in cards if c.get("embedding")]
    centroid = np.array(embeddings, dtype=float).mean(axis=0).tolist() if embeddings else []

    topic_counts: Counter[str] = Counter()
    for c in cards:
        topic_counts.update(c.get("topics") or [])
    predominant = [topic for topic, _ in topic_counts.most_common(10)]

    courses[course] = {
        "course": course,
        "title": course.replace("-", " ").title(),
        "predominant_topics": predominant,
        "file_count": len(cards),
        "embedding": centroid,
    }
    save_courses(academic_hub_root, courses)


_PROMPT_TEMPLATE = """You are cataloging one document from a personal study corpus for a search index.

The document's containing folder is categorized as '{folder_category}', but classify based on \
the actual content below, not the folder name alone -- e.g. a file that is actually an exam \
should be classified "exam" even if it lives in a folder named for practice problem sets.

Respond with ONLY a JSON object with exactly these keys:
"title" (string, the document's own title or a short descriptive name),
"doc_type" (one of: "textbook", "problem_set", "exam", "ta_notes", "handwritten_notes"),
"summary" (2-3 sentences describing what this document covers),
"level" (one of: "introductory", "intermediate", "advanced"),
"has_solutions" (boolean -- true only if THIS document itself shows worked solutions/answers, \
not just problem statements).

--- DOCUMENT START ---
{content_sample}
--- DOCUMENT END ---"""


def generate_index_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str, page_count: int, client,
) -> dict:
    """One structured-JSON generation call plus one embedding call. Never
    proposes `topics` -- that's the corpus-wide retag pass's job (spec §5),
    kept deliberately out of scope for a single-document call."""
    prompt = _PROMPT_TEMPLATE.format(folder_category=folder_category, content_sample=content_sample)
    response = call_with_retries(lambda: client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0,
            "thinking_config": {"thinking_level": "minimal"},
        },
    ))
    parsed = json.loads(response.text)

    title = str(parsed.get("title") or "").strip()
    doc_type = parsed.get("doc_type")
    if doc_type not in KNOWN_DOC_TYPES:
        doc_type = folder_category
    summary = str(parsed.get("summary") or "").strip()
    level = parsed.get("level")
    if level not in KNOWN_LEVELS:
        level = "introductory"
    has_solutions = bool(parsed.get("has_solutions", False))

    embed_response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{title}\n\n{summary}",
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    embedding = list(embed_response.embeddings[0].values)

    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "course": course,
        "doc_type": doc_type,
        "title": title,
        "summary": summary,
        "topics": [],
        "level": level,
        "has_solutions": has_solutions,
        "page_count": page_count,
        "rag_md_path": None,
        "embedding": embedding,
        "embedding_model": EMBEDDING_MODEL_ID,
        "source_updated_at": now_iso(),
        "needs_indexing": False,
    }


def make_failure_card(file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str) -> dict:
    """Written when generate_index_card() raises -- keeps file_id/path so
    §4.3 reconciliation can find and complete this exact card on a later
    rebuild, rather than mistaking it for a new file each time."""
    return {
        "file_id": file_id,
        "path": path,
        "source_pdf_path": source_pdf_path,
        "course": course,
        "doc_type": folder_category,
        "title": "",
        "summary": "",
        "topics": [],
        "level": None,
        "has_solutions": None,
        "page_count": None,
        "rag_md_path": None,
        "embedding": [],
        "embedding_model": None,
        "source_updated_at": now_iso(),
        "needs_indexing": True,
    }


def find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None:
    index_dir = _index_dir(academic_hub_root)
    if not os.path.isdir(index_dir):
        return None
    for name in sorted(os.listdir(index_dir)):
        if not name.endswith(".json") or name in ("courses.json", "topics.json"):
            continue
        course = name[:-len(".json")]
        for card in load_shard(academic_hub_root, course):
            if card.get("file_id") == file_id:
                return course, card
    return None


def _replace_card(cards: list[dict], file_id: str, updated: dict) -> list[dict]:
    return [updated if c.get("file_id") == file_id else c for c in cards]


def reconcile_and_write(
    academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str,
    folder_category: str, content_sample: str, page_count: int, client,
) -> dict:
    """The single entry point both pipeline hooks (and rebuild) call.
    Implements spec §4.3: never treats `path` as identity -- reconciles by
    `file_id` across every shard before ever generating anything new."""
    found = find_card_by_file_id(academic_hub_root, file_id)

    if found is not None:
        old_course, old_card = found
        changed = (
            old_card.get("path") != path
            or old_card.get("source_pdf_path") != source_pdf_path
            or old_card.get("orphaned")
        )
        updated = dict(old_card)
        updated["path"] = path
        updated["source_pdf_path"] = source_pdf_path
        updated["course"] = course
        updated.pop("orphaned", None)
        if changed:
            updated["source_updated_at"] = now_iso()

        if old_course == course:
            if changed:
                save_shard(academic_hub_root, course, _replace_card(
                    load_shard(academic_hub_root, course), file_id, updated,
                ))
                recompute_course_entry(academic_hub_root, course)
            return updated

        # Moved to a different course.
        remaining = [c for c in load_shard(academic_hub_root, old_course) if c.get("file_id") != file_id]
        save_shard(academic_hub_root, old_course, remaining)
        new_course_cards = load_shard(academic_hub_root, course)
        new_course_cards.append(updated)
        save_shard(academic_hub_root, course, new_course_cards)
        recompute_course_entry(academic_hub_root, old_course)
        recompute_course_entry(academic_hub_root, course)
        return updated

    # No match anywhere -- genuinely new content (spec §4.3).
    try:
        card = generate_index_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path, course=course,
            folder_category=folder_category, content_sample=content_sample,
            page_count=page_count, client=client,
        )
    except Exception as err:
        print(f"WARNING: index card generation failed for {path} ({err}); writing needs_indexing card.")
        card = make_failure_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path,
            course=course, folder_category=folder_category,
        )

    cards = load_shard(academic_hub_root, course)
    cards.append(card)
    save_shard(academic_hub_root, course, cards)
    recompute_course_entry(academic_hub_root, course)
    return card


def set_rag_md_path(academic_hub_root: str, file_id: str, rag_md_path: str) -> bool:
    """Called by describe_images.py's hook (Task 10) once it produces
    .rag.md -- finds the existing card by file_id (reusing
    find_card_by_file_id rather than duplicating the shard scan) and sets
    rag_md_path on it, without touching anything else on the card (no
    regeneration). Returns False (never raises) if no card exists yet for
    this file_id -- the caller logs that as a warning, same failure-
    isolation philosophy as everywhere else in this module."""
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    course, card = found
    updated = dict(card)
    updated["rag_md_path"] = rag_md_path
    save_shard(academic_hub_root, course, _replace_card(
        load_shard(academic_hub_root, course), file_id, updated,
    ))
    return True
