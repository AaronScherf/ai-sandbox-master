"""One-time local migration of stored Markdown content hashes.

Cards written under an older hash scheme store the raw-bytes (legacy) hash,
or the location-insensitive hash with the file's line endings preserved. This
rewrites a card's stored hash (and its chunk records' hash, which must equal
the card's or the chunks look stale and get re-embedded) to the current
line-ending-insensitive hash when, and only when, the file is unchanged since
the card was written, i.e. the stored value is one the file legitimately
carries under an accepted scheme and line-ending form
(`index_card.accepted_content_hashes`). Rewriting is optional: matching already
accepts the older forms; it just retires the compatibility path.

No network, no model client. Default is a dry run:

    python -m tools.rehash_content_hashes --hub-root PATH [--apply]

Spec: docs/superpowers/plans/academic_hub/2026-11-03-hub-path-resilience-p1-stable-hashes.md (Task 4).
"""
from __future__ import annotations

import argparse
import os

from core.env.corpus_write_lock import corpus_write_lock
from core.indexer.chunk_index import load_chunks, save_chunks
from core.indexer.index_card import (
    compute_content_hash,
    content_hash_matches,
    list_courses,
    load_shard,
    save_shard,
)


def plan(hub_root: str) -> dict:
    result: dict = {"rewrite": [], "unchanged": 0, "stale": [], "missing": []}
    for course in list_courses(hub_root):
        for card in load_shard(hub_root, course):
            stored = card.get("content_hash")
            path = card.get("path") or ""
            if not stored or not path.endswith(".md"):
                continue
            absolute = os.path.join(hub_root, *path.split("/"))
            if not os.path.isfile(absolute):
                result["missing"].append(path)
                continue
            new = compute_content_hash(absolute)
            if stored == new:
                result["unchanged"] += 1
            elif content_hash_matches(absolute, stored):
                result["rewrite"].append({"course": course, "file_id": card["file_id"],
                                          "path": path, "old": stored, "new": new})
            else:
                result["stale"].append({"file_id": card["file_id"], "path": path})
    return result


def apply(hub_root: str) -> dict:
    result = plan(hub_root)
    by_course: dict[str, list[dict]] = {}
    for row in result["rewrite"]:
        by_course.setdefault(row["course"], []).append(row)
    applied = 0
    for course, rows in by_course.items():
        new_by_id = {row["file_id"]: row["new"] for row in rows}
        old_by_id = {row["file_id"]: row["old"] for row in rows}
        # Chunks first: a run interrupted before the cards are saved leaves
        # chunks on the new hash and cards on the old, which a rerun heals
        # (the chunk step accepts either hash).
        chunks = load_chunks(hub_root, course)
        changed_chunks = False
        for chunk in chunks:
            file_id = chunk.get("file_id")
            if file_id in new_by_id and chunk.get("content_hash") == old_by_id[file_id]:
                chunk["content_hash"] = new_by_id[file_id]
                changed_chunks = True
        if changed_chunks:
            save_chunks(hub_root, course, chunks)
        cards = load_shard(hub_root, course)
        for card in cards:
            if card.get("file_id") in new_by_id and card.get("content_hash") == old_by_id[card["file_id"]]:
                card["content_hash"] = new_by_id[card["file_id"]]
                applied += 1
        save_shard(hub_root, course, cards)
    result["applied"] = applied
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite stored Markdown content hashes to the location-insensitive scheme (no API calls).")
    parser.add_argument("--hub-root", required=True)
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args()
    if args.apply:
        with corpus_write_lock([args.hub_root], "rehash content hashes"):
            summary = apply(args.hub_root)
    else:
        summary = plan(args.hub_root)
    print({key: (len(value) if isinstance(value, list) else value) for key, value in summary.items()})
    for row in summary.get("stale", []):
        print("stale (left unchanged):", row["path"])


if __name__ == "__main__":
    main()
