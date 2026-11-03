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

Review items (Task 5). `ambiguous` and `orphan` differences become findings in the corpus-health
decision ledger (`tools.corpus_health.state.StateStore`; kinds `relink` / `orphan_card`), shaped for
the shared review page by `core.indexer.review_envelope`:
- `raise_relink_items(hub_root, differences=None, store=None)` (lock held for the whole call;
  `raise_relink_items_unlocked` for lock holders; `differences` defaults to `reconcile(hub_root)` and
  if given must be a FULL reconcile result): upserts one finding per non-moved difference
  (fingerprint = envelope item_id, scope `file_id:<id>`, root `academic-hub-index`, path = the card's
  old path), sweeps relink/orphan findings no longer present, marks each open `relink` card
  `link_state: "unresolved"` and clears the mark from every other card. Declined items are kept
  declined in the ledger and are not returned or marked. Writes only the ledger and `link_state`.
- `resolve(hub_root, file_id, chosen_path)`: re-runs `reconcile` (stale-safe) and applies only a
  CURRENT ambiguous difference whose candidates include `chosen_path`, via `apply_one_unlocked` under
  the lock; then clears `link_state` and records the finding accepted + applied. False, never raises,
  when there is no such difference, it is an orphan, the path is not a candidate, or the apply is
  refused.
- `reject(hub_root, file_id)`: records the finding declined (not re-raised for the same candidate
  set), clears `link_state`, leaves the card path as is. Idempotent; False only with no such item.
The ledger is imported lazily (`tools.corpus_health`), so importing this module keeps core free of a
tools dependency; `store=None` means the hub's default ledger (`default_state_dir(hub_root)`).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from core.env.corpus_write_lock import corpus_write_lock
from core.indexer.index_card import (
    _index_dir, find_card_by_file_id, list_courses, load_shard, set_link_state, update_card_paths,
)
from core.indexer.reconcile import Difference, reconcile
from core.indexer.review_envelope import ReviewItem, difference_to_item, is_unresolved

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
    lead = ""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                lead = "\n"  # torn last line: keep it from fusing with this record
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(lead + json.dumps(record.__dict__, ensure_ascii=False) + "\n")
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


def _recover(hub_root: str) -> None:
    """Complete interrupted repairs: a `pending` whose card already sits at `new` (crash between the
    card write and the `done` line) gets its `done` appended."""
    state = _latest(_read_log(hub_root))
    for entry in state.values():
        if entry["status"] != "pending":
            continue
        found = find_card_by_file_id(hub_root, entry["file_id"])
        if found is not None and found[1].get("path") == entry["new"]:
            _append(hub_root, _as_record(entry, "done"))


def _claimed_by_other(hub_root: str, new: str, file_id: str) -> bool:
    target = _norm(new).lower()
    for course in list_courses(hub_root):
        for card in load_shard(hub_root, course):
            if card.get("file_id") != file_id and _norm(card.get("path") or "").lower() == target:
                return True
    return False


def _apply_unlocked(hub_root: str, diff: Difference, new_path: str | None) -> RepairRecord | None:
    """Skip (None) when: orphan; ambiguous without new_path; moved with no candidate; the card's path
    is no longer `old_path`; the target file is gone; or another card already holds the target (only
    when the target was defaulted). Raises ValueError for a `new_path` that is not a candidate or that
    another card already holds (an explicit choice that cannot be honored should be loud)."""
    if diff.kind == "orphan" or (diff.kind == "ambiguous" and new_path is None):
        return None
    allowed = [c.path for c in diff.candidates]
    if new_path is None and not allowed:
        return None
    new = new_path if new_path is not None else allowed[0]
    if new not in allowed:
        raise ValueError(f"{new_path!r} is not a candidate for {diff.file_id}")
    old = diff.old_path
    found = find_card_by_file_id(hub_root, diff.file_id)
    if found is None:
        return None
    _, card = found
    if not os.path.isfile(os.path.join(hub_root, new)):
        return None
    if _claimed_by_other(hub_root, new, diff.file_id):
        if new_path is not None:
            raise ValueError(f"{new!r} is already the path of another card")
        return None

    entries = _read_log(hub_root)
    state = _latest(entries)
    pending = next((e for e in reversed(entries)
                    if e["status"] == "pending" and state[e["repair_id"]]["status"] == "pending"
                    and (e["file_id"], e["old"], e["new"]) == (diff.file_id, old, new)), None)

    if pending is not None:  # interrupted before the card write: finish it, no second pending
        if card.get("path") != old:
            return None
        rec = _as_record(pending, "done")
        rag = rec.new_rag_md_path
        if rag == rec.old_rag_md_path or not rag or not os.path.isfile(os.path.join(hub_root, rag)):
            rag = None
            rec.new_rag_md_path = rec.old_rag_md_path
        update_card_paths(hub_root, diff.file_id, new, rag)
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


def apply_one_unlocked(hub_root: str, difference: Difference, new_path: str | None = None) -> RepairRecord | None:
    """`apply_one` for callers that already hold the corpus write lock (it is not reentrant).

    `moved`: applies its sole candidate (or `new_path`, which must be a candidate). `ambiguous`:
    applies only when `new_path` is given and is a candidate. `orphan`: never. Raises ValueError for a
    `new_path` that is not a candidate or is already another card's path."""
    _recover(hub_root)
    return _apply_unlocked(hub_root, difference, new_path)


def apply_one(hub_root: str, difference: Difference, new_path: str | None = None) -> RepairRecord | None:
    """Lock + `apply_one_unlocked`."""
    with corpus_write_lock([hub_root], "reconcile repair"):
        return apply_one_unlocked(hub_root, difference, new_path)


def apply_repairs(hub_root: str, differences: list[Difference]) -> list[RepairRecord]:
    """Apply every `moved` difference under one lock hold; return the repairs actually made. Because
    each repair is written to its card before the next is checked, a later difference aiming at an
    already-taken path is skipped."""
    out: list[RepairRecord] = []
    with corpus_write_lock([hub_root], "reconcile repair"):
        _recover(hub_root)
        for diff in differences:
            if diff.kind != "moved":
                continue
            rec = _apply_unlocked(hub_root, diff, None)
            if rec is not None:
                out.append(rec)
    return out


def undo_repair(hub_root: str, repair_id: str) -> bool:
    """Restore the card's `path`/`rag_md_path` from the log. False (never raises) if the repair is
    unknown, not `done` (pending or already undone), or the card's path is no longer its `new`."""
    with corpus_write_lock([hub_root], "reconcile undo"):
        _recover(hub_root)
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


# --- review items: relink / orphan findings in the corpus-health ledger (Task 5) ---

# The relink kinds ("relink", "orphan_card") are defined once, as
# tools.corpus_health.state.SELF_REFRESHED_KINDS, and imported lazily where needed.
LEDGER_ROOT = "academic-hub-index"
_OPEN = {"pending_review", "deferred"}
_ENVELOPE_STATUS = {"pending_review": "pending", "failed": "pending", "deferred": "deferred",
                    "accepted": "accepted", "blocked": "accepted", "applied": "accepted",
                    "declined": "declined"}


def _default_store(hub_root: str):
    from tools.corpus_health.state import StateStore, default_state_dir
    return StateStore(default_state_dir(hub_root))


def _scope(file_id: str) -> str:
    return f"file_id:{file_id}"


def _finding(diff: Difference, item: ReviewItem):
    from tools.corpus_health.finding import Finding
    name = os.path.basename(diff.old_path)
    if item.type == "relink":
        listed = "; ".join(f"{c['path']} ({c['basis']} {c['score']:.2f})" for c in item.candidates)
        return Finding(
            "relink", LEDGER_ROOT, diff.old_path, f"Relink {name}",
            f"card {diff.file_id} no longer resolves; candidates: {listed}. {diff.evidence}".strip(),
            suggested_action="choose the card's new location, or dismiss to leave it unlinked",
            fingerprint=item.item_id, severity="actionable", cost_category="local_manual",
            scope=_scope(diff.file_id),
        )
    return Finding(
        "orphan_card", LEDGER_ROOT, diff.old_path, f"Orphaned card {name}",
        f"card {diff.file_id} no longer resolves and no candidate file was found. {diff.evidence}".strip(),
        suggested_action="report only: restore the file or dismiss",
        fingerprint=item.item_id, severity="informational", cost_category="local_manual",
        scope=_scope(diff.file_id),
    )


def _with_ledger(item: ReviewItem, entry: dict) -> ReviewItem:
    decision = entry.get("decision") or {}
    item.status = _ENVELOPE_STATUS.get(entry.get("status"), "pending")
    item.created = entry.get("created_at") or entry.get("first_seen") or ""
    item.updated = decision.get("at") or entry.get("last_seen") or item.created
    return item


def raise_relink_items(hub_root: str, differences: list[Difference] | None = None,
                       store=None) -> list[ReviewItem]:
    """Upsert a ledger finding per ambiguous/orphan difference and mark open relink cards unresolved.

    `differences` defaults to `reconcile(hub_root)` run here. If given it MUST be a full reconcile
    result: every relink/orphan finding and `link_state` mark absent from it is swept (vanished) /
    cleared, so a partial list un-raises the rest. Returns the items the owner has not declined, with
    ledger status and timestamps. Takes the corpus write lock for the whole call (not reentrant):
    callers already holding it use `raise_relink_items_unlocked`. `store=None` = the hub's default
    ledger."""
    with corpus_write_lock([hub_root], "reconcile relink raise"):
        return raise_relink_items_unlocked(hub_root, differences, store)


def raise_relink_items_unlocked(hub_root: str, differences: list[Difference] | None = None,
                                store=None) -> list[ReviewItem]:
    """`raise_relink_items` for callers that already hold the corpus write lock."""
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    if differences is None:
        differences = reconcile(hub_root)
    store = store or _default_store(hub_root)
    raised = [(d, difference_to_item(d)) for d in differences if d.kind != "moved"]
    refreshed = store.refresh([_finding(d, item) for d, item in raised], sweep_kinds=SELF_REFRESHED_KINDS)
    ledger = {e.get("finding_id"): e for e in store.entries(kinds=SELF_REFRESHED_KINDS)}
    out: list[ReviewItem] = []
    unresolved: set[str] = set()
    for (d, item), finding in zip(raised, refreshed):
        entry = ledger.get(finding.finding_id) or {}
        item = _with_ledger(item, entry)
        if item.status == "declined":
            continue
        out.append(item)
        if item.type == "relink" and entry.get("status") in _OPEN:
            unresolved.add(d.file_id)
    for course in list_courses(hub_root):
        for card in load_shard(hub_root, course):
            fid = card.get("file_id")
            if fid in unresolved and not is_unresolved(card):
                set_link_state(hub_root, fid, "unresolved")
            elif fid not in unresolved and is_unresolved(card):
                set_link_state(hub_root, fid, None)
    return out


def _current_difference(hub_root: str, file_id: str) -> Difference | None:
    return next((d for d in reconcile(hub_root) if d.file_id == file_id), None)


def _record_decision(store, diff: Difference, decision: str, detail: dict | None = None) -> None:
    (finding,) = store.refresh([_finding(diff, difference_to_item(diff))], sweep_kinds=())
    entry = store.get_entry(finding.finding_id) or {}
    if entry.get("status") not in _OPEN:
        return  # already decided (e.g. a resolve after a dismissal): the repair stands, ledger kept
    store.decide(finding.finding_id, decision, finding.fingerprint)
    if decision == "accepted":
        store.record_action(finding.finding_id, finding.fingerprint, "applied", detail or {})


def resolve(hub_root: str, file_id: str, chosen_path: str, *, store=None) -> bool:
    """Relink the card to `chosen_path` if it is a candidate of the card's CURRENT ambiguous
    difference. False (never raises) otherwise, or when the apply is refused."""
    diff = _current_difference(hub_root, file_id)
    if diff is None or diff.kind != "ambiguous" or chosen_path not in [c.path for c in diff.candidates]:
        return False
    with corpus_write_lock([hub_root], "reconcile relink resolve"):
        try:
            rec = apply_one_unlocked(hub_root, diff, chosen_path)
        except ValueError:
            return False
        if rec is None:
            return False
        set_link_state(hub_root, file_id, None)
    try:
        _record_decision(store or _default_store(hub_root), diff, "accepted",
                         {"repair_id": rec.repair_id, "path": chosen_path})
    except Exception as exc:  # the repair is logged and undoable; the next raise reconciles the ledger
        print(f"WARNING: relink {file_id} applied but the ledger was not updated: {exc}")
    return True


def reject(hub_root: str, file_id: str, *, store=None) -> bool:
    """Dismiss the card's relink/orphan item: decline it in the ledger (not re-raised for the same
    candidate set), clear `link_state`, leave the card path as is. Idempotent; False only when there
    is neither a ledger item nor a current ambiguous/orphan difference for `file_id`."""
    store = store or _default_store(hub_root)
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    entries = [e for e in store.entries(kinds=SELF_REFRESHED_KINDS)
               if e.get("finding", {}).get("scope") == _scope(file_id) and e.get("status") != "vanished"]
    for e in entries:
        if e.get("status") in _OPEN:
            store.decide(e["finding_id"], "declined", e["finding"].get("fingerprint"))
    if not entries:
        diff = _current_difference(hub_root, file_id)
        if diff is None or diff.kind == "moved":
            return False
        _record_decision(store, diff, "declined")
    with corpus_write_lock([hub_root], "reconcile relink reject"):
        set_link_state(hub_root, file_id, None)
    return True
