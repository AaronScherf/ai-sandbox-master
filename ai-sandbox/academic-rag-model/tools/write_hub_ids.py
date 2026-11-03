"""Stamp a stable `hub_id` into every authored note under <hub-root>/academic_notes/.

    python -m tools.write_hub_ids --hub-root PATH [--apply] [--include-excalidraw-json]

Dry run by default. `--apply` writes the id into each note's frontmatter
(`.md`, including `.excalidraw.md`) and sets `hub_id` on the matching index
card (matched by `path`), leaving `content_hash` untouched (the id line is
hash-neutral). Plain `.excalidraw` JSON files are skipped unless
`--include-excalidraw-json` is given. Derived `.rag.md` outputs,
`academic_resources/` and `.index/` are never touched. No API calls.

Writes land in academic_notes/, a separate git repo that you commit yourself.
"""
from __future__ import annotations

import argparse
import os

from core.env.corpus_write_lock import corpus_write_lock
from core.indexer.hub_identity import read_hub_id, write_hub_id
from core.indexer.index_card import list_courses, load_shard, save_shard


def _authored_files(hub_root: str, include_excalidraw_json: bool):
    """Yield (course, abs_path) for every authored note, sorted."""
    notes_root = os.path.join(hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return
    for course in sorted(os.listdir(notes_root)):
        course_dir = os.path.join(notes_root, course)
        if not os.path.isdir(course_dir) or course.startswith("."):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for name in sorted(filenames):
                lower = name.lower()
                if lower.endswith(".rag.md"):
                    continue
                if lower.endswith(".md") or (include_excalidraw_json and lower.endswith(".excalidraw")):
                    yield course, os.path.join(dirpath, name)


def plan(hub_root: str, include_excalidraw_json: bool = False) -> dict:
    would: dict[str, int] = {}
    for course, path in _authored_files(hub_root, include_excalidraw_json):
        if not read_hub_id(path):
            would[course] = would.get(course, 0) + 1
    return {"would_write": would}


def apply(hub_root: str, include_excalidraw_json: bool = False) -> dict:
    written = 0
    skipped: list[tuple[str, str]] = []
    stamped: dict[str, dict[str, str]] = {}  # course -> {rel path: hub_id}
    for course, path in _authored_files(hub_root, include_excalidraw_json):
        rel = os.path.relpath(path, hub_root).replace(os.sep, "/")
        had = read_hub_id(path)
        try:
            hub_id = write_hub_id(path)
        except ValueError as err:
            skipped.append((path, str(err)))
            continue
        if not had:
            written += 1
        stamped.setdefault(course, {})[rel] = hub_id
    cards_updated = 0
    for course in list_courses(hub_root):
        ids = stamped.get(course)
        if not ids:
            continue
        cards = load_shard(hub_root, course)
        changed = False
        for card in cards:
            hub_id = ids.get(str(card.get("path", "")).replace("\\", "/"))
            if hub_id and card.get("hub_id") != hub_id:
                card["hub_id"] = hub_id  # content_hash deliberately untouched
                cards_updated += 1
                changed = True
        if changed:
            save_shard(hub_root, course, cards)
    return {"written": written, "skipped": skipped, "cards_updated": cards_updated}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stamp stable hub_id identities into authored notes (no API calls).")
    parser.add_argument("--hub-root", required=True)
    parser.add_argument("--apply", action="store_true", help="write the ids (default: dry run)")
    parser.add_argument("--include-excalidraw-json", action="store_true",
                        help="also stamp plain .excalidraw JSON files (skipped by default)")
    args = parser.parse_args()
    if not args.apply:
        summary = plan(args.hub_root, args.include_excalidraw_json)
        for course, count in summary["would_write"].items():
            print(f"{course}: would write {count}")
        print(f"total would write: {sum(summary['would_write'].values())} (dry run; pass --apply)")
        return
    print("NOTE: writes land in academic_notes/, a separate git repo; commit them there yourself.")
    with corpus_write_lock([args.hub_root], "write hub ids"):
        summary = apply(args.hub_root, args.include_excalidraw_json)
    print(f"written: {summary['written']}, cards updated: {summary['cards_updated']}, skipped: {len(summary['skipped'])}")
    for path, reason in summary["skipped"]:
        print(f"skipped: {path}: {reason}")


if __name__ == "__main__":
    main()
