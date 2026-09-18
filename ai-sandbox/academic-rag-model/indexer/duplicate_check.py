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

import difflib
import re

from indexer.index_card import compute_file_id, find_card_by_file_id

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
