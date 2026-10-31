"""The recall probe: how many of OpenAlex's top works for the question's wording are already in the corpus (spec 2026-10-31)."""
from __future__ import annotations

import math
from datetime import date
from itertools import islice

from ..backfill_years import _normalize_title
from .corpus import Corpus
from .match import Constraint, vocab_for
from .subregions import Subregions
from discovery.discover_journal_articles.discovery import iter_topic_works

_QUERY_FACETS = ("intervention", "outcome")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval for k of n, or None when n is 0."""
    if n <= 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def build_query(constraints: list[Constraint], vocabs: dict, subregions: Subregions) -> str:
    """Intervention and outcome labels and country names, space-joined, duplicates dropped; other facets are left out."""
    words: list[str] = []
    for c in constraints:
        if c.facet == "countries":
            word = subregions.names.get(c.value.upper(), c.value)
        elif c.facet in _QUERY_FACETS:
            vocab = vocab_for(c.facet, vocabs)
            term = vocab.terms.get(c.value) if vocab is not None else None
            word = term.label if term else ""
        else:
            continue
        if word and word not in words:
            words.append(word)
    return " ".join(words)


def _id(value: str | None) -> str:
    return (value or "").strip().lower().removeprefix("https://openalex.org/")


def _doi(value: str | None) -> str:
    return (value or "").strip().lower().removeprefix("https://doi.org/")


def match_work(work, corpus: Corpus) -> tuple[str, str] | None:
    """(file id, rule) of the corpus paper this OpenAlex work is: by OpenAlex id, then DOI, then normalized title."""
    for rule, key, get in (("openalex_id", _id(work.openalex_id), lambda p: _id(p.openalex_id)),
                           ("doi", _doi(work.doi), lambda p: _doi(p.doi)),
                           ("title", _normalize_title(work.title), lambda p: _normalize_title(p.title))):
        if not key:
            continue
        for fid, paper in corpus.papers.items():
            if get(paper) == key:
                return fid, rule
    return None


def run_probe(corpus: Corpus, constraints: list[Constraint], vocabs: dict, subregions: Subregions, mailto: str,
              n: int = 25, fetch=None, today: str | None = None) -> dict:
    """Top-`n` OpenAlex works for the question's wording, matched to the corpus. Never raises: a failure is reported as `error`."""
    fetch = fetch or iter_topic_works
    query = build_query(constraints, vocabs, subregions)
    if not query:
        return {"query": query, "requested": n, "error": "the question has no intervention, outcome or country to search for"}
    matched, retrieved = [], 0
    try:
        for found in islice(fetch(query, mailto, n), n):
            retrieved += 1
            hit = match_work(found, corpus)
            if hit:
                matched.append({"file_id": hit[0], "by": hit[1]})
    except Exception as exc:  # network and HTTP failures vary by layer; the offline report must still be written
        return {"query": query, "requested": n, "error": f"{type(exc).__name__}: {exc}"}
    interval = wilson(len(matched), retrieved)
    return {"query": query, "requested": n, "retrieved": retrieved, "in_corpus": len(matched),
            "interval": list(interval) if interval else None, "matched": matched,
            "not_in_corpus": retrieved - len(matched), "fetched": today or date.today().isoformat()}
