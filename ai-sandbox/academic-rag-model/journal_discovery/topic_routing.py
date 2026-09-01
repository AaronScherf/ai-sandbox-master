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
from pathlib import Path

from journal_discovery.discovery import Work

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
