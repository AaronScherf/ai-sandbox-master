"""
backfill_topics.py
One-time pass per spec Section B.3: existing sidecars only ever stored
flat Concept display-names (Topics weren't fetched historically). Looks
up each manifest entry by DOI against the live OpenAlex API and writes
the resulting `topics` list into that paper's existing sidecar, touching
nothing else -- not its folder, not its PDF.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from core.env.gemini_utils import load_dotenv_override
from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import resolve_work_by_doi
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path
from discovery.discover_journal_articles.topic_routing import sanitize_topic_name


def _sidecar_path_for(articles_dir: Path, folder: str, key: str) -> Path:
    stem = sanitize_topic_name(key)[:80] or "paper"
    return articles_dir / folder / f"{stem}.meta.json"


def backfill_topics(manifest: dict, articles_dir, mailto: str) -> dict:
    articles_dir = Path(articles_dir)
    counts = {"updated": 0, "skipped_no_folder": 0, "skipped_no_doi": 0, "skipped_not_found": 0}

    for key, entry in manifest.items():
        folder = entry.get("folder")
        if not folder:
            counts["skipped_no_folder"] += 1
            continue
        sidecar = _sidecar_path_for(articles_dir, folder, key)
        if not sidecar.exists():
            counts["skipped_no_folder"] += 1
            continue
        if key.startswith("http"):
            counts["skipped_no_doi"] += 1
            continue

        work = resolve_work_by_doi(key, mailto)
        if work is None:
            counts["skipped_not_found"] += 1
            continue

        sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
        sidecar_data["topics"] = [
            {"id": t.id, "display_name": t.display_name, "score": t.score} for t in work.topics
        ]
        write_json_atomic(sidecar, sidecar_data)
        counts["updated"] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Backfill OpenAlex Topics data into existing journal-article sidecars.")
    default_articles_dir = Path(__file__).resolve().parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    load_dotenv_override()
    mailto = os.environ.get("OPENALEX_CONTACT_EMAIL")
    if not mailto:
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env.")
        raise SystemExit(1)

    manifest = load_manifest(manifest_path(args.articles_dir))
    counts = backfill_topics(manifest, args.articles_dir, mailto)
    print(f"Updated: {counts['updated']}")
    print(f"Skipped (no folder/sidecar): {counts['skipped_no_folder']}")
    print(f"Skipped (no DOI): {counts['skipped_no_doi']}")
    print(f"Skipped (not found in OpenAlex): {counts['skipped_not_found']}")


if __name__ == "__main__":
    main()
