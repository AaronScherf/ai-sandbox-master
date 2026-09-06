"""
note_indexing.py
Writes a synthesized group note (+ sidecar) to
academic_notes/<course>/lecture-notes/ and registers it with the
existing Source Indexer, the same way notes/transcribe_notes.py calls
reconcile_and_write() inline right after writing its own output. Spec
§6.
"""
from __future__ import annotations

import json
import os

from indexer.index_card import LECTURE_NOTE_DOC_TYPES, compute_content_hash, compute_id_from_parts, reconcile_and_write


def write_group_note(academic_hub_root: str, course: str, slug: str, markdown: str, sidecar: dict) -> tuple[str, str]:
    """Writes the note + its `.meta.json` sidecar, returns their paths
    relative to academic_hub_root (what reconcile_and_write expects)."""
    lecture_notes_dir = os.path.join(academic_hub_root, "academic_notes", course, "lecture-notes")
    os.makedirs(lecture_notes_dir, exist_ok=True)

    md_path = os.path.join(lecture_notes_dir, f"{slug}.md")
    meta_path = os.path.join(lecture_notes_dir, f"{slug}.meta.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, ensure_ascii=False)

    rel_md_path = os.path.relpath(md_path, academic_hub_root).replace(os.sep, "/")
    rel_meta_path = os.path.relpath(meta_path, academic_hub_root).replace(os.sep, "/")
    return rel_md_path, rel_meta_path


def index_group_note(
    academic_hub_root: str, course: str, member_video_ids: list, rel_md_path: str,
    rel_meta_path: str, client,
) -> dict:
    """Registers the note with the shared Source Indexer. file_id is
    derived from the group's member video IDs (its stable identity),
    not the Markdown content (the mutable, re-synthesizable artifact) --
    the same "hash the immutable source" idea compute_file_id already
    applies to a textbook's PDF bytes. content_hash is read back from
    the just-written file (not hashed from the in-memory `markdown`
    string) to avoid a mismatch with what a later rebuild() pass would
    independently recompute from disk (e.g. newline translation on a
    text-mode write)."""
    md_path = os.path.join(academic_hub_root, rel_md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        content_sample = f.read()
    file_id = compute_id_from_parts(member_video_ids)
    content_hash = compute_content_hash(md_path)
    return reconcile_and_write(
        academic_hub_root, file_id=file_id, path=rel_md_path, source_pdf_path=rel_meta_path,
        course=course, folder_category="lecture-notes", content_sample=content_sample,
        page_count=None, client=client, content_hash=content_hash,
        known_doc_types=LECTURE_NOTE_DOC_TYPES,
    )
