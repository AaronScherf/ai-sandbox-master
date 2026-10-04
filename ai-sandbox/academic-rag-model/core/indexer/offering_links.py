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
import re

from core.env.academic_hub_paths import find_containing_offering_label, to_resources_root
from core.indexer.index_card import (
    compute_content_hash,
    cosine_similarity,
    find_card_by_file_id,
    list_courses,
    load_shard,
    now_iso,
    recompute_course_entry,
    save_shard,
)

OFFERING_LINK_AUTO_THRESHOLD = 0.90  # starting guess -- calibrate against real data via `--dry-run`
OFFERING_LINK_REVIEW_THRESHOLD = 0.80  # starting guess -- calibrate against real data via `--dry-run`

_SECTION_START = "<!-- offering-links:start -->"
_SECTION_END = "<!-- offering-links:end -->"
_NOTES_PREFIX = "academic_notes/"
_WIKILINK_UNSAFE_RE = re.compile(r"[\[\]|^#\r\n]")


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
    path = _WIKILINK_UNSAFE_RE.sub(" ", path).strip()
    offering_text = offering_label if offering_label is not None else "current"
    title = _WIKILINK_UNSAFE_RE.sub(" ", card.get("title") or os.path.basename(path)).strip()
    alias = f"{offering_text}: {title}"
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
    False (logged, not raised) if the file doesn't exist, or exists but
    can't be read/written (permissions, non-UTF-8 bytes) -- an indexing
    side-effect must never block or abort the rest of a run over one bad
    file."""
    md_path = os.path.join(academic_hub_root, card["path"])
    if not os.path.isfile(md_path):
        print(f"WARNING: cannot write related-notes section, file not found: {md_path}")
        return False

    try:
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
    except (OSError, UnicodeDecodeError) as err:
        print(f"WARNING: cannot write related-notes section for {md_path} ({err})")
        return False
    return True


def _remove_related_section(academic_hub_root: str, card: dict) -> bool:
    """Removes the delimited block entirely (rather than leaving an empty
    '## Related notes' with no bullets) when a card ends up with no
    remaining links -- e.g. its only linked pair was just dismissed."""
    md_path = os.path.join(academic_hub_root, card["path"])
    if not os.path.isfile(md_path):
        return False
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        start = content.find(_SECTION_START)
        if start == -1:
            return True
        end = content.find(_SECTION_END)
        end = end + len(_SECTION_END) if end != -1 else len(content)
        new_content = (content[:start] + content[end:].lstrip("\n")).rstrip("\n") + "\n"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except (OSError, UnicodeDecodeError) as err:
        print(f"WARNING: cannot remove related-notes section for {md_path} ({err})")
        return False
    return True


def _merge_related(existing: list[dict] | None, new_entries: list[dict]) -> list[dict]:
    """Replaces any prior entry for the same file_id (per spec), keeping
    every other existing entry untouched -- a single write_matches() call
    only knows about the pairs in its own `matches` argument, so it must
    not wipe out links a separate, earlier call recorded for a different
    pair on the same card."""
    new_ids = {e["file_id"] for e in new_entries}
    kept = [e for e in (existing or []) if e.get("file_id") not in new_ids]
    return kept + new_entries


def _resolve_related_tuple(entry: dict, academic_hub_root: str) -> tuple[dict, str | None, float] | None:
    """Looks up the full card (for its title) behind a stored
    related_offerings entry, so the markdown block can be rebuilt from
    the complete merged list, not just the new matches passed to this
    call. None if the target card no longer exists (deleted/orphaned)."""
    found = find_card_by_file_id(academic_hub_root, entry["file_id"])
    if found is None:
        return None
    _, target_card = found
    offering = derive_offering_for_card(target_card, academic_hub_root)
    return target_card, offering, entry["similarity"]


def write_matches(
    academic_hub_root: str, matches: list[tuple[dict, dict, float]], confidence: str,
) -> dict:
    """Writes both directions of every match: each card's related_offerings
    index field, merged with (not replacing) any prior entry for a
    different pair, and both cards' Obsidian-visible markdown section,
    rebuilt from the full merged list so an earlier call's links stay
    visible. Also refreshes content_hash to match the just-written
    markdown, so index_search's rebuild doesn't see the card as stale and
    regenerate it (losing related_offerings in the process). Offerings for
    the markdown aliases are recomputed fresh per related entry via
    derive_offering_for_card() (needed anyway for pre-existing entries
    this call didn't itself produce), so no offerings map is accepted
    here -- a caller that already has one (run_for_course) doesn't need
    to pass it."""
    stats = {"links_written": 0, "markdown_writes_skipped": 0}
    new_related_by_fid: dict[str, list[dict]] = {}

    for card_a, card_b, similarity in matches:
        new_related_by_fid.setdefault(card_a["file_id"], []).append(
            {"file_id": card_b["file_id"], "path": card_b["path"], "similarity": similarity, "confidence": confidence}
        )
        new_related_by_fid.setdefault(card_b["file_id"], []).append(
            {"file_id": card_a["file_id"], "path": card_a["path"], "similarity": similarity, "confidence": confidence}
        )
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
            if fid not in new_related_by_fid:
                continue
            merged = _merge_related(card.get("related_offerings"), new_related_by_fid[fid])
            card["related_offerings"] = merged

            related_tuples = [
                t for t in (_resolve_related_tuple(entry, academic_hub_root) for entry in merged) if t is not None
            ]
            if append_related_section(academic_hub_root, card, related_tuples):
                card["content_hash"] = compute_content_hash(os.path.join(academic_hub_root, card["path"]))
            else:
                stats["markdown_writes_skipped"] += 1
            changed = True
        if changed:
            save_shard(academic_hub_root, course, shard)
            recompute_course_entry(academic_hub_root, course)

    return stats


def _already_linked_ids(card: dict) -> set[str]:
    return {e.get("file_id") for e in (card.get("related_offerings") or []) if isinstance(e, dict)}


def _pair_summary(card_a: dict, card_b: dict, similarity: float) -> dict:
    return {
        "file_id_a": card_a["file_id"], "title_a": card_a.get("title", ""), "path_a": card_a["path"],
        "file_id_b": card_b["file_id"], "title_b": card_b.get("title", ""), "path_b": card_b["path"],
        "similarity": similarity,
    }


def run_for_course(academic_hub_root: str, course: str, dry_run: bool = False) -> dict:
    all_cards = [
        c for c in load_shard(academic_hub_root, course)
        if c.get("embedding") and not c.get("orphaned") and not c.get("needs_indexing")
    ]
    offerings = {c["file_id"]: derive_offering_for_card(c, academic_hub_root) for c in all_cards}
    cards_with_offerings = [(c, offerings[c["file_id"]]) for c in all_cards]

    auto_matches, review_matches = find_cross_offering_matches(cards_with_offerings)

    dismissals = load_dismissals(academic_hub_root)

    def _keep(match: tuple[dict, dict, float]) -> bool:
        card_a, card_b, _ = match
        if is_dismissed(dismissals, card_a["file_id"], card_b["file_id"]):
            return False
        # Already linked (e.g. a prior auto-match, or a resolved review
        # match) -- don't re-process it: for a review-band pair this is
        # what stops a resolved match from bouncing back into review.json
        # on the very next run, since its similarity hasn't changed.
        if card_b["file_id"] in _already_linked_ids(card_a):
            return False
        return True

    auto_matches = [m for m in auto_matches if _keep(m)]
    review_matches = [m for m in review_matches if _keep(m)]

    if not dry_run and auto_matches:
        write_matches(academic_hub_root, auto_matches, confidence="high")

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

    return {
        "auto_matches": len(auto_matches),
        "review_matches": len(review_matches),
        "auto_pairs": [_pair_summary(a, b, sim) for a, b, sim in auto_matches],
        "review_pairs": [_pair_summary(a, b, sim) for a, b, sim in review_matches],
    }


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
    write_matches(academic_hub_root, [(card_a, card_b, entry["similarity"])], confidence="high")

    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    save_review(academic_hub_root, remaining)
    return True


def _remove_link(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    """Strips any existing related_offerings entry (and rebuilds or
    removes the markdown section) for this pair on both sides -- used
    when a previously-linked pair is dismissed, so the dismissal actually
    removes what's already visible, not just future re-linking."""
    for file_id, other_id in ((file_id_a, file_id_b), (file_id_b, file_id_a)):
        found = find_card_by_file_id(academic_hub_root, file_id)
        if found is None:
            continue
        course, _card = found
        shard = load_shard(academic_hub_root, course)
        changed = False
        for c in shard:
            if c.get("file_id") != file_id:
                continue
            related = c.get("related_offerings") or []
            if not any(e.get("file_id") == other_id for e in related if isinstance(e, dict)):
                break
            new_related = [e for e in related if e.get("file_id") != other_id]
            c["related_offerings"] = new_related
            if new_related:
                related_tuples = [
                    t for t in (_resolve_related_tuple(e, academic_hub_root) for e in new_related) if t is not None
                ]
                wrote = append_related_section(academic_hub_root, c, related_tuples)
            else:
                wrote = _remove_related_section(academic_hub_root, c)
            if wrote:
                c["content_hash"] = compute_content_hash(os.path.join(academic_hub_root, c["path"]))
            changed = True
            break
        if changed:
            save_shard(academic_hub_root, course, shard)
            recompute_course_entry(academic_hub_root, course)


def reject_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Permanently dismisses this pair: clears it from review.json if
    pending, strips any link already written on both sides if the pair
    was already auto-linked, and records the dismissal either way so
    neither tier nor a future run ever re-surfaces it. Always succeeds."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    if len(remaining) != len(review):
        save_review(academic_hub_root, remaining)
    _remove_link(academic_hub_root, file_id_a, file_id_b)
    record_dismissal(academic_hub_root, file_id_a, file_id_b)
    return True


def _academic_hub_dir():
    from pathlib import Path
    # offering_links.py lives at academic-rag-model/core/indexer/ -- two
    # levels under academic-rag-model, which is itself a sibling of
    # academic-hub under ai-sandbox/. Four parents, matching
    # route_notes_transcribe.py's own identical resolution for its equally
    # 2-levels-deep location (pipelines/transcribe_notes/).
    return Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"


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
        reject_pending(academic_hub_dir, a, b)
        print("dismissed")
        return

    courses = args.course if args.course is not None else list_courses(academic_hub_dir)
    for course in courses:
        stats = run_for_course(academic_hub_dir, course, dry_run=args.dry_run)
        print(f"{course}: {stats['auto_matches']} linked, {stats['review_matches']} pending review")
        if args.dry_run:
            for pair in stats["auto_pairs"] + stats["review_pairs"]:
                print(
                    f"  [{pair['similarity']:.3f}] {pair['file_id_a']} {pair['title_a']!r} <-> "
                    f"{pair['file_id_b']} {pair['title_b']!r}"
                )


if __name__ == "__main__":
    main()
