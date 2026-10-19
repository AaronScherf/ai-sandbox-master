"""Page-level access to a converted transcript, and the quote check every extracted fact must pass."""
from __future__ import annotations

import re
import unicodedata

from .schema import MAX_QUOTE_CHARS, MIN_QUOTE_CHARS

_PAGE = re.compile(r"<!--\s*page\s+(\d+)\s*-->")
_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'", "\u201c": '"', "\u201d": '"',
                         "\u2013": "-", "\u2014": "-", "\u2212": "-"})
_MARKUP = re.compile(r"[*_`#>|]")


def split_pages(md: str) -> dict[int, str]:
    parts = _PAGE.split(md)
    # parts = [preamble, "1", text1, "2", text2, ...]
    return {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def normalize(text: str) -> str:
    """Fold what transcription and typesetting vary on, so a faithful quote matches and little else does:
    ligatures (NFKC), curly quotes and dashes, Markdown emphasis and table marks, and a hyphen between letters
    (so a word broken across a line, 'trans-\\nfers', matches 'transfers'), then case
    and whitespace. Minus signs and range dashes are kept: a dropped sign must not verify."""
    t = unicodedata.normalize("NFKC", text).replace("\u00ad", "").translate(_QUOTES)
    t = re.sub(r"(?<=[^\W\d_])-\s*(?=[^\W\d_])", "", _MARKUP.sub(" ", t))
    return re.sub(r"\s+", " ", t).strip().casefold()


def _pages_of(locator, pages: dict[int, str]) -> tuple[list[int] | None, str | None]:
    items = locator if isinstance(locator, list) else [locator]
    if not items or any(isinstance(p, bool) or not isinstance(p, int) for p in items):
        return None, "locator: give a page number, or a list of page numbers, that was offered on the card"
    missing = [p for p in items if p not in pages]
    if missing:
        return None, f"locator: page(s) {missing} were not offered on this card"
    return items, None


def check_quote(quote, locator, pages: dict[int, str]) -> str | None:
    """None when `quote` appears (after normalization) on the located page(s); otherwise why not."""
    located, problem = _pages_of(locator, pages)
    if problem:
        return problem
    if not isinstance(quote, str):
        return "quote: must be text copied from the page"
    n = len(quote.strip())
    if n < MIN_QUOTE_CHARS:
        return f"quote: must be at least {MIN_QUOTE_CHARS} characters"
    if n > MAX_QUOTE_CHARS:
        return f"quote: must be at most {MAX_QUOTE_CHARS} characters; quote the shortest passage that supports the fact"
    haystack = normalize(" ".join(pages[p] for p in located))
    if normalize(quote) not in haystack:
        label = "page " + ", ".join(map(str, located)) if len(located) == 1 else "pages " + ", ".join(map(str, located))
        return f"quote: not found on {label}; copy the wording exactly from the page text on the card"
    return None
