"""
chapter_index.py
Pure-Python helpers for building a chapter index from a textbook PDF --
either from its embedded outline, or bootstrapped from a parse of its own
rendered table of contents -- used by convert_textbook.py to align chunk
boundaries to chapter breaks and to tag output pages with physical PDF page
index and (where derivable) printed folio number.

Deliberately has NO dependency on marker, torch, or surya: convert_textbook.py
imports those at module scope, which requires the GCP VM's CUDA environment
to even succeed, so nothing that depends on them can be unit tested off that
VM. Everything in this module can be, on any machine with pypdf installed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ChapterEntry:
    title: str
    physical_page: int | None = None
    folio_page: int | None = None
    folio_is_roman: bool = False
    folio_raw: str | None = None


def get_outline_chapters(reader) -> list[ChapterEntry]:
    """
    Top-level (depth 1) entries from the PDF's embedded outline/bookmarks,
    resolved to physical page numbers. Never raises: returns [] if there's
    no outline, or if resolving any entry fails outright.
    """
    try:
        outline = reader.outline
    except Exception:
        return []
    if not outline:
        return []

    chapters = []
    for item in outline:
        # pypdf represents nested outline levels as sub-lists; only take
        # top-level Destination objects here, not nested lists (those are
        # subsections, which chunking deliberately ignores).
        if isinstance(item, list):
            continue
        try:
            page_num = reader.get_destination_page_number(item)
            title = str(item.title).strip()
        except Exception:
            continue
        if title:
            chapters.append(ChapterEntry(title=title, physical_page=page_num))
    return chapters


_ROMAN_CHARS = "ivxlcdm"
_ARABIC_FOLIO_RE = re.compile(r"^\d{1,4}$")
_ROMAN_FOLIO_RE = re.compile(r"^[ivxlcdm]{1,7}$", re.IGNORECASE)
_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
_ROMAN_TABLE = [
    (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
    (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
    (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
]


def _normalize_roman_ocr(token: str) -> str:
    """
    Corrects a common OCR confusion where a printed lowercase roman
    numeral 'i' is misread as lowercase 'l' -- confirmed against real
    output: Rudin's printed "ix" (9) came out as literal "lX". Only
    triggers on a leading lowercase 'l' immediately followed by another
    uppercase roman letter, since a genuine roman numeral is consistently
    cased within one token -- a lowercase 'l' next to an uppercase letter
    is itself the tell that this isn't a real roman numeral as typed.
    """
    if len(token) >= 2 and token[0] == "l" and token[1].isupper() and token[1].lower() in _ROMAN_CHARS:
        return "i" + token[1:]
    return token


def _int_to_roman(n: int) -> str:
    if n <= 0 or n > 3999:
        return ""
    result = []
    for value, symbol in _ROMAN_TABLE:
        while n >= value:
            result.append(symbol)
            n -= value
    return "".join(result)


def _roman_to_int(token: str) -> int | None:
    """Converts a roman numeral string to an int, or None if invalid.
    Round-trips the result back through _int_to_roman to reject
    non-canonical junk (e.g. "iiii", "vv") that naive subtractive-pair
    parsing would otherwise accept."""
    token = token.lower()
    if not token or any(ch not in _ROMAN_VALUES for ch in token):
        return None
    total, prev = 0, 0
    for ch in reversed(token):
        value = _ROMAN_VALUES[ch]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    if _int_to_roman(total) != token:
        return None
    return total


def _parse_folio_token(token: str) -> tuple[int | None, bool, str | None]:
    """
    Given a candidate trailing token from a TOC line or a page's own
    header/footer, returns (folio_page, is_roman, folio_raw), or
    (None, False, None) if it doesn't look like a folio number at all.
    """
    if _ARABIC_FOLIO_RE.match(token):
        return int(token), False, token
    # Reject ambiguous OCR noise: a single lowercase 'l' is not confidently correctable.
    if token == "l":
        return None, False, None
    normalized = _normalize_roman_ocr(token)
    if _ROMAN_FOLIO_RE.match(normalized):
        value = _roman_to_int(normalized)
        if value is not None:
            return value, True, token
    return None, False, None
