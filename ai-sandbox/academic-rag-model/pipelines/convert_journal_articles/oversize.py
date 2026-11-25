"""Owner decisions for PDFs over the page limit in the research corpus (a book or monograph is not a paper).

A PDF over THRESHOLD pages that has not been transcribed yet is never converted on its own. It is recorded here as an
open item, the owner decides on a review Artifact, and `apply_decisions` carries the choice out:

- `article`: transcribe it and treat it like a paper (the pipeline lets it through from then on).
- `leave`: keep the PDF where it is, do not transcribe it, and stop warning about it.
- `move`: move the PDF (and its .meta.json) to `<base>/oversize_PDF/`, out of every topic folder.

The ledger is `<index_root>/.index/oversize_review/decisions.json`, keyed by the PDF's path relative to the index root.
"""

import datetime
import json
import os
import shutil
from pathlib import Path

THRESHOLD = 100
OVERSIZE_DIR = "oversize_PDF"
CHOICES = ("article", "leave", "move")


def ledger_path(index_root: str) -> str:
    return os.path.join(index_root, ".index", "oversize_review", "decisions.json")


def load(index_root: str) -> dict[str, dict]:
    try:
        with open(ledger_path(index_root), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(index_root: str, ledger: dict[str, dict]) -> None:
    path = ledger_path(index_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def register(index_root: str, rel_path: str, pages: int) -> dict:
    """Records an oversize PDF as an open item (no choice yet) unless it is already known. Returns its entry."""
    ledger = load(index_root)
    entry = ledger.setdefault(rel_path, {"pages": pages, "choice": None})
    entry["pages"] = pages
    _save(index_root, ledger)
    return entry


def open_items(index_root: str) -> dict[str, dict]:
    return {p: e for p, e in load(index_root).items() if not e.get("choice")}


def choice_for(index_root: str, rel_path: str) -> str | None:
    return load(index_root).get(rel_path, {}).get("choice")


def apply_decisions(index_root: str, decisions: dict[str, str]) -> dict[str, str]:
    """Applies {rel_path: choice}. Returns what happened per path. A move whose destination already exists is
    refused and the item stays open; an unknown choice raises before anything changes."""
    bad = {c for c in decisions.values() if c not in CHOICES}
    if bad:
        raise ValueError(f"unknown choice {sorted(bad)}; use one of {CHOICES}")
    root = Path(index_root)
    ledger = load(index_root)
    result: dict[str, str] = {}
    for rel in decisions:
        resolved = (root / rel).resolve()
        if not rel or not resolved.is_relative_to(root.resolve()) or len(rel.split("/")) < 2:
            raise ValueError(f"path {rel!r} is not inside the corpus folder; nothing was changed")
    for rel, choice in decisions.items():
        entry = ledger.setdefault(rel, {"pages": None, "choice": None})
        if choice == "move":
            base = rel.split("/")[0]
            src = root / rel
            dst = root / base / OVERSIZE_DIR / src.name
            if not src.exists():
                result[rel] = "missing: nothing to move"
                continue
            if dst.exists():
                result[rel] = f"refused: {dst.relative_to(root).as_posix()} already exists"
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            sidecar = src.with_suffix(".meta.json")
            if sidecar.exists():
                shutil.move(str(sidecar), str(dst.with_suffix(".meta.json")))
            entry["moved_to"] = dst.relative_to(root).as_posix()
        entry["choice"] = choice
        entry["at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result[rel] = "moved" if choice == "move" else choice
    _save(index_root, ledger)
    return result
