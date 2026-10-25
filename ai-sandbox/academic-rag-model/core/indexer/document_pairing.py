"""
document_pairing.py
Automated detection of document pairs within a single course -- a
problem set and its solution set, or a lecture's slides and its notes --
using only each card's own filename/path (naming-convention and
structural heuristics), never content or embeddings. Deliberately
separate from index_card.py (like offering_links.py), and deliberately
narrower than it: no cosine similarity, no cross-offering comparison --
every pairing candidate must share the same course and the same
inferred offering year (see _offering_year()), so a 2024 homework never
gets paired against a 2025 solution set that happens to share the same
number.

Confident pairs (naming convention gives exactly one unambiguous base
document -- a single problem set, or a single slides/notes pair) are
written automatically. Ambiguous groups (more than one candidate base
document sharing the same family+number+offering) are deferred to the
same ledger + review-artifact + resolve/reject pattern offering_links.py
uses, rather than guessing.

Spec: docs/trackers/academic_hub_to_do.md TODO-0039.
"""
from __future__ import annotations

import json
import os
import re

from core.indexer.index_card import (
    find_card_by_file_id,
    list_courses,
    load_shard,
    now_iso,
    recompute_course_entry,
    save_shard,
)

PROBLEM_SOLUTION_PAIR_TYPE = "problem_solution"
LECTURE_SLIDES_NOTES_PAIR_TYPE = "lecture_slides_notes"

# Explicit "this is a solution/answer document" markers -- a strong
# enough signal on its own that extra leftover tokens (e.g. a model name
# like "gemini" in "problem_set_1_gemini_solutions") don't disqualify it.
_SOLUTION_MARKERS = frozenset({"solution", "solutions", "sol", "sols", "answer", "answers"})

# Tokens that, alone, identify a problem-set-family filename. "problem"
# and "set" are only treated as a family signal together (see
# _PROBLEM_FAMILY_PAIR below) -- either word alone is too generic (e.g.
# a "problem" in an unrelated title, a furniture "set").
_PROBLEM_FAMILY_TOKENS = frozenset({"hw", "homework", "pset", "ps"})
_PROBLEM_FAMILY_PAIR = ("problem", "set")

# Qualifier tokens that may appear on either side of a problem/solution
# pair without disqualifying it as the "base" problem document (e.g.
# "Part_I_HW4" is still base-shaped once "part"/"i" are allowed through).
_PROBLEM_ALLOWED_EXTRA = frozenset({
    "part", "i", "ii", "iii", "iv", "v", "guided", "final", "revised",
    "long", "short", "extended", "updated", "with",
})

# "notes" alone is far too generic a token (ta_notes, hand-written
# notes, class notes...) to trigger lecture-family membership by itself
# -- membership requires one of these; "notes"/"note" then only decide
# which *role* within an already-triggered lecture-family group.
_LECTURE_FAMILY_TRIGGERS = frozenset({"lecture", "lec", "slides", "slide"})
_SLIDES_MARKERS = frozenset({"slides", "slide"})
_NOTES_MARKERS = frozenset({"notes", "note"})

_YEAR_RE = re.compile(r"class[_\s]?(\d{4})|(\d{4})[_\s]?class", re.I)
_TOKEN_SPLIT_RE = re.compile(r"[_\-]+")
_ALPHA_OR_DIGIT_RE = re.compile(r"[A-Za-z]+|\d+")


def _links_dir(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "document_pairs")


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
    pair = tuple(sorted([file_id_a, file_id_b]))
    for d in dismissals:
        if not isinstance(d, dict):
            continue
        if tuple(sorted([d.get("file_id_a"), d.get("file_id_b")])) == pair:
            return True
    return False


def record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    dismissals = load_dismissals(academic_hub_root)
    if is_dismissed(dismissals, file_id_a, file_id_b):
        return
    a, b = sorted([file_id_a, file_id_b])
    dismissals.append({"file_id_a": a, "file_id_b": b, "dismissed_at": now_iso()})
    save_dismissals(academic_hub_root, dismissals)


def _tokenize(stem: str) -> list[str]:
    """Splits a filename stem into lowercased alpha-only/digit-only
    tokens, treating underscore/dash/space as separators and also
    splitting letter-digit boundaries within a single separator-free run
    (so "pset3", "HW4Sol", "slides1" each still yield a distinct numeric
    token). Not full tokenization -- a mid-run case change like
    "slidesASYM" stays one token, which is fine here since it carries no
    digit and therefore can't match any pairing group anyway."""
    stem = stem.replace(" ", "_")
    tokens: list[str] = []
    for chunk in _TOKEN_SPLIT_RE.split(stem):
        if not chunk:
            continue
        tokens.extend(_ALPHA_OR_DIGIT_RE.findall(chunk))
    return [t.lower() for t in tokens]


def _offering_year(path: str) -> str | None:
    """A 4-digit offering year adjacent to the word "class" in path
    (academic_notes/.../class_2024/... or 2024_class/...), or None for a
    course's default/current-offering directories that carry no such
    marker. Deliberately not the same mechanism as offering_links.py's
    .notes_subset.json marker -- that marker is opt-in and sparse (set
    for a handful of deliberately-compared prior offerings), while every
    course here routinely has multiple same-numbered homeworks living
    one directory apart (Homeworks/ vs Homeworks/Solutions/) that must
    not be confused with a genuinely different year's homework of the
    same number."""
    m = _YEAR_RE.search(path)
    if not m:
        return None
    return m.group(1) or m.group(2)


def classify_document(card: dict) -> dict | None:
    """Pure filename/path classification of one card into a pairing
    slot: which family (problem_solution / lecture_slides_notes), which
    role within it (problem/solution, slides/notes), and the group key
    other candidates must share to be considered its counterpart. None
    for the (overwhelming majority) of cards that carry none of the
    recognized naming markers at all, or that carry a family marker with
    no identifying number, or an auxiliary document that matches a
    family+number but isn't recognizably the base document or an
    explicitly-marked solution/notes variant (e.g. "homework_4_hints",
    "homework_3_tutoring_audit" -- real files in this corpus that are
    neither a problem set nor a solution set for homework 4/3)."""
    stem = os.path.splitext(os.path.basename(card["path"]))[0]
    tokens = _tokenize(stem)
    token_set = set(tokens)
    # A candidate homework/lecture index must be a short (1-2 digit),
    # *isolated* digit token -- not immediately next to another
    # digit-only token. A bare isdigit() check also matches 4-digit
    # years (a textbook title ending "..._2026") and the runs of
    # 2-digit date/time fragments embedded in Excalidraw export
    # filenames ("2026-09-10 10.09.33" tokenizes to six consecutive
    # digit tokens) -- none of those are an identifying number. On real
    # corpus data, picking the first bare digit token collapsed every
    # dated lecture note in a course together with an unrelated
    # textbook into one false "same lecture number" group, because both
    # happened to contain the literal string "2026".
    number = next(
        (
            t for i, t in enumerate(tokens)
            if t.isdigit() and len(t) <= 2
            and not (i > 0 and tokens[i - 1].isdigit())
            and not (i + 1 < len(tokens) and tokens[i + 1].isdigit())
        ),
        None,
    )
    if number is None:
        return None

    offering_key = (card.get("course"), _offering_year(card["path"]))

    is_problem_family = bool(token_set & _PROBLEM_FAMILY_TOKENS) or (
        _PROBLEM_FAMILY_PAIR[0] in token_set and _PROBLEM_FAMILY_PAIR[1] in token_set
    )
    if is_problem_family:
        if token_set & _SOLUTION_MARKERS:
            role = "solution"
        else:
            removable = (
                _PROBLEM_FAMILY_TOKENS | set(_PROBLEM_FAMILY_PAIR) | _PROBLEM_ALLOWED_EXTRA | {number}
            )
            leftover = [t for t in tokens if t not in removable]
            if leftover:
                return None
            role = "problem"
        return {
            "pair_type": PROBLEM_SOLUTION_PAIR_TYPE,
            "role": role,
            "group_key": (*offering_key, "problem_set", number),
        }

    if token_set & _LECTURE_FAMILY_TRIGGERS:
        if token_set & _SLIDES_MARKERS:
            role = "slides"
        elif token_set & _NOTES_MARKERS:
            role = "notes"
        else:
            return None  # "lecture_12" alone -- no marker says which side it is
        return {
            "pair_type": LECTURE_SLIDES_NOTES_PAIR_TYPE,
            "role": role,
            "group_key": (*offering_key, "lecture", number),
        }

    return None


def find_document_pairs(
    cards: list[dict],
) -> tuple[list[tuple[dict, dict, str]], list[tuple[dict, dict, str]]]:
    """Pure function -- no file I/O. Groups cards (expected to all be
    from one course -- callers pass one course's shard, same convention
    as offering_links.find_cross_offering_matches per-course call) by
    classify_document()'s group_key, then pairs each group's "base" role
    (problem, for problem_solution; both slides and notes, for
    lecture_slides_notes -- see confidence rule below) against its
    counterpart role. Returns (auto_pairs, review_pairs), each a list of
    (card_a, card_b, pair_type).

    Confidence rule: a problem_solution group is confident (auto) iff it
    has exactly one problem (base) document -- one base pairing with
    several solution variants (e.g. a homework's "solutions" and
    "guided_solutions" are both genuine, real-corpus pairs) is not
    ambiguous, but two candidate base documents sharing a solution is.
    A lecture_slides_notes group is confident only when both sides have
    exactly one document -- neither slides nor notes has an inherently
    "base" role to break the tie the way a problem set does."""
    groups: dict[tuple, dict[str, list[dict]]] = {}
    for card in cards:
        classified = classify_document(card)
        if classified is None:
            continue
        key = classified["group_key"]
        groups.setdefault(key, {}).setdefault(classified["role"], []).append(card)

    auto_pairs: list[tuple[dict, dict, str]] = []
    review_pairs: list[tuple[dict, dict, str]] = []
    for key, roles in groups.items():
        if key[2] == "problem_set":
            pair_type = PROBLEM_SOLUTION_PAIR_TYPE
            base, variants = roles.get("problem", []), roles.get("solution", [])
            confident = len(base) == 1
        else:
            pair_type = LECTURE_SLIDES_NOTES_PAIR_TYPE
            base, variants = roles.get("slides", []), roles.get("notes", [])
            confident = len(base) == 1 and len(variants) == 1

        if not base or not variants:
            continue

        target = auto_pairs if confident else review_pairs
        for a in base:
            for b in variants:
                target.append((a, b, pair_type))

    return auto_pairs, review_pairs


def _already_paired_ids(card: dict) -> set[str]:
    return {e.get("file_id") for e in (card.get("paired_with") or []) if isinstance(e, dict)}


def _merge_paired(existing: list[dict] | None, new_entries: list[dict]) -> list[dict]:
    new_ids = {e["file_id"] for e in new_entries}
    kept = [e for e in (existing or []) if e.get("file_id") not in new_ids]
    return kept + new_entries


def write_pairs(
    academic_hub_root: str, course: str, pairs: list[tuple[dict, dict, str]], confidence: str,
) -> dict:
    """Writes both directions of every pair onto each card's own
    `paired_with` index field (merged with, not replacing, any prior
    entry for a different counterpart), within a single course's shard.
    Unlike offering_links.write_matches, there is no Obsidian-visible
    markdown side effect here -- TODO-0039 scoped this to index-card data
    only; a human-facing surface for `paired_with` (and for the review
    ledger this module writes) is a separate follow-up, same as
    offering_links' own review artifact was built once its ledger shape
    was settled."""
    stats = {"links_written": 0}
    new_by_fid: dict[str, list[dict]] = {}
    for card_a, card_b, pair_type in pairs:
        new_by_fid.setdefault(card_a["file_id"], []).append(
            {"file_id": card_b["file_id"], "path": card_b["path"], "pair_type": pair_type, "confidence": confidence}
        )
        new_by_fid.setdefault(card_b["file_id"], []).append(
            {"file_id": card_a["file_id"], "path": card_a["path"], "pair_type": pair_type, "confidence": confidence}
        )
        stats["links_written"] += 1

    shard = load_shard(academic_hub_root, course)
    changed = False
    for card in shard:
        fid = card.get("file_id")
        if fid not in new_by_fid:
            continue
        card["paired_with"] = _merge_paired(card.get("paired_with"), new_by_fid[fid])
        changed = True
    if changed:
        save_shard(academic_hub_root, course, shard)
        recompute_course_entry(academic_hub_root, course)
    return stats


def _pair_summary(card_a: dict, card_b: dict, pair_type: str) -> dict:
    return {
        "file_id_a": card_a["file_id"], "title_a": card_a.get("title", ""), "path_a": card_a["path"],
        "file_id_b": card_b["file_id"], "title_b": card_b.get("title", ""), "path_b": card_b["path"],
        "pair_type": pair_type,
    }


def run_for_course(academic_hub_root: str, course: str, dry_run: bool = False) -> dict:
    all_cards = [c for c in load_shard(academic_hub_root, course) if not c.get("orphaned")]
    auto_pairs, review_pairs = find_document_pairs(all_cards)

    dismissals = load_dismissals(academic_hub_root)

    def _keep(pair: tuple[dict, dict, str]) -> bool:
        card_a, card_b, _ = pair
        if is_dismissed(dismissals, card_a["file_id"], card_b["file_id"]):
            return False
        if card_b["file_id"] in _already_paired_ids(card_a):
            return False
        return True

    auto_pairs = [p for p in auto_pairs if _keep(p)]
    review_pairs = [p for p in review_pairs if _keep(p)]

    if not dry_run and auto_pairs:
        write_pairs(academic_hub_root, course, auto_pairs, confidence="high")

    if not dry_run and review_pairs:
        existing_review = load_review(academic_hub_root)
        existing_pairs = {tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) for e in existing_review}
        for card_a, card_b, pair_type in review_pairs:
            pair = tuple(sorted([card_a["file_id"], card_b["file_id"]]))
            if pair in existing_pairs:
                continue
            existing_review.append({
                "file_id_a": pair[0], "file_id_b": pair[1], "pair_type": pair_type, "course": course,
            })
        save_review(academic_hub_root, existing_review)

    return {
        "auto_matches": len(auto_pairs),
        "review_matches": len(review_pairs),
        "auto_pairs": [_pair_summary(a, b, t) for a, b, t in auto_pairs],
        "review_pairs": [_pair_summary(a, b, t) for a, b, t in review_pairs],
    }


def resolve_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Confirms a pending review pair: writes it as a high-confidence
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
    course, card_a = found_a
    _, card_b = found_b
    write_pairs(academic_hub_root, course, [(card_a, card_b, entry["pair_type"])], confidence="high")

    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    save_review(academic_hub_root, remaining)
    return True


def _remove_pair(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
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
            paired = c.get("paired_with") or []
            if not any(e.get("file_id") == other_id for e in paired if isinstance(e, dict)):
                break
            c["paired_with"] = [e for e in paired if e.get("file_id") != other_id]
            changed = True
            break
        if changed:
            save_shard(academic_hub_root, course, shard)
            recompute_course_entry(academic_hub_root, course)


def reject_pending(academic_hub_root: str, file_id_a: str, file_id_b: str) -> bool:
    """Permanently dismisses this pair: clears it from review.json if
    pending, strips any link already written on both sides if it was
    already auto-linked, and records the dismissal either way. Always
    succeeds."""
    review = load_review(academic_hub_root)
    pair = tuple(sorted([file_id_a, file_id_b]))
    remaining = [e for e in review if tuple(sorted([e.get("file_id_a"), e.get("file_id_b")])) != pair]
    if len(remaining) != len(review):
        save_review(academic_hub_root, remaining)
    _remove_pair(academic_hub_root, file_id_a, file_id_b)
    record_dismissal(academic_hub_root, file_id_a, file_id_b)
    return True


def _academic_hub_dir():
    from pathlib import Path
    # document_pairing.py lives at academic-rag-model/core/indexer/ --
    # same resolution as offering_links.py's own _academic_hub_dir().
    return Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect and link problem-set/solution-set and lecture-slides/lecture-notes pairs "
                    "within a course, using filename/path naming-convention heuristics only."
    )
    parser.add_argument("--course", action="append", default=None,
                         help="Limit to this course (repeatable). Default: every course.")
    parser.add_argument("--dry-run", action="store_true", help="Report pairs without writing anything.")
    parser.add_argument("--resolve", metavar="FILE_ID_A:FILE_ID_B",
                         help="Confirm one pending review pair, writing it as a high-confidence link.")
    parser.add_argument("--reject", metavar="FILE_ID_A:FILE_ID_B",
                         help="Permanently dismiss one pending review pair.")
    args = parser.parse_args()

    academic_hub_dir = str(_academic_hub_dir())

    if args.resolve:
        a, b = args.resolve.split(":", 1)
        print("resolved" if resolve_pending(academic_hub_dir, a, b) else "no such pending pair")
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
                    f"  [{pair['pair_type']}] {pair['file_id_a']} {pair['title_a']!r} <-> "
                    f"{pair['file_id_b']} {pair['title_b']!r}"
                )


if __name__ == "__main__":
    main()
