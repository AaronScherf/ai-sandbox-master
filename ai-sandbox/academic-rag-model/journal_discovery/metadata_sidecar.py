"""
metadata_sidecar.py
Per spec S3: a <paper>.meta.json sidecar carrying OpenAlex bibliographic
data forward for Zotero sync and dedup, deliberately separate from
convert_journal_articles.py's own frontmatter schema (routing/model/tags),
which this subproject never touches.
"""
from __future__ import annotations

import json
from pathlib import Path

from journal_discovery.discovery import Work


def sidecar_path(pdf_path) -> Path:
    return Path(pdf_path).with_suffix(".meta.json")


def write_sidecar(pdf_path, work: Work, relevance_score: float | None, source_tier: str | None) -> None:
    data = {
        "title": work.title,
        "authors": work.authors,
        "year": work.year,
        "doi": work.doi,
        "openalex_id": work.openalex_id,
        "concepts": work.concepts,
        "source_tier": source_tier,
        "relevance_score": relevance_score,
        "page_count": work.page_count,
    }
    with open(sidecar_path(pdf_path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
