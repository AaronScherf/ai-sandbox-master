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

# At or above this score, a Tier 2 match auto-resolves immediately
# instead of blocking on a human decision (pipeline-autonomy-policies
# spec, Component 1a) -- an initial judgment call, not derived from data;
# revisit once real runs provide a score distribution to tune against.
# Below it (but still >= SURFACE_THRESHOLD above), behavior is unchanged
# from before this policy existed: always surfaced, never auto-resolved --
# this is deliberately where the Mas-Colell/Rubinstein-style false-
# positive risk concentrates (see tests/test_duplicate_check.py's
# TestScoreCandidate.test_similar_but_different_books_surface_above_threshold).
AUTO_SKIP_THRESHOLD = 0.85


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


def find_exact_duplicate(academic_hub_root: str, pdf_path: str, current_course: str, file_id: str | None = None) -> tuple[str, dict] | None:
    """Tier 1 (spec §3): byte-identical duplicate in a *different* course.
    find_card_by_file_id() already searches every course unconditionally
    (indexer/index_card.py), so no change is needed there -- this just
    excludes a match that happens to already be in the current course,
    which is convert_textbook.py's own existing same-run skip check's
    job, not this module's.

    `file_id` is optional -- pass it when a caller (run_duplicate_check)
    has already hashed the same PDF for another purpose, so this doesn't
    redundantly re-read and re-hash a potentially large file. Computed
    here as before when omitted, so every existing/independent caller
    (including this module's own tests) is unaffected."""
    if file_id is None:
        file_id = compute_file_id(pdf_path)

    # The current course's OWN shard is checked first, before the global
    # lookup, because find_card_by_file_id() returns the first match in
    # list_courses()'s *sorted* order -- so a book that already has cards
    # in both this course and an alphabetically-earlier other course would
    # otherwise be reported as a cross-course duplicate and pointlessly
    # cloned, masking the fact that this course already has it. A
    # same-course hit is convert_textbook.py's own reconciliation job.
    if any(card.get("file_id") == file_id for card in load_shard(academic_hub_root, current_course)):
        return None

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
    """Deliberately one level DOWN inside .index/, not directly in it:
    indexer.index_card.list_courses() treats every `*.json` file that is a
    direct child of `.index/` (except courses.json/tags.json) as a course
    shard, so a `.index/duplicate_dismissals.json` would surface as a
    phantom course named "duplicate_dismissals" -- and index_search.py's
    `rebuild --prune` would then walk that "shard", find none of its
    entries backed by a real file, and delete every recorded dismissal.
    list_courses() only ever scans direct children, never subdirectories,
    so `.index/duplicates/` is structurally outside its namespace."""
    return os.path.join(academic_hub_root, ".index", "duplicates", "dismissals.json")


def _pending_confirmation_path(academic_hub_root: str) -> str:
    """Same nested-path reasoning as _dismissals_path above -- a flat
    .index/-level file would be misread as a phantom course by
    list_courses() and eventually deleted by `rebuild --prune`. Lives in
    the same .index/duplicates/ directory as dismissals.json, git-tracked
    the same way (durable index state, not run-local scratch output)."""
    return os.path.join(academic_hub_root, ".index", "duplicates", "pending_confirmation.json")


def load_pending_confirmations(academic_hub_root: str) -> list[dict]:
    path = _pending_confirmation_path(academic_hub_root)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_pending_confirmations(academic_hub_root: str, entries: list[dict]) -> None:
    path = _pending_confirmation_path(academic_hub_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def record_pending_confirmation(academic_hub_root: str, entry: dict) -> None:
    entries = load_pending_confirmations(academic_hub_root)
    entries.append(entry)
    save_pending_confirmations(academic_hub_root, entries)


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
    """Tolerates a hand-edited entry that isn't a well-formed
    {"file_id_a","file_id_b"} dict -- such an entry simply doesn't match
    anything, rather than raising and taking the whole run down with it
    (same degrade-don't-crash rule as the rest of this module)."""
    pair = tuple(sorted([file_id_a, file_id_b]))
    for d in dismissals:
        if not isinstance(d, dict):
            continue
        a, b = d.get("file_id_a"), d.get("file_id_b")
        if a is None or b is None:
            continue
        if tuple(sorted([a, b])) == pair:
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


def copy_duplicate_artifacts(
    academic_hub_root: str, canonical_course: str, canonical_card: dict,
    new_course: str, new_folder_category: str, new_source_pdf_path: str,
    pending_confirmation: bool = False,
) -> dict:
    """Copies a confirmed duplicate's processed_outputs/<BookDir>/ tree
    into the new course and clones its index card (spec §5). The canonical
    card/files are never modified -- this only ever reads from the
    canonical location and writes to the new one.

    Every path is derived from `new_source_pdf_path` (the real relative
    path of the PDF that triggered this check, e.g.
    `academic_resources/microecon/textbooks/Ok.pdf`) rather than rebuilt
    from `new_course`/`new_folder_category`: the latter silently dropped
    the leading `academic_resources/` segment that every real card carries
    (convert_textbook.py derives its own `rel_md_path` the same way, from
    the PDF's own path) and that every reader expects -- notably
    index_search.py's `_textbook_book_dirs`, which only ever walks
    `academic_resources/<course>/<category>/processed_outputs`.

    `new_folder_category` is retained purely as a sanity check against the
    category segment derived from the PDF path; a mismatch is a caller bug
    worth a warning, not worth failing the copy over."""
    canonical_book_dir = os.path.join(academic_hub_root, os.path.normpath(os.path.dirname(canonical_card["path"])))
    folder_name = os.path.basename(canonical_book_dir)

    rel_category_dir = os.path.dirname(new_source_pdf_path.replace(os.sep, "/")).strip("/")
    if not rel_category_dir:
        raise ValueError(
            f"new_source_pdf_path {new_source_pdf_path!r} has no parent directory; "
            f"expected something like academic_resources/<course>/<category>/<Book>.pdf",
        )
    derived_category = rel_category_dir.rsplit("/", 1)[-1]
    if new_folder_category and derived_category != new_folder_category:
        print(f"WARNING: folder category {new_folder_category!r} does not match the one derived from "
              f"{new_source_pdf_path!r} ({derived_category!r}); using the path-derived one.", file=sys.stderr)

    rel_new_book_dir = f"{rel_category_dir}/processed_outputs/{folder_name}"
    new_book_dir = os.path.join(academic_hub_root, os.path.normpath(rel_new_book_dir))
    os.makedirs(os.path.dirname(new_book_dir), exist_ok=True)
    if os.path.exists(new_book_dir):
        shutil.rmtree(new_book_dir)
    shutil.copytree(canonical_book_dir, new_book_dir)

    new_file_id = compute_id_from_parts([canonical_card["file_id"], new_course])

    # The copied _metadata.json is a byte-for-byte clone and so still names
    # the CANONICAL course's PDF. index_search.py's `rebuild` textbook
    # backfill reads source_pdf_path (not source_pdf_file_id -- that field
    # is written but never read back by rebuild) to locate a file to hash
    # via compute_file_id(), then derives `course_name` from that same
    # path string. Repointing source_pdf_path at the new course's own PDF
    # keeps `_metadata.json` internally consistent (describe_images.py
    # does key off source_pdf_file_id) and is directionally correct, but
    # it is NOT what actually prevents rebuild-corruption for a Tier 1
    # (byte-identical) clone -- hashing the new course's copy always
    # yields the same file_id as canonical, repointed or not. The
    # `duplicate_of_file_id` field written below is what actually fixes
    # that: index_search.py's rebuild() recognizes it and skips re-hashing
    # this directory entirely (see
    # docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md
    # Component 3). A failure here leaves an already-successful copy in
    # place, so it warns rather than unwinding the whole copy.
    metadata_path = os.path.join(new_book_dir, f"{folder_name}_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            metadata["source_pdf_path"] = new_source_pdf_path
            metadata["source_pdf_file_id"] = new_file_id
            metadata["duplicate_of_file_id"] = canonical_card["file_id"]
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
        except Exception as err:
            print(f"WARNING: could not repoint {folder_name}_metadata.json at the new course's PDF ({err}); "
                  f"a future `index_search.py rebuild` over {new_course!r} may misattribute this book.", file=sys.stderr)

    new_card = dict(canonical_card)
    new_card["file_id"] = new_file_id
    new_card["course"] = new_course
    new_card["path"] = f"{rel_new_book_dir}/{folder_name}.md"
    new_card["source_pdf_path"] = new_source_pdf_path
    new_card["duplicate_of_file_id"] = canonical_card["file_id"]
    new_card["source_updated_at"] = now_iso()
    if pending_confirmation:
        # High-confidence auto-skip (pipeline-autonomy-policies spec,
        # Component 1a) -- distinguishes this clone from a Tier 1 exact
        # match or a human-confirmed Tier 2 "yes", neither of which needs
        # post-hoc review. Absent (not False) on every other call, so
        # existing/older cards never gain a meaningless extra key.
        new_card["duplicate_pending_confirmation"] = True

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

    # A hand-edited/truncated dismissals file must not take down a whole
    # batch before a single PDF is even looked at -- same degrade-safely
    # rule every other step in this loop already follows. Falling back to
    # "nothing was ever dismissed" is the safe direction: the worst case is
    # being re-asked about a pair already dismissed, versus losing the run.
    try:
        dismissals = load_dismissals(academic_hub_root)
        if not isinstance(dismissals, list):
            raise ValueError(f"expected a list of dismissal entries, got {type(dismissals).__name__}")
    except Exception as err:
        print(f"WARNING: could not load dismissals from {_dismissals_path(academic_hub_root)} ({err}); "
              f"treating nothing as previously dismissed.", file=sys.stderr)
        dismissals = []

    to_convert: list[str] = []
    skipped: list[tuple] = []
    unresolved: list[dict] = []
    auto_skipped_pending_confirmation: list[dict] = []

    for pdf_path in pdf_paths:
        pdf_filename = os.path.basename(pdf_path)
        rel_pdf_path = os.path.relpath(pdf_path, academic_hub_root).replace(os.sep, "/")

        # Computed once and reused below (find_exact_duplicate accepts it
        # directly) rather than re-reading/re-hashing a potentially large
        # PDF a second time. Guarded like every other per-candidate step:
        # a failure here must degrade this one PDF to "no match found",
        # never crash the whole batch (spec §6).
        try:
            incoming_file_id = compute_file_id(pdf_path)
        except Exception as err:
            print(f"WARNING: could not compute file_id for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            to_convert.append(pdf_filename)
            continue

        try:
            exact = find_exact_duplicate(academic_hub_root, pdf_path, current_course, file_id=incoming_file_id)
        except Exception as err:
            print(f"WARNING: exact-match check failed for {pdf_filename} ({err}); treating as no match.", file=sys.stderr)
            exact = None

        if exact is not None:
            canonical_course, canonical_card = exact
            try:
                copy_duplicate_artifacts(
                    academic_hub_root, canonical_course, canonical_card,
                    current_course, new_folder_category, rel_pdf_path,
                )
                skipped.append((pdf_filename, canonical_course, canonical_card["path"], "exact"))
            except Exception as err:
                # Copy didn't actually succeed -- reporting this as
                # "skipped" would be a lie (the new course would have no
                # artifacts at all). Fail toward converting instead
                # (spec §6) so nothing is silently lost.
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
            continue

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

        if decision is None and best["combined"] >= AUTO_SKIP_THRESHOLD:
            # High-confidence auto-skip (spec Component 1a) -- only when
            # no explicit --resolve decision was already given for this
            # exact incoming_file_id; an explicit decision always wins.
            try:
                new_card = copy_duplicate_artifacts(
                    academic_hub_root, best["course"], best["card"],
                    current_course, new_folder_category, rel_pdf_path,
                    pending_confirmation=True,
                )
                skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
                pending_entry = {
                    "incoming_file_id": incoming_file_id, "pdf_filename": pdf_filename,
                    "course": current_course, "matched_course": best["course"],
                    "matched_file_id": best["card"]["file_id"],
                    "matched_title": best["card"].get("title", ""),
                    "score": best["combined"], "new_card_file_id": new_card["file_id"],
                    "queued_at": now_iso(),
                }
                try:
                    record_pending_confirmation(academic_hub_root, pending_entry)
                except Exception as err:
                    # The copy already succeeded -- losing this record
                    # would hide a clone that still needs review, not lose
                    # the clone itself. Still surface it in THIS run's own
                    # report even if it couldn't be persisted for later.
                    print(f"WARNING: could not persist pending-confirmation record for {pdf_filename} ({err}); "
                          f"it will not appear in a later --review-pending until this is retried.", file=sys.stderr)
                auto_skipped_pending_confirmation.append(pending_entry)
            except Exception as err:
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
            continue

        if decision is None and not non_interactive:
            decision = prompt_fn(pdf_filename, best)

        if decision == "yes":
            try:
                copy_duplicate_artifacts(
                    academic_hub_root, best["course"], best["card"],
                    current_course, new_folder_category, rel_pdf_path,
                )
                skipped.append((pdf_filename, best["course"], best["card"]["path"], "fuzzy"))
            except Exception as err:
                print(f"WARNING: could not copy duplicate artifacts for {pdf_filename} ({err}); converting instead.", file=sys.stderr)
                to_convert.append(pdf_filename)
        elif decision == "no":
            try:
                record_dismissal(academic_hub_root, incoming_file_id, best["card"]["file_id"])
                dismissals = load_dismissals(academic_hub_root)
            except Exception as err:
                # The user's "no" decision still holds for this run even
                # if persisting it failed -- worst case it gets asked
                # again next run, which is safe, just mildly annoying.
                print(f"WARNING: could not record dismissal for {pdf_filename} ({err}); it may be re-prompted next run.", file=sys.stderr)
            to_convert.append(pdf_filename)
        else:
            to_convert.append(pdf_filename)
            unresolved.append({"pdf_filename": pdf_filename, "incoming_file_id": incoming_file_id, "candidates": candidates})

    return {
        "to_convert": to_convert, "skipped": skipped, "unresolved": unresolved,
        "auto_skipped_pending_confirmation": auto_skipped_pending_confirmation,
    }


def _print_report(result: dict) -> None:
    print("\n[Duplicate check]")
    print(f"  To convert ({len(result['to_convert'])}):")
    for name in result["to_convert"]:
        print(f"    - {name}")
    print(f"  Skipped -- duplicate found, artifacts copied ({len(result['skipped'])}):")
    for pdf_filename, course, path, tier in result["skipped"]:
        print(f"    - {pdf_filename}\n      -> {course}: {path} (tier: {tier})")
    if result["auto_skipped_pending_confirmation"]:
        print(f"  Auto-skipped as likely duplicate -- please confirm ({len(result['auto_skipped_pending_confirmation'])}):")
        for entry in result["auto_skipped_pending_confirmation"]:
            print(f"    - {entry['pdf_filename']}\n      -> {entry['matched_course']}: {entry['matched_title']} "
                  f"(score {entry['score']:.2f}, incoming file_id={entry['incoming_file_id']})")
        print("    Review with: python -m indexer.duplicate_check --review-pending")
    if result["unresolved"]:
        print(f"  Needs confirmation -- rerun with --resolve ({len(result['unresolved'])}):")
        for item in result["unresolved"]:
            print(f"    - {item['pdf_filename']} (incoming file_id={item['incoming_file_id']})")
            for c in item["candidates"]:
                print(f"        -> {c['course']}: {c['card']['title']} (score {c['combined']:.2f}, file_id={c['card']['file_id']})")


def _print_pending_confirmations(entries: list[dict]) -> None:
    print(f"\n[Pending duplicate confirmations] ({len(entries)}):")
    for entry in entries:
        print(f"  - {entry['pdf_filename']} (course={entry.get('course', '?')})")
        print(f"      -> {entry.get('matched_course', '?')}: {entry.get('matched_title', '?')} "
              f"(score {entry.get('score', 0):.2f}, incoming file_id={entry.get('incoming_file_id', '?')})")
    if entries:
        print("  Confirm with: python -m indexer.duplicate_check --confirm-pending FILE_ID")
        print("  Reject with:  python -m indexer.duplicate_check --reject-pending FILE_ID")


def write_to_convert_file(path: str, to_convert: list[str]) -> None:
    """Writes the final to-convert filenames, one per line, for the calling
    shell to read straight back into PDF_FILENAMES. This exists because a
    confirmed duplicate's *source PDF is deliberately never deleted* (spec
    §5 only ever copies artifacts into the new course), so the conversion
    instructions' old "just re-glob TEXTBOOK_SUBDIR" step returned the
    identical file list as before the check and reconverted the very book
    that was just resolved. An empty to_convert writes an empty file --
    `mapfile -t` then yields a zero-length array, which both instructions
    documents already branch on as "nothing left to convert".

    `newline="\n"` is deliberate, not a default: this file is always read
    back by a bash `mapfile`, never by a Windows-native tool, so it must
    stay LF-only regardless of platform. Without it, Python's text-mode
    write on Windows translates every "\n" to "\r\n" -- `mapfile -t` only
    strips the trailing "\n", so each filename comes back with an
    invisible trailing "\r" that breaks every path built from it.
    Confirmed live running this exact command from Windows Git Bash."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for name in to_convert:
            f.write(f"{name}\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-course duplicate textbook detection -- run before uploading PDFs "
                     "for conversion. See docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md",
    )
    parser.add_argument(
        "--textbook-subdir", default=None,
        help="Path relative to academic-hub/, e.g. academic_resources/microecon/textbooks (same value as the conversion instructions' Step 0.2). "
             "Required unless --review-pending, --confirm-pending, or --reject-pending is given.",
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
    parser.add_argument(
        "--emit-to-convert", default=None, metavar="PATH",
        help="Also write the final 'to convert' PDF filenames (one per line) to PATH, in addition to the "
             "human-readable report on stdout. Read it back with `mapfile -t PDF_FILENAMES < PATH`: a confirmed "
             "duplicate's source PDF is deliberately never deleted, so re-globbing the folder would re-include it.",
    )
    parser.add_argument(
        "--review-pending", action="store_true",
        help="List every pending duplicate-confirmation entry across all courses, instead of running a normal "
             "check against --textbook-subdir.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    academic_hub_root = args.academic_hub_root or _default_academic_hub_root()

    if args.review_pending:
        _print_pending_confirmations(load_pending_confirmations(academic_hub_root))
        return

    if not args.textbook_subdir:
        parser.error("--textbook-subdir is required unless --review-pending is given")

    resolutions: dict[str, str] = {}
    for entry in args.resolve:
        file_id, sep, decision = entry.partition("=")
        if not sep or decision not in ("yes", "no"):
            parser.error(f"--resolve {entry!r} must be FILE_ID=yes or FILE_ID=no")
        resolutions[file_id] = decision

    result = run_duplicate_check(args.textbook_subdir, academic_hub_root, args.non_interactive, resolutions)
    _print_report(result)
    if args.emit_to_convert:
        write_to_convert_file(args.emit_to_convert, result["to_convert"])
        print(f"\n  Wrote {len(result['to_convert'])} filename(s) to {args.emit_to_convert}")


if __name__ == "__main__":
    main()
