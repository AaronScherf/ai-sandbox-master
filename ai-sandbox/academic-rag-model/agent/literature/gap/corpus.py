"""The rows of literature.sqlite the gap analysis reads, as plain dataclasses."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fact:
    facet: str
    shown: str  # a vocabulary term id, an ISO country code, or "proposed:<wording>"
    label: str
    tier: str
    quote: str | None = None
    locator: str | None = None


@dataclass(frozen=True)
class PaperRow:
    file_id: str
    title: str | None
    year: int | None
    doi: str | None


@dataclass
class Corpus:
    papers: dict[str, PaperRow] = field(default_factory=dict)
    facts: dict[str, list[Fact]] = field(default_factory=dict)
    results: dict[str, list[dict]] = field(default_factory=dict)


def load_corpus(conn: sqlite3.Connection) -> Corpus:
    corpus = Corpus()
    for fid, title, year, doi in conn.execute("SELECT file_id, title, year, doi FROM papers ORDER BY file_id"):
        corpus.papers[fid] = PaperRow(fid, title, year, doi)
    for row in conn.execute("SELECT file_id, facet, term_id, label, tier, quote, locator FROM facts ORDER BY rowid"):
        corpus.facts.setdefault(row[0], []).append(Fact(*row[1:]))
    for fid, claim, direction, magnitude, quote in conn.execute(
            "SELECT file_id, claim, direction, magnitude, quote FROM results ORDER BY rowid"):
        corpus.results.setdefault(fid, []).append(
            {"claim": claim, "direction": direction, "magnitude": magnitude, "quote": quote})
    return corpus
