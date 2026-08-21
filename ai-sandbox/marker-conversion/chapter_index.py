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

import difflib
import logging
import re
from collections import Counter
from dataclasses import dataclass


_logger = logging.getLogger(__name__)


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


_CHAPTER_WORD_RE = re.compile(r"^chapter\s+\d+\b[.:]?\s*(.*)$", re.IGNORECASE)
_CHAPTER_WORD_NUM_RE = re.compile(r"^chapter\s+(\d+)\b", re.IGNORECASE)
_STANDALONE_CHAPTER_MARKER_RE = re.compile(r"^chapter\s+(\d+)\s*$", re.IGNORECASE)
_BARE_CHAPTER_NUM_RE = re.compile(r"^(\d+)\.?\s+(\S.*)$")
_TOC_LINK_RE = re.compile(r"\[([^\]]*)\]\(#page-(\d+)-\d+\)")


def _cells_from_markdown_line(line: str) -> str:
    """Joins a markdown table row's non-empty, non-separator cells with a
    single space. For a non-table line, strips a leading heading marker
    (#, ##, ...) and returns the rest unchanged."""
    stripped = re.sub(r"^#{1,6}\s*", "", line.strip())
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        cells = [c for c in cells if c and not re.fullmatch(r"-+", c)]
        return " ".join(cells)
    return stripped


def _strip_markdown_inline(text: str) -> tuple[str, int | None]:
    """
    Strips bold/italic markup and <b>/<i> tags. If a markdown link
    [text](#page-N-M) is present, replaces it with its visible text and
    separately returns the physical page N; otherwise returns
    (cleaned_text, None).
    """
    physical_page = None
    m = _TOC_LINK_RE.search(text)
    if m:
        physical_page = int(m.group(2))
        text = text[: m.start()] + m.group(1) + text[m.end() :]
    text = re.sub(r"</?b>|</?i>", "", text)
    text = re.sub(r"[*_]{1,3}", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, physical_page


def parse_printed_toc(markdown_text: str) -> list[ChapterEntry]:
    """
    Extracts chapter-level (title, physical_page, folio_page) entries from
    a book's own rendered table of contents. Scans every line rather than
    trying to detect a TOC "region" -- the chapter-level match itself
    (Chapter N prefix, bare N. prefix, or a preceding standalone Chapter N
    marker line) is specific enough not to false-positive on body prose,
    and this also means a TOC split across multiple separate markdown
    tables (observed in Rudin, due to a page break mid-TOC) is handled
    without any special-casing. Subsection-level entries and non-chapter
    front-matter entries (Preface, Acknowledgments, ...) are silently
    skipped, not raised on -- confirmed necessary by a garbled OCR line
    observed in Axler's own subsection entries.
    """
    chapters: list[ChapterEntry] = []
    pending_chapter_num: str | None = None

    for raw_line in markdown_text.splitlines():
        joined = _cells_from_markdown_line(raw_line)
        if not joined:
            continue
        text, physical_page = _strip_markdown_inline(joined)
        if not text:
            continue

        standalone = _STANDALONE_CHAPTER_MARKER_RE.match(text)
        if standalone:
            pending_chapter_num = standalone.group(1)
            continue

        chapter_num, remainder = None, text
        m = _CHAPTER_WORD_NUM_RE.match(text)
        if m:
            chapter_num = m.group(1)
            remainder = _CHAPTER_WORD_RE.match(text).group(1)
        else:
            m = _BARE_CHAPTER_NUM_RE.match(text)
            if m:
                chapter_num, remainder = m.group(1), m.group(2)
            elif pending_chapter_num is not None:
                chapter_num, remainder = pending_chapter_num, text

        pending_chapter_num = None  # consumed either way -- one shot

        if chapter_num is None:
            continue

        tokens = remainder.rsplit(None, 1)
        if len(tokens) != 2:
            continue
        title_text, last_token = tokens
        folio_page, folio_is_roman, folio_raw = _parse_folio_token(last_token)
        if folio_page is None:
            continue

        title_text = title_text.strip(" .")
        if not title_text:
            continue

        chapters.append(
            ChapterEntry(
                title=title_text,
                physical_page=physical_page,
                folio_page=folio_page,
                folio_is_roman=folio_is_roman,
                folio_raw=folio_raw,
            )
        )

    return chapters


def detect_printed_folio(page_text: str) -> tuple[int, bool, str] | None:
    """
    Given the markdown slice for one physical page, checks the first and
    last non-empty lines for something that looks like a printed page
    number (arabic or roman, <=4 chars) -- last line checked first, since
    footers are more common than headers for page numbers in textbooks.
    Returns (folio_page, is_roman, raw_token), or None if neither line
    qualifies (expected for pages that don't print a folio at all, or
    where it wasn't OCR'd cleanly).
    """
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return None
    for candidate in (lines[-1], lines[0]):
        if len(candidate) > 4:
            continue
        folio_page, is_roman, raw = _parse_folio_token(candidate)
        if folio_page is not None:
            return folio_page, is_roman, raw
    return None


def _normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"^chapter\s+\d+[.:]?\s*", "", t)
    t = re.sub(r"[^\w\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def match_chapter_titles(
    a: list[ChapterEntry], b: list[ChapterEntry]
) -> list[tuple[ChapterEntry, ChapterEntry]]:
    """
    Fuzzy-matches titles between two chapter lists (e.g. outline-sourced
    physical pages vs. TOC-parsed folio numbers). Returns matched pairs
    only; unmatched entries on either side are dropped silently.
    """
    pairs = []
    used_b: set[int] = set()
    for entry_a in a:
        norm_a = _normalize_title(entry_a.title)
        best_idx, best_ratio = None, 0.0
        for idx, entry_b in enumerate(b):
            if idx in used_b:
                continue
            ratio = difflib.SequenceMatcher(None, norm_a, _normalize_title(entry_b.title)).ratio()
            if ratio > best_ratio:
                best_ratio, best_idx = ratio, idx
        if best_idx is not None and best_ratio > 0.8:
            pairs.append((entry_a, b[best_idx]))
            used_b.add(best_idx)
    return pairs


def compute_folio_offset(
    outline_chapters: list[ChapterEntry], toc_chapters: list[ChapterEntry]
) -> int | None:
    """
    Computes physical_page - folio_page from title-matched pairs (roman
    folios excluded -- they aren't part of the book's linear arabic
    sequence). Returns the consensus offset if a majority of samples agree
    within +/-1; otherwise logs a WARNING with the disagreement and returns
    None -- callers must treat None as "don't tag folio numbers," not 0.
    """
    samples = []
    for entry_a, entry_b in match_chapter_titles(outline_chapters, toc_chapters):
        physical = entry_a.physical_page if entry_a.physical_page is not None else entry_b.physical_page
        folio = entry_b.folio_page if entry_b.folio_page is not None else entry_a.folio_page
        is_roman = entry_a.folio_is_roman or entry_b.folio_is_roman
        if physical is not None and folio is not None and not is_roman:
            samples.append(physical - folio)

    if len(samples) < 2:
        _logger.warning(
            "Not enough matched chapter samples to compute a folio offset (%d found, need >=2).",
            len(samples),
        )
        return None

    counts = Counter(samples)
    consensus_offset, _ = counts.most_common(1)[0]
    agreeing = sum(c for value, c in counts.items() if abs(value - consensus_offset) <= 1)
    if agreeing < max(2, len(samples) // 2 + 1):
        _logger.warning("Folio offset samples disagree: %s -- not tagging folio numbers for this book.", dict(counts))
        return None
    return consensus_offset


_PAGE_MARKER_RE = re.compile(r"<!-- page (\d+) -->")


def bootstrap_chapter_index_from_front_matter(
    front_matter_text: str,
) -> tuple[list[ChapterEntry], int | None]:
    """
    Used when there's no embedded PDF outline. Given the already-converted,
    already-page-tagged markdown of the front-matter chunk: parses its own
    printed TOC, then finds the one physical page in that same chunk whose
    own printed folio matches the TOC's first chapter -- from that single
    anchor, every other TOC entry's physical page follows by arithmetic
    (physical = folio + offset).
    """
    toc_chapters = parse_printed_toc(front_matter_text)
    if not toc_chapters:
        _logger.warning("No parseable table of contents found in front matter; falling back to no chapter awareness.")
        return [], None

    boundaries = [(m.start(), int(m.group(1))) for m in _PAGE_MARKER_RE.finditer(front_matter_text)]
    if not boundaries:
        _logger.warning("No page markers found in front matter text; cannot anchor TOC to physical pages.")
        return [], None

    first_folio = toc_chapters[0].folio_page
    anchor_physical = None
    for idx, (start, physical_page) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(front_matter_text)
        detected = detect_printed_folio(front_matter_text[start:end])
        if detected is not None and detected[0] == first_folio and not detected[1]:
            anchor_physical = physical_page
            break

    if anchor_physical is None:
        _logger.warning(
            "Could not find a physical page whose own printed folio matches the TOC's first "
            "chapter (folio %s); falling back to no chapter awareness.",
            first_folio,
        )
        return [], None

    offset = anchor_physical - first_folio
    resolved = [
        ChapterEntry(
            title=entry.title,
            physical_page=entry.folio_page + offset,
            folio_page=entry.folio_page,
            folio_is_roman=False,
            folio_raw=entry.folio_raw,
        )
        for entry in toc_chapters
        if not entry.folio_is_roman and entry.folio_page is not None and entry.folio_page >= first_folio
    ]
    return resolved, offset
