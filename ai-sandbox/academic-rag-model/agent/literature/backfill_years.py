"""Mechanical backfill of publication_year onto journal_article index cards that lack it (no LLM).

Three resolution tiers, in order: (1) an identifier (doi or openalex_id) already on the card; (2) for a
manually-downloaded paper with neither, a title match in research/journal-articles/needs_manual_downloads.md,
which records a doi/OpenAlex link per paper even after it converts; (3) last resort, an OpenAlex title search,
accepted only when the result's own title matches the card's -- a title search can return the wrong paper, so a
mismatch is reported, never silently applied. All three reuse discovery's own OpenAlex resolvers."""
from __future__ import annotations

import re
from pathlib import Path

from core.indexer.index_card import list_courses, load_shard, set_card_fields
from discovery.discover_journal_articles.discovery import (
    resolve_work_by_doi, resolve_work_by_openalex_id, resolve_work_by_title,
)

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://\S+)\)")


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def cards_missing_year(index_root: str) -> list[dict]:
    """journal_article cards with no publication_year, across every course."""
    return [card for course in list_courses(index_root) for card in load_shard(index_root, course)
            if card.get("doc_type") == "journal_article" and card.get("publication_year") is None]


def parse_manual_downloads(path) -> dict[str, tuple[str, str]]:
    """normalized title -> ('doi', bare doi) or ('openalex_id', url), from needs_manual_downloads.md's
    [title](link) entries. {} when the file doesn't exist."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for title, url in _LINK_RE.findall(text):
        if "doi.org/" in url:
            out[_normalize_title(title)] = ("doi", url.split("doi.org/", 1)[1])
        elif "openalex.org/" in url:
            out[_normalize_title(title)] = ("openalex_id", url)
    return out


def _default_manual_downloads_path(index_root: str) -> Path:
    return Path(index_root) / "journal-articles" / "needs_manual_downloads.md"


def resolve_year(card: dict, mailto: str, *, resolve_doi=resolve_work_by_doi,
                  resolve_openalex=resolve_work_by_openalex_id) -> int | None:
    """The card's publication year from OpenAlex, trying its doi first and its openalex_id second. None when
    neither identifier is present, or OpenAlex has no year for either lookup that succeeds."""
    doi = card.get("doi")
    if doi:
        work = resolve_doi(doi, mailto)
        if work and work.year:
            return work.year
    openalex_id = card.get("openalex_id")
    if openalex_id:
        work = resolve_openalex(openalex_id, mailto)
        if work and work.year:
            return work.year
    return None


def backfill_years(index_root: str, mailto: str, *, resolve_doi=resolve_work_by_doi,
                    resolve_openalex=resolve_work_by_openalex_id, resolve_title=resolve_work_by_title,
                    manual_downloads: dict[str, tuple[str, str]] | None = None) -> dict[str, str]:
    """Fills publication_year on every journal_article card missing it. Returns file_id -> outcome:
    'backfilled', 'no identifier' (nothing resolved it), 'not found in OpenAlex' (the card's own identifier
    didn't resolve), or 'uncertain title match: <title>' (a title search found a different-looking paper; not
    applied)."""
    if manual_downloads is None:
        manual_downloads = parse_manual_downloads(_default_manual_downloads_path(index_root))
    outcomes: dict[str, str] = {}
    for card in cards_missing_year(index_root):
        fid = card["file_id"]
        title = card.get("title") or ""
        if card.get("doi") or card.get("openalex_id"):
            year = resolve_year(card, mailto, resolve_doi=resolve_doi, resolve_openalex=resolve_openalex)
            if year is None:
                outcomes[fid] = "not found in OpenAlex"
            else:
                set_card_fields(index_root, fid, {"publication_year": year})
                outcomes[fid] = "backfilled"
            continue
        match = manual_downloads.get(_normalize_title(title))
        if match:
            kind, ident = match
            work = resolve_doi(ident, mailto) if kind == "doi" else resolve_openalex(ident, mailto)
            if work and work.year:
                set_card_fields(index_root, fid, {"publication_year": work.year, kind: ident})
                outcomes[fid] = "backfilled"
                continue
        work = resolve_title(title, mailto)
        if work is None or work.year is None:
            outcomes[fid] = "no identifier"
        elif _normalize_title(work.title) != _normalize_title(title):
            outcomes[fid] = f"uncertain title match: {work.title}"
        else:
            set_card_fields(index_root, fid, {"publication_year": work.year})
            outcomes[fid] = "backfilled"
    return outcomes
