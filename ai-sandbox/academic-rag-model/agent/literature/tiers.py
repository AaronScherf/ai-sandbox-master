"""Confidence tiers for the facts of a double-extracted paper.

A: both extraction passes found it. B: one pass found it and the checker found support for it in the paper.
C: one pass found it and the checker did not support it, could not settle it, or has not looked yet."""
from __future__ import annotations

from .verify import silver_split

LEGEND = {
    "A": "both independent extraction passes found it",
    "B": "one pass found it and the checker found support for it in the paper's own text",
    "C": "one pass found it and the checker did not support it, could not settle it, or has not looked yet",
}
ORDER = "ABC"
_OF_GROUP = {"agreed": "A", "confirmed": "B", "open": "C"}


def tiered_facts(records, file_id: str, vocabs: dict | None = None) -> list[dict]:
    """Every fact of one paper with its tier; empty until the paper has two extraction passes."""
    split = silver_split(records, file_id, vocabs)
    return [dict(item, tier=tier) for group, tier in _OF_GROUP.items() for item in split[group]]


def at_least(items: list[dict], floor: str) -> list[dict]:
    """Facts at the given tier or better (A is best)."""
    return [i for i in items if ORDER.index(i["tier"]) <= ORDER.index(floor)]
