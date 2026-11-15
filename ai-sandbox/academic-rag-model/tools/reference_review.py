"""Local, metadata-only ledger for reference-checker human review.

The checker-to-ledger selection and decision operations are added in later steps.
This module owns stable IDs, the shared ReviewItem shape, and atomic storage.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from core.indexer.review_envelope import ReviewItem, _digest
from tools.reference_checker import normalized


DEFAULT_STORE = Path(__file__).resolve().parents[1] / ".reference_checker_review"
FILES = {"review": "review.json", "dismissals": "dismissals.json", "defects": "defects.json"}


def item_id(note_rel_path: str, doi: str) -> str:
    """Identify one DOI question in one note, independent of its mentions."""
    return _digest("reference_check", note_rel_path, doi.lower())


def dismissal_key(doi: str, citation: str) -> tuple[str, str]:
    """The same-work decision carries across notes for identical citation text."""
    return doi.lower(), normalized(citation)


def make_item(note_rel_path: str, doi: str, mentions: list[dict], *, tier: str,
              reason: str, evidence: str, record: dict | None = None) -> ReviewItem:
    """Project checker metadata into one shared-envelope review item.

    Only explicit fields are copied, so raw registry responses and note bodies
    cannot enter the ledger through this adapter.
    """
    record = record or {}
    summary = {key: record.get(key) for key in ("title", "authors", "year", "venue")}
    cited = [{"line": mention["line"], "cited_text": mention["cited_text"],
              "normalized_citation": normalized(mention["cited_text"])} for mention in mentions]
    return ReviewItem(
        item_id(note_rel_path, doi), "reference_check", [note_rel_path, doi],
        [{"registry": summary, "mentions": cited, "tier": tier,
          "reason": reason, "evidence": evidence}],
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
