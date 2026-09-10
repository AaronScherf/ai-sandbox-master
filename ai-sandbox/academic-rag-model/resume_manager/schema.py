"""
schema.py
The structured master-resume schema (spec §3 Revision 2): field lists per
category, stable id assignment, and a generic required-field/traceability
check shared by normalize.py's extraction verification.
"""
from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "entry"


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_for_comparison(text: str) -> str:
    """Collapses any run of whitespace (including non-breaking spaces and
    line-wrap newlines) to a single space, and lowercases, before a
    traceability comparison. Confirmed real (2026-09-09) against the
    actual resume bootstrap: the source PDF's text layer line-wraps
    mid-sentence and uses non-breaking/doubled spacing in places, which
    the LLM correctly normalizes when extracting flowing prose -- a
    literal substring check flagged that faithful normalization as
    "invented" on nearly every bullet and degree line. Lowercasing too,
    since the LLM also legitimately re-capitalizes a sentence-initial
    word when lifting a parenthetical into its own field."""
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


CONTACT_REQUIRED = ["name", "location", "email", "linkedin_url", "github_url", "website_url"]
WORK_EXPERIENCE_REQUIRED = ["org", "role", "location", "start_date", "end_date"]
WORK_EXPERIENCE_LIST_FIELDS = ["bullets"]
EDUCATION_REQUIRED = ["institution", "degree", "location", "start_date", "end_date"]
AWARDS_REQUIRED = ["name", "description", "date"]
PUBLICATIONS_REQUIRED = ["title", "date", "venue"]
SKILLS_REQUIRED = ["category"]
SKILLS_LIST_FIELDS = ["items"]


def assign_ids(entries: list[dict], key_field: str) -> None:
    """Mutates each entry in place, adding a stable 'id' slug derived from
    key_field (e.g. 'org' for work_experience, 'institution' for
    education), disambiguated with an ordinal for duplicates -- never left
    to the LLM to invent (spec §3)."""
    seen: dict[str, int] = {}
    for entry in entries:
        base = slugify(str(entry.get(key_field, "")))
        seen[base] = seen.get(base, 0) + 1
        entry["id"] = f"{base}-{seen[base]}"


def verify_entry_fields(
    entry: dict, raw_text: str, required_fields: list[str], list_fields: list[str] = (),
) -> list[str]:
    """Returns human-readable problems for one entry: an empty required
    field, a required field whose value isn't traceable as a substring of
    raw_text, or a list-field item that's empty or untraceable (spec §3
    step 4). 'end_date' is exempt from the traceability check when its
    value is the literal "Present" -- a source resume showing no end date
    for an ongoing role has nothing to trace that sentinel to. Entry
    identified in messages by its 'id' if present."""
    label = entry.get("id") or "<entry>"
    normalized_raw = _normalize_for_comparison(raw_text)
    problems: list[str] = []
    for field in required_fields:
        value = entry.get(field)
        if not value:
            problems.append(f"{label}: required field '{field}' is empty")
            continue
        if field == "end_date" and value == "Present":
            continue
        if _normalize_for_comparison(str(value)) not in normalized_raw:
            problems.append(f"{label}: field '{field}' value '{value}' not found in raw extraction")
    for field in list_fields:
        for item in entry.get(field) or []:
            if not item:
                problems.append(f"{label}: an item in '{field}' is empty")
            elif _normalize_for_comparison(str(item)) not in normalized_raw:
                problems.append(f"{label}: '{field}' item '{item}' not found in raw extraction")
    return problems
