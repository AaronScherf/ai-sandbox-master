"""Detect and repair duplicate `hub_id`s (hub-path-resilience P4).

Two authored notes (or two index cards) must never share a hub_id. Detection reads file
frontmatter ids and card ids; derived outputs are skipped exactly as `tools.write_hub_ids` skips
them. Repair re-stamps every file but the keeper with a fresh id and points its card at it
(content_hash untouched). Dry run unless `apply=True`. No API calls.
"""
from __future__ import annotations

import os
import subprocess

from core.indexer.hub_identity import read_hub_id, replace_hub_id, write_hub_id
from core.indexer.index_card import list_courses, load_shard, save_shard

_PLACEHOLDER = "(new id on apply)"


def _norm(path: str) -> str:
    return str(path).replace("\\", "/")


def _file_ids(hub_root: str) -> dict[str, str]:
    from tools.write_hub_ids import _candidate_files  # one definition of "authored, not derived"

    ids: dict[str, str] = {}
    for _course, path, derived in _candidate_files(hub_root, True):
        if derived:
            continue
        try:
            hub_id = read_hub_id(path)
        except OSError:
            continue
        if hub_id:
            ids[_norm(os.path.relpath(path, hub_root))] = hub_id
    return ids


def _card_ids(hub_root: str) -> dict[str, str]:
    ids: dict[str, str] = {}
    for course in list_courses(hub_root):
        for card in load_shard(hub_root, course):
            if card.get("hub_id") and card.get("path"):
                ids[_norm(card["path"])] = card["hub_id"]
    return ids


def find_duplicate_hub_ids(hub_root: str) -> dict[str, list[str]]:
    """id -> sorted hub-relative paths, only ids held by 2+ files or by 2+ cards."""
    files, cards = _file_ids(hub_root), _card_ids(hub_root)
    by_id: dict[str, dict[str, set[str]]] = {}
    for kind, mapping in (("files", files), ("cards", cards)):
        for path, hub_id in mapping.items():
            by_id.setdefault(hub_id, {"files": set(), "cards": set()})[kind].add(path)
    return {hub_id: sorted(v["files"] | v["cards"]) for hub_id, v in sorted(by_id.items())
            if len(v["files"]) > 1 or len(v["cards"]) > 1}


def _first_commit_time(hub_root: str, rel: str) -> float | None:
    try:
        out = subprocess.run(["git", "log", "--follow", "--diff-filter=A", "--format=%ct", "--", os.path.basename(rel)],
                             cwd=os.path.dirname(os.path.join(hub_root, rel)), capture_output=True, text=True,
                             timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    times = [int(t) for t in out.stdout.split() if t.isdigit()]
    return float(min(times)) if out.returncode == 0 and times else None


def _default_keeper(hub_root: str, hub_id: str, paths: list[str], cards: dict[str, str]) -> str:
    pointed = [p for p in paths if cards.get(p) == hub_id] or paths
    dated = [(t, p) for p in pointed if (t := _first_commit_time(hub_root, p)) is not None]
    if len(dated) == len(pointed) and dated:
        return min(dated)[1]
    return sorted(pointed)[0]


def restamp_duplicates(hub_root: str, keep: dict[str, str], apply: bool = False) -> list[tuple[str, str, str]]:
    """Return (path, old_id, new_id) for every non-keeper. Default keeper: the file its card
    points at, else oldest by git first commit, else the lexicographically first path."""
    duplicates = find_duplicate_hub_ids(hub_root)
    cards = _card_ids(hub_root)
    changes: list[tuple[str, str, str]] = []
    new_for: dict[str, str] = {}
    for hub_id, paths in duplicates.items():
        keeper = _norm(keep[hub_id]) if hub_id in keep else _default_keeper(hub_root, hub_id, paths, cards)
        for path in paths:
            if path == keeper:
                continue
            abs_path = os.path.join(hub_root, path)
            has_file = os.path.isfile(abs_path)
            own = read_hub_id(abs_path) if has_file else None
            if not apply:
                changes.append((path, hub_id, own if has_file and own and own != hub_id else _PLACEHOLDER))
            elif has_file and own == hub_id:
                new_for[path] = replace_hub_id(abs_path)
                changes.append((path, hub_id, new_for[path]))
            elif has_file:  # only its card carried the duplicate: adopt the file's own id
                new_for[path] = own or write_hub_id(abs_path)
                changes.append((path, hub_id, new_for[path]))
    if apply and new_for:
        for course in list_courses(hub_root):
            shard = load_shard(hub_root, course)
            changed = False
            for card in shard:
                new = new_for.get(_norm(card.get("path", "")))
                if new and card.get("hub_id") != new:
                    card["hub_id"] = new  # content_hash deliberately untouched
                    changed = True
            if changed:
                save_shard(hub_root, course, shard)
    return changes
