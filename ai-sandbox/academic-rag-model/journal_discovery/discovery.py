"""
discovery.py
OpenAlex-only work resolution: resolves a faculty name or topic query
into Work records. Knows nothing about relevance scoring, full-text
access, or where files land -- see relevance.py, access.py,
topic_routing.py for those.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from journal_discovery.http_utils import fetch_with_retries

_OPENALEX_BASE = "https://api.openalex.org"
COLUMBIA_ROR = "https://ror.org/00hj8s172"

_ARXIV_URL_RE = re.compile(r"arxiv\.org/abs/([\w.\-]+)", re.IGNORECASE)

# Confirmed live 2026-09-02: an author's OpenAlex works list includes
# RCT trial registrations and replication-data records (type="dataset")
# alongside real papers -- these can never have a fetchable PDF and
# shouldn't burn a --max-results/--max-examined candidate slot.
_EXCLUDED_WORK_TYPES = frozenset({"dataset"})


@dataclass
class Work:
    openalex_id: str
    doi: str | None
    title: str
    authors: list[str]
    year: int | None
    abstract: str | None
    concepts: list[str] = field(default_factory=list)
    oa_url: str | None = None
    is_oa: bool = False
    arxiv_id: str | None = None
    page_count: int | None = None


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """OpenAlex stores abstracts as {word: [positions]} to sidestep
    publisher copyright on the plain-text form -- reassembling it here is
    the standard, documented way to get the abstract back."""
    if not inverted_index:
        return None
    positions = []
    for word, indices in inverted_index.items():
        for index in indices:
            positions.append((index, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _bare_doi(doi_url: str | None) -> str | None:
    """OpenAlex's own `doi` field is a full https://doi.org/... URL, not
    a bare DOI -- Unpaywall's API and our own manifest/dedup keys both
    want the bare form."""
    if not doi_url:
        return None
    return doi_url.split("doi.org/")[-1]


def _extract_arxiv_id(record: dict) -> str | None:
    for location in record.get("locations") or []:
        url = (location or {}).get("landing_page_url") or ""
        match = _ARXIV_URL_RE.search(url)
        if match:
            return match.group(1)
    return None


def _work_from_openalex(record: dict) -> Work:
    concepts = sorted(record.get("concepts") or [], key=lambda c: c.get("score", 0), reverse=True)
    open_access = record.get("open_access") or {}
    return Work(
        openalex_id=record.get("id"),
        doi=_bare_doi(record.get("doi")),
        title=record.get("title") or "Untitled",
        authors=[
            (a.get("author") or {}).get("display_name", "")
            for a in record.get("authorships") or []
        ],
        year=record.get("publication_year"),
        abstract=reconstruct_abstract(record.get("abstract_inverted_index")),
        concepts=[c.get("display_name") for c in concepts if c.get("display_name")],
        oa_url=open_access.get("oa_url"),
        is_oa=bool(open_access.get("is_oa")),
        arxiv_id=_extract_arxiv_id(record),
        page_count=None,  # OpenAlex doesn't reliably provide this
    )


def resolve_author_id(name: str, mailto: str, ror: str = COLUMBIA_ROR) -> str | None:
    params = {"search": name, "mailto": mailto}
    if ror:
        params["filter"] = f"last_known_institutions.ror:{ror}"
    response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/authors", params=params)
    results = response.json().get("results", [])
    if not results and ror:
        response = fetch_with_retries(
            "GET", f"{_OPENALEX_BASE}/authors", params={"search": name, "mailto": mailto}
        )
        results = response.json().get("results", [])
    return results[0]["id"] if results else None


def iter_author_works(author_id: str, mailto: str, batch_size: int):
    page = 1
    while True:
        params = {
            "filter": f"author.id:{author_id}",
            "sort": "publication_year:desc,cited_by_count:desc",
            "per-page": batch_size,
            "page": page,
            "mailto": mailto,
        }
        response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/works", params=params)
        results = response.json().get("results", [])
        if not results:
            return
        for record in results:
            if record.get("type") in _EXCLUDED_WORK_TYPES:
                continue
            yield _work_from_openalex(record)
        page += 1


def iter_topic_works(keywords: str, mailto: str, batch_size: int, ror: str | None = None):
    page = 1
    while True:
        search_filter = f"default.search:{keywords}"
        if ror:
            search_filter += f",institutions.ror:{ror}"
        params = {
            "filter": search_filter,
            "per-page": batch_size,
            "page": page,
            "mailto": mailto,
        }
        response = fetch_with_retries("GET", f"{_OPENALEX_BASE}/works", params=params)
        results = response.json().get("results", [])
        if not results:
            return
        for record in results:
            if record.get("type") in _EXCLUDED_WORK_TYPES:
                continue
            yield _work_from_openalex(record)
        page += 1


def resolve_works(faculty: list[str], topics: list[str], mailto: str, batch_size: int):
    """Chains every --faculty query (fully paged) then every --topic query
    into one generator, per spec S4 step 1. Deliberately lazy (a
    generator, not a list) so an early stop in relevance.select_relevant_works
    (S3's max-results/max-examined ceilings) never pages further into
    OpenAlex than it needs to."""
    for name in faculty:
        author_id = resolve_author_id(name, mailto)
        if author_id is None:
            print(f"WARNING: could not resolve an OpenAlex author id for {name!r}; skipping.")
            continue
        yield from iter_author_works(author_id, mailto, batch_size)
    for keywords in topics:
        yield from iter_topic_works(keywords, mailto, batch_size)
