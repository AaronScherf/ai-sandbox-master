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
from discovery.discover_journal_articles.manifest import load_manifest, manifest_path, save_manifest
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


_TAG_RELEVANCE_FLOOR = 0.2


def resolve_folder_proposal(manifest: dict, articles_dir, key: str, chosen_folder: str) -> None:
    """Applies exactly one accepted decision from the review ledger:
    moves the paper's PDF+sidecar into chosen_folder only if it differs
    from the current folder, writes every above-floor topic into the
    sidecar as a tag regardless of which folder was chosen, and updates
    manifest[key]. Never called automatically -- only from an explicit
    --resolve KEY:FOLDER CLI call driven by a human decision recorded in
    the review Artifact."""
    entry = manifest.get(key)
    if entry is None:
        raise KeyError(f"{key!r} not found in manifest")
    if not chosen_folder or sanitize_topic_name(chosen_folder) != chosen_folder:
        raise ValueError(
            f"{chosen_folder!r} is not a valid sanitized folder name "
            f"(expected {sanitize_topic_name(chosen_folder)!r})"
        )

    articles_dir = Path(articles_dir)
    current_folder = entry.get("folder") or "misc"
    stem = sanitize_topic_name(key)[:80] or "paper"
    old_dir = articles_dir / current_folder
    new_dir = articles_dir / chosen_folder
    old_pdf, old_sidecar = old_dir / f"{stem}.pdf", old_dir / f"{stem}.meta.json"
    new_pdf, new_sidecar = new_dir / f"{stem}.pdf", new_dir / f"{stem}.meta.json"

    # Idempotency: a prior call may have crashed (or hit a file another
    # process had open) after moving one file but not the other. Resume
    # from wherever each file actually is instead of failing on a
    # source that's already gone.
    sidecar_path = old_sidecar if old_sidecar.exists() else new_sidecar
    sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    topics_data = sidecar_data.get("topics") or []
    sidecar_data["tags"] = sorted({
        sanitize_topic_name(t["display_name"]) for t in topics_data if t.get("score", 0) > _TAG_RELEVANCE_FLOOR
    })

    if chosen_folder != current_folder:
        new_dir.mkdir(parents=True, exist_ok=True)
        if old_pdf.exists():
            old_pdf.replace(new_pdf)
        elif not new_pdf.exists():
            raise FileNotFoundError(f"PDF not found at {old_pdf} or {new_pdf}")
        if sidecar_path == old_sidecar:
            sidecar_path = old_sidecar.replace(new_sidecar)
        entry["folder"] = chosen_folder

    write_json_atomic(sidecar_path, sidecar_data)

    topics = [Topic(id=t["id"], display_name=t["display_name"], score=t["score"]) for t in topics_data]
    entry["topic_decision_fingerprint"] = topics_fingerprint(topics)


def parse_resolve_arg(value: str) -> tuple[str, str]:
    """Splits a --resolve KEY:FOLDER argument on the LAST colon, not the
    first -- a manifest key built from an OpenAlex id is itself a URL
    containing colons (e.g. "https://openalex.org/W123"), so
    str.partition(":") would wrongly cut it down to "https"."""
    key, _, folder = value.rpartition(":")
    return key, folder


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build or apply the classification proposal review ledger.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    parser.add_argument("--build", action="store_true", help="(Re)write the review ledger from the current manifest/sidecars.")
    parser.add_argument("--resolve", metavar="KEY:FOLDER", help="Apply an accepted decision: move KEY into FOLDER (or keep it, tagging only, if FOLDER matches the current folder).")
    parser.add_argument("--reject", metavar="KEY", help="Record that KEY's current folder was explicitly kept as-is, without changing anything else.")
    args = parser.parse_args()

    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)

    if args.build:
        path = write_proposals_ledger(manifest, args.articles_dir)
        print(f"Wrote {path}")
        return

    if args.resolve:
        key, folder = parse_resolve_arg(args.resolve)
        resolve_folder_proposal(manifest, args.articles_dir, key, folder)
        save_manifest(manifest_file, manifest)
        print(f"Applied: {key} -> {folder}")
        return

    if args.reject:
        resolve_folder_proposal(manifest, args.articles_dir, args.reject, manifest[args.reject].get("folder") or "misc")
        save_manifest(manifest_file, manifest)
        print(f"Kept {args.reject} in its current folder; recorded as reviewed.")
        return

    parser.error("one of --build, --resolve, or --reject is required")


if __name__ == "__main__":
    main()
