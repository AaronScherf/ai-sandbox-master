"""Logged, reversible auto-repair of exact moves (hub-path-resilience P3, Task 4).

Only `moved` Differences (one decisive exact match) are ever applied; ambiguous and orphan are left
for review. A repair updates CARD fields only: `path`, and `rag_md_path` when that sidecar sat in the
same directory as the old path and also exists at the corresponding new location. Note frontmatter
(source_* hints) is never touched, so nothing is written into the academic_notes repo. Nothing is
deleted and no model is called.

Write-ahead log `<hub>/.index/reconcile_log.jsonl`, append-only, one JSON object per line:
`{repair_id, file_id, old, new, old_rag_md_path, new_rag_md_path, ts, status}` with status
`pending` (appended BEFORE the card write), `done` (after), `undone` (after an undo).

repair_id = sha256(file_id|old|new)[:12] + "-" + N, where N counts how many distinct repairs with that
triple the log already holds (so a move repaired, undone and repaired again gets a fresh id). A
`pending` with no `done` for the same triple is an interrupted run: re-running reuses its id and
completes the card write without a second `pending`.

Locking: `apply_repairs`, `apply_one` and `undo_repair` each hold the corpus write lock for their
whole action (the lock is not reentrant, so internals never lock).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from core.env.corpus_write_lock import corpus_write_lock
from core.indexer.index_card import _index_dir, find_card_by_file_id, update_card_paths
from core.indexer.reconcile import Difference

LOG_NAME = "reconcile_log.jsonl"


@dataclass
class RepairRecord:
    repair_id: str
    file_id: str
    old: str
    new: str
    old_rag_md_path: str | None
    new_rag_md_path: str | None
    ts: str
    status: str


def log_path(hub_root: str) -> str:
    return os.path.join(_index_dir(hub_root), LOG_NAME)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_log(hub_root: str) -> list[dict]:
    path = log_path(hub_root)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except ValueError:
                continue  # a torn last line from a crash; never fatal
            if isinstance(value, dict) and "repair_id" in value:
                out.append(value)
    return out


def _append(hub_root: str, record: RepairRecord) -> None:
    path = log_path(hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _as_record(entry: dict, status: str) -> RepairRecord:
    return RepairRecord(
        entry["repair_id"], entry["file_id"], entry["old"], entry["new"],
        entry.get("old_rag_md_path"), entry.get("new_rag_md_path"), _now(), status,
    )


def _latest(entries: list[dict]) -> dict[str, dict]:
    """repair_id -> its last log line (the current status)."""
    state: dict[str, dict] = {}
    for e in entries:
        state[e["repair_id"]] = e
    return state


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def _new_rag(hub_root: str, card: dict, old: str, new: str) -> str | None:
    rag = card.get("rag_md_path")
    if not rag:
        return None
    rag, old, new = _norm(rag), _norm(old), _norm(new)
    old_dir, new_dir = os.path.dirname(old), os.path.dirname(new)
    if os.path.dirname(rag) != old_dir:
        return None
    candidate = f"{new_dir}/{os.path.basename(rag)}" if new_dir else os.path.basename(rag)
    return candidate if os.path.isfile(os.path.join(hub_root, candidate)) else None


def _apply_unlocked(hub_root: str, diff: Difference, new_path: str | None) -> RepairRecord | None:
    if diff.kind != "moved":
        return None
    allowed = [c.path for c in diff.candidates]
    new = new_path if new_path is not None else (allowed[0] if allowed else None)
    if new is None or new not in allowed:
        raise ValueError(f"{new_path!r} is not a candidate for {diff.file_id}")
    old = diff.old_path
    found = find_card_by_file_id(hub_root, diff.file_id)
    if found is None:
        return None
    _, card = found
    if not os.path.isfile(os.path.join(hub_root, new)):
        return None

    entries = _read_log(hub_root)
    state = _latest(entries)
    pending = next((e for e in reversed(entries)
                    if e["status"] == "pending" and state[e["repair_id"]]["status"] == "pending"
                    and (e["file_id"], e["old"], e["new"]) == (diff.file_id, old, new)), None)

    if pending is not None:  # interrupted run: finish it, no second pending
        if card.get("path") not in (old, new):
            return None
        rec = _as_record(pending, "done")
        if card.get("path") == old:
            update_card_paths(hub_root, diff.file_id, new, rec.new_rag_md_path
                              if rec.new_rag_md_path != rec.old_rag_md_path else None)
        _append(hub_root, rec)
        return rec

    if card.get("path") != old:
        return None
    digest = hashlib.sha256(f"{diff.file_id}|{old}|{new}".encode("utf-8")).hexdigest()[:12]
    n = sum(1 for rid in state if rid.startswith(digest + "-")) + 1
    new_rag = _new_rag(hub_root, card, old, new)
    old_rag = card.get("rag_md_path")
    pend = RepairRecord(f"{digest}-{n}", diff.file_id, old, new, old_rag,
                        new_rag if new_rag else old_rag, _now(), "pending")
    _append(hub_root, pend)
    update_card_paths(hub_root, diff.file_id, new, new_rag)
    done = RepairRecord(**{**pend.__dict__, "ts": _now(), "status": "done"})
    _append(hub_root, done)
    return done


def apply_one(hub_root: str, difference: Difference, new_path: str | None = None) -> RepairRecord | None:
    """Apply one `moved` difference (or, for review, a user-chosen candidate via `new_path`, which
    must be one of the difference's candidates else ValueError). None when skipped: not `moved`, the
    card's path is no longer `old_path`, or the target file is gone."""
    with corpus_write_lock([hub_root], "reconcile repair"):
        return _apply_unlocked(hub_root, difference, new_path)


def apply_repairs(hub_root: str, differences: list[Difference]) -> list[RepairRecord]:
    """Apply every `moved` difference under one lock hold; return the repairs actually made."""
    out: list[RepairRecord] = []
    with corpus_write_lock([hub_root], "reconcile repair"):
        for diff in differences:
            rec = _apply_unlocked(hub_root, diff, None)
            if rec is not None:
                out.append(rec)
    return out


def undo_repair(hub_root: str, repair_id: str) -> bool:
    """Restore the card's `path`/`rag_md_path` from the log. False (never raises) if the repair is
    unknown, not `done` (pending or already undone), or the card's path is no longer its `new`."""
    with corpus_write_lock([hub_root], "reconcile undo"):
        last = _latest(_read_log(hub_root)).get(repair_id)
        if last is None or last["status"] != "done":
            return False
        found = find_card_by_file_id(hub_root, last["file_id"])
        if found is None or found[1].get("path") != last["new"]:
            return False
        rec = _as_record(last, "undone")
        restore_rag = rec.old_rag_md_path if rec.old_rag_md_path != rec.new_rag_md_path else None
        update_card_paths(hub_root, rec.file_id, rec.old, restore_rag)
        _append(hub_root, rec)
        return True
