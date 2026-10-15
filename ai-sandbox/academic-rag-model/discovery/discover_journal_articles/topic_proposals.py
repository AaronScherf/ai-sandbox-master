"""
topic_proposals.py
Read-only classification-proposal ledger per spec Section B: never moves
a file on its own. build_proposals_ledger()/write_proposals_ledger()
only ever produce review data, surfaced through an interactive Artifact
per the project's standing convention (core/indexer/offering_links.py).
resolve_folder_proposal() (added in Task 12) is the only thing that
actually moves a file, driven by an explicit accepted decision.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from discovery.discover_journal_articles.atomic_io import write_json_atomic
from discovery.discover_journal_articles.discovery import Topic
from discovery.discover_journal_articles.topic_routing import propose_folder, sanitize_topic_name

_ACTIVE_STATUSES = frozenset({"fetched", "downloaded"})


def proposals_ledger_path(articles_dir) -> Path:
    return Path(articles_dir) / ".discovery" / "topic_proposals.json"


def topics_fingerprint(topics: list[Topic]) -> str:
    """A stable fingerprint over (id, score) pairs -- changes only when
    OpenAlex actually re-ranks or adds/removes topics for this paper,
    not on sidecar key ordering."""
    pairs = sorted((t.id, round(t.score, 6)) for t in topics)
    return hashlib.sha256(json.dumps(pairs, sort_keys=True).encode("utf-8")).hexdigest()


def _sidecar_path_for(folder_dir: Path, key: str) -> Path:
    # Same filename formula as topic_routing.pdf_filename()/discover.py's
    # write_sidecar() call site, applied to the bare manifest key.
    stem = sanitize_topic_name(key)[:80] or "paper"
    return folder_dir / f"{stem}.meta.json"


def build_proposals_ledger(manifest: dict, articles_dir) -> list[dict]:
    articles_dir = Path(articles_dir)
    entries = []
    for key, manifest_entry in manifest.items():
        if manifest_entry.get("status") not in _ACTIVE_STATUSES:
            continue
        folder = manifest_entry.get("folder")
        if not folder:
            continue
        sidecar = _sidecar_path_for(articles_dir / folder, key)
        if not sidecar.exists():
            continue

        sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
        topics_data = sidecar_data.get("topics") or []
        if not topics_data:
            continue

        topics = [Topic(id=t["id"], display_name=t["display_name"], score=t["score"]) for t in topics_data]
        proposal = propose_folder(topics, folder)
        fingerprint = topics_fingerprint(topics)
        recorded_fingerprint = manifest_entry.get("topic_decision_fingerprint")

        entries.append({
            "key": key,
            "title": sidecar_data.get("title"),
            "current_folder": proposal.current_folder,
            "candidates": [{"folder": name, "score": score} for name, score in proposal.candidates],
            "fingerprint": fingerprint,
            "stale": recorded_fingerprint is not None and recorded_fingerprint != fingerprint,
        })
    return entries


def write_proposals_ledger(manifest: dict, articles_dir) -> Path:
    entries = build_proposals_ledger(manifest, articles_dir)
    path = proposals_ledger_path(articles_dir)
    write_json_atomic(path, entries)
    return path
