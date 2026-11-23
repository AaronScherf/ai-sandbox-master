"""Bibliographic metadata and DOI verification (spec A, step 1). Mismatches are flagged, never overwritten."""

import datetime
import json
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from difflib import SequenceMatcher

Lookup = Callable[[str], dict | None]
USER_AGENT = "academic-rag-model-doi-check/1.0"
TITLE_RATIO = 0.9
MIN_PREFIX_WORDS = 6  # a shorter title must be at least this long to match as a prefix


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z]+", " ", (text or "").casefold())).strip()


def title_match(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    short, long_ = sorted((na, nb), key=len)
    if len(short.split()) >= MIN_PREFIX_WORDS and long_.startswith(short + " "):
        return True  # a card often lacks the registry's subtitle
    return SequenceMatcher(None, na, nb).ratio() >= TITLE_RATIO


def _norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi.strip(), flags=re.I).lower()
    return doi or None


def parse_crossref_message(msg: dict) -> dict:
    authors = [a.get("name") or " ".join(p for p in (a.get("given"), a.get("family")) if p) for a in msg.get("author", [])]
    parts = (msg.get("issued") or {}).get("date-parts") or [[None]]
    return {
        "title": (msg.get("title") or [""])[0], "authors": [a for a in authors if a], "year": parts[0][0],
        "journal": (msg.get("container-title") or [""])[0], "doi": _norm_doi(msg.get("DOI")),
    }


def parse_openalex_work(work: dict) -> dict:
    source = ((work.get("primary_location") or {}).get("source") or {})
    return {
        "title": work.get("title") or "",
        "authors": [(a.get("author") or {}).get("display_name") for a in work.get("authorships", [])
                    if (a.get("author") or {}).get("display_name")],
        "year": work.get("publication_year"), "journal": source.get("display_name") or "",
        "doi": _norm_doi(work.get("doi")),
        "openalex_id": _short_id({"id": work["id"]}) if work.get("id") else None, "topics": parse_openalex_topics(work),
    }


def _get_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except (OSError, ValueError):
        return None


def crossref_lookup(doi: str) -> dict | None:
    data = _get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    return parse_crossref_message(data["message"]) if data and data.get("message") else None


def openalex_lookup(doi: str) -> dict | None:
    data = _get_json("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    return parse_openalex_work(data) if data and data.get("title") else None


def verify_bibliography(card: dict, lookup: Lookup, *, source: str = "crossref") -> dict:
    """Checks the card's DOI, title and year against a registry record. Returns fill-in `fields` (only for keys the
    card lacks), `doi_verified` {date, source, match} and `mismatches`."""
    verified = {"date": datetime.date.today().isoformat(), "source": source, "match": "unverified"}
    doi = _norm_doi(card.get("doi"))
    record = lookup(doi) if doi else None
    if not record:
        return {"fields": {}, "doi_verified": verified, "mismatches": []}
    mismatches = []
    if card.get("title") and record.get("title") and not title_match(card["title"], record["title"]):
        mismatches.append(f"title: card {card['title']!r} vs registry {record['title']!r}")
    if record.get("doi") and record["doi"] != doi:
        mismatches.append(f"doi: card {doi!r} vs registry {record['doi']!r}")
    fields = {}
    if not mismatches:
        for card_key, rec_key in (("authors", "authors"), ("publication_year", "year"), ("journal", "journal")):
            if not card.get(card_key) and record.get(rec_key):
                fields[card_key] = record[rec_key]
        if record.get("openalex_id"):
            fields["openalex_id"] = record["openalex_id"]
        if record.get("topics"):
            fields["openalex_topics"] = record["topics"]
    verified["match"] = "mismatch" if mismatches else "match"
    return {"fields": fields, "doi_verified": verified, "mismatches": mismatches}


def _short_id(value: dict | None) -> str | None:
    return value["id"].rstrip("/").rsplit("/", 1)[-1] if value and value.get("id") else None


def parse_openalex_topics(work: dict) -> list[dict]:
    """Scored topics of an OpenAlex work with their field, subfield and domain ids (short form)."""
    return [{"id": _short_id({"id": t["id"]}), "name": t.get("display_name", ""), "score": t.get("score"),
             "field_id": _short_id(t.get("field")), "subfield_id": _short_id(t.get("subfield")),
             "domain_id": _short_id(t.get("domain"))} for t in work.get("topics", []) if t.get("id")]


def fetch_openalex_topics(openalex_id: str) -> list[dict] | None:
    short = openalex_id.rstrip("/").rsplit("/", 1)[-1]
    data = _get_json("https://api.openalex.org/works/" + urllib.parse.quote(short))
    return parse_openalex_topics(data) if data else None
