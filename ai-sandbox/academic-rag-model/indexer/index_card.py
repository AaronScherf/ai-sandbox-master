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

from common.gemini_utils import call_with_retries
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONALITY = 768
EMBEDDING_MODEL_ID = f"{EMBEDDING_MODEL}:{EMBEDDING_DIMENSIONALITY}"
GENERATION_MODEL = "gemini-3.1-flash-lite"

KNOWN_DOC_TYPES = frozenset({"textbook", "problem_set", "ta_notes", "handwritten_notes"})
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


def compute_content_hash(md_path: str) -> str:
    """Truncated SHA-256 of the .md file's own bytes -- the staleness
    signal (spec §4.3), immune to anything that touches a file's mtime
    without changing its content (a container/session remount, a sync
    tool, a backup restore -- confirmed live: a real rebuild once
    reported 14 spuriously "updated" cards after something reset every
    .md's mtime to the same instant, none of which had actually
    changed). Reads the file directly rather than reusing
    `content_sample` -- the textbook loop truncates that sample to
    TEXTBOOK_CONTENT_SAMPLE_CHARS for the LLM prompt, which would miss a
    real change past that point."""
    with open(md_path, "rb") as f:
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


def list_courses(academic_hub_root: str) -> list[str]:
    index_dir = _index_dir(academic_hub_root)
    if not os.path.isdir(index_dir):
        return []
    return [
        name[:-len(".json")]
        for name in sorted(os.listdir(index_dir))
        if name.endswith(".json") and name not in ("courses.json", "tags.json")
    ]


def tags_path(academic_hub_root: str) -> str:
    return os.path.join(_index_dir(academic_hub_root), "tags.json")


def load_tags(academic_hub_root: str) -> list[dict]:
    path = tags_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tags(academic_hub_root: str, tags: list[dict]) -> None:
    path = tags_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tags, f, indent=2, ensure_ascii=False)


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

    tag_counts: Counter[str] = Counter()
    for c in cards:
        tag_counts.update(c.get("tags") or [])
    predominant = [tag for tag, _ in tag_counts.most_common(10)]

    courses[course] = {
        "course": course,
        "title": course.replace("-", " ").title(),
        "predominant_tags": predominant,
        "file_count": len(cards),
        "embedding": centroid,
    }
    save_courses(academic_hub_root, courses)


_PROMPT_TEMPLATE = """You are cataloging one document from a personal study corpus for a search index.

The document's containing folder is categorized as '{folder_category}', but classify based on \
the actual content below, not the folder name alone.

Respond with ONLY a JSON object with exactly these keys:
"title" (string, the document's own title or a short descriptive name),
"doc_type" (one of: {doc_type_options}),
"summary" (2-3 sentences describing what this document covers),
"level" (one of: "introductory", "intermediate", "advanced"),
"has_solutions" (boolean -- true only if THIS document itself shows worked solutions/answers, \
not just problem statements).

--- DOCUMENT START ---
{content_sample}
--- DOCUMENT END ---"""


def generate_index_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_sample: str, page_count: int, client, content_hash: str | None = None,
    known_doc_types: frozenset[str] = KNOWN_DOC_TYPES,
) -> dict:
    """One structured-JSON generation call plus one embedding call. Never
    proposes `tags` -- that's the corpus-wide retag pass's job (spec §5),
    kept deliberately out of scope for a single-document call.

    known_doc_types defaults to the academic-hub vocabulary
    (KNOWN_DOC_TYPES) but is a plain parameter, not a hardcoded
    constant -- a different corpus (e.g. essays/convert_essays.py's
    personal-essay corpus) passes its own set so the LLM isn't forced
    to squeeze non-academic content into an academic-hub-shaped bucket
    (confirmed live: every essay in a first real run got force-fit into
    "textbook" or "handwritten_notes", neither of which is remotely
    correct -- the four-value enum was baked into the prompt string
    itself, not just the post-hoc validation)."""
    doc_type_options = ", ".join(f'"{t}"' for t in sorted(known_doc_types))
    prompt = _PROMPT_TEMPLATE.format(
        folder_category=folder_category, content_sample=content_sample, doc_type_options=doc_type_options,
    )
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
    if isinstance(parsed, list):
        # Confirmed live: despite response_mime_type="application/json"
        # and prompt instructions asking for a bare object,
        # gemini-3.1-flash-lite sometimes wraps an otherwise
        # well-formed response in a one-element array (reproduced
        # against LN_Linear Algebra.md). Unwrap rather than crash --
        # every field below already falls back gracefully if the
        # unwrapped value isn't a dict either.
        parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {}

    title = str(parsed.get("title") or "").strip()
    doc_type = parsed.get("doc_type")
    if doc_type not in known_doc_types:
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
        "tags": [],
        "level": level,
        "has_solutions": has_solutions,
        "page_count": page_count,
        "rag_md_path": None,
        "embedding": embedding,
        "embedding_model": EMBEDDING_MODEL_ID,
        "source_updated_at": now_iso(),
        "content_hash": content_hash,
        "needs_indexing": False,
    }


def make_failure_card(
    file_id: str, path: str, source_pdf_path: str, course: str, folder_category: str,
    content_hash: str | None = None,
) -> dict:
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
        "tags": [],
        "level": None,
        "has_solutions": None,
        "page_count": None,
        "rag_md_path": None,
        "embedding": [],
        "embedding_model": None,
        "source_updated_at": now_iso(),
        "content_hash": content_hash,
        "needs_indexing": True,
    }


def find_card_by_file_id(academic_hub_root: str, file_id: str) -> tuple[str, dict] | None:
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("file_id") == file_id:
                return course, card
    return None


def _replace_card(cards: list[dict], file_id: str, updated: dict) -> list[dict]:
    return [updated if c.get("file_id") == file_id else c for c in cards]


def move_card(academic_hub_root: str, file_id: str, new_course: str) -> bool:
    """Moves a card between course shards when a paper's folder gets
    corrected (audit_metadata.py's folder check). Updates the card's own
    course/path/source_pdf_path fields to match its new location, and
    recomputes both the old and new course's rollup entry in
    courses.json so centroid/predominant_tags stay correct on both
    sides. A no-op (still True) when the card is already in new_course."""
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    old_course, card = found
    if old_course == new_course:
        return True

    old_cards = [c for c in load_shard(academic_hub_root, old_course) if c["file_id"] != file_id]
    save_shard(academic_hub_root, old_course, old_cards)
    recompute_course_entry(academic_hub_root, old_course)

    card = dict(card)
    card["course"] = new_course
    if card.get("path"):
        card["path"] = card["path"].replace(f"{old_course}/", f"{new_course}/", 1)
    if card.get("source_pdf_path"):
        card["source_pdf_path"] = card["source_pdf_path"].replace(f"{old_course}/", f"{new_course}/", 1)

    new_cards = load_shard(academic_hub_root, new_course)
    new_cards.append(card)
    save_shard(academic_hub_root, new_course, new_cards)
    recompute_course_entry(academic_hub_root, new_course)
    return True


def reconcile_and_write(
    academic_hub_root: str, file_id: str, path: str, source_pdf_path: str, course: str,
    folder_category: str, content_sample: str, page_count: int, client,
    content_hash: str | None = None, known_doc_types: frozenset[str] = KNOWN_DOC_TYPES,
) -> dict:
    """The single entry point both pipeline hooks (and rebuild) call.
    Implements spec §4.3: never treats `path` as identity -- reconciles by
    `file_id` across every shard before ever generating anything new.
    known_doc_types is forwarded to generate_index_card() only on the
    genuinely-new-content path below -- reconciling an existing card
    never re-derives doc_type, so it's a no-op there."""
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
        updated["content_hash"] = content_hash
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
            page_count=page_count, client=client, content_hash=content_hash,
            known_doc_types=known_doc_types,
        )
    except Exception as err:
        print(f"WARNING: index card generation failed for {path} ({err}); writing needs_indexing card.")
        card = make_failure_card(
            file_id=file_id, path=path, source_pdf_path=source_pdf_path,
            course=course, folder_category=folder_category, content_hash=content_hash,
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
