"""Local, metadata-only ledger for reference-checker human review.

This module owns selection, stable IDs, decisions, the shared ReviewItem shape,
atomic storage, and its command-line entry point.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core.indexer.review_envelope import ReviewItem, _digest
from tools.reference_checker import RegistryClient, TIER_RANK, check_note, normalized


DEFAULT_STORE = Path(__file__).resolve().parents[1] / ".reference_checker_review"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
FILES = {"review": "review.json", "dismissals": "dismissals.json", "defects": "defects.json",
         "false_positives": "false_positives.json"}
REVIEW_TIERS = {"REVIEW", "AMBIGUOUS", "PLAUSIBLE", "UNCHECKED", "UNRESOLVED"}
DEFECT_TIERS = {"WRONG_WORK", "NOT_FOUND"}


def item_id(note_rel_path: str, doi: str) -> str:
    """Identify one DOI question in one note, independent of its mentions."""
    return _digest("reference_check", note_rel_path, doi.lower())


def dismissal_key(doi: str, citation: str) -> tuple[str, str]:
    """The same-work decision carries across notes for identical citation text."""
    return doi.lower(), normalized(citation)


def make_item(note_rel_path: str, doi: str, mentions: list[dict], *, tier: str,
              reason: str, evidence: str, record: dict | None = None,
              siblings: list[dict] | None = None) -> ReviewItem:
    """Project checker metadata into one shared-envelope review item.

    Only explicit fields are copied, so raw registry responses and note bodies
    cannot enter the ledger through this adapter.
    """
    record = record or {}
    summary = {key: record.get(key) for key in ("title", "authors", "year", "venue")}
    cited = [{"line": mention["line"], "cited_text": mention["cited_text"],
              "normalized_citation": normalized(mention["cited_text"])} for mention in mentions]
    candidate = {"registry": summary, "mentions": cited, "tier": tier,
                 "reason": reason, "evidence": evidence}
    if siblings:
        candidate["siblings"] = [{key: sibling.get(key) for key in ("doi", "title", "year", "type")}
                                 for sibling in siblings[:5]]
    return ReviewItem(
        item_id(note_rel_path, doi), "reference_check", [note_rel_path, doi],
        [candidate],
    )


def _path(kind: str, store: Path) -> Path:
    return store / FILES[kind]


def _load(kind: str, store: Path) -> list[dict]:
    path = _path(kind, store)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"{path} must contain a JSON list of objects")
    return data


def _save(kind: str, entries: list[dict], store: Path) -> None:
    """Replace a complete ledger file only after its new JSON is on disk."""
    path = _path(kind, store)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         suffix=".tmp", dir=path.parent, delete=False) as temp:
            temp_path = Path(temp.name)
            json.dump(entries, temp, indent=2, ensure_ascii=False)
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_review(store: Path = DEFAULT_STORE) -> list[ReviewItem]:
    return [ReviewItem.from_dict(row) for row in _load("review", Path(store))]


def save_review(items: list[ReviewItem], store: Path = DEFAULT_STORE) -> None:
    _save("review", [item.to_dict() for item in items], Path(store))


def load_dismissals(store: Path = DEFAULT_STORE) -> list[dict]:
    return _load("dismissals", Path(store))


def save_dismissals(entries: list[dict], store: Path = DEFAULT_STORE) -> None:
    _save("dismissals", entries, Path(store))


def load_defects(store: Path = DEFAULT_STORE) -> list[dict]:
    return _load("defects", Path(store))


def save_defects(entries: list[dict], store: Path = DEFAULT_STORE) -> None:
    _save("defects", entries, Path(store))


def load_false_positives(store: Path = DEFAULT_STORE) -> list[dict]:
    return _load("false_positives", Path(store))


def save_false_positives(entries: list[dict], store: Path = DEFAULT_STORE) -> None:
    _save("false_positives", entries, Path(store))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _note_path(path: str | Path, repo_root: Path) -> tuple[Path, str]:
    resolved = Path(path).resolve()
    relative = resolved.relative_to(repo_root.resolve())
    return resolved, relative.as_posix()


def _selected(note_rel_path: str, rows: list[dict], dismissed: set[tuple[str, str]]) -> tuple[list[ReviewItem], list[dict]]:
    """Group DOI mentions and route the worst tier to review or defects."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        doi = str(row.get("identifier") or "")
        if doi.lower().startswith("10."):
            groups.setdefault(doi.lower(), []).append(row)
    items, defects = [], []
    for doi, mentions in groups.items():
        worst = max(mentions, key=lambda row: (TIER_RANK.get(row.get("tier"), TIER_RANK["UNRESOLVED"]),
                                               bool(row.get("siblings"))))
        tier = worst.get("tier", "UNRESOLVED")
        cited = [{"line": row.get("line"), "cited_text": row["citation"]} for row in mentions]
        if tier in DEFECT_TIERS:
            defects.append({"note": note_rel_path, "doi": doi, "tier": tier,
                            "reason": worst.get("reason", ""), "mentions": cited,
                            "source": "checker"})
        elif tier in REVIEW_TIERS and not all(dismissal_key(doi, row["citation"]) in dismissed for row in mentions):
            answer = worst.get("registry_answer") or {}
            siblings = []
            seen_siblings = set()
            for row in mentions:
                for sibling in row.get("siblings") or []:
                    sibling_doi = str(sibling.get("doi") or "").lower()
                    if sibling_doi and sibling_doi not in seen_siblings:
                        seen_siblings.add(sibling_doi)
                        siblings.append(sibling)
            items.append(make_item(note_rel_path, doi, cited, tier=tier,
                                   reason=("checker could not judge" if tier in {"UNCHECKED", "UNRESOLVED"}
                                           else worst.get("reason", "")),
                                   evidence=worst.get("evidence", ""),
                                   record=answer.get("record"), siblings=siblings))
    return items, defects


def raise_items(note_paths: list[str | Path], client, *, store: Path = DEFAULT_STORE,
                repo_root: Path = DEFAULT_REPO_ROOT) -> list[ReviewItem]:
    """Check notes, upsert their open DOI questions, and refresh checker defects.

    Only files beneath ``repo_root`` are accepted. Each scanned note replaces
    its old checker findings; unrelated notes and human defects are retained.
    """
    store, repo_root = Path(store), Path(repo_root)
    existing = {item.item_id: item for item in load_review(store)}
    defects = load_defects(store)
    dismissed = {(entry.get("doi"), entry.get("normalized_citation"))
                 for entry in load_dismissals(store)}
    scanned: set[str] = set()
    raised: list[ReviewItem] = []
    now = _now()
    for path in note_paths:
        absolute, relative = _note_path(path, repo_root)
        if relative in scanned:
            continue
        scanned.add(relative)
        rows = check_note(absolute.read_text(encoding="utf-8"), client)
        current, found_defects = _selected(relative, rows, dismissed)
        current_citations = {}
        for row in rows:
            doi = str(row.get("identifier") or "").lower()
            if doi.startswith("10."):
                current_citations.setdefault(doi, set()).add(normalized(row["citation"]))
        defects = [d for d in defects if not (
            d.get("note") == relative and (
                d.get("source") == "checker" or
                (d.get("source") == "human" and
                 {normalized(m["cited_text"]) for m in d.get("mentions", [])}
                 != current_citations.get(d.get("doi"), set()))))]
        defects.extend(found_defects)
        current_ids = {item.item_id for item in current}
        existing = {iid: item for iid, item in existing.items()
                    if item.subject_ids[0] != relative or iid in current_ids}
        for item in current:
            prior = existing.get(item.item_id)
            if prior:
                item.created = prior.created
                item.updated = prior.updated
                if prior.candidates == item.candidates:
                    item.status = prior.status
                else:
                    item.updated = now
            else:
                item.created = item.updated = now
            existing[item.item_id] = item
            if item.status in {"pending", "deferred"}:
                raised.append(item)
    if scanned:
        save_review(sorted(existing.values(), key=lambda item: item.item_id), store)
        save_defects(sorted(defects, key=lambda d: (d.get("note", ""), d.get("doi", ""), d.get("source", ""))), store)
    return raised


def _find_open(item_id: str, store: Path) -> tuple[list[ReviewItem], ReviewItem | None]:
    items = load_review(store)
    item = next((i for i in items if i.item_id == item_id), None)
    return items, item


def _mention_keys(item: ReviewItem) -> set[tuple[str, str]]:
    doi = item.subject_ids[1]
    return {dismissal_key(doi, mention["cited_text"])
            for mention in item.candidates[0]["mentions"]}


def is_human_confirmed(doi: str, citation: str, *, store: Path = DEFAULT_STORE) -> bool:
    """Read-only later-gate hook; not wired to any checker or pipeline."""
    wanted = dismissal_key(doi, citation)
    return wanted in {(entry.get("doi"), entry.get("normalized_citation"))
                      for entry in load_dismissals(store)}


def resolve(item_id: str, *, store: Path = DEFAULT_STORE) -> bool:
    """Accept same-work and dismiss every mention key, including across notes."""
    store = Path(store)
    items, item = _find_open(item_id, store)
    if item is None or item.status not in {"pending", "deferred", "accepted"}:
        return False
    existing = load_dismissals(store)
    known = {(entry.get("doi"), entry.get("normalized_citation")) for entry in existing}
    now = _now()
    added = False
    for doi, citation in sorted(_mention_keys(item)):
        if (doi, citation) not in known:
            existing.append({"doi": doi, "normalized_citation": citation,
                             "item_id": item_id, "decided_at": now})
            added = True
    if added:
        save_dismissals(existing, store)
    dismissed = {(entry.get("doi"), entry.get("normalized_citation")) for entry in existing}
    changed = False
    for candidate in items:
        if candidate.status in {"pending", "deferred"} and _mention_keys(candidate) <= dismissed:
            candidate.status = "accepted"
            candidate.updated = now
            changed = True
    if changed:
        save_review(items, store)
    return True


def reject(item_id: str, reason: str, *, store: Path = DEFAULT_STORE) -> bool:
    """Decline one note's item as wrong work or an extraction false positive."""
    if reason not in {"wrong_work", "not_citation"}:
        raise ValueError("reason must be wrong_work or not_citation")
    store = Path(store)
    items, item = _find_open(item_id, store)
    if item is None or item.status not in {"pending", "deferred", "declined"}:
        return False
    note, doi = item.subject_ids
    mentions = [{"line": m["line"], "cited_text": m["cited_text"]}
                for m in item.candidates[0]["mentions"]]
    if item.status == "declined":
        if reason == "wrong_work":
            return any(d.get("note") == note and d.get("doi") == doi.lower()
                       and d.get("source") == "human" and d.get("mentions") == mentions
                       for d in load_defects(store))
        return any(row.get("item_id") == item_id and row.get("mentions") == mentions
                   for row in load_false_positives(store))
    now = _now()
    if reason == "wrong_work":
        defects = load_defects(store)
        entry = {"note": note, "doi": doi.lower(), "tier": "WRONG_WORK",
                 "reason": "human reviewer: wrong work", "mentions": mentions,
                 "source": "human"}
        defects = [d for d in defects if not (d.get("note"), d.get("doi"), d.get("source"))
                   == (note, doi.lower(), "human")]
        defects.append(entry)
        save_defects(defects, store)
    else:
        false_positives = load_false_positives(store)
        if not any(row.get("item_id") == item_id and row.get("mentions") == mentions
                   for row in false_positives):
            false_positives.append({"item_id": item_id, "note": note, "doi": doi.lower(),
                                    "mentions": mentions, "recorded_at": now})
            save_false_positives(false_positives, store)
    if item.status != "declined":
        item.status = "declined"
        item.updated = now
        save_review(items, store)
    return True


def defer(item_id: str, *, store: Path = DEFAULT_STORE) -> bool:
    """Keep an unresolved question available on the next raise."""
    items, item = _find_open(item_id, Path(store))
    if item is None or item.status not in {"pending", "deferred"}:
        return False
    if item.status == "pending":
        item.status = "deferred"
        item.updated = _now()
        save_review(items, Path(store))
    return True


def apply_decisions(decisions: list, *, dry_run: bool = False,
                    store: Path = DEFAULT_STORE) -> list[dict]:
    """Apply hub-review-shaped records; report bad records without stopping the batch."""
    results, seen = [], set()
    for decision in decisions:
        iid = decision.get("item_id") if isinstance(decision, dict) else None
        action = decision.get("action") if isinstance(decision, dict) else None
        chosen = decision.get("chosen") if isinstance(decision, dict) else None
        result = {"item_id": iid, "type": "reference_check", "action": action}
        try:
            if not isinstance(iid, str) or action not in {"accept", "decline", "defer"}:
                result.update(outcome="error", detail="malformed decision")
            elif iid in seen:
                result.update(outcome="stale", detail="duplicate decision in batch")
            elif action == "decline" and chosen not in {"wrong_work", "not_citation"}:
                result.update(outcome="error", detail="decline needs chosen: wrong_work or not_citation")
            else:
                item = next((item for item in load_review(store) if item.item_id == iid), None)
                if item is None:
                    result.update(outcome="stale", detail="unknown item_id")
                elif item.status == "accepted" and action == "accept":
                    result.update(outcome="already_applied", detail="already accepted")
                elif item.status == "declined" and action == "decline" and reject_reason_matches(item, chosen, store):
                    result.update(outcome="already_applied", detail="already declined")
                elif item.status not in {"pending", "deferred"}:
                    result.update(outcome="stale", detail=f"item is {item.status}")
                elif dry_run:
                    result.update(outcome="would_apply", detail=action if action != "decline" else chosen)
                else:
                    ok = (resolve(iid, store=store) if action == "accept" else
                          reject(iid, chosen, store=store) if action == "decline" else
                          defer(iid, store=store))
                    result.update(outcome="applied" if ok else "stale",
                                  detail=action if action != "decline" else chosen)
                if result["outcome"] not in {"error", "stale"}:
                    seen.add(iid)
        except Exception as exc:
            result.update(outcome="error", detail=f"{type(exc).__name__}: {exc}")
        results.append(result)
    return results


def reject_reason_matches(item: ReviewItem, reason: str, store: Path) -> bool:
    """Check a declined item's recorded reason without causing a write."""
    note, doi = item.subject_ids
    mentions = [{"line": m["line"], "cited_text": m["cited_text"]}
                for m in item.candidates[0]["mentions"]]
    if reason == "wrong_work":
        return any(d.get("note") == note and d.get("doi") == doi.lower()
                   and d.get("source") == "human" and d.get("mentions") == mentions
                   for d in load_defects(store))
    if reason == "not_citation":
        return any(row.get("item_id") == item.item_id and row.get("mentions") == mentions
                   for row in load_false_positives(store))
    return False


def list_items(status: str = "open", *, store: Path = DEFAULT_STORE) -> list[ReviewItem]:
    """Read-only view; open includes deferred questions."""
    items = load_review(store)
    if status == "all":
        return items
    if status == "open":
        return [item for item in items if item.status in {"pending", "deferred"}]
    return [item for item in items if item.status == status]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.reference_review")
    sub = parser.add_subparsers(dest="command", required=True)
    raising = sub.add_parser("raise", help="check notes and update the local review ledger")
    raising.add_argument("notes", nargs="+", type=Path)
    raising.add_argument("--offline", action="store_true", help="read cached registry answers only")
    raising.add_argument("--cache", type=Path, default=Path(__file__).resolve().parents[1] / ".reference_checker_cache")
    listing = sub.add_parser("list", help="print stored review items without writing")
    listing.add_argument("--status", choices=("open", "pending", "deferred", "accepted", "declined", "all"),
                         default="open")
    applying = sub.add_parser("apply", help="apply a JSON list of review decisions")
    applying.add_argument("decisions", type=Path)
    applying.add_argument("--dry-run", action="store_true", help="report actions without writing")
    args = parser.parse_args(argv)
    try:
        if args.command == "raise":
            client = RegistryClient(args.cache, online=not args.offline)
            items = raise_items(args.notes, client, store=DEFAULT_STORE, repo_root=DEFAULT_REPO_ROOT)
            requested = {_note_path(path, DEFAULT_REPO_ROOT)[1] for path in args.notes}
            defects = [d for d in load_defects(DEFAULT_STORE) if d.get("note") in requested]
            payload = {"items": [item.to_dict() for item in items], "defects": defects}
        elif args.command == "list":
            payload = [item.to_dict() for item in list_items(args.status, store=DEFAULT_STORE)]
        else:
            decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
            if not isinstance(decisions, list):
                raise ValueError("decisions file must be a JSON list")
            payload = apply_decisions(decisions, dry_run=args.dry_run, store=DEFAULT_STORE)
    except (OSError, ValueError) as exc:
        print(f"reference review: {exc}", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
