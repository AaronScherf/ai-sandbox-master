"""Pipeline preflight (hub-path-resilience P4): refuse to run on links that need a human decision.

`check` returns the open items that block a run needing certain courses/files; `require_resolved`
raises `UnresolvedLinksError` when there are any. It never applies a repair and never writes a card
(`raise_relink_items_unlocked(..., mark_link_state=False)`): it may only write the local ledger and
`<state_dir>/preflight.json`.

Cost: a stat-only `tree_fingerprint` of `academic_notes/` + `academic_resources/` + the hub's `.index/` is compared with the
one stored after the last finished reconcile. Equal -> no reconcile, read the open ledger items (and the
remembered waiting exact moves, which are not ledger items) so an unchanged tree with an open item still
refuses. Different -> reconcile, raise ledger items, remember the new fingerprint.

The fingerprint lives in the local state dir, not `.index/`: mtimes differ per machine and `.index/` is
tracked, so a stored fingerprint there would diff on every run and be wrong on every other machine.
Blocking: `relink` items and waiting `moved` differences whose card is in `needs`; `orphan` items warn
on stderr and never block (the file is gone, nothing to read).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.indexer.index_card import find_card_by_file_id
from core.indexer.reconcile import reconcile
from core.indexer.reconcile_apply import demote_undone, raise_relink_items_unlocked
from core.indexer.review_envelope import ReviewItem, difference_to_item, relink_item_id

_ROOTS = ("academic_notes", "academic_resources")
_SKIP = {".git", ".obsidian", ".index"}
_OPEN = {"pending_review", "deferred"}
_KIND_TO_TYPE = {"relink": "relink", "orphan_card": "orphan"}
_FILE = "preflight.json"
_PAGE_CMD = "python -m tools.hub_review page --hub-root"


@dataclass(frozen=True)
class Needs:
    """What a pipeline reads. `courses=None` means the whole hub."""
    courses: frozenset[str] | None = None
    file_ids: frozenset[str] = frozenset()


class UnresolvedLinksError(RuntimeError):
    def __init__(self, items: list[ReviewItem], hub_root: str = "<hub>"):
        self.items = items
        moves = sum(1 for i in items if i.type == "moved")
        msg = (f"{len(items)} unresolved link(s) block this run; decide them with "
               f"`{_PAGE_CMD} {hub_root}`")
        if moves:
            msg += (f" ({moves} exact move(s) are waiting: apply them with "
                    f"`python -m tools.hub_review repair --hub-root {hub_root} --apply`)")
        super().__init__(msg)


def tree_fingerprint(hub_root: str) -> str:
    """sha256 over sorted (relpath, size, mtime_ns) of the files under the note/resource roots and the
    hub's own `.index/` (a pull, rebuild or undo can change cards while the notes stay the same)."""
    rows: list[tuple[str, int, int]] = []

    def walk(abs_dir: str, rel: str, skip=_SKIP) -> None:
        try:
            it = list(os.scandir(abs_dir))
        except OSError:
            return
        for e in it:
            if e.name in skip:
                continue
            r = f"{rel}/{e.name}"
            if e.is_dir(follow_symlinks=False):
                walk(e.path, r, skip)
            elif e.is_file():
                st = e.stat()
                rows.append((r, st.st_size, st.st_mtime_ns))

    for root in _ROOTS:
        walk(os.path.join(hub_root, root), root)
    walk(os.path.join(hub_root, ".index"), ".index", {".git"})
    h = hashlib.sha256()
    for row in sorted(rows):
        h.update(repr(row).encode("utf-8"))
    return h.hexdigest()


def _default_store(hub_root: str):
    from tools.corpus_health.state import StateStore, default_state_dir
    return StateStore(default_state_dir(hub_root))


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _course_of(hub_root: str, file_id: str) -> str | None:
    found = find_card_by_file_id(hub_root, file_id)
    return found[1].get("course") if found else None


def _needed(hub_root: str, item: ReviewItem, needs: Needs) -> bool:
    if needs.courses is None:
        return True
    return any(fid in needs.file_ids or _course_of(hub_root, fid) in needs.courses
               for fid in item.subject_ids)


def _ledger_items(store) -> list[ReviewItem]:
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    items = []
    for entry in store.entries(kinds=SELF_REFRESHED_KINDS):
        if entry.get("status") not in _OPEN:
            continue
        finding = entry.get("finding") or {}
        fid = str(finding.get("scope") or "").removeprefix("file_id:")
        items.append(ReviewItem(finding.get("fingerprint") or entry.get("finding_id") or fid,
                                _KIND_TO_TYPE[finding["kind"]], [fid], [], "pending"))
    return items


def _waiting_moves(hub_root: str, differences) -> list[dict]:
    out = []
    for d in demote_undone(hub_root, differences):
        if d.kind == "moved" and d.candidates:
            out.append({"file_id": d.file_id, "old_path": d.old_path, "new_path": d.candidates[0].path})
    return out


def _still_waiting(hub_root: str, move: dict) -> bool:
    """A remembered move stops blocking once its card was repaired (card path no longer the old one)."""
    found = find_card_by_file_id(hub_root, move["file_id"])
    return bool(found) and found[1].get("path") == move["old_path"]


def check(hub_root: str, needs: Needs, store=None) -> list[ReviewItem]:
    """Blocking items for `needs`. Reconciles only when the tree changed since the last finished one."""
    store = store or _default_store(hub_root)
    path = os.path.join(str(store.directory), _FILE)
    fingerprint = tree_fingerprint(hub_root)
    state = _load(path)
    if state.get("fingerprint") != fingerprint:
        with ExitStack() as stack:
            try:
                stack.enter_context(corpus_write_lock([hub_root], "preflight reconcile"))
            except CorpusWriteLockError as exc:
                if "writer already active" not in str(exc):
                    raise
                # Another writer holds the lock: a pure read is still safe, so look at the tree as it is
                # now and write neither the ledger nor preflight.json (the writer owns the state).
                items = _busy_items(hub_root, store, reconcile(hub_root))
                return _blocking(hub_root, items, needs)
            differences = reconcile(hub_root)
            raise_relink_items_unlocked(hub_root, differences, store, mark_link_state=False)
            waiting = _waiting_moves(hub_root, differences)
        state = {"fingerprint": fingerprint, "waiting_moves": waiting}
        _save(path, state)
    items = _ledger_items(store)
    for m in state.get("waiting_moves") or []:
        if _still_waiting(hub_root, m):
            items.append(_moved_item(m["file_id"], m["new_path"]))
    return _blocking(hub_root, items, needs)


def _moved_item(file_id: str, new_path: str) -> ReviewItem:
    return ReviewItem(relink_item_id(file_id, [new_path]), "moved", [file_id],
                      [{"path": new_path, "basis": "exact_move"}], "pending")


def _busy_items(hub_root: str, store, differences) -> list[ReviewItem]:
    """Open items when the write lock is busy: the open ledger entries plus what a fresh reconcile shows
    that the ledger has not closed. Writes nothing."""
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    items = _ledger_items(store)
    seen = {i.item_id for i in items}
    closed = {(e.get("finding") or {}).get("fingerprint") for e in store.entries(kinds=SELF_REFRESHED_KINDS)
              if e.get("status") in {"declined", "accepted", "applied"}}
    for m in _waiting_moves(hub_root, differences):
        item = _moved_item(m["file_id"], m["new_path"])
        if item.item_id not in seen:
            items.append(item)
    for d in demote_undone(hub_root, differences):
        if d.kind == "moved":
            continue
        item = difference_to_item(d)
        if item.item_id not in seen and item.item_id not in closed:
            seen.add(item.item_id)
            items.append(item)
    return items


def _blocking(hub_root: str, items: list[ReviewItem], needs: Needs) -> list[ReviewItem]:
    orphans = [i for i in items if i.type == "orphan" and _needed(hub_root, i, needs)]
    if orphans:
        print(f"warning: {len(orphans)} orphan card(s) (file gone) in scope; not blocking. "
              f"Review: {_PAGE_CMD} {hub_root}", file=sys.stderr)
    return [i for i in items if i.type != "orphan" and _needed(hub_root, i, needs)]


def require_resolved(hub_root: str, needs: Needs, store=None, *, ignore: bool = False) -> None:
    items = check(hub_root, needs, store)
    if not items:
        return
    if ignore:
        print(f"warning: ignoring {len(items)} unresolved link(s); results may use stale paths",
              file=sys.stderr)
        return
    raise UnresolvedLinksError(items, hub_root)


def enforce(hub_root: str, needs: Needs, *, ignore: bool = False, refuse: bool = True) -> None:
    """Entry-point wrapper: exit code 2 with the message on stderr when blocked.

    `refuse=False` (read-only commands) only warns and continues if preflight cannot run. With
    `refuse=True` a preflight that cannot run (lock held, no repo) fails closed (exit 2) unless `ignore`.
    """
    try:
        require_resolved(hub_root, needs, ignore=ignore or not refuse)
    except UnresolvedLinksError as exc:
        if not refuse:
            print(f"warning: {exc}", file=sys.stderr)
            return
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:  # noqa: BLE001
        reason = f"{type(exc).__name__}: {exc}"
        if refuse and not ignore:
            # Fail closed: a concurrent writer or an unresolvable repo is when the check matters most.
            print(f"link preflight could not run ({reason}); refusing. "
                  f"Fix the cause or pass --ignore-unresolved to run anyway.", file=sys.stderr)
            raise SystemExit(2) from exc
        print(f"warning: link preflight skipped ({reason})", file=sys.stderr)
