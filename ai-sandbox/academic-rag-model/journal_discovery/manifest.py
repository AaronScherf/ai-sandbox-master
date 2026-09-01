"""
manifest.py
Dedup manifest per spec S5: research/journal-articles/.discovery/seen.json,
keyed by DOI (falling back to OpenAlex work id absent a DOI), so a paper
reached by both a --faculty and a --topic query in the same or a later
run is only ever fetched once.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from journal_discovery.discovery import Work


def manifest_path(articles_dir) -> Path:
    return Path(articles_dir) / ".discovery" / "seen.json"


def load_manifest(path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(path, manifest: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def manifest_key(work: Work) -> str:
    return work.doi or work.openalex_id


def is_seen(manifest: dict, key: str) -> bool:
    return key in manifest


def record_outcome(manifest: dict, key: str, status: str, folder: str | None = None) -> None:
    entry = {"status": status, "fetched_at": datetime.now(timezone.utc).isoformat()}
    if folder is not None:
        entry["folder"] = folder
    manifest[key] = entry
