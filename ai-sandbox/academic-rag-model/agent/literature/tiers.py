"""Confidence tiers for the facts of a double-extracted paper.

A: both extraction passes found it. B: one pass found it and the checker found support for it in the paper.
C: one pass found it and the checker did not support it, could not settle it, or has not looked yet."""
from __future__ import annotations

from . import schema
from .verify import silver_split

LEGEND = {
    "A": "both independent extraction passes found it",
    "B": "one pass found it and the checker found support for it in the paper's own text",
    "C": "one pass found it and the checker did not support it, could not settle it, or has not looked yet",
}
ORDER = "ABC"
_OF_GROUP = {"agreed": "A", "confirmed": "B", "open": "C"}


def _rejected(item: dict, file_id: str, rejected_keys: set) -> bool:
    shown = item["shown"]
    if not shown.startswith("proposed:"):
        return False
    vocab_name = schema.FACETS.get(item["facet"], item["facet"])
    return (file_id, vocab_name, shown.removeprefix("proposed:")) in rejected_keys


def tiered_facts(records, file_id: str, vocabs: dict | None = None, proposals=None) -> list[dict]:
    """Every fact of one paper with its tier; empty until the paper has two extraction passes. A fact whose free-text
    value was already proposed and rejected (a human decided it is not a real taxonomy concept, not just a gap) is
    dropped rather than shown as if it were a normal fact -- pass `proposals` (a Proposals) so that decision takes
    effect here instead of only in the proposals ledger."""
    split = silver_split(records, file_id, vocabs)
    items = [dict(item, tier=tier) for group, tier in _OF_GROUP.items() for item in split[group]]
    if proposals is None:
        return items
    rejected_keys = proposals.rejected_keys()
    return [i for i in items if not _rejected(i, file_id, rejected_keys)]


def at_least(items: list[dict], floor: str) -> list[dict]:
    """Facts at the given tier or better (A is best)."""
    return [i for i in items if ORDER.index(i["tier"]) <= ORDER.index(floor)]
