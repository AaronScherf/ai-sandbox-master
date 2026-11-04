"""Shared hub review page: export pending items, build the page, apply recorded decisions, and run
or undo exact-move repairs (hub-path-resilience P3, Task 6 + final wave).

    python -m tools.hub_review export --hub-root HUB [--out PATH] [--no-raise]
    python -m tools.hub_review page --hub-root HUB [--out PATH] [--no-raise]
    python -m tools.hub_review apply DECISIONS.json --hub-root HUB [--dry-run]
    python -m tools.hub_review repair --hub-root HUB [--apply]
    python -m tools.hub_review undo REPAIR_ID --hub-root HUB
    (--hub-root is required and goes AFTER the subcommand; before it, it is rejected)

`repair` lists the exact (`moved`) differences reconcile found; with `--apply` it applies them through
`reconcile_apply.apply_repairs` (one corpus-lock hold, logged in `.index/reconcile_log.jsonl`) and
prints each repair_id. `undo REPAIR_ID` reverts one (`reconcile_apply.undo_repair`; exit 1 if refused);
an undone move is never auto-applied again but is offered on the review page instead. `export`/`page`
never apply moves: when some are waiting they print a one-line note to stderr.

WRITES: plain `export` and `page` first run `reconcile_apply.raise_relink_items`, which takes the corpus
write lock, runs a full reconcile, upserts relink/orphan findings in the corpus-health ledger and sets
`link_state` on cards with an open relink (the ledger must hold an item before it can be resolved). Use
`--no-raise` for a pure read: items come from a fresh reconcile minus what the ledger already closed,
plus the offering/pairing review files; nothing is written. Deferred relink/orphan items stay listed
(status "deferred") until decided. `apply --dry-run` is also write-free.

One page, separate ledgers: relink/orphan items live in the corpus-health ledger, offering links and
document pairings in their own review.json files; each decision is applied through the owning module's
resolve/reject. The tool never talks to the Artifact service. Flow: `page` bakes the pending items into
a self-contained HTML page; the controller publishes it with a `db` capability; viewers write one doc per
item into its `decisions` collection (`{item_id, action: accept|decline|defer, chosen, ts}`, doc id =
item_id); the controller dumps that collection to a JSON list and runs `apply`.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.indexer import document_pairing, offering_links, reconcile_apply
from core.indexer.index_card import find_card_by_file_id
from core.indexer.reconcile import reconcile
from core.indexer.review_envelope import (
    ReviewItem, difference_to_item, offering_link_to_item, pairing_to_item,
)

PAGE_TEMPLATE = Path(__file__).with_name("hub_review_page.html")
ACTIONS = {"accept", "decline", "defer"}
_CLOSED = {"declined", "accepted", "applied", "vanished"}


def _default_store(hub_root: str):
    return reconcile_apply._default_store(hub_root)


def _pending_moves(hub_root: str, differences) -> list:
    """The exact moves `repair --apply` would apply (undone moves excluded: they are review items)."""
    return [d for d in reconcile_apply.demote_undone(hub_root, differences) if d.kind == "moved"]


def _pending_relink(hub_root: str, store, raise_items: bool, moves_out: list | None = None) -> list[ReviewItem]:
    differences = reconcile(hub_root)
    if moves_out is not None:
        moves_out.extend(_pending_moves(hub_root, differences))
    if raise_items:
        return [i for i in reconcile_apply.raise_relink_items(hub_root, differences, store=store)
                if i.status in ("pending", "deferred")]
    # read only (dry run): derive from reconcile and drop what the ledger already closed
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    entries = store.entries(kinds=SELF_REFRESHED_KINDS)
    closed = {e.get("finding", {}).get("fingerprint") for e in entries if e.get("status") in _CLOSED}
    deferred = {e.get("finding", {}).get("fingerprint") for e in entries if e.get("status") == "deferred"}
    items = [difference_to_item(d) for d in reconcile_apply.demote_undone(hub_root, differences)
             if d.kind != "moved"]
    items = [i for i in items if i.item_id not in closed]
    for i in items:
        if i.item_id in deferred:
            i.status = "deferred"
    return items


def collect(hub_root: str, store=None, raise_items: bool = True, moves_out: list | None = None) -> list[ReviewItem]:
    """Open (pending or deferred) items from the three ledgers, sorted by (type, item_id).
    `raise_items=True` writes the ledger and card link_state (see module docstring); False writes nothing.
    `moves_out`, if given, receives the pending exact moves (`repair` applies them; they are not items)."""
    store = store or _default_store(hub_root)
    items = _pending_relink(hub_root, store, raise_items, moves_out)
    items += [offering_link_to_item(e, hub_root) for e in offering_links.load_review(hub_root)]
    items += [pairing_to_item(e, hub_root) for e in document_pairing.load_review(hub_root)]
    return sorted(items, key=lambda i: (i.type, i.item_id))


def _card_path(hub_root: str, file_id: str):
    found = find_card_by_file_id(hub_root, file_id)
    return found[1].get("path") if found else None


def _exported(hub_root: str, item: ReviewItem) -> dict:
    d = item.to_dict()
    d.pop("updated", None)  # ledger last_seen changes on every raise; keeps export deterministic
    d["subject_paths"] = [_card_path(hub_root, fid) for fid in item.subject_ids]
    return d


def export(hub_root: str, store=None, raise_items: bool = True, moves_out: list | None = None) -> dict:
    items = collect(hub_root, store, raise_items, moves_out)
    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hub_root": hub_root,
            "items": [_exported(hub_root, i) for i in items]}


def render_page(payload: dict) -> str:
    # '<' escaped so neither </script> nor <!-- can occur inside the embedded JSON; U+2028/9 for old parsers
    payload = {k: v for k, v in payload.items() if k != "hub_root"}  # no absolute local paths in the page
    blob = (json.dumps(payload, sort_keys=True).replace("<", "\\u003c")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    return PAGE_TEMPLATE.read_text(encoding="utf-8").replace("__REVIEW_ITEMS__", blob)


def _defer_in_ledger(store, item: ReviewItem) -> bool:
    from tools.corpus_health.state import SELF_REFRESHED_KINDS
    for e in store.entries(kinds=SELF_REFRESHED_KINDS):
        fp = e.get("finding", {}).get("fingerprint")
        if fp != item.item_id:
            continue
        if e.get("status") == "deferred":
            return True  # idempotent
        if e.get("status") == "pending_review":
            store.decide(e["finding_id"], "deferred", fp)
            return True
    return False


def _dispatch(hub_root: str, item: ReviewItem, action: str, chosen, store, dry_run: bool) -> tuple[str, str]:
    """-> (outcome, detail). Raises nothing the caller must not catch."""
    t = item.type
    if t in ("relink", "orphan"):
        fid = item.subject_ids[0]
        if action == "accept":
            if t == "orphan":
                return "error", "orphan items are report only; decline to dismiss"
            if chosen not in [c["path"] for c in item.candidates]:
                return "error", "accept needs a chosen path that is one of the candidates"
            if dry_run:
                return "would_apply", f"relink {fid} -> {chosen}"
            ok = reconcile_apply.resolve(hub_root, fid, chosen, store=store)
            return ("applied", f"relinked {fid} -> {chosen}") if ok else ("error", "resolve refused")
        if action == "decline":
            if dry_run:
                return "would_apply", f"dismiss {fid}"
            ok = reconcile_apply.reject(hub_root, fid, store=store)
            return ("applied", f"dismissed {fid}") if ok else ("error", "reject found no item")
        if dry_run:
            return "would_apply", f"defer {fid}"
        return ("deferred", "deferred in ledger") if _defer_in_ledger(store, item) else ("error", "no open ledger entry")
    mod = offering_links if t == "offering_link" else document_pairing
    a, b = item.subject_ids
    if action == "defer":
        return ("would_apply", "no-op (stays in review.json)") if dry_run else ("noop", "stays in review.json")
    if dry_run:
        return "would_apply", f"{action} {t} {a} / {b}"
    ok = mod.resolve_pending(hub_root, a, b) if action == "accept" else mod.reject_pending(hub_root, a, b)
    return ("applied", f"{action}ed") if ok else ("error", f"{mod.__name__.rsplit('.', 1)[-1]} refused")


def apply_decisions(hub_root: str, decisions: list, dry_run: bool = False, store=None) -> list[dict]:
    """Dispatch each decision to its owning module. Never raises for a single decision."""
    store = store or _default_store(hub_root)
    current = {i.item_id: i for i in collect(hub_root, store, raise_items=not dry_run)}
    results, seen = [], set()
    for dec in decisions:
        iid = dec.get("item_id") if isinstance(dec, dict) else None
        action = dec.get("action") if isinstance(dec, dict) else None
        res = {"item_id": iid, "type": None, "action": action}
        try:
            if not isinstance(iid, str) or action not in ACTIONS:
                res.update(outcome="error", detail="malformed decision")
            elif iid in seen:
                res.update(outcome="stale", detail="duplicate decision for this item; ignored")
            elif iid not in current:
                res.update(outcome="stale", detail="no such pending item")
            else:
                item = current[iid]
                res["type"] = item.type
                outcome, detail = _dispatch(hub_root, item, action, dec.get("chosen"), store, dry_run)
                res.update(outcome=outcome, detail=detail)
                if outcome != "error":
                    seen.add(iid)  # a failed attempt may be retried by a later decision
        except Exception as exc:  # one bad decision never aborts the rest
            res.update(outcome="error", detail=f"{type(exc).__name__}: {exc}")
        results.append(res)
    return results


def repair(hub_root: str, apply: bool = False) -> int:
    """List (dry run) or apply the pending exact moves. Prints one line per move/repair and a summary."""
    moves = _pending_moves(hub_root, reconcile(hub_root))
    if not apply:
        for d in moves:
            print(f"would move {d.file_id}: {d.old_path} -> {d.candidates[0].path}  ({d.evidence})")
        print(f"dry run: {len(moves)} exact move(s) would be applied; rerun with --apply")
        return 0
    records = reconcile_apply.apply_repairs(hub_root, moves)
    for r in records:
        print(f"repaired {r.repair_id} {r.file_id}: {r.old} -> {r.new}")
    skipped = len(moves) - len(records)
    print(f"{len(records)} repair(s) applied" + (f", {skipped} skipped (card or target changed)" if skipped else "")
          + "; undo one with: python -m tools.hub_review undo REPAIR_ID --hub-root HUB")
    return 0


def undo(hub_root: str, repair_id: str) -> int:
    if reconcile_apply.undo_repair(hub_root, repair_id):
        print(f"undone {repair_id}; this move will be offered on the review page, not re-applied")
        return 0
    print(f"cannot undo {repair_id}: unknown id, not a completed repair, already undone, "
          f"or the card has moved since", file=sys.stderr)
    return 1


def _note_moves(moves: list) -> None:
    if moves:
        print(f"{len(moves)} exact moves are waiting: run `repair`", file=sys.stderr)


def _write(text: str, out: str | None) -> None:
    if out:
        Path(out).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tools.hub_review")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hub-root", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    helps = {"export": "write the pending items as JSON. WRITES the ledger and card link_state unless --no-raise",
             "page": "write the review page. WRITES the ledger and card link_state unless --no-raise"}
    for name in ("export", "page"):
        sp = sub.add_parser(name, parents=[common], help=helps[name], description=helps[name])
        sp.add_argument("--out")
        sp.add_argument("--no-raise", action="store_true", help="read only: do not raise relink items into the ledger")
    ap = sub.add_parser("apply", parents=[common])
    ap.add_argument("decisions")
    ap.add_argument("--dry-run", action="store_true")
    rp = sub.add_parser("repair", parents=[common],
                        help="list exact moves; --apply applies them (logged, undoable)")
    rp.add_argument("--apply", action="store_true", help="apply the moves (takes the corpus write lock)")
    up = sub.add_parser("undo", parents=[common], help="undo one repair by its repair_id")
    up.add_argument("repair_id")
    args = p.parse_args(argv)
    if args.cmd == "repair":
        return repair(args.hub_root, apply=args.apply)
    if args.cmd == "undo":
        return undo(args.hub_root, args.repair_id)
    if args.cmd in ("export", "page"):
        moves: list = []
        payload = export(args.hub_root, raise_items=not args.no_raise, moves_out=moves)
        _write(json.dumps(payload, indent=2, sort_keys=True) if args.cmd == "export" else render_page(payload),
               args.out)
        _note_moves(moves)
        return 0
    try:
        decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
        if not isinstance(decisions, list):
            raise ValueError("decisions file must be a JSON list")
    except (OSError, ValueError) as exc:
        print(f"cannot read decisions: {exc}", file=sys.stderr)
        return 2
    results = apply_decisions(args.hub_root, decisions, dry_run=args.dry_run)
    for r in results:
        print(f"{r['outcome']:<11} {str(r['type'] or '-'):<17} {str(r['action']):<8} {r['item_id']}  {r.get('detail', '')}")
    counts: dict[str, int] = {}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    print(("dry run: " if args.dry_run else "") + f"{len(results)} decisions; "
          + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
