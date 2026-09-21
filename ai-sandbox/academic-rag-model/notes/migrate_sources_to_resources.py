"""
migrate_sources_to_resources.py
One-shot migration: moves heavy note sources (PDFs, Excalidraw
.svg/.png exports, docx/pptx) from academic_notes/ to academic_resources/,
mirroring each file's <course>/<category>/<filename> relative path. Never
moves a .excalidraw.md scene file or anything under processed_outputs/ --
those stay in academic_notes/ by design (see
docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md and its
2026-09-21 addendum for the docx/pptx scope decision).
After moving files, calls index_search.rebuild() so every affected card's
source_pdf_path/source_asset_path gets refreshed via its existing cheap
"file moved, content unchanged" reconciliation -- no LLM call in the
common case.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from common.academic_hub_paths import to_resources_root

_EXCALIDRAW_IMAGE_EXTENSIONS = (".png", ".svg")
# 2026-09-21 addendum: docx/pptx are in scope too (user decision) -- purely
# mechanical, no downstream code reads them from their new location, so
# they only need to be included in this filter, nothing else.
_MECHANICAL_EXTENSIONS = (".docx", ".pptx")


def find_migration_candidates(academic_hub_root: str, course: str | None = None) -> list[tuple[str, str]]:
    notes_root = os.path.join(academic_hub_root, "academic_notes")
    if not os.path.isdir(notes_root):
        return []
    candidates: list[tuple[str, str]] = []
    for course_name in sorted(os.listdir(notes_root)):
        if course and course_name != course:
            continue
        course_dir = os.path.join(notes_root, course_name)
        if not os.path.isdir(course_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(course_dir):
            dirnames[:] = [d for d in dirnames if d != "processed_outputs" and not d.startswith(".")]
            for name in sorted(filenames):
                lower = name.lower()
                is_pdf = lower.endswith(".pdf")
                is_excalidraw_image = any(lower.endswith(f".excalidraw{ext}") for ext in _EXCALIDRAW_IMAGE_EXTENSIONS)
                is_mechanical = lower.endswith(_MECHANICAL_EXTENSIONS)
                if not (is_pdf or is_excalidraw_image or is_mechanical):
                    continue
                current_path = os.path.join(dirpath, name)
                target_path = to_resources_root(current_path)
                candidates.append((current_path, target_path))
    return candidates


def migrate_one(current_path: str, target_path: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  would move: {current_path} -> {target_path}")
        return
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.move(current_path, target_path)
    print(f"  moved: {current_path} -> {target_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Move heavy note sources (PDFs, Excalidraw .svg/.png exports, docx/pptx) from "
                    "academic_notes/ to academic_resources/, then resync the source index."
    )
    parser.add_argument("--course", default=None, help="Limit to this course. Default: every course.")
    parser.add_argument("--dry-run", action="store_true", help="List what would move without touching anything.")
    parser.add_argument("--no-reindex", action="store_true", help="Skip the rebuild() call after moving files.")
    args = parser.parse_args()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    candidates = find_migration_candidates(str(academic_hub_dir), course=args.course)
    if not candidates:
        print("Nothing to migrate.")
        return

    print(f"{len(candidates)} file(s) to migrate.")
    for current_path, target_path in candidates:
        migrate_one(current_path, target_path, dry_run=args.dry_run)

    if args.dry_run:
        return

    if args.no_reindex:
        print("Skipping reindex (--no-reindex). Run `python -m indexer.index_search rebuild` when ready.")
        return

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    from indexer.index_search import rebuild
    load_dotenv_override()
    client = get_gemini_client()
    if client is None:
        print("WARNING: could not get a Gemini client; skipping reindex. "
              "Run `python -m indexer.index_search rebuild` by hand.")
        sys.exit(1)
    stats = rebuild(str(academic_hub_dir), client, course=args.course)
    print(f"Reindex complete: {stats}")


if __name__ == "__main__":
    main()
