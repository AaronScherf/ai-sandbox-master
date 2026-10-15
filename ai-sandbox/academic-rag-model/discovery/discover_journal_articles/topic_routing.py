"""
topic_routing.py
Per spec S1/S3: routes a fetched paper into a topic subfolder derived
from its top OpenAlex concept, auto-creating the folder when no existing
one fits (a deliberate design choice for this subproject -- contrast
indexer/retag.py's conservative fallback-tagging, discussed in the spec's
own follow-on section, S9).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from discovery.discover_journal_articles.discovery import Topic, Work

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def sanitize_topic_name(concept_display_name: str | None) -> str:
    if not concept_display_name:
        return "misc"
    cleaned = _NON_ALNUM_RE.sub("-", concept_display_name.strip().lower()).strip("-")
    return cleaned or "misc"


def route_to_folder(articles_dir, work: Work) -> Path:
    top_concept = work.concepts[0] if work.concepts else None
    folder_name = sanitize_topic_name(top_concept)
    folder = Path(articles_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def pdf_filename(work: Work) -> str:
    """Lives here, not in discovery.py alongside Work, specifically to
    avoid a circular import: this needs sanitize_topic_name(), and
    discovery.py must never import from topic_routing.py (which already
    imports Work from discovery.py)."""
    key = work.doi or work.openalex_id or work.title
    return f"{sanitize_topic_name(key)[:80] or 'paper'}.pdf"


@dataclass
class FolderProposal:
    current_folder: str
    candidates: list[tuple[str, float]]  # (sanitized folder name, score), highest first


def propose_folder(topics: list[Topic], current_folder: str) -> FolderProposal:
    """Ranks candidate folders by each topic's own relevance score --
    deliberately NOT breadth-first like route_to_folder()'s Concepts-
    based rule, since that rule is exactly what files an agriculture
    paper under 'Business' whenever Business happens to be the broadest
    Concept present. Pure function: never touches the filesystem or
    moves anything -- see resolve_folder_proposal() for the only thing
    that actually applies a decision."""
    seen: set[str] = set()
    candidates: list[tuple[str, float]] = []
    for topic in sorted(topics, key=lambda t: -t.score):
        folder_name = sanitize_topic_name(topic.display_name)
        if folder_name in seen:
            continue
        seen.add(folder_name)
        candidates.append((folder_name, topic.score))
    return FolderProposal(current_folder=current_folder, candidates=candidates)
