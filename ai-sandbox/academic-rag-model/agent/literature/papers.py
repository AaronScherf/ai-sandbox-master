"""Which converted papers can be extracted, and the identity each carries from its index card."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.indexer.index_card import list_courses, load_shard

from .store import check_file_id
from .transcript import split_pages

_IDENTITY_KEYS = ("openalex_id", "doi", "publication_year", "openalex_topics")


@dataclass(frozen=True)
class Paper:
    file_id: str
    path: str
    title: str
    identity: dict


def eligible_papers(index_root: str) -> tuple[list[Paper], dict[str, str]]:
    """Journal papers whose transcript exists and has page markers, plus a file_id -> reason map for the rest."""
    papers: list[Paper] = []
    skipped: dict[str, str] = {}
    for course in list_courses(index_root):
        for card in load_shard(index_root, course):
            if card.get("doc_type") != "journal_article":
                continue
            fid = str(card.get("file_id") or "")
            try:
                check_file_id(fid)
            except ValueError:
                skipped[fid or "(no file_id)"] = "invalid file_id on the index card"
                continue
            if card.get("needs_indexing") or card.get("orphaned"):
                skipped[fid] = "card needs indexing or is orphaned; convert and index the paper first"
                continue
            rel = card.get("path") or ""
            md = Path(index_root) / rel
            if not rel or not md.is_file():
                skipped[fid] = "no transcript file"
                continue
            if not split_pages(md.read_text(encoding="utf-8")):
                skipped[fid] = "transcript has no page markers"
                continue
            identity = {"file_id": fid, "title": card.get("title") or ""}
            identity.update({k: card[k] for k in _IDENTITY_KEYS if card.get(k) is not None})
            papers.append(Paper(fid, rel, identity["title"], identity))
    return papers, skipped


def _title_key(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).split())


def drop_duplicate_titles(papers: list[Paper], have_record: set[str]) -> tuple[list[Paper], dict[str, str]]:
    """Keep one copy of each title (manual downloads produce duplicates): the copy that already has a record, else the
    lowest file_id. Papers without a title are never treated as duplicates. Returns (kept, file_id -> reason)."""
    groups: dict[str, list[Paper]] = {}
    for p in papers:
        groups.setdefault(_title_key(p.title) or f"\0{p.file_id}", []).append(p)
    keep: dict[str, str] = {}
    skipped: dict[str, str] = {}
    for members in groups.values():
        chosen = sorted(members, key=lambda p: (p.file_id not in have_record, p.file_id))[0]
        keep[chosen.file_id] = chosen.file_id
        for p in members:
            if p is not chosen:
                skipped[p.file_id] = f"duplicate of {chosen.file_id} (same title); use --include-duplicates to extract it anyway"
    return [p for p in papers if p.file_id in keep], skipped
