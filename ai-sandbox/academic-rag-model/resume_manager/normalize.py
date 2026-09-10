"""
normalize.py
Deterministic, section-aware chunking of the raw resume extraction into
the structured schema (schema.py) -- replaces Revision 2's LLM-based
extraction entirely (spec §3 Revision 3, per real evidence: the LLM
extraction step, not the raw text extraction itself, was the entire
source of every real bug found -- a miscategorized entry with dropped
bullets, a dropped-but-present thesis, and ~90 minutes of CPU-only Ollama
calls to get there).

The source document is a machine-generated, regularly-formatted resume:
section boundaries are marked by short header lines (fuzzy-matched
against known synonyms, not hardcoded to one exact phrase, so a
differently-worded resume export can still be recognized -- see
match_section_header()), and each section's entries follow a small
number of fixed line-shapes. No LLM call, no network, no sampling
variance: a value is either extracted from a recognized shape or the
parser raises ResumeParseError naming exactly what didn't match, rather
than silently guessing.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from resume_manager.schema import (
    AWARDS_REQUIRED, CONTACT_REQUIRED, EDUCATION_REQUIRED, PUBLICATIONS_REQUIRED,
    SKILLS_LIST_FIELDS, SKILLS_REQUIRED, WORK_EXPERIENCE_LIST_FIELDS, WORK_EXPERIENCE_REQUIRED,
    verify_entry_fields,
)

_NOT_SPECIFIED = "Not specified"
_ZERO_WIDTH_SPACE = "​"
_BULLET_PREFIX = "• "

_DATE_RANGE_RE = re.compile(r"^(?P<start>\d{2}/\d{4})\s*-\s*(?P<end>\d{2}/\d{4}|Present)$")
_GPA_RE = re.compile(r"^(?P<degree>.*?)\s*•\s*GPA:\s*(?P<gpa>.+)$")
_EDU_LOCATION_DATES_RE = re.compile(r"^(?P<location>.*?)\s*•\s*(?P<start>\d{2}/\d{4})\s*-\s*(?P<end>\d{2}/\d{4}|Present)$")
_THESIS_RE = re.compile(r"^Thesis:\s*(.+)$", re.IGNORECASE)
_AWARD_NAME_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<description>.+)\)$")
_PUBLISHED_AT_RE = re.compile(r"^Published at:\s*(.+)$", re.IGNORECASE)
_PAGE_TAG_RE = re.compile(r"<!--\s*page\s+\d+\s*-->")

_SECTION_SYNONYMS = {
    "work_experience": [
        "work experience", "professional experience", "employment history", "job experience", "experience",
    ],
    "education": ["education", "academic background", "educational background"],
    "awards": ["awards and scholarships", "honors and awards", "awards", "scholarships"],
    "publications": [
        "research presentations and publications", "presentations and publications", "publications", "presentations",
    ],
    "skills": ["skills", "technical skills", "core competencies"],
}
_SECTION_MATCH_THRESHOLD = 80
_MAX_HEADER_LINE_LENGTH = 60


class ResumeParseError(Exception):
    """Raised when the raw extraction doesn't match any recognized
    section/entry shape -- surfaced as a clear, specific failure rather
    than silently guessing (spec §3 Revision 3)."""


def _clean_text(text: str) -> str:
    """Strips zero-width spaces and collapses whitespace runs (including
    line-wrap newlines and non-breaking spaces) to a single space, without
    changing case -- this produces an actual field VALUE, unlike
    schema.py's comparison-only normalizer."""
    text = text.replace(_ZERO_WIDTH_SPACE, "")
    return re.sub(r"\s+", " ", text).strip()


def _strip_frontmatter_and_page_tags(raw_text: str) -> str:
    text = raw_text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + len("\n---"):]
    return _PAGE_TAG_RE.sub("", text)


def _split_lines(text: str) -> list[str]:
    return [_clean_text(line) for line in text.splitlines() if _clean_text(line)]


def _split_chunks(text: str) -> list[list[str]]:
    """Splits section text into blank-line-delimited chunks, each a list
    of its own cleaned, non-blank lines."""
    chunks: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = _clean_text(raw_line)
        if not line:
            if current:
                chunks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        chunks.append(current)
    return chunks


def match_section_header(line: str) -> str | None:
    """Fuzzy-matches a candidate line against known section-header
    synonyms -- not hardcoded to one exact phrase, so a differently-worded
    resume export can still be recognized (spec §3 Revision 3). Returns
    the matched category name, or None if the line isn't a recognized
    section header (too long, a bullet, or no synonym scores above
    threshold)."""
    candidate = _clean_text(line).lower().replace("&", "and")
    if not candidate or candidate.startswith("•") or len(candidate) > _MAX_HEADER_LINE_LENGTH:
        return None
    best_category, best_score = None, 0
    for category, synonyms in _SECTION_SYNONYMS.items():
        for synonym in synonyms:
            score = fuzz.ratio(candidate, synonym)
            if score > best_score:
                best_score, best_category = score, category
    return best_category if best_score >= _SECTION_MATCH_THRESHOLD else None


def _split_into_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_category: str | None = None
    for line in text.splitlines():
        category = match_section_header(line)
        if category:
            current_category = category
            sections.setdefault(category, [])
            continue
        if current_category:
            sections[current_category].append(line)
    return {category: "\n".join(lines_) for category, lines_ in sections.items()}


def _extract_name(text: str) -> str:
    for line in text.splitlines():
        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if match_section_header(cleaned):
            break
        return cleaned
    return _NOT_SPECIFIED


def _is_bullets_chunk(chunk: list[str]) -> bool:
    return chunk[0].startswith(_BULLET_PREFIX)


def _parse_bullets(chunk: list[str]) -> list[str]:
    bullets: list[str] = []
    for line in chunk:
        if line.startswith(_BULLET_PREFIX):
            bullets.append(line[len(_BULLET_PREFIX):].strip())
        elif bullets:
            bullets[-1] = f"{bullets[-1]} {line}".strip()
        else:
            raise ResumeParseError(f"bullet continuation line with no preceding bullet: {line!r}")
    return bullets


def _parse_work_experience(section_text: str) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for chunk in _split_chunks(section_text):
        if _is_bullets_chunk(chunk):
            if current is None:
                raise ResumeParseError(f"bullets with no preceding role: {chunk!r}")
            current["bullets"] = _parse_bullets(chunk)
            continue
        if len(chunk) == 4 and _DATE_RANGE_RE.match(chunk[1]):
            org, dates_line, role, location = chunk
            match = _DATE_RANGE_RE.match(dates_line)
            current = {
                "org": org, "role": role, "location": location,
                "start_date": match["start"], "end_date": match["end"], "bullets": [],
            }
            entries.append(current)
            continue
        if len(chunk) == 2:
            if current is None:
                raise ResumeParseError(f"role/location with no preceding employer: {chunk!r}")
            role, location = chunk
            current = {
                "org": current["org"], "role": role, "location": location,
                "start_date": _NOT_SPECIFIED, "end_date": _NOT_SPECIFIED, "bullets": [],
            }
            entries.append(current)
            continue
        raise ResumeParseError(f"unrecognized work-experience chunk shape: {chunk!r}")
    return entries


def _parse_education(section_text: str) -> list[dict]:
    lines = _split_lines(section_text)
    entries: list[dict] = []
    i = 0
    while i < len(lines):
        thesis_match = _THESIS_RE.match(lines[i])
        if thesis_match:
            if not entries:
                raise ResumeParseError(f"thesis line with no preceding education entry: {lines[i]!r}")
            entries[-1]["thesis"] = thesis_match.group(1).strip()
            i += 1
            continue
        if i + 2 >= len(lines):
            raise ResumeParseError(f"incomplete education entry starting at: {lines[i]!r}")
        institution, degree_line, location_dates_line = lines[i], lines[i + 1], lines[i + 2]
        gpa_match = _GPA_RE.match(degree_line)
        degree = gpa_match.group("degree").strip() if gpa_match else degree_line
        gpa = gpa_match.group("gpa").strip() if gpa_match else _NOT_SPECIFIED
        ld_match = _EDU_LOCATION_DATES_RE.match(location_dates_line)
        if not ld_match:
            raise ResumeParseError(f"unrecognized education location/dates line: {location_dates_line!r}")
        entries.append({
            "institution": institution, "degree": degree, "gpa": gpa,
            "location": ld_match.group("location").strip(),
            "start_date": ld_match.group("start"), "end_date": ld_match.group("end"),
            "thesis": _NOT_SPECIFIED,
        })
        i += 3
    return entries


def _parse_awards(section_text: str) -> list[dict]:
    lines = _split_lines(section_text)
    entries: list[dict] = []
    i = 0
    while i < len(lines):
        if i + 1 >= len(lines):
            raise ResumeParseError(f"incomplete award entry starting at: {lines[i]!r}")
        name_line, date_line = lines[i], lines[i + 1]
        match = _AWARD_NAME_RE.match(name_line)
        if match:
            name, description = match.group("name").strip(), match.group("description").strip()
        else:
            name, description = name_line, _NOT_SPECIFIED
        entries.append({"name": name, "description": description, "date": date_line})
        i += 2
    return entries


def _parse_publications(section_text: str) -> list[dict]:
    lines = _split_lines(section_text)
    entries: list[dict] = []
    i = 0
    while i < len(lines):
        published_match = _PUBLISHED_AT_RE.match(lines[i])
        if published_match:
            if not entries:
                raise ResumeParseError(f"'Published at:' line with no preceding publication: {lines[i]!r}")
            entries[-1]["link"] = published_match.group(1).strip()
            i += 1
            continue
        if i + 2 >= len(lines):
            raise ResumeParseError(f"incomplete publication entry starting at: {lines[i]!r}")
        title, date, venue = lines[i], lines[i + 1], lines[i + 2]
        entries.append({"title": title, "date": date, "venue": venue, "link": _NOT_SPECIFIED})
        i += 3
    return entries


def _parse_skills(section_text: str) -> list[dict]:
    entries: list[dict] = []
    current: dict | None = None
    for chunk in _split_chunks(section_text):
        if _is_bullets_chunk(chunk):
            if current is None:
                raise ResumeParseError(f"skill items with no preceding category: {chunk!r}")
            items: list[str] = []
            for bullet in _parse_bullets(chunk):
                items.extend(part.strip() for part in bullet.split(",") if part.strip())
            current["items"] = items
            continue
        current = {"category": " ".join(chunk), "items": []}
        entries.append(current)
    return entries


def extract_resume_schema(raw_text: str) -> dict | None:
    """Deterministically parses raw_text into the structured schema (spec
    §3 Revision 3) -- no LLM call, no network, no sampling variance.
    Returns None if the document doesn't match any recognized section/
    entry shape, the same failure contract as the old LLM-based version,
    so convert_resume.py needs no changes."""
    try:
        text = _strip_frontmatter_and_page_tags(raw_text)
        sections = _split_into_sections(text)
        if not sections:
            raise ResumeParseError("no recognizable resume sections found (no fuzzy-matched section header at all)")
        return {
            "contact": {
                "name": _extract_name(text), "location": _NOT_SPECIFIED, "email": _NOT_SPECIFIED,
                "linkedin_url": _NOT_SPECIFIED, "github_url": _NOT_SPECIFIED, "website_url": _NOT_SPECIFIED,
            },
            "work_experience": _parse_work_experience(sections.get("work_experience", "")),
            "education": _parse_education(sections.get("education", "")),
            "awards": _parse_awards(sections.get("awards", "")),
            "publications": _parse_publications(sections.get("publications", "")),
            "skills": _parse_skills(sections.get("skills", "")),
        }
    except ResumeParseError as err:
        print(f"WARNING: deterministic resume parsing failed: {err}")
        return None


def verify_extraction(parsed: dict, raw_text: str) -> list[str]:
    """Schema-level verification (spec §3 step 4): every required field on
    every entry must be non-empty and traceable to raw_text. Kept as a
    defense-in-depth check on the parser's own correctness -- a
    deterministically-extracted value is traceable to raw_text by
    construction, so this should always report clean; a real problem here
    would mean a parser regex captured the wrong thing. Returns a list of
    human-readable problems; empty means a clean pass."""
    problems: list[str] = []
    problems += verify_entry_fields(parsed.get("contact") or {}, raw_text, CONTACT_REQUIRED)
    for entry in parsed.get("work_experience") or []:
        problems += verify_entry_fields(entry, raw_text, WORK_EXPERIENCE_REQUIRED, WORK_EXPERIENCE_LIST_FIELDS)
    for entry in parsed.get("education") or []:
        problems += verify_entry_fields(entry, raw_text, EDUCATION_REQUIRED)
    for entry in parsed.get("awards") or []:
        problems += verify_entry_fields(entry, raw_text, AWARDS_REQUIRED)
    for entry in parsed.get("publications") or []:
        problems += verify_entry_fields(entry, raw_text, PUBLICATIONS_REQUIRED)
    for entry in parsed.get("skills") or []:
        problems += verify_entry_fields(entry, raw_text, SKILLS_REQUIRED, SKILLS_LIST_FIELDS)
    return problems
