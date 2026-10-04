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
from core.indexer.index_card import (
    cosine_similarity,
    find_card_by_file_id,
    list_courses,
    load_shard,
    now_iso,
    recompute_course_entry,
    save_shard,
)

OFFERING_LINK_AUTO_THRESHOLD = 0.90  # starting guess -- calibrate against real data (Task 4)
OFFERING_LINK_REVIEW_THRESHOLD = 0.80  # starting guess -- calibrate against real data (Task 4)

_SECTION_START = "<!-- offering-links:start -->"
_SECTION_END = "<!-- offering-links:end -->"
_NOTES_PREFIX = "academic_notes/"


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


def find_cross_offering_matches(
    cards_with_offerings: list[tuple[dict, str | None]],
    auto_threshold: float = OFFERING_LINK_AUTO_THRESHOLD,
    review_threshold: float = OFFERING_LINK_REVIEW_THRESHOLD,
) -> tuple[list[tuple[dict, dict, float]], list[tuple[dict, dict, float]]]:
    """Pure function -- no file I/O. Compares every pair of cards whose
    offerings differ (two primary cards, both None, are therefore never
    compared here at all -- that's retag.py's subject-clustering job, not
    this one's). Returns (auto_matches, review_matches), each a list of
    (card_a, card_b, similarity) above its respective threshold."""
    auto_matches = []
    review_matches = []
    n = len(cards_with_offerings)
    for i in range(n):
        card_a, offering_a = cards_with_offerings[i]
        for j in range(i + 1, n):
            card_b, offering_b = cards_with_offerings[j]
            if offering_a == offering_b:
                continue
            similarity = cosine_similarity(card_a.get("embedding") or [], card_b.get("embedding") or [])
            if similarity >= auto_threshold:
                auto_matches.append((card_a, card_b, similarity))
            elif similarity >= review_threshold:
                review_matches.append((card_a, card_b, similarity))
    return auto_matches, review_matches


def link_target_display(card: dict, offering_label: str | None) -> tuple[str, str]:
    """(wikilink target path, alias text) for card. The target is
    card["path"] relative to the academic_notes/ vault root (Obsidian's
    actual sync root is that directory's own standalone git repo, not
    academic-hub/ itself) with the .md suffix stripped -- a bare filename
    link would be ambiguous given real collisions already in this corpus
    (e.g. slides1.md exists under both professor_notes/ and
    class_2024/Class Notes/Slides/)."""
    path = card["path"]
    if path.startswith(_NOTES_PREFIX):
        path = path[len(_NOTES_PREFIX):]
    if path.endswith(".md"):
        path = path[: -len(".md")]
    offering_text = offering_label if offering_label is not None else "current"
    alias = f"{offering_text}: {card.get('title') or os.path.basename(path)}"
    return path, alias


def _build_related_section(related: list[tuple[dict, str | None, float]]) -> str:
    lines = [_SECTION_START, "## Related notes"]
    for target_card, offering_label, similarity in related:
        link_path, alias = link_target_display(target_card, offering_label)
        lines.append(f"- [[{link_path}|{alias}]] (similarity: {similarity:.2f})")
    lines.append(_SECTION_END)
    return "\n".join(lines) + "\n"


def append_related_section(academic_hub_root: str, card: dict, related: list[tuple[dict, str | None, float]]) -> bool:
    """Appends (or replaces, if already present) an idempotent, delimited
    '## Related notes' block at the end of card's own .md file. Returns
    False (logged, not raised) if the file doesn't exist on disk --
    an indexing side-effect must never block on a missing file."""
    md_path = os.path.join(academic_hub_root, card["path"])
    if not os.path.isfile(md_path):
        print(f"WARNING: cannot write related-notes section, file not found: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_section = _build_related_section(related)
    start = content.find(_SECTION_START)
    if start == -1:
        separator = "" if content.endswith("\n") else "\n"
        new_content = content + separator + "\n" + new_section
    else:
        end = content.find(_SECTION_END)
        end = end + len(_SECTION_END) if end != -1 else len(content)
        new_content = content[:start] + new_section + content[end:].lstrip("\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def write_matches(
    academic_hub_root: str, matches: list[tuple[dict, dict, float]], confidence: str,
    offerings: dict[str, str | None],
) -> dict:
    """Writes both directions of every match: each card's related_offerings
    index field (replacing any prior entry for that same pair, so a rerun
    is idempotent) and both cards' Obsidian-visible markdown section.
    `offerings` maps file_id -> offering_label, precomputed by the caller
    (Task 6) via derive_offering_for_card() for every card involved."""
    stats = {"links_written": 0, "markdown_writes_skipped": 0}
    by_file_id_related: dict[str, list[tuple[dict, str | None, float]]] = {}

    for card_a, card_b, similarity in matches:
        by_file_id_related.setdefault(card_a["file_id"], []).append((card_b, offerings.get(card_b["file_id"]), similarity))
        by_file_id_related.setdefault(card_b["file_id"], []).append((card_a, offerings.get(card_a["file_id"]), similarity))
        stats["links_written"] += 1

    # Group touched cards by the course each one's own path implies, so
    # each shard is loaded and saved exactly once regardless of how many
    # matches touch cards in it.
    touched_paths: dict[str, str] = {}
    for card_a, card_b, _ in matches:
        touched_paths[card_a["file_id"]] = card_a["path"]
        touched_paths[card_b["file_id"]] = card_b["path"]
    courses = {path.replace("\\", "/").split("/")[1] for path in touched_paths.values()}

    for course in courses:
        shard = load_shard(academic_hub_root, course)
        changed = False
        for card in shard:
            fid = card.get("file_id")
            if fid not in by_file_id_related:
                continue
            card["related_offerings"] = [
                {"file_id": other["file_id"], "path": other["path"], "similarity": sim, "confidence": confidence}
                for other, _label, sim in by_file_id_related[fid]
            ]
            changed = True
        if changed:
            save_shard(academic_hub_root, course, shard)
            recompute_course_entry(academic_hub_root, course)

    for card_a, card_b, _ in matches:
        for card in (card_a, card_b):
            related = by_file_id_related[card["file_id"]]
            if not append_related_section(academic_hub_root, card, related):
                stats["markdown_writes_skipped"] += 1

    return stats


def run_for_course(academic_hub_root: str, course: str, dry_run: bool = False) -> dict:
    all_cards = [
        c for c in load_shard(academic_hub_root, course)
        if c.get("embedding") and not c.get("orphaned") and not c.get("needs_indexing")
    ]
    offerings = {c["file_id"]: derive_offering_for_card(c, academic_hub_root) for c in all_cards}
    cards_with_offerings = [(c, offerings[c["file_id"]]) for c in all_cards]

    auto_matches, review_matches = find_cross_offering_matches(cards_with_offerings)

    dismissals = load_dismissals(academic_hub_root)
    auto_matches = [
        m for m in auto_matches if not is_dismissed(dismissals, m[0]["file_id"], m[1]["file_id"])
    ]
    review_matches = [
        m for m in review_matches if not is_dismissed(dismissals, m[0]["file_id"], m[1]["file_id"])
    ]

    if not dry_run and auto_matches:
        write_matches(academic_hub_root, auto_matches, confidence="high", offerings=offerings)

    if not dry_run and review_matches:
        existing_review = load_review(academic_hub_root)
        existing_pairs = {tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) for e in existing_review}
        for card_a, card_b, similarity in review_matches:
            pair = tuple(sorted([card_a["file_id"], card_b["file_id"]]))
            if pair in existing_pairs:
                continue
            existing_review.append({
                "file_id_a": pair[0], "file_id_b": pair[1], "similarity": similarity, "course": course,
            })
        save_review(academic_hub_root, existing_review)

    return {"auto_matches": len(auto_matches), "review_matches": len(review_matches)}


def resolve_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Confirms a pending review match: writes it as a high-confidence
    link (same as an auto-match) and removes it from review.json."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    entry = next((e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) == pair), None)
    if entry is None:
        return False

    found_a = find_card_by_file_id(academic_hub_root, file_id_a)
    found_b = find_card_by_file_id(academic_hub_root, file_id_b)
    if found_a is None or found_b is None:
        return False
    _, card_a = found_a
    _, card_b = found_b
    offerings = {
        file_id_a: derive_offering_for_card(card_a, academic_hub_root),
        file_id_b: derive_offering_for_card(card_b, academic_hub_root),
    }
    write_matches(academic_hub_root, [(card_a, card_b, entry["similarity"])], confidence="high", offerings=offerings)

    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    save_review(academic_hub_root, remaining)
    return True


def reject_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Permanently dismisses a pending review match and clears it from
    review.json. Returns True even if the pair was already dismissed but
    present in review.json (clearing the stale entry is still useful)."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    was_pending = len(remaining) != len(review)
    record_dismissal(academic_hub_root, file_id_a, file_id_b)
    if was_pending:
        save_review(academic_hub_root, remaining)
    return was_pending


def _academic_hub_dir():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent / "academic-hub"


def main() -> None:
    import argparse

    from core.env.gemini_utils import load_dotenv_override

    load_dotenv_override()
    parser = argparse.ArgumentParser(
        description="Find and link likely corollaries between a course's marked prior "
                    "offerings and its other content, using each card's existing embedding."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course.")
    parser.add_argument("--dry-run", action="store_true", help="Report matches without writing anything.")
    parser.add_argument("--resolve", metavar="FILE_ID_A:FILE_ID_B",
                         help="Confirm one pending review match, writing it as a high-confidence link.")
    parser.add_argument("--reject", metavar="FILE_ID_A:FILE_ID_B",
                         help="Permanently dismiss one pending review match.")
    args = parser.parse_args()

    academic_hub_dir = str(_academic_hub_dir())

    if args.resolve:
        a, b = args.resolve.split(":", 1)
        print("resolved" if resolve_pending(academic_hub_dir, a, b) else "no such pending match")
        return
    if args.reject:
        a, b = args.reject.split(":", 1)
        print("dismissed" if reject_pending(academic_hub_dir, a, b) else "no such pending match")
        return

    courses = args.course if args.course is not None else list_courses(academic_hub_dir)
    for course in courses:
        stats = run_for_course(academic_hub_dir, course, dry_run=args.dry_run)
        print(f"{course}: {stats['auto_matches']} linked, {stats['review_matches']} pending review")


if __name__ == "__main__":
    main()
