"""
store.py
Read/write for the extracted problem corpus at
<academic_hub_root>/.problem_corpus/<course>.json -- mirrors
indexer/chunk_index.py's .index/chunks/<course>.json convention exactly
(spec: docs/superpowers/specs/2026-09-06-problem-corpus-extraction-design.md
Section 5).
"""
from __future__ import annotations

import json
import os


def corpus_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".problem_corpus")


def corpus_path(academic_hub_root: str, course: str) -> str:
    return os.path.join(corpus_dir(academic_hub_root), f"{course}.json")


def load_records(academic_hub_root: str, course: str) -> list[dict]:
    path = corpus_path(academic_hub_root, course)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_file_records(academic_hub_root: str, course: str, file_id: str, records: list[dict]) -> None:
    """Atomically replaces every existing record for this file_id with
    `records` (upsert-by-file_id, not upsert-by-record-id) -- loads the
    course's full record list, drops anything already tagged with this
    file_id, appends the new set, writes the whole file back. One file's
    re-extraction never touches another file's already-stored records."""
    existing = load_records(academic_hub_root, course)
    remaining = [r for r in existing if r["source"]["file_id"] != file_id]
    path = corpus_path(academic_hub_root, course)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(remaining + records, f, indent=2, ensure_ascii=False)
