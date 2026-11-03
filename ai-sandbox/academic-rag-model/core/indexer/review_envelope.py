"""Shared review-item envelope (hub-path-resilience P3, Task 5). PURE: no I/O, no writes.

One shape for the three human-decision ledgers so a single review page can list them all, while each
item is still applied through its own ledger's resolve/reject (spec: "Combining the review queues:
one page, separate ledgers"; no storage merge):

| type               | from                                  | applied by                                   |
|--------------------|---------------------------------------|----------------------------------------------|
| `relink`           | ambiguous reconcile `Difference`      | `reconcile_apply.resolve` / `reject`         |
| `orphan`           | orphan reconcile `Difference`         | report only: `reconcile_apply.reject` (resolve refuses) |
| `offering_link`    | `.index/offering_links/review.json`   | `offering_links.resolve_pending` / `reject_pending` |
| `document_pairing` | the document_pairing review.json      | `document_pairing.resolve_pending` / `reject_pending` |

`item_id` is deterministic. relink/orphan: sha256(file_id + sorted candidate paths), so the same
question asked twice is the same item, and a changed candidate set is a new question. Pair ledgers:
sha256(type + sorted pair of file ids).

The ledger side effects (corpus-health findings, the card's `link_state`) live in
`core/indexer/reconcile_apply.py` (`raise_relink_items`, `resolve`, `reject`).
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Literal

from core.indexer.reconcile import Difference

Status = Literal["pending", "accepted", "declined", "deferred"]
UNRESOLVED = "unresolved"


@dataclass
class ReviewItem:
    item_id: str
    type: str
    subject_ids: list[str]
    candidates: list[dict] = field(default_factory=list)
    status: Status = "pending"
    created: str = ""
    updated: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewItem":
        return cls(
            item_id=data["item_id"], type=data["type"], subject_ids=list(data.get("subject_ids") or []),
            candidates=[dict(c) for c in data.get("candidates") or []], status=data.get("status", "pending"),
            created=data.get("created", ""), updated=data.get("updated", ""),
        )


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]


def relink_item_id(file_id: str, candidate_paths: list[str]) -> str:
    return _digest(file_id, *sorted(candidate_paths))


def difference_to_item(d: Difference) -> ReviewItem:
    """`ambiguous` -> type `relink` (candidates ranked as given); `orphan` -> type `orphan` (report
    only, no candidates). `moved` is applied automatically and is never an item: ValueError.
    created/updated are left empty; `raise_relink_items` fills them from the ledger."""
    if d.kind == "moved":
        raise ValueError(f"a moved difference is not a review item ({d.file_id})")
    if d.kind == "ambiguous":
        candidates = [{"path": c.path, "basis": c.basis, "score": c.score} for c in d.candidates]
        return ReviewItem(relink_item_id(d.file_id, [c.path for c in d.candidates]), "relink",
                          [d.file_id], candidates)
    if d.kind == "orphan":
        return ReviewItem(relink_item_id(d.file_id, []), "orphan", [d.file_id], [])
    raise ValueError(f"unknown difference kind {d.kind!r}")


def _pair_item(kind: str, entry: dict, basis: str, score) -> ReviewItem:
    a, b = entry["file_id_a"], entry["file_id_b"]
    return ReviewItem(
        _digest(kind, *sorted([a, b])), kind, [a, b],
        [{"path": entry.get("path_b"), "file_id": b, "basis": basis, "score": score}],
        "pending", entry.get("created", ""), entry.get("updated", ""),
    )


def offering_link_to_item(entry: dict) -> ReviewItem:
    """An `offering_links` review.json entry ({file_id_a, file_id_b, similarity, course}). Read only:
    entries in review.json are pending by construction (resolved/rejected ones are removed)."""
    return _pair_item("offering_link", entry, "embedding_similarity", entry.get("similarity"))


def pairing_to_item(entry: dict) -> ReviewItem:
    """A `document_pairing` review.json entry ({file_id_a, file_id_b, pair_type, course}). Read only."""
    return _pair_item("document_pairing", entry, entry.get("pair_type") or "document_pairing", None)


def is_unresolved(card: dict) -> bool:
    """True while the card has an open relink item: consumers must not use it as a link/pair
    candidate (spec section 4: "Consumers refuse to use the unresolved link")."""
    return card.get("link_state") == UNRESOLVED
