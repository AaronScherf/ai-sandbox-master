"""Stamp a stable `hub_id` into every authored note under <hub-root>/academic_notes/.

    python -m tools.write_hub_ids --hub-root PATH [--apply] [--include-excalidraw-json]

Dry run by default. `--apply` writes the id into each note's frontmatter
(`.md`, including `.excalidraw.md`) and sets `hub_id` on the matching index
card (matched by `path`), leaving `content_hash` untouched (the id line is
hash-neutral). Plain `.excalidraw` JSON files are skipped unless
`--include-excalidraw-json` is given. `academic_resources/` and `.index/` are
never touched. Derived outputs, whose producers rewrite them and would drop the
id, are never stamped and are listed as skipped ("derived output"): anything
under a `processed_outputs/` directory (note transcriptions, raw Excalidraw
transcripts), `*.rag.md`, `*.excalidraw.questions.md` sidecars, and video
lecture notes (a `.md` with a sibling `<stem>.meta.json`). No API calls.

Writes land in academic_notes/, a separate git repo that you commit yourself.
"""
from __future__ import annotations

import argparse
import os

from core.env.corpus_write_lock import corpus_write_lock
from core.indexer.hub_identity import check_stampable, read_hub_id, write_hub_id
from core.indexer.index_card import list_courses, load_shard, save_shard


DERIVED = "derived output"
_DERIVED_SUFFIXES = (".rag.md", ".excalidraw.questions.md")


def _derived(dirpath: str, name: str, filenames: list[str]) -> bool:
    lower = name.lower()
    if lower.endswith(_DERIVED_SUFFIXES):
        return True
    if "processed_outputs" in dirpath.replace("\\", "/").split("/"):
        return True
    return lower.endswith(".md") and f"{name[:-3]}.meta.json" in filenames  # a video lecture note


def _candidate_files(hub_root: str, include_excalidraw_json: bool):
    """Yield (course, abs_path, derived) for every `.md` (and opted-in `.excalidraw`) under academic_notes/,
    sorted."""
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
                if lower.endswith(".md") or (include_excalidraw_json and lower.endswith(".excalidraw")):
                    yield course, os.path.join(dirpath, name), _derived(dirpath, name, filenames)


def plan(hub_root: str, include_excalidraw_json: bool = False) -> dict:
    would: dict[str, int] = {}
    skipped: list[tuple[str, str]] = []
    for course, path, derived in _candidate_files(hub_root, include_excalidraw_json):
        if derived:
            skipped.append((path, DERIVED))
            continue
        if not read_hub_id(path):
            try:
                check_stampable(path)
            except ValueError as err:
                skipped.append((path, str(err)))
                continue
            would[course] = would.get(course, 0) + 1
    return {"would_write": would, "skipped": skipped}


def apply(hub_root: str, include_excalidraw_json: bool = False) -> dict:
    written = 0
    skipped: list[tuple[str, str]] = []
    stamped: dict[str, dict[str, str]] = {}  # course -> {rel path: hub_id}
    for course, path, derived in _candidate_files(hub_root, include_excalidraw_json):
        if derived:
            skipped.append((path, DERIVED))
            continue
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
    parser.add_argument("--fix-duplicates", action="store_true",
                        help="re-stamp files that share a hub_id (dry run unless --apply)")
    args = parser.parse_args()
    if args.fix_duplicates:
        from core.indexer.duplicate_ids import restamp_duplicates
        if not args.apply:
            changes = restamp_duplicates(args.hub_root, {}, apply=False)
        else:
            print("NOTE: writes land in academic_notes/, a separate git repo; commit them there yourself.")
            with corpus_write_lock([args.hub_root], "restamp duplicate hub ids"):
                changes = restamp_duplicates(args.hub_root, {}, apply=True)
        for path, old, new in changes:
            print(f"{path}: {old} -> {new}")
        print(f"{len(changes)} duplicate(s) {'restamped' if args.apply else 'found (dry run; pass --apply)'}")
        return
    if not args.apply:
        summary = plan(args.hub_root, args.include_excalidraw_json)
        for course, count in summary["would_write"].items():
            print(f"{course}: would write {count}")
        for path, reason in summary["skipped"]:
            print(f"would skip: {path}: {reason}")
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
