"""Mechanical backfill of publication_year onto journal_article index cards that lack it (no LLM).

Uses whichever identifier (doi, then openalex_id) a card already carries to look the year up on OpenAlex,
the same resolvers discovery's own pipeline uses, and stamps it on with set_card_fields."""
from __future__ import annotations

from core.indexer.index_card import list_courses, load_shard, set_card_fields
from discovery.discover_journal_articles.discovery import resolve_work_by_doi, resolve_work_by_openalex_id


def cards_missing_year(index_root: str) -> list[dict]:
    """journal_article cards with no publication_year, across every course."""
    return [card for course in list_courses(index_root) for card in load_shard(index_root, course)
            if card.get("doc_type") == "journal_article" and card.get("publication_year") is None]


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
                    resolve_openalex=resolve_work_by_openalex_id) -> dict[str, str]:
    """Fills publication_year on every journal_article card missing it. Returns file_id -> outcome:
    'backfilled', 'no identifier' (neither doi nor openalex_id on the card), or 'not found in OpenAlex'."""
    outcomes: dict[str, str] = {}
    for card in cards_missing_year(index_root):
        fid = card["file_id"]
        if not card.get("doi") and not card.get("openalex_id"):
            outcomes[fid] = "no identifier"
            continue
        year = resolve_year(card, mailto, resolve_doi=resolve_doi, resolve_openalex=resolve_openalex)
        if year is None:
            outcomes[fid] = "not found in OpenAlex"
            continue
        set_card_fields(index_root, fid, {"publication_year": year})
        outcomes[fid] = "backfilled"
    return outcomes
