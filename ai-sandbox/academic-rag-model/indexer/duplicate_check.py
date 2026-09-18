"""
duplicate_check.py
Cross-course duplicate-textbook detection, run as a pre-flight step
before any PDF in a course's textbook folder is uploaded/converted (see
convert_textbook_instructions.md Step 0.4 and
convert_textbook_agent_instructions.md Step 0.3). Deliberately has no
torch/marker/pypdf/genai dependency, same constraint as index_card.py
and textbook/bib_info.py, so it stays testable and runnable with no GPU,
no VM, and no network.

Spec: docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import os
import re
import shutil
import sys
from pathlib import Path

from indexer.index_card import compute_file_id, compute_id_from_parts, derive_course, find_card_by_file_id, list_courses, load_shard, now_iso, recompute_course_entry, save_shard
from textbook.bib_info import extract_bibliographic_info_from_filename

# A card only stores `title` (from generate_index_card()'s LLM/regex
# tiers) -- never author/year as their own fields. The candidate side of
# a fuzzy comparison instead parses author/year out of the candidate's
# own output folder name, which textbook.bib_info.derive_folder_name
# always writes as "<AuthorLastName>_<SanitizedTitle>_<Year>" (spec §3).
_TITLE_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")

# Below this combined score, a fuzzy candidate is never mentioned to the
# user at all -- deliberately loose (0.6, not a high-trust bar) because
# Tier 2 never auto-skips regardless of score (spec §3-4); this threshold
# only controls noise, never trust.
SURFACE_THRESHOLD = 0.6


def normalize_title(title: str) -> str:
    """Lowercase, punctuation-stripped, whitespace-collapsed -- comparison
    key for difflib title similarity, not a display value."""
    if not title:
        return ""
    cleaned = _TITLE_PUNCTUATION_RE.sub("", title).lower()
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def parse_author_year_from_folder_name(folder_name: str) -> tuple[str, str]:
    """Reverses textbook.bib_info.derive_folder_name's
    "<AuthorLastName>_<SanitizedTitle>_<Year>" convention -- author and
    year are always single tokens by construction (sanitize_filename
    never puts an underscore at either edge), unlike the sanitized title
    in between, which is not extracted here since the candidate's real
    `title` field (on its index card) is used instead of re-deriving one
    from this sanitized folder segment."""
    parts = folder_name.split("_")
    author = parts[0] if parts else ""
    year = parts[-1] if len(parts) > 2 else ""
    return author, year


def score_candidate(incoming: dict, candidate_title: str, candidate_author: str, candidate_year: str) -> dict:
    """Scores one candidate card against the incoming PDF's filename-derived
    bibliographic guess (spec §3). Never raises on empty/missing fields --
    every comparison degrades to a 0-bonus no-op rather than erroring, so a
    book with an unparseable filename still gets *some* score instead of
    crashing the whole batch (see Task 3's per-candidate error isolation,
    which is a second, independent safety net on top of this)."""
    title_score = difflib.SequenceMatcher(
        None, normalize_title(incoming.get("title", "")), normalize_title(candidate_title),
    ).ratio()

    author_bonus = 0.0
    incoming_author = (incoming.get("author") or "").strip()
    if incoming_author and candidate_author:
        incoming_last = incoming_author.split()[-1].lower()
        if incoming_last and incoming_last in candidate_author.lower():
            author_bonus = 0.15

    year_bonus = 0.0
    incoming_year = (incoming.get("year") or "").strip()
    if incoming_year and candidate_year:
        try:
            diff = abs(int(incoming_year) - int(candidate_year))
            if diff == 0:
                year_bonus = 0.1
            elif diff == 1:
                year_bonus = 0.05
        except ValueError:
            pass

    combined = min(1.0, title_score + author_bonus + year_bonus)
    return {"title_score": title_score, "author_bonus": author_bonus, "year_bonus": year_bonus, "combined": combined}


def find_exact_duplicate(academic_hub_root: str, pdf_path: str, current_course: str) -> tuple[str, dict] | None:
    """Tier 1 (spec §3): byte-identical duplicate in a *different* course.
    find_card_by_file_id() already searches every course unconditionally
    (indexer/index_card.py), so no change is needed there -- this just
    excludes a match that happens to already be in the current course,
    which is convert_textbook.py's own existing same-run skip check's
    job, not this module's."""
    file_id = compute_file_id(pdf_path)
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return None
    course, card = found
    if course == current_course:
        return None
    return course, card


def find_fuzzy_candidates(academic_hub_root: str, incoming: dict, current_course: str) -> list[dict]:
    """Tier 2 (spec §3): scores `incoming` (a bib_info-shaped
    {"title","author","year"} dict) against every textbook card in every
    *other* course. A card that can't be scored (malformed `path`, missing
    `title`) is skipped with a warning rather than aborting the whole scan
    (spec §6's error-isolation rule) -- same for a course whose shard file
    itself fails to load."""
    results = []
    for course in list_courses(academic_hub_root):
        if course == current_course:
            continue
        try:
            cards = load_shard(academic_hub_root, course)
        except Exception as err:
            print(f"WARNING: could not load shard for course {course!r} ({err}); skipping its candidates.", file=sys.stderr)
            continue

        for card in cards:
            if card.get("doc_type") != "textbook":
                continue
            try:
                folder_name = os.path.basename(os.path.dirname(card["path"]))
                author, year = parse_author_year_from_folder_name(folder_name)
                scores = score_candidate(incoming, card.get("title", ""), author, year)
            except Exception as err:
                print(f"WARNING: could not score candidate {card.get('path')!r} in course {course!r} ({err}); skipping.", file=sys.stderr)
                continue

            if scores["combined"] >= SURFACE_THRESHOLD:
                results.append({"course": course, "card": card, **scores})

    results.sort(key=lambda r: r["combined"], reverse=True)
    return results


def _dismissals_path(academic_hub_root: str) -> str:
    return os.path.join(academic_hub_root, ".index", "duplicate_dismissals.json")


def load_dismissals(academic_hub_root: str) -> list[dict]:
    path = _dismissals_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dismissals(academic_hub_root: str, dismissals: list[dict]) -> None:
    path = _dismissals_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dismissals, f, indent=2, ensure_ascii=False)


def is_dismissed(dismissals: list[dict], file_id_a: str, file_id_b: str) -> bool:
    pair = tuple(sorted([file_id_a, file_id_b]))
    return any(tuple(sorted([d["file_id_a"], d["file_id_b"]])) == pair for d in dismissals)


def record_dismissal(academic_hub_root: str, file_id_a: str, file_id_b: str) -> None:
    """No-op (does not duplicate) if this exact pair is already recorded --
    safe to call every time a user says 'no' without checking first."""
    dismissals = load_dismissals(academic_hub_root)
    if is_dismissed(dismissals, file_id_a, file_id_b):
        return
    a, b = sorted([file_id_a, file_id_b])
    dismissals.append({"file_id_a": a, "file_id_b": b, "dismissed_at": now_iso()})
    save_dismissals(academic_hub_root, dismissals)


def copy_duplicate_artifacts(
    academic_hub_root: str, canonical_course: str, canonical_card: dict,
    new_course: str, new_folder_category: str, new_source_pdf_path: str,
) -> dict:
    """Copies a confirmed duplicate's processed_outputs/<BookDir>/ tree
    into the new course and clones its index card (spec §5). The canonical
    card/files are never modified -- this only ever reads from the
    canonical location and writes to the new one."""
    canonical_book_dir = os.path.join(academic_hub_root, os.path.normpath(os.path.dirname(canonical_card["path"])))
    folder_name = os.path.basename(canonical_book_dir)

    new_processed_outputs_dir = os.path.join(academic_hub_root, new_course, new_folder_category, "processed_outputs")
    new_book_dir = os.path.join(new_processed_outputs_dir, folder_name)
    os.makedirs(new_processed_outputs_dir, exist_ok=True)
    if os.path.exists(new_book_dir):
        shutil.rmtree(new_book_dir)
    shutil.copytree(canonical_book_dir, new_book_dir)

    new_file_id = compute_id_from_parts([canonical_card["file_id"], new_course])
    new_card = dict(canonical_card)
    new_card["file_id"] = new_file_id
    new_card["course"] = new_course
    new_card["path"] = f"{new_course}/{new_folder_category}/processed_outputs/{folder_name}/{folder_name}.md"
    new_card["source_pdf_path"] = new_source_pdf_path
    new_card["duplicate_of_file_id"] = canonical_card["file_id"]
    new_card["source_updated_at"] = now_iso()

    cards = [c for c in load_shard(academic_hub_root, new_course) if c.get("file_id") != new_file_id]
    cards.append(new_card)
    save_shard(academic_hub_root, new_course, cards)
    recompute_course_entry(academic_hub_root, new_course)
    return new_card


def _default_academic_hub_root() -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "academic-hub")


def _prompt_yes_no(pdf_filename: str, candidate: dict) -> str:
    """Default interactive prompt -- only reached when non_interactive is
    False, i.e. a human is at a real terminal. An agent must always pass
    non_interactive=True (see convert_textbook_agent_instructions.md Step
    0.3) since this blocks on real stdin."""
    print(f"\nPossible duplicate: {pdf_filename}")
    print(f"  matches {candidate['course']}: {candidate['card']['title']} "
          f"(score {candidate['combined']:.2f}, file_id={candidate['card']['file_id']})")
    answer = input("  Same book? Skip conversion and copy artifacts? [y/N] ").strip().lower()
    return "yes" if answer == "y" else "no"


def run_duplicate_check(
    textbook_subdir: str, academic_hub_root: str, non_interactive: bool,
    resolutions: dict[str, str], prompt_fn=None,
) -> dict:
    """The orchestration Tasks 1-5 build up to (spec §1-6). Kept separate
    from main() so it's directly callable in-process (tests above; also
    lets a future caller skip the CLI/argparse layer entirely)."""
    prompt_fn = prompt_fn or _prompt_yes_no
    current_course = derive_course(textbook_subdir)
    new_folder_category = textbook_subdir.rstrip("/").split("/")[-1]

    pdf_dir = os.path.join(academic_hub_root, textbook_subdir)
    pdf_paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))

    dismissals = load_dismissals(academic_hub_root)
    to_convert: list[str] = []
    skipped: list[tuple] = []
    unresolved: list[dict] = []

    for pdf_path in pdf_paths:
        pdf_filename = os.path.basename(pdf_path)
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        try:
            exact = find_exact_duplicate(academic_hub_root, pdf_path, current_course)
        except Exception as err:
            print(f"WARNING: exact-match check failed for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            exact = None

        if exact is not None:
            canonical_course, canonical_card = exact
            copy_duplicate_artifacts(
                academic_hub_root, canonical_course, canonical_card,
                current_course, new_folder_category, rel_pdf_path,
            )
            skipped.append((pdf_filename, canonical_course, canonical_card["path"], "exact"))
            continue

        incoming_file_id = compute_file_id(pdf_path)
        try:
            incoming_bib = extract_bibliographic_info_from_filename(pdf_path)
            candidates = find_fuzzy_candidates(academic_hub_root, incoming_bib, current_course)
        except Exception as err:
            print(f"WARNING: fuzzy-match check failed for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            candidates = []

        candidates = [c for c in candidates if not is_dismissed(dismissals, incoming_file_id, c["card"]["file_id"])]

        if not candidates:
            to_convert.append(pdf_filename)
            continue

        best = candidates[0]
        decision = resolutions.get(incoming_file_id)
        if decision is None and not non_interactive:
            decision = prompt_fn(pdf_filename, best)

        if decision == "yes":
            copy_duplicate_artifacts(
                academic_hub_root, best["course"], best["card"],
                current_course, new_folder_category, rel_pdf_path,
            )
            skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
        elif decision == "no":
            record_dismissal(academic_hub_root, incoming_file_id, best["card"]["file_id"])
            dismissals = load_dismissals(academic_hub_root)
            to_convert.append(pdf_filename)
        else:
            to_convert.append(pdf_filename)
            unresolved.append({"pdf_filename": pdf_filename, "incoming_file_id": incoming_file_id, "candidates": candidates})

    return {"to_convert": to_convert, "skipped": skipped, "unresolved": unresolved}


def _print_report(result: dict) -> None:
    print("\n[Duplicate check]")
    print(f"  To convert ({len(result['to_convert'])}):")
    for name in result["to_convert"]:
        print(f"    - {name}")
    print(f"  Skipped -- duplicate found, artifacts copied ({len(result['skipped'])}):")
    for pdf_filename, course, path, tier in result["skipped"]:
        print(f"    - {pdf_filename}\n      -> {course}: {path} (tier: {tier})")
    if result["unresolved"]:
        print(f"  Needs confirmation -- rerun with --resolve ({len(result['unresolved'])}):")
        for item in result["unresolved"]:
            print(f"    - {item['pdf_filename']} (incoming file_id={item['incoming_file_id']})")
            for c in item["candidates"]:
                print(f"        -> {c['course']}: {c['card']['title']} (score {c['combined']:.2f}, file_id={c['card']['file_id']})")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-course duplicate textbook detection -- run before uploading PDFs "
                     "for conversion. See docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md",
    )
    parser.add_argument(
        "--textbook-subdir", required=True,
        help="Path relative to academic-hub/, e.g. academic_resources/microecon/textbooks (same value as the conversion instructions' Step 0.2).",
    )
    parser.add_argument("--academic-hub-root", default=None, help="Defaults to the academic-hub/ folder next to this project.")
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Never block on input(); Tier 2 candidates are reported under 'Needs confirmation' and left unresolved unless --resolve is given for them.",
    )
    parser.add_argument(
        "--resolve", action="append", default=[], metavar="FILE_ID=yes|no",
        help="Apply a decision for one Tier 2 candidate's incoming file_id (repeatable).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    resolutions: dict[str, str] = {}
    for entry in args.resolve:
        file_id, sep, decision = entry.partition("=")
        if not sep or decision not in ("yes", "no"):
            parser.error(f"--resolve {entry!r} must be FILE_ID=yes or FILE_ID=no")
        resolutions[file_id] = decision

    academic_hub_root = args.academic_hub_root or _default_academic_hub_root()
    result = run_duplicate_check(args.textbook_subdir, academic_hub_root, args.non_interactive, resolutions)
    _print_report(result)


if __name__ == "__main__":
    main()
