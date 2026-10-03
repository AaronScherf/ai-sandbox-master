"""
offering_links.py
Finds likely corollaries between a course's marked prior offerings (Phase 1's
.notes_subset.json subsets -- see pipelines/transcribe_notes/README.md) and
its other content -- a reused slide deck, a problem set covering the same
material a different year -- using each card's existing title+summary
embedding, the same cosine-similarity-against-a-threshold shape
core/indexer/retag.py already uses for tag clustering, and the same
confidence-tiered dismissals-ledger pattern core/indexer/duplicate_check.py
already uses for fuzzy textbook matches. Deliberately separate from
index_card.py/transcribe_notes.py -- this is a corpus-wide, course-at-a-time
pass on its own explicit schedule, never per-file.

Spec: docs/superpowers/specs/indexer/2026-10-03-cross-offering-linkage-design.md
"""
from __future__ import annotations

import json
import os

from core.env.academic_hub_paths import find_containing_offering_label, to_resources_root
from core.indexer.index_card import now_iso

OFFERING_LINK_AUTO_THRESHOLD = 0.90  # starting guess -- calibrate against real data (Task 4)
OFFERING_LINK_REVIEW_THRESHOLD = 0.80  # starting guess -- calibrate against real data (Task 4)


def _links_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "offering_links")


def _review_path(academic_hub_root: str) -> str:
    return os.path.join(_links_dir(academic_hub_root), "review.json")


def _dismissals_path(academic_hub_root: str) -> str:
    return os.path.join(_links_dir(academic_hub_root), "dismissals.json")


def _load_json_list(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"expected a list, got {type(data).__name__}")
        return data
    except (OSError, ValueError) as err:
        print(f"WARNING: could not load {path} ({err}); treating as empty.")
        return []


def _save_json_list(path: str, entries: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def load_review(academic_hub_root: str) -> list[dict]:
    return _load_json_list(_review_path(academic_hub_root))


def save_review(academic_hub_root: str, entries: list[dict]) -> None:
    _save_json_list(_review_path(academic_hub_root), entries)


def load_dismissals(academic_hub_root: str) -> list[dict]:
    return _load_json_list(_dismissals_path(academic_hub_root))


def save_dismissals(academic_hub_root: str, dismissals: list[dict]) -> None:
    _save_json_list(_dismissals_path(academic_hub_root), dismissals)


def is_dismissed(dismissals: list[dict], file_id_a: str, file_id_b: str) -> bool:
    """Tolerates a hand-edited entry that isn't a well-formed
    {"file_id_a","file_id_b"} dict -- it simply doesn't match anything,
    rather than raising (same degrade-don't-crash rule as duplicate_check.py's
    own is_dismissed, which this mirrors)."""
    pair = tuple(sorted([file_id_a, file_id_b]))
    for d in dismissals:
        if not isinstance(d, dict):
            continue
        if tuple(sorted([d.get("file_id_a"), d.get("file_id_b")])) == pair:
            return True
    return False


def record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    """No-op (does not duplicate) if this exact pair is already recorded --
    safe to call every time a user says 'no' without checking first."""
    dismissals = load_dismissals(academic_hub_root)
    if is_dismissed(dismissals, file_id_a, file_id_b):
        return
    a, b = sorted([file_id_a, file_id_b])
    dismissals.append({"file_id_a": a, "file_id_b": b, "dismissed_at": now_iso()})
    save_dismissals(academic_hub_root, dismissals)


def derive_offering_for_card(card: dict, academic_hub_root: str) -> str | None:
    """Re-derives this card's offering straight from its own path on
    disk, independent of whether the stored offering_label field is
    present -- what makes this correct for cards indexed before that
    field existed (e.g. the real class_2024 cards from Phase 1's first
    real run, which predate it entirely)."""
    abs_notes_path = os.path.join(academic_hub_root, card["path"])
    try:
        abs_resources_path = to_resources_root(abs_notes_path)
    except ValueError:
        return None
    return find_containing_offering_label(abs_resources_path)
