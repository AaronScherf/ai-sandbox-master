"""
bib_info.py
Pure-Python helpers for deriving a book's author_title_year folder name
from its (possibly incomplete) bibliographic info, plus the filename-based
fallback tier for filling in gaps. No torch/marker/pypdf/genai dependency,
matching chapter_index.py/page_markers.py -- shared as-is between
convert_textbook.py (uses these at conversion time) and describe_images.py
(reuses the exact same rules for its naming-reconciliation pass over
already-converted books, so the two can never drift out of sync with
each other).
"""
from __future__ import annotations

import os
import re

# Values commonly left behind by PDF-generating toolchains that don't count
# as a real, descriptive author -- e.g. many LaTeX distributions populate
# /Author with the engine name if \author{} was never set.
_GENERIC_METADATA_VALUES = {
    "latex", "tex", "pdftex", "pdflatex", "xelatex", "lualatex",
    "miktex", "texlive", "microsoft word", "writer", "unknown", ""
}


def sanitize_filename(text: str) -> str:
    """Sanitizes strings to ensure filesystem compatibility."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s-]", "", str(text)).strip()
    cleaned = re.sub(r"[-\s]+", "_", cleaned)
    # Collapse repeated underscores and trim stray leading/trailing ones.
    # Underscore is a word character, so it passes through both regexes
    # above untouched -- if the *input* already contains one (e.g. a source
    # filename with its own punctuation already sanitized to "_" upstream,
    # before this pipeline ever saw it), it can combine with this
    # function's own "_" separator to produce a folder name like
    # "Hayashi__Contents_2007" instead of "Hayashi_Contents_2007". Real,
    # confirmed incident.
    return re.sub(r"_+", "_", cleaned).strip("_")


def is_descriptive_bibliographic_info(info: dict) -> bool:
    """True if info has a real title, or a real (non-generic) author."""
    title_ok = bool(info.get("title", "").strip())
    author = info.get("author", "").strip().lower()
    author_ok = bool(author) and author not in _GENERIC_METADATA_VALUES
    return title_ok or author_ok


def merge_bibliographic_info(primary: dict, fallback: dict) -> dict:
    """Fill in only the blank fields of `primary` from `fallback`."""
    merged = dict(primary)
    for key in ("title", "author", "year"):
        if not merged.get(key):
            merged[key] = fallback.get(key, "")
    return merged


_FILENAME_YEAR_RE = re.compile(r'(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)')
_FILENAME_WORD_RE = re.compile(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+')
# The real, common convention for library/ebook-repository-downloaded PDFs
# (confirmed against real filenames, not assumed): "Title -- Author(s) --
# Edition/Place, Year -- Publisher -- isbn...", segments joined by " -- ".
# Distinct from -- and checked before -- the simpler camelCase/underscore
# convention below, since the two put title and author in opposite order
# and there's no way to tell which convention a given filename uses except
# by whether this separator is present at all.
_FILENAME_SEGMENT_SEP_RE = re.compile(r'\s*--\s*')


def extract_bibliographic_info_from_filename(raw_input: str) -> dict:
    """
    Last-resort tier: parses title/author/year out of a PDF's own filename
    (or a book's existing output folder name, when re-run during naming
    reconciliation). Only ever used to fill in whichever of title/author/
    year the tiers above (PDF document metadata, then LLM/regex parsing of
    the markdown title page) didn't find -- never overrides a real match
    from those, see merge_bibliographic_info().

    Two conventions recognized, tried in order:

    1. " -- "-delimited segments, e.g. "Econometrics -- Bruce E Hansen,
       1962- -- Princeton, New Jersey, 2022 -- Princeton University Press --
       isbn13 9780691235899.pdf" (a real filename from this pipeline's own
       input, and the common shape for library/ebook-repository downloads)
       -- segment 0 is the title, segment 1 the author(s); a first-guess
       "author is the first word" heuristic gets this exactly backwards; a
       Hayashi econometrics book from this same run was misnamed with
       "Econometrics" (its actual title) recorded as the author before this
       was caught and fixed. Year: the LAST 4-digit year found anywhere in
       the filename, not the first -- a birth year like "1962-" attached to
       an author's name (as above) reliably precedes the publication year in
       this convention, so taking the first match picks the wrong one.
    2. No " -- " found: falls back to the simpler camelCase/underscore
       convention ("HansenEconometrics2022.pdf" / "Hansen_Econometrics_2022.pdf"),
       assuming the first word is the author's last name and everything
       after it (minus the year) is the title -- wrong for a filename
       that's just the book's title with no author in it (the single
       leftover word becomes the title guess instead, not the author).

    Heuristic either way, not parsing -- same "naming convenience, not
    authoritative data" caveat as extract_bibliographic_info_from_markdown().
    A wrong guess here is still strictly a fallback of last resort, only
    reached when nothing upstream found anything usable for that field.
    """
    info = {"title": "", "author": "", "year": ""}
    stem = os.path.splitext(os.path.basename(raw_input))[0]

    year_matches = list(_FILENAME_YEAR_RE.finditer(stem))
    if year_matches:
        info["year"] = year_matches[-1].group(1)

    segments = [s.strip() for s in _FILENAME_SEGMENT_SEP_RE.split(stem) if s.strip()]
    if len(segments) >= 2:
        info["title"] = segments[0]
        info["author"] = segments[1]
        return info

    stem_without_year = stem
    if year_matches:
        last = year_matches[-1]
        stem_without_year = stem[:last.start()] + stem[last.end():]
    words = _FILENAME_WORD_RE.findall(re.sub(r'[_\-.]+', ' ', stem_without_year))
    if len(words) >= 2:
        info["author"] = words[0]
        info["title"] = " ".join(words[1:])
    elif len(words) == 1:
        info["title"] = words[0]

    return info


def derive_folder_name(bib_info: dict, raw_input: str) -> str:
    """
    The author_title_year folder-naming rule, used both at conversion time
    (convert_textbook.py's process_one_pdf) and by describe_images.py's
    naming-reconciliation pass over already-converted books -- kept as one
    shared function so the two can never independently drift.
    `raw_input` is only used as a title/whole-name fallback (its basename,
    sanitized), never as the author/year source -- callers wanting the
    filename itself considered as a bibliographic source should already
    have merged in extract_bibliographic_info_from_filename()'s result
    into `bib_info` before calling this.
    """
    if is_descriptive_bibliographic_info(bib_info):
        title_part = sanitize_filename(bib_info["title"]) or \
            sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0])
        if bib_info["author"]:
            first_author = bib_info["author"].split(",")[0].split(" and ")[0].strip()
            lastname_part = sanitize_filename(first_author.split()[-1]) if first_author else "UnknownAuthor"
        else:
            lastname_part = "UnknownAuthor"
        year_part = bib_info["year"] or "0000"
        return f"{lastname_part}_{title_part}_{year_part}"
    return sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "converted_textbook"
